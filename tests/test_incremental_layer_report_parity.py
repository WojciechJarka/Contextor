"""Focused FULL cache and incremental layer-report parity regressions."""

from __future__ import annotations

import ast
import builtins
from copy import deepcopy
from pathlib import Path

import pytest

from contextor.core.analysis.incremental.materialization import (
    ensure_cached_analytics,
)
from contextor.core.analysis.incremental.plan_executor import (
    _build_canonical_layer_index,
    _prepare_candidate_state,
    _refresh_canonical_layer_information,
)
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.reporting_engine.graph_analytics import (
    compute_cached_analytics,
)
from test_desktop_mcp_canonical_parity import (
    _first_difference,
    _state_projection,
)


def _write_sources(root: Path, sources: dict[str, str]) -> None:
    for name, content in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _full_state(root: Path) -> RepositoryAnalysisState:
    errors, _ = ContextorFacade.analyze_project(str(root))
    assert not errors, errors
    cache_dir = repo_cache_dir(root)
    metadata = read_metadata(cache_dir)
    assert metadata is not None
    state = load_engine_state(
        str(cache_dir),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root),
    )
    assert isinstance(state, RepositoryAnalysisState)
    return state


def _layer_projection(state: RepositoryAnalysisState) -> dict:
    return _state_projection(
        state,
        normalize_report_timestamps=True,
    )["fields"]["layer_information"]


def _assert_layer_parity(
    incremental: RepositoryAnalysisState,
    oracle: RepositoryAnalysisState,
    root: Path,
) -> None:
    difference = _first_difference(
        _layer_projection(incremental),
        _layer_projection(oracle),
        "state.layer_information",
    )
    assert difference is None, f"layer report mismatch: {difference!r}; root={root}"


def test_full_materializes_cached_analytics_and_hydration_matches(tmp_path):
    _write_sources(
        tmp_path,
        {
            "provider.py": "PROVIDER_VALUE = 1\n",
            "consumer.py": "from provider import PROVIDER_VALUE\nUSED_VALUE = PROVIDER_VALUE\n",
        },
    )
    full = _full_state(tmp_path)
    assert full.cached_analytics_state == "fresh"
    assert full.cached_analytics == compute_cached_analytics(
        modules=full.modules,
        artifacts=full.artifacts,
        artifact_consumption=full.artifact_consumption,
        hard_edges=full.dependency_graph.hard_edges,
    )
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    assert hydrated.engine.state.cached_analytics == full.cached_analytics
    assert hydrated.engine.state.cached_analytics_state == full.cached_analytics_state


def test_initializer_graph_report_matches_fresh_full_and_preserves_old_view(tmp_path):
    _write_sources(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/child.py": "VALUE = 1\n",
            "consumer.py": "from pkg import child\nCONSUMED_VALUE = child.VALUE\n",
            "unrelated.py": "UNRELATED_VALUE = 2\n",
        },
    )
    _full_state(tmp_path)
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    engine = hydrated.engine
    previous_layer = engine.state.layer_information
    previous_summary = previous_layer["summary_data"]
    previous_copy = deepcopy(previous_layer)
    old_soft = previous_layer["summary_data"]["metrics"]["edges_soft"]
    initializer = tmp_path / "pkg" / "__init__.py"
    initializer.write_text("child = 123\n", encoding="utf-8")

    result = engine.update_file(str(initializer))
    assert result.status == "UPDATED"
    assert previous_layer == previous_copy
    assert previous_summary == previous_copy["summary_data"]
    assert engine.state.layer_information is not previous_layer
    assert engine.state.layer_information["summary_data"] is not previous_summary
    assert engine.state.layer_information["summary_data"]["metrics"]["edges_soft"] < old_soft
    assert engine.state.layer_information["summary_data"]["cycle_count"] == len(engine.state.cycles)
    assert engine.state.layer_information["summary_data"]["collision_count"] == len(
        [c for c in engine.state.collisions if not getattr(c, "is_identical", False)]
    )
    incremental_projection = _layer_projection(engine.state)
    oracle = _full_state(tmp_path)
    difference = _first_difference(
        incremental_projection,
        _layer_projection(oracle),
        "state.layer_information",
    )
    assert difference is None, f"layer report mismatch: {difference!r}; root={tmp_path}"


def test_new_top_level_layer_matches_fresh_full_and_preserves_old_view(tmp_path):
    _write_sources(
        tmp_path,
        {
            "alpha/__init__.py": "",
            "alpha/value.py": "ALPHA_VALUE = 1\n",
            "beta/__init__.py": "",
            "beta/value.py": "BETA_VALUE = 2\n",
        },
    )
    baseline = _full_state(tmp_path)
    assert {
        item["layer"]
        for item in baseline.layer_information["layer_index"]
    } == {"alpha", "beta"}

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    engine = hydrated.engine
    previous_layer = engine.state.layer_information
    previous_summary = previous_layer["summary_data"]
    previous_copy = deepcopy(previous_layer)

    gamma_init = tmp_path / "gamma" / "__init__.py"
    gamma_init.parent.mkdir(parents=True, exist_ok=True)
    gamma_init.write_text("GAMMA_VALUE = 7\n", encoding="utf-8")

    result = engine.update_file(str(gamma_init))
    assert result.status == "UPDATED"
    assert "gamma.__init__" in engine.state.modules

    incremental = deepcopy(engine.state)
    layer_index = incremental.layer_information["layer_index"]
    summary_index = incremental.layer_information["summary_data"]["layer_index"]
    assert [item["layer"] for item in layer_index] == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert layer_index == summary_index

    oracle = _full_state(tmp_path)
    full_index = oracle.layer_information["layer_index"]
    gamma_entry = next(item for item in layer_index if item["layer"] == "gamma")
    full_gamma_entry = next(item for item in full_index if item["layer"] == "gamma")
    assert gamma_entry == full_gamma_entry
    assert gamma_entry["status"] == full_gamma_entry["status"]
    assert gamma_entry["computation_mode"] == full_gamma_entry["computation_mode"]
    assert [item["layer"] for item in full_index] == [
        "alpha",
        "beta",
        "gamma",
    ]
    _assert_layer_parity(incremental, oracle, tmp_path)

    assert previous_layer == previous_copy
    assert previous_summary == previous_copy["summary_data"]


def test_removing_last_layer_module_matches_fresh_full_and_clears_index(tmp_path):
    _write_sources(
        tmp_path,
        {"gamma/only.py": "GAMMA_VALUE = 7\n"},
    )
    baseline = _full_state(tmp_path)
    assert [
        item["layer"]
        for item in baseline.layer_information["layer_index"]
    ] == ["gamma"]

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    engine = hydrated.engine
    previous_layer = engine.state.layer_information
    previous_summary = previous_layer["summary_data"]
    previous_copy = deepcopy(previous_layer)

    source = tmp_path / "gamma" / "only.py"
    source.unlink()
    result = engine.update_file(str(source))
    assert result.status == "DELETED"
    assert "gamma.only" not in engine.state.modules

    incremental = deepcopy(engine.state)
    assert incremental.layer_information["layer_index"] == []
    assert "layer_index" not in incremental.layer_information["summary_data"]

    oracle = _full_state(tmp_path)
    assert oracle.layer_information["layer_index"] == []
    assert "layer_index" not in oracle.layer_information["summary_data"]
    _assert_layer_parity(incremental, oracle, tmp_path)

    assert previous_layer == previous_copy
    assert previous_summary == previous_copy["summary_data"]


def test_layer_index_refresh_does_not_read_or_parse_source_files(tmp_path, monkeypatch):
    _write_sources(
        tmp_path,
        {
            "alpha/__init__.py": "",
            "alpha/value.py": "ALPHA_VALUE = 1\n",
            "beta/__init__.py": "",
            "beta/value.py": "BETA_VALUE = 2\n",
        },
    )
    state = _full_state(tmp_path)
    candidate = _prepare_candidate_state(state)
    assert candidate.modules
    assert candidate.dependency_graph is not None

    repo_root = tmp_path.resolve()
    protected_sources = {
        path.resolve()
        for path in tmp_path.rglob("*.py")
    }
    assert protected_sources

    def is_protected_source(value) -> bool:
        if isinstance(value, int):
            return False
        try:
            path = Path(value).resolve()
            path.relative_to(repo_root)
        except (TypeError, ValueError, OSError):
            return False
        return path in protected_sources

    original_builtin_open = builtins.open
    original_path_open = Path.open

    def guarded_builtin_open(file, *args, **kwargs):
        if is_protected_source(file):
            pytest.fail(f"layer refresh read unchanged Python source: {file}")
        return original_builtin_open(file, *args, **kwargs)

    def guarded_path_open(path, *args, **kwargs):
        if is_protected_source(path):
            pytest.fail(f"layer refresh read unchanged Python source: {path}")
        return original_path_open(path, *args, **kwargs)

    def reject_parse(*args, **kwargs):
        pytest.fail("layer refresh parsed source instead of using canonical RAM")

    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)
    monkeypatch.setattr(ast, "parse", reject_parse)

    index = _build_canonical_layer_index(
        candidate,
        root_path=tmp_path,
        global_summary=state.layer_information["summary_data"],
        global_hotspots=state.layer_information["hotspots"],
    )

    assert [item["layer"] for item in index] == ["alpha", "beta"]


def test_empty_and_untrusted_layer_views_do_not_fabricate_reports(tmp_path):
    state = RepositoryAnalysisState(layer_information={})
    candidate = _prepare_candidate_state(state)
    _refresh_canonical_layer_information(
        candidate,
        root_path=tmp_path,
    )
    assert candidate.layer_information == {}
    assert state.layer_information == {}
    candidate.layer_information = {"summary_data": None}
    with pytest.raises(RuntimeError, match="summary_data is unavailable"):
        _refresh_canonical_layer_information(
            candidate,
            root_path=tmp_path,
        )
    candidate.layer_information = {"summary_data": {"report_header": {}}}
    with pytest.raises(RuntimeError, match="untrusted canonical facts"):
        _refresh_canonical_layer_information(
            candidate,
            root_path=tmp_path,
        )


@pytest.mark.parametrize("invalid_input", ["consumption", "graph"])
def test_cached_analytics_invalid_inputs_remain_untrusted(tmp_path, invalid_input):
    _write_sources(tmp_path, {"provider.py": "PROVIDER_VALUE = 1\n"})
    state = _full_state(tmp_path)
    assert state.cached_analytics_state == "fresh"
    if invalid_input == "consumption":
        state.artifact_consumption_state = "stale"
    else:
        state.dependency_graph = None
    ensure_cached_analytics(state)
    assert state.cached_analytics_state == "stale"


def test_multilayer_cycle_change_checks_preserved_layer_index(tmp_path):
    _write_sources(
        tmp_path,
        {
            "alpha/__init__.py": "",
            "alpha/a.py": "from alpha import b\nA_VALUE = b.B_VALUE\n",
            "alpha/b.py": "from alpha import a\nB_VALUE = a.A_VALUE\n",
            "beta/__init__.py": "",
            "beta/c.py": "BETA_VALUE = 3\n",
        },
    )
    full = _full_state(tmp_path)
    assert {item["layer"] for item in full.layer_information["layer_index"]} == {
        "alpha",
        "beta",
    }
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    engine = hydrated.engine
    before_index = deepcopy(engine.state.layer_information["layer_index"])
    source = tmp_path / "alpha" / "b.py"
    source.write_text("B_VALUE = 1\n", encoding="utf-8")
    result = engine.update_file(str(source))
    assert result.status == "UPDATED"
    incremental = deepcopy(engine.state)
    oracle = _full_state(tmp_path)
    assert incremental.layer_information["layer_index"] == oracle.layer_information["layer_index"], (
        f"preserved layer_index diverged: before={before_index!r}; "
        f"incremental={incremental.layer_information['layer_index']!r}; "
        f"full={oracle.layer_information['layer_index']!r}; root={tmp_path}"
    )
    _assert_layer_parity(incremental, oracle, tmp_path)
