"""
tests/test_cached_facts_live_analytics.py

Stage 3D.3 / 3D.3a / 3D.3b — CACHED_FACTS LIVE Analytics Integration Tests.
Proves pure RAM execution, production parity, bounded recomputations,
snapshot lifecycle, atomicity, consumer projections, plan-vs-execution equality,
minimal invalidation on pure body edits, certainty/completeness freshness preservation,
and zero-call execution minimality for pure implementation-body changes.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import time
import pytest

from contextor.core.analysis.incremental_engine import (
    IncrementalAnalysisEngine,
    IncrementalUpdateResult,
)
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    FileStateManager,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.live_state.store import save_snapshot, load_snapshot
from contextor.core.reporting_engine.graph_analytics import (
    compute_cached_analytics,
    compute_topology_analytics,
    _classify_layer,
    _classify_visibility,
    _compute_export_degrees,
)
from contextor.core.validator.layers import validate_layer_rules
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp_server import get_module_context
from contextor.mcp.runtime import _live_engines


def _setup_multi_layer_repo(tmp_path: Path):
    """
    Creates a multi-layer repository:
    - contextor.core.domain.models (layer: contract)
    - contextor.core.analysis.service (layer: runtime)
    - contextor.ui.controller (layer: ui)
    - contextor.cli.app (layer: cli)
    """
    domain_dir = tmp_path / "contextor" / "core" / "domain"
    analysis_dir = tmp_path / "contextor" / "core" / "analysis"
    ui_dir = tmp_path / "contextor" / "ui"
    cli_dir = tmp_path / "contextor" / "cli"

    domain_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    ui_dir.mkdir(parents=True, exist_ok=True)
    cli_dir.mkdir(parents=True, exist_ok=True)

    models_py = domain_dir / "models.py"
    models_py.write_text(
        "class Model:\n"
        "    def get_data(self):\n"
        "        return 42\n",
        encoding="utf-8",
    )

    service_py = analysis_dir / "service.py"
    service_py.write_text(
        "import contextor.core.domain.models\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return contextor.core.domain.models.Model().get_data()\n",
        encoding="utf-8",
    )

    controller_py = ui_dir / "controller.py"
    controller_py.write_text(
        "import contextor.core.analysis.service\n"
        "class Controller:\n"
        "    def handle(self):\n"
        "        return contextor.core.analysis.service.Service().run()\n",
        encoding="utf-8",
    )

    cli_py = cli_dir / "app.py"
    cli_py.write_text(
        "import contextor.core.analysis.service\n"
        "def run_cli():\n"
        "    return contextor.core.analysis.service.Service().run()\n",
        encoding="utf-8",
    )

    return models_py, service_py, controller_py, cli_py


def test_pure_ram_cached_analytics_computation():
    """1. compute_cached_analytics runs in pure RAM with zero disk I/O or AST parsing."""
    modules = {
        "contextor.core.analysis.service": Module("contextor.core.analysis.service", "contextor/core/analysis/service.py", "/app/service.py", []),
        "contextor.ui.controller": Module("contextor.ui.controller", "contextor/ui/controller.py", "/app/controller.py", []),
    }
    artifacts = {
        "contextor.core.analysis.service": {"own_symbols": ["Service", "run"]},
        "contextor.ui.controller": {"own_symbols": ["Controller"]},
    }
    artifact_consumption = {
        "contextor.core.analysis.service.Service": {"consumers": ["contextor.ui.controller"]},
    }
    hard_edges = {
        "contextor.ui.controller": {"contextor.core.analysis.service"},
        "contextor.core.analysis.service": set(),
    }

    with patch("builtins.open", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")), \
         patch("ast.parse", side_effect=RuntimeError("AST parsing blocked")):

        cached = compute_cached_analytics(
            modules=modules,
            artifacts=artifacts,
            artifact_consumption=artifact_consumption,
            hard_edges=hard_edges,
        )

    assert cached["module_layers"]["contextor.core.analysis.service"] == "runtime"
    assert cached["module_layers"]["contextor.ui.controller"] == "ui"
    assert cached["export_degree"]["contextor.core.analysis.service"] == 2
    assert cached["export_degree"]["contextor.ui.controller"] == 1
    assert cached["visibility"]["contextor.core.analysis.service"] == "public"  # consumed by ui (cross-layer)
    assert cached["visibility"]["contextor.ui.controller"] == "private" # no consumers


def test_production_parity_for_layer_visibility_export_degree_and_validation():
    """2. Parity against production _classify_layer, _classify_visibility, export_degree, and validator."""
    modules = {
        "contextor.core.domain.models": Module("contextor.core.domain.models", "contextor/core/domain/models.py", "/app/models.py", []),
        "contextor.core.analysis.service": Module("contextor.core.analysis.service", "contextor/core/analysis/service.py", "/app/service.py", []),
        "contextor.ui.controller": Module("contextor.ui.controller", "contextor/ui/controller.py", "/app/controller.py", []),
    }
    artifacts = {
        "contextor.core.domain.models": {"own_symbols": ["Model", "get_data"]},
        "contextor.core.analysis.service": {"own_symbols": ["Service"]},
        "contextor.ui.controller": {"own_symbols": ["Controller"]},
    }
    artifact_consumption = {
        "contextor.core.domain.models.Model": {"consumers": ["contextor.core.analysis.service"]},
        "contextor.core.analysis.service.Service": {"consumers": ["contextor.ui.controller"]},
    }
    hard_edges = {
        "contextor.ui.controller": {"contextor.core.analysis.service"},
        "contextor.core.analysis.service": {"contextor.core.domain.models"},
        "contextor.core.domain.models": set(),
    }

    cached = compute_cached_analytics(modules, artifacts, artifact_consumption, hard_edges)

    # Layer parity
    for mod in modules:
        assert cached["module_layers"][mod] == _classify_layer(mod)

    # Visibility parity
    assert cached["visibility"]["contextor.core.domain.models"] == "public"
    assert cached["visibility"]["contextor.core.analysis.service"] == "public"
    assert cached["visibility"]["contextor.ui.controller"] == "private"

    # Export degree parity
    assert cached["export_degree"]["contextor.core.domain.models"] == 2
    assert cached["export_degree"]["contextor.core.analysis.service"] == 1
    assert cached["export_degree"]["contextor.ui.controller"] == 1

    # Layer validation parity
    pg = ProjectGraph(hard_edges=hard_edges, soft_edges={})
    prod_violations = validate_layer_rules(modules, pg)
    assert len(cached["layer_violations"]) == len(prod_violations)


def test_incremental_lifecycle_and_plan_equality(tmp_path):
    """3. Incremental updates maintain plan-vs-execution equality and update cached analytics."""
    models_py, service_py, controller_py, cli_py = _setup_multi_layer_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    # Initialize all files
    for f in (models_py, service_py, controller_py, cli_py):
        res = engine.update_file(str(f))
        assert "cached_analytics" in res.shadow_plan.patch_families
        assert "cached_analytics" in res.execution_trace["patch_families"]
        assert res.cached_analytics_state == "fresh"

    state = engine.state
    assert state.cached_analytics_state == "fresh"
    assert state.cached_analytics["module_layers"]["contextor.core.analysis.service"] == "runtime"
    assert state.cached_analytics["module_layers"]["contextor.ui.controller"] == "ui"
    assert state.cached_analytics["visibility"]["contextor.core.analysis.service"] == "public"
    assert state.cached_analytics["export_degree"]["contextor.core.domain.models"] == 2

    # A. Import & Body removal: service stops importing and calling Model
    time.sleep(0.05)
    service_py.write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return 100\n",
        encoding="utf-8",
    )
    res_body = engine.update_file(str(service_py))
    assert res_body.status == "UPDATED"
    assert "cached_analytics" in res_body.shadow_plan.patch_families
    assert "cached_analytics" in res_body.execution_trace["patch_families"]
    assert res_body.cached_analytics_state == "fresh"
    # models now has no consumers -> private
    assert engine.state.cached_analytics["visibility"]["contextor.core.domain.models"] == "private"

    # B. Definition Addition in models.py
    time.sleep(0.05)
    models_py.write_text(
        "class Model:\n"
        "    def get_data(self): return 42\n"
        "def new_helper(): pass\n",
        encoding="utf-8",
    )
    res_def = engine.update_file(str(models_py))
    assert res_def.status == "UPDATED"
    assert res_def.cached_analytics_state == "fresh"
    assert engine.state.cached_analytics["export_degree"]["contextor.core.domain.models"] == 3

    # C. Pure No-Op
    res_noop = engine.update_file(str(models_py))
    assert res_noop.status == "UNCHANGED"
    assert res_noop.cached_analytics_state == "fresh"
    assert res_noop.shadow_plan is None


def test_layer_violation_detection_and_resolution(tmp_path):
    """4. Layer-rule violations are detected on illegal import and cleared on fix."""
    cli_dir = tmp_path / "cli"
    ui_dir = tmp_path / "ui"
    cli_dir.mkdir(parents=True, exist_ok=True)
    ui_dir.mkdir(parents=True, exist_ok=True)

    app_py = cli_dir / "app.py"
    app_py.write_text("def run(): pass\n", encoding="utf-8")

    view_py = ui_dir / "view.py"
    view_py.write_text("def render(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(app_py))
    engine.update_file(str(view_py))

    assert len(engine.state.cached_analytics["layer_violations"]) == 0

    # Illegal import: cli.app imports ui.view (forbidden by FORBIDDEN_LAYER_RULES: cli -> ui)
    time.sleep(0.05)
    app_py.write_text(
        "import ui.view\n"
        "def run():\n"
        "    ui.view.render()\n",
        encoding="utf-8",
    )
    res = engine.update_file(str(app_py))
    assert res.status == "UPDATED"
    assert res.cached_analytics_state == "fresh"

    violations = engine.state.cached_analytics["layer_violations"]
    assert len(violations) > 0
    assert any("cli.app -> ui.view" in v["message"] for v in violations)

    # Fix the violation
    time.sleep(0.05)
    app_py.write_text("def run(): pass\n", encoding="utf-8")
    res_fix = engine.update_file(str(app_py))
    assert res_fix.status == "UPDATED"
    assert len(engine.state.cached_analytics["layer_violations"]) == 0


class _CachedAnalyticsLegacySnapshotState:
    """Mock state without cached_analytics or topology fields."""
    def __init__(self, modules, graph, metrics):
        self.modules = modules
        self.dependency_graph = graph
        self.metrics = metrics
        self.artifacts = {"contextor.core.analysis.mod": {"own_symbols": ["foo"]}}
        self.artifact_consumption = {}


def test_snapshot_lifecycle_and_consumer_projection(tmp_path):
    """5. Snapshot persistence, legacy reconstruction in RAM, and MCP projection guard."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    mod_dir = tmp_path / "contextor" / "core" / "analysis"
    mod_dir.mkdir(parents=True, exist_ok=True)
    mod_file = mod_dir / "mod.py"
    mod_file.write_text("def foo(): pass\n", encoding="utf-8")

    modules = {"contextor.core.analysis.mod": Module("contextor.core.analysis.mod", "contextor/core/analysis/mod.py", str(mod_file), [])}
    graph = ProjectGraph({"contextor.core.analysis.mod": set()}, {"contextor.core.analysis.mod": set()})
    metrics = compute_graph_metrics({"contextor.core.analysis.mod": set()}, {"contextor.core.analysis.mod": set()})

    # 1. Legacy snapshot reconstruction
    leg_state = _CachedAnalyticsLegacySnapshotState(modules, graph, metrics)
    save_snapshot(leg_state, cache_dir, "legacy_snap", repo_id="r1", root_path=str(tmp_path))

    loaded_leg, _ = load_snapshot(cache_dir, expected_state_id="legacy_snap")
    assert loaded_leg.cached_analytics_state == "deferred"

    with patch("builtins.open", side_effect=OSError("Disk read blocked")):
        engine = IncrementalAnalysisEngine(
            loaded_leg,
            PersistentIdentityRegistry(str(tmp_path)),
            FileStateManager(str(cache_dir)),
            str(tmp_path),
        )

    # Reconstructed to fresh with zero disk reads
    assert engine.state.cached_analytics_state == "fresh"
    assert "contextor.core.analysis.mod" in engine.state.cached_analytics["module_layers"]
    assert engine.state.cached_analytics["export_degree"]["contextor.core.analysis.mod"] == 1

    # 2. Consumer projection in MCP get_module_context
    root_resolved = Path(tmp_path).expanduser().resolve()
    _live_engines[str(root_resolved)] = engine

    fn = getattr(get_module_context, "fn", get_module_context)
    res_raw = fn(str(tmp_path), "contextor.core.analysis.mod", compact=True)
    res = json.loads(res_raw)
    assert res["metrics"]["layer"] == engine.state.cached_analytics["module_layers"]["contextor.core.analysis.mod"]
    assert res["metrics"]["visibility"] == engine.state.cached_analytics["visibility"]["contextor.core.analysis.mod"]
    assert res["metrics"]["export_degree"] == 1

    # 3. Stale snapshot guard
    engine.state.cached_analytics_state = "stale"
    save_snapshot(engine.state, cache_dir, "stale_snap", repo_id="r1", root_path=str(tmp_path))

    loaded_stale, _ = load_snapshot(cache_dir, expected_state_id="stale_snap")
    assert loaded_stale.cached_analytics_state == "stale"

    engine_stale = IncrementalAnalysisEngine(
        loaded_stale,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    assert engine_stale.state.cached_analytics_state == "stale"


def test_atomicity_and_isolation_on_failure(tmp_path):
    """6. Failure during cached analytics computation does not corrupt published state."""
    models_py, service_py, _, _ = _setup_multi_layer_repo(tmp_path)
    cache_dir = tmp_path / "cache"

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(models_py))
    engine.update_file(str(service_py))

    old_cached = dict(engine.state.cached_analytics)
    old_state_obj = engine.state

    # Modify service.py to cause a mock failure inside compute_cached_analytics
    time.sleep(0.05)
    service_py.write_text("def broken(): pass\n", encoding="utf-8")

    with patch("contextor.core.reporting_engine.graph_analytics.compute_cached_analytics", side_effect=RuntimeError("Simulated failure")):
        with pytest.raises(RuntimeError, match="Simulated failure"):
            engine.update_file(str(service_py))

    # Published state must be completely uncorrupted
    assert engine.state.cached_analytics == old_cached
    assert engine.state is old_state_obj


def test_pure_body_change_no_cached_analytics_invalidation(tmp_path):
    """7. Stage 3D.3a: Pure body implementation edit (return 10 -> return 1000) must not schedule cached_analytics."""
    f = tmp_path / "worker.py"
    f.write_text("def compute():\n    return 10\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    res_init = engine.update_file(str(f))
    assert res_init.cached_analytics_state == "fresh"

    old_cached = dict(engine.state.cached_analytics)

    # Pure body implementation edit
    time.sleep(0.15)
    f.write_text("def compute():\n    return 1000000\n", encoding="utf-8")

    with patch("contextor.core.reporting_engine.graph_analytics.compute_cached_analytics") as mock_compute:
        res = engine.update_file(str(f))

        # Pure body change with unchanged imports/exports/usages is UNCHANGED
        assert res.status in ("UNCHANGED", "UPDATED")
        if res.shadow_plan:
            assert "cached_analytics" not in res.shadow_plan.patch_families
        assert "cached_analytics" not in res.execution_trace.get("patch_families", ())
        assert mock_compute.call_count == 0
        assert engine.state.cached_analytics == old_cached
        assert engine.state.cached_analytics_state == "fresh"


def test_runtime_unresolved_certainty_preserves_freshness(tmp_path):
    """8. Stage 3D.3a: runtime_unresolved certainty + complete refresh must keep cached_analytics_state fresh."""
    f = tmp_path / "dyn.py"
    f.write_text("def eval_code(code):\n    return eval(code)\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f))

    # Mock RefreshPlanner to return complete + runtime_unresolved
    plan_unresolved = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("definitions", "module_usages", "artifact_consumption"),
        graph_recomputations=(),
        refresh_completeness="complete",
        semantic_certainty="runtime_unresolved",
        reason="Dynamic eval inside function",
    )

    with patch("contextor.core.analysis.refresh_planner.RefreshPlanner.plan_refresh", return_value=plan_unresolved):
        time.sleep(0.15)
        f.write_text("def eval_code(code):\n    return eval(code) + 1000\n", encoding="utf-8")
        engine.state_manager._state.pop(str(f), None)
        res = engine.update_file(str(f))

    assert res.shadow_plan.refresh_completeness == "complete"
    assert res.shadow_plan.semantic_certainty == "runtime_unresolved"
    assert res.cached_analytics_state == "fresh"
    assert engine.state.cached_analytics_state == "fresh"


def test_requires_resync_invalidates_cached_analytics_freshness(tmp_path):
    """9. Stage 3D.3a: requires_resync completeness must set cached_analytics_state to stale."""
    f = tmp_path / "mod.py"
    f.write_text("def run(): pass\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f))
    assert engine.state.cached_analytics_state == "fresh"

    plan_resync = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("definitions", "module_usages"),
        graph_recomputations=(),
        refresh_completeness="requires_resync",
        semantic_certainty="statically_resolved",
        reason="Corrupted state requires resync",
    )

    with patch("contextor.core.analysis.refresh_planner.RefreshPlanner.plan_refresh", return_value=plan_resync):
        time.sleep(0.15)
        f.write_text("def run(): return 1000\n", encoding="utf-8")
        engine.state_manager._state.pop(str(f), None)
        res = engine.update_file(str(f))

    assert res.shadow_plan.refresh_completeness == "requires_resync"
    assert res.cached_analytics_state == "stale"
    assert engine.state.cached_analytics_state == "stale"


def test_stage3d3b_pure_body_minimal_execution_and_full_static_parity(tmp_path):
    """10. Stage 3D.3b: Pure body edit produces minimal plan (), 0-call execution, and 100% full static parity."""
    f = tmp_path / "calculator.py"
    f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f))

    # Edit pure body: return a + b -> return a + b + 0
    time.sleep(0.15)
    f.write_text("def add(a, b):\n    return a + b + 0\n", encoding="utf-8")
    engine.state_manager._state.pop(str(f), None)

    with patch.object(engine.registry, "sync_with_workspace") as mock_reg_sync, \
         patch("contextor.core.reporting_engine.graph_analytics.compute_cached_analytics") as mock_cached, \
         patch("contextor.core.graph.metrics.compute_graph_metrics") as mock_metrics:

        res = engine.update_file(str(f))

    assert res.shadow_plan.patch_families == ()
    assert res.shadow_plan.reparse_modules == ()
    assert res.shadow_plan.recompute_modules == ()
    assert res.shadow_plan.graph_recomputations == ()
    assert res.execution_trace["patch_families"] == ()
    assert res.execution_trace["graph_recomputations"] == ()

    # Zero-call execution minimality
    assert mock_reg_sync.call_count == 0
    assert mock_cached.call_count == 0
    assert mock_metrics.call_count == 0

    # Static rebuild parity check
    oracle_engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir / "oracle")),
        str(tmp_path),
    )
    oracle_engine.update_file(str(f))

    assert set(engine.state.modules.keys()) == set(oracle_engine.state.modules.keys())
    assert set(engine.state.artifacts.keys()) == set(oracle_engine.state.artifacts.keys())
    assert engine.state.cached_analytics == oracle_engine.state.cached_analytics
    assert engine.state.cached_analytics_state == oracle_engine.state.cached_analytics_state == "fresh"


def test_stage3d3c_call_retarget_minimal_execution_counts_and_parity(tmp_path):
    """11. Stage 3D.3c: Pure call-retarget edit produces ('module_usages', 'artifact_consumption', 'cached_analytics') with 0 definitions patch."""
    target_py = tmp_path / "target.py"
    target_py.write_text(
        "def foo():\n"
        "    return 1\n"
        "def bar():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    consumer_py = tmp_path / "consumer.py"
    consumer_py.write_text(
        "from target import foo, bar\n"
        "def run():\n"
        "    return foo()\n",
        encoding="utf-8",
    )

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(target_py))
    engine.update_file(str(consumer_py))

    old_consumer_artifacts = engine.state.artifacts["consumer"]

    # Retarget call: foo() -> bar() (no definition change, no import change)
    time.sleep(0.15)
    consumer_py.write_text(
        "from target import foo, bar\n"
        "def run():\n"
        "    return bar()\n",
        encoding="utf-8",
    )
    engine.state_manager._state.pop(str(consumer_py), None)

    with patch.object(engine.registry, "sync_with_workspace") as mock_reg_sync, \
         patch("contextor.core.graph.metrics.compute_graph_metrics") as mock_metrics:

        res = engine.update_file(str(consumer_py))

    # Shadow plan assertions
    assert res.shadow_plan.reparse_modules == ()
    assert res.shadow_plan.recompute_modules == ()
    assert res.shadow_plan.graph_recomputations == ()
    assert res.shadow_plan.patch_families == ("module_usages", "artifact_consumption", "cached_analytics")
    assert "definitions" not in res.shadow_plan.patch_families
    assert "identity_registry" not in res.shadow_plan.patch_families

    # Execution trace assertions
    assert res.execution_trace["patch_families"] == ("module_usages", "artifact_consumption", "cached_analytics")
    assert res.execution_trace["graph_recomputations"] == ()

    # Zero unnecessary calls
    assert mock_reg_sync.call_count == 0
    assert mock_metrics.call_count == 0

    # Definitions object in state remains exact same reference or identical
    assert engine.state.artifacts["consumer"]["own_symbols"] == old_consumer_artifacts["own_symbols"]

    # Full static rebuild parity check
    oracle_engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir / "oracle_c")),
        str(tmp_path),
    )
    oracle_engine.update_file(str(target_py))
    oracle_engine.update_file(str(consumer_py))

    assert set(engine.state.modules.keys()) == set(oracle_engine.state.modules.keys())
    assert set(engine.state.artifacts.keys()) == set(oracle_engine.state.artifacts.keys())
    assert engine.state.cached_analytics == oracle_engine.state.cached_analytics
    assert engine.state.cached_analytics_state == oracle_engine.state.cached_analytics_state == "fresh"
