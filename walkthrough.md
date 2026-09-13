# F2L D1J Repair Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## FALSE_TRUNCATION_PROOF

The reached-occurrence map records each non-terminal occurrence at its first FIFO BFS depth. Converging paths therefore preserve the minimal depth and do not report truncation when the final selected flow set already includes the depth-frontier adjacency.

## TRUE_TRUNCATION_PROOF

After BFS, truncation is calculated only from non-terminal occurrences first reached exactly at the depth limit that still have an unselected directional adjacency flow. The dedicated depth-two tail regression reports `truncated=True`.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py`: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py`: PASS — 54 passed in 1.56s.
- `git diff --check` for task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

Full current diff for each task file, covering D1J and this repair.

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index ac158d6..5cbf0ee 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -524,11 +524,10 @@ class LineageQueryService:
             tuple[MaterializedOccurrenceRef, int]
         ] = [(seed, 0)]
         queue_index = 0
-        visited_occurrences = {seed}
+        reached_occurrence_depths = {seed: 0}
         selected_flows: set[tuple] = set()
         steps: list[LineageTraversalStep] = []
         boundaries: list[LineageTraversalBoundary] = []
-        truncated = False

         while queue_index < len(queue):
             current, current_depth = queue[queue_index]
@@ -605,23 +604,28 @@ class LineageQueryService:
                         "unsupported endpoint type."
                     )

-                if step_depth < max_depth:
-                    if next_endpoint not in visited_occurrences:
-                        visited_occurrences.add(next_endpoint)
+                if next_endpoint not in reached_occurrence_depths:
+                    reached_occurrence_depths[
+                        next_endpoint
+                    ] = step_depth
+                    if step_depth < max_depth:
                         queue.append(
                             (next_endpoint, step_depth)
                         )
-                    continue

-                if any(
-                    _flow_match_identity(candidate)
-                    not in selected_flows
-                    for candidate in adjacency.get(
-                        next_endpoint,
-                        (),
-                    )
-                ):
-                    truncated = True
+        truncated = any(
+            depth == max_depth
+            and any(
+                _flow_match_identity(candidate)
+                not in selected_flows
+                for candidate in adjacency.get(
+                    occurrence,
+                    (),
+                )
+            )
+            for occurrence, depth
+            in reached_occurrence_depths.items()
+        )

         return LocalLineageTraversal(
             target=target,
```

### contextor/core/lineage_query/__init__.py

```diff

```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 4173df8..4172a0b 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -1445,3 +1445,115 @@ def test_local_traversal_rejects_invalid_bounds(
             direction=direction,
             max_depth=max_depth,
         )
+def test_local_traversal_does_not_report_false_truncation_for_converging_paths():
+    service, backend, target = _lexical_scope_service()
+    fp = "d" * 64
+    outer = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "outer",
+    )
+    outer_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "outer-result",
+    )
+    tail = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "tail",
+    )
+
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "aa_shortcut",
+            outer,
+            outer_result,
+            LineageRelation.ALIASES,
+            SourceSpan(10, 0, 10, 5),
+            ResolutionKind.LEXICAL_EXACT,
+            LineageConfidence.CONFIRMED,
+            owner_local_id="outer",
+        ),
+    )
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_tail",
+            outer_result,
+            tail,
+            LineageRelation.ASSIGNS,
+            SourceSpan(11, 0, 11, 5),
+            ResolutionKind.LEXICAL_EXACT,
+            LineageConfidence.CONFIRMED,
+            owner_local_id="outer",
+        ),
+    )
+
+    result = service.traverse_lexical_scope(
+        target,
+        outer,
+        direction="downstream",
+        max_depth=2,
+    )
+
+    assert tuple(
+        (step.depth, step.flow.flow.local_id)
+        for step in result.steps
+    ) == (
+        (1, "a_outer_bind"),
+        (1, "aa_shortcut"),
+        (2, "b_outer_call"),
+        (2, "z_tail"),
+    )
+    assert result.truncated is False
+
+
+def test_local_traversal_reports_true_truncation_from_minimal_depth_frontier():
+    service, backend, target = _lexical_scope_service()
+    fp = "d" * 64
+    outer_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "outer-result",
+    )
+    tail = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "tail",
+    )
+
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_tail",
+            outer_result,
+            tail,
+            LineageRelation.ASSIGNS,
+            SourceSpan(11, 0, 11, 5),
+            ResolutionKind.LEXICAL_EXACT,
+            LineageConfidence.CONFIRMED,
+            owner_local_id="outer",
+        ),
+    )
+
+    result = service.traverse_lexical_scope(
+        target,
+        MaterializedOccurrenceRef(
+            "pkg/target.py",
+            fp,
+            "outer",
+        ),
+        direction="downstream",
+        max_depth=2,
+    )
+
+    assert tuple(
+        step.flow.flow.local_id
+        for step in result.steps
+    ) == (
+        "a_outer_bind",
+        "b_outer_call",
+    )
+    assert result.truncated is True
```
