# F2L D1N2 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `tests/analysis/test_lineage_query_service.py`

## SECTION_ORDER_PROOF

Selection canonicalizes every request to `SYMBOL_LINEAGE_SECTION_ORDER`.

## CONNECTIONS_PROOF

The selected connections view retains direct incoming and outgoing typed flow matches.

## PARAMETER_FLOWS_SEPARATION_PROOF

`parameter_flows` maps only the D1K lexical bucket and remains separate from own interface defaults.

## UNRESOLVED_DYNAMIC_ORTHOGONAL_PROOF

Dynamic boundaries remain a separately selected orthogonal section.

## EMPTY_VS_OMITTED_PROOF

An empty selected section is an empty tuple; `None` means the section was omitted.

## NO_REQUERY_PROOF

Selection operates on supplied facts while spies reject calls back into the aggregate and backend.

## VALIDATION_PROOF

The view rejects invalid facts, non-tuple selection, empty section names, duplicates, and unknown sections.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 81 passed in 3.95s
git diff --check -- contextor/core/lineage_query/service.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_query_service.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 9ade6ec..4c925d7 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -54,6 +54,12 @@ _PRIMARY_SEMANTIC_SECTION_BY_RELATION = {
     LineageRelation.DECLARES_PUBLIC_NAMES: "surfaces",
 }
 
+SYMBOL_LINEAGE_SECTION_ORDER = (
+    "interface", "connections", "bindings", "parameter_flows",
+    "calls_interfaces", "returns", "state", "callbacks", "surfaces",
+    "unresolved_dynamic_boundaries",
+)
+
 
 @dataclass(frozen=True)
 class ResolvedLineageTarget:
@@ -393,6 +399,40 @@ class SymbolLineageFacts:
         )
 
 
+@dataclass(frozen=True)
+class SymbolLineageConnections:
+    incoming: tuple[LineageFlowMatch, ...]
+    outgoing: tuple[LineageFlowMatch, ...]
+
+
+@dataclass(frozen=True)
+class SelectedSymbolLineageFacts:
+    facts: SymbolLineageFacts
+    selected_sections: tuple[str, ...]
+    interface: TargetInterfaceFacts | None
+    connections: SymbolLineageConnections | None
+    bindings: tuple[LineageFlowMatch, ...] | None
+    parameter_flows: tuple[LineageFlowMatch, ...] | None
+    calls_interfaces: tuple[LineageFlowMatch, ...] | None
+    returns: tuple[LineageFlowMatch, ...] | None
+    state: tuple[LineageFlowMatch, ...] | None
+    callbacks: tuple[LineageFlowMatch, ...] | None
+    surfaces: LineageSurfaceSection | None
+    unresolved_dynamic_boundaries: tuple[LineageFlowMatch, ...] | None
+
+    @property
+    def target(self) -> ResolvedLineageTarget:
+        return self.facts.target
+
+    @property
+    def metadata_consistent(self) -> bool:
+        return self.facts.metadata_consistent
+
+    @property
+    def complete(self) -> bool:
+        return self.facts.complete
+
+
 class LineageQueryService:
     def __init__(
         self,
@@ -849,6 +889,35 @@ class LineageQueryService:
             sections=sections,
         )
 
+    def select_symbol_lineage_sections(self, facts: SymbolLineageFacts, sections: tuple[str, ...]) -> SelectedSymbolLineageFacts:
+        if not isinstance(facts, SymbolLineageFacts):
+            raise TypeError("facts must be SymbolLineageFacts.")
+        if not isinstance(sections, tuple):
+            raise TypeError("sections must be a tuple of section names.")
+        if any(not isinstance(section, str) or not section for section in sections):
+            raise ValueError("sections must contain non-empty strings.")
+        if len(set(sections)) != len(sections):
+            raise ValueError("sections must not contain duplicates.")
+        requested = set(sections)
+        unknown = tuple(sorted(requested - set(SYMBOL_LINEAGE_SECTION_ORDER)))
+        if unknown:
+            raise ValueError("Unknown symbol lineage sections: " + ", ".join(unknown))
+        selected = tuple(s for s in SYMBOL_LINEAGE_SECTION_ORDER if s in requested)
+        semantic = facts.sections
+        return SelectedSymbolLineageFacts(
+            facts, selected,
+            facts.interface if "interface" in requested else None,
+            SymbolLineageConnections(facts.direct.incoming, facts.direct.outgoing) if "connections" in requested else None,
+            semantic.bindings if "bindings" in requested else None,
+            semantic.parameters if "parameter_flows" in requested else None,
+            semantic.calls_interfaces if "calls_interfaces" in requested else None,
+            semantic.returns if "returns" in requested else None,
+            semantic.state if "state" in requested else None,
+            semantic.callbacks if "callbacks" in requested else None,
+            semantic.surfaces if "surfaces" in requested else None,
+            semantic.unresolved_dynamic if "unresolved_dynamic_boundaries" in requested else None,
+        )
+
     def traverse_lexical_scope(
         self,
         target: ResolvedLineageTarget,
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 22575c8..9f8e851 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -2410,3 +2410,44 @@ def test_symbol_lineage_facts_metadata_mismatch_fails_closed(monkeypatch):
 def test_symbol_lineage_facts_rejects_non_target():
     with pytest.raises(TypeError, match="target must be ResolvedLineageTarget."):
         _service({}).symbol_lineage_facts(object())
+
+
+def test_symbol_lineage_selection_maps_sections_without_requery(monkeypatch):
+    from contextor.core.lineage_query import service as service_module
+    service, backend, target, _ = _target_interface_service()
+    _install_target_parameter_defaults(backend, target)
+    facts = service.symbol_lineage_facts(target)
+    monkeypatch.setattr(service, "symbol_lineage_facts", lambda *_: (_ for _ in ()).throw(AssertionError("selection requeried symbol facts")))
+    monkeypatch.setattr(backend, "source_keys_for_owner", lambda *_: (_ for _ in ()).throw(AssertionError("selection read backend")))
+    selected = service.select_symbol_lineage_sections(facts, tuple(reversed(service_module.SYMBOL_LINEAGE_SECTION_ORDER)))
+    assert selected.selected_sections == service_module.SYMBOL_LINEAGE_SECTION_ORDER
+    assert selected.interface is facts.interface
+    assert selected.connections is not None
+    assert selected.connections.incoming == facts.direct.incoming
+    assert selected.parameter_flows is facts.sections.parameters
+    assert selected.unresolved_dynamic_boundaries is facts.sections.unresolved_dynamic
+
+
+def test_symbol_lineage_selection_distinguishes_selected_empty_from_omitted():
+    service, _backend, target, _ = _target_interface_service()
+    facts = service.symbol_lineage_facts(target)
+    selected = service.select_symbol_lineage_sections(facts, ("callbacks",))
+    assert selected.callbacks == ()
+    assert selected.interface is None
+    assert selected.connections is None
+
+
+def test_symbol_lineage_selection_allows_empty_and_rejects_invalid_contract():
+    service, _backend, target, _ = _target_interface_service()
+    facts = service.symbol_lineage_facts(target)
+    assert service.select_symbol_lineage_sections(facts, ()).selected_sections == ()
+    with pytest.raises(TypeError, match="facts must be SymbolLineageFacts."):
+        service.select_symbol_lineage_sections(object(), ())
+    with pytest.raises(TypeError, match="sections must be a tuple of section names."):
+        service.select_symbol_lineage_sections(facts, ["interface"])
+    with pytest.raises(ValueError, match="sections must contain non-empty strings."):
+        service.select_symbol_lineage_sections(facts, ("",))
+    with pytest.raises(ValueError, match="sections must not contain duplicates."):
+        service.select_symbol_lineage_sections(facts, ("state", "state"))
+    with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
+        service.select_symbol_lineage_sections(facts, ("mystery",))
```
