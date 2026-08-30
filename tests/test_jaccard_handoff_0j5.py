from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reporting_engine import graph_analytics
from contextor.core.reporting_engine.graph_analytics import (
    SharedUsageClustersHandoff,
    _compact_clusters,
    build_jaccard_clusters,
    generate_graph_analytics_report,
    is_valid_shared_usage_clusters_handoff,
)


def _artifact_data():
    return {
        "artifacts": {
            "pkg::Thing": {
                "artifact_id": "pkg::Thing",
                "artifact": "pkg.Thing",
                "kind": "class",
                "definer_module": "pkg",
                "consumers": ["pkg.one", "pkg.two"],
                "consumer_count": 2,
            }
        },
        "_module_artifacts": {
            "pkg::Thing": {"artifact": "pkg.Thing"},
        },
        "_usage_sidecar": {},
    }


class _CompactIndex:
    def get_module_id(self, value):
        return f"module:{value}"

    def get_artifact_id(self, value):
        return f"artifact:{value}"


def _handoff(artifact_data, *, clusters=None, **changes):
    values = {
        "clusters": tuple(
            build_jaccard_clusters(artifact_data)
            if clusters is None
            else clusters
        ),
        "scope": "global",
        "min_jaccard": 0.30,
        "max_cluster_size": 25,
        "min_cluster_size": 2,
        "artifact_data_identity": id(artifact_data),
        "artifact_keys": tuple(artifact_data["artifacts"]),
        "raw_artifact_keys": tuple(artifact_data["_module_artifacts"]),
        "complete": True,
    }
    values.update(changes)
    return SharedUsageClustersHandoff(**values)


def test_global_handoff_is_raw_and_compaction_is_non_mutating():
    artifact_data = _artifact_data()
    raw = build_jaccard_clusters(artifact_data)
    before = [dict(cluster) for cluster in raw]
    captured = []

    report = generate_graph_analytics_report(
        artifact_data=artifact_data,
        hard_edges={"pkg.one": [], "pkg.two": []},
        modules={"pkg.one": {}, "pkg.two": {}},
        index_dict=_CompactIndex(),
        scope="global",
        raw_clusters_out=captured,
    )
    plain_report = generate_graph_analytics_report(
        artifact_data=artifact_data,
        hard_edges={"pkg.one": [], "pkg.two": []},
        modules={"pkg.one": {}, "pkg.two": {}},
        index_dict=_CompactIndex(),
        scope="global",
    )

    assert captured == raw
    assert captured == before
    assert report == plain_report
    assert report["shared_usage_clusters"] != raw
    assert report["shared_usage_clusters"][0]["modules"] == [
        "module:pkg.one",
        "module:pkg.two",
    ]
    assert report["shared_usage_clusters"][0]["shared_artifact_keys"] == [
        "artifact:pkg::Thing",
    ]


def test_handoff_validator_accepts_exact_current_run_and_rejects_invalid_variants():
    artifact_data = _artifact_data()
    raw_artifacts = artifact_data["_module_artifacts"]
    valid = _handoff(artifact_data)

    assert is_valid_shared_usage_clusters_handoff(
        valid, artifact_data=artifact_data, raw_artifacts=raw_artifacts
    )
    for complete in (1, "true", None):
        assert not is_valid_shared_usage_clusters_handoff(
            replace(valid, complete=complete),
            artifact_data=artifact_data,
            raw_artifacts=raw_artifacts,
        )
    assert not is_valid_shared_usage_clusters_handoff(
        None, artifact_data=artifact_data, raw_artifacts=raw_artifacts
    )
    assert not is_valid_shared_usage_clusters_handoff(
        {"clusters": []}, artifact_data=artifact_data, raw_artifacts=raw_artifacts
    )
    assert not is_valid_shared_usage_clusters_handoff(
        _handoff(artifact_data, complete=False),
        artifact_data=artifact_data,
        raw_artifacts=raw_artifacts,
    )
    assert not is_valid_shared_usage_clusters_handoff(
        _handoff(artifact_data, scope="layer"),
        artifact_data=artifact_data,
        raw_artifacts=raw_artifacts,
    )
    assert not is_valid_shared_usage_clusters_handoff(
        _handoff(artifact_data, min_jaccard=0.4),
        artifact_data=artifact_data,
        raw_artifacts=raw_artifacts,
    )

    cluster = valid.clusters[0]
    malformed_clusters = [
        {**cluster, "shared_artifact_count": len(cluster["shared_artifact_keys"]) + 1},
        {**cluster, "shared_artifact_count": len(cluster["shared_artifact_keys"]) - 1},
        {**cluster, "shared_artifact_count": "1"},
        {**cluster, "shared_artifact_count": True},
        {
            **cluster,
            "shared_artifact_count": 2,
            "shared_artifact_keys": [
                cluster["shared_artifact_keys"][0],
                cluster["shared_artifact_keys"][0],
            ],
        },
        {
            **cluster,
            "modules": [cluster["modules"][0], cluster["modules"][0]],
        },
        {**cluster, "size": len(cluster["modules"]) + 1},
        {**cluster, "size": "2"},
        {**cluster, "size": True},
        {**cluster, "jaccard_similarity": "not-a-number"},
        {**cluster, "shared_ratio": "not-a-number"},
    ]
    for malformed in malformed_clusters:
        assert not is_valid_shared_usage_clusters_handoff(
            _handoff(artifact_data, clusters=[malformed]),
            artifact_data=artifact_data,
            raw_artifacts=raw_artifacts,
        )

    second_cluster = {
        **cluster,
        "modules": sorted([cluster["modules"][0], "zzzz_extra"]),
        "size": 2,
    }
    assert not is_valid_shared_usage_clusters_handoff(
        _handoff(artifact_data, clusters=[cluster, second_cluster]),
        artifact_data=artifact_data,
        raw_artifacts=raw_artifacts,
    )

    malformed_artifact_data = {"artifacts": None}
    malformed_artifact_handoff = replace(
        valid,
        artifact_data_identity=id(malformed_artifact_data),
        artifact_keys=(),
    )
    assert not is_valid_shared_usage_clusters_handoff(
        malformed_artifact_handoff,
        artifact_data=malformed_artifact_data,
        raw_artifacts=raw_artifacts,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "inflated_count",
        "deflated_count",
        "non_int_count",
        "inconsistent_size",
        "non_int_size",
        "malformed_similarity",
        "malformed_ratio",
        "intra_cluster_duplicate",
        "cross_cluster_duplicate",
        "complete_one",
        "complete_string",
        "complete_none",
        "duplicate_shared_key",
    ],
)
def test_facade_rejected_handoff_falls_back_without_failing(
    tmp_path: Path, mutation: str
):
    (tmp_path / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "one.py").write_text(
        "from source import VALUE\n", encoding="utf-8"
    )
    (tmp_path / "two.py").write_text(
        "from source import VALUE\n", encoding="utf-8"
    )

    real_execute = graph_analytics.compute_shared_usage_clusters_from_state

    def reject_handoff(*args, **kwargs):
        result = original_execute(*args, **kwargs)
        handoff = result["_raw_shared_usage_clusters"]
        assert handoff.clusters
        cluster = handoff.clusters[0]
        if mutation == "inflated_count":
            cluster = {
                **cluster,
                "shared_artifact_count": len(cluster["shared_artifact_keys"]) + 1,
            }
        elif mutation == "deflated_count":
            cluster = {
                **cluster,
                "shared_artifact_count": len(cluster["shared_artifact_keys"]) - 1,
            }
        elif mutation == "non_int_count":
            cluster = {**cluster, "shared_artifact_count": "1"}
        elif mutation == "inconsistent_size":
            cluster = {**cluster, "size": len(cluster["modules"]) + 1}
        elif mutation == "non_int_size":
            cluster = {**cluster, "size": "2"}
        elif mutation == "malformed_similarity":
            cluster = {**cluster, "jaccard_similarity": "not-a-number"}
        elif mutation == "malformed_ratio":
            cluster = {**cluster, "shared_ratio": "not-a-number"}
        elif mutation == "intra_cluster_duplicate":
            cluster = {
                **cluster,
                "modules": [cluster["modules"][0], cluster["modules"][0]],
            }
        elif mutation == "cross_cluster_duplicate":
            second_cluster = {
                **cluster,
                "modules": sorted([cluster["modules"][0], "zzzz_extra"]),
                "size": 2,
            }
            result["_raw_shared_usage_clusters"] = replace(
                handoff, clusters=(cluster, second_cluster)
            )
            return result
        elif mutation == "complete_one":
            result["_raw_shared_usage_clusters"] = replace(
                handoff, complete=1
            )
            return result
        elif mutation == "complete_string":
            result["_raw_shared_usage_clusters"] = replace(
                handoff, complete="true"
            )
            return result
        elif mutation == "complete_none":
            result["_raw_shared_usage_clusters"] = replace(
                handoff, complete=None
            )
            return result
        elif mutation == "duplicate_shared_key":
            key = cluster["shared_artifact_keys"][0]
            cluster = {
                **cluster,
                "shared_artifact_keys": [key, key],
                "shared_artifact_count": 2,
            }
        result["_raw_shared_usage_clusters"] = replace(handoff, clusters=(cluster,))
        return result

    original_execute = __import__(
        "contextor.core.api.facade", fromlist=["execute_global_pipeline"]
    ).execute_global_pipeline
    with (
        patch(
            "contextor.core.api.facade.execute_global_pipeline",
            side_effect=reject_handoff,
        ),
        patch.object(
            graph_analytics,
            "compute_shared_usage_clusters_from_state",
            wraps=real_execute,
        ) as fallback,
    ):
        errors, _ = ContextorFacade().analyze_project(str(tmp_path))

    assert not errors
    assert fallback.call_count == 1


def test_facade_uses_valid_handoff_without_canonical_duplicate(tmp_path: Path):
    (tmp_path / "one.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("from one import VALUE\n", encoding="utf-8")

    with patch(
        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
        side_effect=AssertionError("valid handoff must skip canonical recomputation"),
    ):
        errors, _ = ContextorFacade().analyze_project(str(tmp_path))

    assert not errors
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    state = hydrated.engine.state
    assert state.shared_usage_clusters_state == "fresh"


def test_layer_graph_analytics_does_not_capture_raw_global_handoff():
    captured = []
    report = generate_graph_analytics_report(
        artifact_data={"artifacts": {}},
        hard_edges={"pkg.one": []},
        modules={"pkg.one": {}},
        scope="layer",
        scope_modules={"pkg.one"},
        raw_clusters_out=captured,
    )

    assert report["scope"] == "layer"
    assert captured == []


def test_compaction_keeps_input_when_called_directly():
    raw = [
        {
            "modules": ["pkg.one", "pkg.two"],
            "shared_artifact_keys": ["pkg::Thing"],
            "size": 2,
            "shared_artifact_count": 1,
            "jaccard_similarity": 1.0,
            "shared_ratio": 1.0,
        }
    ]
    before = [dict(raw[0]), list(raw[0]["modules"]), list(raw[0]["shared_artifact_keys"])]
    _compact_clusters(raw, _CompactIndex())
    assert raw[0] == before[0]
    assert raw[0]["modules"] == before[1]
    assert raw[0]["shared_artifact_keys"] == before[2]
