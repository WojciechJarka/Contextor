from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from contextor.core.analysis.incremental.preparation import (
    prepare_source_update,
)
from contextor.core.analysis.incremental.plan_executor import (
    execute_refresh_plan,
)
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.validator.collisions import (
    COLLISION_FACT_KEYS,
    CollisionFact,
    compute_collisions_from_facts,
    extract_module_collision_facts,
    materialize_canonical_collision_facts,
)


def _write_sources(root: Path, sources: dict[str, str]) -> None:
    for relative, content in sources.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _run_full_and_load(root: Path) -> RepositoryAnalysisState:
    errors, _result = ContextorFacade.analyze_project(str(root))
    assert not errors, f"FULL validation failed for {root}: {errors!r}"

    cache_dir = repo_cache_dir(root)
    metadata = read_metadata(cache_dir)
    assert metadata is not None, f"FULL did not persist snapshot for {root}"
    state = load_engine_state(
        str(cache_dir),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert isinstance(state, RepositoryAnalysisState)
    assert state.state_id == metadata.state_id
    assert state.revision == metadata.revision
    return state


def _assert_ast_free_plain_facts(
    collision_facts: dict[str, list[dict]],
) -> None:
    for module_id, facts in collision_facts.items():
        assert isinstance(module_id, str)
        for fact in facts:
            assert type(fact) is dict
            assert tuple(fact) == COLLISION_FACT_KEYS
            assert all(not isinstance(value, ast.AST) for value in fact.values())


def test_full_unique_collision_facts_use_empty_code_and_plain_dicts(tmp_path):
    _write_sources(
        tmp_path,
        {
            "alpha.py": (
                "def alpha_api():\n"
                "    return 1\n"
                "\n"
                "ALPHA_VALUE = 2\n"
            ),
            "beta.py": "def beta_api():\n    return 3\n",
        },
    )

    state = _run_full_and_load(tmp_path)

    assert state.collisions_state == "fresh"
    assert state.collisions == []
    _assert_ast_free_plain_facts(state.collision_facts)
    assert state.collision_facts
    assert all(
        fact["code"] == ""
        for facts in state.collision_facts.values()
        for fact in facts
    )


def test_new_module_incremental_collision_facts_match_fresh_full(tmp_path):
    _write_sources(
        tmp_path,
        {
            "alpha/__init__.py": "",
            "alpha/api.py": "def alpha_api():\n    return 1\n",
            "beta/__init__.py": "",
            "beta/consumer.py": (
                "from alpha.api import alpha_api\n"
                "BETA_RESULT = alpha_api()\n"
            ),
        },
    )
    baseline = _run_full_and_load(tmp_path)
    assert baseline.collisions_state == "fresh"

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    engine = hydrated.engine
    previous_mapping = engine.state.collision_facts
    previous_value = deepcopy(previous_mapping)

    gamma_init = tmp_path / "gamma" / "__init__.py"
    gamma_init.parent.mkdir(parents=True, exist_ok=True)
    gamma_init.write_text("GAMMA_VALUE = 7\n", encoding="utf-8")

    result = engine.update_file(str(gamma_init.resolve()))
    assert result.status == "UPDATED"
    assert "gamma.__init__" in engine.state.modules
    assert engine.state.collisions_state == "fresh"

    incremental_facts = deepcopy(engine.state.collision_facts)
    _assert_ast_free_plain_facts(incremental_facts)
    assert previous_mapping == previous_value

    fresh_full = _run_full_and_load(tmp_path)
    assert fresh_full.collisions_state == "fresh"
    _assert_ast_free_plain_facts(fresh_full.collision_facts)
    assert incremental_facts == fresh_full.collision_facts
    assert incremental_facts["gamma.__init__"][0]["code"] == ""


def test_unique_lazy_facts_materialize_without_unparse_or_input_mutation(
    monkeypatch,
):
    import contextor.core.validator.collisions as collisions_module

    tree = ast.parse(
        "def unique_first():\n"
        "    return 1\n"
        "\n"
        "def unique_second():\n"
        "    return 2\n"
    )
    original = {
        "pkg.module": extract_module_collision_facts(
            tree,
            "pkg.module",
            "pkg/module.py",
        )
    }
    original_facts = list(original["pkg.module"])
    original_snapshots = [
        fact._to_plain_dict(render_code=False)
        for fact in original_facts
    ]
    original_nodes = [fact._node for fact in original_facts]
    assert all(fact._rendered_code is None for fact in original_facts)

    def unexpected_unparse(_node):
        raise AssertionError("unique collision facts must not be unparsed")

    monkeypatch.setattr(collisions_module.ast, "unparse", unexpected_unparse)
    result = materialize_canonical_collision_facts(original)

    assert list(result) == list(original)
    assert [id(fact) for fact in original["pkg.module"]] == [
        id(fact) for fact in original_facts
    ]
    assert [fact._to_plain_dict(render_code=False) for fact in original_facts] == (
        original_snapshots
    )
    assert [fact._node for fact in original_facts] == original_nodes
    assert all(fact._rendered_code is None for fact in original_facts)
    assert all(type(fact) is dict for fact in result["pkg.module"])
    assert all(fact["code"] == "" for fact in result["pkg.module"])
    assert all(
        tuple(fact) == COLLISION_FACT_KEYS
        for fact in result["pkg.module"]
    )
    assert all(
        not isinstance(value, ast.AST)
        for facts in result.values()
        for fact in facts
        for value in fact.values()
    )


@pytest.mark.parametrize(
    ("source_b", "expected_kind", "expected_code_b"),
    [
        (
            "def shared_api(value):\n    return value + 1\n",
            "IDENTICAL_DEFINITION_DUPLICATE",
            "def shared_api(value):\n    return value + 1",
        ),
        (
            "def shared_api(value):\n    return value + 2\n",
            "NAME_COLLISION",
            "def shared_api(value):\n    return value + 2",
        ),
    ],
)
def test_candidate_code_is_preserved_and_classification_matches(
    source_b,
    expected_kind,
    expected_code_b,
):
    source_a = "def shared_api(value):\n    return value + 1\n"
    facts = {
        "mod_a": extract_module_collision_facts(
            ast.parse(source_a),
            "mod_a",
            "mod_a.py",
        ),
        "mod_b": extract_module_collision_facts(
            ast.parse(source_b),
            "mod_b",
            "mod_b.py",
        ),
    }

    canonical = materialize_canonical_collision_facts(facts)

    assert canonical["mod_a"][0]["code"] == (
        "def shared_api(value):\n    return value + 1"
    )
    assert canonical["mod_b"][0]["code"] == expected_code_b
    _assert_ast_free_plain_facts(canonical)

    errors = compute_collisions_from_facts(canonical)
    assert len(errors) == 1
    assert errors[0].kind == expected_kind
    assert errors[0].code_snippets == {
        "mod_a": "def shared_api(value):\n    return value + 1",
        "mod_b": expected_code_b,
    }


def test_missing_code_for_multi_module_candidate_fails_closed():
    facts = {
        "mod_a": [
            {
                "name": "shared_api",
                "type": "function",
                "file": "mod_a",
                "file_path": "mod_a.py",
                "code": "",
                "line_start": 1,
                "line_end": 2,
                "col_start": 0,
                "col_end": 10,
            }
        ],
        "mod_b": [
            {
                "name": "shared_api",
                "type": "function",
                "file": "mod_b",
                "file_path": "mod_b.py",
                "code": "",
                "line_start": 1,
                "line_end": 2,
                "col_start": 0,
                "col_end": 10,
            }
        ],
    }
    original = deepcopy(facts)

    with pytest.raises(
        ValueError,
        match="Missing code for canonical collision candidate",
    ):
        materialize_canonical_collision_facts(facts)

    assert facts == original


@pytest.mark.parametrize("failure_kind", ["incomplete", "missing_code"])
def test_incremental_invalid_collision_candidate_is_not_fresh(
    tmp_path,
    monkeypatch,
    failure_kind,
):
    import contextor.core.analysis.incremental.materialization as materialization_module
    import contextor.core.validator.collisions as collisions_module

    _write_sources(
        tmp_path,
        {
            "alpha.py": "def shared_api():\n    return 1\n",
            "beta.py": "def beta_only():\n    return 0\n",
        },
    )
    state = _run_full_and_load(tmp_path)
    assert state.collisions_state == "fresh"
    previous_facts = deepcopy(state.collision_facts)

    beta_path = tmp_path / "beta.py"
    beta_path.write_text(
        "def beta_only():\n"
        "    return 0\n"
        "\n"
        "def shared_api():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    prepared = prepare_source_update(
        file_path=str(beta_path.resolve()),
        module_path="beta",
        is_new=False,
        old_module=state.modules["beta"],
        old_artifacts=state.artifacts.get("beta", {}),
        old_usage=state.module_usages.get("beta"),
        persistent_id="beta",
        old_collision_facts=state.collision_facts["beta"],
    )
    assert prepared.collision_facts_changed
    plan = RefreshPlanner.plan_refresh(
        delta=prepared.delta,
        usage_delta=prepared.usage_delta,
        collision_facts_changed=prepared.collision_facts_changed,
    )

    if failure_kind == "incomplete":
        monkeypatch.setattr(
            materialization_module,
            "_validate_collision_facts_dict",
            lambda _facts, _modules: False,
        )
    else:
        def blank_candidate_codes(collision_facts, _modules):
            result = {}
            for module_id, module_facts in collision_facts.items():
                result[module_id] = []
                for fact in module_facts:
                    if isinstance(fact, CollisionFact):
                        entry = fact._to_plain_dict(render_code=False)
                    else:
                        entry = dict(fact)
                    entry["code"] = ""
                    result[module_id].append(entry)
            return result

        monkeypatch.setattr(
            collisions_module,
            "resolve_collision_candidate_codes",
            blank_candidate_codes,
        )

    outcome = execute_refresh_plan(
        state=state,
        delta=prepared.delta,
        usage_delta=prepared.usage_delta,
        plan=plan,
        new_imports=prepared.new_imports,
        new_artifacts=prepared.new_artifacts,
        new_usage=prepared.new_usage,
        root_path=tmp_path.resolve(),
        file_path=str(beta_path.resolve()),
        new_collision_facts=prepared.new_collision_facts,
        new_reexport_facts=prepared.new_reexport_facts,
    )

    assert state.collisions_state == "fresh"
    assert state.collision_facts == previous_facts
    assert outcome.candidate_state.collisions_state == "deferred"
