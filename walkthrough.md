# F2L D1I Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## LEXICAL_SCOPE_CONTRACT

`lexical_scope_facts` reads only backend metadata, owner-index candidate keys, and those candidate slices. It returns exact root-owned flows plus immediate nested lexical scopes; no graph traversal, source read, AST work, materialization, or re-resolution is used.

## ROOT_FILTER_PROOF

A root requires an exact semantic-anchor binding for the resolved artifact and a matching anchor of kind class, function, async_function, lambda, or comprehension. The plain-binding regression returns no root and no scope facts.

## EXACT_OWNER_FILTER_PROOF

The target fixture returns only flows whose `owner_local_id` equals the exact root ID. Module defaults and nested-function/comprehension flows are excluded.

## NESTED_SCOPE_BOUNDARY_PROOF

Only direct lexical-anchor children of the root appear as `nested_scopes`; descendants are not expanded recursively.

## NO_REPO_SCAN_PROOF

The regression replaces `backend.source_keys` with a failure and `lexical_scope_facts` still succeeds, proving it uses only `source_keys_for_owner` plus `iter_sources`.

## COMPLETENESS_PROOF

Completeness requires a root, fresh global family/index metadata, complete semantic-anchor bindings, and fresh root-slice manifest state with both ownership flags. Regressions cover missing flow ownership, missing anchor ownership, and stale family state.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py`: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py`: PASS — 39 passed in 2.23s.
- `git diff --check` for task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/lineage_query/service.py

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
index ba8c258..922b66c 100644
--- a/contextor/core/lineage_query/service.py
+++ b/contextor/core/lineage_query/service.py
@@ -3,6 +3,7 @@ from __future__ import annotations
 from dataclasses import dataclass

 from contextor.core.domain.lineage_facts import (
+    MaterializedAnchorFact,
     MaterializedFlowFact,
     MaterializedOccurrenceRef,
     MaterializedSurfaceFact,
@@ -16,6 +17,17 @@ from contextor.core.lineage_query.backend import (
 from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog


+_LEXICAL_SCOPE_KINDS = frozenset(
+    {
+        "class",
+        "function",
+        "async_function",
+        "lambda",
+        "comprehension",
+    }
+)
+
+
 @dataclass(frozen=True)
 class ResolvedLineageTarget:
     artifact_id: str
@@ -54,6 +66,45 @@ class LineageSurfaceMatch:
     surface: MaterializedSurfaceFact


+@dataclass(frozen=True)
+class LineageScopeRootMatch:
+    source_key: str
+    source_fingerprint: str
+    binding: SemanticAnchorBinding
+    anchor: MaterializedAnchorFact
+
+
+@dataclass(frozen=True)
+class LineageLocalAnchorMatch:
+    source_key: str
+    source_fingerprint: str
+    anchor: MaterializedAnchorFact
+
+
+@dataclass(frozen=True)
+class LexicalScopeFacts:
+    target: ResolvedLineageTarget
+    metadata: LineageBackendMetadata
+    roots: tuple[LineageScopeRootMatch, ...]
+    flows: tuple[LineageFlowMatch, ...]
+    nested_scopes: tuple[LineageLocalAnchorMatch, ...]
+    materialization_complete: bool
+
+    @property
+    def scope_available(self) -> bool:
+        return bool(self.roots)
+
+    @property
+    def complete(self) -> bool:
+        return (
+            self.scope_available
+            and self.materialization_complete
+            and self.metadata.family_state == "fresh"
+            and self.metadata.query_index_state == "fresh"
+            and self.metadata.semantic_anchor_bindings_complete
+        )
+
+
 @dataclass(frozen=True)
 class DirectLineageFacts:
     target: ResolvedLineageTarget
@@ -244,6 +295,104 @@ class LineageQueryService:
             surfaces=tuple(surfaces),
         )

+    def lexical_scope_facts(
+        self,
+        target: ResolvedLineageTarget,
+    ) -> LexicalScopeFacts:
+        if not isinstance(target, ResolvedLineageTarget):
+            raise TypeError("target must be ResolvedLineageTarget.")
+
+        metadata = self._backend.metadata()
+        roots: list[LineageScopeRootMatch] = []
+        flows: list[LineageFlowMatch] = []
+        nested_scopes: list[LineageLocalAnchorMatch] = []
+        materialization_complete = True
+
+        source_keys = self._backend.source_keys_for_owner(
+            target.artifact_id
+        )
+        for source in self._backend.iter_sources(source_keys):
+            manifest = source.manifest
+            anchors_by_id = {
+                anchor.local_id: anchor
+                for anchor in source.anchors
+            }
+            root_ids: set[str] = set()
+
+            for binding in source.semantic_anchors:
+                if binding.owner_id != target.artifact_id:
+                    continue
+                anchor = anchors_by_id.get(
+                    binding.reference.local_id
+                )
+                if (
+                    anchor is None
+                    or anchor.kind not in _LEXICAL_SCOPE_KINDS
+                ):
+                    continue
+                root_ids.add(anchor.local_id)
+                roots.append(
+                    LineageScopeRootMatch(
+                        source_key=manifest.source_key,
+                        source_fingerprint=(
+                            manifest.source_fingerprint
+                        ),
+                        binding=binding,
+                        anchor=anchor,
+                    )
+                )
+
+            if not root_ids:
+                continue
+
+            if not (
+                manifest.status.value == "fresh"
+                and manifest.anchor_ownership_materialized
+                and manifest.flow_ownership_materialized
+            ):
+                materialization_complete = False
+
+            for flow in source.flows:
+                if flow.owner_local_id not in root_ids:
+                    continue
+                flows.append(
+                    LineageFlowMatch(
+                        source_key=manifest.source_key,
+                        source_fingerprint=(
+                            manifest.source_fingerprint
+                        ),
+                        flow=flow,
+                    )
+                )
+
+            for anchor in source.anchors:
+                if (
+                    anchor.owner_local_id in root_ids
+                    and anchor.kind in _LEXICAL_SCOPE_KINDS
+                ):
+                    nested_scopes.append(
+                        LineageLocalAnchorMatch(
+                            source_key=manifest.source_key,
+                            source_fingerprint=(
+                                manifest.source_fingerprint
+                            ),
+                            anchor=anchor,
+                        )
+                    )
+
+        roots.sort(key=_scope_root_match_key)
+        flows.sort(key=_flow_match_key)
+        nested_scopes.sort(key=_local_anchor_match_key)
+
+        return LexicalScopeFacts(
+            target=target,
+            metadata=metadata,
+            roots=tuple(roots),
+            flows=tuple(flows),
+            nested_scopes=tuple(nested_scopes),
+            materialization_complete=materialization_complete,
+        )
+

 def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
     binding = match.binding
@@ -257,6 +406,43 @@ def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
     )


+def _scope_root_match_key(
+    match: LineageScopeRootMatch,
+) -> tuple:
+    binding = match.binding
+    anchor = match.anchor
+    span = anchor.span
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        binding.owner_id,
+        binding.qualified_name,
+        anchor.local_id,
+        anchor.kind,
+        span.start_line,
+        span.start_column,
+        span.end_line,
+        span.end_column,
+    )
+
+
+def _local_anchor_match_key(
+    match: LineageLocalAnchorMatch,
+) -> tuple:
+    anchor = match.anchor
+    span = anchor.span
+    return (
+        match.source_key,
+        match.source_fingerprint,
+        anchor.local_id,
+        anchor.kind,
+        span.start_line,
+        span.start_column,
+        span.end_line,
+        span.end_column,
+    )
+
+
 def _flow_match_key(match: LineageFlowMatch) -> tuple:
     flow = match.flow
     evidence = flow.evidence
```

### contextor/core/lineage_query/__init__.py

```diff
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
index 8d9e3f5..3bd7cdd 100644
--- a/contextor/core/lineage_query/__init__.py
+++ b/contextor/core/lineage_query/__init__.py
@@ -5,9 +5,12 @@ from contextor.core.lineage_query.backend import (
 )
 from contextor.core.lineage_query.service import (
     DirectLineageFacts,
+    LexicalScopeFacts,
     LineageAnchorMatch,
     LineageFlowMatch,
+    LineageLocalAnchorMatch,
     LineageQueryService,
+    LineageScopeRootMatch,
     LineageSurfaceMatch,
     LineageTargetResolution,
     ResolvedLineageTarget,
@@ -16,10 +19,13 @@ from contextor.core.lineage_query.service import (
 __all__ = [
     "CanonicalLineageBackend",
     "DirectLineageFacts",
+    "LexicalScopeFacts",
     "LineageAnchorMatch",
     "LineageBackendMetadata",
     "LineageFlowMatch",
+    "LineageLocalAnchorMatch",
     "LineageQueryService",
+    "LineageScopeRootMatch",
     "LineageSurfaceMatch",
     "LineageTargetResolution",
     "RepositoryStateLineageBackend",
```

### tests/analysis/test_lineage_query_service.py

```diff
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
index 6561f92..99c7bfd 100644
--- a/tests/analysis/test_lineage_query_service.py
+++ b/tests/analysis/test_lineage_query_service.py
@@ -492,3 +492,502 @@ def test_direct_facts_never_enumerates_repo_wide_source_keys(monkeypatch):

     assert result.incoming
     assert result.outgoing
+def _lexical_scope_service(
+    *,
+    family_state="fresh",
+    anchor_ownership=True,
+    flow_ownership=True,
+):
+    owner = "A17/2"
+    other_owner = "A99/1"
+    source_key = "pkg/target.py"
+    reference_key = "pkg/reference.py"
+    fp = "d" * 64
+    ref_fp = "e" * 64
+    span = SourceSpan(1, 0, 1, 8)
+
+    module_ref = MaterializedOccurrenceRef(
+        source_key,
+        fp,
+        "module",
+    )
+    outer_ref = MaterializedOccurrenceRef(
+        source_key,
+        fp,
+        "outer",
+    )
+    inner_ref = MaterializedOccurrenceRef(
+        source_key,
+        fp,
+        "inner",
+    )
+    comprehension_ref = MaterializedOccurrenceRef(
+        source_key,
+        fp,
+        "comprehension",
+    )
+    local_ref = MaterializedOccurrenceRef(
+        source_key,
+        fp,
+        "local",
+    )
+
+    module_anchor = MaterializedAnchorFact(
+        "module",
+        module_ref,
+        "module",
+        span,
+    )
+    outer_anchor = MaterializedAnchorFact(
+        "outer",
+        outer_ref,
+        "function",
+        span,
+        owner_local_id="module",
+    )
+    inner_anchor = MaterializedAnchorFact(
+        "inner",
+        inner_ref,
+        "function",
+        span,
+        owner_local_id="outer",
+    )
+    comprehension_anchor = MaterializedAnchorFact(
+        "comprehension",
+        comprehension_ref,
+        "comprehension",
+        span,
+        owner_local_id="outer",
+    )
+    local_anchor = MaterializedAnchorFact(
+        "local",
+        local_ref,
+        "binding",
+        span,
+        owner_local_id="outer",
+    )
+    semantic_binding = SemanticAnchorBinding(
+        owner,
+        "pkg.target::outer",
+        outer_ref,
+    )
+
+    source = MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint=fp,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=5,
+            flow_count=5,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=anchor_ownership,
+            flow_ownership_materialized=flow_ownership,
+        ),
+        anchors=tuple(
+            sorted(
+                (
+                    module_anchor,
+                    outer_anchor,
+                    inner_anchor,
+                    comprehension_anchor,
+                    local_anchor,
+                )
+            )
+        ),
+        flows=tuple(
+            sorted(
+                (
+                    MaterializedFlowFact(
+                        "a_outer_bind",
+                        outer_ref,
+                        local_ref,
+                        LineageRelation.BINDS,
+                        span,
+                        ResolutionKind.LEXICAL_EXACT,
+                        LineageConfidence.CONFIRMED,
+                        owner_local_id="outer",
+                    ),
+                    MaterializedFlowFact(
+                        "b_outer_call",
+                        local_ref,
+                        MaterializedOccurrenceRef(
+                            source_key,
+                            fp,
+                            "outer-result",
+                        ),
+                        LineageRelation.CALL_RESULT,
+                        span,
+                        ResolutionKind.CALL_EXACT,
+                        LineageConfidence.CONFIRMED,
+                        owner_local_id="outer",
+                    ),
+                    MaterializedFlowFact(
+                        "c_inner_return",
+                        inner_ref,
+                        MaterializedOccurrenceRef(
+                            source_key,
+                            fp,
+                            "inner-result",
+                        ),
+                        LineageRelation.RETURNS,
+                        span,
+                        ResolutionKind.LEXICAL_EXACT,
+                        LineageConfidence.CONFIRMED,
+                        owner_local_id="inner",
+                    ),
+                    MaterializedFlowFact(
+                        "d_comprehension_assign",
+                        comprehension_ref,
+                        MaterializedOccurrenceRef(
+                            source_key,
+                            fp,
+                            "comprehension-result",
+                        ),
+                        LineageRelation.ASSIGNS,
+                        span,
+                        ResolutionKind.LEXICAL_EXACT,
+                        LineageConfidence.CONFIRMED,
+                        owner_local_id="comprehension",
+                    ),
+                    MaterializedFlowFact(
+                        "e_definition_default",
+                        module_ref,
+                        outer_ref,
+                        LineageRelation.DEFAULTS_TO_PARAMETER,
+                        span,
+                        ResolutionKind.SIGNATURE_EXACT,
+                        LineageConfidence.CONFIRMED,
+                        owner_local_id="module",
+                    ),
+                )
+            )
+        ),
+        semantic_anchors=(semantic_binding,),
+    )
+
+    reference_owner_ref = MaterializedOccurrenceRef(
+        reference_key,
+        ref_fp,
+        "reference-owner",
+    )
+    reference = MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=reference_key,
+            source_fingerprint=ref_fp,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=1,
+            flow_count=1,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
+            flow_ownership_materialized=True,
+        ),
+        anchors=(
+            MaterializedAnchorFact(
+                "reference-owner",
+                reference_owner_ref,
+                "function",
+                span,
+            ),
+        ),
+        flows=(
+            MaterializedFlowFact(
+                "reference-to-target",
+                SemanticEndpoint(owner),
+                reference_owner_ref,
+                LineageRelation.CALL_RESULT,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id="reference-owner",
+            ),
+        ),
+    )
+
+    sources = {
+        source_key: source,
+        reference_key: reference,
+    }
+    owner_source_index, source_owner_index, anchor_complete = (
+        build_lineage_query_indexes(sources)
+    )
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            revision=31,
+            provenance="live",
+            lineage_facts_state=family_state,
+            lineage_facts_semantic_version="1",
+            lineage_facts_by_source=sources,
+            lineage_owner_source_index=owner_source_index,
+            lineage_source_owner_index=source_owner_index,
+            lineage_query_index_state="fresh",
+            lineage_semantic_anchor_bindings_complete=(
+                anchor_complete
+            ),
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts={
+                owner: "pkg.target::outer",
+                other_owner: "pkg.other::thing",
+            },
+        ),
+    )
+    resolved = service.resolve_target(owner)
+    assert resolved.status == "resolved"
+    assert resolved.target is not None
+    return service, backend, resolved.target
+
+
+def test_lexical_scope_facts_return_only_exact_root_owned_flows():
+    service, _, target = _lexical_scope_service()
+
+    result = service.lexical_scope_facts(target)
+
+    assert result.target is target
+    assert result.metadata.revision == 31
+    assert result.scope_available is True
+    assert result.materialization_complete is True
+    assert result.complete is True
+
+    assert len(result.roots) == 1
+    assert result.roots[0].source_key == "pkg/target.py"
+    assert result.roots[0].binding.owner_id == "A17/2"
+    assert result.roots[0].anchor.local_id == "outer"
+    assert result.roots[0].anchor.kind == "function"
+
+    assert tuple(
+        item.flow.local_id
+        for item in result.flows
+    ) == (
+        "a_outer_bind",
+        "b_outer_call",
+    )
+
+    assert tuple(
+        item.anchor.local_id
+        for item in result.nested_scopes
+    ) == (
+        "comprehension",
+        "inner",
+    )
+
+    assert all(
+        item.source_key == "pkg/target.py"
+        for item in (
+            *result.roots,
+            *result.flows,
+            *result.nested_scopes,
+        )
+    )
+
+
+def test_lexical_scope_facts_do_not_cross_into_nested_scopes():
+    service, _, target = _lexical_scope_service()
+
+    result = service.lexical_scope_facts(target)
+
+    returned = {
+        item.flow.local_id
+        for item in result.flows
+    }
+    assert "c_inner_return" not in returned
+    assert "d_comprehension_assign" not in returned
+    assert "e_definition_default" not in returned
+
+
+def test_lexical_scope_facts_ignore_candidate_slice_without_semantic_root():
+    service, backend, target = _lexical_scope_service()
+
+    assert backend.source_keys_for_owner(
+        target.artifact_id
+    ) == (
+        "pkg/reference.py",
+        "pkg/target.py",
+    )
+
+    result = service.lexical_scope_facts(target)
+
+    assert all(
+        item.source_key != "pkg/reference.py"
+        for item in (
+            *result.roots,
+            *result.flows,
+            *result.nested_scopes,
+        )
+    )
+
+
+def test_lexical_scope_facts_are_incomplete_without_flow_ownership():
+    service, _, target = _lexical_scope_service(
+        flow_ownership=False,
+    )
+
+    result = service.lexical_scope_facts(target)
+
+    assert result.scope_available is True
+    assert result.materialization_complete is False
+    assert result.complete is False
+    assert tuple(
+        item.flow.local_id
+        for item in result.flows
+    ) == (
+        "a_outer_bind",
+        "b_outer_call",
+    )
+
+
+def test_lexical_scope_facts_are_incomplete_without_anchor_ownership():
+    service, _, target = _lexical_scope_service(
+        anchor_ownership=False,
+    )
+
+    result = service.lexical_scope_facts(target)
+
+    assert result.scope_available is True
+    assert result.materialization_complete is False
+    assert result.complete is False
+
+
+def test_lexical_scope_facts_expose_stale_family_fail_closed():
+    service, _, target = _lexical_scope_service(
+        family_state="stale",
+    )
+
+    result = service.lexical_scope_facts(target)
+
+    assert result.scope_available is True
+    assert result.metadata.family_state == "stale"
+    assert result.complete is False
+    assert result.flows
+
+
+def test_lexical_scope_facts_never_enumerate_repo_wide_source_keys(
+    monkeypatch,
+):
+    service, backend, target = _lexical_scope_service()
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(
+            AssertionError("repo scan")
+        ),
+    )
+
+    result = service.lexical_scope_facts(target)
+
+    assert result.complete is True
+    assert result.flows
+
+
+def test_lexical_scope_facts_do_not_treat_plain_binding_as_scope():
+    owner = "A17/2"
+    source_key = "pkg/value.py"
+    fingerprint = "f" * 64
+    span = SourceSpan(1, 0, 1, 5)
+    binding_ref = MaterializedOccurrenceRef(
+        source_key,
+        fingerprint,
+        "value-binding",
+    )
+    module_ref = MaterializedOccurrenceRef(
+        source_key,
+        fingerprint,
+        "module",
+    )
+    source = MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint=fingerprint,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=2,
+            flow_count=1,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
+            flow_ownership_materialized=True,
+        ),
+        anchors=tuple(
+            sorted(
+                (
+                    MaterializedAnchorFact(
+                        "module",
+                        module_ref,
+                        "module",
+                        span,
+                    ),
+                    MaterializedAnchorFact(
+                        "value-binding",
+                        binding_ref,
+                        "binding",
+                        span,
+                        owner_local_id="module",
+                    ),
+                )
+            )
+        ),
+        flows=(
+            MaterializedFlowFact(
+                "module-assignment",
+                module_ref,
+                binding_ref,
+                LineageRelation.ASSIGNS,
+                span,
+                ResolutionKind.LEXICAL_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id="module",
+            ),
+        ),
+        semantic_anchors=(
+            SemanticAnchorBinding(
+                owner,
+                "pkg.value::value",
+                binding_ref,
+            ),
+        ),
+    )
+    sources = {source_key: source}
+    owner_source_index, source_owner_index, anchor_complete = (
+        build_lineage_query_indexes(sources)
+    )
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_semantic_version="1",
+            lineage_facts_by_source=sources,
+            lineage_owner_source_index=owner_source_index,
+            lineage_source_owner_index=source_owner_index,
+            lineage_query_index_state="fresh",
+            lineage_semantic_anchor_bindings_complete=(
+                anchor_complete
+            ),
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts={
+                owner: "pkg.value::value",
+            },
+        ),
+    )
+    resolved = service.resolve_target(owner)
+    assert resolved.target is not None
+
+    result = service.lexical_scope_facts(
+        resolved.target
+    )
+
+    assert result.roots == ()
+    assert result.flows == ()
+    assert result.nested_scopes == ()
+    assert result.scope_available is False
+    assert result.complete is False
```
