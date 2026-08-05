"""
Artifact usage report.

Regression coverage for the defect that made this report silently empty:
the module view handed to build_symbol_references() lacked an `imports`
attribute, so every module raised AttributeError inside a worker and was
discarded by a bare `except Exception: pass`.
"""

from contextor.core.reporting_layer.artifact_usage_report import (
    generate_artifact_usage_report,
)
from contextor.core.symbol_engine.indexer import build_index


def test_report_is_not_empty(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    report = generate_artifact_usage_report(modules, str(sample_repo))

    assert report["artifact_count"] > 0
    assert report["artifacts"]


def test_no_module_is_silently_skipped(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    report = generate_artifact_usage_report(modules, str(sample_repo))

    assert report.get("skipped_module_count", 0) == 0


def test_consumers_are_attributed_to_the_right_module(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    report = generate_artifact_usage_report(modules, str(sample_repo))

    engine = report["artifacts"].get("core.alpha::Engine")

    assert engine is not None, "Engine must appear in the artifact index"
    assert engine["definer_module"] == "core.alpha"
    assert "ui.app" in engine["consumers"]


def test_test_traceability_covers_every_module(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    report = generate_artifact_usage_report(modules, str(sample_repo))

    assert set(report["test_traceability"]) == set(modules)

from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report

def test_usage_sidecar_and_filtering(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))
    report = generate_artifact_usage_report(modules, str(sample_repo))
    
    # 1. sidecar should be present and contain usage blocks
    sidecar = report.get("_usage_sidecar", {})
    assert sidecar
    assert "core.alpha::Engine" in sidecar
    assert "direct_calls" in sidecar["core.alpha::Engine"]
    
    # usage should not be inline in artifacts anymore
    engine = report["artifacts"]["core.alpha::Engine"]
    assert "usage" not in engine
    assert engine["artifact_id"] == "core.alpha::Engine"
    
    # 2. Filtering orphans: MAX_ITEMS from core.alpha shouldn't be there because consumer_count is 0
    assert "core.alpha::MAX_ITEMS" not in report["artifacts"]
    
    # 3. compact report formatting
    compact = compact_artifact_report(report)
    assert compact["_format_version"] == "2"
    assert "shared_artifact_keys" in compact
    assert "shared_artifacts" not in compact
    assert compact["full_artifact_count"] == report["artifact_count"]
