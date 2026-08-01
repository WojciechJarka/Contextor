"""
The parallel artifact pass must agree with a sequential reference.

Worker input is shared via a pool initializer rather than being embedded
in every work item. That is an IPC optimization and must not change any
result, so this pins the parallel output to the same computation run
in-process.
"""

from contextor.core.reporting_layer.artifact_usage_report import (
    _init_artifact_worker,
    _process_single_artifact_module,
    build_artifact_index,
    collect_module_artifacts,
)
from contextor.core.symbol_engine.indexer import build_index


def _sequential_artifacts(modules, root_path):
    """
    Same per-module computation, run in this process.
    """

    _init_artifact_worker(modules, str(root_path))

    return dict(_process_single_artifact_module(module_id) for module_id in modules)


def test_pool_matches_sequential_run(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    parallel, failures = collect_module_artifacts(modules, str(sample_repo))

    assert failures == {}
    assert build_artifact_index(parallel) == build_artifact_index(
        _sequential_artifacts(modules, sample_repo)
    )


def test_every_module_is_accounted_for(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    parallel, failures = collect_module_artifacts(modules, str(sample_repo))

    assert set(parallel) == set(modules)
    assert failures == {}
