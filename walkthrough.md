# F2L D1J Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## SEED_CONTRACT

Traversal accepts only a `MaterializedOccurrenceRef` seed occurring in the exact lexical-scope graph. An incomplete scope or an outside seed returns no steps or boundaries.

## DETERMINISTIC_BFS_PROOF

Traversal constructs adjacency only from `scope.flows`, sorts matches with the established flow key, uses a bounded FIFO BFS, and selects each flow at most once.

## UPSTREAM_DOWNSTREAM_PROOF

Downstream follows source-to-target and upstream follows target-to-source. Focused regressions assert the exact step sequence for both directions.

## TERMINAL_BOUNDARY_PROOF

Symbolic and semantic endpoints are terminal boundaries. Dynamic and unresolved flows are also terminal, even when their endpoint is an occurrence; terminal flows are reported but never enqueued.

## CYCLE_PROOF

Visited occurrences and selected flow identities prevent cycle re-expansion and duplicate steps. The cycle regression finishes without truncation.

## TRUNCATION_PROOF

`truncated=True` is set only where the depth limit leaves an unselected directional flow from a reached occurrence. Terminal boundaries do not cause truncation.

## FAIL_CLOSED_PROOF

Incomplete lexical ownership metadata and an outside seed both return empty traversal results with traversal unavailable.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py`: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py`: PASS — 52 passed in 2.19s.
- `git diff --check` for task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index a340b81..ac158d6 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -3,10 +3,13 @@ from __future__ import annotations
 from dataclasses import dataclass

 from contextor.core.domain.lineage_facts import (
+    LineageConfidence,
     MaterializedAnchorFact,
     MaterializedFlowFact,
     MaterializedOccurrenceRef,
     MaterializedSurfaceFact,
+    MaterializedSymbolicRef,
+    ResolutionKind,
     SemanticAnchorBinding,
     SemanticEndpoint,
 )
@@ -109,6 +112,41 @@ class LexicalScopeFacts:
         )


+@dataclass(frozen=True)
+class LineageTraversalStep:
+    depth: int
+    flow: LineageFlowMatch
+
+
+@dataclass(frozen=True)
+class LineageTraversalBoundary:
+    depth: int
+    flow: LineageFlowMatch
+    endpoint: (
+        MaterializedOccurrenceRef
+        | MaterializedSymbolicRef
+        | SemanticEndpoint
+    )
+    reason: str
+
+
+@dataclass(frozen=True)
+class LocalLineageTraversal:
+    target: ResolvedLineageTarget
+    scope: LexicalScopeFacts
+    seed: MaterializedOccurrenceRef
+    direction: str
+    max_depth: int
+    seed_in_scope: bool
+    steps: tuple[LineageTraversalStep, ...]
+    boundaries: tuple[LineageTraversalBoundary, ...]
+    truncated: bool
+
+    @property
+    def traversal_available(self) -> bool:
+        return self.scope.complete and self.seed_in_scope
+
+
 @dataclass(frozen=True)
 class DirectLineageFacts:
     target: ResolvedLineageTarget
@@ -402,6 +440,201 @@ class LineageQueryService:
         )


+    def traverse_lexical_scope(
+        self,
+        target: ResolvedLineageTarget,
+        seed: MaterializedOccurrenceRef,
+        *,
+        direction: str,
+        max_depth: int = 1,
+    ) -> LocalLineageTraversal:
+        if not isinstance(target, ResolvedLineageTarget):
+            raise TypeError(
+                "target must be ResolvedLineageTarget."
+            )
+        if not isinstance(seed, MaterializedOccurrenceRef):
+            raise TypeError(
+                "seed must be MaterializedOccurrenceRef."
+            )
+        if direction not in {"upstream", "downstream"}:
+            raise ValueError(
+                "direction must be 'upstream' or 'downstream'."
+            )
+        if (
+            isinstance(max_depth, bool)
+            or not isinstance(max_depth, int)
+            or not 1 <= max_depth <= 3
+        ):
+            raise ValueError(
+                "max_depth must be an integer from 1 to 3."
+            )
+
+        scope = self.lexical_scope_facts(target)
+
+        scope_occurrences: set[
+            MaterializedOccurrenceRef
+        ] = set()
+        for match in scope.flows:
+            if isinstance(
+                match.flow.source,
+                MaterializedOccurrenceRef,
+            ):
+                scope_occurrences.add(match.flow.source)
+            if isinstance(
+                match.flow.target,
+                MaterializedOccurrenceRef,
+            ):
+                scope_occurrences.add(match.flow.target)
+
+        seed_in_scope = seed in scope_occurrences
+        if not scope.complete or not seed_in_scope:
+            return LocalLineageTraversal(
+                target=target,
+                scope=scope,
+                seed=seed,
+                direction=direction,
+                max_depth=max_depth,
+                seed_in_scope=seed_in_scope,
+                steps=(),
+                boundaries=(),
+                truncated=False,
+            )
+
+        adjacency: dict[
+            MaterializedOccurrenceRef,
+            list[LineageFlowMatch],
+        ] = {}
+        for match in scope.flows:
+            endpoint = (
+                match.flow.source
+                if direction == "downstream"
+                else match.flow.target
+            )
+            if not isinstance(
+                endpoint,
+                MaterializedOccurrenceRef,
+            ):
+                continue
+            adjacency.setdefault(endpoint, []).append(match)
+
+        for matches in adjacency.values():
+            matches.sort(key=_flow_match_key)
+
+        queue: list[
+            tuple[MaterializedOccurrenceRef, int]
+        ] = [(seed, 0)]
+        queue_index = 0
+        visited_occurrences = {seed}
+        selected_flows: set[tuple] = set()
+        steps: list[LineageTraversalStep] = []
+        boundaries: list[LineageTraversalBoundary] = []
+        truncated = False
+
+        while queue_index < len(queue):
+            current, current_depth = queue[queue_index]
+            queue_index += 1
+
+            for match in adjacency.get(current, ()):
+                flow_key = _flow_match_identity(match)
+                if flow_key in selected_flows:
+                    continue
+
+                step_depth = current_depth + 1
+                selected_flows.add(flow_key)
+                steps.append(
+                    LineageTraversalStep(
+                        depth=step_depth,
+                        flow=match,
+                    )
+                )
+
+                next_endpoint = (
+                    match.flow.target
+                    if direction == "downstream"
+                    else match.flow.source
+                )
+
+                terminal_reason = _terminal_flow_reason(
+                    match.flow
+                )
+                if terminal_reason is not None:
+                    boundaries.append(
+                        LineageTraversalBoundary(
+                            depth=step_depth,
+                            flow=match,
+                            endpoint=next_endpoint,
+                            reason=terminal_reason,
+                        )
+                    )
+                    continue
+
+                if isinstance(
+                    next_endpoint,
+                    MaterializedSymbolicRef,
+                ):
+                    boundaries.append(
+                        LineageTraversalBoundary(
+                            depth=step_depth,
+                            flow=match,
+                            endpoint=next_endpoint,
+                            reason="symbolic",
+                        )
+                    )
+                    continue
+
+                if isinstance(
+                    next_endpoint,
+                    SemanticEndpoint,
+                ):
+                    boundaries.append(
+                        LineageTraversalBoundary(
+                            depth=step_depth,
+                            flow=match,
+                            endpoint=next_endpoint,
+                            reason="semantic",
+                        )
+                    )
+                    continue
+
+                if not isinstance(
+                    next_endpoint,
+                    MaterializedOccurrenceRef,
+                ):
+                    raise TypeError(
+                        "Canonical lineage flow has an "
+                        "unsupported endpoint type."
+                    )
+
+                if step_depth < max_depth:
+                    if next_endpoint not in visited_occurrences:
+                        visited_occurrences.add(next_endpoint)
+                        queue.append(
+                            (next_endpoint, step_depth)
+                        )
+                    continue
+
+                if any(
+                    _flow_match_identity(candidate)
+                    not in selected_flows
+                    for candidate in adjacency.get(
+                        next_endpoint,
+                        (),
+                    )
+                ):
+                    truncated = True
+
+        return LocalLineageTraversal(
+            target=target,
+            scope=scope,
+            seed=seed,
+            direction=direction,
+            max_depth=max_depth,
+            seed_in_scope=True,
+            steps=tuple(steps),
+            boundaries=tuple(boundaries),
+            truncated=truncated,
+        )
+
 def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
     binding = match.binding
     reference = binding.reference
@@ -466,6 +699,33 @@ def _flow_match_key(match: LineageFlowMatch) -> tuple:
     )


+def _flow_match_identity(
+    match: LineageFlowMatch,
+) -> tuple[str, str, str]:
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        match.flow.local_id,
+    )
+
+
+def _terminal_flow_reason(
+    flow: MaterializedFlowFact,
+) -> str | None:
+    if (
+        flow.resolution_kind
+        is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+        or flow.confidence is LineageConfidence.DYNAMIC
+    ):
+        return "dynamic"
+    if (
+        flow.resolution_kind
+        is ResolutionKind.UNRESOLVED_NAME
+        or flow.confidence is LineageConfidence.UNRESOLVED
+    ):
+        return "unresolved"
+    return None
+
 def _surface_match_key(match: LineageSurfaceMatch) -> tuple:
     surface = match.surface
     evidence = surface.evidence
```

### contextor/core/lineage_query/__init__.py

```diff
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
index 3bd7cdd..29ed990 100644
--- a/contextor/core/lineage_query/__init__.py
+++ b/contextor/core/lineage_query/__init__.py
@@ -13,6 +13,9 @@ from contextor.core.lineage_query.service import (
     LineageScopeRootMatch,
     LineageSurfaceMatch,
     LineageTargetResolution,
+    LineageTraversalBoundary,
+    LineageTraversalStep,
+    LocalLineageTraversal,
     ResolvedLineageTarget,
 )

@@ -28,6 +31,9 @@ __all__ = [
     "LineageScopeRootMatch",
     "LineageSurfaceMatch",
     "LineageTargetResolution",
+    "LineageTraversalBoundary",
+    "LineageTraversalStep",
+    "LocalLineageTraversal",
     "RepositoryStateLineageBackend",
     "ResolvedLineageTarget",
 ]
```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 1a9cba3..4173df8 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -1078,3 +1078,370 @@ def test_lexical_scope_facts_fail_closed_for_multiple_exact_roots():
     assert result.complete is False
     assert result.flows == ()
     assert result.nested_scopes == ()
+def _append_scope_flow(backend, flow):
+    source = backend.get_source("pkg/target.py")
+    assert source is not None
+    backend._sources["pkg/target.py"] = replace(
+        source,
+        manifest=replace(
+            source.manifest,
+            flow_count=source.manifest.flow_count + 1,
+        ),
+        flows=tuple(
+            sorted(
+                (
+                    *source.flows,
+                    flow,
+                )
+            )
+        ),
+    )
+
+
+def test_local_traversal_downstream_is_deterministic_and_bounded():
+    service, _, target = _lexical_scope_service()
+    seed = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer",
+    )
+
+    depth_one = service.traverse_lexical_scope(
+        target,
+        seed,
+        direction="downstream",
+        max_depth=1,
+    )
+    depth_two = service.traverse_lexical_scope(
+        target,
+        seed,
+        direction="downstream",
+        max_depth=2,
+    )
+
+    assert depth_one.traversal_available is True
+    assert depth_one.seed_in_scope is True
+    assert tuple(
+        (step.depth, step.flow.flow.local_id)
+        for step in depth_one.steps
+    ) == (
+        (1, "a_outer_bind"),
+    )
+    assert depth_one.truncated is True
+
+    assert tuple(
+        (step.depth, step.flow.flow.local_id)
+        for step in depth_two.steps
+    ) == (
+        (1, "a_outer_bind"),
+        (2, "b_outer_call"),
+    )
+    assert depth_two.truncated is False
+
+
+def test_local_traversal_upstream_reverses_exact_local_edges():
+    service, _, target = _lexical_scope_service()
+    seed = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer-result",
+    )
+
+    result = service.traverse_lexical_scope(
+        target,
+        seed,
+        direction="upstream",
+        max_depth=2,
+    )
+
+    assert result.traversal_available is True
+    assert tuple(
+        (step.depth, step.flow.flow.local_id)
+        for step in result.steps
+    ) == (
+        (1, "b_outer_call"),
+        (2, "a_outer_bind"),
+    )
+    assert result.boundaries == ()
+    assert result.truncated is False
+
+
+def test_local_traversal_symbolic_endpoint_is_terminal_boundary():
+    service, backend, target = _lexical_scope_service()
+    outer_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer-result",
+    )
+    symbolic = MaterializedSymbolicRef(
+        source_key="pkg/target.py",
+        source_fingerprint="d" * 64,
+        kind=ExtractedSymbolicKind.RETURN,
+        module_name="external.pkg",
+        symbol_name="result",
+    )
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_symbolic_boundary",
+            outer_result,
+            symbolic,
+            LineageRelation.RETURNS,
+            SourceSpan(10, 0, 10, 5),
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
+            "d" * 64,
+            "outer",
+        ),
+        direction="downstream",
+        max_depth=3,
+    )
+
+    assert tuple(
+        step.flow.flow.local_id
+        for step in result.steps
+    ) == (
+        "a_outer_bind",
+        "b_outer_call",
+        "z_symbolic_boundary",
+    )
+    assert len(result.boundaries) == 1
+    assert result.boundaries[0].endpoint == symbolic
+    assert result.boundaries[0].reason == "symbolic"
+
+
+def test_local_traversal_semantic_endpoint_is_terminal_boundary():
+    service, backend, target = _lexical_scope_service()
+    outer_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer-result",
+    )
+    semantic = SemanticEndpoint("A99/1")
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_semantic_boundary",
+            outer_result,
+            semantic,
+            LineageRelation.CALL_RESULT,
+            SourceSpan(10, 0, 10, 5),
+            ResolutionKind.CALL_EXACT,
+            LineageConfidence.CONFIRMED,
+            owner_local_id="outer",
+        ),
+    )
+
+    result = service.traverse_lexical_scope(
+        target,
+        MaterializedOccurrenceRef(
+            "pkg/target.py",
+            "d" * 64,
+            "outer",
+        ),
+        direction="downstream",
+        max_depth=3,
+    )
+
+    assert result.boundaries[-1].endpoint == semantic
+    assert result.boundaries[-1].reason == "semantic"
+
+
+def test_local_traversal_dynamic_edge_is_terminal_even_with_occurrence_endpoint():
+    service, backend, target = _lexical_scope_service()
+    fp = "d" * 64
+    outer_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "outer-result",
+    )
+    dynamic_result = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "dynamic-result",
+    )
+    after_dynamic = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        fp,
+        "after-dynamic",
+    )
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "y_dynamic",
+            outer_result,
+            dynamic_result,
+            LineageRelation.CALL_RESULT,
+            SourceSpan(10, 0, 10, 5),
+            ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY,
+            LineageConfidence.DYNAMIC,
+            dynamic_boundary="dynamic_call",
+            owner_local_id="outer",
+        ),
+    )
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_after_dynamic",
+            dynamic_result,
+            after_dynamic,
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
+        max_depth=3,
+    )
+
+    returned = tuple(
+        step.flow.flow.local_id
+        for step in result.steps
+    )
+    assert returned == (
+        "a_outer_bind",
+        "b_outer_call",
+        "y_dynamic",
+    )
+    assert "z_after_dynamic" not in returned
+    assert result.boundaries[-1].endpoint == dynamic_result
+    assert result.boundaries[-1].reason == "dynamic"
+
+
+def test_local_traversal_cycle_is_bounded_without_duplicate_flows():
+    service, backend, target = _lexical_scope_service()
+    fp = "d" * 64
+    _append_scope_flow(
+        backend,
+        MaterializedFlowFact(
+            "z_cycle",
+            MaterializedOccurrenceRef(
+                "pkg/target.py",
+                fp,
+                "outer-result",
+            ),
+            MaterializedOccurrenceRef(
+                "pkg/target.py",
+                fp,
+                "outer",
+            ),
+            LineageRelation.ALIASES,
+            SourceSpan(10, 0, 10, 5),
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
+        max_depth=3,
+    )
+
+    assert tuple(
+        step.flow.flow.local_id
+        for step in result.steps
+    ) == (
+        "a_outer_bind",
+        "b_outer_call",
+        "z_cycle",
+    )
+    assert result.truncated is False
+
+
+def test_local_traversal_fails_closed_when_scope_is_incomplete():
+    service, _, target = _lexical_scope_service(
+        flow_ownership=False,
+    )
+    seed = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer",
+    )
+
+    result = service.traverse_lexical_scope(
+        target,
+        seed,
+        direction="downstream",
+        max_depth=2,
+    )
+
+    assert result.scope.complete is False
+    assert result.seed_in_scope is True
+    assert result.traversal_available is False
+    assert result.steps == ()
+    assert result.boundaries == ()
+    assert result.truncated is False
+
+
+def test_local_traversal_rejects_seed_outside_exact_scope():
+    service, _, target = _lexical_scope_service()
+
+    result = service.traverse_lexical_scope(
+        target,
+        MaterializedOccurrenceRef(
+            "pkg/target.py",
+            "d" * 64,
+            "not-in-scope",
+        ),
+        direction="downstream",
+        max_depth=2,
+    )
+
+    assert result.seed_in_scope is False
+    assert result.traversal_available is False
+    assert result.steps == ()
+
+
+@pytest.mark.parametrize(
+    ("direction", "max_depth", "exception"),
+    [
+        ("sideways", 1, ValueError),
+        ("downstream", 0, ValueError),
+        ("downstream", 4, ValueError),
+        ("downstream", True, ValueError),
+    ],
+)
+def test_local_traversal_rejects_invalid_bounds(
+    direction,
+    max_depth,
+    exception,
+):
+    service, _, target = _lexical_scope_service()
+    seed = MaterializedOccurrenceRef(
+        "pkg/target.py",
+        "d" * 64,
+        "outer",
+    )
+
+    with pytest.raises(exception):
+        service.traverse_lexical_scope(
+            target,
+            seed,
+            direction=direction,
+            max_depth=max_depth,
+        )
```
