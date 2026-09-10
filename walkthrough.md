STATUS=FINAL_PASS

TASK=Contextor Stage D4 — remove unrelated facade format churn.
BASE=52337fa59bf877b2781b834e0a69990b5b486649

SCOPE=Restored lineage_extraction.py exactly from BASE and reapplied only the six approved D4 changes: imports plus forwarding adapters for comprehension lifecycle, block control, and comprehension execution. Accepted control/comprehensions modules were not changed.

VERIFY=
- git diff --ignore-space-at-eol BASE -- lineage_extraction.py shows only the approved import and five adapter hunks.
- git diff --check BASE -- all three D4 production files: PASS.

TESTS=
- tests/analysis/test_lineage_extraction_equivalence.py -q: 2 passed.
- tests/analysis/test_lineage_extraction.py -q: 97 passed.
- tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q: 110 passed.

FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 65b54ba..9597c85 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -20,6 +20,13 @@ from contextor.core.analysis.lineage_extraction_contracts import (
 )
 from contextor.core.analysis.lineage_extraction_calls import bind_call_arguments, collect_call_arguments, current_import_info, default_flows, emit_argument_to_parameter, function_signature_evidence, parameter_anchors, register_import_binding, resolve_current_imported_callable, resolve_current_local_callable
 from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic, return_symbolic
+from contextor.core.analysis.lineage_extraction_comprehensions import (
+    begin_comprehension,
+    finish_comprehension,
+    publish_executed_walrus,
+    visit_comprehension_expression,
+)
+from contextor.core.analysis.lineage_extraction_control import visit_block_from_frame
 from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
@@ -75,24 +82,12 @@ class _AnchorExtractor:
         lexical_enclosing_owner: str | None,
         effective_walrus_owner: str | None,
     ) -> _ActiveComprehension:
-        record = _ActiveComprehension(
+        return begin_comprehension(
+            self.state,
             lookup_owner,
             lexical_enclosing_owner,
             effective_walrus_owner,
-            self._clone_frame(effective_walrus_owner),
-            set(),
-        )
-        self._replace_frame(
-            lookup_owner,
-            self._clone_frame(lexical_enclosing_owner),
         )
-        imports = self._import_frame(lookup_owner)
-        imports.clear()
-        imports.update(
-            self._import_frame(lexical_enclosing_owner)
-        )
-        self.state._active_comprehensions.append(record)
-        return record
 
     def _publish_executed_walrus(
         self,
@@ -100,46 +95,21 @@ class _AnchorExtractor:
         binding: ExtractedOccurrenceRef,
         target_owner: str | None,
     ) -> None:
-        for record in self.state._active_comprehensions:
-            if record.effective_walrus_owner != target_owner:
-                continue
-            record.touched_walrus_names.add(name)
-            self._frame(record.lookup_owner)[name] = binding
+        return publish_executed_walrus(
+            self.state,
+            name,
+            binding,
+            target_owner,
+        )
 
     def _finish_comprehension(
         self,
         record: _ActiveComprehension,
     ) -> None:
-        if (
-            not self.state._active_comprehensions
-            or self.state._active_comprehensions[-1] is not record
-        ):
-            raise RuntimeError(
-                "Comprehension lineage stack mismatch"
-            )
-        body_frame = self._clone_frame(
-            record.effective_walrus_owner
-        )
-        merged = self._merge_frames(
-            (record.walrus_entry_frame, body_frame)
+        return finish_comprehension(
+            self.state,
+            record,
         )
-        self._replace_frame(
-            record.effective_walrus_owner,
-            merged,
-        )
-        self.state._active_comprehensions.pop()
-        for parent in self.state._active_comprehensions:
-            if (
-                parent.effective_walrus_owner
-                != record.effective_walrus_owner
-            ):
-                continue
-            for name in record.touched_walrus_names:
-                parent.touched_walrus_names.add(name)
-                if name in merged:
-                    self._frame(parent.lookup_owner)[name] = merged[name]
-                else:
-                    self._frame(parent.lookup_owner).pop(name, None)
 
     def _merge_frames(
         self,
@@ -154,10 +124,14 @@ class _AnchorExtractor:
         walrus_owner: str | None,
         frame: dict[str, ExtractedOccurrenceRef],
     ) -> dict[str, ExtractedOccurrenceRef]:
-        self._replace_frame(owner, frame)
-        for child in body:
-            self._visit(child, owner, walrus_owner)
-        return self._clone_frame(owner)
+        return visit_block_from_frame(
+            self.state,
+            body,
+            owner,
+            walrus_owner,
+            frame,
+            visit=self._visit,
+        )
 
     def _blocked_names(self, owner: str | None) -> set[str]:
         return self.state.blocked_names(owner)
@@ -310,65 +284,17 @@ class _AnchorExtractor:
         owner: str | None,
         walrus_owner: str | None,
     ) -> None:
-        comprehension_id = self._add(
-            "comprehension",
+        return visit_comprehension_expression(
+            self.state,
+            self.paths,
             node,
-            None,
-            owner,
-        )
-        if not generators:
-            raise ValueError(
-                "Parsed comprehension without generators"
-            )
-        first = generators[0]
-        self._visit(
-            first.iter,
+            generators,
+            values,
             owner,
             walrus_owner,
+            visit=self._visit,
+            runtime_bind_target=self._runtime_bind_target,
         )
-        effective_walrus_owner = walrus_owner or owner
-        record = self._begin_comprehension(
-            comprehension_id,
-            owner,
-            effective_walrus_owner,
-        )
-        try:
-            self._runtime_bind_target(
-                first.target,
-                comprehension_id,
-                effective_walrus_owner,
-            )
-            for condition in first.ifs:
-                self._visit(
-                    condition,
-                    comprehension_id,
-                    effective_walrus_owner,
-                )
-            for generator in generators[1:]:
-                self._visit(
-                    generator.iter,
-                    comprehension_id,
-                    effective_walrus_owner,
-                )
-                self._runtime_bind_target(
-                    generator.target,
-                    comprehension_id,
-                    effective_walrus_owner,
-                )
-                for condition in generator.ifs:
-                    self._visit(
-                        condition,
-                        comprehension_id,
-                        effective_walrus_owner,
-                    )
-            for value in values:
-                self._visit(
-                    value,
-                    comprehension_id,
-                    effective_walrus_owner,
-                )
-        finally:
-            self._finish_comprehension(record)
 
     def _visit_ListComp(self, node, owner, walrus_owner) -> None:
         self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
diff --git a/contextor/core/analysis/lineage_extraction_control.py b/contextor/core/analysis/lineage_extraction_control.py
new file mode 100644
index 0000000..976208f
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_control.py
@@ -0,0 +1,25 @@
+from __future__ import annotations
+
+import ast
+from collections.abc import Callable
+
+from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
+from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef
+
+
+VisitFn = Callable[[ast.AST, str | None, str | None], None]
+
+
+def visit_block_from_frame(
+    state: LineageExtractionState,
+    body: list[ast.stmt],
+    owner: str | None,
+    walrus_owner: str | None,
+    frame: dict[str, ExtractedOccurrenceRef],
+    *,
+    visit: VisitFn,
+) -> dict[str, ExtractedOccurrenceRef]:
+    state.replace_frame(owner, frame)
+    for child in body:
+        visit(child, owner, walrus_owner)
+    return state.clone_frame(owner)
diff --git a/contextor/core/analysis/lineage_extraction_comprehensions.py b/contextor/core/analysis/lineage_extraction_comprehensions.py
new file mode 100644
index 0000000..64afdff
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_comprehensions.py
@@ -0,0 +1,165 @@
+from __future__ import annotations
+
+import ast
+from collections.abc import Callable
+
+from contextor.core.analysis.lineage_extraction_emit import add_anchor
+from contextor.core.analysis.lineage_extraction_state import (
+    _ActiveComprehension,
+    LineageExtractionState,
+)
+from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef
+
+VisitFn = Callable[[ast.AST, str | None, str | None], None]
+RuntimeBindTargetFn = Callable[[ast.AST, str | None, str | None], None]
+
+
+def begin_comprehension(
+    state: LineageExtractionState,
+    lookup_owner: str,
+    lexical_enclosing_owner: str | None,
+    effective_walrus_owner: str | None,
+) -> _ActiveComprehension:
+    record = _ActiveComprehension(
+        lookup_owner,
+        lexical_enclosing_owner,
+        effective_walrus_owner,
+        state.clone_frame(effective_walrus_owner),
+        set(),
+    )
+    state.replace_frame(
+        lookup_owner,
+        state.clone_frame(lexical_enclosing_owner),
+    )
+    imports = state.import_frame(lookup_owner)
+    imports.clear()
+    imports.update(
+        state.import_frame(lexical_enclosing_owner)
+    )
+    state._active_comprehensions.append(record)
+    return record
+
+
+def publish_executed_walrus(
+    state: LineageExtractionState,
+    name: str,
+    binding: ExtractedOccurrenceRef,
+    target_owner: str | None,
+) -> None:
+    for record in state._active_comprehensions:
+        if record.effective_walrus_owner != target_owner:
+            continue
+        record.touched_walrus_names.add(name)
+        state.frame(record.lookup_owner)[name] = binding
+
+
+def finish_comprehension(
+    state: LineageExtractionState,
+    record: _ActiveComprehension,
+) -> None:
+    if (
+        not state._active_comprehensions
+        or state._active_comprehensions[-1] is not record
+    ):
+        raise RuntimeError(
+            "Comprehension lineage stack mismatch"
+        )
+    body_frame = state.clone_frame(
+        record.effective_walrus_owner
+    )
+    merged = state.merge_frames(
+        (record.walrus_entry_frame, body_frame)
+    )
+    state.replace_frame(
+        record.effective_walrus_owner,
+        merged,
+    )
+    state._active_comprehensions.pop()
+    for parent in state._active_comprehensions:
+        if (
+            parent.effective_walrus_owner
+            != record.effective_walrus_owner
+        ):
+            continue
+        for name in record.touched_walrus_names:
+            parent.touched_walrus_names.add(name)
+            if name in merged:
+                state.frame(parent.lookup_owner)[name] = merged[name]
+            else:
+                state.frame(parent.lookup_owner).pop(name, None)
+
+
+def visit_comprehension_expression(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.AST,
+    generators: list[ast.comprehension],
+    values: tuple[ast.AST, ...],
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+    runtime_bind_target: RuntimeBindTargetFn,
+) -> None:
+    comprehension_id = add_anchor(
+        state,
+        paths,
+        "comprehension",
+        node,
+        None,
+        owner,
+    )
+    if not generators:
+        raise ValueError(
+            "Parsed comprehension without generators"
+        )
+    first = generators[0]
+    visit(
+        first.iter,
+        owner,
+        walrus_owner,
+    )
+    effective_walrus_owner = walrus_owner or owner
+    record = begin_comprehension(
+        state,
+        comprehension_id,
+        owner,
+        effective_walrus_owner,
+    )
+    try:
+        runtime_bind_target(
+            first.target,
+            comprehension_id,
+            effective_walrus_owner,
+        )
+        for condition in first.ifs:
+            visit(
+                condition,
+                comprehension_id,
+                effective_walrus_owner,
+            )
+        for generator in generators[1:]:
+            visit(
+                generator.iter,
+                comprehension_id,
+                effective_walrus_owner,
+            )
+            runtime_bind_target(
+                generator.target,
+                comprehension_id,
+                effective_walrus_owner,
+            )
+            for condition in generator.ifs:
+                visit(
+                    condition,
+                    comprehension_id,
+                    effective_walrus_owner,
+                )
+        for value in values:
+            visit(
+                value,
+                comprehension_id,
+                effective_walrus_owner,
+            )
+    finally:
+        finish_comprehension(state, record)

