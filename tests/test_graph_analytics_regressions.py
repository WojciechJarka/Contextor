from contextor.core.reporting_engine.graph_analytics import (
    build_module_dependency_matrix,
    generate_graph_analytics_report,
)


def test_class_consumption_without_inheritance_evidence_is_not_inheritance():
    artifacts = {
        "artifacts": {
            "pkg.model::Engine": {
                "kind": "class",
                "definer_module": "pkg.model",
                "consumers": ["pkg.consumer"],
            }
        }
    }

    matrix = build_module_dependency_matrix(artifacts, {})

    assert matrix["pkg.consumer"]["pkg.model"]["dep_types"] == ["import"]


def test_explicit_inheritance_evidence_is_preserved():
    artifacts = {
        "artifacts": {
            "pkg.model::Engine": {
                "kind": "class",
                "definer_module": "pkg.model",
                "consumers": ["pkg.child"],
            }
        },
        "_usage_sidecar": {
            "pkg.model::Engine": {"inheritance": ["pkg.child"]},
        },
    }

    matrix = build_module_dependency_matrix(artifacts, {})

    assert matrix["pkg.child"]["pkg.model"]["dep_types"] == ["inheritance"]


def test_scoped_graph_analytics_keeps_isolated_modules():
    report = generate_graph_analytics_report(
        artifact_data={"artifacts": {}},
        hard_edges={"pkg.connected": []},
        scope="layer",
        scope_modules={"pkg.connected", "pkg.isolated"},
    )

    assert report["module_count"] == 2
    assert set(report["modules"]) == {"pkg.connected", "pkg.isolated"}
    assert report["modules"]["pkg.isolated"]["fan_in"] == 0
    assert report["modules"]["pkg.isolated"]["fan_out"] == 0


def test_fan_degrees_match_the_dependency_matrix():
    report = generate_graph_analytics_report(
        artifact_data={"artifacts": {}},
        hard_edges={"pkg.consumer": ["pkg.model"], "pkg.model": []},
    )

    assert report["modules"]["pkg.consumer"]["fan_out"] == 1
    assert report["modules"]["pkg.model"]["fan_in"] == 1
