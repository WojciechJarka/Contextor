STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh canonical edit context for contextor/core/analysis/lineage_extraction.py: module contextor.core.analysis.lineage_extraction, revision 499, no warnings, fresh syntax diagnostics; current correction continues the authorized Stage 1C.3 working changes at HEAD 279e65de0ec40e5c6383075f9d16301b4b7f7fb7.
IMPLEMENTATION=Added _runtime_target_names and invalidated only runtime-bound target names from for/async-for exit frames and the except alias from handler exit frames. This prevents restoration of a prior exact binding after the runtime scope. with/async-with and all general control-flow merge behavior are unchanged.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q; .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_extraction.py
TEST_RESULTS=31 passed in 1.27s; 42 passed in 3.13s; git diff --check passed (only Git LF-to-CRLF informational warnings).
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 4482268..be9f0a3 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -479,6 +479,18 @@ class _AnchorExtractor:
             return
         self._visit(target, owner, walrus_owner)
 
+    def _runtime_target_names(self, target: ast.AST) -> set[str]:
+        if isinstance(target, ast.Name):
+            return {target.id}
+        if isinstance(target, (ast.Tuple, ast.List)):
+            names: set[str] = set()
+            for item in target.elts:
+                names.update(self._runtime_target_names(item))
+            return names
+        if isinstance(target, ast.Starred):
+            return self._runtime_target_names(target.value)
+        return set()
+
     def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
         source = self._value(node.value, owner, walrus_owner)
         for target in node.targets:
@@ -526,6 +538,7 @@ class _AnchorExtractor:
     def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.iter, owner, walrus_owner)
         entry_frame = self._clone_frame(owner)
+        target_names = self._runtime_target_names(node.target)
         self._runtime_bind_target(
             node.target,
             owner,
@@ -533,14 +546,18 @@ class _AnchorExtractor:
         )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, entry_frame)
+        exit_frame = dict(entry_frame)
+        for name in target_names:
+            exit_frame.pop(name, None)
+        self._replace_frame(owner, exit_frame)
         for child in node.orelse:
             self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, entry_frame)
+        self._replace_frame(owner, exit_frame)
 
     def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.iter, owner, walrus_owner)
         entry_frame = self._clone_frame(owner)
+        target_names = self._runtime_target_names(node.target)
         self._runtime_bind_target(
             node.target,
             owner,
@@ -548,10 +565,13 @@ class _AnchorExtractor:
         )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, entry_frame)
+        exit_frame = dict(entry_frame)
+        for name in target_names:
+            exit_frame.pop(name, None)
+        self._replace_frame(owner, exit_frame)
         for child in node.orelse:
             self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, entry_frame)
+        self._replace_frame(owner, exit_frame)
 
     def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
         for item in node.items:
@@ -616,17 +636,18 @@ class _AnchorExtractor:
         if node.type is not None:
             self._visit(node.type, owner, walrus_owner)
         entry_frame = self._clone_frame(owner)
-        if isinstance(node.name, str):
+        alias_name = node.name if isinstance(node.name, str) else None
+        if alias_name is not None:
             binding = ExtractedOccurrenceRef(
-                self._add("binding", node, node.name, owner)
+                self._add("binding", node, alias_name, owner)
             )
-            if node.name not in self._blocked_names(owner):
+            if alias_name not in self._blocked_names(owner):
                 source = self._occurrence(
                     "runtime_bound_local",
                     node,
-                    node.name,
+                    alias_name,
                 )
-                self._frame(owner)[node.name] = binding
+                self._frame(owner)[alias_name] = binding
                 self._flow(
                     source=source,
                     target=binding,
@@ -637,7 +658,10 @@ class _AnchorExtractor:
                 )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, entry_frame)
+        exit_frame = dict(entry_frame)
+        if alias_name is not None:
+            exit_frame.pop(alias_name, None)
+        self._replace_frame(owner, exit_frame)
 
     def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
         if node.pattern is not None:
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index a3674e4..9c10d2d 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -155,6 +155,74 @@ def test_stage_1c_for_target_is_runtime_bound_only_inside_loop_body():
     )
 
 
+def test_stage_1c_for_target_does_not_restore_prior_exact_binding_after_loop():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " item = 1\n"
+        " for item in items:\n"
+        "  inside = item\n"
+        " after = item\n"
+    )
+    prior = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "item")
+        if anchor.span.start_line == 2
+    )
+    runtime_binding = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "item")
+        if anchor.span.start_line == 3
+    )
+    inside = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == runtime_binding.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
+        and flow.evidence.start_line == 4
+    )
+    assert inside.source.local_id == runtime_binding.local_id
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id in {prior.local_id, runtime_binding.local_id}
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
+        and flow.evidence.start_line == 5
+        for flow in facts.flows
+    )
+
+
+def test_stage_1c_for_else_does_not_claim_prior_or_runtime_target_as_exact():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " item = 1\n"
+        " for item in items:\n"
+        "  pass\n"
+        " else:\n"
+        "  probe = item\n"
+    )
+    item_bindings = {
+        anchor.local_id
+        for anchor in _stage_1c_named(facts, "binding", "item")
+    }
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id in item_bindings
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
+        and flow.evidence.start_line == 6
+        for flow in facts.flows
+    )
+
+
 def test_stage_1c_for_destructuring_gets_independent_runtime_sources():
     facts = _stage_1c_facts(
         "def run(rows):\n"
@@ -262,6 +330,44 @@ def test_stage_1c_except_alias_is_runtime_bound_only_inside_handler():
     )
 
 
+def test_stage_1c_except_alias_does_not_restore_prior_exact_binding_after_handler():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " exc = 1\n"
+        " try:\n"
+        "  pass\n"
+        " except Error as exc:\n"
+        "  inside = exc\n"
+        " after = exc\n"
+    )
+    bindings = _stage_1c_named(facts, "binding", "exc")
+    prior = next(anchor for anchor in bindings if anchor.span.start_line == 2)
+    handler = next(anchor for anchor in bindings if anchor.span.start_line == 5)
+    inside = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == handler.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
+        and flow.evidence.start_line == 6
+    )
+    assert inside.source.local_id == handler.local_id
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id in {prior.local_id, handler.local_id}
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
+        and flow.evidence.start_line == 7
+        for flow in facts.flows
+    )
+
+
 def test_stage_1c_async_for_and_async_with_use_runtime_bound_locals():
     facts = _stage_1c_facts(
         "async def run(items, manager):\n"

