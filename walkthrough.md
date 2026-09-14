# P1A — Extracted lineage cache codec

## STATUS

SUCCESS

Implemented the requested internal, versioned, lossless JSON-safe codec for ExtractedLineageSourceFacts. Indexer and CacheManager were not changed; __all__ was preserved.

## VALIDATION

.\\.venv\\Scripts\\python.exe -m pytest -q tests\\analysis\\test_lineage_cache_codec.py tests\\analysis\\test_lineage_extraction_equivalence.py

6 passed in 0.94s

git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_cache_codec.py passed.

## FILES_CHANGED

- contextor/core/analysis/lineage_extraction.py
- tests/analysis/test_lineage_cache_codec.py

## FULL_DIFFS

\`\`\`diff
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 6fdd7a1..bb8e1aa 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -64,9 +64,322 @@ from contextor.core.domain.lineage_facts import (
     ExtractedLineageSourceFacts,
     ExtractedOccurrenceRef,
     ExtractedSurfaceFact,
+    ExtractedSymbolicKind,
+    ExtractedSymbolicRef,
+    LineageConfidence,
     LineageFamilyStatus,
+    LineageRelation,
+    ProviderRef,
+    ResolutionKind,
+    SourceSpan,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
 )
 
+LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION = 1
+
+_LINEAGE_CACHE_TOP_LEVEL_KEYS = frozenset(
+    {
+        "schema_version",
+        "source_key",
+        "source_fingerprint",
+        "status",
+        "resource_limit_reason",
+        "anchors",
+        "flows",
+        "surfaces",
+    }
+)
+_LINEAGE_CACHE_ANCHOR_KEYS = frozenset(
+    {"local_id", "kind", "span", "owner_local_id"}
+)
+_LINEAGE_CACHE_FLOW_KEYS = frozenset(
+    {
+        "local_id",
+        "source",
+        "target",
+        "relation",
+        "evidence",
+        "resolution_kind",
+        "confidence",
+        "dynamic_boundary",
+        "provider",
+        "owner_local_id",
+    }
+)
+_LINEAGE_CACHE_SURFACE_KEYS = frozenset(
+    {
+        "local_id",
+        "kind",
+        "exposed",
+        "evidence",
+        "resolution_kind",
+        "confidence",
+        "declared_name",
+        "dynamic_boundary",
+        "provider",
+        "declaration_evidence",
+    }
+)
+_LINEAGE_CACHE_OCCURRENCE_REF_KEYS = frozenset({"type", "local_id"})
+_LINEAGE_CACHE_SYMBOLIC_REF_KEYS = frozenset(
+    {"type", "kind", "module_name", "symbol_name", "source_local_id"}
+)
+_LINEAGE_CACHE_PROVIDER_KEYS = frozenset({"provider_id", "provider_version"})
+_LINEAGE_CACHE_STATUSES = frozenset(
+    {
+        LineageFamilyStatus.FRESH,
+        LineageFamilyStatus.RESOURCE_LIMIT,
+    }
+)
+
+
+def _serialize_lineage_span(span: SourceSpan) -> list[int]:
+    return [
+        span.start_line,
+        span.start_column,
+        span.end_line,
+        span.end_column,
+    ]
+
+
+def _deserialize_lineage_span(payload: object) -> SourceSpan:
+    if (
+        not isinstance(payload, list)
+        or len(payload) != 4
+        or any(
+            isinstance(value, bool) or not isinstance(value, int)
+            for value in payload
+        )
+    ):
+        raise ValueError("Cached lineage span must contain exactly four integers.")
+    return SourceSpan(*payload)
+
+
+def _serialize_lineage_ref(
+    ref: ExtractedOccurrenceRef | ExtractedSymbolicRef,
+) -> dict:
+    if isinstance(ref, ExtractedOccurrenceRef):
+        return {
+            "type": "occurrence",
+            "local_id": ref.local_id,
+        }
+    if isinstance(ref, ExtractedSymbolicRef):
+        return {
+            "type": "symbolic",
+            "kind": ref.kind.value,
+            "module_name": ref.module_name,
+            "symbol_name": ref.symbol_name,
+            "source_local_id": ref.source_local_id,
+        }
+    raise TypeError("Unsupported extracted lineage reference.")
+
+
+def _deserialize_lineage_ref(
+    payload: object,
+) -> ExtractedOccurrenceRef | ExtractedSymbolicRef:
+    if not isinstance(payload, dict):
+        raise ValueError("Cached lineage reference must be an object.")
+
+    ref_type = payload.get("type")
+    if ref_type == "occurrence":
+        if set(payload) != _LINEAGE_CACHE_OCCURRENCE_REF_KEYS:
+            raise ValueError("Malformed cached occurrence reference.")
+        return ExtractedOccurrenceRef(local_id=payload["local_id"])
+
+    if ref_type == "symbolic":
+        if set(payload) != _LINEAGE_CACHE_SYMBOLIC_REF_KEYS:
+            raise ValueError("Malformed cached symbolic reference.")
+        return ExtractedSymbolicRef(
+            kind=ExtractedSymbolicKind(payload["kind"]),
+            module_name=payload["module_name"],
+            symbol_name=payload["symbol_name"],
+            source_local_id=payload["source_local_id"],
+        )
+
+    raise ValueError("Unknown cached lineage reference type.")
+
+
+def _serialize_lineage_provider(provider: ProviderRef | None) -> dict | None:
+    if provider is None:
+        return None
+    return {
+        "provider_id": provider.provider_id,
+        "provider_version": provider.provider_version,
+    }
+
+
+def _deserialize_lineage_provider(payload: object) -> ProviderRef | None:
+    if payload is None:
+        return None
+    if not isinstance(payload, dict) or set(payload) != _LINEAGE_CACHE_PROVIDER_KEYS:
+        raise ValueError("Malformed cached lineage provider.")
+    return ProviderRef(
+        provider_id=payload["provider_id"],
+        provider_version=payload["provider_version"],
+    )
+
+
+def serialize_extracted_lineage_source_facts(
+    facts: ExtractedLineageSourceFacts,
+) -> dict:
+    if not isinstance(facts, ExtractedLineageSourceFacts):
+        raise TypeError("facts must be ExtractedLineageSourceFacts.")
+    if facts.status not in _LINEAGE_CACHE_STATUSES:
+        raise ValueError("Extracted lineage cache supports only fresh/resource_limit.")
+
+    return {
+        "schema_version": LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
+        "source_key": facts.source_key,
+        "source_fingerprint": facts.source_fingerprint,
+        "status": facts.status.value,
+        "resource_limit_reason": facts.resource_limit_reason,
+        "anchors": [
+            {
+                "local_id": anchor.local_id,
+                "kind": anchor.kind,
+                "span": _serialize_lineage_span(anchor.span),
+                "owner_local_id": anchor.owner_local_id,
+            }
+            for anchor in facts.anchors
+        ],
+        "flows": [
+            {
+                "local_id": flow.local_id,
+                "source": _serialize_lineage_ref(flow.source),
+                "target": _serialize_lineage_ref(flow.target),
+                "relation": flow.relation.value,
+                "evidence": _serialize_lineage_span(flow.evidence),
+                "resolution_kind": flow.resolution_kind.value,
+                "confidence": flow.confidence.value,
+                "dynamic_boundary": flow.dynamic_boundary,
+                "provider": _serialize_lineage_provider(flow.provider),
+                "owner_local_id": flow.owner_local_id,
+            }
+            for flow in facts.flows
+        ],
+        "surfaces": [
+            {
+                "local_id": surface.local_id,
+                "kind": surface.kind.value,
+                "exposed": _serialize_lineage_ref(surface.exposed),
+                "evidence": _serialize_lineage_span(surface.evidence),
+                "resolution_kind": surface.resolution_kind.value,
+                "confidence": surface.confidence.value,
+                "declared_name": surface.declared_name,
+                "dynamic_boundary": surface.dynamic_boundary,
+                "provider": _serialize_lineage_provider(surface.provider),
+                "declaration_evidence": (
+                    surface.declaration_evidence.value
+                    if surface.declaration_evidence is not None
+                    else None
+                ),
+            }
+            for surface in facts.surfaces
+        ],
+    }
+
+
+def deserialize_extracted_lineage_source_facts(
+    payload: object,
+    *,
+    source_key: str,
+    source_fingerprint: str,
+) -> ExtractedLineageSourceFacts | None:
+    try:
+        if not isinstance(payload, dict):
+            return None
+        if set(payload) != _LINEAGE_CACHE_TOP_LEVEL_KEYS:
+            return None
+        if payload["schema_version"] != LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION:
+            return None
+        if payload["source_key"] != source_key:
+            return None
+        if payload["source_fingerprint"] != source_fingerprint:
+            return None
+
+        status = LineageFamilyStatus(payload["status"])
+        if status not in _LINEAGE_CACHE_STATUSES:
+            return None
+
+        anchors_payload = payload["anchors"]
+        flows_payload = payload["flows"]
+        surfaces_payload = payload["surfaces"]
+        if not isinstance(anchors_payload, list):
+            return None
+        if not isinstance(flows_payload, list):
+            return None
+        if not isinstance(surfaces_payload, list):
+            return None
+
+        anchors = []
+        for item in anchors_payload:
+            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_ANCHOR_KEYS:
+                return None
+            anchors.append(
+                ExtractedAnchorFact(
+                    local_id=item["local_id"],
+                    kind=item["kind"],
+                    span=_deserialize_lineage_span(item["span"]),
+                    owner_local_id=item["owner_local_id"],
+                )
+            )
+
+        flows = []
+        for item in flows_payload:
+            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_FLOW_KEYS:
+                return None
+            flows.append(
+                ExtractedFlowFact(
+                    local_id=item["local_id"],
+                    source=_deserialize_lineage_ref(item["source"]),
+                    target=_deserialize_lineage_ref(item["target"]),
+                    relation=LineageRelation(item["relation"]),
+                    evidence=_deserialize_lineage_span(item["evidence"]),
+                    resolution_kind=ResolutionKind(item["resolution_kind"]),
+                    confidence=LineageConfidence(item["confidence"]),
+                    dynamic_boundary=item["dynamic_boundary"],
+                    provider=_deserialize_lineage_provider(item["provider"]),
+                    owner_local_id=item["owner_local_id"],
+                )
+            )
+
+        surfaces = []
+        for item in surfaces_payload:
+            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_SURFACE_KEYS:
+                return None
+            declaration_evidence = item["declaration_evidence"]
+            surfaces.append(
+                ExtractedSurfaceFact(
+                    local_id=item["local_id"],
+                    kind=SurfaceKind(item["kind"]),
+                    exposed=_deserialize_lineage_ref(item["exposed"]),
+                    evidence=_deserialize_lineage_span(item["evidence"]),
+                    resolution_kind=ResolutionKind(item["resolution_kind"]),
+                    confidence=LineageConfidence(item["confidence"]),
+                    declared_name=item["declared_name"],
+                    dynamic_boundary=item["dynamic_boundary"],
+                    provider=_deserialize_lineage_provider(item["provider"]),
+                    declaration_evidence=(
+                        None
+                        if declaration_evidence is None
+                        else SurfaceDeclarationEvidence(declaration_evidence)
+                    ),
+                )
+            )
+
+        return ExtractedLineageSourceFacts(
+            source_key=source_key,
+            source_fingerprint=source_fingerprint,
+            anchors=tuple(anchors),
+            flows=tuple(flows),
+            surfaces=tuple(surfaces),
+            status=status,
+            resource_limit_reason=payload["resource_limit_reason"],
+        )
+    except (KeyError, TypeError, ValueError):
+        return None
+
 
 class _AnchorExtractor:
     def __init__(self, paths: dict[int, str], source_key: str) -> None:

\`\`\`

