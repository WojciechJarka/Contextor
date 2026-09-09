STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh canonical edit context for contextor/core/analysis/lineage_extraction.py: module contextor.core.analysis.lineage_extraction, revision 496, workspace synchronized, no syntax diagnostics; target files were clean and HEAD matched 279e65de0ec40e5c6383075f9d16301b4b7f7fb7.
IMPLEMENTATION=Added runtime-bound local bindings for for/async for, with/async with, and except aliases. Loop and handler frames restore the entry frame after their scoped bodies; with bindings remain available after normal body exit. No iterable, context-expression, or exception-expression producer flow is created.
DEFERRED=Control-flow cloning/merge/invalidation beyond scoped entry-frame restoration remains Stage 1C.4. Returns/local calls/star binding, imports/rebind safety, and comprehension/walrus edge cases remain deferred as specified.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q; .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_extraction.py
TEST_RESULTS=28 passed in 1.08s; 39 passed in 2.97s; git diff --check passed (only Git LF-to-CRLF informational warnings).
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 4983fe8..4482268 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -435,6 +435,50 @@ class _AnchorExtractor:
         self._frame(owner)[target.id] = binding
         self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
 
+    def _runtime_bind_target(
+        self,
+        target: ast.AST,
+        owner: str | None,
+        walrus_owner: str | None,
+    ) -> None:
+        if isinstance(target, ast.Name):
+            binding = ExtractedOccurrenceRef(
+                self._add("binding", target, target.id, owner)
+            )
+            if target.id in self._blocked_names(owner):
+                return
+            source = self._occurrence(
+                "runtime_bound_local",
+                target,
+                target.id,
+            )
+            self._frame(owner)[target.id] = binding
+            self._flow(
+                source=source,
+                target=binding,
+                relation=LineageRelation.ASSIGNS,
+                node=target,
+                resolution_kind=ResolutionKind.LEXICAL_EXACT,
+                confidence=LineageConfidence.CONFIRMED,
+            )
+            return
+        if isinstance(target, (ast.Tuple, ast.List)):
+            for item in target.elts:
+                self._runtime_bind_target(
+                    item,
+                    owner,
+                    walrus_owner,
+                )
+            return
+        if isinstance(target, ast.Starred):
+            self._runtime_bind_target(
+                target.value,
+                owner,
+                walrus_owner,
+            )
+            return
+        self._visit(target, owner, walrus_owner)
+
     def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
         source = self._value(node.value, owner, walrus_owner)
         for target in node.targets:
@@ -479,6 +523,68 @@ class _AnchorExtractor:
             return
         self._frame(owner)[node.target.id] = binding
 
+    def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.iter, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
+        self._runtime_bind_target(
+            node.target,
+            owner,
+            walrus_owner,
+        )
+        for child in node.body:
+            self._visit(child, owner, walrus_owner)
+        self._replace_frame(owner, entry_frame)
+        for child in node.orelse:
+            self._visit(child, owner, walrus_owner)
+        self._replace_frame(owner, entry_frame)
+
+    def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.iter, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
+        self._runtime_bind_target(
+            node.target,
+            owner,
+            walrus_owner,
+        )
+        for child in node.body:
+            self._visit(child, owner, walrus_owner)
+        self._replace_frame(owner, entry_frame)
+        for child in node.orelse:
+            self._visit(child, owner, walrus_owner)
+        self._replace_frame(owner, entry_frame)
+
+    def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
+        for item in node.items:
+            self._visit(
+                item.context_expr,
+                owner,
+                walrus_owner,
+            )
+            if item.optional_vars is not None:
+                self._runtime_bind_target(
+                    item.optional_vars,
+                    owner,
+                    walrus_owner,
+                )
+        for child in node.body:
+            self._visit(child, owner, walrus_owner)
+
+    def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
+        for item in node.items:
+            self._visit(
+                item.context_expr,
+                owner,
+                walrus_owner,
+            )
+            if item.optional_vars is not None:
+                self._runtime_bind_target(
+                    item.optional_vars,
+                    owner,
+                    walrus_owner,
+                )
+        for child in node.body:
+            self._visit(child, owner, walrus_owner)
+
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
         for alias in node.names:
             local_name = alias.asname or alias.name.split(".", 1)[0]
@@ -509,10 +615,29 @@ class _AnchorExtractor:
     def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
         if node.type is not None:
             self._visit(node.type, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
         if isinstance(node.name, str):
-            self._add("binding", node, node.name, owner)
+            binding = ExtractedOccurrenceRef(
+                self._add("binding", node, node.name, owner)
+            )
+            if node.name not in self._blocked_names(owner):
+                source = self._occurrence(
+                    "runtime_bound_local",
+                    node,
+                    node.name,
+                )
+                self._frame(owner)[node.name] = binding
+                self._flow(
+                    source=source,
+                    target=binding,
+                    relation=LineageRelation.ASSIGNS,
+                    node=node,
+                    resolution_kind=ResolutionKind.LEXICAL_EXACT,
+                    confidence=LineageConfidence.CONFIRMED,
+                )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
+        self._replace_frame(owner, entry_frame)
 
     def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
         if node.pattern is not None:
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index f415dbc..a3674e4 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -105,6 +105,181 @@ def _stage_1c_named(facts, kind, name):
     return [item for item in facts.anchors if item.kind == kind and parse_local_occurrence_id(item.local_id)[3] == name]
 
 
+def _stage_1c_runtime_assignment(facts, name):
+    return next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.ASSIGNS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.source.local_id)[0] == "runtime_bound_local"
+        and parse_local_occurrence_id(flow.source.local_id)[3] == name
+        and parse_local_occurrence_id(flow.target.local_id)[3] == name
+    )
+
+
+def test_stage_1c_for_target_is_runtime_bound_only_inside_loop_body():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " for item in items:\n"
+        "  inside = item\n"
+        " after = item\n"
+    )
+    runtime = _stage_1c_runtime_assignment(facts, "item")
+    item_binding = _stage_1c_named(facts, "binding", "item")[0]
+    assert runtime.target.local_id == item_binding.local_id
+    inside_load = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == item_binding.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
+        and flow.evidence.start_line == 3
+    )
+    assert inside_load.source.local_id == item_binding.local_id
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
+        and flow.evidence.start_line == 4
+        for flow in facts.flows
+    )
+
+
+def test_stage_1c_for_destructuring_gets_independent_runtime_sources():
+    facts = _stage_1c_facts(
+        "def run(rows):\n"
+        " for left, *rest in rows:\n"
+        "  a = left\n"
+        "  b = rest\n"
+    )
+    left_runtime = _stage_1c_runtime_assignment(facts, "left")
+    rest_runtime = _stage_1c_runtime_assignment(facts, "rest")
+    assert left_runtime.source.local_id != rest_runtime.source.local_id
+    assert parse_local_occurrence_id(left_runtime.source.local_id)[0] == "runtime_bound_local"
+    assert parse_local_occurrence_id(rest_runtime.source.local_id)[0] == "runtime_bound_local"
+    assert not any(
+        flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[3] in {"left", "rest"}
+        and parse_local_occurrence_id(flow.source.local_id)[0] != "runtime_bound_local"
+        for flow in facts.flows
+    )
+
+
+def test_stage_1c_with_binding_is_runtime_bound_and_remains_available_after_body():
+    facts = _stage_1c_facts(
+        "def run(manager):\n"
+        " with manager as resource:\n"
+        "  inside = resource\n"
+        " after = resource\n"
+    )
+    runtime = _stage_1c_runtime_assignment(facts, "resource")
+    resource_binding = _stage_1c_named(facts, "binding", "resource")[0]
+    assert runtime.target.local_id == resource_binding.local_id
+    loads = [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == resource_binding.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "resource"
+    ]
+    assert {flow.evidence.start_line for flow in loads} == {3, 4}
+
+
+def test_stage_1c_with_items_bind_sequentially_without_context_producer_flow():
+    facts = _stage_1c_facts(
+        "def run(first):\n"
+        " with first as x, x as y:\n"
+        "  result = y\n"
+    )
+    x_runtime = _stage_1c_runtime_assignment(facts, "x")
+    y_runtime = _stage_1c_runtime_assignment(facts, "y")
+    x_binding = _stage_1c_named(facts, "binding", "x")[0]
+    second_context_load = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == x_binding.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "x"
+        and flow.evidence.start_line == 2
+    )
+    assert second_context_load.source.local_id == x_binding.local_id
+    assert parse_local_occurrence_id(x_runtime.source.local_id)[0] == "runtime_bound_local"
+    assert parse_local_occurrence_id(y_runtime.source.local_id)[0] == "runtime_bound_local"
+
+
+def test_stage_1c_except_alias_is_runtime_bound_only_inside_handler():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " try:\n"
+        "  pass\n"
+        " except Error as exc:\n"
+        "  inside = exc\n"
+        " after = exc\n"
+    )
+    runtime = _stage_1c_runtime_assignment(facts, "exc")
+    exc_binding = _stage_1c_named(facts, "binding", "exc")[0]
+    assert runtime.target.local_id == exc_binding.local_id
+    inside_load = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == exc_binding.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
+        and flow.evidence.start_line == 5
+    )
+    assert inside_load.source.local_id == exc_binding.local_id
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
+        and flow.evidence.start_line == 6
+        for flow in facts.flows
+    )
+
+
+def test_stage_1c_async_for_and_async_with_use_runtime_bound_locals():
+    facts = _stage_1c_facts(
+        "async def run(items, manager):\n"
+        " async for item in items:\n"
+        "  seen = item\n"
+        " async with manager as resource:\n"
+        "  used = resource\n"
+    )
+    item_runtime = _stage_1c_runtime_assignment(facts, "item")
+    resource_runtime = _stage_1c_runtime_assignment(facts, "resource")
+    assert parse_local_occurrence_id(item_runtime.source.local_id)[0] == "runtime_bound_local"
+    assert parse_local_occurrence_id(resource_runtime.source.local_id)[0] == "runtime_bound_local"
+    assert item_runtime.resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert resource_runtime.resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert item_runtime.confidence is LineageConfidence.CONFIRMED
+    assert resource_runtime.confidence is LineageConfidence.CONFIRMED
+
+
 def test_stage_1c_direct_assignments_chain_through_current_frame():
     facts = _stage_1c_facts(
         "def run(arg):\n"

