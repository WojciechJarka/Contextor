# CONTEXTOR P1D3-WARN-3B-R1 — implementer report

## CONTRACT_CONFLICT_RESOLUTION

DIRECT_EVIDENCE: Architect replaced the impossible positive self-loop test. Canonical `build_graph` still rejects `source == target`, while `analyze_import_cycle_topology` retains explicit self-loop support. The new T15A–D tests follow that distinction. Neither producer was modified.

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP inspected installed partial claims and existing v2 eligibility first. `graph.py:82` still discards self-import edges; `scc.py:123` identifies explicit self-loop SCCs. WARN-3A and WARN-1 v2 helper were unchanged. The failed prior attempt left no source/test file in the worktree. Prechange structural cycle count was 16.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Initial and final HEAD `2cddf1a39c3014805d83ae019b4eb061da272f56`. Initial worktree clean. Final worktree contains only the two authorized new Python files and this report. No commit, push, restart or active user's FULL/LIVE operation.

## PURE ELIGIBILITY CONTRACT

CODE_PATH_PROVED: `_verified_installed_partial_model_pass_paths` calls the existing lock-scoped installed partial checker, then validates canonical SCC summaries and every current structural cycle path. It performs no I/O, IPC, store access, state mutation or path-inventory rebuild. The caller owns the LIVE lock.

## INSTALLED GENERATION AUTHORITY

CODE_PATH_PROVED: Exact successful installed binding, revision, state ID, graph SHA, claims SHA, activity epoch and LIVE authority are required. Missing, malformed or foreign verification returns empty. There is no persisted-only or v2 fallback.

## STRUCTURAL PATH VALIDATION

CODE_PATH_PROVED: Every path must be a closed simple directed path with exact nonempty string nodes, edges in current hard_edges, exactly one cyclic SCC and no duplicate record. SCC summaries must be ordered tuples of exact three-key dicts with exact canonical member tuples. Any malformed item makes the whole result empty. The validator has no unconditional self-loop ban: a valid `a-a` form would pass simple-cycle shape and is rejected for genuine FULL input because the graph lacks `a -> a`.

## PASS / INDETERMINATE

CONTRACT_PROVED: Real isolated FULL/store/LIVE PASS/INDETERMINATE retained only the PASS SCC path. A separate unavailable SCC did not erase it.

## PASS / HAZARD

CONTRACT_PROVED: Real PASS/HAZARD retained only the PASS path and excluded HAZARD.

## TWO_PASS

CONTRACT_PROVED: Real TWO_PASS retained both SCC paths. Distinct SCC paths were not cross-classified.

## SELF-LOOP PRODUCER CONTRACT

CODE_PATH_PROVED: `graph.py` routes hard-edge insertion through `_add_edge`, which returns for `source == target`. `scc.py` can classify an explicitly supplied self-loop, but official FULL does not produce one from `a.py: import a`.

## REPLACED T15 RESULTS

CONTRACT_PROVED: R1-T15A actual isolated FULL on `a.py: import a` had no `a -> a` edge, no cyclic SCC, no partial receipt and no invented eligibility. R1-T15B replaced cycles temporarily with `a-a` under a genuine installed TWO_PASS receipt; eligibility was empty because the edge was absent. R1-T15C `a-a-a` was empty because interior nodes repeat. Both test mutations were restored. R1-T15D source inspection confirms no artificial blanket self-loop rule.

## MALFORMED PATH FAIL-CLOSED

CONTRACT_PROVED: Repeated walk, duplicate path, invalid edge, malformed path after valid PASS, absent/stale/malformed path inventory all returned empty for the entire evaluation. Two distinct valid paths in one genuine PASS SCC each qualified.

## FOREIGN / STALE / FORGED RECEIPTS

CONTRACT_PROVED: Foreign revision/service/process/repository/state/root/graph/claims identities, missing receipt, forged classification/digest, stale families and resync all returned empty. Complete v2-only receipt did not grant partial eligibility; WARN-1 v2 behavior stayed positive on its valid fixture.

## STRUCTURAL STATE IMMUTABILITY

CONTRACT_PROVED: Repeated evaluation left hard edges, SCCs, cycles, partial receipt, activity epoch and diagnostic journal unchanged. A newer real committed generation installed through the isolated server's publish path removed prior eligibility.

## DETERMINISM

CONTRACT_PROVED: Two calls under the unchanged installed generation returned the same immutable frozenset.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on both new Python files exited 0. New focused module: 30 passed, 0 failed, 0 skipped, 31.68 s, exit 0. Four required regression modules: 118 passed, 0 failed, 0 skipped, 53.59 s, exit 0. Both new-file `git diff --no-index --check` calls exited 0. No global suite ran.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected both new files at canonical revision 854; `workspace_sync=verified`, live provenance, fresh module/graph/topology/structural cycles and stale cycle_semantics. Structural DFS back-edge count remained 16 (prechange 16). Production helper has only hard dependencies on `live_installed_partial_claims` and `scc`. No new counted structural cycle. This does not prove active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/partial_warning_eligibility.py` (new)
- `tests/test_cycle_semantics_partial_warning_eligibility.py` (new)

`walkthrough.md` is this report. Complete actual diffs follow.

## FULL_DIFFS


### New production module

```diff
diff --git a/contextor/core/cycle_semantics/partial_warning_eligibility.py b/contextor/core/cycle_semantics/partial_warning_eligibility.py
new file mode 100644
index 0000000..49eae39
--- /dev/null
+++ b/contextor/core/cycle_semantics/partial_warning_eligibility.py
@@ -0,0 +1,132 @@
+"""Pure installed partial SCC model-PASS path eligibility.
+
+The caller holds the canonical LIVE owner's state lock throughout this call.
+Eligibility is restricted static-model evidence, not runtime safety.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+
+from .live_installed_partial_claims import (
+    _PARTIAL_LIVE_AUTHORITY,
+    _PARTIAL_LIVE_MATCH,
+    assess_live_installed_partial_claims,
+)
+from .scc import analyze_import_cycle_topology
+
+
+def _verified_installed_partial_model_pass_paths(
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
+) -> frozenset[tuple[str, ...]]:
+    """Select validated structural paths in installed partial PASS SCCs."""
+    empty: frozenset[tuple[str, ...]] = frozenset()
+    try:
+        installed = assess_live_installed_partial_claims(
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
+        if (
+            type(installed) is not dict
+            or installed.get("status") != "ok"
+            or installed.get("binding_state") != _PARTIAL_LIVE_MATCH
+            or installed.get("revision") != expected_revision
+            or installed.get("state_id") != expected_state_id
+            or installed.get("graph_sha256") != expected_graph_sha256
+            or installed.get("claims_sha256") != expected_claims_sha256
+            or installed.get("activity_epoch") != activity_epoch
+            or installed.get("authority") != _PARTIAL_LIVE_AUTHORITY
+        ):
+            return empty
+
+        hard_edges = state.dependency_graph.hard_edges
+        if not isinstance(hard_edges, Mapping):
+            return empty
+        topology = analyze_import_cycle_topology(hard_edges)
+        components = topology.cyclic_components
+        summaries = installed.get("components")
+        if (
+            type(summaries) is not tuple
+            or len(summaries) != len(components)
+            or any(
+                type(summary) is not dict
+                or set(summary) != {
+                    "members", "preparation_state", "model_classification",
+                }
+                or type(summary["members"]) is not tuple
+                or summary["members"] != component.members
+                for summary, component in zip(summaries, components)
+            )
+        ):
+            return empty
+
+        paths = getattr(state, "cycles", None)
+        if not isinstance(paths, (list, tuple)):
+            return empty
+        memberships = tuple(frozenset(item.members) for item in components)
+        eligible = {
+            index
+            for index, summary in enumerate(summaries)
+            if summary["preparation_state"] == "PREPARED_UNPUBLISHED"
+            and summary["model_classification"]
+            == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        }
+        result: set[tuple[str, ...]] = set()
+        seen_paths: set[tuple[str, ...]] = set()
+        for path in paths:
+            if (
+                not isinstance(path, (list, tuple))
+                or len(path) < 2
+                or any(type(node) is not str or not node for node in path)
+                or path[0] != path[-1]
+            ):
+                return empty
+            interior = tuple(path[:-1])
+            if len(interior) != len(set(interior)):
+                return empty
+            path_identity = tuple(path)
+            if path_identity in seen_paths:
+                return empty
+            seen_paths.add(path_identity)
+            if any(
+                target not in hard_edges.get(source, ())
+                for source, target in zip(path, path[1:])
+            ):
+                return empty
+            nodes = frozenset(interior)
+            matching = tuple(
+                index for index, members in enumerate(memberships)
+                if nodes <= members
+            )
+            if len(matching) != 1:
+                return empty
+            if matching[0] in eligible:
+                result.add(path_identity)
+        return frozenset(result)
+    except (
+        AttributeError, KeyError, TypeError, ValueError, IndexError,
+        RecursionError, OverflowError,
+    ):
+        return empty
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_partial_warning_eligibility.py b/tests/test_cycle_semantics_partial_warning_eligibility.py
new file mode 100644
index 0000000..16ea63f
--- /dev/null
+++ b/tests/test_cycle_semantics_partial_warning_eligibility.py
@@ -0,0 +1,288 @@
+"""Installed partial model-PASS paths remain separate from warning projection."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.partial_warning_eligibility import (
+    _verified_installed_partial_model_pass_paths,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _full, _owner, _persisted,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _expected(server, state, metadata):
+    receipt = state.cycle_partial_source_publication
+    return {
+        "canonical_revision": server._revision,
+        "authority_identity": server._authority_identity,
+        "activity_epoch": server._activity_epoch,
+        "expected_revision": metadata.revision,
+        "expected_state_id": metadata.state_id,
+        "expected_repo_id": metadata.repo_id,
+        "expected_root_path": metadata.root_path,
+        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
+        "expected_claims_sha256": receipt.claims_sha256,
+        "expected_service_instance_id": server.endpoint.service_instance_id,
+        "expected_process_start_identity": server.endpoint.process_start_identity,
+    }
+
+
+def _eligible(server, state, metadata, **changes):
+    with server._lock:
+        return _verified_installed_partial_model_pass_paths(
+            state, **{**_expected(server, state, metadata), **changes},
+        )
+
+
+def _paths_for(state, members):
+    return frozenset(
+        tuple(path) for path in state.cycles
+        if frozenset(path[:-1]) <= frozenset(members)
+    )
+
+
+@pytest.mark.parametrize("sources", [PASS_AND_UNKNOWN, PASS_AND_HAZARD, TWO_PASS])
+def test_t01_t02_t03_t17_t24_individual_scc_eligibility(
+    tmp_path, isolated_dirs, sources,
+):
+    _, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, _):
+        result = _eligible(server, state, metadata)
+        assert _paths_for(state, ("a", "b")) <= result
+        if sources is TWO_PASS:
+            assert result == frozenset(tuple(path) for path in state.cycles)
+        else:
+            assert result == _paths_for(state, ("a", "b"))
+            assert _paths_for(state, ("x", "y")).isdisjoint(result)
+        assert type(result) is frozenset
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
+def test_t04_t05_t06_t07_t08_invalid_identity(tmp_path, isolated_dirs, change):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        assert _eligible(server, state, metadata, **change) == frozenset()
+
+
+@pytest.mark.parametrize("mutation", [
+    "missing", "classification", "digest", "semantic", "cycles", "resync",
+])
+def test_t09_t11_t12_invalid_installed_receipt_or_family(
+    tmp_path, isolated_dirs, mutation,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        expected = _expected(server, state, metadata)
+        receipt = state.cycle_partial_source_publication
+        if mutation == "missing":
+            state.cycle_partial_source_publication = None
+        elif mutation == "classification":
+            items = list(receipt.preparation.component_preparations)
+            items[0] = replace(items[0], model_classification="FORGED")
+            state.cycle_partial_source_publication = replace(
+                receipt, preparation=replace(
+                    receipt.preparation, component_preparations=tuple(items),
+                ),
+            )
+        elif mutation == "digest":
+            state.cycle_partial_source_publication = replace(
+                receipt, claims_sha256="0" * 64,
+            )
+        elif mutation == "semantic":
+            state.cycle_semantics_state = "stale"
+        elif mutation == "cycles":
+            state.cycles_state = "stale"
+        else:
+            state.resync_required = True
+        with server._lock:
+            assert _verified_installed_partial_model_pass_paths(
+                state, **expected,
+            ) == frozenset()
+
+
+def test_t10_t23_v2_only_cannot_establish_partial_eligibility(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False, complete=True)
+    with _owner(state, metadata) as (server, _):
+        with server._lock:
+            result = _verified_installed_partial_model_pass_paths(
+                state,
+                canonical_revision=server._revision,
+                authority_identity=server._authority_identity,
+                activity_epoch=server._activity_epoch,
+                expected_revision=metadata.revision,
+                expected_state_id=metadata.state_id,
+                expected_repo_id=metadata.repo_id,
+                expected_root_path=metadata.root_path,
+                expected_graph_sha256=state.cycle_semantics.graph_sha256,
+                expected_claims_sha256="0" * 64,
+                expected_service_instance_id=server.endpoint.service_instance_id,
+                expected_process_start_identity=server.endpoint.process_start_identity,
+            )
+            assert result == frozenset()
+            assert _verified_model_pass_cycle_paths(
+                state, expected_revision=metadata.revision,
+                expected_state_id=metadata.state_id,
+                expected_repo_id=metadata.repo_id,
+                expected_root_path=metadata.root_path,
+            )
+
+
+@pytest.mark.parametrize("path", [
+    ["a", "b", "a", "b", "a"],
+    ["a", "b", "a"],
+    ["a", "missing", "a"],
+])
+def test_t13_t14_t16_malformed_path_fails_entire_result(
+    tmp_path, isolated_dirs, path,
+):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        assert _eligible(server, state, metadata)
+        state.cycles.append(path)
+        assert _eligible(server, state, metadata) == frozenset()
+
+
+def test_r1_t15a_genuine_full_self_import_has_no_cycle_or_receipt(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(
+        tmp_path, {"a": "import a\n"}, partial=True,
+    )
+    assert "a" not in state.dependency_graph.hard_edges.get("a", ())
+    assert state.cycle_semantics.import_sites.topology.cyclic_components == ()
+    assert state.cycle_partial_source_publication is None
+    assert state.cycles == []
+    assert root.exists()
+    with _owner(state, metadata) as (server, _):
+        with server._lock:
+            assert _verified_installed_partial_model_pass_paths(
+                state,
+                canonical_revision=server._revision,
+                authority_identity=server._authority_identity,
+                activity_epoch=server._activity_epoch,
+                expected_revision=metadata.revision,
+                expected_state_id=metadata.state_id,
+                expected_repo_id=metadata.repo_id,
+                expected_root_path=metadata.root_path,
+                expected_graph_sha256=state.cycle_semantics.graph_sha256,
+                expected_claims_sha256="0" * 64,
+                expected_service_instance_id=server.endpoint.service_instance_id,
+                expected_process_start_identity=server.endpoint.process_start_identity,
+            ) == frozenset()
+
+
+@pytest.mark.parametrize("path", [
+    ["a", "a"],
+    ["a", "a", "a"],
+])
+def test_r1_t15b_t15c_self_loop_paths_rejected_without_synthetic_receipt(
+    tmp_path, isolated_dirs, path,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, _):
+        assert _eligible(server, state, metadata)
+        original = state.cycles
+        try:
+            state.cycles = [path]
+            assert _eligible(server, state, metadata) == frozenset()
+        finally:
+            state.cycles = original
+        assert _eligible(server, state, metadata)
+
+
+def test_t18_two_distinct_paths_in_one_genuine_pass_scc(
+    tmp_path, isolated_dirs,
+):
+    sources = {
+        "a": "import b\nimport c\nvalue = 1\n",
+        "b": "import a\nvalue = 2\n",
+        "c": "import a\nvalue = 3\n",
+    }
+    _, state, metadata = _fixture(tmp_path, sources)
+    with _owner(state, metadata) as (server, _):
+        state.cycles = [["a", "b", "a"], ["a", "c", "a"]]
+        assert _eligible(server, state, metadata) == frozenset({
+            ("a", "b", "a"), ("a", "c", "a"),
+        })
+
+
+@pytest.mark.parametrize("mutation", ["absent", "stale", "malformed"])
+def test_t19_missing_stale_or_malformed_paths(tmp_path, isolated_dirs, mutation):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        if mutation == "absent":
+            state.cycles = None
+        elif mutation == "stale":
+            state.cycles_state = "stale"
+        else:
+            state.cycles = ["not a path"]
+        assert _eligible(server, state, metadata) == frozenset()
+
+
+def test_t20_t21_pure_and_deterministic(tmp_path, isolated_dirs):
+    _, state, metadata = _fixture(tmp_path)
+    with _owner(state, metadata) as (server, _):
+        before = copy.deepcopy((
+            state.dependency_graph.hard_edges,
+            state.cycle_semantics.import_sites.topology.cyclic_components,
+            state.cycles,
+            state.cycle_partial_source_publication,
+            server._activity_epoch,
+            server._events,
+        ))
+        first = _eligible(server, state, metadata)
+        assert first
+        assert _eligible(server, state, metadata) == first
+        after = (
+            state.dependency_graph.hard_edges,
+            state.cycle_semantics.import_sites.topology.cyclic_components,
+            state.cycles,
+            state.cycle_partial_source_publication,
+            server._activity_epoch,
+            server._events,
+        )
+        assert after == before
+
+
+def test_t22_new_generation_removes_eligibility(tmp_path, isolated_dirs):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, _):
+        old_expected = _expected(server, state, metadata)
+        assert _eligible(server, state, metadata)
+        _full(root, partial=False)
+        newer, newer_metadata = _persisted(root)
+        assert server._execute_publish({
+            "state": newer, "origin": "isolated_test",
+        })["status"] == "ok"
+        with server._lock:
+            assert _verified_installed_partial_model_pass_paths(
+                server._state, **old_expected,
+            ) == frozenset()
+        assert newer_metadata.revision > metadata.revision
```

## CONTRACT_CONFLICTS

NONE after the architect's T15 replacement.

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE loaded-code adoption, runtime import safety and active warning projection behavior. This stage does not suppress warnings.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: WARN-3B-R1 eligibility and focused regressions pass. Architectural GO remains with ChatGPT. STOP after this stage.

