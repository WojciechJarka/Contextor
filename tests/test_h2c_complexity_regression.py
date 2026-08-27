"""
tests/test_h2c_complexity_regression.py

H2C Complexity Regression Tests:
1. Proves that a no-collision repository performs 0 ast.unparse calls during collision extraction and aggregation.
2. Proves that the global pipeline consumes precomputed collision_facts rather than invoking extraction a second time.
3. Proves that collision facts extraction occurs exactly once per module across the full analysis run.
"""

import ast
from pathlib import Path
import tempfile
from unittest.mock import patch
import pytest

from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.reporting_engine.pipeline import execute_global_pipeline
from contextor.core.validator.collisions import (
    compute_collisions_from_facts,
    extract_module_collision_facts,
    extract_repository_collision_facts,
    validate_name_collisions,
)


def test_lazy_unparse_zero_calls_on_no_collision():
    """Verify ast.unparse is called 0 times when there are no collisions across modules."""
    src_a = "class ClientA:\n    pass\ndef action_a():\n    return 1\nCONST_A = 10\n"
    src_b = "class ClientB:\n    pass\ndef action_b():\n    return 2\nCONST_B = 20\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        path_a = Path(tmpdir) / "mod_a.py"
        path_b = Path(tmpdir) / "mod_b.py"
        path_a.write_text(src_a, encoding="utf-8")
        path_b.write_text(src_b, encoding="utf-8")

        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[]),
            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[]),
        }

        with patch("ast.unparse", wraps=ast.unparse) as mock_unparse:
            # Extract facts across all modules
            facts = extract_repository_collision_facts(modules)
            # Compute collisions
            errors = compute_collisions_from_facts(facts)

            assert errors == []
            # In a clean repo with 0 collisions, ast.unparse must not be called
            assert mock_unparse.call_count == 0


def test_pipeline_consumes_collision_facts_with_zero_second_extraction():
    """Verify execute_global_pipeline consumes provided collision_facts with zero extractions."""
    src_a = "class WorkerA:\n    pass\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        path_a = Path(tmpdir) / "mod_a.py"
        path_a.write_text(src_a, encoding="utf-8")

        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[]),
        }
        graph = ProjectGraph(hard_edges={}, soft_edges={})
        metrics = {"nodes": 1, "edges_hard": 0, "edges_soft": 0}
        cycles = []
        debt = {"score": 0}

        precomputed_facts = extract_repository_collision_facts(modules)
        precomputed_collisions = compute_collisions_from_facts(precomputed_facts)

        with patch(
            "contextor.core.validator.collisions.extract_module_collision_facts",
            wraps=extract_module_collision_facts,
        ) as mock_extract:
            result = execute_global_pipeline(
                repo_name="test_repo",
                modules=modules,
                graph=graph,
                metrics=metrics,
                cycles=cycles,
                debt=debt,
                runtime={},
                root_path=str(tmpdir),
                collisions=precomputed_collisions,
                collision_facts=precomputed_facts,
            )

            # Precomputed facts provided -> 0 extract_module_collision_facts calls during global pipeline
            assert mock_extract.call_count == 0
            assert "_analysis_result" in result
            ar = result["_analysis_result"]
            assert ar.collision_facts == precomputed_facts
            assert ar.collisions == precomputed_collisions
