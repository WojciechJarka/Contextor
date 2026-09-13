# F2L D1N3b2x Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## MODULE_OWNER_PROOF

State flow contains canonical module owner `17/2`; named output maps it to `pkg.mod`, indexed output preserves the ID.

## ARTIFACT_OWNER_PROOF

Connection semantic endpoint preserves artifact owner `A17/2` in indexed output and maps it to `pkg.mod::handler` in named output.

## MIXED_NAMED_PROOF

One named payload resolves both module and artifact owner identities using `owner_names`.

## MIXED_INDEXED_RESOLVER_PROOF

Indexed resolver declares `id_kinds: ["module", "artifact"]` through existing `lookup_index_entries`.

## SLOT_OPAQUE_PROOF

Module-global and artifact-return slots remain unchanged opaque canonical strings.

## AUTO_MISSING_OWNER_PROOF

Named/auto diagnostics list missing module and artifact owners deterministically.

## TESTS_RUN

```text
tests/mcp/test_lineage_response.py tests/analysis/test_lineage_live_query.py tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py
136 passed in 2.94s

tests/mcp/test_lineage_response.py
27 passed in 1.80s

py_compile and scoped git diff --check
PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/lineage_response.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
index c8f60af..30a9ac5 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -232,24 +232,24 @@ def build_symbol_lineage_represented_payload(
     selected: SelectedSymbolLineageFacts,
     *,
     representation: str = "auto",
-    artifact_names: Mapping[str, str] | None = None,
+    owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
 ) -> dict:
     if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
     if not isinstance(representation, str): raise TypeError("representation must be a string.")
     requested = representation.strip().lower()
     if not mcp_rep.is_supported_representation(requested): raise ValueError("representation must be 'auto', 'indexed', or 'named'.")
-    if artifact_names is not None:
-        if not isinstance(artifact_names, Mapping): raise TypeError("artifact_names must be a mapping.")
-        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in artifact_names.items()): raise ValueError("artifact_names must map non-empty artifact IDs to non-empty names.")
+    if owner_names is not None:
+        if not isinstance(owner_names, Mapping): raise TypeError("owner_names must be a mapping.")
+        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in owner_names.items()): raise ValueError("owner_names must map non-empty owner IDs to non-empty names.")
     base = build_symbol_lineage_payload(
         selected,
         state_freshness=state_freshness,
     )
-    missing = tuple(owner for owner in _semantic_owner_ids(base) if artifact_names is None or owner not in artifact_names)
-    indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}})
+    missing = tuple(owner for owner in _semantic_owner_ids(base) if owner_names is None or owner not in owner_names)
+    indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"id_kinds": ["module", "artifact"], "resolve_via": "lookup_index_entries"}})
     indexed_bytes = mcp_rep.serialized_json_bytes(indexed)
-    named = None if missing else _named_semantic_owners(base, artifact_names or {})
+    named = None if missing else _named_semantic_owners(base, owner_names or {})
     if named is not None:
         assert isinstance(named, dict); named.update({"representation": "named", "requested_representation": requested})
     named_bytes = mcp_rep.serialized_json_bytes(named) if named is not None else None
@@ -272,13 +272,13 @@ def _represented_response_candidate(
     *,
     mode: str,
     representation: str,
-    artifact_names: Mapping[str, str] | None,
+    owner_names: Mapping[str, str] | None,
     state_freshness: Mapping[str, object] | None,
 ) -> dict:
     result = build_symbol_lineage_represented_payload(
         selected,
         representation=representation,
-        artifact_names=artifact_names,
+        owner_names=owner_names,
         state_freshness=state_freshness,
     )
     result["mode"] = mode
@@ -289,7 +289,7 @@ def build_symbol_lineage_represented_preview(
     selected: SelectedSymbolLineageFacts,
     *,
     representation: str = "auto",
-    artifact_names: Mapping[str, str] | None = None,
+    owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
     candidate_mode: str = "fetch",
 ) -> dict:
@@ -302,7 +302,7 @@ def build_symbol_lineage_represented_preview(
         selected,
         mode=candidate_mode,
         representation=representation,
-        artifact_names=artifact_names,
+        owner_names=owner_names,
         state_freshness=state_freshness,
     )
     sections = candidate["sections"]
@@ -362,7 +362,7 @@ def render_symbol_lineage_response(
     mode: str = "auto",
     sections: tuple[str, ...] | None = None,
     representation: str = "auto",
-    artifact_names: Mapping[str, str] | None = None,
+    owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
     allow_large_output: bool = False,
 ) -> str:
@@ -396,7 +396,7 @@ def render_symbol_lineage_response(
         result = build_symbol_lineage_represented_preview(
             selected,
             representation=representation,
-            artifact_names=artifact_names,
+            owner_names=owner_names,
             state_freshness=state_freshness,
             candidate_mode="fetch",
         )
@@ -423,7 +423,7 @@ def render_symbol_lineage_response(
         selected,
         mode=plan.mode,
         representation=representation,
-        artifact_names=artifact_names,
+        owner_names=owner_names,
         state_freshness=state_freshness,
     )
     candidate_bytes = (
@@ -441,7 +441,7 @@ def render_symbol_lineage_response(
             build_symbol_lineage_represented_preview(
                 selected,
                 representation=representation,
-                artifact_names=artifact_names,
+                owner_names=owner_names,
                 state_freshness=state_freshness,
                 candidate_mode="auto",
             )
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index d127644..b64426c 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -9,7 +9,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedSurfaceFact, ResolutionKind,
     SemanticAnchorBinding, SemanticEndpoint, SemanticInterfaceDescriptor,
     SourceSpan, SurfaceDeclarationEvidence, SurfaceKind,
-    build_parameter_value_slot, build_return_slot, ParameterKind,
+    build_parameter_value_slot, build_return_slot, build_module_global_slot, ParameterKind,
 )
 from contextor.core.lineage_query.backend import LineageBackendMetadata
 from contextor.core.lineage_query.service import (
@@ -32,6 +32,13 @@ from contextor.mcp.lineage_response import (
 )
 
 
+def _owner_names_fixture():
+    return {
+        "17/2": "pkg.mod",
+        "A17/2": "pkg.mod::handler",
+    }
+
+
 def _selected_lineage_fixture():
     target = ResolvedLineageTarget("A17/2", "pkg.mod::handler", "pkg.mod", "handler", "exact_id")
     metadata = LineageBackendMetadata(7, "live", "fresh", "1", 1, "fresh", True)
@@ -48,14 +55,31 @@ def _selected_lineage_fixture():
     symbolic_ref = MaterializedSymbolicRef("pkg/mod.py", "1" * 64, ExtractedSymbolicKind.IMPORT, "pkg.dep", "value")
     local_ref = MaterializedOccurrenceRef("pkg/mod.py", "1" * 64, "local")
     binding_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("binding", symbolic_ref, local_ref, LineageRelation.BINDS, span, ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED))
+    module_state_slot = build_module_global_slot(
+        "17/2",
+        "CACHE",
+    )
+    state_flow = LineageFlowMatch(
+        "pkg/mod.py",
+        "1" * 64,
+        MaterializedFlowFact(
+            "state-read",
+            SemanticEndpoint("17/2", module_state_slot),
+            local_ref,
+            LineageRelation.READS_STATE,
+            span,
+            ResolutionKind.LEXICAL_EXACT,
+            LineageConfidence.CONFIRMED,
+        ),
+    )
     dynamic_flow = LineageFlowMatch("pkg/mod.py", "1" * 64, MaterializedFlowFact("dynamic", local_ref, ref, LineageRelation.ASSIGNS, span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, dynamic_boundary="runtime-test"))
     surface_match = LineageSurfaceMatch("pkg/mod.py", "1" * 64, MaterializedSurfaceFact("public-handler", SurfaceKind.PUBLIC_SYMBOL, ref, span, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, "handler", declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION))
     direct = DirectLineageFacts(target, metadata, (definition,), (incoming,), (), (surface_match,))
     root = LineageScopeRootMatch("pkg/mod.py", "1" * 64, binding, anchor)
-    scope = LexicalScopeFacts(target, metadata, (root,), (binding_flow, dynamic_flow), (), True)
-    sections = SemanticLineageSections(target, scope, direct, (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
+    scope = LexicalScopeFacts(target, metadata, (root,), (binding_flow, dynamic_flow, state_flow), (), True)
+    sections = SemanticLineageSections(target, scope, direct, (binding_flow, dynamic_flow), (), (), (), (state_flow,), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
     facts = SymbolLineageFacts(target, interface, sections)
-    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
+    return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (binding_flow, dynamic_flow), (), (), (), (state_flow,), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
 
 
 def _with_repeated_connections(
@@ -216,9 +240,7 @@ def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_i
     named = build_symbol_lineage_represented_payload(
         selected,
         representation="named",
-        artifact_names={
-            "A17/2": "pkg.mod::handler",
-        },
+        owner_names=_owner_names_fixture(),
     )
     indexed = build_symbol_lineage_represented_payload(
         selected,
@@ -243,6 +265,11 @@ def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_i
         "slot": build_return_slot("A17/2"),
     }
 
+    named_state = named["sections"]["state"][0]["source"]
+    indexed_state = indexed["sections"]["state"][0]["source"]
+    assert named_state == {"kind": "semantic", "owner": "pkg.mod", "slot": build_module_global_slot("17/2", "CACHE")}
+    assert indexed_state == {"kind": "semantic", "owner_id": "17/2", "slot": build_module_global_slot("17/2", "CACHE")}
+
     assert (
         named_semantic["slot"]
         == indexed_semantic["slot"]
@@ -294,7 +321,7 @@ def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_i
 
     assert indexed["representation"] == "indexed"
     assert indexed["resolver"] == {
-        "index_kind": "artifact",
+        "id_kinds": ["module", "artifact"],
         "resolve_via": "lookup_index_entries",
     }
     assert (
@@ -309,19 +336,18 @@ def test_symbol_lineage_representation_fails_closed_and_auto_falls_back():
         ValueError,
         match=(
             "Named lineage representation unavailable "
-            "for semantic owners: A17/2"
+            "for semantic owners: 17/2, A17/2"
         ),
     ):
         build_symbol_lineage_represented_payload(
             selected,
             representation="named",
-            artifact_names={},
+            owner_names={},
         )
-
     result = build_symbol_lineage_represented_payload(
         selected,
         representation="auto",
-        artifact_names={},
+        owner_names={},
     )
 
     assert result["representation"] == "indexed"
@@ -331,7 +357,7 @@ def test_symbol_lineage_representation_fails_closed_and_auto_falls_back():
     )
     assert result["representation_decision"][
         "missing_named_owners"
-    ] == ["A17/2"]
+    ] == ["17/2", "A17/2"]
     assert (
         result["representation_decision"][
             "named_candidate_bytes"
@@ -345,9 +371,7 @@ def test_symbol_lineage_auto_named_and_material_indexed_saving():
     named = build_symbol_lineage_represented_payload(
         selected,
         representation="auto",
-        artifact_names={
-            "A17/2": "pkg.mod::handler",
-        },
+        owner_names=_owner_names_fixture(),
     )
 
     named_decision = named["representation_decision"]
@@ -388,9 +412,7 @@ def test_symbol_lineage_auto_named_and_material_indexed_saving():
     indexed = build_symbol_lineage_represented_payload(
         expanded,
         representation="auto",
-        artifact_names={
-            "A17/2": long_name,
-        },
+        owner_names={**_owner_names_fixture(), "A17/2": long_name},
     )
 
     indexed_decision = (
@@ -418,19 +440,19 @@ def test_symbol_lineage_representation_validates_request_contract():
         build_symbol_lineage_represented_payload(selected, representation=object())
     with pytest.raises(ValueError, match="representation must be 'auto', 'indexed', or 'named'."):
         build_symbol_lineage_represented_payload(selected, representation="other")
-    with pytest.raises(TypeError, match="artifact_names must be a mapping."):
-        build_symbol_lineage_represented_payload(selected, representation="named", artifact_names=[])
+    with pytest.raises(TypeError, match="owner_names must be a mapping."):
+        build_symbol_lineage_represented_payload(selected, representation="named", owner_names=[])
     with pytest.raises(
         ValueError,
         match=(
-            "artifact_names must map non-empty "
-            "artifact IDs to non-empty names."
+            "owner_names must map non-empty "
+            "owner IDs to non-empty names."
         ),
     ):
         build_symbol_lineage_represented_payload(
             selected,
             representation="named",
-            artifact_names={
+            owner_names={
                 "A17/2": "",
             },
         )
@@ -494,20 +516,18 @@ def test_symbol_lineage_auto_falls_back_to_exact_representation_aware_preview():
 
 def test_symbol_lineage_explicit_preview_sizes_exact_represented_fetch_candidate():
     selected = _selected_lineage_fixture()
-    names = {
-        "A17/2": "pkg.mod::handler",
-    }
+    names = _owner_names_fixture()
 
     preview = build_symbol_lineage_represented_preview(
         selected,
         representation="named",
-        artifact_names=names,
+        owner_names=names,
         candidate_mode="fetch",
     )
     candidate = build_symbol_lineage_represented_payload(
         selected,
         representation="named",
-        artifact_names=names,
+        owner_names=names,
     )
     candidate["mode"] = "fetch"
```

