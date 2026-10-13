"""Package initializer usage details follow the canonical FULL reference target."""

from __future__ import annotations

import ast
import builtins
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.reference import engine as reference_engine
from contextor.core.reference.engine import (
    CanonicalReferenceEvidenceUnavailable,
    _usage_fact_contains_target,
    build_symbol_references_from_canonical,
)
from contextor.core.reference.shared import _canonicalize_package_reference_target


_PACKAGE_REFERENCE_DETAIL_SOURCES = {
    "alpha/__init__.py": b"from .api import api_function\n",
    "alpha/api.py": b"def api_function():\n    return 1\n",
    "beta/__init__.py": b"",
    "beta/consumer.py": (
        b"from alpha import api_function\n"
        b"CONSUMER_RESULT = api_function()\n"
    ),
    "loose.py": b"LOOSE_VALUE = 0\n",
}


def _run_full(root: Path) -> RepositoryAnalysisState:
    errors, _ = ContextorFacade.analyze_project(str(root))
    assert not errors, f"FULL analysis failed for isolated fixture {root}: {errors!r}"
    cache = repo_cache_dir(root)
    metadata = read_metadata(cache)
    assert metadata is not None
    state = load_engine_state(
        str(cache),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert isinstance(state, RepositoryAnalysisState)
    assert state.state_id == metadata.state_id
    assert state.revision == metadata.revision
    return state


@pytest.fixture(scope="module")
def retargeted_states(tmp_path_factory):
    parent = tmp_path_factory.mktemp("package_reference_detail")
    root = parent / "repo"
    root.mkdir()
    for relative, content in _PACKAGE_REFERENCE_DETAIL_SOURCES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CONTEXTOR_CACHE_DIR", str(parent / "cache"))
        baseline_state = _run_full(root)
        hydrated = hydrate_repository_engine(root)
        assert hydrated is not None
        engine = hydrated.engine
        assert engine.state.state_id == baseline_state.state_id
        original_state = engine.state
        original_snapshot = copy.deepcopy(original_state)
        original_consumers_view = (
            original_state.artifacts["alpha.__init__"]["consumers"]
        )
        original_consumers = copy.deepcopy(
            original_consumers_view
        )

        assert "api_function" not in original_consumers

        target = root / "alpha" / "__init__.py"
        target.write_bytes(b"api_function = 7\n")
        result = engine.update_file(str(target.resolve()))
        assert result.status == "UPDATED"
        incremental_state = engine.state
        full_state = _run_full(root)

    return {
        "original": original_snapshot,
        "original_consumers_view": original_consumers_view,
        "original_consumers": original_consumers,
        "incremental": incremental_state,
        "full": full_state,
        "update_status": result.status,
    }


def test_package_initializer_match_uses_current_module_domain():
    modules = {"alpha.__init__", "alpha.api", "beta.consumer"}
    assert not _usage_fact_contains_target(
        "alpha.api_function", "alpha.__init__", "api_function"
    )
    assert _usage_fact_contains_target(
        "alpha.api_function",
        "alpha.__init__",
        "api_function",
        current_modules=modules,
    )


def test_real_import_alias_is_canonicalized(retargeted_states, monkeypatch):
    state = retargeted_states["incremental"]
    facts = state.module_usages["beta.consumer"]
    assert facts.reference_evidence_materialized
    assert ("api_function", "alpha.api_function") in facts.aliases
    direct_call = next(
        item for item in facts.reference_evidence if item[1] == "direct_calls"
    )
    assert direct_call == ("alpha.api_function", "direct_calls", "", 2)

    observed = []
    canonicalize = reference_engine._canonicalize_package_reference_target

    def record_canonicalization(target, modules):
        observed.append(target)
        return canonicalize(target, modules)

    with monkeypatch.context() as patch:
        patch.setattr(
            reference_engine,
            "_canonicalize_package_reference_target",
            record_canonicalization,
        )
        assert _usage_fact_contains_target(
            direct_call[0],
            "alpha.__init__",
            "api_function",
            facts.aliases,
            current_modules=set(state.modules),
        )

    assert observed == ["alpha.api_function", "alpha.api_function"]
    assert _canonicalize_package_reference_target(
        dict(facts.aliases)["api_function"], set(state.modules)
    ) == "alpha.__init__.api_function"


def test_real_submodule_identity_takes_longest_prefix_precedence():
    modules = {
        "alpha.__init__",
        "alpha.api",
        "alpha.api_function",
        "beta.consumer",
    }
    assert _canonicalize_package_reference_target(
        "alpha.api_function", modules
    ) == "alpha.api_function"
    assert not _usage_fact_contains_target(
        "alpha.api_function",
        "alpha.__init__",
        "api_function",
        current_modules=modules,
    )


def test_reexport_retarget_matches_full_consumer_detail(retargeted_states):
    incremental = retargeted_states["incremental"]
    full = retargeted_states["full"]
    target = "alpha.__init__::api_function"
    for state in (incremental, full):
        assert state.artifact_consumption[target] == {
            "consumers": ["beta.consumer"],
            "channels": {"beta.consumer": ["api_imports", "direct_calls"]},
        }

    incremental_record = incremental.artifacts["alpha.__init__"]["consumers"]["api_function"]
    full_record = full.artifacts["alpha.__init__"]["consumers"]["api_function"]
    assert incremental_record == full_record
    assert incremental_record["consumers"] == ["beta.consumer"]
    assert incremental_record["usage"]["direct_calls"] == ["beta.consumer"]
    assert incremental_record["usage"]["direct_calls_detail"] == [
        {"module": "beta.consumer", "line": 2, "context": None}
    ]
    assert incremental_record["consumer_count"] == {
        "total": 1,
        "direct_calls": 1,
        "callbacks": 0,
        "events": 0,
        "qualified_refs": 0,
        "api_imports": 1,
        "inheritance": 0,
    }


def test_cow_and_missing_reference_evidence_fail_closed(retargeted_states):
    original = retargeted_states["original"]
    incremental = retargeted_states["incremental"]
    old_consumers_view = (
        retargeted_states["original_consumers_view"]
    )
    assert original is not incremental
    assert original.artifacts["alpha.__init__"]["consumers"] == (
        retargeted_states["original_consumers"]
    )
    assert old_consumers_view == (
        retargeted_states["original_consumers"]
    )

    assert old_consumers_view is not (
        incremental.artifacts["alpha.__init__"]["consumers"]
    )

    assert "api_function" not in old_consumers_view

    assert "api_function" not in (
        original.artifacts["alpha.__init__"]["consumers"]
    )

    assert "api_function" in (
        incremental.artifacts["alpha.__init__"]["consumers"]
    )

    assert incremental.artifacts["alpha.__init__"]["consumers"][
        "api_function"
    ] is not old_consumers_view.get("api_function")

    modules = set(incremental.modules)
    usages = dict(incremental.module_usages)
    usages.pop("beta.consumer")
    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
        build_symbol_references_from_canonical(
            definer_module="alpha.__init__",
            symbols=["api_function"],
            artifact_consumption=incremental.artifact_consumption,
            module_usages=usages,
            current_modules=modules,
        )

    usages = dict(incremental.module_usages)
    usages["beta.consumer"] = replace(
        usages["beta.consumer"], reference_evidence_materialized=False
    )
    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
        build_symbol_references_from_canonical(
            definer_module="alpha.__init__",
            symbols=["api_function"],
            artifact_consumption=incremental.artifact_consumption,
            module_usages=usages,
            current_modules=modules,
        )


def test_canonical_detail_projection_reads_only_materialized_ram_facts(
    retargeted_states, monkeypatch
):
    state = retargeted_states["incremental"]

    def unexpected_io(*_args, **_kwargs):
        pytest.fail("canonical RAM projection performed source I/O or parsing")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", unexpected_io)
        patch.setattr(Path, "read_text", unexpected_io)
        patch.setattr(Path, "read_bytes", unexpected_io)
        patch.setattr(ast, "parse", unexpected_io)
        patch.setattr(reference_engine, "read_source", unexpected_io)
        references = build_symbol_references_from_canonical(
            definer_module="alpha.__init__",
            symbols=["api_function"],
            artifact_consumption=state.artifact_consumption,
            module_usages=state.module_usages,
            current_modules=set(state.modules),
        )

    assert references["api_function"]["called_by_detail"] == [
        {"module": "beta.consumer", "line": 2, "context": None}
    ]
