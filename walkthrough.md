# CONTEXTOR C16-B03-P1D3F2

## FILES_CHANGED

- contextor/core/cycle_semantics/optional_generation_anchor.py
- tests/test_cycle_semantics_optional_generation_verification.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; first required test module with `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository: 13 passed, 1 failed in 15.78 s. Failed: `test_modified_canonical_graph_rejected` raises `dataclasses.FrozenInstanceError: cannot assign to field 'hard_edges'` at test setup, before assessment. The six-module follow-up was not run because the required first stage failed and the task says stop on TEST_FAILURE. No independent redesign or fix. `git diff --check` passed.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Final Contextor MCP module contexts for both changed modules: canonical_revision=1040, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16; cycle_semantics family=stale. An intermediate read of production module at revision 1039 returned workspace_sync=unverified; final revision 1040 verified. No production FULL, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/optional_generation_anchor.py b/contextor/core/cycle_semantics/optional_generation_anchor.py
index 8bcd464..336f0c7 100644
--- a/contextor/core/cycle_semantics/optional_generation_anchor.py
+++ b/contextor/core/cycle_semantics/optional_generation_anchor.py
@@ -98,3 +98,162 @@ def make_optional_prepared_generation_anchor(
         graph_sha256=manifest.graph_sha256,
         source_manifest_sha256=manifest.source_manifest_sha256,
     )
+
+
+OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY = (
+    "CALLER_SUPPLIED_GENERATION_CONSISTENCY"
+    "_NOT_STORE_OR_SOURCE_OR_LIVE_AUTHENTICATED"
+    "_NOT_RUNTIME_SAFETY"
+)
+
+
+@dataclass(frozen=True)
+class OptionalPreparedGenerationAssessment:
+    status: str
+    reason: str | None
+    revision: int | None
+    state_id: str | None
+    graph_sha256: str | None
+    source_manifest_sha256: str | None
+    authority: str = OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY
+
+
+def assess_optional_prepared_generation(
+    anchor: object,
+    preparation: object,
+    state: object,
+    metadata: object,
+) -> OptionalPreparedGenerationAssessment:
+    """Compare v3 preview against a supplied canonical generation.
+
+    No filesystem access, store lookup, LIVE IPC, mutation, receipt,
+    source-origin certification or runtime safety determination.
+    The caller supplies state and metadata; their origin is not proven.
+    """
+    from contextor.core.analysis.state_manager import (
+        RepositoryAnalysisState,
+    )
+    from contextor.core.live_state.store import LiveStateMetadata
+    from .contracts import CycleSemanticsSnapshot
+    from .partial_scc_claims import (
+        PreparedOptionalPartialSCCClaims,
+        validate_optional_partial_scc_claims,
+    )
+
+    revision = (
+        anchor.revision
+        if type(anchor) is OptionalPreparedGenerationAnchor
+        and type(anchor.revision) is int
+        else None
+    )
+    state_id = (
+        anchor.state_id
+        if type(anchor) is OptionalPreparedGenerationAnchor
+        and type(anchor.state_id) is str
+        else None
+    )
+
+    def unavailable(reason):
+        return OptionalPreparedGenerationAssessment(
+            status="UNAVAILABLE",
+            reason=reason,
+            revision=revision,
+            state_id=state_id,
+            graph_sha256=None,
+            source_manifest_sha256=None,
+        )
+
+    if (
+        type(anchor) is not OptionalPreparedGenerationAnchor
+        or type(preparation) is not OriginalWorkerManifestPreparation
+        or type(state) is not RepositoryAnalysisState
+        or type(metadata) is not LiveStateMetadata
+    ):
+        return unavailable("INVALID_INPUT_CONTRACT")
+
+    try:
+        expected_anchor = make_optional_prepared_generation_anchor(
+            preparation, metadata,
+        )
+    except (
+        AttributeError, KeyError, TypeError, ValueError,
+        RecursionError, OverflowError,
+    ):
+        return unavailable("PREPARATION_CONTRACT_INVALID")
+
+    if expected_anchor is None or anchor != expected_anchor:
+        return unavailable("ANCHOR_METADATA_MISMATCH")
+
+    if (
+        type(getattr(state, "revision", None)) is not int
+        or state.revision != metadata.revision
+        or type(getattr(state, "state_id", None)) is not str
+        or state.state_id != metadata.state_id
+    ):
+        return unavailable("CANONICAL_GENERATION_IDENTITY_MISMATCH")
+
+    snapshot = getattr(state, "cycle_semantics", None)
+
+    if (
+        getattr(state, "cycle_semantics_state", None) != "fresh"
+        or getattr(state, "cycles_state", None) != "fresh"
+        or getattr(state, "resync_required", False) is not False
+        or type(snapshot) is not CycleSemanticsSnapshot
+        or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or snapshot.source_issues
+    ):
+        return unavailable("CANONICAL_CYCLE_EVIDENCE_NOT_FRESH")
+
+    graph = getattr(state, "dependency_graph", None)
+    hard_edges = getattr(graph, "hard_edges", None)
+    modules = getattr(state, "modules", None)
+    package_root = getattr(state, "package_root", None)
+
+    if (
+        type(hard_edges) is not dict
+        or type(modules) is not dict
+        or set(hard_edges) != set(modules)
+        or package_root is not None
+        and type(package_root) is not str
+    ):
+        return unavailable("CANONICAL_INDEX_GRAPH_DOMAIN_INVALID")
+
+    indexed_imports = {}
+
+    try:
+        indexed_imports = {
+            name: module.imports
+            for name, module in modules.items()
+        }
+
+        claims = validate_optional_partial_scc_claims(
+            hard_edges,
+            snapshot,
+            preparation,
+            indexed_imports,
+            package_root=package_root or None,
+        )
+    except (
+        AttributeError, KeyError, TypeError, ValueError,
+        IndexError, RecursionError, OverflowError,
+    ):
+        return unavailable("OPTIONAL_CLAIM_VALIDATION_UNAVAILABLE")
+
+    if (
+        type(claims) is not PreparedOptionalPartialSCCClaims
+        or claims.graph_sha256 != anchor.graph_sha256
+        or claims.declared_manifest_sha256
+        != anchor.source_manifest_sha256
+        or claims.source_modules != preparation.source_modules
+        or claims.components != preparation.component_preparations
+    ):
+        return unavailable("OPTIONAL_DECLARATIONS_GENERATION_MISMATCH")
+
+    return OptionalPreparedGenerationAssessment(
+        status="MATCHED_SUPPLIED_GENERATION_NON_ATOMIC",
+        reason=None,
+        revision=metadata.revision,
+        state_id=metadata.state_id,
+        graph_sha256=anchor.graph_sha256,
+        source_manifest_sha256=anchor.source_manifest_sha256,
+    )

diff --git a/tests/test_cycle_semantics_optional_generation_verification.py b/tests/test_cycle_semantics_optional_generation_verification.py
new file mode 100644
index 0000000..3a9dfc2
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_generation_verification.py
@@ -0,0 +1,249 @@
+"""P1D3F2: independently compare supplied generation declarations."""
+
+from copy import copy
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.optional_generation_anchor import (
+    OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY,
+    OptionalPreparedGenerationAssessment,
+    assess_optional_prepared_generation,
+)
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
+    state, metadata = _persisted(root)
+
+    return (
+        result.cycle_source_preparation_generation_anchor,
+        result.cycle_source_preparation_preview,
+        state,
+        metadata,
+    )
+
+
+def _assess(case):
+    return assess_optional_prepared_generation(*case)
+
+
+def test_real_persisted_generation_matches(tmp_path, isolated_dirs):
+    case = _case(tmp_path)
+    anchor, preview, state, metadata = case
+
+    result = _assess(case)
+
+    assert type(result) is OptionalPreparedGenerationAssessment
+    assert result.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
+    assert result.reason is None
+    assert result.authority == OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY
+    assert result.revision == metadata.revision
+    assert result.state_id == metadata.state_id
+    assert result.graph_sha256 == anchor.graph_sha256
+    assert result.source_manifest_sha256 == (
+        preview.manifest.source_manifest_sha256
+    )
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+    assert result == _assess(case)
+
+
+def test_old_anchor_rejected_after_new_full_even_same_digest(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    first = _optional(root)
+    old_anchor = first.cycle_source_preparation_generation_anchor
+    old_preview = first.cycle_source_preparation_preview
+
+    second = _optional(root)
+    new_anchor = second.cycle_source_preparation_generation_anchor
+    new_preview = second.cycle_source_preparation_preview
+    state, metadata = _persisted(root)
+
+    assert new_anchor.revision > old_anchor.revision
+    assert old_anchor.source_manifest_sha256 == (
+        new_anchor.source_manifest_sha256
+    )
+
+    old = assess_optional_prepared_generation(
+        old_anchor, old_preview, state, metadata,
+    )
+    new = assess_optional_prepared_generation(
+        new_anchor, new_preview, state, metadata,
+    )
+
+    assert old.status == "UNAVAILABLE"
+    assert old.reason == "ANCHOR_METADATA_MISMATCH"
+    assert new.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
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
+def test_forged_anchor_identity_rejected(
+    tmp_path, isolated_dirs, field, value,
+):
+    case = list(_case(tmp_path))
+    case[0] = replace(case[0], **{field: value})
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "ANCHOR_METADATA_MISMATCH"
+
+
+def test_modified_supplied_metadata_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+    case[3] = replace(
+        case[3],
+        revision=case[3].revision + 1,
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "ANCHOR_METADATA_MISMATCH"
+
+
+def test_state_generation_mismatch_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+    changed = copy(case[2])
+    changed.state_id = "different-state"
+    case[2] = changed
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "CANONICAL_GENERATION_IDENTITY_MISMATCH"
+
+
+def test_stale_cycle_semantics_rejected(tmp_path, isolated_dirs):
+    case = list(_case(tmp_path))
+    changed = copy(case[2])
+    changed.cycle_semantics_state = "stale"
+    case[2] = changed
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"
+
+
+def test_resync_required_rejected(tmp_path, isolated_dirs):
+    case = list(_case(tmp_path))
+    changed = copy(case[2])
+    changed.resync_required = True
+    case[2] = changed
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "CANONICAL_CYCLE_EVIDENCE_NOT_FRESH"
+
+
+def test_modified_canonical_graph_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+    changed = copy(case[2])
+    changed_graph = copy(changed.dependency_graph)
+    changed_graph.hard_edges = {
+        name: set(targets)
+        for name, targets in changed_graph.hard_edges.items()
+    }
+    changed_graph.hard_edges["pkg.a"].add("pkg.helper")
+    changed.dependency_graph = changed_graph
+    case[2] = changed
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"
+
+
+def test_changed_canonical_import_facts_rejected(
+    tmp_path, isolated_dirs,
+):
+    case = list(_case(tmp_path))
+    changed = copy(case[2])
+    changed.modules = dict(changed.modules)
+
+    module = changed.modules["pkg.a"]
+
+    changed.modules["pkg.a"] = replace(
+        module,
+        imports=[
+            item
+            for item in module.imports
+            if not item.is_from_import
+        ],
+    )
+    case[2] = changed
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"
+
+
+def test_forged_manifest_rejected(tmp_path, isolated_dirs):
+    case = list(_case(tmp_path))
+    preview = case[1]
+
+    case[1] = replace(
+        preview,
+        manifest=replace(
+            preview.manifest,
+            source_manifest_sha256="0" * 64,
+        ),
+    )
+
+    result = _assess(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "ANCHOR_METADATA_MISMATCH"
+
+
+def test_validation_performs_no_source_reread(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    case = _case(tmp_path)
+
+    def forbidden(self):
+        raise AssertionError("filesystem reread forbidden")
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(Path, "read_bytes", forbidden)
+        scoped.setattr(Path, "read_text", forbidden)
+        result = _assess(case)
+
+    assert result.status == "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
```

## FINAL_VERDICT

TEST_FAILURE
