# F2L D1N1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `tests/analysis/test_lineage_query_service.py`

## COMPOSITION_PROOF

`symbol_lineage_facts()` calls exactly `target_interface_facts(target)` and `semantic_sections(target)` once.

## NON_LEXICAL_NOT_APPLICABLE_PROOF

A complete non-callable exact target with zero lexical roots is authoritative `not_applicable` and remains top-level complete.

## CLASS_SEMANTICS_NOTE

Callable state and lexical scope are independent: non-callable symbols may still have an available lexical scope.

## AMBIGUITY_FAIL_CLOSED_PROOF

Ambiguous exact definitions produce unknown scope state and incomplete aggregate output.

## METADATA_CONSISTENCY_PROOF

Mixed interface/direct/scope metadata makes `metadata_consistent=False` and fails top-level completeness without selecting a revision.

## NO_TRAVERSAL_PROOF

The composition test replaces traversal with an assertion failure; the aggregate completes without invoking it.

## TESTS_RUN

```text
python -m py_compile contextor/core/lineage_query/service.py: PASS
python -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 78 passed in 2.14s
git diff --check -- contextor/core/lineage_query/service.py tests/analysis/test_lineage_query_service.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_query_service.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index eb8eddb..9ade6ec 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -350,6 +350,49 @@ class DirectLineageFacts:
         )
 
 
+@dataclass(frozen=True)
+class SymbolLineageFacts:
+    target: ResolvedLineageTarget
+    interface: TargetInterfaceFacts
+    sections: SemanticLineageSections
+
+    @property
+    def direct(self) -> DirectLineageFacts:
+        return self.sections.direct
+
+    @property
+    def scope(self) -> LexicalScopeFacts:
+        return self.sections.scope
+
+    @property
+    def metadata(self) -> LineageBackendMetadata:
+        return self.direct.metadata
+
+    @property
+    def metadata_consistent(self) -> bool:
+        return (
+            self.interface.metadata == self.direct.metadata
+            and self.direct.metadata == self.scope.metadata
+        )
+
+    @property
+    def scope_state(self) -> str:
+        if self.scope.complete:
+            return "available"
+        if self.interface.complete and not self.scope.roots:
+            return "not_applicable"
+        return "unknown"
+
+    @property
+    def complete(self) -> bool:
+        return (
+            self.metadata_consistent
+            and self.interface.complete
+            and self.direct.complete
+            and self.scope_state in {"available", "not_applicable"}
+        )
+
+
 class LineageQueryService:
     def __init__(
         self,
@@ -792,6 +835,20 @@ class LineageQueryService:
         )
 
 
+    def symbol_lineage_facts(
+        self,
+        target: ResolvedLineageTarget,
+    ) -> SymbolLineageFacts:
+        if not isinstance(target, ResolvedLineageTarget):
+            raise TypeError("target must be ResolvedLineageTarget.")
+        interface = self.target_interface_facts(target)
+        sections = self.semantic_sections(target)
+        return SymbolLineageFacts(
+            target=target,
+            interface=interface,
+            sections=sections,
+        )
+
     def traverse_lexical_scope(
         self,
         target: ResolvedLineageTarget,
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 9a1b1a4..22575c8 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -2341,3 +2341,72 @@ def test_target_interface_ambiguous_definition_normalizes_as_unknown():
     assert result.signature_digest is None
     assert result.return_slot is None
     assert result.parameter_slots == ()
+
+
+def test_symbol_lineage_facts_composes_complete_callable_without_extra_query_paths(monkeypatch):
+    service, backend, target, _ = _target_interface_service()
+    _install_target_parameter_defaults(backend, target)
+    calls = {"interface": 0, "sections": 0}
+    interface, sections = service.target_interface_facts, service.semantic_sections
+    def interface_spy(value):
+        calls["interface"] += 1
+        return interface(value)
+    def sections_spy(value):
+        calls["sections"] += 1
+        return sections(value)
+    monkeypatch.setattr(service, "target_interface_facts", interface_spy)
+    monkeypatch.setattr(service, "semantic_sections", sections_spy)
+    monkeypatch.setattr(service, "traverse_lexical_scope", lambda *a, **k: (_ for _ in ()).throw(AssertionError("symbol aggregate used traversal")))
+    result = service.symbol_lineage_facts(target)
+    assert result.target is target
+    assert calls == {"interface": 1, "sections": 1}
+    assert result.interface.callable_state == "callable"
+    assert result.scope_state == "available"
+    assert result.metadata_consistent is True
+    assert result.complete is True
+
+
+def test_symbol_lineage_facts_treats_authoritative_non_lexical_symbol_as_not_applicable():
+    service, backend, target, _ = _target_interface_service()
+    provider = backend.get_source("pkg/target.py")
+    assert provider is not None
+    backend._sources["pkg/target.py"] = replace(
+        provider,
+        anchors=(replace(provider.anchors[0], kind="binding"),),
+        interface_descriptors=(),
+    )
+    result = service.symbol_lineage_facts(target)
+    assert result.interface.complete is True
+    assert result.interface.callable_state == "non_callable"
+    assert result.scope.roots == ()
+    assert result.scope_state == "not_applicable"
+    assert result.direct.complete is True
+    assert result.complete is True
+
+
+def test_symbol_lineage_facts_ambiguous_definition_fails_closed():
+    service, _backend, target, _ = _target_interface_service(duplicate_definition=True)
+    result = service.symbol_lineage_facts(target)
+    assert result.interface.definition_ambiguous is True
+    assert result.scope_state == "unknown"
+    assert result.complete is False
+
+
+def test_symbol_lineage_facts_metadata_mismatch_fails_closed(monkeypatch):
+    service, backend, target, _ = _target_interface_service()
+    _install_target_parameter_defaults(backend, target)
+    interface, sections = service.target_interface_facts(target), service.semantic_sections(target)
+    mismatched = replace(interface, metadata=replace(interface.metadata, revision=999))
+    monkeypatch.setattr(service, "target_interface_facts", lambda _: mismatched)
+    monkeypatch.setattr(service, "semantic_sections", lambda _: sections)
+    result = service.symbol_lineage_facts(target)
+    assert result.metadata_consistent is False
+    assert result.interface.complete is True
+    assert result.direct.complete is True
+    assert result.scope_state == "available"
+    assert result.complete is False
+
+
+def test_symbol_lineage_facts_rejects_non_target():
+    with pytest.raises(TypeError, match="target must be ResolvedLineageTarget."):
+        _service({}).symbol_lineage_facts(object())
```
