import copy

import pytest

from contextor.core.analysis.lineage_extraction import (
    LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
    deserialize_extracted_lineage_source_facts,
    serialize_extracted_lineage_source_facts,
)
from contextor.core.domain.lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSurfaceFact,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    ProviderRef,
    ResolutionKind,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
)


_FINGERPRINT = "1" * 64


def test_extracted_lineage_cache_codec_round_trip_fresh() -> None:
    span = SourceSpan(1, 0, 1, 8)
    provider = ProviderRef("fixture-provider", "1")

    facts = ExtractedLineageSourceFacts(
        source_key="pkg/mod.py",
        source_fingerprint=_FINGERPRINT,
        anchors=(
            ExtractedAnchorFact(
                local_id="module",
                kind="module",
                span=span,
                owner_local_id="root",
            ),
        ),
        flows=(
            ExtractedFlowFact(
                local_id="flow",
                source=ExtractedOccurrenceRef("local"),
                target=ExtractedSymbolicRef(
                    ExtractedSymbolicKind.IMPORT,
                    "pkg.dep",
                    "value",
                    "local",
                ),
                relation=LineageRelation.BINDS,
                evidence=span,
                resolution_kind=ResolutionKind.IMPORT_EXACT,
                confidence=LineageConfidence.CONFIRMED,
                provider=provider,
                owner_local_id="module",
            ),
        ),
        surfaces=(
            ExtractedSurfaceFact(
                local_id="surface",
                kind=SurfaceKind.PUBLIC_SYMBOL,
                exposed=ExtractedOccurrenceRef("local"),
                evidence=span,
                resolution_kind=ResolutionKind.PYTHON_NAME_CONVENTION,
                confidence=LineageConfidence.INFERRED,
                declared_name="value",
                provider=provider,
                declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
            ),
        ),
    )

    payload = serialize_extracted_lineage_source_facts(facts)

    assert payload["schema_version"] == LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION
    assert (
        deserialize_extracted_lineage_source_facts(
            payload,
            source_key="pkg/mod.py",
            source_fingerprint=_FINGERPRINT,
        )
        == facts
    )


def test_extracted_lineage_cache_codec_round_trip_resource_limit() -> None:
    facts = ExtractedLineageSourceFacts(
        source_key="pkg/mod.py",
        source_fingerprint=_FINGERPRINT,
        status=LineageFamilyStatus.RESOURCE_LIMIT,
        resource_limit_reason="node_limit",
    )

    payload = serialize_extracted_lineage_source_facts(facts)

    restored = deserialize_extracted_lineage_source_facts(
        payload,
        source_key="pkg/mod.py",
        source_fingerprint=_FINGERPRINT,
    )

    assert restored == facts
    assert restored is not None
    assert restored.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert restored.resource_limit_reason == "node_limit"


def test_extracted_lineage_cache_codec_rejects_wrong_schema() -> None:
    facts = ExtractedLineageSourceFacts(
        source_key="pkg/mod.py",
        source_fingerprint=_FINGERPRINT,
    )
    payload = serialize_extracted_lineage_source_facts(facts)
    payload["schema_version"] = LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION + 1

    assert (
        deserialize_extracted_lineage_source_facts(
            payload,
            source_key="pkg/mod.py",
            source_fingerprint=_FINGERPRINT,
        )
        is None
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.__setitem__("schema_version", True),
        lambda payload: payload.__setitem__("schema_version", 1.0),
        lambda payload: payload.__setitem__("source_key", "other.py"),
        lambda payload: payload.__setitem__("source_fingerprint", "2" * 64),
        lambda payload: payload.pop("status"),
        lambda payload: payload.__setitem__("unexpected", "value"),
        lambda payload: payload["flows"][0]["source"].__setitem__("type", "unknown"),
        lambda payload: payload["flows"][0].__setitem__("relation", "UNKNOWN"),
        lambda payload: payload["flows"][0].__setitem__("evidence", [1, 0, 1]),
        lambda payload: payload["flows"][0].__setitem__(
            "provider",
            {"provider_id": "fixture-provider"},
        ),
    ],
    ids=[
        "boolean-schema",
        "float-schema",
        "wrong-source-key",
        "wrong-source-fingerprint",
        "missing-top-level-key",
        "extra-top-level-key",
        "unknown-ref-type",
        "unknown-enum",
        "malformed-span",
        "malformed-provider",
    ],
)
def test_extracted_lineage_cache_codec_rejects_malformed_payloads(mutate) -> None:
    span = SourceSpan(1, 0, 1, 8)
    facts = ExtractedLineageSourceFacts(
        source_key="pkg/mod.py",
        source_fingerprint=_FINGERPRINT,
        anchors=(
            ExtractedAnchorFact(
                local_id="module",
                kind="module",
                span=span,
            ),
        ),
        flows=(
            ExtractedFlowFact(
                local_id="flow",
                source=ExtractedOccurrenceRef("local"),
                target=ExtractedSymbolicRef(
                    ExtractedSymbolicKind.IMPORT,
                    "pkg.dep",
                    "value",
                    "local",
                ),
                relation=LineageRelation.BINDS,
                evidence=span,
                resolution_kind=ResolutionKind.IMPORT_EXACT,
                confidence=LineageConfidence.CONFIRMED,
                provider=ProviderRef("fixture-provider", "1"),
                owner_local_id="module",
            ),
        ),
    )
    payload = copy.deepcopy(serialize_extracted_lineage_source_facts(facts))
    mutate(payload)

    assert (
        deserialize_extracted_lineage_source_facts(
            payload,
            source_key="pkg/mod.py",
            source_fingerprint=_FINGERPRINT,
        )
        is None
    )
