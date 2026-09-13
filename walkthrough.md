# F2L D1G Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/domain/lineage_facts.py`
- `contextor/core/analysis/lineage_materialization.py`
- `contextor/core/live_state/store.py`
- `tests/analysis/test_lineage_materialization.py`
- `tests/test_lineage_state_lifecycle.py`

`walkthrough.md` is deliberately excluded from ACTUAL_DIFF.

## ANCHOR_OWNERSHIP_CONTRACT

`MaterializedAnchorFact.owner_local_id` is copied only from `ExtractedAnchorFact.owner_local_id` during materialization. A materialized slice validates that an owner exists in the same slice and that ownership has no cycle. No AST path, source span, name, or local-ID-prefix heuristic reconstructs ownership.

## LEGACY_FAIL_CLOSED

The semantic version is unchanged. Hydration supplies `owner_local_id=None` and `anchor_ownership_materialized=False` when legacy snapshots lack the fields. Ownership is therefore explicitly unavailable rather than inferred. Query, service, backend, and index layers were not changed.

## TESTS_RUN

- `./.venv/Scripts/python.exe -m py_compile contextor/core/domain/lineage_facts.py contextor/core/analysis/lineage_materialization.py contextor/core/live_state/store.py`: PASS.
- `./.venv/Scripts/python.exe -m pytest -q tests/analysis/test_lineage_materialization.py tests/test_lineage_state_lifecycle.py`: PASS — 52 passed in 5.45s.
- `git diff --check` for all five task files: PASS (only CRLF conversion warnings).

## ACTUAL_DIFF

### contextor/core/domain/lineage_facts.py

```diff
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 68e67cd..f736fe4 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -336,11 +336,16 @@ class MaterializedAnchorFact:
     reference: MaterializedOccurrenceRef
     kind: str
     span: SourceSpan
+    owner_local_id: str | None = None

     def __post_init__(self) -> None:
         _require_token(self.local_id, "local_id")
         _require_token(self.kind, "kind")
         _require_materialized_anchor_reference(self.reference)
+        if self.owner_local_id is not None:
+            _require_token(self.owner_local_id, "owner_local_id")
+            if self.owner_local_id == self.local_id:
+                raise ValueError("Materialized anchor cannot own itself.")


 @dataclass(frozen=True, order=True)
@@ -424,6 +429,7 @@ class SourceLineageManifest:
     surface_count: int
     resource_limit_reason: str | None = None
     semantic_anchor_bindings_materialized: bool = False
+    anchor_ownership_materialized: bool = False

     def __post_init__(self) -> None:
         _require_token(self.source_key, "source_key")
@@ -435,6 +441,8 @@ class SourceLineageManifest:
             raise TypeError(
                 "semantic_anchor_bindings_materialized must be boolean."
             )
+        if not isinstance(self.anchor_ownership_materialized, bool):
+            raise TypeError("anchor_ownership_materialized must be boolean.")
         _validate_source_status(self.status, self.resource_limit_reason)


@@ -491,8 +499,30 @@ class MaterializedLineageSourceFacts:
             )
             if expected != actual:
                 raise ValueError("Fresh lineage manifest counts must match facts.")
+        anchor_ids = {anchor.local_id for anchor in self.anchors}
+        anchor_owners: dict[str, str | None] = {}
         for anchor in self.anchors:
             _require_slice_occurrence(anchor.reference, self.manifest)
+            if (
+                anchor.owner_local_id is not None
+                and anchor.owner_local_id not in anchor_ids
+            ):
+                raise ValueError(
+                    "Materialized anchor owner must reference an anchor in its slice."
+                )
+            anchor_owners[anchor.local_id] = anchor.owner_local_id
+
+        for local_id in anchor_owners:
+            seen: set[str] = set()
+            current: str | None = local_id
+            while current is not None:
+                if current in seen:
+                    raise ValueError(
+                        "Materialized anchor ownership contains a cycle."
+                    )
+                seen.add(current)
+                current = anchor_owners.get(current)
+
         for flow in self.flows:
             _require_slice_occurrence(flow.source, self.manifest)
             _require_slice_occurrence(flow.target, self.manifest)
```

### contextor/core/analysis/lineage_materialization.py

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index b506350..789b901 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -129,7 +129,11 @@ def materialize_lineage_source_facts(
     anchors = tuple(
         sorted(
             MaterializedAnchorFact(
-                anchor.local_id, occurrence(anchor.local_id), anchor.kind, anchor.span
+                local_id=anchor.local_id,
+                reference=occurrence(anchor.local_id),
+                kind=anchor.kind,
+                span=anchor.span,
+                owner_local_id=anchor.owner_local_id,
             )
             for anchor in extracted.anchors
         )
@@ -196,6 +200,7 @@ def materialize_lineage_source_facts(
         len(surfaces),
         extracted.resource_limit_reason,
         semantic_anchor_bindings_materialized=True,
+        anchor_ownership_materialized=True,
     )
     return MaterializedLineageSourceFacts(
         manifest,
```

### contextor/core/live_state/store.py

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 28fed1f..5915f47 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -150,6 +150,13 @@ def _revalidate_lineage_manifest(manifest: Any) -> SourceLineageManifest:
                 False,
             )
         ),
+        anchor_ownership_materialized=bool(
+            getattr(
+                manifest,
+                "anchor_ownership_materialized",
+                False,
+            )
+        ),
     )
     if rebuilt.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION:
         raise pickle.UnpicklingError(
@@ -165,6 +172,7 @@ def _revalidate_lineage_anchor(anchor: Any) -> MaterializedAnchorFact:
         anchor,
         reference=_revalidate_lineage_endpoint(anchor.reference),
         span=_revalidate_lineage_span(anchor.span),
+        owner_local_id=getattr(anchor, "owner_local_id", None),
     )
```

### tests/analysis/test_lineage_materialization.py

```diff
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index 4dbcebc..5006541 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -18,7 +18,11 @@ from contextor.core.domain.lineage_facts import (
     ExtractedSymbolicRef,
     ExtractedSurfaceFact,
     LineageConfidence,
+    LineageFamilyStatus,
     LineageRelation,
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    MaterializedAnchorFact,
+    MaterializedLineageSourceFacts,
     MaterializedOccurrenceRef,
     MaterializedSymbolicRef,
     ParameterKind,
@@ -29,6 +33,7 @@ from contextor.core.domain.lineage_facts import (
     SemanticEndpointOrigin,
     SemanticEndpointRole,
     SemanticInterfaceDescriptor,
+    SourceLineageManifest,
     SourceSpan,
     SurfaceDeclarationEvidence,
     SurfaceKind,
@@ -73,6 +78,84 @@ def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
     assert first.flows[0].resolution_kind is ResolutionKind.LEXICAL_EXACT


+def test_materialized_slice_rejects_missing_or_cyclic_anchor_owner():
+    span = SourceSpan(1, 0, 1, 1)
+    source_key = "pkg.py"
+    fingerprint = "f" * 64
+
+    parent_ref = MaterializedOccurrenceRef(
+        source_key,
+        fingerprint,
+        "parent",
+    )
+    child_ref = MaterializedOccurrenceRef(
+        source_key,
+        fingerprint,
+        "child",
+    )
+    manifest = SourceLineageManifest(
+        source_key,
+        fingerprint,
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus.FRESH,
+        1,
+        0,
+        0,
+        semantic_anchor_bindings_materialized=True,
+        anchor_ownership_materialized=True,
+    )
+
+    with pytest.raises(ValueError, match="owner must reference"):
+        MaterializedLineageSourceFacts(
+            manifest=manifest,
+            anchors=(
+                MaterializedAnchorFact(
+                    "child",
+                    child_ref,
+                    "binding",
+                    span,
+                    owner_local_id="missing",
+                ),
+            ),
+        )
+
+    cycle_manifest = SourceLineageManifest(
+        source_key,
+        fingerprint,
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus.FRESH,
+        2,
+        0,
+        0,
+        semantic_anchor_bindings_materialized=True,
+        anchor_ownership_materialized=True,
+    )
+    with pytest.raises(ValueError, match="ownership contains a cycle"):
+        MaterializedLineageSourceFacts(
+            manifest=cycle_manifest,
+            anchors=tuple(
+                sorted(
+                    (
+                        MaterializedAnchorFact(
+                            "parent",
+                            parent_ref,
+                            "function",
+                            span,
+                            owner_local_id="child",
+                        ),
+                        MaterializedAnchorFact(
+                            "child",
+                            child_ref,
+                            "binding",
+                            span,
+                            owner_local_id="parent",
+                        ),
+                    )
+                )
+            ),
+        )
+
+
 def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
     span = SourceSpan(1, 0, 1, 1)
     module_anchor = "occ:v1:module:root:i:0:n:pkg"
@@ -122,6 +205,14 @@ def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
             MaterializedOccurrenceRef("pkg/mod.py", "sha256:test", method_anchor),
         ),
     )
+    anchors_by_id = {
+        anchor.local_id: anchor
+        for anchor in initial.anchors
+    }
+    assert initial.manifest.anchor_ownership_materialized is True
+    assert anchors_by_id[module_anchor].owner_local_id is None
+    assert anchors_by_id[class_anchor].owner_local_id == module_anchor
+    assert anchors_by_id[method_anchor].owner_local_id == class_anchor

     reresolved = reresolve_materialized_lineage_source_facts(
         initial,
@@ -136,6 +227,8 @@ def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
         "A1/1",
         "A2/2",
     )
+    assert reresolved.anchors == initial.anchors
+    assert reresolved.manifest.anchor_ownership_materialized is True

     removed = reresolve_materialized_lineage_source_facts(
         reresolved,
```

### tests/test_lineage_state_lifecycle.py

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index bdc4968..14fd07e 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -71,6 +71,7 @@ def _lineage_slice() -> MaterializedLineageSourceFacts:
             1,
             1,
             semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
         ),
         anchors=(
             MaterializedAnchorFact(
@@ -226,6 +227,88 @@ def test_snapshot_legacy_semantic_anchor_fields_fail_closed(tmp_path):
     assert loaded.lineage_query_index_state == "fresh"


+def test_snapshot_preserves_materialized_anchor_ownership(tmp_path):
+    source_key = "owned.py"
+    fingerprint = "o" * 64
+    span = SourceSpan(1, 0, 2, 1)
+    parent = MaterializedAnchorFact(
+        "owner",
+        MaterializedOccurrenceRef(source_key, fingerprint, "owner"),
+        "function",
+        span,
+    )
+    child = MaterializedAnchorFact(
+        "child",
+        MaterializedOccurrenceRef(source_key, fingerprint, "child"),
+        "binding",
+        span,
+        owner_local_id="owner",
+    )
+    source_slice = MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key,
+            fingerprint,
+            LINEAGE_FACTS_SEMANTIC_VERSION,
+            LineageFamilyStatus.FRESH,
+            2,
+            0,
+            0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
+        ),
+        anchors=tuple(sorted((parent, child))),
+    )
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={source_key: source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    save_snapshot(state, tmp_path, "anchor-ownership")
+    loaded, _ = load_snapshot(
+        tmp_path,
+        expected_state_id="anchor-ownership",
+    )
+
+    loaded_slice = loaded.lineage_facts_by_source[source_key]
+    loaded_by_id = {
+        anchor.local_id: anchor
+        for anchor in loaded_slice.anchors
+    }
+    assert loaded_slice.manifest.anchor_ownership_materialized is True
+    assert loaded_by_id["child"].owner_local_id == "owner"
+
+
+def test_snapshot_legacy_anchor_ownership_fails_closed(tmp_path):
+    source_slice = _lineage_slice()
+    object.__delattr__(
+        source_slice.manifest,
+        "anchor_ownership_materialized",
+    )
+    for anchor in source_slice.anchors:
+        if hasattr(anchor, "owner_local_id"):
+            object.__delattr__(anchor, "owner_local_id")
+
+    state = RepositoryAnalysisState(
+        lineage_facts_by_source={"pkg.py": source_slice},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    save_snapshot(state, tmp_path, "legacy-anchor-ownership")
+    loaded, _ = load_snapshot(
+        tmp_path,
+        expected_state_id="legacy-anchor-ownership",
+    )
+
+    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]
+    assert loaded_slice.manifest.anchor_ownership_materialized is False
+    assert all(
+        anchor.owner_local_id is None
+        for anchor in loaded_slice.anchors
+    )
+
+
 @pytest.mark.parametrize(
     ("family_state", "version", "with_slice"),
     [
```
