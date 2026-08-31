from pathlib import Path

import contextor.core.api.facade as facade
from contextor.core.analysis.incremental.materialization import RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.validator.collisions import compute_collisions_from_facts


def _modules(tmp_path, names=("one", "two")):
    result = {}
    for name in names:
        path = tmp_path / f"{name}.py"
        path.write_text(f"def {name}():\n    return 1\n", encoding="utf-8")
        result[name] = Module(name, f"{name}.py", str(path), [])
    return result


def _fact(module, name="public", code="def public():\n    return 1\n"):
    return {
        "name": name,
        "type": "function",
        "file": module,
        "file_path": f"{module}.py",
        "code": code,
        "line_start": 1,
        "line_end": 2,
        "col_start": 0,
        "col_end": 12,
    }


def test_hydrated_complete_facts_skip_repository_extraction_and_preserve_output(
    tmp_path, monkeypatch
):
    modules = _modules(tmp_path, ("one", "two"))
    facts = {"one": [_fact("one")], "two": [_fact("two")]}
    state = RepositoryAnalysisState(
        modules=modules, collision_facts=facts, collisions_state="fresh"
    )
    expected = compute_collisions_from_facts(facts)
    called = []
    monkeypatch.setattr(
        facade,
        "assemble_collision_facts_or_fallback",
        lambda *args: called.append(args) or (_ for _ in ()).throw(
            AssertionError("hydrated complete facts must not fall back")
        ),
    )

    selected = facade._assemble_layer_collision_facts(
        modules, state=state
    )

    assert selected is facts
    assert compute_collisions_from_facts(selected) == expected
    assert called == []


def test_hydrated_empty_complete_facts_are_accepted_without_fallback(tmp_path, monkeypatch):
    modules = _modules(tmp_path, ("one", "two"))
    state = RepositoryAnalysisState(
        modules=modules, collision_facts={"one": [], "two": []}, collisions_state="fresh"
    )
    monkeypatch.setattr(
        facade,
        "assemble_collision_facts_or_fallback",
        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
    )

    selected = facade._assemble_layer_collision_facts(
        modules, state=state
    )

    assert selected == {"one": [], "two": []}
    assert compute_collisions_from_facts(selected) == []


def test_hydrated_invalid_or_deferred_facts_use_authoritative_fallback(tmp_path, monkeypatch):
    modules = _modules(tmp_path, ("one",))
    fallback = {"one": [_fact("one", name="fallback")]}
    for facts, status in (
        ({"one": [{"bad": "fact"}]}, "fresh"),
        ({"one": []}, "deferred"),
        ({}, "fresh"),
    ):
        calls = []
        monkeypatch.setattr(
            facade,
            "assemble_collision_facts_or_fallback",
            lambda modules, indexed: calls.append((modules, indexed)) or fallback,
        )
        state = RepositoryAnalysisState(
            modules=modules, collision_facts=facts, collisions_state=status
        )
        assert facade._assemble_layer_collision_facts(
            modules, state=state
        ) is fallback
        assert len(calls) == 1 and calls[0][1] is None


def test_fallback_complete_indexed_facts_use_existing_authority(tmp_path, monkeypatch):
    modules = _modules(tmp_path, ("one",))
    facts = {"one": [_fact("one")]}
    calls = []
    monkeypatch.setattr(
        facade,
        "assemble_collision_facts_or_fallback",
        lambda got_modules, got_facts: calls.append((got_modules, got_facts)) or facts,
    )

    selected = facade._assemble_layer_collision_facts(
        modules, indexed_facts=facts
    )

    assert selected is facts
    assert calls == [(modules, facts)]


def test_fallback_invalid_indexed_facts_delegate_fallback_without_second_validation(
    tmp_path, monkeypatch
):
    modules = _modules(tmp_path, ("one", "two"))
    invalid = {"one": []}
    fallback = {"one": [], "two": []}
    calls = []
    monkeypatch.setattr(
        facade,
        "assemble_collision_facts_or_fallback",
        lambda got_modules, got_facts: calls.append((got_modules, got_facts)) or fallback,
    )

    assert facade._assemble_layer_collision_facts(
        modules, indexed_facts=invalid
    ) is fallback
    assert calls == [(modules, invalid)]


def test_metrics_path_aggregates_selected_facts_without_validator(tmp_path, monkeypatch):
    modules = _modules(tmp_path, ("one", "two"))
    facts = {"one": [_fact("one")], "two": [_fact("two")]}
    graph = type("Graph", (), {"hard_edges": {}, "soft_edges": {}})()
    monkeypatch.setattr(
        facade,
        "validate_name_collisions",
        lambda *args: (_ for _ in ()).throw(AssertionError("validator must not run")),
    )

    metrics, cycles, collisions, debt = facade._compute_metrics_and_debt(
        modules, graph, collision_facts=facts
    )

    assert collisions == compute_collisions_from_facts(facts)


def test_selected_facts_preserve_collision_classes_and_detail_fields():
    divergent = {
        "one": [_fact("one", code="def public():\n    return 1\n")],
        "two": [_fact("two", code="def public():\n    return 2\n")],
    }
    identical = {
        "one": [_fact("one")],
        "two": [_fact("two")],
    }

    divergent_errors = compute_collisions_from_facts(divergent)
    identical_errors = compute_collisions_from_facts(identical)

    assert divergent_errors[0].kind == "NAME_COLLISION"
    assert divergent_errors[0].is_identical is False
    assert identical_errors[0].kind == "IDENTICAL_DEFINITION_DUPLICATE"
    assert identical_errors[0].is_identical is True
    for error in divergent_errors + identical_errors:
        assert error.artifact_type == "function"
        assert error.symbol_details
        assert error.code_snippets
