"""Immutable, phase-safe domain contracts for repository lineage facts.

This module is intentionally pure: it does not read source, inspect an AST,
consult a registry, or allocate persistent identities.  Extracted facts carry
only source-local references.  Materialized facts are the only phase allowed
to carry opaque semantic-owner tokens and derived interface slots.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final
from urllib.parse import quote, unquote


LINEAGE_FACTS_SEMANTIC_VERSION: Final[str] = "1"
_SLOT_VERSION: Final[str] = "v1"
_SLOT_PREFIX: Final[str] = "slot"


class LineageRelation(str, Enum):
    BINDS = "BINDS"
    ASSIGNS = "ASSIGNS"
    ARGUMENT_TO_PARAMETER = "ARGUMENT_TO_PARAMETER"
    RETURNS = "RETURNS"
    CALL_RESULT = "CALL_RESULT"
    READS_STATE = "READS_STATE"
    WRITES_STATE = "WRITES_STATE"
    ALIASES = "ALIASES"
    CAPTURES = "CAPTURES"
    CALLBACK_REGISTERS = "CALLBACK_REGISTERS"
    CALLBACK_INVOKES = "CALLBACK_INVOKES"
    INHERITS = "INHERITS"
    OVERRIDES = "OVERRIDES"
    EXPOSES = "EXPOSES"
    DEFAULTS_TO_PARAMETER = "DEFAULTS_TO_PARAMETER"
    DECLARES_PUBLIC_NAMES = "DECLARES_PUBLIC_NAMES"


class ResolutionKind(str, Enum):
    LEXICAL_EXACT = "LEXICAL_EXACT"
    IMPORT_EXACT = "IMPORT_EXACT"
    CALL_EXACT = "CALL_EXACT"
    SIGNATURE_EXACT = "SIGNATURE_EXACT"
    STATIC_MRO_EXACT = "STATIC_MRO_EXACT"
    LITERAL_CONTAINER_EXACT = "LITERAL_CONTAINER_EXACT"
    BOUNDED_STATIC_SET = "BOUNDED_STATIC_SET"
    UNRESOLVED_NAME = "UNRESOLVED_NAME"
    DYNAMIC_RUNTIME_BOUNDARY = "DYNAMIC_RUNTIME_BOUNDARY"
    PYTHON_NAME_CONVENTION = "PYTHON_NAME_CONVENTION"
    RECEPTOR_PROVIDED = "RECEPTOR_PROVIDED"


class LineageConfidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    INFERRED = "INFERRED"
    UNRESOLVED = "UNRESOLVED"
    DYNAMIC = "DYNAMIC"


class SurfaceKind(str, Enum):
    PUBLIC_SYMBOL = "PUBLIC_SYMBOL"
    EXPORT = "EXPORT"
    REEXPORT = "REEXPORT"
    ENTRYPOINT = "ENTRYPOINT"
    REGISTRATION = "REGISTRATION"


class SurfaceDeclarationEvidence(str, Enum):
    STATIC_DECLARATION = "STATIC_DECLARATION"
    LITERAL_ALL_DECLARATION = "LITERAL_ALL_DECLARATION"


class LineageFamilyStatus(str, Enum):
    NOT_MATERIALIZED = "not_materialized"
    FRESH = "fresh"
    STALE = "stale"
    DEFERRED = "deferred"
    RESOURCE_LIMIT = "resource_limit"


class ParameterKind(str, Enum):
    POSITIONAL_ONLY = "posonly"
    POSITIONAL_OR_KEYWORD = "poskw"
    VAR_POSITIONAL = "vararg"
    KEYWORD_ONLY = "kwonly"
    VAR_KEYWORD = "varkw"


class SemanticSlotKind(str, Enum):
    PARAMETER_VALUE = "param-value"
    POSITIONAL_BINDING = "bind-pos"
    KEYWORD_BINDING = "bind-kw"
    RETURN = "return"
    MODULE_GLOBAL = "module-global"
    CLASS_ATTRIBUTE = "class-attr"
    INSTANCE_ATTRIBUTE = "instance-attr"
    PUBLIC = "public"
    ENTRYPOINT = "entry"


class ExtractedSymbolicKind(str, Enum):
    DEFINITION = "definition"
    CALLEE = "callee"
    IMPORT = "import"
    PARAMETER = "parameter"
    RETURN = "return"
    STATE = "state"
    PUBLIC_TARGET = "public_target"


class SemanticEndpointRole(str, Enum):
    FLOW_SOURCE = "flow_source"
    FLOW_TARGET = "flow_target"
    SURFACE_EXPOSED = "surface_exposed"


@dataclass(frozen=True, order=True)
class SourceSpan:
    """Exact source evidence; it is never semantic identity."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __post_init__(self) -> None:
        if min(self.start_line, self.start_column, self.end_line, self.end_column) < 0:
            raise ValueError("SourceSpan coordinates must be non-negative.")
        if (self.end_line, self.end_column) < (self.start_line, self.start_column):
            raise ValueError("SourceSpan end must not precede start.")


@dataclass(frozen=True, order=True)
class ExtractedOccurrenceRef:
    """Revision-local reference valid only within one extracted source slice."""

    local_id: str

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")


@dataclass(frozen=True, order=True)
class ExtractedSymbolicRef:
    """Source-local symbolic input for a later active-ID materializer."""

    kind: ExtractedSymbolicKind
    module_name: str
    symbol_name: str
    source_local_id: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.module_name, "module_name")
        _require_token(self.symbol_name, "symbol_name")
        if self.source_local_id is not None:
            _require_token(self.source_local_id, "source_local_id")

    @property
    def qualified_name(self) -> str:
        """Existing Contextor symbolic convention, derived from structural fields."""

        return f"{self.module_name}::{self.symbol_name}"


@dataclass(frozen=True, order=True)
class SemanticEndpoint:
    """Opaque semantic endpoint available only after materialization."""

    owner_id: str
    slot: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.owner_id, "owner_id")
        if self.slot is not None:
            parse_semantic_slot(self.slot)
            if parse_semantic_slot(self.slot).owner_id != self.owner_id:
                raise ValueError("Semantic endpoint slot owner must match owner_id.")


@dataclass(frozen=True, order=True)
class ProviderRef:
    provider_id: str
    provider_version: str

    def __post_init__(self) -> None:
        _require_token(self.provider_id, "provider_id")
        _require_token(self.provider_version, "provider_version")


@dataclass(frozen=True, order=True)
class MaterializedOccurrenceRef:
    """Canonical-slice local occurrence; never a stable cross-source boundary."""

    source_key: str
    source_fingerprint: str
    local_id: str

    def __post_init__(self) -> None:
        _require_token(self.source_key, "source_key")
        _require_token(self.source_fingerprint, "source_fingerprint")
        _require_token(self.local_id, "local_id")


@dataclass(frozen=True, order=True)
class MaterializedSymbolicRef:
    """Canonical-slice symbolic boundary, never an occurrence or owner."""

    source_key: str
    source_fingerprint: str
    kind: ExtractedSymbolicKind
    module_name: str
    symbol_name: str
    source_local_id: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.source_key, "source_key")
        _require_token(self.source_fingerprint, "source_fingerprint")
        _require_token(self.module_name, "module_name")
        _require_token(self.symbol_name, "symbol_name")
        if self.source_local_id is not None:
            _require_token(self.source_local_id, "source_local_id")


@dataclass(frozen=True, order=True)
class SemanticEndpointOrigin:
    """Compact symbolic provenance for one strengthened semantic endpoint."""

    source_key: str
    source_fingerprint: str
    fact_local_id: str
    endpoint_role: SemanticEndpointRole
    kind: ExtractedSymbolicKind
    module_name: str
    symbol_name: str
    source_local_id: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.source_key, "source_key")
        _require_token(self.source_fingerprint, "source_fingerprint")
        _require_token(self.fact_local_id, "fact_local_id")
        if not isinstance(self.endpoint_role, SemanticEndpointRole):
            raise TypeError("endpoint_role must be SemanticEndpointRole.")
        if not isinstance(self.kind, ExtractedSymbolicKind):
            raise TypeError("kind must be ExtractedSymbolicKind.")
        _require_token(self.module_name, "module_name")
        _require_token(self.symbol_name, "symbol_name")
        if self.source_local_id is not None:
            _require_token(self.source_local_id, "source_local_id")


@dataclass(frozen=True, order=True)
class ExtractedAnchorFact:
    local_id: str
    kind: str
    span: SourceSpan
    owner_local_id: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        _require_token(self.kind, "kind")
        if self.owner_local_id is not None:
            _require_token(self.owner_local_id, "owner_local_id")


@dataclass(frozen=True, order=True)
class ExtractedFlowFact:
    local_id: str
    source: ExtractedOccurrenceRef | ExtractedSymbolicRef
    target: ExtractedOccurrenceRef | ExtractedSymbolicRef
    relation: LineageRelation
    evidence: SourceSpan
    resolution_kind: ResolutionKind
    confidence: LineageConfidence
    dynamic_boundary: str | None = None
    provider: ProviderRef | None = None

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        if not isinstance(self.source, (ExtractedOccurrenceRef, ExtractedSymbolicRef)) or not isinstance(self.target, (ExtractedOccurrenceRef, ExtractedSymbolicRef)):
            raise TypeError("Extracted flow endpoints must be extracted occurrence or symbolic references.")
        _validate_confidence(self.resolution_kind, self.confidence)
        _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
        _validate_provider(self.provider)


@dataclass(frozen=True, order=True)
class ExtractedSurfaceFact:
    local_id: str
    kind: SurfaceKind
    exposed: ExtractedOccurrenceRef | ExtractedSymbolicRef
    evidence: SourceSpan
    resolution_kind: ResolutionKind
    confidence: LineageConfidence
    declared_name: str
    dynamic_boundary: str | None = None
    provider: ProviderRef | None = None
    declaration_evidence: SurfaceDeclarationEvidence | None = None

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        _require_token(self.declared_name, "declared_name")
        if not isinstance(self.exposed, (ExtractedOccurrenceRef, ExtractedSymbolicRef)):
            raise TypeError("Extracted surfaces must use extracted occurrence or symbolic references.")
        _validate_confidence(self.resolution_kind, self.confidence)
        _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
        _validate_provider(self.provider)
        _validate_surface_declaration_evidence(self.kind, self.declaration_evidence)


@dataclass(frozen=True)
class ExtractedLineageSourceFacts:
    """Parsed-AST output: source-local only, never canonical cross-source facts."""

    source_key: str
    source_fingerprint: str
    anchors: tuple[ExtractedAnchorFact, ...] = ()
    flows: tuple[ExtractedFlowFact, ...] = ()
    surfaces: tuple[ExtractedSurfaceFact, ...] = ()
    status: LineageFamilyStatus = LineageFamilyStatus.FRESH
    resource_limit_reason: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.source_key, "source_key")
        _require_token(self.source_fingerprint, "source_fingerprint")
        _validate_source_status(self.status, self.resource_limit_reason)
        _require_sorted_unique(self.anchors, "anchors")
        _require_sorted_unique(self.flows, "flows")
        _require_sorted_unique(self.surfaces, "surfaces")


@dataclass(frozen=True, order=True)
class MaterializedAnchorFact:
    local_id: str
    reference: MaterializedOccurrenceRef
    kind: str
    span: SourceSpan

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        _require_token(self.kind, "kind")
        _require_materialized_anchor_reference(self.reference)


@dataclass(frozen=True, order=True)
class MaterializedFlowFact:
    local_id: str
    source: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
    target: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
    relation: LineageRelation
    evidence: SourceSpan
    resolution_kind: ResolutionKind
    confidence: LineageConfidence
    dynamic_boundary: str | None = None
    provider: ProviderRef | None = None

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        _require_materialized_reference(self.source, "Materialized flow source")
        _require_materialized_reference(self.target, "Materialized flow target")
        if isinstance(self.source, MaterializedOccurrenceRef) and isinstance(self.target, MaterializedOccurrenceRef):
            if self.source.source_key != self.target.source_key or self.source.source_fingerprint != self.target.source_fingerprint:
                raise ValueError("Cross-source occurrence-to-occurrence flow is not canonical.")
        _validate_confidence(self.resolution_kind, self.confidence)
        _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
        _validate_provider(self.provider)


@dataclass(frozen=True, order=True)
class MaterializedSurfaceFact:
    local_id: str
    kind: SurfaceKind
    exposed: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
    evidence: SourceSpan
    resolution_kind: ResolutionKind
    confidence: LineageConfidence
    declared_name: str
    dynamic_boundary: str | None = None
    provider: ProviderRef | None = None
    declaration_evidence: SurfaceDeclarationEvidence | None = None

    def __post_init__(self) -> None:
        _require_token(self.local_id, "local_id")
        _require_token(self.declared_name, "declared_name")
        _require_materialized_reference(self.exposed, "Materialized surfaces")
        _validate_confidence(self.resolution_kind, self.confidence)
        _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
        _validate_provider(self.provider)
        _validate_surface_declaration_evidence(self.kind, self.declaration_evidence)
        _validate_materialized_surface_target(
            self.exposed,
            self.resolution_kind,
            self.confidence,
        )


@dataclass(frozen=True)
class SourceLineageManifest:
    source_key: str
    source_fingerprint: str
    semantic_version: str
    status: LineageFamilyStatus
    anchor_count: int
    flow_count: int
    surface_count: int
    resource_limit_reason: str | None = None

    def __post_init__(self) -> None:
        _require_token(self.source_key, "source_key")
        _require_token(self.source_fingerprint, "source_fingerprint")
        _require_token(self.semantic_version, "semantic_version")
        if min(self.anchor_count, self.flow_count, self.surface_count) < 0:
            raise ValueError("Lineage manifest counts must be non-negative.")
        _validate_source_status(self.status, self.resource_limit_reason)


@dataclass(frozen=True, order=True)
class SemanticInterfaceDescriptor:
    owner_id: str
    slots: tuple[str, ...]
    signature_digest: str

    def __post_init__(self) -> None:
        _require_token(self.owner_id, "owner_id")
        _require_token(self.signature_digest, "signature_digest")
        _require_sorted_unique(self.slots, "slots")
        for slot in self.slots:
            if parse_semantic_slot(slot).owner_id != self.owner_id:
                raise ValueError("Descriptor slots must belong to owner_id.")


@dataclass(frozen=True)
class MaterializedLineageSourceFacts:
    """Canonical source slice with local occurrences and semantic boundaries.

    A ``MaterializedOccurrenceRef`` is a canonical source-local occurrence
    belonging to this manifest's source slice.  A ``SemanticEndpoint`` is a
    semantic/interface boundary.  Foreign or cross-source occurrences cannot
    be stable cross-source endpoints.
    """

    manifest: SourceLineageManifest
    anchors: tuple[MaterializedAnchorFact, ...] = ()
    flows: tuple[MaterializedFlowFact, ...] = ()
    surfaces: tuple[MaterializedSurfaceFact, ...] = ()
    interface_descriptors: tuple[SemanticInterfaceDescriptor, ...] = ()
    semantic_endpoint_origins: tuple[SemanticEndpointOrigin, ...] = ()

    def __post_init__(self) -> None:
        _require_sorted_unique(self.anchors, "anchors")
        _require_sorted_unique(self.flows, "flows")
        _require_sorted_unique(self.surfaces, "surfaces")
        _require_sorted_unique(self.interface_descriptors, "interface_descriptors")
        _require_sorted_unique(self.semantic_endpoint_origins, "semantic_endpoint_origins")
        if self.manifest.status == LineageFamilyStatus.FRESH:
            expected = (len(self.anchors), len(self.flows), len(self.surfaces))
            actual = (
                self.manifest.anchor_count,
                self.manifest.flow_count,
                self.manifest.surface_count,
            )
            if expected != actual:
                raise ValueError("Fresh lineage manifest counts must match facts.")
        for anchor in self.anchors:
            _require_slice_occurrence(anchor.reference, self.manifest)
        for flow in self.flows:
            _require_slice_occurrence(flow.source, self.manifest)
            _require_slice_occurrence(flow.target, self.manifest)
        for surface in self.surfaces:
            _require_slice_occurrence(surface.exposed, self.manifest)
        self._validate_semantic_endpoint_origins()

    def _validate_semantic_endpoint_origins(self) -> None:
        flow_by_id = {flow.local_id: flow for flow in self.flows}
        surface_by_id = {surface.local_id: surface for surface in self.surfaces}
        locators: set[tuple[str, SemanticEndpointRole]] = set()
        for origin in self.semantic_endpoint_origins:
            if (
                origin.source_key != self.manifest.source_key
                or origin.source_fingerprint != self.manifest.source_fingerprint
            ):
                raise ValueError("Semantic endpoint origin must belong to its slice.")
            locator = (origin.fact_local_id, origin.endpoint_role)
            if locator in locators:
                raise ValueError("Semantic endpoint origins must have unique locators.")
            locators.add(locator)
            if origin.endpoint_role is SemanticEndpointRole.FLOW_SOURCE:
                endpoint = getattr(flow_by_id.get(origin.fact_local_id), "source", None)
            elif origin.endpoint_role is SemanticEndpointRole.FLOW_TARGET:
                endpoint = getattr(flow_by_id.get(origin.fact_local_id), "target", None)
            else:
                endpoint = getattr(surface_by_id.get(origin.fact_local_id), "exposed", None)
            if not isinstance(endpoint, SemanticEndpoint):
                raise ValueError(
                    "Semantic endpoint origin must locate a semantic endpoint."
                )


@dataclass(frozen=True, order=True)
class SemanticSlot:
    raw: str
    owner_id: str
    kind: SemanticSlotKind
    parts: tuple[str, ...]


def build_parameter_value_slot(
    owner_id: str,
    kind: ParameterKind,
    *,
    ordinal: int | None = None,
    name: str | None = None,
) -> str:
    if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD):
        return _build_parameter_ordinal_slot(owner_id, SemanticSlotKind.PARAMETER_VALUE, kind, ordinal)
    if kind == ParameterKind.KEYWORD_ONLY:
        return _build_slot(owner_id, SemanticSlotKind.PARAMETER_VALUE, kind.value, _required_name(name))
    if kind in (ParameterKind.VAR_POSITIONAL, ParameterKind.VAR_KEYWORD):
        return _build_slot(owner_id, SemanticSlotKind.PARAMETER_VALUE, kind.value)
    raise ValueError(f"Unsupported parameter kind: {kind!r}")


def build_positional_binding_slot(owner_id: str, kind: ParameterKind, *, ordinal: int | None = None) -> str:
    if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD):
        return _build_parameter_ordinal_slot(owner_id, SemanticSlotKind.POSITIONAL_BINDING, kind, ordinal)
    if kind == ParameterKind.VAR_POSITIONAL:
        return _build_slot(owner_id, SemanticSlotKind.POSITIONAL_BINDING, kind.value)
    raise ValueError("Only positional-compatible parameters have positional binding slots.")


def build_keyword_binding_slot(owner_id: str, kind: ParameterKind, *, name: str | None = None) -> str:
    if kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY):
        return _build_slot(owner_id, SemanticSlotKind.KEYWORD_BINDING, "fixed", _required_name(name))
    if kind == ParameterKind.VAR_KEYWORD:
        return _build_slot(owner_id, SemanticSlotKind.KEYWORD_BINDING, kind.value)
    raise ValueError("Only keyword-compatible parameters have keyword binding slots.")


def build_return_slot(owner_id: str) -> str:
    return _build_slot(owner_id, SemanticSlotKind.RETURN)


def build_module_global_slot(module_id: str, name: str) -> str:
    return _build_slot(module_id, SemanticSlotKind.MODULE_GLOBAL, _required_name(name))


def build_class_attr_slot(class_id: str, name: str) -> str:
    return _build_slot(class_id, SemanticSlotKind.CLASS_ATTRIBUTE, _required_name(name))


def build_instance_attr_slot(class_id: str, name: str) -> str:
    return _build_slot(class_id, SemanticSlotKind.INSTANCE_ATTRIBUTE, _required_name(name))


def build_public_slot(module_id: str, name: str) -> str:
    return _build_slot(module_id, SemanticSlotKind.PUBLIC, _required_name(name))


def build_entrypoint_slot(module_id: str, name: str) -> str:
    return _build_slot(module_id, SemanticSlotKind.ENTRYPOINT, _required_name(name))


def parse_semantic_slot(raw: str) -> SemanticSlot:
    """Parse the sole supported slot representation with round-trip validation."""

    _require_token(raw, "slot")
    pieces = raw.split(":")
    if len(pieces) < 4 or pieces[0] != _SLOT_PREFIX or pieces[1] != _SLOT_VERSION:
        raise ValueError("Invalid semantic slot prefix/version.")
    owner_id = _decode_component(pieces[2])
    _require_token(owner_id, "slot owner_id")
    try:
        kind = SemanticSlotKind(pieces[3])
    except ValueError as exc:
        raise ValueError("Unknown semantic slot kind.") from exc
    parts = tuple(_decode_component(value) for value in pieces[4:])
    slot = SemanticSlot(raw=raw, owner_id=owner_id, kind=kind, parts=parts)
    _validate_slot_shape(slot)
    if _build_slot(owner_id, kind, *parts) != raw:
        raise ValueError("Semantic slot is not canonically encoded.")
    return slot


def _build_parameter_ordinal_slot(owner_id: str, slot_kind: SemanticSlotKind, kind: ParameterKind, ordinal: int | None) -> str:
    if ordinal is None or isinstance(ordinal, bool) or ordinal < 0:
        raise ValueError("Parameter ordinal must be a non-negative integer.")
    return _build_slot(owner_id, slot_kind, kind.value, str(ordinal))


def _build_slot(owner_id: str, kind: SemanticSlotKind, *parts: str) -> str:
    _require_token(owner_id, "owner_id")
    encoded = [_SLOT_PREFIX, _SLOT_VERSION, _encode_component(owner_id), kind.value]
    encoded.extend(_encode_component(part) for part in parts)
    return ":".join(encoded)


def _validate_slot_shape(slot: SemanticSlot) -> None:
    parts = slot.parts
    if slot.kind in (SemanticSlotKind.RETURN,):
        valid = not parts
    elif slot.kind in (SemanticSlotKind.MODULE_GLOBAL, SemanticSlotKind.CLASS_ATTRIBUTE, SemanticSlotKind.INSTANCE_ATTRIBUTE, SemanticSlotKind.PUBLIC, SemanticSlotKind.ENTRYPOINT):
        valid = len(parts) == 1 and bool(parts[0])
    elif slot.kind == SemanticSlotKind.PARAMETER_VALUE:
        valid = (
            len(parts) == 2
            and parts[0] in {ParameterKind.POSITIONAL_ONLY.value, ParameterKind.POSITIONAL_OR_KEYWORD.value}
            and parts[1].isdigit()
        ) or (
            len(parts) == 2 and parts[0] == ParameterKind.KEYWORD_ONLY.value and bool(parts[1])
        ) or (
            len(parts) == 1 and parts[0] in {ParameterKind.VAR_POSITIONAL.value, ParameterKind.VAR_KEYWORD.value}
        )
    elif slot.kind == SemanticSlotKind.POSITIONAL_BINDING:
        valid = (
            len(parts) == 2
            and parts[0] in {ParameterKind.POSITIONAL_ONLY.value, ParameterKind.POSITIONAL_OR_KEYWORD.value}
            and parts[1].isdigit()
        ) or (len(parts) == 1 and parts[0] == ParameterKind.VAR_POSITIONAL.value)
    elif slot.kind == SemanticSlotKind.KEYWORD_BINDING:
        valid = (len(parts) == 2 and parts[0] == "fixed" and bool(parts[1])) or (
            len(parts) == 1 and parts[0] == ParameterKind.VAR_KEYWORD.value
        )
    else:
        valid = False
    if not valid:
        raise ValueError("Invalid semantic slot shape.")


def _encode_component(value: str) -> str:
    _require_token(value, "slot component")
    return quote(value, safe="-._~")


def _decode_component(value: str) -> str:
    if not value:
        raise ValueError("Semantic slot component must not be empty.")
    decoded = unquote(value)
    if quote(decoded, safe="-._~") != value:
        raise ValueError("Semantic slot component is not canonically escaped.")
    return decoded


def _required_name(name: str | None) -> str:
    if name is None:
        raise ValueError("A non-empty name is required.")
    _require_token(name, "name")
    return name


def _require_token(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string.")


def _validate_optional_token(value: str | None, label: str) -> None:
    if value is not None:
        _require_token(value, label)


_EXACT_SURFACE_TARGET_RESOLUTIONS = frozenset({
    ResolutionKind.LEXICAL_EXACT,
    ResolutionKind.IMPORT_EXACT,
    ResolutionKind.CALL_EXACT,
    ResolutionKind.SIGNATURE_EXACT,
    ResolutionKind.STATIC_MRO_EXACT,
    ResolutionKind.LITERAL_CONTAINER_EXACT,
})


def _validate_confidence(kind: ResolutionKind, confidence: LineageConfidence) -> None:
    required = {
        ResolutionKind.PYTHON_NAME_CONVENTION: LineageConfidence.INFERRED,
        ResolutionKind.BOUNDED_STATIC_SET: LineageConfidence.INFERRED,
        ResolutionKind.UNRESOLVED_NAME: LineageConfidence.UNRESOLVED,
        ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY: LineageConfidence.DYNAMIC,
    }.get(kind)
    if required is not None and confidence != required:
        raise ValueError(f"{kind.value} requires {required.value} confidence.")
    if kind in _EXACT_SURFACE_TARGET_RESOLUTIONS and confidence in {
        LineageConfidence.UNRESOLVED,
        LineageConfidence.DYNAMIC,
    }:
        raise ValueError("Exact resolution kinds cannot be unresolved or dynamic.")


def _validate_dynamic_boundary(
    kind: ResolutionKind,
    confidence: LineageConfidence,
    boundary: str | None,
) -> None:
    _validate_optional_token(boundary, "dynamic_boundary")
    if kind == ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and confidence == LineageConfidence.DYNAMIC and boundary is None:
        raise ValueError("DYNAMIC_RUNTIME_BOUNDARY requires dynamic_boundary.")


def _validate_provider(provider: ProviderRef | None) -> None:
    if provider is not None and not isinstance(provider, ProviderRef):
        raise TypeError("provider must be a ProviderRef or None.")


def _validate_surface_declaration_evidence(
    kind: SurfaceKind,
    declaration_evidence: SurfaceDeclarationEvidence | None,
) -> None:
    if declaration_evidence is not None and not isinstance(
        declaration_evidence, SurfaceDeclarationEvidence
    ):
        raise TypeError("declaration_evidence must be SurfaceDeclarationEvidence or None")
    if (
        declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
        and kind is not SurfaceKind.EXPORT
    ):
        raise ValueError(
            "LITERAL_ALL_DECLARATION is valid only for SurfaceKind.EXPORT"
        )


def claims_exact_semantic_target(
    resolution_kind: ResolutionKind,
    confidence: LineageConfidence,
) -> bool:
    return (
        confidence is LineageConfidence.CONFIRMED
        and (
            resolution_kind in _EXACT_SURFACE_TARGET_RESOLUTIONS
            or resolution_kind is ResolutionKind.RECEPTOR_PROVIDED
        )
    )


def _validate_materialized_surface_target(
    exposed: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
    resolution_kind: ResolutionKind,
    confidence: LineageConfidence,
) -> None:
    if claims_exact_semantic_target(resolution_kind, confidence) and isinstance(
        exposed, MaterializedOccurrenceRef
    ):
        raise ValueError(
            "confirmed exact semantic surface target cannot remain a bare local "
            "occurrence; requires SemanticEndpoint or exact symbolic boundary"
        )


def _validate_source_status(status: LineageFamilyStatus, reason: str | None) -> None:
    if status == LineageFamilyStatus.RESOURCE_LIMIT:
        _require_token(reason or "", "resource_limit_reason")
    elif reason is not None:
        raise ValueError("resource_limit_reason is only valid for resource_limit.")


def _require_sorted_unique(values: tuple[object, ...], label: str) -> None:
    if tuple(sorted(values)) != values or len(set(values)) != len(values):
        raise ValueError(f"{label} must be sorted and unique.")


def _require_materialized_anchor_reference(value: MaterializedOccurrenceRef) -> None:
    if not isinstance(value, MaterializedOccurrenceRef):
        raise TypeError("Materialized anchors require canonical occurrence references.")

def _require_materialized_reference(
    value: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
    label: str,
) -> None:
    if not isinstance(value, (MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint)):
        raise TypeError(f"{label} require canonical occurrence, symbolic boundary, or semantic endpoint references.")


def _require_slice_occurrence(
    value: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
    manifest: SourceLineageManifest,
) -> None:
    if isinstance(value, (MaterializedOccurrenceRef, MaterializedSymbolicRef)) and (
        value.source_key != manifest.source_key
        or value.source_fingerprint != manifest.source_fingerprint
    ):
        raise ValueError("Materialized source slice contains foreign local reference.")


__all__ = [
    "AnchorFact",
    "ExtractedAnchorFact",
    "ExtractedFlowFact",
    "ExtractedLineageSourceFacts",
    "ExtractedOccurrenceRef",
    "ExtractedSymbolicKind",
    "ExtractedSymbolicRef",
    "ProviderRef",
    "ExtractedSurfaceFact",
    "FlowFact",
    "LINEAGE_FACTS_SEMANTIC_VERSION",
    "LineageConfidence",
    "LineageFamilyStatus",
    "LineageRelation",
    "MaterializedAnchorFact",
    "MaterializedFlowFact",
    "MaterializedLineageSourceFacts",
    "MaterializedOccurrenceRef",
    "MaterializedSymbolicRef",
    "MaterializedSurfaceFact",
    "ParameterKind",
    "ResolutionKind",
    "SemanticEndpoint",
    "SemanticInterfaceDescriptor",
    "SemanticSlot",
    "SemanticSlotKind",
    "SourceLineageManifest",
    "SourceSpan",
    "SurfaceFact",
    "SurfaceDeclarationEvidence",
    "SurfaceKind",
    "build_class_attr_slot",
    "build_entrypoint_slot",
    "build_instance_attr_slot",
    "build_keyword_binding_slot",
    "build_module_global_slot",
    "build_parameter_value_slot",
    "build_positional_binding_slot",
    "build_public_slot",
    "build_return_slot",
    "parse_semantic_slot",
]

# Intentional public aliases make the three requested generic names phase-safe
# only through their explicit Extracted*/Materialized* forms.
AnchorFact = ExtractedAnchorFact | MaterializedAnchorFact
FlowFact = ExtractedFlowFact | MaterializedFlowFact
SurfaceFact = ExtractedSurfaceFact | MaterializedSurfaceFact
