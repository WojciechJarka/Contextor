"""WARN-4B: warning transitions without rewriting structural-cycle history."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.cycle_warning_projection import (
    InstalledCycleWarningProjection,
)
from contextor.core.cycle_semantics.cycle_warning_transitions import (
    CycleWarningTransition,
    InstalledCycleWarningDelta,
    diff_installed_cycle_warning_projections,
)
from tests.test_cycle_semantics_cycle_warning_projection import _project
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture,
    _full,
    _owner,
    _persisted,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD,
    PASS_AND_UNKNOWN,
    TWO_PASS,
    _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _installed_next(root, server, *, partial=False, default=False):
    if default:
        errors, result = ContextorFacade.analyze_project(str(root))
        assert isinstance(errors, list) and result is not None
    else:
        _full(root, partial=partial)
    state, metadata = _persisted(root)
    assert server._execute_publish({
        "state": state, "origin": "isolated_test",
    })["status"] == "ok"
    return _project(server, state, metadata), state, metadata


def _diff(before, after):
    result = diff_installed_cycle_warning_projections(before, after)
    assert type(result) is InstalledCycleWarningDelta
    return result


def _event(path, action, old, new):
    return CycleWarningTransition(tuple(path), action, old, new)


def _unavailable(result):
    assert result == InstalledCycleWarningDelta(
        status="UNAVAILABLE",
        reason="WARNING_PROJECTION_UNAVAILABLE",
        from_revision=None,
        to_revision=None,
        transitions=None,
    )


def _projection(revision, structural, accepted=()):
    structural = tuple(tuple(p) for p in structural)
    accepted = tuple(tuple(p) for p in accepted)
    active = tuple(p for p in structural if p not in accepted)
    return InstalledCycleWarningProjection(
        status="FRESH", reason=None, revision=revision,
        structural_paths=structural, model_pass_paths=accepted,
        active_warning_paths=active,
    )


def test_t01_pass_unknown_to_default_reactivates_only_pass(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        after, _, _ = _installed_next(root, server, default=True)
        assert before.structural_paths == after.structural_paths
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
        )


def test_t02_default_to_partial_accepts_only_pass(tmp_path, isolated_dirs):
    root = _repo(tmp_path, PASS_AND_UNKNOWN)
    errors, result = ContextorFacade.analyze_project(str(root))
    assert isinstance(errors, list) and result is not None
    state, meta = _persisted(root)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        after, _, _ = _installed_next(root, server, partial=True)
        assert before.structural_paths == after.structural_paths
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
        )


def test_t03_two_pass_to_default_reactivates_both(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, TWO_PASS)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        after, _, _ = _installed_next(root, server, default=True)
        assert _diff(before, after).transitions == tuple(
            _event(path, "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE")
            for path in before.structural_paths
        )


def test_t04_pass_hazard_reactivates_only_pass(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_HAZARD)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        assert before.active_warning_paths == (("x", "y", "x"),)
        after, _, _ = _installed_next(root, server, default=True)
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
        )


def test_t05_real_cycle_removed_is_structural_removed(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        (root / "b.py").write_text("value = 2\n", encoding="utf-8")
        after, _, _ = _installed_next(root, server, default=True)
        assert ("a", "b", "a") not in after.structural_paths
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "STRUCTURAL_REMOVED", "MODEL_PASS", None),
        )


def test_t06_real_new_cycle_added_as_active(tmp_path, isolated_dirs):
    root = _repo(tmp_path, {"a": "import b\n", "b": "value = 2\n"})
    errors, result = ContextorFacade.analyze_project(str(root))
    assert isinstance(errors, list) and result is not None
    state, meta = _persisted(root)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        assert before.structural_paths == ()
        (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")
        after, _, _ = _installed_next(root, server, default=True)
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "STRUCTURAL_ADDED", None, "ACTIVE"),
        )


def test_t07_real_new_pass_cycle_is_structural_added(tmp_path, isolated_dirs):
    root = _repo(tmp_path, {"a": TWO_PASS["a"], "b": TWO_PASS["b"]})
    errors, result = ContextorFacade.analyze_project(str(root))
    assert isinstance(errors, list) and result is not None
    state, meta = _persisted(root)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        assert before.active_warning_paths == (("a", "b", "a"),)
        (root / "x.py").write_text(TWO_PASS["x"], encoding="utf-8")
        (root / "y.py").write_text(TWO_PASS["y"], encoding="utf-8")
        after, _, _ = _installed_next(root, server, partial=True)
        assert after.model_pass_paths == (("a", "b", "a"), ("x", "y", "x"))
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
            _event(("x", "y", "x"), "STRUCTURAL_ADDED", None, "MODEL_PASS"),
        )


def test_t08_real_pass_cycle_removed(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, TWO_PASS)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        (root / "y.py").write_text("value = 4\n", encoding="utf-8")
        after, _, _ = _installed_next(root, server, partial=True)
        assert ("x", "y", "x") not in after.structural_paths
        assert _diff(before, after).transitions == (
            _event(("x", "y", "x"), "STRUCTURAL_REMOVED", "MODEL_PASS", None),
        )


def test_t09_t10_identical_or_unchanged_partition(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        assert _diff(before, before) == InstalledCycleWarningDelta(
            status="FRESH", reason=None, from_revision=meta.revision,
            to_revision=meta.revision, transitions=(),
        )
        after, _, _ = _installed_next(root, server, partial=True)
        assert _diff(before, after).transitions == ()
        assert after.revision > before.revision


def test_t11_t12_revision_order_and_same_revision_conflict():
    a = ("a", "b", "a")
    before = _projection(9, (a,))
    later = _projection(8, (a,))
    _unavailable(_diff(before, later))
    conflict = _projection(9, (a,), (a,))
    _unavailable(_diff(before, conflict))
    reordered = _projection(9, (a, ("x", "y", "x")))
    _unavailable(_diff(before, reordered))


def test_t13_t14_unavailable_either_side(tmp_path, isolated_dirs):
    _, state, meta = _fixture(tmp_path)
    with _owner(state, meta) as (server, _):
        fresh = _project(server, state, meta)
    unavailable = replace(fresh, status="UNAVAILABLE", reason="STALE")
    _unavailable(_diff(unavailable, fresh))
    _unavailable(_diff(fresh, unavailable))


@pytest.mark.parametrize("mutation", [
    {"structural_paths": (("a", "b", "a", "b", "a"),)},
    {"structural_paths": (("a", "b", "a"), ("a", "b", "a"))},
    {"structural_paths": (("a", "b", "a"), ("x", "a", "x")),
     "model_pass_paths": (("a", "b", "a"),), "active_warning_paths": ()},
    {"structural_paths": (("a", "b", "a"),), "model_pass_paths": (("z", "q", "z"),)},
    {"revision": True},
    {"revision": -1},
    {"model_pass_paths": [["a", "b", "a"]]},
])
def test_t15_invalid_projection_fails_closed(mutation):
    a = ("a", "b", "a")
    valid = _projection(1, (a,))
    damaged = replace(valid, **mutation)
    _unavailable(_diff(valid, damaged))
    _unavailable(_diff(damaged, valid))


def test_t16_subset_order_must_follow_structural_order():
    a = ("a", "b", "a")
    b = ("x", "y", "x")
    valid = _projection(1, (a, b), (a, b))
    _unavailable(_diff(valid, replace(valid, model_pass_paths=(b, a))))
    all_active = _projection(1, (a, b))
    _unavailable(_diff(all_active, replace(all_active, active_warning_paths=(b, a))))


def test_t17_valid_empty_acyclic_transition(tmp_path, isolated_dirs):
    root = _repo(tmp_path, {"a": "value = 1\n"})
    errors, result = ContextorFacade.analyze_project(str(root))
    assert isinstance(errors, list) and result is not None
    state, meta = _persisted(root)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        after, _, _ = _installed_next(root, server, default=True)
        assert before.structural_paths == after.structural_paths == ()
        assert _diff(before, after).transitions == ()


def test_t18_mixed_real_reactivation_removed_added_order(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        (root / "y.py").write_text("value = 4\n", encoding="utf-8")
        (root / "u.py").write_text("import v\nvalue = 5\n", encoding="utf-8")
        (root / "v.py").write_text("import u\nvalue = 6\n", encoding="utf-8")
        after, _, _ = _installed_next(root, server, default=True)
        assert _diff(before, after).transitions == (
            _event(("a", "b", "a"), "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
            _event(("x", "y", "x"), "STRUCTURAL_REMOVED", "ACTIVE", None),
            _event(("u", "v", "u"), "STRUCTURAL_ADDED", None, "ACTIVE"),
        )


def test_t19_t20_no_false_structural_added_or_removed():
    a = ("a", "b", "a")
    active = _projection(1, (a,))
    accepted = _projection(2, (a,), (a,))
    assert _diff(active, accepted).transitions == (
        _event(a, "MODEL_ACCEPTED", "ACTIVE", "MODEL_PASS"),
    )
    assert _diff(accepted, replace(active, revision=3)).transitions == (
        _event(a, "WARNING_REACTIVATED", "MODEL_PASS", "ACTIVE"),
    )


def test_t21_t22_t23_deterministic_pure_and_frozen(tmp_path, isolated_dirs):
    root, state, meta = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        new, _, _ = _installed_next(root, server, default=True)
        original = copy.deepcopy((
            state.dependency_graph.hard_edges, state.cycles,
            state.cycle_partial_source_publication, server._activity_epoch,
            server._events,
        ))
        first = _diff(before, new)
        assert first == _diff(before, new)
        assert (
            state.dependency_graph.hard_edges, state.cycles,
            state.cycle_partial_source_publication, server._activity_epoch,
            server._events,
        ) == original
        with pytest.raises(FrozenInstanceError):
            first.transitions[0].action = "STRUCTURAL_REMOVED"
        with pytest.raises(FrozenInstanceError):
            first.transitions = ()


def test_t24_existing_projection_and_partial_eligibility_unchanged(
    tmp_path, isolated_dirs,
):
    _, state, meta = _fixture(tmp_path, PASS_AND_HAZARD)
    with _owner(state, meta) as (server, _):
        before = _project(server, state, meta)
        assert before.model_pass_paths == (("a", "b", "a"),)
        assert before.active_warning_paths == (("x", "y", "x"),)
        assert _diff(before, before).transitions == ()
        assert _project(server, state, meta) == before


def test_wrong_types_and_containers_are_rejected():
    a = ("a", "b", "a")
    valid = _projection(1, (a,))
    for damaged in (
        None,
        object(),
        replace(valid, structural_paths=[a]),
        replace(valid, structural_paths=(("a", 5, "a"),)),
        replace(valid, model_pass_paths=(a,), active_warning_paths=(a,)),
        replace(valid, model_pass_paths=None),
        replace(valid, active_warning_paths=()),
        replace(valid, reason="unexpected"),
    ):
        _unavailable(_diff(valid, damaged))
        _unavailable(_diff(damaged, valid))
