# F2L D1E — canonical semantic-anchor seed

## STATUS

PASS

Domknięto canonical seed pomiędzy active artifact owner ID a source-local materialized anchor przez `SemanticAnchorBinding`. Binding powstaje wyłącznie dla exact qualified path z canonical `owner_local_id` chain oraz aktywnego `active_artifact_ids`; nie jest flow ani surface.

## FILES_CHANGED

- `contextor/core/domain/lineage_facts.py`
- `contextor/core/analysis/lineage_materialization.py`
- `contextor/core/live_state/store.py`
- `contextor/core/lineage_query/backend.py`
- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_materialization.py`
- `tests/test_lineage_state_lifecycle.py`
- `tests/analysis/test_lineage_query_backend.py`
- `tests/analysis/test_lineage_query_service.py`
- `walkthrough.md` — raport tasku; jego własny diff nie jest częścią `ACTUAL_DIFF`.

## SEMANTIC_ANCHOR_CONTRACT

- `SemanticAnchorBinding(owner_id, qualified_name, MaterializedOccurrenceRef)` wskazuje wyłącznie anchor z tego samego materialized slice.
- Materializer buduje binding dla `class`, `function`, `async_function`, `binding` i `import_binding`, tylko gdy owner path z `owner_local_id` chain jest exact active artifact identity.
- Niekanoniczny local ID, niepełny owner chain albo brak aktywnego ownera nie tworzą bindingu; nie powodują source/AST work.
- Re-resolution zmienia owner ID przez `active_artifact_ids` bez source work; usunięty owner usuwa binding.
- Direct query korzysta z bindingu jako canonical seed dla local anchor/flow/surface occurrence. `MaterializedSymbolicRef` nie jest wzmacniany.

## LEGACY_FAIL_CLOSED

- Nie zmieniono `LINEAGE_FACTS_SEMANTIC_VERSION`.
- Legacy snapshot bez `semantic_anchor_bindings_materialized` oraz `semantic_anchors` normalizuje się do odpowiednio `False` i `()`.
- `DirectLineageFacts.complete` jest `True` tylko przy family `fresh` oraz pełnej materializacji semantic-anchor bindings wszystkich slices.
- Retained facts w stale/deferred/resource_limit/not_materialized nie są ukrywane, ale nie są deklarowane jako kompletne.

## TESTS_RUN

| Command | Result |
|---|---|
| `.\\.venv\\Scripts\\python.exe -m pytest -q tests/analysis/test_lineage_materialization.py tests/test_lineage_state_lifecycle.py tests/analysis/test_lineage_query_backend.py tests/analysis/test_lineage_query_service.py` | PASS — `75 passed in 5.92s` |
| `.\\.venv\\Scripts\\python.exe -m py_compile contextor/core/domain/lineage_facts.py contextor/core/analysis/lineage_materialization.py contextor/core/live_state/store.py contextor/core/lineage_query/backend.py contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py` | PASS |
| `git diff --check` task files | PASS — bez błędów whitespace; dla nowych plików exit `1` z `--no-index` jest oczekiwanym sygnałem różnicy względem `/dev/null` |

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 6b2a284..68e67cd 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -343,6 +343,24 @@ class MaterializedAnchorFact:
         _require_materialized_anchor_reference(self.reference)


+@dataclass(frozen=True, order=True)
+class SemanticAnchorBinding:
+    owner_id: str
+    qualified_name: str
+    reference: MaterializedOccurrenceRef
+
+    def __post_init__(self) -> None:
+        _require_token(self.owner_id, "owner_id")
+        if self.qualified_name.count("::") != 1:
+            raise ValueError(
+                "Semantic anchor qualified_name must be canonical module::symbol."
+            )
+        module_name, symbol_name = self.qualified_name.split("::", 1)
+        _require_token(module_name, "semantic anchor module_name")
+        _require_token(symbol_name, "semantic anchor symbol_name")
+        _require_materialized_anchor_reference(self.reference)
+
+
 @dataclass(frozen=True, order=True)
 class MaterializedFlowFact:
     local_id: str
@@ -405,6 +423,7 @@ class SourceLineageManifest:
     flow_count: int
     surface_count: int
     resource_limit_reason: str | None = None
+    semantic_anchor_bindings_materialized: bool = False

     def __post_init__(self) -> None:
         _require_token(self.source_key, "source_key")
@@ -412,6 +431,10 @@ class SourceLineageManifest:
         _require_token(self.semantic_version, "semantic_version")
         if min(self.anchor_count, self.flow_count, self.surface_count) < 0:
             raise ValueError("Lineage manifest counts must be non-negative.")
+        if not isinstance(self.semantic_anchor_bindings_materialized, bool):
+            raise TypeError(
+                "semantic_anchor_bindings_materialized must be boolean."
+            )
         _validate_source_status(self.status, self.resource_limit_reason)


@@ -446,6 +469,7 @@ class MaterializedLineageSourceFacts:
     surfaces: tuple[MaterializedSurfaceFact, ...] = ()
     interface_descriptors: tuple[SemanticInterfaceDescriptor, ...] = ()
     semantic_endpoint_origins: tuple[SemanticEndpointOrigin, ...] = ()
+    semantic_anchors: tuple[SemanticAnchorBinding, ...] = ()

     def __post_init__(self) -> None:
         _require_sorted_unique(self.anchors, "anchors")
@@ -453,6 +477,11 @@ class MaterializedLineageSourceFacts:
         _require_sorted_unique(self.surfaces, "surfaces")
         _require_sorted_unique(self.interface_descriptors, "interface_descriptors")
         _require_sorted_unique(self.semantic_endpoint_origins, "semantic_endpoint_origins")
+        _require_sorted_unique(self.semantic_anchors, "semantic_anchors")
+        if self.semantic_anchors and not self.manifest.semantic_anchor_bindings_materialized:
+            raise ValueError(
+                "Semantic anchors require materialized semantic anchor bindings."
+            )
         if self.manifest.status == LineageFamilyStatus.FRESH:
             expected = (len(self.anchors), len(self.flows), len(self.surfaces))
             actual = (
@@ -469,6 +498,13 @@ class MaterializedLineageSourceFacts:
             _require_slice_occurrence(flow.target, self.manifest)
         for surface in self.surfaces:
             _require_slice_occurrence(surface.exposed, self.manifest)
+        anchor_references = {anchor.reference for anchor in self.anchors}
+        for semantic_anchor in self.semantic_anchors:
+            _require_slice_occurrence(semantic_anchor.reference, self.manifest)
+            if semantic_anchor.reference not in anchor_references:
+                raise ValueError(
+                    "Semantic anchor must reference a materialized anchor in its slice."
+                )
         self._validate_semantic_endpoint_origins()

     def _validate_semantic_endpoint_origins(self) -> None:
@@ -801,6 +837,7 @@ __all__ = [
     "MaterializedSurfaceFact",
     "ParameterKind",
     "ResolutionKind",
+    "SemanticAnchorBinding",
     "SemanticEndpoint",
     "SemanticInterfaceDescriptor",
     "SemanticSlot",
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index db4978c..b506350 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -7,6 +7,7 @@ from types import MappingProxyType
 from typing import Mapping

 from contextor.core.analysis.lineage_extraction_contracts import (
+    _module_name_from_source_key,
     parse_local_occurrence_id,
 )
 from contextor.core.domain.lineage_facts import (
@@ -24,6 +25,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedSurfaceFact,
     ParameterKind,
     ResolutionKind,
+    SemanticAnchorBinding,
     SemanticEndpoint,
     SemanticEndpointOrigin,
     SemanticEndpointRole,
@@ -132,6 +134,11 @@ def materialize_lineage_source_facts(
             for anchor in extracted.anchors
         )
     )
+    semantic_anchors = _semantic_anchor_bindings(
+        extracted,
+        resolution,
+        occurrence,
+    )
     flows = tuple(sorted(
         MaterializedFlowFact(
             flow.local_id,
@@ -188,6 +195,7 @@ def materialize_lineage_source_facts(
         len(flows),
         len(surfaces),
         extracted.resource_limit_reason,
+        semantic_anchor_bindings_materialized=True,
     )
     return MaterializedLineageSourceFacts(
         manifest,
@@ -196,6 +204,7 @@ def materialize_lineage_source_facts(
         surfaces,
         tuple(sorted(descriptors.values())),
         tuple(sorted(origins)),
+        semantic_anchors,
     )


@@ -317,6 +326,22 @@ def reresolve_materialized_lineage_source_facts(
         )
         for surface in materialized.surfaces
     ))
+    semantic_anchors = tuple(
+        sorted(
+            SemanticAnchorBinding(
+                owner_id,
+                binding.qualified_name,
+                binding.reference,
+            )
+            for binding in materialized.semantic_anchors
+            if (
+                owner_id := resolution.active_artifact_ids.get(
+                    binding.qualified_name
+                )
+            )
+            is not None
+        )
+    )
     return MaterializedLineageSourceFacts(
         materialized.manifest,
         materialized.anchors,
@@ -324,9 +349,82 @@ def reresolve_materialized_lineage_source_facts(
         surfaces,
         tuple(sorted(descriptors.values())),
         tuple(sorted(resolved_origins)),
+        semantic_anchors,
     )


+def _semantic_anchor_bindings(
+    extracted: ExtractedLineageSourceFacts,
+    resolution: LineageResolutionContext,
+    occurrence,
+) -> tuple[SemanticAnchorBinding, ...]:
+    anchors_by_id = {
+        anchor.local_id: anchor
+        for anchor in extracted.anchors
+    }
+    module_name = _module_name_from_source_key(extracted.source_key)
+    result: list[SemanticAnchorBinding] = []
+
+    for anchor in extracted.anchors:
+        if anchor.kind not in {
+            "class",
+            "function",
+            "async_function",
+            "binding",
+            "import_binding",
+        }:
+            continue
+
+        symbol_path = _anchor_symbol_path(anchor, anchors_by_id)
+        if symbol_path is None:
+            continue
+
+        qualified_name = f"{module_name}::{symbol_path}"
+        owner_id = resolution.active_artifact_ids.get(qualified_name)
+        if owner_id is None:
+            continue
+
+        result.append(
+            SemanticAnchorBinding(
+                owner_id,
+                qualified_name,
+                occurrence(anchor.local_id),
+            )
+        )
+
+    return tuple(sorted(result))
+
+
+def _anchor_symbol_path(anchor, anchors_by_id) -> str | None:
+    parts: list[str] = []
+    current = anchor
+    seen: set[str] = set()
+
+    while current.kind != "module":
+        if current.local_id in seen:
+            raise ValueError("Lineage anchor ownership contains a cycle.")
+        seen.add(current.local_id)
+
+        try:
+            _kind, _path, _ordinal, name = parse_local_occurrence_id(
+                current.local_id
+            )
+        except ValueError:
+            return None
+        if not name:
+            return None
+        parts.append(name)
+
+        owner_local_id = current.owner_local_id
+        if owner_local_id is None:
+            return None
+        current = anchors_by_id.get(owner_local_id)
+        if current is None:
+            return None
+
+    return ".".join(reversed(parts))
+
+
 def _semantic_origin(
     reference: ExtractedSymbolicRef,
     source_key: str,
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 4ff7f4f..74f258d 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -25,6 +25,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedSurfaceFact,
     ProviderRef,
     ResolutionKind,
+    SemanticAnchorBinding,
     SemanticEndpoint,
     SemanticEndpointOrigin,
     SemanticEndpointRole,
@@ -140,7 +141,16 @@ def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
         raise pickle.UnpicklingError("Invalid lineage source manifest.")
     if not isinstance(manifest.status, LineageFamilyStatus):
         raise pickle.UnpicklingError("Invalid lineage manifest status.")
-    rebuilt = replace(manifest)
+    rebuilt = replace(
+        manifest,
+        semantic_anchor_bindings_materialized=bool(
+            getattr(
+                manifest,
+                "semantic_anchor_bindings_materialized",
+                False,
+            )
+        ),
+    )
     if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
         raise pickle.UnpicklingError(
             "Unsupported lineage manifest semantic version."
@@ -211,6 +221,19 @@ def _revalidate_lineage_origin(origin: Any) -> SemanticEndpointOrigin:
     return replace(origin)


+def _revalidate_lineage_semantic_anchor(
+    binding: Any,
+) -> SemanticAnchorBinding:
+    if not isinstance(binding, SemanticAnchorBinding):
+        raise pickle.UnpicklingError(
+            "Invalid lineage semantic anchor binding."
+        )
+    return replace(
+        binding,
+        reference=_revalidate_lineage_endpoint(binding.reference),
+    )
+
+
 def _revalidate_lineage_slice(
     source_slice: Any,
 ) -> MaterializedLineageSourceFacts:
@@ -241,6 +264,10 @@ def _revalidate_lineage_slice(
             _revalidate_lineage_origin(item)
             for item in getattr(source_slice, "semantic_endpoint_origins", ())
         ),
+        semantic_anchors=tuple(
+            _revalidate_lineage_semantic_anchor(item)
+            for item in getattr(source_slice, "semantic_anchors", ())
+        ),
     )
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index c97d171..4dbcebc 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -24,6 +24,7 @@ from contextor.core.domain.lineage_facts import (
     ParameterKind,
     ProviderRef,
     ResolutionKind,
+    SemanticAnchorBinding,
     SemanticEndpoint,
     SemanticEndpointOrigin,
     SemanticEndpointRole,
@@ -72,6 +73,79 @@ def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
     assert first.flows[0].resolution_kind is ResolutionKind.LEXICAL_EXACT


+def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
+    span = SourceSpan(1, 0, 1, 1)
+    module_anchor = "occ:v1:module:root:i:0:n:pkg"
+    class_anchor = "occ:v1:class:0:i:0:n:Thing"
+    method_anchor = "occ:v1:function:0.0:i:0:n:run"
+    facts = _facts(
+        anchors=tuple(
+            sorted(
+                (
+                    ExtractedAnchorFact(module_anchor, "module", span),
+                    ExtractedAnchorFact(
+                        class_anchor,
+                        "class",
+                        span,
+                        module_anchor,
+                    ),
+                    ExtractedAnchorFact(
+                        method_anchor,
+                        "function",
+                        span,
+                        class_anchor,
+                    ),
+                )
+            )
+        ),
+    )
+    initial = materialize_lineage_source_facts(
+        facts,
+        _context(
+            artifacts={
+                "pkg.mod::Thing": "A1/1",
+                "pkg.mod::Thing.run": "A2/1",
+            }
+        ),
+    )
+
+    assert initial.manifest.semantic_anchor_bindings_materialized is True
+    assert initial.semantic_anchors == (
+        SemanticAnchorBinding(
+            "A1/1",
+            "pkg.mod::Thing",
+            MaterializedOccurrenceRef("pkg/mod.py", "sha256:test", class_anchor),
+        ),
+        SemanticAnchorBinding(
+            "A2/1",
+            "pkg.mod::Thing.run",
+            MaterializedOccurrenceRef("pkg/mod.py", "sha256:test", method_anchor),
+        ),
+    )
+
+    reresolved = reresolve_materialized_lineage_source_facts(
+        initial,
+        _context(
+            artifacts={
+                "pkg.mod::Thing": "A1/1",
+                "pkg.mod::Thing.run": "A2/2",
+            }
+        ),
+    )
+    assert tuple(binding.owner_id for binding in reresolved.semantic_anchors) == (
+        "A1/1",
+        "A2/2",
+    )
+
+    removed = reresolve_materialized_lineage_source_facts(
+        reresolved,
+        _context(artifacts={"pkg.mod::Thing": "A1/1"}),
+    )
+    assert tuple(binding.qualified_name for binding in removed.semantic_anchors) == (
+        "pkg.mod::Thing",
+    )
+
+
 def test_exact_active_return_parameter_and_descriptor_slots_are_materialized():
     span = SourceSpan(1, 0, 1, 1)
     owner = "A1/1"
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 1c1e37e..b1ffd80 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -37,6 +37,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedSurfaceFact,
     ProviderRef,
     ResolutionKind,
+    SemanticAnchorBinding,
     SemanticEndpoint,
     SemanticEndpointRole,
     SemanticInterfaceDescriptor,
@@ -69,6 +70,7 @@ def _lineage_slice() -> MaterializedLineageSourceFacts:
             1,
             1,
             1,
+            semantic_anchor_bindings_materialized=True,
         ),
         anchors=(
             MaterializedAnchorFact(
@@ -112,6 +114,9 @@ def _lineage_slice() -> MaterializedLineageSourceFacts:
                 "signature-digest",
             ),
         ),
+        semantic_anchors=(
+            SemanticAnchorBinding("A1", "pkg::thing", occurrence),
+        ),
     )


@@ -186,6 +191,32 @@ def test_snapshot_round_trip_preserves_lineage_endpoint_types_and_metadata(
     )
     assert loaded_slice.surfaces[0].provider == ProviderRef("fixture", "1")
     assert loaded_slice.surfaces[0].dynamic_boundary == "runtime-registration"
+    assert loaded_slice.semantic_anchors == source_slice.semantic_anchors
+
+
+def test_snapshot_legacy_semantic_anchor_fields_fail_closed(tmp_path):
+    source_slice = _lineage_slice()
+    object.__delattr__(
+        source_slice.manifest,
+        "semantic_anchor_bindings_materialized",
+    )
+    object.__delattr__(source_slice, "semantic_anchors")
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    save_snapshot(state, tmp_path, "legacy-semantic-anchors")
+
+    loaded, _ = load_snapshot(
+        tmp_path,
+        expected_state_id="legacy-semantic-anchors",
+    )
+    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]
+
+    assert loaded_slice.manifest.semantic_anchor_bindings_materialized is False
+    assert loaded_slice.semantic_anchors == ()


 @pytest.mark.parametrize(
diff --git a/contextor/core/lineage_query/backend.py b/contextor/core/lineage_query/backend.py
new file mode 100644
index 0000000..8cae93f
--- /dev/null
+++ b/contextor/core/lineage_query/backend.py
@@ -0,0 +1,211 @@
+from __future__ import annotations
+
+from collections.abc import Iterable, Mapping
+from dataclasses import dataclass
+from typing import Protocol, runtime_checkable
+
+from contextor.core.domain.lineage_facts import (
+    LineageFamilyStatus,
+    MaterializedLineageSourceFacts,
+    SemanticEndpoint,
+    SourceLineageManifest,
+)
+
+
+_MISSING = object()
+
+
+@dataclass(frozen=True)
+class LineageBackendMetadata:
+    revision: int | None
+    provenance: str
+    family_state: str
+    semantic_version: str | None
+    source_count: int
+    semantic_anchor_bindings_complete: bool
+
+
+@runtime_checkable
+class CanonicalLineageBackend(Protocol):
+    def metadata(self) -> LineageBackendMetadata: ...
+
+    def source_keys(self) -> tuple[str, ...]: ...
+
+    def get_source(
+        self,
+        source_key: str,
+    ) -> MaterializedLineageSourceFacts | None: ...
+
+    def get_manifest(
+        self,
+        source_key: str,
+    ) -> SourceLineageManifest | None: ...
+
+    def source_keys_for_owner(
+        self,
+        owner_id: str,
+    ) -> tuple[str, ...]: ...
+
+    def iter_sources(
+        self,
+        source_keys: Iterable[str] | None = None,
+    ) -> tuple[MaterializedLineageSourceFacts, ...]: ...
+
+
+class RepositoryStateLineageBackend:
+    """Read-only lineage backend over one already-hydrated canonical state."""
+
+    def __init__(self, state: object) -> None:
+        raw_sources = getattr(state, "lineage_facts_by_source", {})
+        if raw_sources is None:
+            raw_sources = {}
+        if not isinstance(raw_sources, Mapping):
+            raise TypeError("lineage_facts_by_source must be a mapping.")
+
+        for source_key in raw_sources:
+            if not isinstance(source_key, str) or not source_key:
+                raise TypeError(
+                    "lineage_facts_by_source keys must be non-empty strings."
+                )
+
+        self._state = state
+        self._sources = raw_sources
+
+    def metadata(self) -> LineageBackendMetadata:
+        raw_revision = getattr(self._state, "revision", None)
+        if raw_revision is not None and (
+            isinstance(raw_revision, bool) or not isinstance(raw_revision, int)
+        ):
+            raise TypeError("Canonical lineage revision must be an integer or None.")
+
+        raw_provenance = getattr(self._state, "provenance", "snapshot") or "snapshot"
+        if not isinstance(raw_provenance, str):
+            raise TypeError("Canonical lineage provenance must be a string.")
+
+        raw_family_state = getattr(
+            self._state,
+            "lineage_facts_state",
+            LineageFamilyStatus.NOT_MATERIALIZED.value,
+        )
+        try:
+            family_state = LineageFamilyStatus(raw_family_state).value
+        except (TypeError, ValueError) as exc:
+            raise ValueError(
+                "Canonical lineage family state is invalid."
+            ) from exc
+
+        semantic_version = getattr(
+            self._state,
+            "lineage_facts_semantic_version",
+            None,
+        )
+        if semantic_version is not None and (
+            not isinstance(semantic_version, str) or not semantic_version
+        ):
+            raise TypeError(
+                "Canonical lineage semantic version must be a non-empty string or None."
+            )
+
+        semantic_anchor_bindings_complete = (
+            family_state == LineageFamilyStatus.FRESH.value
+            and all(
+                self.get_source(source_key)
+                .manifest.semantic_anchor_bindings_materialized
+                for source_key in self.source_keys()
+            )
+        )
+        return LineageBackendMetadata(
+            revision=raw_revision,
+            provenance=raw_provenance,
+            family_state=family_state,
+            semantic_version=semantic_version,
+            source_count=len(self._sources),
+            semantic_anchor_bindings_complete=semantic_anchor_bindings_complete,
+        )
+
+    def source_keys(self) -> tuple[str, ...]:
+        return tuple(sorted(self._sources))
+
+    def get_source(
+        self,
+        source_key: str,
+    ) -> MaterializedLineageSourceFacts | None:
+        if not isinstance(source_key, str) or not source_key:
+            raise ValueError("source_key must be a non-empty string.")
+
+        value = self._sources.get(source_key, _MISSING)
+        if value is _MISSING:
+            return None
+        if not isinstance(value, MaterializedLineageSourceFacts):
+            raise TypeError(
+                f"Canonical lineage slice {source_key!r} has invalid type."
+            )
+        return value
+
+    def get_manifest(
+        self,
+        source_key: str,
+    ) -> SourceLineageManifest | None:
+        source = self.get_source(source_key)
+        return source.manifest if source is not None else None
+
+    def source_keys_for_owner(
+        self,
+        owner_id: str,
+    ) -> tuple[str, ...]:
+        if not isinstance(owner_id, str) or not owner_id:
+            raise ValueError("owner_id must be a non-empty string.")
+
+        matches: list[str] = []
+        for source_key in self.source_keys():
+            source = self.get_source(source_key)
+            assert source is not None
+            flow_match = any(
+                (
+                    isinstance(flow.source, SemanticEndpoint)
+                    and flow.source.owner_id == owner_id
+                )
+                or (
+                    isinstance(flow.target, SemanticEndpoint)
+                    and flow.target.owner_id == owner_id
+                )
+                for flow in source.flows
+            )
+            surface_match = any(
+                isinstance(surface.exposed, SemanticEndpoint)
+                and surface.exposed.owner_id == owner_id
+                for surface in source.surfaces
+            )
+            anchor_match = any(
+                binding.owner_id == owner_id
+                for binding in source.semantic_anchors
+            )
+            if flow_match or surface_match or anchor_match:
+                matches.append(source_key)
+        return tuple(matches)
+
+    def iter_sources(
+        self,
+        source_keys: Iterable[str] | None = None,
+    ) -> tuple[MaterializedLineageSourceFacts, ...]:
+        if source_keys is None:
+            keys = self.source_keys()
+        else:
+            if isinstance(source_keys, (str, bytes)):
+                raise TypeError("source_keys must be an iterable of source-key strings.")
+
+            requested: set[str] = set()
+            for source_key in source_keys:
+                if not isinstance(source_key, str) or not source_key:
+                    raise ValueError(
+                        "source_keys must contain only non-empty strings."
+                    )
+                requested.add(source_key)
+            keys = tuple(sorted(requested))
+
+        result: list[MaterializedLineageSourceFacts] = []
+        for source_key in keys:
+            source = self.get_source(source_key)
+            if source is not None:
+                result.append(source)
+        return tuple(result)
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
new file mode 100644
index 0000000..660f10c
--- /dev/null
+++ b/contextor/core/lineage_query/service.py
@@ -0,0 +1,311 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from contextor.core.domain.lineage_facts import (
+    MaterializedFlowFact,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
+    SemanticAnchorBinding,
+    SemanticEndpoint,
+)
+from contextor.core.lineage_query.backend import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+)
+from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog
+
+
+@dataclass(frozen=True)
+class ResolvedLineageTarget:
+    artifact_id: str
+    qualified_name: str
+    module_name: str
+    symbol_name: str
+    resolution: str
+
+
+@dataclass(frozen=True)
+class LineageTargetResolution:
+    status: str
+    query: str
+    target: ResolvedLineageTarget | None = None
+    candidates: tuple[ResolvedLineageTarget, ...] = ()
+
+
+@dataclass(frozen=True)
+class LineageAnchorMatch:
+    source_key: str
+    source_fingerprint: str
+    binding: SemanticAnchorBinding
+
+
+@dataclass(frozen=True)
+class LineageFlowMatch:
+    source_key: str
+    source_fingerprint: str
+    flow: MaterializedFlowFact
+
+
+@dataclass(frozen=True)
+class LineageSurfaceMatch:
+    source_key: str
+    source_fingerprint: str
+    surface: MaterializedSurfaceFact
+
+
+@dataclass(frozen=True)
+class DirectLineageFacts:
+    target: ResolvedLineageTarget
+    metadata: LineageBackendMetadata
+    anchors: tuple[LineageAnchorMatch, ...]
+    incoming: tuple[LineageFlowMatch, ...]
+    outgoing: tuple[LineageFlowMatch, ...]
+    surfaces: tuple[LineageSurfaceMatch, ...]
+
+    @property
+    def complete(self) -> bool:
+        return (
+            self.metadata.family_state == "fresh"
+            and self.metadata.semantic_anchor_bindings_complete
+        )
+
+
+class LineageQueryService:
+    def __init__(
+        self,
+        backend: CanonicalLineageBackend,
+        catalog: IndexCatalog,
+    ) -> None:
+        if not isinstance(backend, CanonicalLineageBackend):
+            raise TypeError("backend must implement CanonicalLineageBackend.")
+        if not isinstance(catalog, IndexCatalog):
+            raise TypeError("catalog must be IndexCatalog.")
+        self._backend = backend
+        self._catalog = catalog
+
+    def resolve_target(self, query: str) -> LineageTargetResolution:
+        if not isinstance(query, str):
+            raise TypeError("query must be a string.")
+
+        raw = query.strip()
+        if not raw:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        if ARTIFACT_ID_RE.fullmatch(raw):
+            artifact_id = raw[0].upper() + raw[1:]
+            qualified_name = self._catalog.artifacts.get(artifact_id)
+            if qualified_name is None:
+                return LineageTargetResolution(
+                    status="not_found",
+                    query=raw,
+                )
+            return LineageTargetResolution(
+                status="resolved",
+                query=raw,
+                target=_target(
+                    artifact_id,
+                    str(qualified_name),
+                    resolution="exact_id",
+                ),
+            )
+
+        if raw.count("::") != 1:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        module_name, symbol_name = raw.split("::", 1)
+        if not module_name or not symbol_name:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        matches = tuple(
+            _target(
+                str(artifact_id),
+                str(qualified_name),
+                resolution="exact_identity",
+            )
+            for artifact_id, qualified_name in sorted(
+                self._catalog.artifacts.items(),
+                key=lambda item: (str(item[1]), str(item[0])),
+            )
+            if str(qualified_name) == raw
+        )
+
+        if not matches:
+            return LineageTargetResolution(
+                status="not_found",
+                query=raw,
+            )
+        if len(matches) > 1:
+            return LineageTargetResolution(
+                status="ambiguous",
+                query=raw,
+                candidates=matches,
+            )
+        return LineageTargetResolution(
+            status="resolved",
+            query=raw,
+            target=matches[0],
+        )
+
+    def direct_facts(
+        self,
+        target: ResolvedLineageTarget,
+    ) -> DirectLineageFacts:
+        if not isinstance(target, ResolvedLineageTarget):
+            raise TypeError("target must be ResolvedLineageTarget.")
+
+        metadata = self._backend.metadata()
+        anchors: list[LineageAnchorMatch] = []
+        incoming: list[LineageFlowMatch] = []
+        outgoing: list[LineageFlowMatch] = []
+        surfaces: list[LineageSurfaceMatch] = []
+
+        source_keys = self._backend.source_keys_for_owner(target.artifact_id)
+        for source in self._backend.iter_sources(source_keys):
+            manifest = source.manifest
+            anchor_refs: set[MaterializedOccurrenceRef] = set()
+            for binding in source.semantic_anchors:
+                if binding.owner_id != target.artifact_id:
+                    continue
+                anchor_refs.add(binding.reference)
+                anchors.append(
+                    LineageAnchorMatch(
+                        source_key=manifest.source_key,
+                        source_fingerprint=manifest.source_fingerprint,
+                        binding=binding,
+                    )
+                )
+
+            for flow in source.flows:
+                match = LineageFlowMatch(
+                    source_key=manifest.source_key,
+                    source_fingerprint=manifest.source_fingerprint,
+                    flow=flow,
+                )
+                target_matches = (
+                    isinstance(flow.target, SemanticEndpoint)
+                    and flow.target.owner_id == target.artifact_id
+                ) or (
+                    isinstance(flow.target, MaterializedOccurrenceRef)
+                    and flow.target in anchor_refs
+                )
+                source_matches = (
+                    isinstance(flow.source, SemanticEndpoint)
+                    and flow.source.owner_id == target.artifact_id
+                ) or (
+                    isinstance(flow.source, MaterializedOccurrenceRef)
+                    and flow.source in anchor_refs
+                )
+                if target_matches:
+                    incoming.append(match)
+                if source_matches:
+                    outgoing.append(match)
+
+            for surface in source.surfaces:
+                if (
+                    (
+                        isinstance(surface.exposed, SemanticEndpoint)
+                        and surface.exposed.owner_id == target.artifact_id
+                    )
+                    or (
+                        isinstance(surface.exposed, MaterializedOccurrenceRef)
+                        and surface.exposed in anchor_refs
+                    )
+                ):
+                    surfaces.append(
+                        LineageSurfaceMatch(
+                            source_key=manifest.source_key,
+                            source_fingerprint=manifest.source_fingerprint,
+                            surface=surface,
+                        )
+                    )
+
+        anchors.sort(key=_anchor_match_key)
+        incoming.sort(key=_flow_match_key)
+        outgoing.sort(key=_flow_match_key)
+        surfaces.sort(key=_surface_match_key)
+
+        return DirectLineageFacts(
+            target=target,
+            metadata=metadata,
+            anchors=tuple(anchors),
+            incoming=tuple(incoming),
+            outgoing=tuple(outgoing),
+            surfaces=tuple(surfaces),
+        )
+
+
+def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
+    binding = match.binding
+    reference = binding.reference
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        binding.owner_id,
+        binding.qualified_name,
+        reference.local_id,
+    )
+
+
+def _flow_match_key(match: LineageFlowMatch) -> tuple:
+    flow = match.flow
+    evidence = flow.evidence
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        flow.local_id,
+        flow.relation.value,
+        evidence.start_line,
+        evidence.start_column,
+        evidence.end_line,
+        evidence.end_column,
+    )
+
+
+def _surface_match_key(match: LineageSurfaceMatch) -> tuple:
+    surface = match.surface
+    evidence = surface.evidence
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        surface.local_id,
+        surface.kind.value,
+        surface.declared_name,
+        evidence.start_line,
+        evidence.start_column,
+        evidence.end_line,
+        evidence.end_column,
+    )
+
+
+def _target(
+    artifact_id: str,
+    qualified_name: str,
+    *,
+    resolution: str,
+) -> ResolvedLineageTarget:
+    if qualified_name.count("::") != 1:
+        raise ValueError(
+            "Active artifact identity must be canonical module::symbol."
+        )
+    module_name, symbol_name = qualified_name.split("::", 1)
+    if not module_name or not symbol_name:
+        raise ValueError(
+            "Active artifact identity must be canonical module::symbol."
+        )
+    return ResolvedLineageTarget(
+        artifact_id=artifact_id,
+        qualified_name=qualified_name,
+        module_name=module_name,
+        symbol_name=symbol_name,
+        resolution=resolution,
+    )
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
new file mode 100644
index 0000000..8d9e3f5
--- /dev/null
+++ b/contextor/core/lineage_query/__init__.py
@@ -0,0 +1,27 @@
+from contextor.core.lineage_query.backend import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+    RepositoryStateLineageBackend,
+)
+from contextor.core.lineage_query.service import (
+    DirectLineageFacts,
+    LineageAnchorMatch,
+    LineageFlowMatch,
+    LineageQueryService,
+    LineageSurfaceMatch,
+    LineageTargetResolution,
+    ResolvedLineageTarget,
+)
+
+__all__ = [
+    "CanonicalLineageBackend",
+    "DirectLineageFacts",
+    "LineageAnchorMatch",
+    "LineageBackendMetadata",
+    "LineageFlowMatch",
+    "LineageQueryService",
+    "LineageSurfaceMatch",
+    "LineageTargetResolution",
+    "RepositoryStateLineageBackend",
+    "ResolvedLineageTarget",
+]
diff --git a/tests/analysis/test_lineage_query_backend.py b/tests/analysis/test_lineage_query_backend.py
new file mode 100644
index 0000000..c44686e
--- /dev/null
+++ b/tests/analysis/test_lineage_query_backend.py
@@ -0,0 +1,137 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    LineageFamilyStatus,
+    MaterializedLineageSourceFacts,
+    SourceLineageManifest,
+)
+from contextor.core.lineage_query import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+    RepositoryStateLineageBackend,
+)
+
+
+def _slice(source_key: str) -> MaterializedLineageSourceFacts:
+    return MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint="f" * 64,
+            semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=0,
+            flow_count=0,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+        )
+    )
+
+
+def _state():
+    source_a = _slice("pkg/a.py")
+    source_b = _slice("pkg/b.py")
+    return (
+        SimpleNamespace(
+            revision=11,
+            provenance="live",
+            lineage_facts_state="fresh",
+            lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+            lineage_facts_by_source={
+                "pkg/b.py": source_b,
+                "pkg/a.py": source_a,
+            },
+        ),
+        source_a,
+        source_b,
+    )
+
+
+def test_repository_state_backend_exposes_canonical_metadata():
+    state, _, _ = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    assert isinstance(backend, CanonicalLineageBackend)
+    assert backend.metadata() == LineageBackendMetadata(
+        revision=11,
+        provenance="live",
+        family_state="fresh",
+        semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+        source_count=2,
+        semantic_anchor_bindings_complete=True,
+    )
+
+
+def test_repository_state_backend_preserves_slice_identity_and_order():
+    state, source_a, source_b = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    assert backend.source_keys() == ("pkg/a.py", "pkg/b.py")
+    assert backend.get_source("pkg/a.py") is source_a
+    assert backend.get_manifest("pkg/a.py") is source_a.manifest
+    assert backend.get_source("pkg/missing.py") is None
+    assert backend.get_manifest("pkg/missing.py") is None
+
+    assert backend.iter_sources(
+        ["pkg/b.py", "pkg/a.py", "pkg/a.py", "pkg/missing.py"]
+    ) == (source_a, source_b)
+
+
+def test_repository_state_backend_defaults_to_not_materialized():
+    backend = RepositoryStateLineageBackend(SimpleNamespace())
+
+    assert backend.metadata() == LineageBackendMetadata(
+        revision=None,
+        provenance="snapshot",
+        family_state="not_materialized",
+        semantic_version=None,
+        source_count=0,
+        semantic_anchor_bindings_complete=False,
+    )
+    assert backend.source_keys() == ()
+    assert backend.iter_sources() == ()
+
+
+def test_repository_state_backend_rejects_invalid_storage_shape():
+    with pytest.raises(TypeError, match="must be a mapping"):
+        RepositoryStateLineageBackend(
+            SimpleNamespace(lineage_facts_by_source=[])
+        )
+
+    with pytest.raises(TypeError, match="non-empty strings"):
+        RepositoryStateLineageBackend(
+            SimpleNamespace(lineage_facts_by_source={1: _slice("pkg/a.py")})
+        )
+
+
+def test_repository_state_backend_fails_closed_on_invalid_slice():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_by_source={"pkg/a.py": object()}
+        )
+    )
+
+    with pytest.raises(TypeError, match="invalid type"):
+        backend.get_source("pkg/a.py")
+
+
+def test_repository_state_backend_rejects_invalid_family_state():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="pretend_fresh",
+            lineage_facts_by_source={},
+        )
+    )
+
+    with pytest.raises(ValueError, match="family state is invalid"):
+        backend.metadata()
+
+
+def test_repository_state_backend_rejects_string_as_source_collection():
+    state, _, _ = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(TypeError, match="iterable of source-key strings"):
+        backend.iter_sources("pkg/a.py")
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
new file mode 100644
index 0000000..b1d8155
--- /dev/null
+++ b/tests/analysis/test_lineage_query_service.py
@@ -0,0 +1,462 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.domain.lineage_facts import (
+    ExtractedSymbolicKind,
+    LineageConfidence,
+    LineageFamilyStatus,
+    LineageRelation,
+    MaterializedFlowFact,
+    MaterializedLineageSourceFacts,
+    MaterializedAnchorFact,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
+    MaterializedSymbolicRef,
+    ResolutionKind,
+    SemanticAnchorBinding,
+    SemanticEndpoint,
+    SourceLineageManifest,
+    SourceSpan,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
+)
+from contextor.core.lineage_query import (
+    LineageQueryService,
+    RepositoryStateLineageBackend,
+    ResolvedLineageTarget,
+)
+from contextor.core.report_query import IndexCatalog
+
+
+def _service(artifacts: dict[str, str]) -> LineageQueryService:
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_by_source={},
+        )
+    )
+    return LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts=artifacts,
+        ),
+    )
+
+
+def test_resolves_active_artifact_id_exactly():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("a17/2")
+
+    assert result.status == "resolved"
+    assert result.target == ResolvedLineageTarget(
+        artifact_id="A17/2",
+        qualified_name="pkg.mod::handler",
+        module_name="pkg.mod",
+        symbol_name="handler",
+        resolution="exact_id",
+    )
+    assert result.candidates == ()
+
+
+def test_resolves_exact_qualified_identity_to_same_owner():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "resolved"
+    assert result.target == ResolvedLineageTarget(
+        artifact_id="A17/2",
+        qualified_name="pkg.mod::handler",
+        module_name="pkg.mod",
+        symbol_name="handler",
+        resolution="exact_identity",
+    )
+
+
+def test_missing_syntactic_artifact_id_never_falls_back():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("A999/1")
+
+    assert result.status == "not_found"
+    assert result.target is None
+    assert result.candidates == ()
+
+
+@pytest.mark.parametrize(
+    "query",
+    [
+        "",
+        "handler",
+        "pkg.mod",
+        "pkg.mod::",
+        "::handler",
+        "pkg.mod::handler::extra",
+    ],
+)
+def test_non_exact_target_shapes_are_rejected(query):
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target(query)
+
+    assert result.status == "invalid"
+    assert result.target is None
+
+
+def test_resolution_is_case_sensitive_for_qualified_identity():
+    service = _service(
+        {"A17/2": "pkg.mod::Handler"}
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "not_found"
+
+
+def test_duplicate_active_identity_fails_closed_as_ambiguous():
+    service = _service(
+        {
+            "A18/1": "pkg.mod::handler",
+            "A17/2": "pkg.mod::handler",
+        }
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "ambiguous"
+    assert result.target is None
+    assert tuple(item.artifact_id for item in result.candidates) == (
+        "A17/2",
+        "A18/1",
+    )
+
+
+def test_recovery_catalog_is_not_used_for_lineage_resolution():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_by_source={},
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts={},
+            recovered_artifacts={
+                "A17/2": "pkg.mod::handler",
+            },
+        ),
+    )
+
+    by_id = service.resolve_target("A17/2")
+    by_name = service.resolve_target("pkg.mod::handler")
+
+    assert by_id.status == "not_found"
+    assert by_name.status == "not_found"
+
+
+def test_resolution_does_not_read_or_iterate_lineage_slices():
+    class ResolutionOnlyBackend:
+        def metadata(self):
+            raise AssertionError("resolution must not read lineage metadata")
+
+        def source_keys(self):
+            raise AssertionError("resolution must not enumerate lineage")
+
+        def get_source(self, source_key):
+            raise AssertionError("resolution must not read lineage")
+
+        def get_manifest(self, source_key):
+            raise AssertionError("resolution must not read lineage")
+
+        def source_keys_for_owner(self, owner_id):
+            raise AssertionError("resolution must not index lineage")
+
+        def iter_sources(self, source_keys=None):
+            raise AssertionError("resolution must not iterate lineage")
+
+    service = LineageQueryService(
+        ResolutionOnlyBackend(),
+        IndexCatalog(
+            modules={},
+            artifacts={"A17/2": "pkg.mod::handler"},
+        ),
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "resolved"
+    assert result.target is not None
+    assert result.target.artifact_id == "A17/2"
+
+
+def _direct_slice(
+    source_key: str,
+    fingerprint: str,
+    *,
+    anchors=(),
+    flows=(),
+    surfaces=(),
+    semantic_anchors=(),
+):
+    ordered_anchors = tuple(sorted(anchors))
+    ordered_flows = tuple(sorted(flows))
+    ordered_surfaces = tuple(sorted(surfaces))
+    return MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint=fingerprint,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=len(ordered_anchors),
+            flow_count=len(ordered_flows),
+            surface_count=len(ordered_surfaces),
+            semantic_anchor_bindings_materialized=True,
+        ),
+        anchors=ordered_anchors,
+        flows=ordered_flows,
+        surfaces=ordered_surfaces,
+        semantic_anchors=tuple(sorted(semantic_anchors)),
+    )
+
+
+def _direct_service(*, family_state="fresh"):
+    owner = "A17/2"
+    other_owner = "A99/1"
+    fp_a = "a" * 64
+    fp_b = "b" * 64
+    span = SourceSpan(4, 1, 4, 8)
+
+    symbolic_boundary = MaterializedSymbolicRef(
+        source_key="pkg/a.py",
+        source_fingerprint=fp_a,
+        kind=ExtractedSymbolicKind.PUBLIC_TARGET,
+        module_name="external.pkg",
+        symbol_name="unknown",
+    )
+
+    source_a = _direct_slice(
+        "pkg/a.py",
+        fp_a,
+        flows=(
+            MaterializedFlowFact(
+                "a_incoming",
+                symbolic_boundary,
+                SemanticEndpoint(owner),
+                LineageRelation.ALIASES,
+                span,
+                ResolutionKind.IMPORT_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+            MaterializedFlowFact(
+                "b_unrelated",
+                MaterializedOccurrenceRef("pkg/a.py", fp_a, "local"),
+                SemanticEndpoint(other_owner),
+                LineageRelation.ASSIGNS,
+                span,
+                ResolutionKind.LEXICAL_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+        ),
+    )
+
+    source_b = _direct_slice(
+        "pkg/b.py",
+        fp_b,
+        flows=(
+            MaterializedFlowFact(
+                "a_outgoing",
+                SemanticEndpoint(owner),
+                MaterializedOccurrenceRef("pkg/b.py", fp_b, "consumer"),
+                LineageRelation.CALL_RESULT,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+        ),
+        surfaces=(
+            MaterializedSurfaceFact(
+                "surface_target",
+                SurfaceKind.PUBLIC_SYMBOL,
+                SemanticEndpoint(owner),
+                span,
+                ResolutionKind.LEXICAL_EXACT,
+                LineageConfidence.CONFIRMED,
+                "handler",
+                declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
+            ),
+        ),
+    )
+
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            revision=21,
+            provenance="live",
+            lineage_facts_state=family_state,
+            lineage_facts_semantic_version="1",
+            lineage_facts_by_source={
+                "pkg/b.py": source_b,
+                "pkg/a.py": source_a,
+            },
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts={
+                owner: "pkg.target::handler",
+                other_owner: "pkg.other::thing",
+            },
+        ),
+    )
+    resolved = service.resolve_target(owner)
+    assert resolved.status == "resolved"
+    assert resolved.target is not None
+    return service, backend, resolved.target, symbolic_boundary
+
+
+def test_backend_returns_only_candidate_sources_for_semantic_owner():
+    _, backend, target, _ = _direct_service()
+
+    assert backend.source_keys_for_owner(target.artifact_id) == (
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+    assert backend.source_keys_for_owner("A404/1") == ()
+
+
+def test_direct_facts_return_exact_incoming_outgoing_and_surface_matches():
+    service, _, target, symbolic_boundary = _direct_service()
+
+    result = service.direct_facts(target)
+
+    assert result.target is target
+    assert result.metadata.revision == 21
+    assert result.complete is True
+
+    assert tuple(item.source_key for item in result.incoming) == (
+        "pkg/a.py",
+    )
+    assert tuple(item.flow.local_id for item in result.incoming) == (
+        "a_incoming",
+    )
+    assert result.incoming[0].flow.source == symbolic_boundary
+
+    assert tuple(item.source_key for item in result.outgoing) == (
+        "pkg/b.py",
+    )
+    assert tuple(item.flow.local_id for item in result.outgoing) == (
+        "a_outgoing",
+    )
+
+    assert tuple(item.source_key for item in result.surfaces) == (
+        "pkg/b.py",
+    )
+    assert tuple(item.surface.local_id for item in result.surfaces) == (
+        "surface_target",
+    )
+
+
+def test_direct_facts_do_not_match_unrelated_semantic_owner():
+    service, _, _, _ = _direct_service()
+    resolved = service.resolve_target("A99/1")
+    assert resolved.status == "resolved"
+    assert resolved.target is not None
+
+    result = service.direct_facts(resolved.target)
+
+    assert tuple(item.flow.local_id for item in result.incoming) == (
+        "b_unrelated",
+    )
+    assert result.outgoing == ()
+    assert result.surfaces == ()
+
+
+def test_direct_facts_expose_nonfresh_family_fail_closed():
+    service, _, target, _ = _direct_service(family_state="stale")
+
+    result = service.direct_facts(target)
+
+    assert result.metadata.family_state == "stale"
+    assert result.complete is False
+    assert result.incoming
+    assert result.outgoing
+
+
+def test_direct_facts_seed_ordinary_symbol_from_semantic_anchor_binding():
+    owner = "A17/2"
+    source_key = "pkg/target.py"
+    fingerprint = "c" * 64
+    span = SourceSpan(4, 1, 4, 8)
+    occurrence = MaterializedOccurrenceRef(source_key, fingerprint, "handler")
+    anchor = MaterializedAnchorFact("handler", occurrence, "function", span)
+    binding = SemanticAnchorBinding(owner, "pkg.target::handler", occurrence)
+    surface = MaterializedSurfaceFact(
+        "public-handler",
+        SurfaceKind.PUBLIC_SYMBOL,
+        occurrence,
+        span,
+        ResolutionKind.UNRESOLVED_NAME,
+        LineageConfidence.UNRESOLVED,
+        "handler",
+    )
+    source = _direct_slice(
+        source_key,
+        fingerprint,
+        anchors=(anchor,),
+        surfaces=(surface,),
+        semantic_anchors=(binding,),
+    )
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_semantic_version="1",
+            lineage_facts_by_source={source_key: source},
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(modules={}, artifacts={owner: "pkg.target::handler"}),
+    )
+    resolved = service.resolve_target(owner)
+    assert resolved.target is not None
+
+    result = service.direct_facts(resolved.target)
+
+    assert result.complete is True
+    assert tuple(item.binding for item in result.anchors) == (binding,)
+    assert tuple(item.surface.local_id for item in result.surfaces) == (
+        "public-handler",
+    )
+    assert result.incoming == ()
+    assert result.outgoing == ()
+
+
+def test_direct_facts_are_incomplete_when_fresh_slice_lacks_anchor_materialization():
+    service, backend, target, _ = _direct_service()
+    source = backend.get_source("pkg/a.py")
+    assert source is not None
+    object.__setattr__(
+        source.manifest,
+        "semantic_anchor_bindings_materialized",
+        False,
+    )
+
+    result = service.direct_facts(target)
+
+    assert result.metadata.family_state == "fresh"
+    assert result.metadata.semantic_anchor_bindings_complete is False
+    assert result.complete is False
```

## GATE

Zatrzymano po D1E. Oczekiwana jest komenda `proceduj` przed kolejnym krokiem.
