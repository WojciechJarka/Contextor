# F2L D1N2a Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `tests/analysis/test_lineage_query_service.py`

## SELECTED_COMPLETENESS_PROOF

Selection completeness now certifies only selected logical units.

## INTERFACE_ISOLATION_PROOF

A complete selected interface remains complete despite unselected scope metadata mismatch.

## CONNECTIONS_ISOLATION_PROOF

A complete selected connections section remains complete despite unselected ambiguous interface.

## NON_LEXICAL_EMPTY_PROOF

Lexical empty sections are complete when the scope is authoritatively not applicable.

## SELECTED_METADATA_PROOF

Metadata comparison includes only projections required by selected sections.

## EMPTY_SELECTION_PROOF

An empty request is vacuously metadata-consistent and complete.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 84 passed in 3.06s
git diff --check -- contextor/core/lineage_query/service.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_query_service.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index 4c925d7..960b6cd 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -60,6 +60,11 @@ SYMBOL_LINEAGE_SECTION_ORDER = (
     "unresolved_dynamic_boundaries",
 )
 
+_LEXICAL_SYMBOL_LINEAGE_SECTIONS = frozenset({
+    "bindings", "parameter_flows", "calls_interfaces", "returns",
+    "state", "callbacks", "unresolved_dynamic_boundaries",
+})
+
 
 @dataclass(frozen=True)
 class ResolvedLineageTarget:
@@ -425,13 +430,44 @@ class SelectedSymbolLineageFacts:
         return self.facts.target
 
     @property
-    def metadata_consistent(self) -> bool:
+    def aggregate_metadata_consistent(self) -> bool:
         return self.facts.metadata_consistent
 
     @property
-    def complete(self) -> bool:
+    def aggregate_complete(self) -> bool:
         return self.facts.complete
 
+    @property
+    def metadata_consistent(self) -> bool:
+        selected = set(self.selected_sections)
+        metadata: list[LineageBackendMetadata] = []
+        if "interface" in selected:
+            metadata.append(self.facts.interface.metadata)
+        if "connections" in selected or "surfaces" in selected:
+            metadata.append(self.facts.direct.metadata)
+        needs_scope = bool(selected & _LEXICAL_SYMBOL_LINEAGE_SECTIONS) or "surfaces" in selected
+        if needs_scope:
+            metadata.append(self.facts.scope.metadata)
+            if self.facts.scope_state == "not_applicable":
+                metadata.append(self.facts.interface.metadata)
+        return not metadata or all(item == metadata[0] for item in metadata[1:])
+
+    @property
+    def complete(self) -> bool:
+        if not self.metadata_consistent:
+            return False
+        selected = set(self.selected_sections)
+        if "interface" in selected and not self.facts.interface.complete:
+            return False
+        if "connections" in selected and not self.facts.direct.complete:
+            return False
+        needs_scope = bool(selected & _LEXICAL_SYMBOL_LINEAGE_SECTIONS)
+        if needs_scope and self.facts.scope_state not in {"available", "not_applicable"}:
+            return False
+        if "surfaces" in selected and (not self.facts.direct.complete or self.facts.scope_state not in {"available", "not_applicable"}):
+            return False
+        return True
+
 
 class LineageQueryService:
     def __init__(
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 9f8e851..31c46c1 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -2451,3 +2451,29 @@ def test_symbol_lineage_selection_allows_empty_and_rejects_invalid_contract():
         service.select_symbol_lineage_sections(facts, ("state", "state"))
     with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
         service.select_symbol_lineage_sections(facts, ("mystery",))
+
+
+def test_symbol_lineage_selection_interface_complete_is_independent_of_unselected_scope_metadata():
+    service, backend, target, _ = _target_interface_service()
+    _install_target_parameter_defaults(backend, target)
+    facts = service.symbol_lineage_facts(target)
+    mismatched = replace(facts, sections=replace(facts.sections, scope=replace(facts.scope, metadata=replace(facts.scope.metadata, revision=999))))
+    selected = service.select_symbol_lineage_sections(mismatched, ("interface",))
+    assert selected.aggregate_metadata_consistent is False
+    assert selected.aggregate_complete is False
+    assert selected.metadata_consistent is True
+    assert selected.complete is True
+
+
+def test_symbol_lineage_selection_connections_ignore_unselected_interface_incompleteness():
+    service, _backend, target, _ = _target_interface_service(duplicate_definition=True)
+    selected = service.select_symbol_lineage_sections(service.symbol_lineage_facts(target), ("connections",))
+    assert selected.complete is True
+    assert selected.metadata_consistent is True
+
+
+def test_symbol_lineage_selection_empty_request_is_vacuously_complete():
+    service, _backend, target, _ = _target_interface_service()
+    selected = service.select_symbol_lineage_sections(service.symbol_lineage_facts(target), ())
+    assert selected.metadata_consistent is True
+    assert selected.complete is True
```
