from __future__ import annotations

import ast

from contextor.core.analysis.state_manager import canonical_python_source_path
from contextor.core.analysis.lineage_extraction_contracts import (
    DEFAULT_LINEAGE_EXTRACTION_LIMITS,
    ExtractedLineageContribution,
    ExtractedLineageProvider,
    LineageExtractionLimits,
    ParsedLineageSourceInput,
    _FINGERPRINT_RE,
    _index_ast_paths,
    _module_name_from_source_key,
    build_local_occurrence_id,
    parse_local_occurrence_id,
)
from contextor.core.analysis.lineage_extraction_emit import occurrence
from contextor.core.analysis.lineage_extraction_comprehensions import (
    publish_executed_walrus,
    visit_comprehension_expression,
)
from contextor.core.analysis.lineage_extraction_control import (
    visit_async_for,
    visit_async_with,
    visit_except_handler,
    visit_for,
    visit_if,
    visit_match,
    visit_match_as,
    visit_match_mapping,
    visit_match_star,
    visit_try,
    visit_while,
    visit_with,
)
from contextor.core.analysis.lineage_extraction_bindings import (
    finalize_captures,
    runtime_bind_target,
    visit_ann_assign,
    visit_assign,
    visit_aug_assign,
    visit_global,
    visit_name,
    visit_named_expr,
    visit_nonlocal,
)
from contextor.core.analysis.lineage_extraction_visitors import (
    visit_call,
    visit_class_def,
    visit_function,
    visit_import,
    visit_import_from,
    visit_lambda,
    visit_module,
    visit_return,
    visit_yield,
)
from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces, observe_all_subscript_mutation
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

LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION = 1

_LINEAGE_CACHE_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "source_key",
        "source_fingerprint",
        "status",
        "resource_limit_reason",
        "anchors",
        "flows",
        "surfaces",
    }
)
_LINEAGE_CACHE_ANCHOR_KEYS = frozenset(
    {"local_id", "kind", "span", "owner_local_id"}
)
_LINEAGE_CACHE_FLOW_KEYS = frozenset(
    {
        "local_id",
        "source",
        "target",
        "relation",
        "evidence",
        "resolution_kind",
        "confidence",
        "dynamic_boundary",
        "provider",
        "owner_local_id",
    }
)
_LINEAGE_CACHE_SURFACE_KEYS = frozenset(
    {
        "local_id",
        "kind",
        "exposed",
        "evidence",
        "resolution_kind",
        "confidence",
        "declared_name",
        "dynamic_boundary",
        "provider",
        "declaration_evidence",
    }
)
_LINEAGE_CACHE_OCCURRENCE_REF_KEYS = frozenset({"type", "local_id"})
_LINEAGE_CACHE_SYMBOLIC_REF_KEYS = frozenset(
    {"type", "kind", "module_name", "symbol_name", "source_local_id"}
)
_LINEAGE_CACHE_PROVIDER_KEYS = frozenset({"provider_id", "provider_version"})
_LINEAGE_CACHE_STATUSES = frozenset(
    {
        LineageFamilyStatus.FRESH,
        LineageFamilyStatus.RESOURCE_LIMIT,
    }
)


def _serialize_lineage_span(span: SourceSpan) -> list[int]:
    return [
        span.start_line,
        span.start_column,
        span.end_line,
        span.end_column,
    ]


def _deserialize_lineage_span(payload: object) -> SourceSpan:
    if (
        not isinstance(payload, list)
        or len(payload) != 4
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in payload
        )
    ):
        raise ValueError("Cached lineage span must contain exactly four integers.")
    return SourceSpan(*payload)


def _serialize_lineage_ref(
    ref: ExtractedOccurrenceRef | ExtractedSymbolicRef,
) -> dict:
    if isinstance(ref, ExtractedOccurrenceRef):
        return {
            "type": "occurrence",
            "local_id": ref.local_id,
        }
    if isinstance(ref, ExtractedSymbolicRef):
        return {
            "type": "symbolic",
            "kind": ref.kind.value,
            "module_name": ref.module_name,
            "symbol_name": ref.symbol_name,
            "source_local_id": ref.source_local_id,
        }
    raise TypeError("Unsupported extracted lineage reference.")


def _deserialize_lineage_ref(
    payload: object,
) -> ExtractedOccurrenceRef | ExtractedSymbolicRef:
    if not isinstance(payload, dict):
        raise ValueError("Cached lineage reference must be an object.")

    ref_type = payload.get("type")
    if ref_type == "occurrence":
        if set(payload) != _LINEAGE_CACHE_OCCURRENCE_REF_KEYS:
            raise ValueError("Malformed cached occurrence reference.")
        return ExtractedOccurrenceRef(local_id=payload["local_id"])

    if ref_type == "symbolic":
        if set(payload) != _LINEAGE_CACHE_SYMBOLIC_REF_KEYS:
            raise ValueError("Malformed cached symbolic reference.")
        return ExtractedSymbolicRef(
            kind=ExtractedSymbolicKind(payload["kind"]),
            module_name=payload["module_name"],
            symbol_name=payload["symbol_name"],
            source_local_id=payload["source_local_id"],
        )

    raise ValueError("Unknown cached lineage reference type.")


def _serialize_lineage_provider(provider: ProviderRef | None) -> dict | None:
    if provider is None:
        return None
    return {
        "provider_id": provider.provider_id,
        "provider_version": provider.provider_version,
    }


def _deserialize_lineage_provider(payload: object) -> ProviderRef | None:
    if payload is None:
        return None
    if not isinstance(payload, dict) or set(payload) != _LINEAGE_CACHE_PROVIDER_KEYS:
        raise ValueError("Malformed cached lineage provider.")
    return ProviderRef(
        provider_id=payload["provider_id"],
        provider_version=payload["provider_version"],
    )


def serialize_extracted_lineage_source_facts(
    facts: ExtractedLineageSourceFacts,
) -> dict:
    if not isinstance(facts, ExtractedLineageSourceFacts):
        raise TypeError("facts must be ExtractedLineageSourceFacts.")
    if facts.status not in _LINEAGE_CACHE_STATUSES:
        raise ValueError("Extracted lineage cache supports only fresh/resource_limit.")

    return {
        "schema_version": LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
        "source_key": facts.source_key,
        "source_fingerprint": facts.source_fingerprint,
        "status": facts.status.value,
        "resource_limit_reason": facts.resource_limit_reason,
        "anchors": [
            {
                "local_id": anchor.local_id,
                "kind": anchor.kind,
                "span": _serialize_lineage_span(anchor.span),
                "owner_local_id": anchor.owner_local_id,
            }
            for anchor in facts.anchors
        ],
        "flows": [
            {
                "local_id": flow.local_id,
                "source": _serialize_lineage_ref(flow.source),
                "target": _serialize_lineage_ref(flow.target),
                "relation": flow.relation.value,
                "evidence": _serialize_lineage_span(flow.evidence),
                "resolution_kind": flow.resolution_kind.value,
                "confidence": flow.confidence.value,
                "dynamic_boundary": flow.dynamic_boundary,
                "provider": _serialize_lineage_provider(flow.provider),
                "owner_local_id": flow.owner_local_id,
            }
            for flow in facts.flows
        ],
        "surfaces": [
            {
                "local_id": surface.local_id,
                "kind": surface.kind.value,
                "exposed": _serialize_lineage_ref(surface.exposed),
                "evidence": _serialize_lineage_span(surface.evidence),
                "resolution_kind": surface.resolution_kind.value,
                "confidence": surface.confidence.value,
                "declared_name": surface.declared_name,
                "dynamic_boundary": surface.dynamic_boundary,
                "provider": _serialize_lineage_provider(surface.provider),
                "declaration_evidence": (
                    surface.declaration_evidence.value
                    if surface.declaration_evidence is not None
                    else None
                ),
            }
            for surface in facts.surfaces
        ],
    }


def deserialize_extracted_lineage_source_facts(
    payload: object,
    *,
    source_key: str,
    source_fingerprint: str,
) -> ExtractedLineageSourceFacts | None:
    try:
        if not isinstance(payload, dict):
            return None
        if set(payload) != _LINEAGE_CACHE_TOP_LEVEL_KEYS:
            return None
        if payload["schema_version"] != LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION:
            return None
        if payload["source_key"] != source_key:
            return None
        if payload["source_fingerprint"] != source_fingerprint:
            return None

        status = LineageFamilyStatus(payload["status"])
        if status not in _LINEAGE_CACHE_STATUSES:
            return None

        anchors_payload = payload["anchors"]
        flows_payload = payload["flows"]
        surfaces_payload = payload["surfaces"]
        if not isinstance(anchors_payload, list):
            return None
        if not isinstance(flows_payload, list):
            return None
        if not isinstance(surfaces_payload, list):
            return None

        anchors = []
        for item in anchors_payload:
            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_ANCHOR_KEYS:
                return None
            anchors.append(
                ExtractedAnchorFact(
                    local_id=item["local_id"],
                    kind=item["kind"],
                    span=_deserialize_lineage_span(item["span"]),
                    owner_local_id=item["owner_local_id"],
                )
            )

        flows = []
        for item in flows_payload:
            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_FLOW_KEYS:
                return None
            flows.append(
                ExtractedFlowFact(
                    local_id=item["local_id"],
                    source=_deserialize_lineage_ref(item["source"]),
                    target=_deserialize_lineage_ref(item["target"]),
                    relation=LineageRelation(item["relation"]),
                    evidence=_deserialize_lineage_span(item["evidence"]),
                    resolution_kind=ResolutionKind(item["resolution_kind"]),
                    confidence=LineageConfidence(item["confidence"]),
                    dynamic_boundary=item["dynamic_boundary"],
                    provider=_deserialize_lineage_provider(item["provider"]),
                    owner_local_id=item["owner_local_id"],
                )
            )

        surfaces = []
        for item in surfaces_payload:
            if not isinstance(item, dict) or set(item) != _LINEAGE_CACHE_SURFACE_KEYS:
                return None
            declaration_evidence = item["declaration_evidence"]
            surfaces.append(
                ExtractedSurfaceFact(
                    local_id=item["local_id"],
                    kind=SurfaceKind(item["kind"]),
                    exposed=_deserialize_lineage_ref(item["exposed"]),
                    evidence=_deserialize_lineage_span(item["evidence"]),
                    resolution_kind=ResolutionKind(item["resolution_kind"]),
                    confidence=LineageConfidence(item["confidence"]),
                    declared_name=item["declared_name"],
                    dynamic_boundary=item["dynamic_boundary"],
                    provider=_deserialize_lineage_provider(item["provider"]),
                    declaration_evidence=(
                        None
                        if declaration_evidence is None
                        else SurfaceDeclarationEvidence(declaration_evidence)
                    ),
                )
            )

        return ExtractedLineageSourceFacts(
            source_key=source_key,
            source_fingerprint=source_fingerprint,
            anchors=tuple(anchors),
            flows=tuple(flows),
            surfaces=tuple(surfaces),
            status=status,
            resource_limit_reason=payload["resource_limit_reason"],
        )
    except (KeyError, TypeError, ValueError):
        return None


class _AnchorExtractor:
    def __init__(self, paths: dict[int, str], source_key: str) -> None:
        self.paths = paths
        self.source_key = source_key
        self.module_name = _module_name_from_source_key(source_key)
        self.state = LineageExtractionState()

    def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...], tuple[ExtractedSurfaceFact, ...]]:
        self._visit(tree, None, None)
        finalize_captures(self.state, self.paths)
        module_owner = next(anchor.local_id for anchor in self.state.anchors if anchor.kind == "module")
        finalize_surfaces(self.state, self.paths, self.module_name, module_owner)
        return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows)), tuple(sorted(self.state.surfaces))

    def _publish_executed_walrus(
        self,
        name: str,
        binding: ExtractedOccurrenceRef,
        target_owner: str | None,
    ) -> None:
        return publish_executed_walrus(
            self.state,
            name,
            binding,
            target_owner,
        )

    def _value(
        self,
        node: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef:
        self._visit(node, owner, walrus_owner)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            return occurrence(
                self.state,
                self.paths,
                "name_load",
                node,
                node.id,
            )
        if isinstance(node, ast.Call):
            return occurrence(
                self.state,
                self.paths,
                "call_result",
                node,
            )
        return occurrence(
            self.state,
            self.paths,
            "expression_result",
            node,
        )

    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is not None:
            method(node, owner_local_id, walrus_owner_local_id)
            return
        for child in ast.iter_child_nodes(node):
            self._visit(child, owner_local_id, walrus_owner_local_id)

    def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
        return visit_module(self.state, self.paths, node, visit=self._visit)

    def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
        return visit_class_def(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
        return visit_function(self.state, self.paths, self.module_name, node, kind, owner, walrus_owner, visit=self._visit)

    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "function", owner, walrus_owner)

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "async_function", owner, walrus_owner)

    def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        return visit_lambda(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)

    def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
        return visit_return(self.state, self.paths, self.module_name, node, owner, walrus_owner, value=self._value)

    def _visit_Yield(self, node: ast.Yield, owner: str | None, walrus_owner: str | None) -> None:
        return visit_yield(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_YieldFrom(self, node: ast.YieldFrom, owner: str | None, walrus_owner: str | None) -> None:
        return visit_yield(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
        return visit_call(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)

    def _visit_comprehension_expression(
        self,
        node: ast.AST,
        generators: list[ast.comprehension],
        values: tuple[ast.AST, ...],
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        return visit_comprehension_expression(
            self.state,
            self.paths,
            node,
            generators,
            values,
            owner,
            walrus_owner,
            visit=self._visit,
            runtime_bind_target=self._runtime_bind_target,
        )

    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)

    def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
        visit_name(self.state, self.paths, node, owner)

    def _visit_Subscript(self, node: ast.Subscript, owner: str | None, walrus_owner: str | None) -> None:
        observe_all_subscript_mutation(self.state, node, owner)
        self._visit(node.value, owner, walrus_owner)
        self._visit(node.slice, owner, walrus_owner)

    def _runtime_bind_target(
        self,
        target: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        runtime_bind_target(self.state, self.paths, target, owner, walrus_owner, visit=self._visit)

    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
        visit_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
        visit_ann_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
        visit_named_expr(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit, publish_walrus=self._publish_executed_walrus)

    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
        visit_aug_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
        return visit_if(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
        return visit_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
        return visit_async_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
        return visit_while(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
        return visit_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
        return visit_async_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_import(self.state, self.paths, node, owner)

    def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_import_from(self.state, self.paths, self.source_key, node, owner)

    def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
        visit_global(self.state, self.paths, node, owner)

    def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
        visit_nonlocal(self.state, self.paths, node, owner)

    def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
        return visit_try(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
        return visit_except_handler(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match_as(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_match_star(self.state, self.paths, node, owner)

    def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match_mapping(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)


def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
    if not isinstance(tree, ast.AST):
        raise TypeError("tree must be ast.AST.")
    canonical_key = canonical_python_source_path(source_key)
    if canonical_key is None or canonical_key != source_key:
        raise ValueError("source_key must be canonical repository-relative POSIX Python path.")
    if not isinstance(source_fingerprint, str) or _FINGERPRINT_RE.fullmatch(source_fingerprint) is None:
        raise ValueError("source_fingerprint must be lowercase raw-byte SHA-256.")
    if not isinstance(limits, LineageExtractionLimits):
        raise TypeError("limits must be LineageExtractionLimits.")
    paths, limit_reason = _index_ast_paths(tree, limits)
    if limit_reason is not None:
        return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, status=LineageFamilyStatus.RESOURCE_LIMIT, resource_limit_reason=limit_reason)
    anchors, flows, surfaces = _AnchorExtractor(paths, source_key).extract(tree)
    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=surfaces, status=LineageFamilyStatus.FRESH)


__all__ = [
    "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
    "ExtractedLineageContribution",
    "ExtractedLineageProvider",
    "LineageExtractionLimits",
    "ParsedLineageSourceInput",
    "build_local_occurrence_id",
    "extract_lineage_source_facts",
    "parse_local_occurrence_id",
]
