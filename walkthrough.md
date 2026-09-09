FILES_CHANGED=
contextor/core/domain/lineage_facts.py
contextor/core/domain/__init__.py
tests/domain/test_lineage_facts.py

TESTS_RUN=
pytest tests/domain/test_lineage_facts.py -q -> PATH executable unavailable (`pytest` not recognized)
.venv\\Scripts\\python.exe -m pytest tests/domain/test_lineage_facts.py -q

TEST_RESULTS=
51 passed in 9.09s

ACTUAL_DIFF=
diff --git a/contextor/core/domain/__init__.py b/contextor/core/domain/__init__.py
index be7cb2f..ba97aa8 100644
--- a/contextor/core/domain/__init__.py
+++ b/contextor/core/domain/__init__.py
@@ -53,6 +53,7 @@ from .lineage_facts import (
     SemanticSlotKind,
     SourceLineageManifest,
     SourceSpan,
+    SurfaceDeclarationEvidence,
     SurfaceKind,
     build_class_attr_slot,
     build_entrypoint_slot,
@@ -101,6 +102,7 @@ __all__ = [
     "SemanticSlotKind",
     "SourceLineageManifest",
     "SourceSpan",
+    "SurfaceDeclarationEvidence",
     "SurfaceKind",
     "build_class_attr_slot",
     "build_entrypoint_slot",
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 74e787f..629b284 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -67,6 +67,11 @@ class SurfaceKind(str, Enum):
     REGISTRATION = "REGISTRATION"
 
 
+class SurfaceDeclarationEvidence(str, Enum):
+    STATIC_DECLARATION = "STATIC_DECLARATION"
+    LITERAL_ALL_DECLARATION = "LITERAL_ALL_DECLARATION"
+
+
 class LineageFamilyStatus(str, Enum):
     NOT_MATERIALIZED = "not_materialized"
     FRESH = "fresh"
@@ -238,6 +243,7 @@ class ExtractedSurfaceFact:
     declared_name: str
     dynamic_boundary: str | None = None
     provider: ProviderRef | None = None
+    declaration_evidence: SurfaceDeclarationEvidence | None = None
 
     def __post_init__(self) -> None:
         _require_token(self.local_id, "local_id")
@@ -247,6 +253,7 @@ class ExtractedSurfaceFact:
         _validate_confidence(self.resolution_kind, self.confidence)
         _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
         _validate_provider(self.provider)
+        _validate_surface_declaration_evidence(self.kind, self.declaration_evidence)
 
 
 @dataclass(frozen=True)
@@ -318,6 +325,7 @@ class MaterializedSurfaceFact:
     declared_name: str
     dynamic_boundary: str | None = None
     provider: ProviderRef | None = None
+    declaration_evidence: SurfaceDeclarationEvidence | None = None
 
     def __post_init__(self) -> None:
         _require_token(self.local_id, "local_id")
@@ -326,6 +334,12 @@ class MaterializedSurfaceFact:
         _validate_confidence(self.resolution_kind, self.confidence)
         _validate_dynamic_boundary(self.resolution_kind, self.confidence, self.dynamic_boundary)
         _validate_provider(self.provider)
+        _validate_surface_declaration_evidence(self.kind, self.declaration_evidence)
+        _validate_materialized_surface_target(
+            self.exposed,
+            self.resolution_kind,
+            self.confidence,
+        )
 
 
 @dataclass(frozen=True)
@@ -365,7 +379,13 @@ class SemanticInterfaceDescriptor:
 
 @dataclass(frozen=True)
 class MaterializedLineageSourceFacts:
-    """Canonical source slice; all endpoints use resolved semantic identities."""
+    """Canonical source slice with local occurrences and semantic boundaries.
+
+    A ``MaterializedOccurrenceRef`` is a canonical source-local occurrence
+    belonging to this manifest's source slice.  A ``SemanticEndpoint`` is a
+    semantic/interface boundary.  Foreign or cross-source occurrences cannot
+    be stable cross-source endpoints.
+    """
 
     manifest: SourceLineageManifest
     anchors: tuple[MaterializedAnchorFact, ...] = ()
@@ -557,6 +577,16 @@ def _validate_optional_token(value: str | None, label: str) -> None:
         _require_token(value, label)
 
 
+_EXACT_SURFACE_TARGET_RESOLUTIONS = frozenset({
+    ResolutionKind.LEXICAL_EXACT,
+    ResolutionKind.IMPORT_EXACT,
+    ResolutionKind.CALL_EXACT,
+    ResolutionKind.SIGNATURE_EXACT,
+    ResolutionKind.STATIC_MRO_EXACT,
+    ResolutionKind.LITERAL_CONTAINER_EXACT,
+})
+
+
 def _validate_confidence(kind: ResolutionKind, confidence: LineageConfidence) -> None:
     required = {
         ResolutionKind.PYTHON_NAME_CONVENTION: LineageConfidence.INFERRED,
@@ -566,14 +596,10 @@ def _validate_confidence(kind: ResolutionKind, confidence: LineageConfidence) ->
     }.get(kind)
     if required is not None and confidence != required:
         raise ValueError(f"{kind.value} requires {required.value} confidence.")
-    if kind in {
-        ResolutionKind.LEXICAL_EXACT,
-        ResolutionKind.IMPORT_EXACT,
-        ResolutionKind.CALL_EXACT,
-        ResolutionKind.SIGNATURE_EXACT,
-        ResolutionKind.STATIC_MRO_EXACT,
-        ResolutionKind.LITERAL_CONTAINER_EXACT,
-    } and confidence in {LineageConfidence.UNRESOLVED, LineageConfidence.DYNAMIC}:
+    if kind in _EXACT_SURFACE_TARGET_RESOLUTIONS and confidence in {
+        LineageConfidence.UNRESOLVED,
+        LineageConfidence.DYNAMIC,
+    }:
         raise ValueError("Exact resolution kinds cannot be unresolved or dynamic.")
 
 
@@ -592,6 +618,49 @@ def _validate_provider(provider: ProviderRef | None) -> None:
         raise TypeError("provider must be a ProviderRef or None.")
 
 
+def _validate_surface_declaration_evidence(
+    kind: SurfaceKind,
+    declaration_evidence: SurfaceDeclarationEvidence | None,
+) -> None:
+    if declaration_evidence is not None and not isinstance(
+        declaration_evidence, SurfaceDeclarationEvidence
+    ):
+        raise TypeError("declaration_evidence must be SurfaceDeclarationEvidence or None")
+    if (
+        declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
+        and kind is not SurfaceKind.EXPORT
+    ):
+        raise ValueError(
+            "LITERAL_ALL_DECLARATION is valid only for SurfaceKind.EXPORT"
+        )
+
+
+def _claims_exact_semantic_target(
+    resolution_kind: ResolutionKind,
+    confidence: LineageConfidence,
+) -> bool:
+    return (
+        confidence is LineageConfidence.CONFIRMED
+        and (
+            resolution_kind in _EXACT_SURFACE_TARGET_RESOLUTIONS
+            or resolution_kind is ResolutionKind.RECEPTOR_PROVIDED
+        )
+    )
+
+
+def _validate_materialized_surface_target(
+    exposed: MaterializedOccurrenceRef | SemanticEndpoint,
+    resolution_kind: ResolutionKind,
+    confidence: LineageConfidence,
+) -> None:
+    if _claims_exact_semantic_target(resolution_kind, confidence) and not isinstance(
+        exposed, SemanticEndpoint
+    ):
+        raise ValueError(
+            "confirmed exact semantic surface target requires SemanticEndpoint"
+        )
+
+
 def _validate_source_status(status: LineageFamilyStatus, reason: str | None) -> None:
     if status == LineageFamilyStatus.RESOURCE_LIMIT:
         _require_token(reason or "", "resource_limit_reason")
@@ -652,6 +721,7 @@ __all__ = [
     "SourceLineageManifest",
     "SourceSpan",
     "SurfaceFact",
+    "SurfaceDeclarationEvidence",
     "SurfaceKind",
     "build_class_attr_slot",
     "build_entrypoint_slot",
diff --git a/tests/domain/test_lineage_facts.py b/tests/domain/test_lineage_facts.py
index 96c912d..72d6536 100644
--- a/tests/domain/test_lineage_facts.py
+++ b/tests/domain/test_lineage_facts.py
@@ -5,6 +5,7 @@ import sys
 import pytest
 
 from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
     ExtractedAnchorFact,
     ExtractedFlowFact,
     ExtractedLineageSourceFacts,
@@ -26,6 +27,7 @@ from contextor.core.domain.lineage_facts import (
     SemanticEndpoint,
     SourceLineageManifest,
     SourceSpan,
+    SurfaceDeclarationEvidence,
     SurfaceKind,
     build_class_attr_slot,
     build_instance_attr_slot,
@@ -114,7 +116,7 @@ def test_materialized_slice_rejects_foreign_occurrences_but_allows_semantic_boun
         MaterializedLineageSourceFacts(source_manifest, (), (MaterializedFlowFact("f", endpoint, foreign, LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED),), ())
     surface_manifest = SourceLineageManifest("a.py", "a", "1", LineageFamilyStatus.FRESH, 0, 0, 1)
     with pytest.raises(ValueError, match="foreign occurrence"):
-        MaterializedLineageSourceFacts(surface_manifest, (), (), (MaterializedSurfaceFact("s", SurfaceKind.EXPORT, foreign, span, ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED, "x"),))
+        MaterializedLineageSourceFacts(surface_manifest, (), (), (MaterializedSurfaceFact("s", SurfaceKind.EXPORT, foreign, span, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, "x"),))
 
 
 def test_provider_pair_and_dynamic_surface_boundary_contract():
@@ -245,3 +247,209 @@ def test_domain_module_does_not_import_or_construct_persistent_registry():
     module = sys.modules["contextor.core.domain.lineage_facts"]
     assert "PersistentIdentityRegistry" not in vars(module)
     assert not any(name.endswith("persistent_registry") for name in sys.modules if name.startswith("contextor.core.domain.lineage_facts"))
+
+
+@pytest.mark.parametrize(
+    ("declaration_evidence", "resolution_kind", "confidence", "dynamic_boundary"),
+    [
+        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED, None),
+        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
+        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
+        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
+        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
+        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.LITERAL_CONTAINER_EXACT, LineageConfidence.CONFIRMED, None),
+        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
+        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
+        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
+        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
+        (None, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
+    ],
+)
+def test_surface_declaration_evidence_and_target_resolution_are_orthogonal(
+    declaration_evidence,
+    resolution_kind,
+    confidence,
+    dynamic_boundary,
+):
+    kind = (
+        SurfaceKind.EXPORT
+        if declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
+        else SurfaceKind.PUBLIC_SYMBOL
+    )
+    surface = ExtractedSurfaceFact(
+        "surface",
+        kind,
+        ExtractedOccurrenceRef("occurrence"),
+        SourceSpan(1, 0, 1, 1),
+        resolution_kind,
+        confidence,
+        "name",
+        dynamic_boundary=dynamic_boundary,
+        declaration_evidence=declaration_evidence,
+    )
+    assert surface.declaration_evidence is declaration_evidence
+
+
+def test_literal_all_declaration_requires_export_surface_kind():
+    span = SourceSpan(1, 0, 1, 1)
+    ExtractedSurfaceFact(
+        "export",
+        SurfaceKind.EXPORT,
+        ExtractedOccurrenceRef("occurrence"),
+        span,
+        ResolutionKind.LITERAL_CONTAINER_EXACT,
+        LineageConfidence.CONFIRMED,
+        "name",
+        declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
+    )
+    for kind in (
+        SurfaceKind.PUBLIC_SYMBOL,
+        SurfaceKind.REEXPORT,
+        SurfaceKind.ENTRYPOINT,
+        SurfaceKind.REGISTRATION,
+    ):
+        with pytest.raises(ValueError, match="LITERAL_ALL_DECLARATION"):
+            ExtractedSurfaceFact(
+                "not-export",
+                kind,
+                ExtractedOccurrenceRef("occurrence"),
+                span,
+                ResolutionKind.UNRESOLVED_NAME,
+                LineageConfidence.UNRESOLVED,
+                "name",
+                declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
+            )
+
+
+@pytest.mark.parametrize(
+    "resolution_kind",
+    [
+        ResolutionKind.LEXICAL_EXACT,
+        ResolutionKind.IMPORT_EXACT,
+        ResolutionKind.CALL_EXACT,
+        ResolutionKind.SIGNATURE_EXACT,
+        ResolutionKind.STATIC_MRO_EXACT,
+        ResolutionKind.LITERAL_CONTAINER_EXACT,
+    ],
+)
+def test_materialized_confirmed_exact_surface_targets_require_semantic_endpoint(
+    resolution_kind,
+):
+    span = SourceSpan(1, 0, 1, 1)
+    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
+    with pytest.raises(ValueError, match="confirmed exact semantic surface target"):
+        MaterializedSurfaceFact(
+            "surface",
+            SurfaceKind.EXPORT,
+            occurrence,
+            span,
+            resolution_kind,
+            LineageConfidence.CONFIRMED,
+            "name",
+        )
+    surface = MaterializedSurfaceFact(
+        "surface",
+        SurfaceKind.EXPORT,
+        SemanticEndpoint("artifact/1"),
+        span,
+        resolution_kind,
+        LineageConfidence.CONFIRMED,
+        "name",
+    )
+    assert isinstance(surface.exposed, SemanticEndpoint)
+
+
+def test_materialized_confirmed_receptor_target_requires_semantic_endpoint():
+    span = SourceSpan(1, 0, 1, 1)
+    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
+    with pytest.raises(ValueError, match="confirmed exact semantic surface target"):
+        MaterializedSurfaceFact(
+            "surface",
+            SurfaceKind.REGISTRATION,
+            occurrence,
+            span,
+            ResolutionKind.RECEPTOR_PROVIDED,
+            LineageConfidence.CONFIRMED,
+            "name",
+        )
+    surface = MaterializedSurfaceFact(
+        "surface",
+        SurfaceKind.REGISTRATION,
+        SemanticEndpoint("artifact/1"),
+        span,
+        ResolutionKind.RECEPTOR_PROVIDED,
+        LineageConfidence.CONFIRMED,
+        "name",
+    )
+    assert isinstance(surface.exposed, SemanticEndpoint)
+
+
+def test_exact_reexport_uses_static_declaration_and_semantic_endpoint():
+    surface = MaterializedSurfaceFact(
+        "reexport",
+        SurfaceKind.REEXPORT,
+        SemanticEndpoint("artifact/1"),
+        SourceSpan(1, 0, 1, 1),
+        ResolutionKind.IMPORT_EXACT,
+        LineageConfidence.CONFIRMED,
+        "name",
+        declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
+    )
+    assert surface.declaration_evidence is SurfaceDeclarationEvidence.STATIC_DECLARATION
+
+
+@pytest.mark.parametrize(
+    ("resolution_kind", "confidence", "dynamic_boundary"),
+    [
+        (ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
+        (ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
+        (ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
+    ],
+)
+def test_nonexact_materialized_surface_targets_can_remain_local_occurrences(
+    resolution_kind,
+    confidence,
+    dynamic_boundary,
+):
+    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
+    surface = MaterializedSurfaceFact(
+        "surface",
+        SurfaceKind.EXPORT,
+        occurrence,
+        SourceSpan(1, 0, 1, 1),
+        resolution_kind,
+        confidence,
+        "name",
+        dynamic_boundary=dynamic_boundary,
+    )
+    assert surface.exposed is occurrence
+
+
+def test_surface_declaration_evidence_rejects_invalid_type_and_preserves_convention_guard():
+    span = SourceSpan(1, 0, 1, 1)
+    with pytest.raises(TypeError, match="declaration_evidence"):
+        ExtractedSurfaceFact(
+            "surface",
+            SurfaceKind.EXPORT,
+            ExtractedOccurrenceRef("occurrence"),
+            span,
+            ResolutionKind.UNRESOLVED_NAME,
+            LineageConfidence.UNRESOLVED,
+            "name",
+            declaration_evidence="STATIC_DECLARATION",  # type: ignore[arg-type]
+        )
+    with pytest.raises(ValueError, match="PYTHON_NAME_CONVENTION"):
+        ExtractedSurfaceFact(
+            "surface",
+            SurfaceKind.PUBLIC_SYMBOL,
+            ExtractedOccurrenceRef("occurrence"),
+            span,
+            ResolutionKind.PYTHON_NAME_CONVENTION,
+            LineageConfidence.CONFIRMED,
+            "name",
+            declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
+        )
+
+
+def test_lineage_facts_semantic_version_remains_initial_version():
+    assert LINEAGE_FACTS_SEMANTIC_VERSION == "1"

