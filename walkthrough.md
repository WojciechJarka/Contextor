# F2L D1K Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## COMPLETE_RELATION_MAPPING_PROOF

The primary-section mapping covers exactly every `LineageRelation`; a missing relation raises `ValueError` rather than falling back.

## PRIMARY_SECTION_PROOF

Semantic sections preserve the established exact scope-flow order while projecting bindings, parameters, calls/interfaces, returns, state, callbacks, and surface flows.

## UNCERTAINTY_ORTHOGONAL_PROOF

Dynamic and unresolved flows remain in their primary semantic section and additionally appear in `unresolved_dynamic`.

## SURFACE_COMPOSITION_PROOF

Surface flows and exact direct surface facts remain separate models in one `LineageSurfaceSection`.

## NESTED_SCOPE_EXCLUSION_PROOF

Sections consume only `lexical_scope_facts().flows`, excluding nested-scope and definition-default flows.

## AMBIGUOUS_ROOT_FAIL_CLOSED_PROOF

Ambiguous roots leave lexical scope flows empty, so every flow section is empty and completion is false.

## NO_TRAVERSAL_PROOF

The regression patches local traversal to fail; semantic projection still succeeds because it does not invoke traversal.

## TESTS_RUN

- `py_compile` for service and package exports: PASS.
- Focused pytest service/backend: PASS — 62 passed in 2.05s.
- `git diff --check`: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 5cbf0ee..3c08454 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -4,6 +4,7 @@ from dataclasses import dataclass

 from contextor.core.domain.lineage_facts import (
     LineageConfidence,
+    LineageRelation,
     MaterializedAnchorFact,
     MaterializedFlowFact,
     MaterializedOccurrenceRef,
@@ -30,6 +31,25 @@ _LEXICAL_SCOPE_KINDS = frozenset(
     }
 )

+_PRIMARY_SEMANTIC_SECTION_BY_RELATION = {
+    LineageRelation.BINDS: "bindings",
+    LineageRelation.ASSIGNS: "bindings",
+    LineageRelation.ALIASES: "bindings",
+    LineageRelation.CAPTURES: "bindings",
+    LineageRelation.ARGUMENT_TO_PARAMETER: "parameters",
+    LineageRelation.DEFAULTS_TO_PARAMETER: "parameters",
+    LineageRelation.CALL_RESULT: "calls_interfaces",
+    LineageRelation.INHERITS: "calls_interfaces",
+    LineageRelation.OVERRIDES: "calls_interfaces",
+    LineageRelation.RETURNS: "returns",
+    LineageRelation.READS_STATE: "state",
+    LineageRelation.WRITES_STATE: "state",
+    LineageRelation.CALLBACK_REGISTERS: "callbacks",
+    LineageRelation.CALLBACK_INVOKES: "callbacks",
+    LineageRelation.EXPOSES: "surfaces",
+    LineageRelation.DECLARES_PUBLIC_NAMES: "surfaces",
+}
+

 @dataclass(frozen=True)
 class ResolvedLineageTarget:
@@ -147,6 +167,31 @@ class LocalLineageTraversal:
         return self.scope.complete and self.seed_in_scope


+@dataclass(frozen=True)
+class LineageSurfaceSection:
+    flows: tuple[LineageFlowMatch, ...]
+    facts: tuple[LineageSurfaceMatch, ...]
+
+
+@dataclass(frozen=True)
+class SemanticLineageSections:
+    target: ResolvedLineageTarget
+    scope: LexicalScopeFacts
+    direct: DirectLineageFacts
+    bindings: tuple[LineageFlowMatch, ...]
+    parameters: tuple[LineageFlowMatch, ...]
+    calls_interfaces: tuple[LineageFlowMatch, ...]
+    returns: tuple[LineageFlowMatch, ...]
+    state: tuple[LineageFlowMatch, ...]
+    callbacks: tuple[LineageFlowMatch, ...]
+    surfaces: LineageSurfaceSection
+    unresolved_dynamic: tuple[LineageFlowMatch, ...]
+
+    @property
+    def complete(self) -> bool:
+        return self.scope.complete and self.direct.complete
+
+
 @dataclass(frozen=True)
 class DirectLineageFacts:
     target: ResolvedLineageTarget
@@ -439,6 +484,71 @@ class LineageQueryService:
             materialization_complete=materialization_complete,
         )

+    def semantic_sections(
+        self,
+        target: ResolvedLineageTarget,
+    ) -> SemanticLineageSections:
+        if not isinstance(target, ResolvedLineageTarget):
+            raise TypeError(
+                "target must be ResolvedLineageTarget."
+            )
+
+        scope = self.lexical_scope_facts(target)
+        direct = self.direct_facts(target)
+
+        buckets: dict[str, list[LineageFlowMatch]] = {
+            "bindings": [],
+            "parameters": [],
+            "calls_interfaces": [],
+            "returns": [],
+            "state": [],
+            "callbacks": [],
+            "surfaces": [],
+        }
+        unresolved_dynamic: list[LineageFlowMatch] = []
+
+        for match in scope.flows:
+            try:
+                section_name = (
+                    _PRIMARY_SEMANTIC_SECTION_BY_RELATION[
+                        match.flow.relation
+                    ]
+                )
+            except KeyError as exc:
+                raise ValueError(
+                    "Canonical lineage relation has no "
+                    "semantic section."
+                ) from exc
+
+            buckets[section_name].append(match)
+
+            if _terminal_flow_reason(match.flow) in {
+                "dynamic",
+                "unresolved",
+            }:
+                unresolved_dynamic.append(match)
+
+        return SemanticLineageSections(
+            target=target,
+            scope=scope,
+            direct=direct,
+            bindings=tuple(buckets["bindings"]),
+            parameters=tuple(buckets["parameters"]),
+            calls_interfaces=tuple(
+                buckets["calls_interfaces"]
+            ),
+            returns=tuple(buckets["returns"]),
+            state=tuple(buckets["state"]),
+            callbacks=tuple(buckets["callbacks"]),
+            surfaces=LineageSurfaceSection(
+                flows=tuple(buckets["surfaces"]),
+                facts=direct.surfaces,
+            ),
+            unresolved_dynamic=tuple(
+                unresolved_dynamic
+            ),
+        )
+

     def traverse_lexical_scope(
         self,
```

### contextor/core/lineage_query/__init__.py

```diff
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
index 29ed990..6f6a35a 100644
--- a/contextor/core/lineage_query/__init__.py
+++ b/contextor/core/lineage_query/__init__.py
@@ -12,11 +12,13 @@ from contextor.core.lineage_query.service import (
     LineageQueryService,
     LineageScopeRootMatch,
     LineageSurfaceMatch,
+    LineageSurfaceSection,
     LineageTargetResolution,
     LineageTraversalBoundary,
     LineageTraversalStep,
     LocalLineageTraversal,
     ResolvedLineageTarget,
+    SemanticLineageSections,
 )

 __all__ = [
@@ -30,10 +32,12 @@ __all__ = [
     "LineageQueryService",
     "LineageScopeRootMatch",
     "LineageSurfaceMatch",
+    "LineageSurfaceSection",
     "LineageTargetResolution",
     "LineageTraversalBoundary",
     "LineageTraversalStep",
     "LocalLineageTraversal",
     "RepositoryStateLineageBackend",
     "ResolvedLineageTarget",
+    "SemanticLineageSections",
 ]
```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 4172a0b..96fed8b 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -1557,3 +1557,375 @@ def test_local_traversal_reports_true_truncation_from_minimal_depth_frontier():
         "b_outer_call",
     )
     assert result.truncated is True
+def _append_scope_surface(backend, surface):
+    source = backend.get_source("pkg/target.py")
+    assert source is not None
+    backend._sources["pkg/target.py"] = replace(
+        source,
+        manifest=replace(
+            source.manifest,
+            surface_count=(
+                source.manifest.surface_count + 1
+            ),
+        ),
+        surfaces=tuple(
+            sorted(
+                (
+                    *source.surfaces,
+                    surface,
+                )
+            )
+        ),
+    )
+
+
+def _append_semantic_section_flow(
+    backend,
+    local_id,
+    relation,
+    *,
+    resolution_kind=ResolutionKind.LEXICAL_EXACT,
+    confidence=LineageConfidence.CONFIRMED,
+    dynamic_boundary=None,
+):
+    fp = "d" * 64
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            local_id,
+            MaterializedOccurrenceRef(
+                "pkg/target.py",
+                fp,
+                f"{local_id}-source",
+            ),
+            MaterializedOccurrenceRef(
+                "pkg/target.py",
+                fp,
+                f"{local_id}-target",
+            ),
+            relation,
+            SourceSpan(30, 0, 30, 5),
+            resolution_kind,
+            confidence,
+            dynamic_boundary=dynamic_boundary,
+            owner_local_id="outer",
+        ),
+    )
+
+
+def test_semantic_section_relation_mapping_covers_domain_exactly():
+    from contextor.core.lineage_query import service as service_module
+
+    assert set(
+        service_module._PRIMARY_SEMANTIC_SECTION_BY_RELATION
+    ) == set(LineageRelation)
+
+    assert (
+        service_module._PRIMARY_SEMANTIC_SECTION_BY_RELATION
+        == {
+            LineageRelation.BINDS: "bindings",
+            LineageRelation.ASSIGNS: "bindings",
+            LineageRelation.ALIASES: "bindings",
+            LineageRelation.CAPTURES: "bindings",
+            LineageRelation.ARGUMENT_TO_PARAMETER: "parameters",
+            LineageRelation.DEFAULTS_TO_PARAMETER: "parameters",
+            LineageRelation.CALL_RESULT: "calls_interfaces",
+            LineageRelation.INHERITS: "calls_interfaces",
+            LineageRelation.OVERRIDES: "calls_interfaces",
+            LineageRelation.RETURNS: "returns",
+            LineageRelation.READS_STATE: "state",
+            LineageRelation.WRITES_STATE: "state",
+            LineageRelation.CALLBACK_REGISTERS: "callbacks",
+            LineageRelation.CALLBACK_INVOKES: "callbacks",
+            LineageRelation.EXPOSES: "surfaces",
+            LineageRelation.DECLARES_PUBLIC_NAMES: "surfaces",
+        }
+    )
+
+
+def test_semantic_sections_project_exact_scope_flows_by_meaning():
+    service, backend, target = _lexical_scope_service()
+
+    _append_semantic_section_flow(
+        backend,
+        "c_parameter",
+        LineageRelation.ARGUMENT_TO_PARAMETER,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "d_return",
+        LineageRelation.RETURNS,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "e_state_read",
+        LineageRelation.READS_STATE,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "f_state_write",
+        LineageRelation.WRITES_STATE,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "g_callback_register",
+        LineageRelation.CALLBACK_REGISTERS,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "h_callback_invoke",
+        LineageRelation.CALLBACK_INVOKES,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "i_exposes",
+        LineageRelation.EXPOSES,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "j_alias",
+        LineageRelation.ALIASES,
+    )
+    _append_semantic_section_flow(
+        backend,
+        "k_inherits",
+        LineageRelation.INHERITS,
+    )
+
+    result = service.semantic_sections(target)
+
+    assert result.complete is True
+
+    assert tuple(
+        item.flow.local_id
+        for item in result.bindings
+    ) == (
+        "a_outer_bind",
+        "j_alias",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.parameters
+    ) == (
+        "c_parameter",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.calls_interfaces
+    ) == (
+        "b_outer_call",
+        "k_inherits",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.returns
+    ) == (
+        "d_return",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.state
+    ) == (
+        "e_state_read",
+        "f_state_write",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.callbacks
+    ) == (
+        "g_callback_register",
+        "h_callback_invoke",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.surfaces.flows
+    ) == (
+        "i_exposes",
+    )
+    assert result.unresolved_dynamic == ()
+
+
+def test_semantic_sections_keep_uncertainty_orthogonal_to_primary_section():
+    service, backend, target = _lexical_scope_service()
+
+    _append_semantic_section_flow(
+        backend,
+        "z_dynamic_assignment",
+        LineageRelation.ASSIGNS,
+        resolution_kind=(
+            ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+        ),
+        confidence=LineageConfidence.DYNAMIC,
+        dynamic_boundary="runtime-assignment",
+    )
+
+    result = service.semantic_sections(target)
+
+    assert tuple(
+        item.flow.local_id
+        for item in result.bindings
+    ) == (
+        "a_outer_bind",
+        "z_dynamic_assignment",
+    )
+    assert tuple(
+        item.flow.local_id
+        for item in result.unresolved_dynamic
+    ) == (
+        "z_dynamic_assignment",
+    )
+
+
+def test_semantic_sections_include_exact_artifact_surfaces():
+    service, backend, target = _lexical_scope_service()
+    fp = "d" * 64
+    outer = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "outer",
+    )
+
+    surface = MaterializedSurfaceFact(
+        "public-outer",
+        SurfaceKind.PUBLIC_SYMBOL,
+        outer,
+        SourceSpan(1, 0, 1, 8),
+        ResolutionKind.PYTHON_NAME_CONVENTION,
+        LineageConfidence.INFERRED,
+        "outer",
+        declaration_evidence=(
+            SurfaceDeclarationEvidence.STATIC_DECLARATION
+        ),
+    )
+    _append_scope_surface(backend, surface)
+
+    result = service.semantic_sections(target)
+
+    assert result.surfaces.flows == ()
+    assert tuple(
+        item.surface.local_id
+        for item in result.surfaces.facts
+    ) == (
+        "public-outer",
+    )
+    assert result.surfaces.facts[0].surface is surface
+
+
+def test_semantic_sections_do_not_pull_nested_scope_flows():
+    service, _, target = _lexical_scope_service()
+
+    result = service.semantic_sections(target)
+
+    all_section_flow_ids = {
+        item.flow.local_id
+        for section in (
+            result.bindings,
+            result.parameters,
+            result.calls_interfaces,
+            result.returns,
+            result.state,
+            result.callbacks,
+            result.surfaces.flows,
+        )
+        for item in section
+    }
+
+    assert "c_inner_return" not in all_section_flow_ids
+    assert (
+        "d_comprehension_assign"
+        not in all_section_flow_ids
+    )
+    assert "e_definition_default" not in all_section_flow_ids
+
+
+def test_semantic_sections_preserve_fail_closed_scope_state():
+    service, _, target = _lexical_scope_service(
+        flow_ownership=False,
+    )
+
+    result = service.semantic_sections(target)
+
+    assert result.scope.complete is False
+    assert result.complete is False
+    assert result.bindings
+    assert result.calls_interfaces
+
+
+def test_semantic_sections_preserve_ambiguous_root_fail_closed():
+    service, backend, target = _lexical_scope_service()
+    source = backend.get_source("pkg/target.py")
+    assert source is not None
+
+    duplicate_ref = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer-redefined",
+    )
+    duplicate_anchor = MaterializedAnchorFact(
+        "outer-redefined",
+        duplicate_ref,
+        "function",
+        SourceSpan(20, 0, 22, 1),
+        owner_local_id="module",
+    )
+    duplicate_binding = SemanticAnchorBinding(
+        target.artifact_id,
+        target.qualified_name,
+        duplicate_ref,
+    )
+
+    backend._sources["pkg/target.py"] = replace(
+        source,
+        manifest=replace(
+            source.manifest,
+            anchor_count=(
+                source.manifest.anchor_count + 1
+            ),
+        ),
+        anchors=tuple(
+            sorted(
+                (
+                    *source.anchors,
+                    duplicate_anchor,
+                )
+            )
+        ),
+        semantic_anchors=tuple(
+            sorted(
+                (
+                    *source.semantic_anchors,
+                    duplicate_binding,
+                )
+            )
+        ),
+    )
+
+    result = service.semantic_sections(target)
+
+    assert result.scope.root_ambiguous is True
+    assert result.scope.flows == ()
+    assert result.complete is False
+    assert result.bindings == ()
+    assert result.parameters == ()
+    assert result.calls_interfaces == ()
+    assert result.returns == ()
+    assert result.state == ()
+    assert result.callbacks == ()
+    assert result.surfaces.flows == ()
+
+
+def test_semantic_sections_never_use_local_traversal(monkeypatch):
+    service, _, target = _lexical_scope_service()
+
+    monkeypatch.setattr(
+        service,
+        "traverse_lexical_scope",
+        lambda *args, **kwargs: (_ for _ in ()).throw(
+            AssertionError("semantic projection used traversal")
+        ),
+    )
+
+    result = service.semantic_sections(target)
+
+    assert result.bindings
+    assert result.calls_interfaces
```
