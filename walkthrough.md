# CONTEXTOR P1D3-WARN-2B-1 — independent SCC preparation declaration validation

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP used first for original-worker preparation ownership and consumers, then current local source read for `original_worker_preparation.py`, `generation_manifest.py`, `publication_binding.py`, `model_source_closure.py`, `scc.py`, `contracts.py`, `source_proof.py`, and WARN-2A-R1 tests. Current `OriginalWorkerManifestPreparation` has `component_preparations`; `PreparedSCCSourceBinding` and manifest v2 remain unchanged. No PREFLIGHT_MISMATCH. Existing helper functions create real indexer worker capture and source-bound preparation in isolated tmp_path repositories.

## HEAD / WORKTREE

DIRECT_EVIDENCE: initial HEAD `de2eea0ef4099911744b1c99e17485471498c0f2`; initial worktree clean. Final HEAD unchanged; final worktree contains only two new authorized Python files and the permitted `walkthrough.md` report. No existing source or test file was edited.

## VALIDATOR CONTRACT

CODE_PATH_PROVED: new `partial_scc_claims.py` defines exactly version `cycle-partial-scc-preparation/1`, authority `DECLARED_PREPARATIONS_NOT_COMMITTED_NOT_SOURCE_CERTIFIED`, frozen `PreparedPartialSCCClaims(graph_sha256, components, version, authority)`, and `validate_partial_scc_claims(hard_edges,snapshot,preparation)`. The function performs no filesystem/network/IPC, parsing, analyzed-module execution, mutation, store operation, receipt sealing or warning action. Return value means only that supplied declarations are internally coherent; caller and byte origin are not authenticated.

## GLOBAL GRAPH AND SCC IDENTITY

CODE_PATH_PROVED: exact snapshot/preparation types, complete non-atomic snapshot coverage and empty source issues are required. Existing `fingerprint_hard_edges`, `analyze_import_cycle_topology` and `compute_cycle_model_source_closures` check valid graph shape, exact graph SHA, nonempty cyclic topology, snapshot import-site topology, sorted cyclic member union and observed cyclic-fingerprint domain. Exact ordered tuple of exact `PreparedSCCSourceBinding` components must match topology. Any envelope failure returns None. T04–T07 cover capture, graph and sequence failures.

## COMPLETE PREPARATION

CONTRACT_PROVED: for status PREPARED_UNPUBLISHED_NON_ATOMIC, validator requires reason=None, exact v2 `PreparedCycleSourceManifest`, equality to component tuple, prepared-only authority, graph hash equality, lowercase SHA-256 global digest and all components PREPARED_UNPUBLISHED. Real PASS/HAZARD and two-PASS fixtures return a declaration object (T02/T03). This does not revalidate source bytes.

## PARTIAL PREPARATION

CONTRACT_PROVED: for status UNAVAILABLE, only P1C0_SOURCE_EVIDENCE_UNAVAILABLE with manifest=None, source_modules=(), and at least one UNAVAILABLE SCC is accepted. T01/T15 show a genuine PASS SCC remains in the tuple with an unrelated unsupported decorator SCC, without promoting the global manifest. T08 rejects forged status/reason.

## PER-SCC SOURCE DECLARATIONS

CODE_PATH_PROVED: each prepared SCC must have no reason, allowed PASS or HAZARD classification, supported FLAT_MODULE/REGULAR_PACKAGE kind, lowercase SHA-256 model-evidence digest and exact ordered source signatures for the computed evidence-source closure. Signature rows must be exact triples with valid raw/AST SHA-256; cyclic raw hashes must match snapshot observed fingerprints. An unavailable SCC must be INDETERMINATE with nonempty reason, no signatures and no model digest. T09–T11/T13–T14 cover malformed declarations; no missing signature is synthesized.

## SHARED SOURCE CONSISTENCY

CONTRACT_PROVED: all prepared SCCs sharing a closure source must declare identical raw and AST hashes. T12 uses real two-SCC preparation with shared.py in both closures, then changes one supplied declaration and observes None. An unavailable SCC contributes no positive signature and does not erase an unrelated coherent prepared component.

## FAIL-CLOSED NEGATIVE RESULTS

DIRECT_EVIDENCE: new module passed tests for missing capture; graph hash/internal-edge mismatch; reordered/missing/duplicated SCC components; forged partial status/reason; missing/duplicated/reordered closure signatures; cyclic fingerprint mismatch; conflicting shared signatures; unsupported classification/state; malformed model digest. All return None. This is declared-data checking, not independent P0/P1B source-byte proof.

## DETERMINISM / IMMUTABILITY

CONTRACT_PROVED: T16 deep-compares input graph, snapshot and preparation after validation. T17 repeats identical calls and compares results. T18 demonstrates the output cannot be passed as an existing v2 manifest to store sealing and cannot provide WARN-1 eligibility. No new receipt digest or authority is computed.

## FOCUSED TEST RESULTS

- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/partial_scc_claims.py tests/test_cycle_semantics_partial_scc_claims.py`: exit 0, no output.
- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_partial_scc_claims.py`: exit 0; 23 passed, 0 failed, 0 skipped in 4.78s.
- DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_original_worker_partial_scc_preparation.py tests/test_cycle_semantics_warning_eligibility.py tests/test_cycle_semantics_publication_binding.py tests/test_cycle_semantics_scc.py`: exit 0; 82 passed, 0 failed, 0 skipped in 13.80s.
- DIRECT_EVIDENCE: `git diff --no-index --check -- /dev/null <new-file>` on each new file reported no whitespace errors. Exit code 1 is Git's expected new-file difference status; only LF-to-CRLF notices were printed. No global suite, active FULL/LIVE, restart, commit or push.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` indexed the production module and test module at revisions 826–827. First production read was workspace_sync=unverified; a second at revision 827 reported verified. Test file reported verified at revision 827. Both had fresh syntax/module/graph/topology and stale cycle_semantics. Production imports existing SCC, contracts, generation_manifest, model_source_closure and original_worker_preparation; its sole indexed consumer is the new test module. This is canonical source synchronization, not loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/partial_scc_claims.py` — new.
- `tests/test_cycle_semantics_partial_scc_claims.py` — new.
- `walkthrough.md` — report only; excluded from source/test diff accounting.

## FULL_DIFFS

Complete actual new-file Git diffs for both Python files follow. No lines omitted.

### Production new-file diff

```diff
diff --git a/contextor/core/cycle_semantics/partial_scc_claims.py b/contextor/core/cycle_semantics/partial_scc_claims.py
new file mode 100644
index 0000000..09822d7
--- /dev/null
+++ b/contextor/core/cycle_semantics/partial_scc_claims.py
@@ -0,0 +1,176 @@
+"""Pure validation of declared, uncommitted per-SCC preparations.
+
+This does not authenticate source bytes, publication, or runtime safety.
+"""
+
+from __future__ import annotations
+
+import re
+from dataclasses import dataclass
+
+from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
+from .generation_manifest import (
+    MANIFEST_VERSION,
+    PreparedCycleSourceManifest,
+    PreparedSCCSourceBinding,
+)
+from .model_source_closure import compute_cycle_model_source_closures
+from .original_worker_preparation import OriginalWorkerManifestPreparation
+from .scc import analyze_import_cycle_topology
+
+
+PARTIAL_SCC_CLAIMS_VERSION = "cycle-partial-scc-preparation/1"
+PARTIAL_SCC_CLAIMS_AUTHORITY = (
+    "DECLARED_PREPARATIONS_NOT_COMMITTED_NOT_SOURCE_CERTIFIED"
+)
+_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
+
+
+@dataclass(frozen=True)
+class PreparedPartialSCCClaims:
+    graph_sha256: str
+    components: tuple[PreparedSCCSourceBinding, ...]
+    version: str = PARTIAL_SCC_CLAIMS_VERSION
+    authority: str = PARTIAL_SCC_CLAIMS_AUTHORITY
+
+
+def validate_partial_scc_claims(
+    hard_edges,
+    snapshot,
+    preparation,
+) -> PreparedPartialSCCClaims | None:
+    """Check supplied graph, snapshot and preparation declarations only."""
+    if (
+        type(snapshot) is not CycleSemanticsSnapshot
+        or type(preparation) is not OriginalWorkerManifestPreparation
+        or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or snapshot.source_issues
+    ):
+        return None
+
+    try:
+        graph_sha256 = fingerprint_hard_edges(hard_edges)
+        topology = analyze_import_cycle_topology(hard_edges)
+        closures = compute_cycle_model_source_closures(hard_edges)
+        components = topology.cyclic_components
+        cyclic_members = tuple(sorted(
+            member for component in components for member in component.members
+        ))
+        observed_rows = snapshot.observed_source_fingerprints
+        if (
+            not components
+            or graph_sha256 != snapshot.graph_sha256
+            or snapshot.import_sites.topology != topology
+            or snapshot.cyclic_modules != cyclic_members
+            or type(observed_rows) is not tuple
+            or any(
+                type(row) is not tuple or len(row) != 2
+                or type(row[0]) is not str or not row[0]
+                or type(row[1]) is not str
+                or _SHA256_PATTERN.fullmatch(row[1]) is None
+                for row in observed_rows
+            )
+        ):
+            return None
+        observed = dict(observed_rows)
+        if (
+            len(observed_rows) != len(cyclic_members)
+            or tuple(sorted(observed)) != cyclic_members
+        ):
+            return None
+
+        declarations = preparation.component_preparations
+        if (
+            type(declarations) is not tuple
+            or len(declarations) != len(components)
+            or any(type(item) is not PreparedSCCSourceBinding for item in declarations)
+            or tuple(item.members for item in declarations)
+            != tuple(component.members for component in components)
+        ):
+            return None
+
+        if preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC":
+            manifest = preparation.manifest
+            if (
+                preparation.reason is not None
+                or type(manifest) is not PreparedCycleSourceManifest
+                or manifest.components != declarations
+                or manifest.version != MANIFEST_VERSION
+                or manifest.authority
+                != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+                or manifest.graph_sha256 != snapshot.graph_sha256
+                or type(manifest.source_manifest_sha256) is not str
+                or _SHA256_PATTERN.fullmatch(manifest.source_manifest_sha256) is None
+                or any(item.preparation_state != "PREPARED_UNPUBLISHED"
+                       for item in declarations)
+            ):
+                return None
+        elif preparation.status == "UNAVAILABLE":
+            if (
+                preparation.reason != "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+                or preparation.manifest is not None
+                or preparation.source_modules != ()
+                or not any(item.preparation_state == "UNAVAILABLE"
+                           for item in declarations)
+            ):
+                return None
+        else:
+            return None
+
+        shared_signatures: dict[str, tuple[str, str]] = {}
+        for structural, closure, item in zip(components, closures, declarations):
+            if item.members != structural.members or closure.members != structural.members:
+                return None
+            if item.preparation_state == "PREPARED_UNPUBLISHED":
+                if (
+                    item.reason is not None
+                    or item.model_classification not in {
+                        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+                    }
+                    or item.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
+                    or type(item.model_evidence_sha256) is not str
+                    or _SHA256_PATTERN.fullmatch(item.model_evidence_sha256) is None
+                    or type(item.source_signatures) is not tuple
+                ):
+                    return None
+                rows = item.source_signatures
+                if any(
+                    type(row) is not tuple or len(row) != 3
+                    or type(row[0]) is not str or not row[0]
+                    or type(row[1]) is not str
+                    or _SHA256_PATTERN.fullmatch(row[1]) is None
+                    or type(row[2]) is not str
+                    or _SHA256_PATTERN.fullmatch(row[2]) is None
+                    for row in rows
+                ):
+                    return None
+                if tuple(row[0] for row in rows) != closure.evidence_source_modules:
+                    return None
+                for module_id, raw_sha256, ast_sha256 in rows:
+                    if module_id in observed and observed[module_id] != raw_sha256:
+                        return None
+                    signature = (raw_sha256, ast_sha256)
+                    if (
+                        module_id in shared_signatures
+                        and shared_signatures[module_id] != signature
+                    ):
+                        return None
+                    shared_signatures[module_id] = signature
+            elif item.preparation_state == "UNAVAILABLE":
+                if (
+                    item.model_classification != "INDETERMINATE"
+                    or type(item.reason) is not str or not item.reason
+                    or item.source_signatures != ()
+                    or item.model_evidence_sha256 is not None
+                ):
+                    return None
+            else:
+                return None
+
+        return PreparedPartialSCCClaims(
+            graph_sha256=snapshot.graph_sha256,
+            components=declarations,
+        )
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
+        return None
```

### Test new-file diff

```diff
diff --git a/tests/test_cycle_semantics_partial_scc_claims.py b/tests/test_cycle_semantics_partial_scc_claims.py
new file mode 100644
index 0000000..c13289f
--- /dev/null
+++ b/tests/test_cycle_semantics_partial_scc_claims.py
@@ -0,0 +1,257 @@
+"""Prepared partial SCC declarations have no publication authority."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.partial_scc_claims import (
+    PARTIAL_SCC_CLAIMS_AUTHORITY,
+    PARTIAL_SCC_CLAIMS_VERSION,
+    PreparedPartialSCCClaims,
+    validate_partial_scc_claims,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.live_state.store import save_snapshot
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD,
+    PASS_AND_UNKNOWN,
+    TWO_PASS,
+    _prepare,
+    _real_pipeline,
+    _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _case(tmp_path, sources=PASS_AND_UNKNOWN, selected=None):
+    root = _repo(tmp_path, sources)
+    if selected is None:
+        index, graph, snapshot = _real_pipeline(root)
+    else:
+        index, graph, snapshot = _real_pipeline(root, selected=selected)
+    preparation = _prepare(index, graph, snapshot)
+    return graph.hard_edges, snapshot, preparation
+
+
+def _validated(edges, snapshot, preparation):
+    return validate_partial_scc_claims(edges, snapshot, preparation)
+
+
+def _replace_component(preparation, position, **changes):
+    items = list(preparation.component_preparations)
+    items[position] = replace(items[position], **changes)
+    return replace(preparation, component_preparations=tuple(items))
+
+
+def test_t01_real_pass_indeterminate_preserves_both_claims(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    result = _validated(edges, snapshot, preparation)
+    assert type(result) is PreparedPartialSCCClaims
+    assert result.graph_sha256 == snapshot.graph_sha256
+    assert result.components == preparation.component_preparations
+    assert result.version == PARTIAL_SCC_CLAIMS_VERSION
+    assert result.authority == PARTIAL_SCC_CLAIMS_AUTHORITY
+    assert tuple(item.preparation_state for item in result.components) == (
+        "PREPARED_UNPUBLISHED", "UNAVAILABLE",
+    )
+
+
+def test_t02_real_pass_hazard_keeps_distinct_complete_claims(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path, PASS_AND_HAZARD)
+    result = _validated(edges, snapshot, preparation)
+    assert type(result) is PreparedPartialSCCClaims
+    assert tuple(item.model_classification for item in result.components) == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    )
+
+
+def test_t03_real_two_pass_keeps_canonical_order(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path, TWO_PASS)
+    result = _validated(edges, snapshot, preparation)
+    assert type(result) is PreparedPartialSCCClaims
+    assert tuple(item.members for item in result.components) == (
+        ("a", "b"), ("x", "y"),
+    )
+
+
+def test_t04_missing_original_capture_cannot_infer_claim(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, TWO_PASS)
+    index, graph, snapshot = _real_pipeline(root, selected=frozenset())
+    preparation = _prepare(index, graph, snapshot)
+    assert preparation.component_preparations == ()
+    assert _validated(graph.hard_edges, snapshot, preparation) is None
+
+
+def test_t05_graph_sha_mismatch_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    assert _validated(edges, replace(snapshot, graph_sha256="0" * 64), preparation) is None
+
+
+def test_t06_changed_internal_hard_edge_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    changed = {name: set(targets) for name, targets in edges.items()}
+    changed["a"].add("a")
+    assert _validated(changed, snapshot, preparation) is None
+
+
+@pytest.mark.parametrize("mutation", ["reordered", "missing", "duplicated"])
+def test_t07_invalid_scc_component_sequence_rejected(
+    tmp_path, isolated_dirs, mutation,
+):
+    edges, snapshot, preparation = _case(tmp_path)
+    items = preparation.component_preparations
+    changed = {
+        "reordered": tuple(reversed(items)),
+        "missing": items[:1],
+        "duplicated": (items[0], items[0]),
+    }[mutation]
+    assert _validated(edges, snapshot, replace(
+        preparation, component_preparations=changed,
+    )) is None
+
+
+@pytest.mark.parametrize("status,reason", [
+    ("PREPARED_UNPUBLISHED_NON_ATOMIC", None),
+    ("UNAVAILABLE", "OTHER"),
+])
+def test_t08_incomplete_forged_status_or_reason_rejected(
+    tmp_path, isolated_dirs, status, reason,
+):
+    edges, snapshot, preparation = _case(tmp_path)
+    assert _validated(edges, snapshot, replace(
+        preparation, status=status, reason=reason,
+    )) is None
+
+
+def test_t09_missing_prepared_closure_signature_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    rows = preparation.component_preparations[0].source_signatures
+    changed = _replace_component(preparation, 0, source_signatures=rows[:-1])
+    assert _validated(edges, snapshot, changed) is None
+
+
+@pytest.mark.parametrize("mutation", ["duplicate", "reorder"])
+def test_t10_duplicate_or_reordered_source_rows_rejected(
+    tmp_path, isolated_dirs, mutation,
+):
+    edges, snapshot, preparation = _case(tmp_path)
+    rows = preparation.component_preparations[0].source_signatures
+    changed_rows = rows + rows[:1] if mutation == "duplicate" else tuple(reversed(rows))
+    changed = _replace_component(preparation, 0, source_signatures=changed_rows)
+    assert _validated(edges, snapshot, changed) is None
+
+
+def test_t11_cyclic_source_fingerprint_mismatch_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    rows = list(preparation.component_preparations[0].source_signatures)
+    rows[0] = (rows[0][0], "0" * 64, rows[0][2])
+    changed = _replace_component(preparation, 0, source_signatures=tuple(rows))
+    assert _validated(edges, snapshot, changed) is None
+
+
+def test_t12_conflicting_shared_source_signatures_rejected(tmp_path, isolated_dirs):
+    sources = {
+        "a": "import b\nimport shared\n",
+        "b": "import a\n",
+        "x": "import y\nimport shared\n",
+        "y": "import x\n",
+        "shared": "value = 1\n",
+    }
+    root = _repo(tmp_path, sources)
+    index, graph, snapshot = _real_pipeline(
+        root, selected=frozenset(sources),
+    )
+    preparation = _prepare(index, graph, snapshot)
+    assert preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert _validated(graph.hard_edges, snapshot, preparation) is not None
+    rows = list(preparation.component_preparations[1].source_signatures)
+    shared_position = next(i for i, row in enumerate(rows) if row[0] == "shared")
+    rows[shared_position] = ("shared", "0" * 64, rows[shared_position][2])
+    changed = _replace_component(preparation, 1, source_signatures=tuple(rows))
+    assert _validated(graph.hard_edges, snapshot, changed) is None
+
+
+@pytest.mark.parametrize("change", [
+    {"model_classification": "UNKNOWN"},
+    {"preparation_state": "OTHER"},
+])
+def test_t13_unsupported_model_or_state_rejected(tmp_path, isolated_dirs, change):
+    edges, snapshot, preparation = _case(tmp_path)
+    assert _validated(edges, snapshot, _replace_component(
+        preparation, 0, **change,
+    )) is None
+
+
+def test_t14_malformed_model_evidence_hash_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    changed = _replace_component(
+        preparation, 0, model_evidence_sha256="NOT_SHA256",
+    )
+    assert _validated(edges, snapshot, changed) is None
+
+
+def test_t15_unavailable_scc_does_not_erase_prepared_scc(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    result = _validated(edges, snapshot, preparation)
+    assert result is not None
+    assert result.components[0].preparation_state == "PREPARED_UNPUBLISHED"
+    assert result.components[1].preparation_state == "UNAVAILABLE"
+
+
+def test_t16_inputs_and_signatures_are_unchanged(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    before = copy.deepcopy((edges, snapshot, preparation))
+    assert _validated(edges, snapshot, preparation) is not None
+    assert (edges, snapshot, preparation) == before
+
+
+def test_t17_repeated_calls_are_deterministic(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    assert _validated(edges, snapshot, preparation) == _validated(
+        edges, snapshot, preparation,
+    )
+
+
+def test_t18_prepared_claims_are_not_manifest_or_receipt(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    claims = _validated(edges, snapshot, preparation)
+    assert type(claims) is PreparedPartialSCCClaims
+    state = RepositoryAnalysisState(
+        dependency_graph=ProjectGraph(
+            hard_edges={name: set(targets) for name, targets in edges.items()},
+            soft_edges={},
+        ),
+        cycles=[["a", "b", "a"], ["x", "y", "x"]],
+        cycles_state="fresh",
+        cycle_semantics=snapshot,
+        cycle_semantics_state="fresh",
+    )
+    with pytest.raises((TypeError, ValueError)):
+        save_snapshot(
+            state, tmp_path, "partial-claims", exact_revision=1,
+            file_state_payload={
+                "_meta": {"state_id": "partial-claims", "revision": 1},
+                "files": {},
+            },
+            prepared_cycle_manifest=claims,
+        )
+    assert state.cycle_source_publication is None
+    assert _verified_model_pass_cycle_paths(
+        state,
+        expected_revision=1,
+        expected_state_id="partial-claims",
+        expected_repo_id="repo",
+        expected_root_path="root",
+    ) == frozenset()
```

## CONTRACT_CONFLICTS

NONE observed. The exact pre-publication declaration boundary fit current source. No manifest v2, receipt v2, store, facade, warning or public schema changed.

## REMAINING UNKNOWN

Active loaded-code adoption, installed LIVE generation and future committed partial-SCC authority were not probed or implemented. A forged but internally coherent declaration may pass by contract; origin/provenance remains for later authority stages.

## FINAL IMPLEMENTER OBSERVATION

CODE_PATH_PROVED: valid independent prepared SCC declarations can coexist with an unavailable SCC in a pure result, while invalid global identity rejects the whole envelope. The result has no authority to suppress warnings. Architectural GO remains with ChatGPT.


