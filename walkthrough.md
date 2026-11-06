# CONTEXTOR C16-B03-P1D3F1

## FILES_CHANGED

- contextor/core/cycle_semantics/optional_generation_anchor.py
- contextor/core/api/facade.py
- tests/test_cycle_semantics_optional_generation_anchor.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2, six specified modules, `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository: 77 passed, 1 failed in 44.00 s. Failed: `test_identical_sources_distinct_full_generations`. The second anchor revision increased as expected, but state_id differed: `20261106_164559` versus `20261106_164558`; test requires equality. No further code or test edits. `git diff --check` passed.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Final Contextor MCP module contexts: facade and optional_generation_anchor at canonical_revision=1036; test at revision=1037. All canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, fresh; cycle_semantics family=stale. No production FULL, update_file, restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index bab03bc..bb45ca0 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1510,6 +1510,26 @@ class ContextorFacade:
                 file_state_payload=file_state_payload,
                 **store_manifest_kwargs,
             )
+            if (
+                cycle_source_selection == "OPTIONAL_NAMED_CHILDREN"
+                and cycle_source_preparation_preview
+                and cycle_source_preparation is not None
+                and meta is not None
+                and analysis_result is not None
+            ):
+                from contextor.core.cycle_semantics.optional_generation_anchor import (
+                    make_optional_prepared_generation_anchor,
+                )
+
+                optional_anchor = make_optional_prepared_generation_anchor(
+                    cycle_source_preparation,
+                    meta,
+                )
+
+                if optional_anchor is not None:
+                    analysis_result.cycle_source_preparation_generation_anchor = (
+                        optional_anchor
+                    )
             emit_stage_component_end(
                 "persistence",
                 "snapshot_save",

diff --git a/contextor/core/cycle_semantics/optional_generation_anchor.py b/contextor/core/cycle_semantics/optional_generation_anchor.py
new file mode 100644
index 0000000..8bcd464
--- /dev/null
+++ b/contextor/core/cycle_semantics/optional_generation_anchor.py
@@ -0,0 +1,100 @@
+"""Post-save identity label for an optional preparation preview.
+
+This caller-visible label does not authenticate the store, original
+source bytes, atomicity, installed LIVE, or Python runtime safety.
+It is not a receipt and must never authorize warning suppression.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from .generation_manifest import (
+    OPTIONAL_MANIFEST_VERSION,
+    PreparedCycleSourceManifest,
+    verify_prepared_optional_manifest_digest,
+)
+from .original_worker_preparation import (
+    OriginalWorkerManifestPreparation,
+)
+
+
+OPTIONAL_GENERATION_ANCHOR_VERSION = (
+    "cycle-optional-generation-anchor/1"
+)
+OPTIONAL_GENERATION_ANCHOR_AUTHORITY = (
+    "CALLER_SUPPLIED_POST_SAVE_METADATA"
+    "_NOT_SOURCE_OR_LIVE_AUTHENTICATED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+
+@dataclass(frozen=True)
+class OptionalPreparedGenerationAnchor:
+    revision: int
+    state_id: str
+    repo_id: str
+    root_path: str
+    graph_sha256: str
+    source_manifest_sha256: str
+    version: str = OPTIONAL_GENERATION_ANCHOR_VERSION
+    authority: str = OPTIONAL_GENERATION_ANCHOR_AUTHORITY
+
+
+def make_optional_prepared_generation_anchor(
+    preparation: object,
+    metadata: object,
+) -> OptionalPreparedGenerationAnchor | None:
+    """Label a prepared v3 manifest with supplied post-save metadata.
+
+    Pure consistency check. Caller origin is not authenticated.
+    Does not read files, access LIVE, modify state or seal receipts.
+    """
+    from contextor.core.live_state.store import LiveStateMetadata
+
+    if (
+        type(preparation) is not OriginalWorkerManifestPreparation
+        or type(metadata) is not LiveStateMetadata
+        or preparation.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or preparation.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        or preparation.reason is not None
+        or type(preparation.manifest) is not PreparedCycleSourceManifest
+        or type(metadata.revision) is not int
+        or metadata.revision < 1
+        or type(metadata.state_id) is not str
+        or not metadata.state_id
+        or type(metadata.repo_id) is not str
+        or not metadata.repo_id
+        or type(metadata.root_path) is not str
+        or not metadata.root_path
+    ):
+        return None
+
+    manifest = preparation.manifest
+
+    if (
+        manifest.version != OPTIONAL_MANIFEST_VERSION
+        or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or not verify_prepared_optional_manifest_digest(manifest)
+        or preparation.component_preparations != manifest.components
+        or type(preparation.source_modules) is not tuple
+    ):
+        return None
+
+    expected_sources = tuple(sorted({
+        module
+        for component in manifest.components
+        for module, _, _ in component.source_signatures
+    }))
+
+    if preparation.source_modules != expected_sources:
+        return None
+
+    return OptionalPreparedGenerationAnchor(
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+        graph_sha256=manifest.graph_sha256,
+        source_manifest_sha256=manifest.source_manifest_sha256,
+    )

diff --git a/tests/test_cycle_semantics_optional_generation_anchor.py b/tests/test_cycle_semantics_optional_generation_anchor.py
new file mode 100644
index 0000000..7c19f23
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_generation_anchor.py
@@ -0,0 +1,207 @@
+"""P1D3F1: optional generation labels remain ephemeral."""
+
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.optional_generation_anchor import (
+    OPTIONAL_GENERATION_ANCHOR_AUTHORITY,
+    OPTIONAL_GENERATION_ANCHOR_VERSION,
+    OptionalPreparedGenerationAnchor,
+    make_optional_prepared_generation_anchor,
+)
+from tests.test_cycle_semantics_optional_child_full_preview import (
+    _repo,
+    _run,
+)
+from tests.test_original_worker_full_receipt_optin import (
+    _persisted,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _optional(root):
+    return _run(
+        root,
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+    )
+
+
+def test_official_full_returns_post_save_generation_anchor(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    result = _optional(root)
+    preview = result.cycle_source_preparation_preview
+    anchor = result.cycle_source_preparation_generation_anchor
+    state, metadata = _persisted(root)
+
+    assert type(anchor) is OptionalPreparedGenerationAnchor
+    assert anchor.version == OPTIONAL_GENERATION_ANCHOR_VERSION
+    assert anchor.authority == OPTIONAL_GENERATION_ANCHOR_AUTHORITY
+
+    assert (
+        anchor.revision,
+        anchor.state_id,
+        anchor.repo_id,
+        anchor.root_path,
+    ) == (
+        metadata.revision,
+        metadata.state_id,
+        metadata.repo_id,
+        metadata.root_path,
+    )
+
+    assert anchor.graph_sha256 == preview.manifest.graph_sha256
+    assert anchor.source_manifest_sha256 == (
+        preview.manifest.source_manifest_sha256
+    )
+    assert anchor.graph_sha256 == state.cycle_semantics.graph_sha256
+
+    assert anchor == make_optional_prepared_generation_anchor(
+        preview, metadata
+    )
+
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+    assert not hasattr(
+        state, "cycle_source_preparation_generation_anchor"
+    )
+    assert not hasattr(
+        state, "cycle_source_preparation_preview"
+    )
+
+
+def test_identical_sources_distinct_full_generations(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    first = _optional(root)
+    first_anchor = first.cycle_source_preparation_generation_anchor
+    first_manifest = (
+        first.cycle_source_preparation_preview.manifest
+    )
+
+    second = _optional(root)
+    second_anchor = second.cycle_source_preparation_generation_anchor
+    second_manifest = (
+        second.cycle_source_preparation_preview.manifest
+    )
+
+    assert second_anchor.revision > first_anchor.revision
+    assert second_anchor.state_id == first_anchor.state_id
+    assert second_anchor.repo_id == first_anchor.repo_id
+    assert second_anchor.root_path == first_anchor.root_path
+
+    assert (
+        first_manifest.source_manifest_sha256
+        == second_manifest.source_manifest_sha256
+    )
+    assert (
+        first_anchor.source_manifest_sha256
+        == second_anchor.source_manifest_sha256
+    )
+    assert first_anchor != second_anchor
+
+
+def test_default_full_has_no_optional_anchor(
+    tmp_path, isolated_dirs,
+):
+    result = _run(_repo(tmp_path))
+    assert not hasattr(
+        result, "cycle_source_preparation_generation_anchor"
+    )
+
+
+def test_hard_only_preview_has_no_optional_anchor(
+    tmp_path, isolated_dirs,
+):
+    result = _run(
+        _repo(tmp_path),
+        cycle_source_preparation_preview=True,
+    )
+    assert not hasattr(
+        result, "cycle_source_preparation_generation_anchor"
+    )
+
+
+def test_unavailable_optional_preview_has_no_anchor(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    (root / "pkg" / "b.py").write_bytes(b"value = 1\n")
+
+    result = _optional(root)
+
+    assert result.cycle_source_preparation_preview.status == (
+        "UNAVAILABLE"
+    )
+    assert not hasattr(
+        result, "cycle_source_preparation_generation_anchor"
+    )
+
+
+def test_forged_manifest_does_not_receive_anchor(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    result = _optional(root)
+    preview = result.cycle_source_preparation_preview
+    _, metadata = _persisted(root)
+
+    forged = replace(
+        preview,
+        manifest=replace(
+            preview.manifest,
+            source_manifest_sha256="0" * 64,
+        ),
+    )
+
+    assert make_optional_prepared_generation_anchor(
+        forged, metadata
+    ) is None
+
+
+def test_wrong_source_domain_does_not_receive_anchor(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    result = _optional(root)
+    preview = result.cycle_source_preparation_preview
+    _, metadata = _persisted(root)
+
+    forged = replace(
+        preview,
+        source_modules=("foreign",),
+    )
+
+    assert make_optional_prepared_generation_anchor(
+        forged, metadata
+    ) is None
+
+
+def test_generation_anchor_does_not_reread_sources(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    result = _optional(root)
+    preview = result.cycle_source_preparation_preview
+    _, metadata = _persisted(root)
+
+    def forbidden(self):
+        raise AssertionError("filesystem reread forbidden")
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(Path, "read_bytes", forbidden)
+        anchor = make_optional_prepared_generation_anchor(
+            preview, metadata
+        )
+
+    assert type(anchor) is OptionalPreparedGenerationAnchor
```

## FINAL_VERDICT

TEST_FAILURE
