from types import SimpleNamespace

import pytest

from contextor.mcp.query_helpers import build_state_freshness


def _state(lineage_state: str):
    return SimpleNamespace(
        revision=7,
        provenance="snapshot",
        state_id="state-7",
        resync_required=False,
        dependency_graph=None,
        topology_metrics_state="deferred",
        artifact_consumption_state="deferred",
        cycles_state="deferred",
        collisions_state="deferred",
        lineage_facts_state=lineage_state,
    )


@pytest.mark.parametrize(
    "lineage_state",
    [
        "not_materialized",
        "fresh",
        "stale",
        "deferred",
        "resource_limit",
    ],
)
def test_lineage_family_is_exposed_in_common_freshness_envelope(
    tmp_path,
    lineage_state,
):
    freshness = build_state_freshness(tmp_path, _state(lineage_state))

    assert freshness["families"]["lineage"] == lineage_state


def test_missing_lineage_state_fails_closed_as_not_materialized(tmp_path):
    state = _state("fresh")
    del state.lineage_facts_state

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["families"]["lineage"] == "not_materialized"
