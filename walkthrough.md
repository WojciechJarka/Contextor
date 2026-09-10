STATUS=FINAL_PASS
FINAL_CANONICAL_REVISION=550

EDIT_CONTEXT_FACADE=
FINAL canonical revision 550. canonical_state=fresh; workspace_sync=verified; provenance=live; syntax_diagnostics.status=checked_and_none with fresh availability and no errors. Canonical diagnostics: name_collisions.count=0 fresh; cycles.count=0 fresh.

EDIT_CONTEXT_CONTROL=
FINAL canonical revision 550. canonical_state=fresh; workspace_sync=verified; provenance=live; syntax_diagnostics.status=checked_and_none with fresh availability and no errors. Canonical diagnostics: name_collisions.count=0 fresh; cycles.count=0 fresh.

COLLISION_EVIDENCE=
Both final edit-context diagnostic summaries report name_collisions.count=0 with availability=fresh. Contextor active pool was available; deferred availability was not a blocker.

CYCLE_EVIDENCE=
Both final edit-context diagnostic summaries report cycles.count=0 with availability=fresh.

DEPENDENCY_EVIDENCE=
Canonical revision 550 module graph confirms facade -> control as a hard dependency. Control has exactly one inbound consumer, the facade. Control's exactly three outbound hard dependencies are lineage_extraction_emit, lineage_extraction_state, and contextor.core.domain.lineage_facts; it does not import facade, bindings, comprehensions, calls, or contracts.

LIVE_EVIDENCE=
get_live_events(after_revision=547, limit=5) returned activity_resync_required=false and final revision 550: desktop_watcher UPDATED lineage_extraction_control at revision 549 and UPDATED lineage_extraction at revision 550. Both final edit-contexts at revision 550 are fresh and verified.

CONTROL_OWNERSHIP=
Textual verification: all 12 supplied semantic visitors are functions in control. The 12 corresponding facade _visit_* methods are forwarding-only adapters.

DISPATCH_INVARIANT=
The sole dynamic dispatch remains _AnchorExtractor._visit at facade line 205: getattr(self, f"_visit_{type(node).__name__}", None). Control has zero def _visit_*, ast.walk, NodeVisitor, getattr dynamic dispatch, and LineageExtractionState() construction.

COMPLIANCE_NOTE=
Control formatting differs from the literal supplied formatting. No formatting change was made during this certification; semantic statement order and callback boundaries remain identical to the accepted D5B implementation.

TEST_RESULTS=2 PASS;97 PASS;110 PASS
DIFF_CHECK=PASS
FILES_CHANGED=
contextor/core/analysis/lineage_extraction.py
contextor/core/analysis/lineage_extraction_control.py
walkthrough.md (report-only; excluded from FULL_DIFFS)

FULL_DIFFS=
```diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index df81ff9..1cbd85c 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -26,7 +26,21 @@ from contextor.core.analysis.lineage_extraction_comprehensions import (
     publish_executed_walrus,
     visit_comprehension_expression,
 )
-from contextor.core.analysis.lineage_extraction_control import visit_block_from_frame
+from contextor.core.analysis.lineage_extraction_control import (
+    visit_async_for,
+    visit_async_with,
+    visit_block_from_frame,
+    visit_except_handler,
+    visit_for,
+    visit_if,
+    visit_match,
+    visit_match_as,
+    visit_match_mapping,
+    visit_match_star,
+    visit_try,
+    visit_while,
+    visit_with,
+)
 from contextor.core.analysis.lineage_extraction_bindings import (
     assign_target,
     runtime_bind_target,
@@ -352,143 +366,22 @@ class _AnchorExtractor:
         visit_aug_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)
 
     def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.test, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
-        body_frame = self._visit_block_from_frame(
-            node.body,
-            owner,
-            walrus_owner,
-            entry_frame,
-        )
-        if node.orelse:
-            else_frame = self._visit_block_from_frame(
-                node.orelse,
-                owner,
-                walrus_owner,
-                entry_frame,
-            )
-        else:
-            else_frame = dict(entry_frame)
-        self._replace_frame(
-            owner,
-            self._merge_frames((body_frame, else_frame)),
-        )
+        return visit_if(self.state, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.iter, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
-        self._replace_frame(owner, entry_frame)
-        self._runtime_bind_target(
-            node.target,
-            owner,
-            walrus_owner,
-        )
-        for child in node.body:
-            self._visit(child, owner, walrus_owner)
-        body_frame = self._clone_frame(owner)
-        loop_exit_frame = self._merge_frames(
-            (entry_frame, body_frame)
-        )
-        self._replace_frame(owner, loop_exit_frame)
-        if not node.orelse:
-            return
-        else_frame = self._visit_block_from_frame(
-            node.orelse,
-            owner,
-            walrus_owner,
-            loop_exit_frame,
-        )
-        self._replace_frame(
-            owner,
-            self._merge_frames((loop_exit_frame, else_frame)),
-        )
+        return visit_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
 
     def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.iter, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
-        self._replace_frame(owner, entry_frame)
-        self._runtime_bind_target(
-            node.target,
-            owner,
-            walrus_owner,
-        )
-        for child in node.body:
-            self._visit(child, owner, walrus_owner)
-        body_frame = self._clone_frame(owner)
-        loop_exit_frame = self._merge_frames(
-            (entry_frame, body_frame)
-        )
-        self._replace_frame(owner, loop_exit_frame)
-        if not node.orelse:
-            return
-        else_frame = self._visit_block_from_frame(
-            node.orelse,
-            owner,
-            walrus_owner,
-            loop_exit_frame,
-        )
-        self._replace_frame(
-            owner,
-            self._merge_frames((loop_exit_frame, else_frame)),
-        )
+        return visit_async_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
 
     def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.test, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
-        body_frame = self._visit_block_from_frame(
-            node.body,
-            owner,
-            walrus_owner,
-            entry_frame,
-        )
-        loop_exit_frame = self._merge_frames(
-            (entry_frame, body_frame)
-        )
-        self._replace_frame(owner, loop_exit_frame)
-        if not node.orelse:
-            return
-        else_frame = self._visit_block_from_frame(
-            node.orelse,
-            owner,
-            walrus_owner,
-            loop_exit_frame,
-        )
-        self._replace_frame(
-            owner,
-            self._merge_frames((loop_exit_frame, else_frame)),
-        )
+        return visit_while(self.state, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
-        for item in node.items:
-            self._visit(
-                item.context_expr,
-                owner,
-                walrus_owner,
-            )
-            if item.optional_vars is not None:
-                self._runtime_bind_target(
-                    item.optional_vars,
-                    owner,
-                    walrus_owner,
-                )
-        for child in node.body:
-            self._visit(child, owner, walrus_owner)
+        return visit_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
 
     def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
-        for item in node.items:
-            self._visit(
-                item.context_expr,
-                owner,
-                walrus_owner,
-            )
-            if item.optional_vars is not None:
-                self._runtime_bind_target(
-                    item.optional_vars,
-                    owner,
-                    walrus_owner,
-                )
-        for child in node.body:
-            self._visit(child, owner, walrus_owner)
+        return visit_async_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
 
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
         for alias in node.names:
@@ -511,100 +404,22 @@ class _AnchorExtractor:
         visit_nonlocal(self.state, self.paths, node, owner)
 
     def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
-        entry_frame = self._clone_frame(owner)
-        normal_frame = self._visit_block_from_frame(
-            node.body,
-            owner,
-            walrus_owner,
-            entry_frame,
-        )
-        if node.orelse:
-            normal_frame = self._visit_block_from_frame(
-                node.orelse,
-                owner,
-                walrus_owner,
-                normal_frame,
-            )
-        reachable_frames = [normal_frame]
-        for handler in node.handlers:
-            self._replace_frame(owner, entry_frame)
-            self._visit(handler, owner, walrus_owner)
-            reachable_frames.append(
-                self._clone_frame(owner)
-            )
-        merged_frame = self._merge_frames(
-            tuple(reachable_frames)
-        )
-        self._replace_frame(owner, merged_frame)
-        for child in node.finalbody:
-            self._visit(child, owner, walrus_owner)
+        return visit_try(self.state, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
-        if node.type is not None:
-            self._visit(node.type, owner, walrus_owner)
-        alias_name = node.name if isinstance(node.name, str) else None
-        if alias_name is not None:
-            binding = ExtractedOccurrenceRef(
-                self._add("binding", node, alias_name, owner)
-            )
-            if alias_name not in self._blocked_names(owner):
-                source = self._occurrence(
-                    "runtime_bound_local",
-                    node,
-                    alias_name,
-                )
-                self._frame(owner)[alias_name] = binding
-                self._flow(
-                    source=source,
-                    target=binding,
-                    relation=LineageRelation.ASSIGNS,
-                    node=node,
-                    resolution_kind=ResolutionKind.LEXICAL_EXACT,
-                    confidence=LineageConfidence.CONFIRMED,
-                )
-        for child in node.body:
-            self._visit(child, owner, walrus_owner)
-        exit_frame = self._clone_frame(owner)
-        if alias_name is not None:
-            exit_frame.pop(alias_name, None)
-        self._replace_frame(owner, exit_frame)
+        return visit_except_handler(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.subject, owner, walrus_owner)
-        entry_frame = self._clone_frame(owner)
-        reachable_frames = [dict(entry_frame)]
-        for case in node.cases:
-            self._replace_frame(owner, entry_frame)
-            self._visit(case.pattern, owner, walrus_owner)
-            if case.guard is not None:
-                self._visit(case.guard, owner, walrus_owner)
-            for child in case.body:
-                self._visit(child, owner, walrus_owner)
-            reachable_frames.append(
-                self._clone_frame(owner)
-            )
-        self._replace_frame(
-            owner,
-            self._merge_frames(tuple(reachable_frames)),
-        )
+        return visit_match(self.state, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
-        if node.pattern is not None:
-            self._visit(node.pattern, owner, walrus_owner)
-        if node.name is not None:
-            self._add("binding", node, node.name, owner)
+        return visit_match_as(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
 
     def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
-        if node.name is not None:
-            self._add("binding", node, node.name, owner)
+        return visit_match_star(self.state, self.paths, node, owner)
 
     def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
-        for key in node.keys:
-            self._visit(key, owner, walrus_owner)
-        for pattern in node.patterns:
-            self._visit(pattern, owner, walrus_owner)
-        if node.rest is not None:
-            self._add("binding", node, node.rest, owner)
+        return visit_match_mapping(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
 
 
 def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
diff --git a/contextor/core/analysis/lineage_extraction_control.py b/contextor/core/analysis/lineage_extraction_control.py
index 976208f..ba85b63 100644
--- a/contextor/core/analysis/lineage_extraction_control.py
+++ b/contextor/core/analysis/lineage_extraction_control.py
@@ -3,23 +3,163 @@ from __future__ import annotations
 import ast
 from collections.abc import Callable
 
+from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
-from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef
-
+from contextor.core.domain.lineage_facts import (
+    ExtractedOccurrenceRef,
+    LineageConfidence,
+    LineageRelation,
+    ResolutionKind,
+)
 
 VisitFn = Callable[[ast.AST, str | None, str | None], None]
+RuntimeBindTargetFn = Callable[[ast.AST, str | None, str | None], None]
 
 
-def visit_block_from_frame(
-    state: LineageExtractionState,
-    body: list[ast.stmt],
-    owner: str | None,
-    walrus_owner: str | None,
-    frame: dict[str, ExtractedOccurrenceRef],
-    *,
-    visit: VisitFn,
-) -> dict[str, ExtractedOccurrenceRef]:
+def visit_block_from_frame(state: LineageExtractionState, body: list[ast.stmt], owner: str | None, walrus_owner: str | None, frame: dict[str, ExtractedOccurrenceRef], *, visit: VisitFn) -> dict[str, ExtractedOccurrenceRef]:
     state.replace_frame(owner, frame)
     for child in body:
         visit(child, owner, walrus_owner)
     return state.clone_frame(owner)
+
+
+def visit_if(state: LineageExtractionState, node: ast.If, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    visit(node.test, owner, walrus_owner)
+    entry_frame = state.clone_frame(owner)
+    body_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
+    if node.orelse:
+        else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, entry_frame, visit=visit)
+    else:
+        else_frame = dict(entry_frame)
+    state.replace_frame(owner, state.merge_frames((body_frame, else_frame)))
+
+
+def visit_for(state: LineageExtractionState, node: ast.For, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
+    visit(node.iter, owner, walrus_owner)
+    entry_frame = state.clone_frame(owner)
+    state.replace_frame(owner, entry_frame)
+    runtime_bind_target(node.target, owner, walrus_owner)
+    for child in node.body:
+        visit(child, owner, walrus_owner)
+    body_frame = state.clone_frame(owner)
+    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
+    state.replace_frame(owner, loop_exit_frame)
+    if not node.orelse:
+        return
+    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
+    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))
+
+
+def visit_async_for(state: LineageExtractionState, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
+    visit(node.iter, owner, walrus_owner)
+    entry_frame = state.clone_frame(owner)
+    state.replace_frame(owner, entry_frame)
+    runtime_bind_target(node.target, owner, walrus_owner)
+    for child in node.body:
+        visit(child, owner, walrus_owner)
+    body_frame = state.clone_frame(owner)
+    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
+    state.replace_frame(owner, loop_exit_frame)
+    if not node.orelse:
+        return
+    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
+    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))
+
+
+def visit_while(state: LineageExtractionState, node: ast.While, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    visit(node.test, owner, walrus_owner)
+    entry_frame = state.clone_frame(owner)
+    body_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
+    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
+    state.replace_frame(owner, loop_exit_frame)
+    if not node.orelse:
+        return
+    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
+    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))
+
+
+def visit_with(state: LineageExtractionState, node: ast.With, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
+    for item in node.items:
+        visit(item.context_expr, owner, walrus_owner)
+        if item.optional_vars is not None:
+            runtime_bind_target(item.optional_vars, owner, walrus_owner)
+    for child in node.body:
+        visit(child, owner, walrus_owner)
+
+
+def visit_async_with(state: LineageExtractionState, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
+    for item in node.items:
+        visit(item.context_expr, owner, walrus_owner)
+        if item.optional_vars is not None:
+            runtime_bind_target(item.optional_vars, owner, walrus_owner)
+    for child in node.body:
+        visit(child, owner, walrus_owner)
+
+
+def visit_try(state: LineageExtractionState, node: ast.Try, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    entry_frame = state.clone_frame(owner)
+    normal_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
+    if node.orelse:
+        normal_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, normal_frame, visit=visit)
+    reachable_frames = [normal_frame]
+    for handler in node.handlers:
+        state.replace_frame(owner, entry_frame)
+        visit(handler, owner, walrus_owner)
+        reachable_frames.append(state.clone_frame(owner))
+    state.replace_frame(owner, state.merge_frames(tuple(reachable_frames)))
+    for child in node.finalbody:
+        visit(child, owner, walrus_owner)
+
+
+def visit_except_handler(state: LineageExtractionState, paths: dict[int, str], node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    if node.type is not None:
+        visit(node.type, owner, walrus_owner)
+    alias_name = node.name if isinstance(node.name, str) else None
+    if alias_name is not None:
+        binding = ExtractedOccurrenceRef(add_anchor(state, paths, "binding", node, alias_name, owner))
+        if alias_name not in state.blocked_names(owner):
+            source = occurrence(state, paths, "runtime_bound_local", node, alias_name)
+            state.frame(owner)[alias_name] = binding
+            emit_flow(state, paths, source=source, target=binding, relation=LineageRelation.ASSIGNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+    for child in node.body:
+        visit(child, owner, walrus_owner)
+    exit_frame = state.clone_frame(owner)
+    if alias_name is not None:
+        exit_frame.pop(alias_name, None)
+    state.replace_frame(owner, exit_frame)
+
+
+def visit_match(state: LineageExtractionState, node: ast.Match, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    visit(node.subject, owner, walrus_owner)
+    entry_frame = state.clone_frame(owner)
+    reachable_frames = [dict(entry_frame)]
+    for case in node.cases:
+        state.replace_frame(owner, entry_frame)
+        visit(case.pattern, owner, walrus_owner)
+        if case.guard is not None:
+            visit(case.guard, owner, walrus_owner)
+        for child in case.body:
+            visit(child, owner, walrus_owner)
+        reachable_frames.append(state.clone_frame(owner))
+    state.replace_frame(owner, state.merge_frames(tuple(reachable_frames)))
+
+
+def visit_match_as(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchAs, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    if node.pattern is not None:
+        visit(node.pattern, owner, walrus_owner)
+    if node.name is not None:
+        add_anchor(state, paths, "binding", node, node.name, owner)
+
+
+def visit_match_star(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchStar, owner: str | None) -> None:
+    if node.name is not None:
+        add_anchor(state, paths, "binding", node, node.name, owner)
+
+
+def visit_match_mapping(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchMapping, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
+    for key in node.keys:
+        visit(key, owner, walrus_owner)
+    for pattern in node.patterns:
+        visit(pattern, owner, walrus_owner)
+    if node.rest is not None:
+        add_anchor(state, paths, "binding", node, node.rest, owner)
```
