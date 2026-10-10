from types import SimpleNamespace

import pytest

from contextor.core.domain.lineage_facts import LineageFamilyStatus
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


_RAW_FAMILIES = {
    "topology_metrics_state": "topology",
    "artifact_consumption_state": "artifact_consumption",
    "cycles_state": "cycles",
    "collisions_state": "collisions",
    "lineage_facts_state": "lineage",
}


@pytest.mark.parametrize("field, family", _RAW_FAMILIES.items())
@pytest.mark.parametrize("marker", [None, "pretend_fresh", True, 17, [], {}], ids=repr)
def test_malformed_family_marker_is_unavailable_without_mutating_state(
    tmp_path, field, family, marker
):
    state = _state("fresh")
    setattr(state, field, marker)

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["families"][family] == "unavailable"
    assert getattr(state, field) is marker


@pytest.mark.parametrize("field, family", _RAW_FAMILIES.items())
def test_missing_family_marker_keeps_documented_default(tmp_path, field, family):
    state = _state("fresh")
    delattr(state, field)

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["families"][family] == (
        "not_materialized" if family == "lineage" else "deferred"
    )
    assert not hasattr(state, field)


@pytest.mark.parametrize("field, family", list(_RAW_FAMILIES.items())[:4])
@pytest.mark.parametrize("marker", ["fresh", "stale", "deferred", "unavailable"])
def test_legal_derived_family_marker_is_preserved(tmp_path, field, family, marker):
    state = _state("fresh")
    setattr(state, field, marker)

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["families"][family] == marker
    assert getattr(state, field) == marker


@pytest.mark.parametrize("status", list(LineageFamilyStatus))
def test_every_legal_lineage_family_marker_is_preserved(tmp_path, status):
    state = _state(status.value)

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["families"]["lineage"] == status.value
    assert state.lineage_facts_state == status.value


def test_resource_limit_lineage_marker_remains_public(tmp_path):
    state = _state("resource_limit")
    assert build_state_freshness(tmp_path, state)["families"]["lineage"] == "resource_limit"


def test_resync_keeps_canonical_stale_and_normalizes_only_malformed_family(tmp_path):
    state = _state("fresh")
    state.resync_required = True
    state.cycles_state = "pretend_fresh"

    freshness = build_state_freshness(tmp_path, state)

    assert freshness["canonical_state"] == "stale"
    assert freshness["families"]["cycles"] == "unavailable"
    assert freshness["families"]["lineage"] == "fresh"
    assert freshness["canonical_revision"] == 7
    assert freshness["provenance"] == "snapshot"
    assert freshness["workspace_sync"] == "unverified"
    assert state.resync_required is True
    assert state.cycles_state == "pretend_fresh"
