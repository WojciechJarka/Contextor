# CONTEXTOR C16-B03-P1D3F3

## FILES_CHANGED

- contextor/core/cycle_semantics/optional_store_generation.py
- tests/test_cycle_semantics_optional_store_generation.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. New module: 14 passed in 14.70 s. Six specified modules: 76 passed in 40.57 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP module contexts for both new modules: canonical_revision=1043, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, same as prechange count; no new structural cycle observed. Cycle_semantics family=stale. No production FULL, update_file, backend restart, or commit. Assessment is local snapshot consistency only; installed LIVE authority and original source provenance remain unproven.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/optional_store_generation.py b/contextor/core/cycle_semantics/optional_store_generation.py
new file mode 100644
index 0000000..2dbce0b
--- /dev/null
+++ b/contextor/core/cycle_semantics/optional_store_generation.py
@@ -0,0 +1,227 @@
+"""Compare optional preview with the current local snapshot.
+
+The cache directory is caller-selected. A successful result means
+consistency with the generation returned by the existing local
+snapshot reader.
+
+This does not authenticate repository ownership, original source
+provenance, installed LIVE, atomic source capture or runtime safety.
+
+No new receipt, publication or warning authority is created.
+"""
+
+from __future__ import annotations
+
+import pickle
+
+from dataclasses import dataclass
+from pathlib import Path
+
+from contextor.core.live_state.store import (
+    LiveStateMetadata,
+    load_snapshot,
+    read_metadata,
+)
+
+from .optional_generation_anchor import (
+    OPTIONAL_GENERATION_ANCHOR_AUTHORITY,
+    OPTIONAL_GENERATION_ANCHOR_VERSION,
+    OptionalPreparedGenerationAnchor,
+    OptionalPreparedGenerationAssessment,
+    assess_optional_prepared_generation,
+)
+from .original_worker_preparation import (
+    OriginalWorkerManifestPreparation,
+)
+
+
+OPTIONAL_STORE_ASSESSMENT_AUTHORITY = (
+    "CALLER_SELECTED_LOCAL_SNAPSHOT_READ_CONSISTENCY"
+    "_NOT_ORIGIN_OR_LIVE_AUTHENTICATED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+
+@dataclass(frozen=True)
+class OptionalStoredGenerationAssessment:
+    status: str
+    reason: str | None
+    revision: int | None
+    state_id: str | None
+    graph_sha256: str | None
+    source_manifest_sha256: str | None
+    authority: str = OPTIONAL_STORE_ASSESSMENT_AUTHORITY
+
+
+def assess_optional_stored_generation(
+    cache_dir: str | Path,
+    anchor: object,
+    preparation: object,
+) -> OptionalStoredGenerationAssessment:
+    """Assess v3 preview against the current local cache generation.
+
+    The existing snapshot loader validates persisted metadata.
+    A second metadata read detects an observed generation rollover.
+
+    The operation does not hold a lock across all checks and does
+    not establish atomicity or installed LIVE authority.
+    """
+
+    revision = (
+        anchor.revision
+        if type(anchor) is OptionalPreparedGenerationAnchor
+        and type(anchor.revision) is int
+        else None
+    )
+
+    state_id = (
+        anchor.state_id
+        if type(anchor) is OptionalPreparedGenerationAnchor
+        and type(anchor.state_id) is str
+        else None
+    )
+
+    def unavailable(reason: str):
+        return OptionalStoredGenerationAssessment(
+            status="UNAVAILABLE",
+            reason=reason,
+            revision=revision,
+            state_id=state_id,
+            graph_sha256=None,
+            source_manifest_sha256=None,
+        )
+
+    if (
+        not isinstance(cache_dir, (str, Path))
+        or not str(cache_dir)
+        or type(anchor) is not OptionalPreparedGenerationAnchor
+        or type(preparation) is not OriginalWorkerManifestPreparation
+    ):
+        return unavailable("INVALID_INPUT_CONTRACT")
+
+    if (
+        type(anchor.revision) is not int
+        or anchor.revision < 1
+        or type(anchor.state_id) is not str
+        or not anchor.state_id
+        or type(anchor.repo_id) is not str
+        or not anchor.repo_id
+        or type(anchor.root_path) is not str
+        or not anchor.root_path
+        or anchor.version != OPTIONAL_GENERATION_ANCHOR_VERSION
+        or anchor.authority != OPTIONAL_GENERATION_ANCHOR_AUTHORITY
+    ):
+        return unavailable("INVALID_ANCHOR_IDENTITY")
+
+    try:
+        before = read_metadata(cache_dir)
+    except (
+        OSError,
+        TypeError,
+        ValueError,
+        AttributeError,
+    ):
+        return unavailable("STORE_METADATA_UNAVAILABLE")
+
+    if type(before) is not LiveStateMetadata:
+        return unavailable("STORE_METADATA_UNAVAILABLE")
+
+    if (
+        before.revision,
+        before.state_id,
+        before.repo_id,
+        before.root_path,
+    ) != (
+        anchor.revision,
+        anchor.state_id,
+        anchor.repo_id,
+        anchor.root_path,
+    ):
+        return unavailable("STORE_GENERATION_NOT_CURRENT")
+
+    try:
+        loaded = load_snapshot(
+            cache_dir,
+            anchor.state_id,
+            expected_repo_id=anchor.repo_id,
+            expected_root_path=anchor.root_path,
+        )
+    except (
+        OSError,
+        EOFError,
+        pickle.PickleError,
+        TypeError,
+        ValueError,
+        AttributeError,
+        KeyError,
+        RecursionError,
+        OverflowError,
+    ):
+        return unavailable("STORE_SNAPSHOT_UNAVAILABLE")
+
+    if type(loaded) is not tuple or len(loaded) != 2:
+        return unavailable("STORE_SNAPSHOT_UNAVAILABLE")
+
+    state, metadata = loaded
+
+    if (
+        type(metadata) is not LiveStateMetadata
+        or metadata != before
+    ):
+        return unavailable("LOADED_METADATA_MISMATCH")
+
+    try:
+        after = read_metadata(cache_dir)
+    except (
+        OSError,
+        TypeError,
+        ValueError,
+        AttributeError,
+    ):
+        return unavailable("STORE_HEAD_CHANGED")
+
+    if type(after) is not LiveStateMetadata or after != before:
+        return unavailable("STORE_HEAD_CHANGED")
+
+    try:
+        assessment = assess_optional_prepared_generation(
+            anchor,
+            preparation,
+            state,
+            metadata,
+        )
+    except (
+        AttributeError,
+        TypeError,
+        ValueError,
+        KeyError,
+        IndexError,
+        RecursionError,
+        OverflowError,
+    ):
+        return unavailable("GENERATION_ASSESSMENT_UNAVAILABLE")
+
+    if (
+        type(assessment) is not OptionalPreparedGenerationAssessment
+        or assessment.status
+        != "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
+        or assessment.reason is not None
+    ):
+        reason = (
+            assessment.reason
+            if type(assessment) is OptionalPreparedGenerationAssessment
+            else None
+        )
+
+        return unavailable(
+            "GENERATION_" + (reason or "UNAVAILABLE")
+        )
+
+    return OptionalStoredGenerationAssessment(
+        status="MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC",
+        reason=None,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        graph_sha256=assessment.graph_sha256,
+        source_manifest_sha256=assessment.source_manifest_sha256,
+    )

diff --git a/tests/test_cycle_semantics_optional_store_generation.py b/tests/test_cycle_semantics_optional_store_generation.py
new file mode 100644
index 0000000..a0f41eb
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_store_generation.py
@@ -0,0 +1,325 @@
+"""P1D3F3: local snapshot generation consistency without receipts."""
+
+from copy import copy
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+import contextor.core.cycle_semantics.optional_store_generation as store_module
+
+from contextor.core.cycle_semantics.optional_store_generation import (
+    OPTIONAL_STORE_ASSESSMENT_AUTHORITY,
+    OptionalStoredGenerationAssessment,
+    assess_optional_stored_generation,
+)
+from contextor.core.paths import repo_cache_dir
+from tests.test_cycle_semantics_optional_generation_anchor import (
+    _optional,
+)
+from tests.test_cycle_semantics_optional_child_full_preview import (
+    _repo,
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
+def _case(tmp_path):
+    root = _repo(tmp_path)
+    result = _optional(root)
+
+    return (
+        root,
+        result.cycle_source_preparation_generation_anchor,
+        result.cycle_source_preparation_preview,
+    )
+
+
+def _assess(case):
+    root, anchor, preparation = case
+
+    return assess_optional_stored_generation(
+        repo_cache_dir(root),
+        anchor,
+        preparation,
+    )
+
+
+def test_current_local_snapshot_matches(
+    tmp_path, isolated_dirs,
+):
+    case = _case(tmp_path)
+    root, anchor, preparation = case
+
+    result = _assess(case)
+    state, metadata = _persisted(root)
+
+    assert type(result) is OptionalStoredGenerationAssessment
+    assert result.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"
+    assert result.reason is None
+    assert result.authority == OPTIONAL_STORE_ASSESSMENT_AUTHORITY
+
+    assert result.revision == metadata.revision
+    assert result.state_id == metadata.state_id
+    assert result.graph_sha256 == anchor.graph_sha256
+    assert result.source_manifest_sha256 == (
+        preparation.manifest.source_manifest_sha256
+    )
+
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+
+    assert result == _assess(case)
+
+
+def test_old_anchor_rejected_after_new_full_even_with_same_digest(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    first = _optional(root)
+    old_anchor = first.cycle_source_preparation_generation_anchor
+    old_preparation = first.cycle_source_preparation_preview
+
+    second = _optional(root)
+    new_anchor = second.cycle_source_preparation_generation_anchor
+    new_preparation = second.cycle_source_preparation_preview
+
+    assert new_anchor.revision > old_anchor.revision
+    assert (
+        old_anchor.source_manifest_sha256
+        == new_anchor.source_manifest_sha256
+    )
+
+    old = assess_optional_stored_generation(
+        repo_cache_dir(root),
+        old_anchor,
+        old_preparation,
+    )
+
+    new = assess_optional_stored_generation(
+        repo_cache_dir(root),
+        new_anchor,
+        new_preparation,
+    )
+
+    assert old.status == "UNAVAILABLE"
+    assert old.reason == "STORE_GENERATION_NOT_CURRENT"
+
+    assert new.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"
+
+
+@pytest.mark.parametrize(
+    "field,value",
+    [
+        ("revision", 999999),
+        ("state_id", "foreign-state"),
+        ("repo_id", "foreign-repo"),
+        ("root_path", "foreign-root"),
+    ],
+)
+def test_foreign_generation_rejected(
+    tmp_path, isolated_dirs, field, value,
+):
+    case = list(_case(tmp_path))
+    case[1] = replace(case[1], **{field: value})
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "STORE_GENERATION_NOT_CURRENT"
+
+
+def test_missing_store_metadata_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    monkeypatch.setattr(
+        store_module,
+        "read_metadata",
+        lambda _path: None,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "STORE_METADATA_UNAVAILABLE"
+
+
+def test_missing_snapshot_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    monkeypatch.setattr(
+        store_module,
+        "load_snapshot",
+        lambda *args, **kwargs: None,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "STORE_SNAPSHOT_UNAVAILABLE"
+
+
+def test_loaded_metadata_mismatch_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    original = store_module.load_snapshot
+
+    def mismatched(*args, **kwargs):
+        loaded = original(*args, **kwargs)
+        state, metadata = loaded
+
+        return (
+            state,
+            replace(
+                metadata,
+                revision=metadata.revision + 1,
+            ),
+        )
+
+    monkeypatch.setattr(
+        store_module,
+        "load_snapshot",
+        mismatched,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "LOADED_METADATA_MISMATCH"
+
+
+def test_observed_store_head_rollover_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+    root = case[0]
+
+    original = store_module.read_metadata
+    initial = original(repo_cache_dir(root))
+    calls = []
+
+    def changed(_path):
+        calls.append(1)
+
+        if len(calls) == 1:
+            return initial
+
+        return replace(
+            initial,
+            revision=initial.revision + 1,
+        )
+
+    monkeypatch.setattr(
+        store_module,
+        "read_metadata",
+        changed,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "STORE_HEAD_CHANGED"
+    assert len(calls) == 2
+
+
+def test_stale_loaded_generation_rejected(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    original = store_module.load_snapshot
+
+    def stale(*args, **kwargs):
+        loaded = original(*args, **kwargs)
+        state, metadata = loaded
+
+        changed = copy(state)
+        changed.cycle_semantics_state = "stale"
+
+        return changed, metadata
+
+    monkeypatch.setattr(
+        store_module,
+        "load_snapshot",
+        stale,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "GENERATION_CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"
+    )
+
+
+def test_forged_manifest_digest_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+    preparation = case[2]
+
+    case[2] = replace(
+        preparation,
+        manifest=replace(
+            preparation.manifest,
+            source_manifest_sha256="0" * 64,
+        ),
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "GENERATION_ANCHOR_METADATA_MISMATCH"
+    )
+
+
+def test_invalid_anchor_authority_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+
+    case[1] = replace(
+        case[1],
+        authority="FORGED_AUTHORITY",
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "INVALID_ANCHOR_IDENTITY"
+
+
+def test_assessment_does_not_reread_python_sources(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    original = Path.read_bytes
+
+    def guarded(self):
+        if self.suffix == ".py":
+            raise AssertionError(
+                "Python source reread forbidden"
+            )
+
+        return original(self)
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(Path, "read_bytes", guarded)
+        result = _assess(case)
+
+    assert result.status == "MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC"
```

## FINAL_VERDICT

PASS
