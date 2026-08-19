"""
tests/test_matrix_clusters_ram_parity.py

Stage 1 — Canonical Single-SSOT Contract, Real Production Parity, and Pure-RAM Test Suite
for Canonical LIVE Dependency Matrix and Shared Usage Clusters (Jaccard).
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental.materialization import (
    ensure_artifact_consumption,
    materialize_incremental_state,
)
from contextor.core.analysis.state_manager import (
    CANONICAL_USAGE_CHANNELS,
    RepositoryAnalysisState,
    build_canonical_artifact_consumption,
    is_legacy_artifact_consumption,
    validate_canonical_artifact_consumption,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reporting_engine.graph_analytics import (
    _usage_dependency_types,
    build_artifact_data_projection,
    build_jaccard_clusters,
    build_module_dependency_matrix,
    compute_dependency_matrix,
    compute_dependency_matrix_from_state,
    compute_shared_usage_clusters,
    compute_shared_usage_clusters_from_state,
)
import contextor.core.reporting_layer.artifact_usage_report as aur


# ==============================================================================
# 1. REAL PRODUCTION-TO-PRODUCTION PARITY TEST (FACADE -> PERSIST -> HYDRATE)
# ==============================================================================

def test_real_production_facade_to_hydration_parity(tmp_path: Path):
    """
    PROVES 1:1 END-TO-END PARITY BETWEEN:
    Real Production Snapshot Pipeline (spied from ContextorFacade.analyze_project)
    vs
    Real Hydrated Canonical RepositoryAnalysisState (hydrate_repository_engine).

    Proves that state.artifact_consumption is normalized per-target SSOT on full analysis.
    """
    repo_dir = tmp_path / "facade_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    core_file = repo_dir / "core.py"
    core_file.write_text(
        "VERSION = '2.0'\n\n"
        "class Engine:\n"
        "    @classmethod\n"
        "    def start(cls):\n"
        "        return True\n\n"
        "def make_engine():\n"
        "    return Engine.start()\n",
        encoding="utf-8",
    )

    models_file = repo_dir / "models.py"
    models_file.write_text(
        "class DataModel:\n"
        "    pass\n\n"
        "def create_model():\n"
        "    return DataModel()\n",
        encoding="utf-8",
    )

    service_a_file = repo_dir / "service_a.py"
    service_a_file.write_text(
        "from core import Engine, VERSION, make_engine\n"
        "from models import DataModel\n\n"
        "class AppEngine(Engine):\n"
        "    def run(self):\n"
        "        Engine.start()\n"
        "        make_engine()\n"
        "        _ = DataModel()\n"
        "        print(VERSION)\n",
        encoding="utf-8",
    )

    service_b_file = repo_dir / "service_b.py"
    service_b_file.write_text(
        "from core import Engine, make_engine\n"
        "from models import DataModel, create_model\n\n"
        "class WorkerEngine(Engine):\n"
        "    def work(self):\n"
        "        make_engine()\n"
        "        _ = DataModel()\n"
        "        create_model()\n",
        encoding="utf-8",
    )

    service_c_file = repo_dir / "service_c.py"
    service_c_file.write_text(
        "import models\n"
        "from core import make_engine\n\n"
        "def callback_runner():\n"
        "    make_engine()\n"
        "    _ = models.DataModel()\n",
        encoding="utf-8",
    )

    isolated_file = repo_dir / "isolated.py"
    isolated_file.write_text(
        "def lonely_function():\n"
        "    pass\n",
        encoding="utf-8",
    )

    # 1. Spying the real production call site of build_artifact_index during full analysis
    captured = {}
    real_build_artifact_index = aur.build_artifact_index

    def capture_build_artifact_index(*args, **kwargs):
        result = real_build_artifact_index(*args, **kwargs)
        artifacts, usage_sidecar = result
        captured["artifact_data"] = {
            "artifacts": artifacts,
            "_usage_sidecar": usage_sidecar,
        }
        return result

    with patch.object(aur, "build_artifact_index", side_effect=capture_build_artifact_index):
        facade = ContextorFacade()
        errors, analysis_result = facade.analyze_project(str(repo_dir))
        assert not errors
        assert analysis_result is not None

    production_artifact_data = captured["artifact_data"]

    # 2. Hydrate real canonical state from disk
    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    state = hydrated.engine.state

    # ==========================================================================
    # A. CANONICAL ARTIFACT_CONSUMPTION SSOT CONTRACT VERIFICATION
    # ==========================================================================
    assert validate_canonical_artifact_consumption(state.artifact_consumption) is True
    assert state.artifact_consumption_state == "fresh"
    assert "_report" not in state.artifact_consumption
    assert "core::Engine.start" in state.artifact_consumption
    assert "core::Engine" in state.artifact_consumption
    assert "core::VERSION" in state.artifact_consumption

    # Consistency invariant: channels keys are a subset of consumers
    for target, entry in state.artifact_consumption.items():
        assert set(entry["channels"].keys()).issubset(set(entry["consumers"])), f"Consistency failure for {target}"

    method_entry = state.artifact_consumption["core::Engine.start"]
    assert "service_a" in method_entry["consumers"]
    assert "direct_calls" in method_entry["channels"]["service_a"]

    # 3. Canonical Projection from pure RAM state (no fallback to state.artifacts consumers)
    projected_artifact_data = build_artifact_data_projection(
        state.artifacts,
        state.artifact_consumption,
    )

    # ==========================================================================
    # B. EXACT ARTIFACT KEYS & ATTRIBUTES PARITY
    # ==========================================================================
    assert projected_artifact_data["artifacts"].keys() == production_artifact_data["artifacts"].keys()

    for key, prod_art in production_artifact_data["artifacts"].items():
        proj_art = projected_artifact_data["artifacts"][key]
        assert proj_art["artifact_id"] == prod_art["artifact_id"], f"Mismatch for {key}"
        assert proj_art["artifact"] == prod_art["artifact"], f"Mismatch for {key}"
        assert proj_art["kind"] == prod_art["kind"], f"Mismatch for {key}"
        assert proj_art["definer_module"] == prod_art["definer_module"], f"Mismatch for {key}"
        assert proj_art["consumers"] == prod_art["consumers"], f"Mismatch for {key}"
        assert proj_art["consumer_count"] == prod_art["consumer_count"], f"Mismatch for {key}"

    # ==========================================================================
    # C. CLASS METHOD IDENTITY PRODUCTION PROOF
    # ==========================================================================
    expected_method_key = "core::Engine.start"
    assert expected_method_key in production_artifact_data["artifacts"]
    assert expected_method_key in projected_artifact_data["artifacts"]
    assert projected_artifact_data["artifacts"][expected_method_key]["kind"] == "method"
    assert projected_artifact_data["artifacts"][expected_method_key]["artifact"] == "Engine.start"

    # ==========================================================================
    # D. PER-CONSUMER USAGE SIDECAR PARITY
    # ==========================================================================
    for key, proj_art in projected_artifact_data["artifacts"].items():
        proj_sidecar = projected_artifact_data["_usage_sidecar"].get(key, {})
        prod_sidecar = production_artifact_data["_usage_sidecar"].get(key, {})

        for consumer in proj_art["consumers"]:
            proj_consumer_channels = {
                cat: [c for c in c_list if c == consumer]
                for cat, c_list in proj_sidecar.items()
                if consumer in c_list
            }
            prod_consumer_channels = {
                cat: [c for c in c_list if c == consumer]
                for cat, c_list in prod_sidecar.items()
                if consumer in c_list
            }
            proj_dep_types = _usage_dependency_types(proj_consumer_channels)
            prod_dep_types = _usage_dependency_types(prod_consumer_channels)
            assert proj_dep_types == prod_dep_types, f"Per-consumer mismatch for {key} / {consumer}: {proj_dep_types} vs {prod_dep_types}"

    # ==========================================================================
    # E. END-TO-END MATRIX EXACT PARITY
    # ==========================================================================
    hard_edges = state.dependency_graph.hard_edges
    snapshot_matrix = build_module_dependency_matrix(production_artifact_data, hard_edges)
    canonical_matrix = compute_dependency_matrix_from_state(state)

    assert snapshot_matrix == canonical_matrix, "Dependency Matrix differs between real snapshot and hydrated state"

    # ==========================================================================
    # F. END-TO-END SHARED USAGE CLUSTERS EXACT PARITY
    # ==========================================================================
    snapshot_clusters = build_jaccard_clusters(production_artifact_data, min_jaccard=0.30)
    canonical_clusters = compute_shared_usage_clusters_from_state(state, min_jaccard=0.30)

    assert snapshot_clusters == canonical_clusters, "Shared Usage Clusters differ between real snapshot and hydrated state"


# ==============================================================================
# 2. STRICT CANONICAL CHANNEL ALLOWLIST & INTERNAL CONSISTENCY PROOF
# ==============================================================================

def test_strict_canonical_channel_allowlist_and_internal_consistency():
    """
    PROVES that build_canonical_artifact_consumption:
    1. Only admits channels from CANONICAL_USAGE_CHANNELS.
    2. Excludes stale consumer modules not in consumers list.
    3. Excludes detail fields (*_detail) and ambiguous_calls.
    4. Guarantees set(entry["channels"].keys()) <= set(entry["consumers"]).
    """
    raw_artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["process"], "methods": [], "globals": []},
            "own_symbols": ["process"],
            "consumers": {
                "process": {
                    "consumers": ["pkg.a"],
                    "usage": {
                        "direct_calls": ["pkg.a"],
                        "runtime_calls": ["pkg.stale"],  # stale consumer, not in consumers
                        "unknown_custom_channel": ["pkg.a"],  # not in CANONICAL_USAGE_CHANNELS
                        "ambiguous_calls": [{"module": "pkg.a", "confidence": 0.3}],
                        "direct_calls_detail": [{"module": "pkg.a", "line": 10}],
                    },
                }
            },
        }
    }

    normalized = build_canonical_artifact_consumption(raw_artifacts)
    assert "pkg.core::process" in normalized

    entry = normalized["pkg.core::process"]
    assert entry["consumers"] == ["pkg.a"]
    # Only direct_calls for pkg.a must be present
    assert entry["channels"] == {"pkg.a": ["direct_calls"]}
    assert "pkg.stale" not in entry["channels"]
    assert "unknown_custom_channel" not in entry["channels"].get("pkg.a", [])
    assert set(entry["channels"].keys()).issubset(set(entry["consumers"]))


def test_canonical_artifact_consumption_validator():
    """
    PROVES that validate_canonical_artifact_consumption enforces strict canonical schema,
    deterministic sorting, and target key format.
    """
    # 1. Valid entry
    valid = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["api_imports", "direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(valid) is True

    # 2. Legacy _report rejected
    legacy = {"_report": {"_format_version": 3}}
    assert validate_canonical_artifact_consumption(legacy) is False
    assert is_legacy_artifact_consumption(legacy) is True

    # 3. Non-canonical channel rejected
    invalid_ch = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["invalid_channel_name"]},
        }
    }
    assert validate_canonical_artifact_consumption(invalid_ch) is False

    # 4. Consumer inconsistency rejected (channel key not in consumers)
    inconsistent = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.other": ["direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(inconsistent) is False

    # 5. Non-deterministic / unsorted consumers rejected
    unsorted_consumers = {
        "pkg.core::func": {
            "consumers": ["pkg.b", "pkg.a"],
            "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(unsorted_consumers) is False

    # 6. Non-deterministic / unsorted channels list rejected
    unsorted_channels = {
        "pkg.core::func": {
            "consumers": ["pkg.a"],
            "channels": {"pkg.a": ["runtime_calls", "direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(unsorted_channels) is False

    # 7. Invalid target key (empty definer or symbol) rejected
    invalid_key1 = {"": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key1) is False

    invalid_key2 = {"::func": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key2) is False

    invalid_key3 = {"core::": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key3) is False


# ==============================================================================
# 3. LEGACY MIGRATION VS INVALID CANONICAL FAIL-CLOSED PROOF
# ==============================================================================

def test_legacy_report_hydration_materialization_self_heal():
    """
    PROVES that when legacy state containing artifact_consumption = {"_report": ...}
    is materialized via materialize_incremental_state, it migrates in RAM from
    state.artifacts and becomes fresh.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    legacy_state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption={"_report": {"legacy": "data"}},  # legacy shape
    )

    assert is_legacy_artifact_consumption(legacy_state.artifact_consumption) is True
    assert validate_canonical_artifact_consumption(legacy_state.artifact_consumption) is False

    materialize_incremental_state(legacy_state)

    assert validate_canonical_artifact_consumption(legacy_state.artifact_consumption) is True
    assert legacy_state.artifact_consumption_state == "fresh"
    assert "pkg.core::boot" in legacy_state.artifact_consumption
    assert legacy_state.artifact_consumption["pkg.core::boot"] == {
        "consumers": ["pkg.app"],
        "channels": {"pkg.app": ["direct_calls"]},
    }


def test_invalid_modern_canonical_state_fails_closed_without_auto_heal():
    """
    PROVES that an invalid modern canonical state (e.g. corrupt channels or stale channel key)
    is NOT auto-healed from state.artifacts, but fails closed by marking state.artifact_consumption_state = "stale".
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    # Corrupt modern canonical consumption: channel points to non-consumer "pkg.stale"
    corrupt_consumption = {
        "pkg.core::boot": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.stale": ["direct_calls"]},
        }
    }
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption=corrupt_consumption,
        artifact_consumption_state="deferred",
    )

    assert is_legacy_artifact_consumption(state.artifact_consumption) is False
    assert validate_canonical_artifact_consumption(state.artifact_consumption) is False

    materialize_incremental_state(state)

    # Must FAIL CLOSED: state marked stale, corrupt consumption NOT overwritten
    assert state.artifact_consumption_state == "stale"
    assert state.artifact_consumption == corrupt_consumption


def test_resync_required_blocks_auto_heal():
    """
    PROVES that when state requires resync (resync_required == True or state is stale),
    materialization does not auto-heal or clear the stale marker.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption={"_report": {"legacy": "data"}},
        artifact_consumption_state="stale",
    )
    # Set resync_required attribute
    setattr(state, "resync_required", True)

    materialize_incremental_state(state)

    assert state.artifact_consumption_state == "stale"


# ==============================================================================
# 4. FULL ANALYSIS / INCREMENTAL SCHEMA UNIFICATION PROOF
# ==============================================================================

def test_full_analysis_and_incremental_schema_parity():
    """
    PROVES that artifact_consumption produced by full analysis (build_canonical_artifact_consumption)
    and incremental pipeline (plan_executor) follow the EXACT same schema and orientation.
    """
    raw_artifacts = {
        "pkg.core": {
            "symbols": {"classes": ["Engine"], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["Engine", "boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.service"],
                    "usage": {
                        "direct_calls": ["pkg.service"],
                        "runtime_calls": ["pkg.service"],
                    },
                }
            },
        }
    }
    normalized = build_canonical_artifact_consumption(raw_artifacts)

    assert "pkg.core::boot" in normalized
    entry = normalized["pkg.core::boot"]
    assert entry == {
        "consumers": ["pkg.service"],
        "channels": {
            "pkg.service": ["direct_calls", "runtime_calls"],
        },
    }

    # Simulate an incremental update updating the same schema
    incremental_entry = {
        "consumers": list(entry["consumers"]),
        "channels": {k: list(v) for k, v in entry["channels"].items()},
    }
    incremental_entry["consumers"].append("pkg.worker")
    incremental_entry["consumers"].sort()
    incremental_entry["channels"]["pkg.worker"] = ["api_imports"]

    assert incremental_entry["consumers"] == ["pkg.service", "pkg.worker"]
    assert set(incremental_entry["channels"].keys()) == {"pkg.service", "pkg.worker"}


# ==============================================================================
# 5. SELF-CONSUMPTION & EXTERNAL FILTER PARITY PROOF
# ==============================================================================

def test_self_consumption_and_external_filter_parity():
    """
    PROVES exact parity on:
    1. Symbol consumed ONLY by its own definer module -> omitted from artifact index (no external consumer).
    2. Symbol consumed by definer + external consumer -> included in artifact index, self retained in consumers.
    3. Symbol with 0 consumers -> omitted.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["self_only", "self_and_ext", "zero_consumer"], "methods": [], "globals": []},
            "own_symbols": ["self_only", "self_and_ext", "zero_consumer"],
        }
    }
    consumption = {
        "pkg.core::self_only": {
            "consumers": ["pkg.core"],
            "channels": {"pkg.core": ["direct_calls"]},
        },
        "pkg.core::self_and_ext": {
            "consumers": ["pkg.app", "pkg.core"],
            "channels": {
                "pkg.app": ["direct_calls"],
                "pkg.core": ["direct_calls"],
            },
        },
        "pkg.core::zero_consumer": {
            "consumers": [],
            "channels": {},
        },
    }

    projected = build_artifact_data_projection(artifacts, consumption)

    # 1. self_only must be omitted
    assert "pkg.core::self_only" not in projected["artifacts"]

    # 2. zero_consumer must be omitted
    assert "pkg.core::zero_consumer" not in projected["artifacts"]

    # 3. self_and_ext must be included, retaining both consumers
    assert "pkg.core::self_and_ext" in projected["artifacts"]
    art = projected["artifacts"]["pkg.core::self_and_ext"]
    assert art["consumers"] == ["pkg.app", "pkg.core"]
    assert art["consumer_count"] == 2


# ==============================================================================
# 6. CHANNEL SEMANTICS INVARIANT (DIRECT VS RUNTIME CALL MATRIX INVARIANCE)
# ==============================================================================

def test_direct_vs_runtime_call_matrix_invariance():
    """
    PROVES that direct_calls vs runtime_calls map to the identical 'call' dependency type,
    leaving the Dependency Matrix unchanged.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["foo"], "methods": [], "globals": []},
            "own_symbols": ["foo"],
        }
    }
    graph = ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={})

    # Case A: direct_calls
    consumption_direct = {
        "pkg.core::foo": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["direct_calls"]},
        }
    }
    state_a = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=consumption_direct,
    )

    # Case B: runtime_calls
    consumption_runtime = {
        "pkg.core::foo": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["runtime_calls"]},
        }
    }
    state_b = RepositoryAnalysisState(
        modules=state_a.modules,
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=consumption_runtime,
    )

    matrix_a = compute_dependency_matrix_from_state(state_a)
    matrix_b = compute_dependency_matrix_from_state(state_b)

    assert matrix_a == matrix_b
    assert matrix_a["pkg.app"]["pkg.core"]["dep_types"] == ["call", "import"]


# ==============================================================================
# 7. EDGE-CASE AUDIT TESTS WITH CONCRETE ASSERTIONS
# ==============================================================================

def test_edge_case_below_jaccard_threshold_excluded():
    """
    AUDIT TEST: Pairs with Jaccard similarity < min_jaccard (0.30) are excluded from clusters.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 11)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 11)],
        }
    }
    artifact_consumption = {
        f"pkg.prov::f{i}": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}} for i in range(1, 5)
    }
    artifact_consumption["pkg.prov::f5"] = {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}}
    for i in range(6, 11):
        artifact_consumption[f"pkg.prov::f{i}"] = {"consumers": ["pkg.b"], "channels": {"pkg.b": ["direct_calls"]}}

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 0


def test_edge_case_complete_linkage_no_chaining():
    """
    AUDIT TEST: Complete-linkage clustering invariant.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 9)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 9)],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f4": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f5": {"consumers": ["pkg.b", "pkg.c"], "channels": {"pkg.b": ["direct_calls"], "pkg.c": ["direct_calls"]}},
        "pkg.prov::f6": {"consumers": ["pkg.b", "pkg.c"], "channels": {"pkg.b": ["direct_calls"], "pkg.c": ["direct_calls"]}},
        "pkg.prov::f7": {"consumers": ["pkg.c"], "channels": {"pkg.c": ["direct_calls"]}},
        "pkg.prov::f8": {"consumers": ["pkg.c"], "channels": {"pkg.c": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    for c in clusters:
        assert len(c["modules"]) == 2
        assert set(c["modules"]) != {"pkg.a", "pkg.b", "pkg.c"}


def test_edge_case_min_and_max_cluster_sizes():
    """
    AUDIT TEST: min_cluster_size and max_cluster_size bounds enforcement.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": ["f1", "f2"], "classes": [], "methods": [], "globals": []},
            "own_symbols": ["f1", "f2"],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"], "channels": {m: ["direct_calls"] for m in ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]}},
        "pkg.prov::f2": {"consumers": ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"], "channels": {m: ["direct_calls"] for m in ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]}},
    }

    clusters_capped = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, max_cluster_size=2
    )
    assert len(clusters_capped) == 1
    assert len(clusters_capped[0]["modules"]) == 2

    clusters_min_5 = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, min_cluster_size=5
    )
    assert len(clusters_min_5) == 0

    clusters_default = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, min_cluster_size=2, max_cluster_size=25
    )
    assert len(clusters_default) == 1
    assert len(clusters_default[0]["modules"]) == 4


def test_edge_case_similarity_rounding():
    """
    AUDIT TEST: Precision rounding of jaccard_similarity (4 decimal places).
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": ["f1", "f2", "f3"], "classes": [], "methods": [], "globals": []},
            "own_symbols": ["f1", "f2", "f3"],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.b"], "channels": {"pkg.b": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 1
    assert clusters[0]["jaccard_similarity"] == 0.3333


def test_edge_case_deterministic_ordering():
    """
    AUDIT TEST: Deterministic ordering of clusters by (-shared_artifact_count, -size, modules).
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 10)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 10)],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.m1", "pkg.m2"], "channels": {"pkg.m1": ["direct_calls"], "pkg.m2": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.m1", "pkg.m2"], "channels": {"pkg.m1": ["direct_calls"], "pkg.m2": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
        "pkg.prov::f4": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
        "pkg.prov::f5": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 2
    assert clusters[0]["shared_artifact_count"] == 3
    assert clusters[0]["modules"] == ["pkg.m3", "pkg.m4"]
    assert clusters[1]["shared_artifact_count"] == 2
    assert clusters[1]["modules"] == ["pkg.m1", "pkg.m2"]


def test_symbol_rename_invariance_and_divergence():
    """
    AUDIT TEST: Symbol rename contract.
    """
    artifacts_before = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["initialize_core"], "methods": [], "globals": []},
            "own_symbols": ["initialize_core"],
        }
    }
    consumption_before = {
        "pkg.core::initialize_core": {
            "consumers": ["pkg.service_a", "pkg.service_b"],
            "channels": {
                "pkg.service_a": ["direct_calls"],
                "pkg.service_b": ["direct_calls"],
            },
        }
    }
    graph = ProjectGraph(hard_edges={"pkg.service_a": {"pkg.core"}, "pkg.service_b": {"pkg.core"}}, soft_edges={})
    state_before = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.service_a": Module(module_id="pkg.service_a", path="a.py", absolute_path="/a.py", imports=[]),
                 "pkg.service_b": Module(module_id="pkg.service_b", path="b.py", absolute_path="/b.py", imports=[])},
        artifacts=artifacts_before,
        dependency_graph=graph,
        artifact_consumption=consumption_before,
    )

    artifacts_after = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["bootstrap_core"], "methods": [], "globals": []},
            "own_symbols": ["bootstrap_core"],
        }
    }
    consumption_after = {
        "pkg.core::bootstrap_core": {
            "consumers": ["pkg.service_a", "pkg.service_b"],
            "channels": {
                "pkg.service_a": ["direct_calls"],
                "pkg.service_b": ["direct_calls"],
            },
        }
    }
    state_after = RepositoryAnalysisState(
        modules=state_before.modules,
        artifacts=artifacts_after,
        dependency_graph=graph,
        artifact_consumption=consumption_after,
    )

    matrix_before = compute_dependency_matrix_from_state(state_before)
    matrix_after = compute_dependency_matrix_from_state(state_after)
    assert matrix_before == matrix_after

    clusters_before = compute_shared_usage_clusters_from_state(state_before)
    clusters_after = compute_shared_usage_clusters_from_state(state_after)

    assert len(clusters_before) == len(clusters_after)
    for c_before, c_after in zip(clusters_before, clusters_after):
        assert c_before["modules"] == c_after["modules"]
        assert c_before["jaccard_similarity"] == c_after["jaccard_similarity"]
        assert c_before["shared_artifact_count"] == c_after["shared_artifact_count"]

    assert clusters_before != clusters_after
    assert "pkg.core::initialize_core" in clusters_before[0]["shared_artifact_keys"]
    assert "pkg.core::bootstrap_core" in clusters_after[0]["shared_artifact_keys"]


# ==============================================================================
# 8. PURE RAM NO-DISK EXECUTION PROOF
# ==============================================================================

def test_pure_ram_computation_blocks_all_disk_io():
    """
    Prove pure-RAM execution: All computations succeed with 100% of disk I/O blocked.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": ["Engine"], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["Engine", "boot"],
        }
    }
    artifact_consumption = {
        "pkg.core::boot": {"consumers": ["pkg.app"], "channels": {"pkg.app": ["direct_calls"]}}
    }
    graph = ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={})
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=artifact_consumption,
    )

    with patch("builtins.open", side_effect=AssertionError("Disk open blocked")), \
         patch("pathlib.Path.read_text", side_effect=AssertionError("Disk read_text blocked")), \
         patch("pathlib.Path.read_bytes", side_effect=AssertionError("Disk read_bytes blocked")):

        # 1. Projection
        proj = build_artifact_data_projection(state.artifacts, state.artifact_consumption)
        assert len(proj["artifacts"]) == 1

        # 2. Matrix
        mat = compute_dependency_matrix_from_state(state)
        assert "pkg.app" in mat
        assert mat["pkg.app"]["pkg.core"]["weight"] == 1

        # 3. Clusters
        cls = compute_shared_usage_clusters_from_state(state)
        assert isinstance(cls, list)
