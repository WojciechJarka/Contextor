# CONTEXTOR P1D3-WARN-4B-R1 — implementer report

## CONTRACT_CONFLICT_RESOLUTION

DIRECT_EVIDENCE: Architect corrected the one invalid negative test input. The earlier `replace(valid, model_pass_paths=())` produced an unchanged valid projection; the supplied replacement `replace(valid, model_pass_paths=None)` is malformed. The corrected literal module now passes.

## EXACT ONE-LINE CORRECTION

CODE_PATH_PROVED: In `test_wrong_types_and_containers_are_rejected`, the only change to the previously supplied test block was `replace(valid, model_pass_paths=None),`. The production block was restored unchanged.

## IMPLEMENTATION_RESULT

DIRECT_EVIDENCE: Both architect-authored files were restored from the original pasted specification through `apply_patch`, with the single specified test-line replacement. No refactor or additional implementation was introduced.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on both new Python files exited 0. Full new WARN-4B module: 25 passed, 0 failed, 0 skipped, 30.11 s, exit 0. Three requested regression modules: 87 passed, 0 failed, 0 skipped, 88.44 s, exit 0. New-file `git diff --no-index --check` calls exited 0. No global suite ran.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` inspected both new files at canonical revision 861. Both returned live provenance, `workspace_sync=verified`, fresh module/graph/topology/structural-cycle families and stale cycle_semantics. Structural DFS back-edge count remained 16 (prechange 16). Production imports only the existing `cycle_warning_projection` module, with one hard dependency; no newly counted structural cycle. This does not prove active loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/cycle_warning_transitions.py` (new)
- `tests/test_cycle_semantics_cycle_warning_transitions.py` (new)

`walkthrough.md` is this report. Complete actual diffs follow.

## FULL_DIFFS


### New production module

```diff
diff --git a/contextor/core/cycle_semantics/cycle_warning_transitions.py b/contextor/core/cycle_semantics/cycle_warning_transitions.py
new file mode 100644
index 0000000..05df759
--- /dev/null
+++ b/contextor/core/cycle_semantics/cycle_warning_transitions.py
@@ -0,0 +1,144 @@
+"""Pure transitions between two installed cycle-warning projections.
+
+The caller captures each projection under its generation's LIVE owner lock.
+This module validates projection shapes but cannot authenticate their origin.
+MODEL_PASS is restricted static-model evidence, never runtime safety.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from .cycle_warning_projection import InstalledCycleWarningProjection
+
+
+@dataclass(frozen=True)
+class CycleWarningTransition:
+    path: tuple[str, ...]
+    action: str
+    previous_state: str | None
+    current_state: str | None
+
+
+@dataclass(frozen=True)
+class InstalledCycleWarningDelta:
+    status: str
+    reason: str | None
+    from_revision: int | None
+    to_revision: int | None
+    transitions: tuple[CycleWarningTransition, ...] | None
+
+
+def _validated_states(
+    projection: InstalledCycleWarningProjection,
+) -> dict[tuple[str, ...], str] | None:
+    """Validate an entire partition, including ordering, before comparing."""
+    if (
+        type(projection) is not InstalledCycleWarningProjection
+        or projection.status != "FRESH"
+        or projection.reason is not None
+        or type(projection.revision) is not int
+        or projection.revision < 0
+        or type(projection.structural_paths) is not tuple
+        or type(projection.model_pass_paths) is not tuple
+        or type(projection.active_warning_paths) is not tuple
+    ):
+        return None
+
+    structural = projection.structural_paths
+    accepted = projection.model_pass_paths
+    active = projection.active_warning_paths
+
+    for paths in (structural, accepted, active):
+        identities: set[tuple[str, ...]] = set()
+        for path in paths:
+            if (
+                type(path) is not tuple
+                or len(path) < 2
+                or any(type(node) is not str or not node for node in path)
+                or path[0] != path[-1]
+                or len(path[:-1]) != len(set(path[:-1]))
+                or path in identities
+            ):
+                return None
+            identities.add(path)
+
+    structural_set = set(structural)
+    accepted_set = set(accepted)
+    active_set = set(active)
+    if (
+        not accepted_set.isdisjoint(active_set)
+        or accepted_set | active_set != structural_set
+        or len(accepted) + len(active) != len(structural)
+        or accepted != tuple(path for path in structural if path in accepted_set)
+        or active != tuple(path for path in structural if path in active_set)
+    ):
+        return None
+
+    return {
+        path: "MODEL_PASS" if path in accepted_set else "ACTIVE"
+        for path in structural
+    }
+
+
+def diff_installed_cycle_warning_projections(
+    previous: InstalledCycleWarningProjection,
+    current: InstalledCycleWarningProjection,
+) -> InstalledCycleWarningDelta:
+    """Diff valid snapshots; do not confuse warning status with topology."""
+    unavailable = InstalledCycleWarningDelta(
+        status="UNAVAILABLE",
+        reason="WARNING_PROJECTION_UNAVAILABLE",
+        from_revision=None,
+        to_revision=None,
+        transitions=None,
+    )
+    try:
+        before = _validated_states(previous)
+        after = _validated_states(current)
+        if before is None or after is None:
+            return unavailable
+        old_revision = previous.revision
+        new_revision = current.revision
+        if new_revision < old_revision:
+            return unavailable
+        if new_revision == old_revision and previous != current:
+            return unavailable
+
+        transitions: list[CycleWarningTransition] = []
+        for path in previous.structural_paths:
+            old_state = before[path]
+            new_state = after.get(path)
+            if new_state == old_state:
+                continue
+            if new_state is None:
+                action = "STRUCTURAL_REMOVED"
+            elif old_state == "ACTIVE":
+                action = "MODEL_ACCEPTED"
+            else:
+                action = "WARNING_REACTIVATED"
+            transitions.append(CycleWarningTransition(
+                path=path,
+                action=action,
+                previous_state=old_state,
+                current_state=new_state,
+            ))
+
+        for path in current.structural_paths:
+            if path not in before:
+                transitions.append(CycleWarningTransition(
+                    path=path,
+                    action="STRUCTURAL_ADDED",
+                    previous_state=None,
+                    current_state=after[path],
+                ))
+
+        return InstalledCycleWarningDelta(
+            status="FRESH",
+            reason=None,
+            from_revision=old_revision,
+            to_revision=new_revision,
+            transitions=tuple(transitions),
+        )
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
+        return unavailable
```

### New test module

```diff
diff --git a/tests/test_cycle_semantics_cycle_warning_transitions.py b/tests/test_cycle_semantics_cycle_warning_transitions.py
new file mode 100644
index 0000000..9dfaec7
--- /dev/null
+++ b/tests/test_cycle_semantics_cycle_warning_transitions.py
@@ -0,0 +1,335 @@
+"""WARN-4B: warning transitions without rewriting structural-cycle history."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import FrozenInstanceError, replace
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.cycle_warning_projection import (
+    InstalledCycleWarningProjection,
+)
+from contextor.core.cycle_semantics.cycle_warning_transitions import (
+    CycleWarningTransition,
+    InstalledCycleWarningDelta,
+    diff_installed_cycle_warning_projections,
+)
+from tests.test_cycle_semantics_cycle_warning_projection import _project
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture,
+    _full,
+    _owner,
+    _persisted,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_HAZARD,
+    PASS_AND_UNKNOWN,
+    TWO_PASS,
+    _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _installed_next(root, server, *, partial=False, default=False):
+    if default:
+        errors, result = ContextorFacade.analyze_project(str(root))
+        assert isinstance(errors, list) and result is not None
+    else:
+        _full(root, partial=partial)
+    state, metadata = _persisted(root)
+    assert server._execute_publish({
+        "state": state, "origin": "isolated_test",
+    })["status"] == "ok"
+    return _project(server, state, metadata), state, metadata
+
+
+def _diff(before, after):
+    result = diff_installed_cycle_warning_projections(before, after)
+    assert type(result) is InstalledCycleWarningDelta
+    return result
+
+
+def _event(path, action, old, new):
+    return CycleWarningTransition(tuple(path), action, old, new)
+
+
+def _unavailable(result):
+    assert result == InstalledCycleWarningDelta(
+        status="UNAVAILABLE",
+        reason="WARNING_PROJECTION_UNAVAILABLE",
+        from_revision=None,
+        to_revision=None,
+        transitions=None,
+    )
+
+
+def _projection(revision, structural, accepted=()):
+    structural = tuple(tuple(p) for p in structural)
+    accepted = tuple(tuple(p) for p in accepted)
+    active = tuple(p for p in structural if p not in accepted)
+    return InstalledCycleWarningProjection(
+        status="FRESH", reason=None, revision=revision,
+        structural_paths=structural, model_pass_paths=accepted,
+        active_warning_paths=active,
+    )
+
+
+def test_t01_pass_unknown_to_default_reactivates_only_pass(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        after, _, _ = _installed_next(root, server, default=True)
+        assert before.structural_paths == after.structural_paths
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
+        )
+
+
+def test_t02_default_to_partial_accepts_only_pass(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, PASS_AND_UNKNOWN)
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert isinstance(errors, list) and result is not None
+    state, meta = _persisted(root)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        after, _, _ = _installed_next(root, server, partial=True)
+        assert before.structural_paths == after.structural_paths
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
+        )
+
+
+def test_t03_two_pass_to_default_reactivates_both(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        after, _, _ = _installed_next(root, server, default=True)
+        assert _diff(before, after).transitions == tuple(
+            _event(path, "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE")
+            for path in before.structural_paths
+        )
+
+
+def test_t04_pass_hazard_reactivates_only_pass(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_HAZARD)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        assert before.active_warning_paths == (("x", "y", "x"),)
+        after, _, _ = _installed_next(root, server, default=True)
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
+        )
+
+
+def test_t05_real_cycle_removed_is_structural_removed(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        (root / "b.py").write_text("value = 2\n", encoding="utf-8")
+        after, _, _ = _installed_next(root, server, default=True)
+        assert ("a", "b", "a") not in after.structural_paths
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "STRUCTURAL_REMOVED", "MODEL_PASS", None),
+        )
+
+
+def test_t06_real_new_cycle_added_as_active(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, {"a": "import b\n", "b": "value = 2\n"})
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert isinstance(errors, list) and result is not None
+    state, meta = _persisted(root)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        assert before.structural_paths == ()
+        (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")
+        after, _, _ = _installed_next(root, server, default=True)
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "STRUCTURAL_ADDED", None, "ACTIVE"),
+        )
+
+
+def test_t07_real_new_pass_cycle_is_structural_added(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, {"a": TWO_PASS["a"], "b": TWO_PASS["b"]})
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert isinstance(errors, list) and result is not None
+    state, meta = _persisted(root)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        assert before.active_warning_paths == (("a", "b", "a"),)
+        (root / "x.py").write_text(TWO_PASS["x"], encoding="utf-8")
+        (root / "y.py").write_text(TWO_PASS["y"], encoding="utf-8")
+        after, _, _ = _installed_next(root, server, partial=True)
+        assert after.model_pass_paths == (("a", "b", "a"), ("x", "y", "x"))
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
+            _event(("x", "y", "x"), "STRUCTURAL_ADDED", None, "MODEL_PASS"),
+        )
+
+
+def test_t08_real_pass_cycle_removed(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        (root / "y.py").write_text("value = 4\n", encoding="utf-8")
+        after, _, _ = _installed_next(root, server, partial=True)
+        assert ("x", "y", "x") not in after.structural_paths
+        assert _diff(before, after).transitions == (
+            _event(("x", "y", "x"), "STRUCTURAL_REMOVED", "MODEL_PASS", None),
+        )
+
+
+def test_t09_t10_identical_or_unchanged_partition(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        assert _diff(before, before) == InstalledCycleWarningDelta(
+            status="FRESH", reason=None, from_revision=meta.revision,
+            to_revision=meta.revision, transitions=(),
+        )
+        after, _, _ = _installed_next(root, server, partial=True)
+        assert _diff(before, after).transitions == ()
+        assert after.revision > before.revision
+
+
+def test_t11_t12_revision_order_and_same_revision_conflict():
+    a = ("a", "b", "a")
+    before = _projection(9, (a,))
+    later = _projection(8, (a,))
+    _unavailable(_diff(before, later))
+    conflict = _projection(9, (a,), (a,))
+    _unavailable(_diff(before, conflict))
+    reordered = _projection(9, (a, ("x", "y", "x")))
+    _unavailable(_diff(before, reordered))
+
+
+def test_t13_t14_unavailable_either_side(tmp_path, isolated_dirs):
+    _, state, meta = _fixture(tmp_path)
+    with _owner(state, meta) as (server, _):
+        fresh = _project(server, state, meta)
+    unavailable = replace(fresh, status="UNAVAILABLE", reason="STALE")
+    _unavailable(_diff(unavailable, fresh))
+    _unavailable(_diff(fresh, unavailable))
+
+
+@pytest.mark.parametrize("mutation", [
+    {"structural_paths": (("a", "b", "a", "b", "a"),)},
+    {"structural_paths": (("a", "b", "a"), ("a", "b", "a"))},
+    {"structural_paths": (("a", "b", "a"), ("x", "a", "x")),
+     "model_pass_paths": (("a", "b", "a"),), "active_warning_paths": ()},
+    {"structural_paths": (("a", "b", "a"),), "model_pass_paths": (("z", "q", "z"),)},
+    {"revision": True},
+    {"revision": -1},
+    {"model_pass_paths": [["a", "b", "a"]]},
+])
+def test_t15_invalid_projection_fails_closed(mutation):
+    a = ("a", "b", "a")
+    valid = _projection(1, (a,))
+    damaged = replace(valid, **mutation)
+    _unavailable(_diff(valid, damaged))
+    _unavailable(_diff(damaged, valid))
+
+
+def test_t16_subset_order_must_follow_structural_order():
+    a = ("a", "b", "a")
+    b = ("x", "y", "x")
+    valid = _projection(1, (a, b), (a, b))
+    _unavailable(_diff(valid, replace(valid, model_pass_paths=(b, a))))
+    all_active = _projection(1, (a, b))
+    _unavailable(_diff(all_active, replace(all_active, active_warning_paths=(b, a))))
+
+
+def test_t17_valid_empty_acyclic_transition(tmp_path, isolated_dirs):
+    root = _repo(tmp_path, {"a": "value = 1\n"})
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert isinstance(errors, list) and result is not None
+    state, meta = _persisted(root)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        after, _, _ = _installed_next(root, server, default=True)
+        assert before.structural_paths == after.structural_paths == ()
+        assert _diff(before, after).transitions == ()
+
+
+def test_t18_mixed_real_reactivation_removed_added_order(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        (root / "y.py").write_text("value = 4\n", encoding="utf-8")
+        (root / "u.py").write_text("import v\nvalue = 5\n", encoding="utf-8")
+        (root / "v.py").write_text("import u\nvalue = 6\n", encoding="utf-8")
+        after, _, _ = _installed_next(root, server, default=True)
+        assert _diff(before, after).transitions == (
+            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
+            _event(("x", "y", "x"), "STRUCTURAL_REMOVED", "ACTIVE", None),
+            _event(("u", "v", "u"), "STRUCTURAL_ADDED", None, "ACTIVE"),
+        )
+
+
+def test_t19_t20_no_false_structural_added_or_removed():
+    a = ("a", "b", "a")
+    active = _projection(1, (a,))
+    accepted = _projection(2, (a,), (a,))
+    assert _diff(active, accepted).transitions == (
+        _event(a, "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
+    )
+    assert _diff(accepted, replace(active, revision=3)).transitions == (
+        _event(a, "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
+    )
+
+
+def test_t21_t22_t23_deterministic_pure_and_frozen(tmp_path, isolated_dirs):
+    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        new, _, _ = _installed_next(root, server, default=True)
+        original = copy.deepcopy((
+            state.dependency_graph.hard_edges, state.cycles,
+            state.cycle_partial_source_publication, server._activity_epoch,
+            server._events,
+        ))
+        first = _diff(before, new)
+        assert first == _diff(before, new)
+        assert (
+            state.dependency_graph.hard_edges, state.cycles,
+            state.cycle_partial_source_publication, server._activity_epoch,
+            server._events,
+        ) == original
+        with pytest.raises(FrozenInstanceError):
+            first.transitions[0].action = "STRUCTURAL_REMOVED"
+        with pytest.raises(FrozenInstanceError):
+            first.transitions = ()
+
+
+def test_t24_existing_projection_and_partial_eligibility_unchanged(
+    tmp_path, isolated_dirs,
+):
+    _, state, meta = _fixture(tmp_path, PASS_AND_HAZARD)
+    with _owner(state, meta) as (server, _):
+        before = _project(server, state, meta)
+        assert before.model_pass_paths == (("a", "b", "a"),)
+        assert before.active_warning_paths == (("x", "y", "x"),)
+        assert _diff(before, before).transitions == ()
+        assert _project(server, state, meta) == before
+
+
+def test_wrong_types_and_containers_are_rejected():
+    a = ("a", "b", "a")
+    valid = _projection(1, (a,))
+    for damaged in (
+        None,
+        object(),
+        replace(valid, structural_paths=[a]),
+        replace(valid, structural_paths=(("a", 5, "a"),)),
+        replace(valid, model_pass_paths=(a,), active_warning_paths=(a,)),
+        replace(valid, model_pass_paths=None),
+        replace(valid, active_warning_paths=()),
+        replace(valid, reason="unexpected"),
+    ):
+        _unavailable(_diff(valid, damaged))
+        _unavailable(_diff(damaged, valid))
```

## REMAINING UNKNOWN

UNKNOWN: The user's active LIVE loaded-code adoption and actual warning-consumer behavior. This stage does not integrate any consumer or change LIVE IPC.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: WARN-4B-R1 exact implementation and focused regressions pass. Architectural GO remains with ChatGPT. STOP after this stage.

