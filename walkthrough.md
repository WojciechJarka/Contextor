# CONTEXTOR P1D3-WARN-4A — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP inspected existing partial eligibility and diagnostics projection first. Existing eligibility required the LIVE owner state lock, structural paths remained in `state.cycles`, and no active consumer used partial acceptance. No material preflight mismatch. Initial structural DFS back-edge count was 16.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Initial and final HEAD `20d2e18a545ccf8a6e21437ada6052aa496e648c`; initial worktree clean. Final changes are two new authorized Python files and this report. No commit, push, restart or active user's FULL/LIVE operation.

## PROJECTION CONTRACT

CODE_PATH_PROVED: Frozen `InstalledCycleWarningProjection` has the six specified fields. `project_installed_cycle_warnings` is pure and assumes a caller-held LIVE lock. It does not access files, store, IPC or warning consumers, and does not mutate state or journal.

## STRUCTURAL INVENTORY

CODE_PATH_PROVED: Fresh cycles and no resync are required. The function validates the exact list/tuple inventory against current hard edges and canonical cyclic SCC topology: closed simple paths, exact nonempty string nodes, directed edges, unique containing SCC and no duplicate records. It retains original path order and never calls `detect_cycles`. Missing, stale or malformed inventory returns `UNAVAILABLE/STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE` with all three path fields and revision `None`.

## INSTALLED AUTHORITY GATE

CODE_PATH_PROVED: After structural validation, the function calls the existing `_verified_installed_partial_model_pass_paths` with all supplied identity and authority arguments unchanged. It accepts no caller-supplied eligibility set and has no v2 fallback. Empty eligibility from absent or invalid installed proof leaves every valid structural path active.

## PASS / INDETERMINATE

CONTRACT_PROVED: Real isolated FULL/store/LIVE PASS/INDETERMINATE produced two structural paths, one model-PASS path and one active warning path.

## PASS / HAZARD

CONTRACT_PROVED: Real PASS/HAZARD retained only PASS in the model subset; HAZARD remained active.

## TWO_PASS

CONTRACT_PROVED: Real TWO_PASS retained both paths as model-PASS and produced no active cycle warnings in the pure projection.

## ABSENT / FOREIGN / STALE EVIDENCE

CONTRACT_PROVED: Default FULL, preview-only and v2-only generations without partial receipt kept every structural cycle active. Foreign expected revision/service/process/repository/state/root/graph/claims identities, removed/forged/digest-tampered receipts also kept all valid structural paths active. Newer real installed generation without receipt restored warnings. Stale cycle inventory or resync returned UNAVAILABLE with None inventories.

## PARTITION INVARIANTS

CODE_PATH_PROVED: Eligible paths are normalized to canonical structural order; the active tuple contains the complement in that same order. Disjointness, union and length invariants are checked before FRESH. A fresh empty acyclic inventory returns three empty tuples. Two distinct valid simple paths in one PASS SCC remain distinct and ordered.

## STRUCTURAL GRAPH RETENTION

CONTRACT_PROVED: Focused tests confirmed hard edges, SCCs, cycles and receipt unchanged. Repeated calls left the diagnostic journal unchanged. No path was removed from canonical state, and no actual warning consumer was changed.

## DETERMINISM / IMMUTABILITY

CONTRACT_PROVED: Repeated calls on one installed generation produced identical frozen projections and matched the unchanged WARN-3B eligibility set.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on both new Python files exited 0. New focused module: initial 28 passed, then T04 was corrected to run true default FULL; rerun 28 passed, 0 failed, 0 skipped, 28.94 s. Four requested regression modules: 116 passed, 0 failed, 0 skipped, 72.97 s. Both new-file whitespace checks via `git diff --no-index --check` exited 0. No global pytest.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected both new files at canonical revision 857; both had live provenance and `workspace_sync=verified`. Module, graph, topology and structural cycles were fresh; cycle_semantics stale. Structural DFS back-edge count stayed 16. Production imports only existing `partial_warning_eligibility` and `scc`; no newly counted structural cycle. This is source/workspace evidence, not active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/cycle_warning_projection.py` (new)
- `tests/test_cycle_semantics_cycle_warning_projection.py` (new)

`walkthrough.md` is this report. Complete actual diffs follow.

## FULL_DIFFS


### New production module

```diff
diff --git a/contextor/core/cycle_semantics/cycle_warning_projection.py b/contextor/core/cycle_semantics/cycle_warning_projection.py
new file mode 100644
index 0000000..e3ce4ca
--- /dev/null
+++ b/contextor/core/cycle_semantics/cycle_warning_projection.py
@@ -0,0 +1,132 @@
+"""Pure projection of installed model acceptance and structural cycle warnings."""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from .partial_warning_eligibility import (
+    _verified_installed_partial_model_pass_paths,
+)
+from .scc import analyze_import_cycle_topology
+
+
+@dataclass(frozen=True)
+class InstalledCycleWarningProjection:
+    status: str
+    reason: str | None
+    revision: int | None
+    structural_paths: tuple[tuple[str, ...], ...] | None
+    model_pass_paths: tuple[tuple[str, ...], ...] | None
+    active_warning_paths: tuple[tuple[str, ...], ...] | None
+
+
+def project_installed_cycle_warnings(
+    state,
+    *,
+    canonical_revision,
+    authority_identity,
+    activity_epoch,
+    expected_revision,
+    expected_state_id,
+    expected_repo_id,
+    expected_root_path,
+    expected_graph_sha256,
+    expected_claims_sha256,
+    expected_service_instance_id,
+    expected_process_start_identity,
+) -> InstalledCycleWarningProjection:
+    """Partition valid canonical paths under a caller-held LIVE state lock."""
+    unavailable = InstalledCycleWarningProjection(
+        status="UNAVAILABLE",
+        reason="STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE",
+        revision=None,
+        structural_paths=None,
+        model_pass_paths=None,
+        active_warning_paths=None,
+    )
+    try:
+        if (
+            getattr(state, "cycles_state", None) != "fresh"
+            or getattr(state, "resync_required", False) is not False
+        ):
+            return unavailable
+        paths = getattr(state, "cycles", None)
+        if type(paths) not in (list, tuple):
+            return unavailable
+        hard_edges = state.dependency_graph.hard_edges
+        if not isinstance(hard_edges, Mapping):
+            return unavailable
+        components = analyze_import_cycle_topology(
+            hard_edges
+        ).cyclic_components
+        memberships = tuple(frozenset(item.members) for item in components)
+        seen_paths: set[tuple[str, ...]] = set()
+        for path in paths:
+            if (
+                type(path) not in (list, tuple)
+                or len(path) < 2
+                or any(type(node) is not str or not node for node in path)
+                or path[0] != path[-1]
+            ):
+                return unavailable
+            interior = tuple(path[:-1])
+            if len(interior) != len(set(interior)):
+                return unavailable
+            identity = tuple(path)
+            if identity in seen_paths:
+                return unavailable
+            seen_paths.add(identity)
+            if any(
+                target not in hard_edges.get(source, ())
+                for source, target in zip(path, path[1:])
+            ):
+                return unavailable
+            nodes = frozenset(interior)
+            if sum(nodes <= members for members in memberships) != 1:
+                return unavailable
+        structural_paths = tuple(tuple(path) for path in paths)
+
+        eligible = _verified_installed_partial_model_pass_paths(
+            state,
+            canonical_revision=canonical_revision,
+            authority_identity=authority_identity,
+            activity_epoch=activity_epoch,
+            expected_revision=expected_revision,
+            expected_state_id=expected_state_id,
+            expected_repo_id=expected_repo_id,
+            expected_root_path=expected_root_path,
+            expected_graph_sha256=expected_graph_sha256,
+            expected_claims_sha256=expected_claims_sha256,
+            expected_service_instance_id=expected_service_instance_id,
+            expected_process_start_identity=expected_process_start_identity,
+        )
+        if type(eligible) is not frozenset or not eligible <= set(structural_paths):
+            return unavailable
+        model_pass_paths = tuple(
+            path for path in structural_paths if path in eligible
+        )
+        active_warning_paths = tuple(
+            path for path in structural_paths if path not in eligible
+        )
+        if (
+            not set(model_pass_paths).isdisjoint(active_warning_paths)
+            or set(model_pass_paths) | set(active_warning_paths)
+            != set(structural_paths)
+            or len(model_pass_paths) + len(active_warning_paths)
+            != len(structural_paths)
+        ):
+            return unavailable
+        return InstalledCycleWarningProjection(
+            status="FRESH",
+            reason=None,
+            revision=canonical_revision,
+            structural_paths=structural_paths,
+            model_pass_paths=model_pass_paths,
+            active_warning_paths=active_warning_paths,
+        )
+    except (
+        AttributeError, KeyError, TypeError, ValueError, IndexError,
+        RecursionError, OverflowError,
+    ):
+        return unavailable
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_cycle_warning_projection.py b/tests/test_cycle_semantics_cycle_warning_projection.py
new file mode 100644
index 0000000..cc0ed47
--- /dev/null
+++ b/tests/test_cycle_semantics_cycle_warning_projection.py
@@ -0,0 +1,316 @@
+"""Pure installed cycle warning projection over genuine isolated generations."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.cycle_warning_projection import (
+    InstalledCycleWarningProjection,
+    project_installed_cycle_warnings,
+)
+from contextor.core.cycle_semantics.partial_warning_eligibility import (
+    _verified_installed_partial_model_pass_paths,
+)
+from contextor.core.api.facade import ContextorFacade
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _full, _owner, _persisted,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _arguments(server, state, metadata, **changes):
+    receipt = state.cycle_partial_source_publication
+    values = {
+        "canonical_revision": server._revision,
+        "authority_identity": server._authority_identity,
+        "activity_epoch": server._activity_epoch,
+        "expected_revision": metadata.revision,
+        "expected_state_id": metadata.state_id,
+        "expected_repo_id": metadata.repo_id,
+        "expected_root_path": metadata.root_path,
+        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
+        "expected_claims_sha256": (
+            receipt.claims_sha256 if receipt is not None else "0" * 64
+        ),
+        "expected_service_instance_id": server.endpoint.service_instance_id,
+        "expected_process_start_identity": server.endpoint.process_start_identity,
+    }
+    return {**values, **changes}
+
+
+def _project(server, state, metadata, **changes):
+    with server._lock:
+        return project_installed_cycle_warnings(
+            state, **_arguments(server, state, metadata, **changes),
+        )
+
+
+def _paths(state):
+    return tuple(tuple(path) for path in state.cycles)
+
+
+def _assert_partition(result):
+    assert type(result) is InstalledCycleWarningProjection
+    assert result.status == "FRESH"
+    structural = result.structural_paths
+    accepted = result.model_pass_paths
+    active = result.active_warning_paths
+    assert set(accepted).isdisjoint(active)
+    assert set(accepted) | set(active) == set(structural)
+    assert len(accepted) + len(active) == len(structural)
+
+
+@pytest.mark.parametrize("sources,expected_accepted", [
+    (PASS_AND_UNKNOWN, 1),
+    (PASS_AND_HAZARD, 1),
+    (TWO_PASS, 2),
+])
+def test_t01_t02_t03_t19_t21_real_scc_partition(
+    tmp_path, isolated_dirs, sources, expected_accepted,
+):
+    _, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, _):
+        result = _project(server, state, metadata)
+        _assert_partition(result)
+        assert result.structural_paths == _paths(state)
+        assert len(result.structural_paths) == 2
+        assert len(result.model_pass_paths) == expected_accepted
+        assert len(result.active_warning_paths) == 2 - expected_accepted
+        assert result.model_pass_paths[0] == tuple(state.cycles[0])
+        if expected_accepted == 1:
+            assert result.active_warning_paths == (tuple(state.cycles[1]),)
+
+
+@pytest.mark.parametrize("mode", ["default", "preview", "v2"])
+def test_t04_t05_t06_absent_partial_receipt_keeps_all_warnings(
+    tmp_path, isolated_dirs, mode,
+):
+    if mode == "default":
+        root = _repo(tmp_path, TWO_PASS)
+        errors, result = ContextorFacade.analyze_project(str(root))
+        assert isinstance(errors, list)
+        assert result is not None
+        assert not hasattr(result, "cycle_source_preparation_preview")
+        state, metadata = _persisted(root)
+    elif mode == "v2":
+        root, state, metadata = _fixture(
+            tmp_path, TWO_PASS, partial=False, complete=True,
+        )
+    else:
+        root, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False)
+        assert state.cycle_source_publication is None
+    assert root.exists()
+    assert state.cycle_partial_source_publication is None
+    with _owner(state, metadata) as (server, _):
+        result = _project(server, state, metadata)
+        _assert_partition(result)
+        assert result.structural_paths == _paths(state)
+        assert result.model_pass_paths == ()
+        assert result.active_warning_paths == _paths(state)
+
+
+@pytest.mark.parametrize("change", [
+    {"expected_revision": 99},
+    {"expected_service_instance_id": "foreign"},
+    {"expected_process_start_identity": "foreign"},
+    {"expected_repo_id": "foreign"},
+    {"expected_state_id": "foreign"},
+    {"expected_root_path": "foreign"},
+    {"expected_graph_sha256": "0" * 64},
+    {"expected_claims_sha256": "0" * 64},
+])
+def test_t07_t08_t09_t10_foreign_expected_generation_keeps_warnings(
+    tmp_path, isolated_dirs, change,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        result = _project(server, state, metadata, **change)
+        _assert_partition(result)
+        assert result.model_pass_paths == ()
+        assert result.active_warning_paths == _paths(state)
+        assert state.cycle_partial_source_publication is not None
+
+
+@pytest.mark.parametrize("mutation", ["missing", "classification", "digest"])
+def test_t11_t22_invalid_partial_receipt_keeps_all_warnings(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        original = state.cycle_partial_source_publication
+        if mutation == "missing":
+            state.cycle_partial_source_publication = None
+        elif mutation == "digest":
+            state.cycle_partial_source_publication = replace(
+                original, claims_sha256="0" * 64,
+            )
+        else:
+            items = list(original.preparation.component_preparations)
+            items[0] = replace(items[0], model_classification="FORGED")
+            state.cycle_partial_source_publication = replace(
+                original,
+                preparation=replace(
+                    original.preparation, component_preparations=tuple(items),
+                ),
+            )
+        try:
+            result = _project(server, state, metadata)
+            _assert_partition(result)
+            assert result.model_pass_paths == ()
+            assert result.active_warning_paths == _paths(state)
+        finally:
+            state.cycle_partial_source_publication = original
+
+
+def test_t12_newer_generation_without_receipt_restores_warnings(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, _):
+        before = _project(server, state, metadata)
+        assert before.active_warning_paths == ()
+        _full(root, partial=False)
+        newer, newer_metadata = _persisted(root)
+        assert server._execute_publish({
+            "state": newer, "origin": "isolated_test",
+        })["status"] == "ok"
+        after = _project(server, newer, newer_metadata)
+        _assert_partition(after)
+        assert after.structural_paths == before.structural_paths
+        assert after.model_pass_paths == ()
+        assert after.active_warning_paths == before.structural_paths
+
+
+@pytest.mark.parametrize("mutation", ["stale", "resync"])
+def test_t13_t14_unavailable_inventory_is_not_zero(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        if mutation == "stale":
+            state.cycles_state = "stale"
+        else:
+            state.resync_required = True
+        result = _project(server, state, metadata)
+        assert result == InstalledCycleWarningProjection(
+            status="UNAVAILABLE",
+            reason="STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE",
+            revision=None,
+            structural_paths=None,
+            model_pass_paths=None,
+            active_warning_paths=None,
+        )
+
+
+@pytest.mark.parametrize("malformed", [
+    ["a", "b", "a", "b", "a"],
+    ["a", "b", "a"],
+    ["a", "missing", "a"],
+    ["a", "a"],
+])
+def test_t15_any_invalid_path_makes_inventory_unavailable(
+    tmp_path, isolated_dirs, malformed,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        original = state.cycles
+        try:
+            state.cycles = [*original, malformed]
+            result = _project(server, state, metadata)
+            assert result.status == "UNAVAILABLE"
+            assert result.structural_paths is None
+            assert result.model_pass_paths is None
+            assert result.active_warning_paths is None
+        finally:
+            state.cycles = original
+
+
+def test_t16_empty_fresh_acyclic_inventory_is_available(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(
+        tmp_path, {"a": "value = 1\n"}, partial=True,
+    )
+    with _owner(state, metadata) as (server, _):
+        result = _project(server, state, metadata)
+        _assert_partition(result)
+        assert result.structural_paths == ()
+        assert result.model_pass_paths == ()
+        assert result.active_warning_paths == ()
+
+
+def test_t17_t18_t23_repeated_projection_is_pure_and_agrees_with_eligibility(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        before = copy.deepcopy((
+            state.dependency_graph.hard_edges,
+            state.cycle_semantics.import_sites.topology.cyclic_components,
+            state.cycles,
+            state.cycle_partial_source_publication,
+            server._events,
+        ))
+        first = _project(server, state, metadata)
+        second = _project(server, state, metadata)
+        assert first == second
+        with server._lock:
+            eligible = _verified_installed_partial_model_pass_paths(
+                state, **_arguments(server, state, metadata),
+            )
+        assert frozenset(first.model_pass_paths) == eligible
+        assert (
+            state.dependency_graph.hard_edges,
+            state.cycle_semantics.import_sites.topology.cyclic_components,
+            state.cycles,
+            state.cycle_partial_source_publication,
+            server._events,
+        ) == before
+
+
+def test_t20_two_distinct_simple_paths_remain_in_canonical_order(
+    tmp_path, isolated_dirs,
+):
+    sources = {
+        "a": "import b\nimport c\nvalue = 1\n",
+        "b": "import a\nvalue = 2\n",
+        "c": "import a\nvalue = 3\n",
+    }
+    _, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, _):
+        original = state.cycles
+        try:
+            state.cycles = [["a", "c", "a"], ["a", "b", "a"]]
+            result = _project(server, state, metadata)
+            _assert_partition(result)
+            assert result.structural_paths == (
+                ("a", "c", "a"), ("a", "b", "a"),
+            )
+            assert result.model_pass_paths == result.structural_paths
+            assert result.active_warning_paths == ()
+        finally:
+            state.cycles = original
+
+
+def test_t24_projection_does_not_call_cycle_builder_or_warning_consumer(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    _, state, metadata = _fixture(tmp_path)
+    import contextor.core.validator.cycles as cycle_validator
+    import contextor.core.diagnostics_projection as diagnostics
+    def forbidden(*args, **kwargs):
+        raise AssertionError("unrelated cycle or warning consumer invoked")
+    monkeypatch.setattr(cycle_validator, "detect_cycles", forbidden, raising=False)
+    monkeypatch.setattr(diagnostics, "diagnostics_summary_for_completed_job", forbidden, raising=False)
+    with _owner(state, metadata) as (server, _):
+        assert _project(server, state, metadata).status == "FRESH"
```

## CONTRACT_CONFLICTS

NONE observed.

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE loaded-code adoption and active Desktop/MCP/get_live_events warning behavior. No consumer integration occurs in this stage.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: Pure WARN-4A projection and focused regressions pass. Architectural GO remains with ChatGPT. STOP after this stage.

