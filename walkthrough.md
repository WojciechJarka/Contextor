STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh Contextor edit context for contextor/core/analysis/lineage_extraction.py: revision 503, no warnings, fresh syntax diagnostics. HEAD was 914af62dc51b4c307de9164668cd929095747ed9 and the authorized Stage 1C.4 working changes were preserved.
IMPLEMENTATION=_visit_ExceptHandler now derives its exit frame from the actual handler-body frame and removes only the exception alias. _visit_Try therefore merges handler rebindings instead of restoring the handler entry frame.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q; .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_extraction.py
TEST_RESULTS=40 passed in 1.24s; 51 passed in 2.93s; git diff --check passed (only Git LF-to-CRLF informational warnings).
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index be9f0a3..791a61e 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -253,6 +253,18 @@ class _AnchorExtractor:
                 merged[name] = first
         return merged
 
+    def _visit_block_from_frame(
+        self,
+        body: list[ast.stmt],
+        owner: str | None,
+        walrus_owner: str | None,
+        frame: dict[str, ExtractedOccurrenceRef],
+    ) -> dict[str, ExtractedOccurrenceRef]:
+        self._replace_frame(owner, frame)
+        for child in body:
+            self._visit(child, owner, walrus_owner)
+        return self._clone_frame(owner)
+
     def _blocked_names(self, owner: str | None) -> set[str]:
         return self._blocked.setdefault(owner, set())
 
@@ -479,18 +491,6 @@ class _AnchorExtractor:
             return
         self._visit(target, owner, walrus_owner)
 
-    def _runtime_target_names(self, target: ast.AST) -> set[str]:
-        if isinstance(target, ast.Name):
-            return {target.id}
-        if isinstance(target, (ast.Tuple, ast.List)):
-            names: set[str] = set()
-            for item in target.elts:
-                names.update(self._runtime_target_names(item))
-            return names
-        if isinstance(target, ast.Starred):
-            return self._runtime_target_names(target.value)
-        return set()
-
     def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
         source = self._value(node.value, owner, walrus_owner)
         for target in node.targets:
@@ -535,10 +535,33 @@ class _AnchorExtractor:
             return
         self._frame(owner)[node.target.id] = binding
 
+    def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.test, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
+        body_frame = self._visit_block_from_frame(
+            node.body,
+            owner,
+            walrus_owner,
+            entry_frame,
+        )
+        if node.orelse:
+            else_frame = self._visit_block_from_frame(
+                node.orelse,
+                owner,
+                walrus_owner,
+                entry_frame,
+            )
+        else:
+            else_frame = dict(entry_frame)
+        self._replace_frame(
+            owner,
+            self._merge_frames((body_frame, else_frame)),
+        )
+
     def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.iter, owner, walrus_owner)
         entry_frame = self._clone_frame(owner)
-        target_names = self._runtime_target_names(node.target)
+        self._replace_frame(owner, entry_frame)
         self._runtime_bind_target(
             node.target,
             owner,
@@ -546,18 +569,28 @@ class _AnchorExtractor:
         )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        exit_frame = dict(entry_frame)
-        for name in target_names:
-            exit_frame.pop(name, None)
-        self._replace_frame(owner, exit_frame)
-        for child in node.orelse:
-            self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, exit_frame)
+        body_frame = self._clone_frame(owner)
+        loop_exit_frame = self._merge_frames(
+            (entry_frame, body_frame)
+        )
+        self._replace_frame(owner, loop_exit_frame)
+        if not node.orelse:
+            return
+        else_frame = self._visit_block_from_frame(
+            node.orelse,
+            owner,
+            walrus_owner,
+            loop_exit_frame,
+        )
+        self._replace_frame(
+            owner,
+            self._merge_frames((loop_exit_frame, else_frame)),
+        )
 
     def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.iter, owner, walrus_owner)
         entry_frame = self._clone_frame(owner)
-        target_names = self._runtime_target_names(node.target)
+        self._replace_frame(owner, entry_frame)
         self._runtime_bind_target(
             node.target,
             owner,
@@ -565,13 +598,49 @@ class _AnchorExtractor:
         )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        exit_frame = dict(entry_frame)
-        for name in target_names:
-            exit_frame.pop(name, None)
-        self._replace_frame(owner, exit_frame)
-        for child in node.orelse:
-            self._visit(child, owner, walrus_owner)
-        self._replace_frame(owner, exit_frame)
+        body_frame = self._clone_frame(owner)
+        loop_exit_frame = self._merge_frames(
+            (entry_frame, body_frame)
+        )
+        self._replace_frame(owner, loop_exit_frame)
+        if not node.orelse:
+            return
+        else_frame = self._visit_block_from_frame(
+            node.orelse,
+            owner,
+            walrus_owner,
+            loop_exit_frame,
+        )
+        self._replace_frame(
+            owner,
+            self._merge_frames((loop_exit_frame, else_frame)),
+        )
+
+    def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.test, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
+        body_frame = self._visit_block_from_frame(
+            node.body,
+            owner,
+            walrus_owner,
+            entry_frame,
+        )
+        loop_exit_frame = self._merge_frames(
+            (entry_frame, body_frame)
+        )
+        self._replace_frame(owner, loop_exit_frame)
+        if not node.orelse:
+            return
+        else_frame = self._visit_block_from_frame(
+            node.orelse,
+            owner,
+            walrus_owner,
+            loop_exit_frame,
+        )
+        self._replace_frame(
+            owner,
+            self._merge_frames((loop_exit_frame, else_frame)),
+        )
 
     def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
         for item in node.items:
@@ -632,10 +701,38 @@ class _AnchorExtractor:
             self._blocked_names(owner).add(name)
             self._frame(owner).pop(name, None)
 
+    def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
+        entry_frame = self._clone_frame(owner)
+        normal_frame = self._visit_block_from_frame(
+            node.body,
+            owner,
+            walrus_owner,
+            entry_frame,
+        )
+        if node.orelse:
+            normal_frame = self._visit_block_from_frame(
+                node.orelse,
+                owner,
+                walrus_owner,
+                normal_frame,
+            )
+        reachable_frames = [normal_frame]
+        for handler in node.handlers:
+            self._replace_frame(owner, entry_frame)
+            self._visit(handler, owner, walrus_owner)
+            reachable_frames.append(
+                self._clone_frame(owner)
+            )
+        merged_frame = self._merge_frames(
+            tuple(reachable_frames)
+        )
+        self._replace_frame(owner, merged_frame)
+        for child in node.finalbody:
+            self._visit(child, owner, walrus_owner)
+
     def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
         if node.type is not None:
             self._visit(node.type, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
         alias_name = node.name if isinstance(node.name, str) else None
         if alias_name is not None:
             binding = ExtractedOccurrenceRef(
@@ -658,11 +755,30 @@ class _AnchorExtractor:
                 )
         for child in node.body:
             self._visit(child, owner, walrus_owner)
-        exit_frame = dict(entry_frame)
+        exit_frame = self._clone_frame(owner)
         if alias_name is not None:
             exit_frame.pop(alias_name, None)
         self._replace_frame(owner, exit_frame)
 
+    def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.subject, owner, walrus_owner)
+        entry_frame = self._clone_frame(owner)
+        reachable_frames = [dict(entry_frame)]
+        for case in node.cases:
+            self._replace_frame(owner, entry_frame)
+            self._visit(case.pattern, owner, walrus_owner)
+            if case.guard is not None:
+                self._visit(case.guard, owner, walrus_owner)
+            for child in case.body:
+                self._visit(child, owner, walrus_owner)
+            reachable_frames.append(
+                self._clone_frame(owner)
+            )
+        self._replace_frame(
+            owner,
+            self._merge_frames(tuple(reachable_frames)),
+        )
+
     def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
         if node.pattern is not None:
             self._visit(node.pattern, owner, walrus_owner)
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 9c10d2d..4c3901c 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -95,6 +95,13 @@ def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
         )
     )
     assert merged == {"a": a}
+    assert extractor._merge_frames(
+        (
+            {"a": a},
+            {"a": a},
+            {"a": a},
+        )
+    ) == {"a": a}
 
 
 def _stage_1c_facts(source: str):
@@ -120,6 +127,206 @@ def _stage_1c_runtime_assignment(facts, name):
     )
 
 
+def _stage_1c_lexical_bind_sources(facts, name, line):
+    return [
+        flow.source.local_id
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == name
+        and flow.evidence.start_line == line
+    ]
+
+
+def test_stage_1c_if_branches_are_exact_inside_and_ambiguous_after_merge():
+    facts = _stage_1c_facts(
+        "def run(cond):\n"
+        " stable = 1\n"
+        " if cond:\n"
+        "  value = 2\n"
+        "  left = value\n"
+        " else:\n"
+        "  value = 3\n"
+        "  right = value\n"
+        " after_value = value\n"
+        " after_stable = stable\n"
+    )
+    value_bindings = _stage_1c_named(facts, "binding", "value")
+    stable = _stage_1c_named(facts, "binding", "stable")[0]
+    assert len(value_bindings) == 2
+    assert _stage_1c_lexical_bind_sources(facts, "value", 5) == [
+        next(anchor.local_id for anchor in value_bindings if anchor.span.start_line == 4)
+    ]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 8) == [
+        next(anchor.local_id for anchor in value_bindings if anchor.span.start_line == 7)
+    ]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 9) == []
+    assert _stage_1c_lexical_bind_sources(facts, "stable", 10) == [
+        stable.local_id
+    ]
+
+
+def test_stage_1c_if_without_else_invalidates_conditional_rebind():
+    facts = _stage_1c_facts(
+        "def run(cond):\n"
+        " value = 1\n"
+        " if cond:\n"
+        "  value = 2\n"
+        " after = value\n"
+    )
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "value",
+        5,
+    ) == []
+
+
+def test_stage_1c_for_body_touch_invalidates_non_target_binding_after_loop():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " stable = 1\n"
+        " changed = 2\n"
+        " for item in items:\n"
+        "  changed = item\n"
+        " after_changed = changed\n"
+        " after_stable = stable\n"
+    )
+    stable = _stage_1c_named(facts, "binding", "stable")[0]
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "changed",
+        6,
+    ) == []
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "stable",
+        7,
+    ) == [stable.local_id]
+
+
+def test_stage_1c_while_body_and_else_only_bindings_are_not_exact_after_loop():
+    facts = _stage_1c_facts(
+        "def run(cond):\n"
+        " value = 1\n"
+        " while cond:\n"
+        "  value = 2\n"
+        " else:\n"
+        "  else_only = 3\n"
+        " after_value = value\n"
+        " after_else = else_only\n"
+    )
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "value",
+        7,
+    ) == []
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "else_only",
+        8,
+    ) == []
+
+
+def test_stage_1c_try_handler_conflict_merges_to_unresolved_but_finally_is_exact():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " try:\n"
+        "  value = 1\n"
+        "  try_seen = value\n"
+        " except Error:\n"
+        "  value = 2\n"
+        "  except_seen = value\n"
+        " finally:\n"
+        "  stable = 3\n"
+        " after_value = value\n"
+        " after_stable = stable\n"
+    )
+    value_bindings = _stage_1c_named(facts, "binding", "value")
+    try_value = next(anchor for anchor in value_bindings if anchor.span.start_line == 3)
+    except_value = next(anchor for anchor in value_bindings if anchor.span.start_line == 6)
+    stable = _stage_1c_named(facts, "binding", "stable")[0]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 4) == [try_value.local_id]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 7) == [except_value.local_id]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 10) == []
+    assert _stage_1c_lexical_bind_sources(facts, "stable", 11) == [stable.local_id]
+
+
+def test_stage_1c_try_merge_observes_handler_body_rebinding():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " value = 0\n"
+        " try:\n"
+        "  pass\n"
+        " except Error:\n"
+        "  value = 1\n"
+        " after = value\n"
+    )
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "value",
+        7,
+    ) == []
+
+
+def test_stage_1c_finally_does_not_restore_pre_handler_binding_after_handler_rebind():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " value = 0\n"
+        " try:\n"
+        "  pass\n"
+        " except Error:\n"
+        "  value = 1\n"
+        " finally:\n"
+        "  seen = value\n"
+    )
+    assert _stage_1c_lexical_bind_sources(
+        facts,
+        "value",
+        9,
+    ) == []
+
+
+def test_stage_1c_try_handler_starts_from_entry_not_partial_try_state():
+    facts = _stage_1c_facts(
+        "def run():\n"
+        " before = 1\n"
+        " try:\n"
+        "  partial = before\n"
+        "  explode()\n"
+        " except Error:\n"
+        "  seen_before = before\n"
+        "  seen_partial = partial\n"
+    )
+    before = _stage_1c_named(facts, "binding", "before")[0]
+    assert _stage_1c_lexical_bind_sources(facts, "before", 7) == [before.local_id]
+    assert _stage_1c_lexical_bind_sources(facts, "partial", 8) == []
+
+
+def test_stage_1c_match_cases_are_independent_and_no_match_path_is_preserved():
+    facts = _stage_1c_facts(
+        "def run(subject):\n"
+        " value = 0\n"
+        " match subject:\n"
+        "  case 1:\n"
+        "   value = 1\n"
+        "   first = value\n"
+        "  case 2:\n"
+        "   value = 2\n"
+        "   second = value\n"
+        " after = value\n"
+    )
+    value_bindings = _stage_1c_named(facts, "binding", "value")
+    first_case = next(anchor for anchor in value_bindings if anchor.span.start_line == 5)
+    second_case = next(anchor for anchor in value_bindings if anchor.span.start_line == 8)
+    assert _stage_1c_lexical_bind_sources(facts, "value", 6) == [first_case.local_id]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 9) == [second_case.local_id]
+    assert _stage_1c_lexical_bind_sources(facts, "value", 10) == []
+
+
 def test_stage_1c_for_target_is_runtime_bound_only_inside_loop_body():
     facts = _stage_1c_facts(
         "def run(items):\n"

