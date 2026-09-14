# P0 L3A1 — lineage reuse gate hardening

## STATUS

SUCCESS. Added only the two requested hardening tests; production code was not changed in this step.

## CONTEXTOR_VERIFICATION

Contextor at fresh LIVE revision 1046 resolves `materialized_lineage_source_matches_resolution`. Its direct callees are the existing `_anchor_symbol_path` and `_seed_defining_interface_descriptors`. Existing `reresolve_materialized_lineage_source_facts` also uses `_seed_defining_interface_descriptors`. This confirms descriptor and semantic-anchor invalidation travel through existing canonical resolution machinery, not a parallel lifecycle.

## VALIDATION

- `.\.venv\Scripts\python.exe -m pytest -q tests\analysis\test_lineage_materialization.py` — **33 passed in 3.48s**.
- Production code unchanged by L3A1.
- `git diff --check` passed before embedding the required raw diffs; the raw diff block may retain context blank-space lines.

## FILES_CHANGED

- `tests/analysis/test_lineage_materialization.py` (L3A1 tests).
- No production-file diff remains in this working tree; the pre-existing L3A predicate was already canonical/tracked before this report diff was captured.

## FULL_DIFFS

```diff
warning: in the working copy of 'tests/analysis/test_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index 1553677..d8832c4 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -910,3 +910,149 @@ def test_materialized_lineage_source_rejects_semantic_endpoint_without_origin():
         legacy_like,
         context,
     ) is False
+
+def test_materialized_lineage_source_rejects_changed_interface_descriptor():
+    span = SourceSpan(1, 0, 1, 1)
+    owner_id = "A9/1"
+    parameter_id = "occ:v1:parameter_poskw:0:i:0:n:value"
+    parameter_slot = build_parameter_value_slot(
+        owner_id,
+        ParameterKind.POSITIONAL_OR_KEYWORD,
+        ordinal=0,
+    )
+    keyword_slot = build_keyword_binding_slot(
+        owner_id,
+        ParameterKind.POSITIONAL_OR_KEYWORD,
+        name="value",
+    )
+    descriptor_v1 = SemanticInterfaceDescriptor(
+        owner_id,
+        tuple(
+            sorted(
+                (
+                    parameter_slot,
+                    build_return_slot(owner_id),
+                )
+            )
+        ),
+        "digest-v1",
+    )
+    descriptor_v2 = SemanticInterfaceDescriptor(
+        owner_id,
+        tuple(
+            sorted(
+                (
+                    parameter_slot,
+                    keyword_slot,
+                    build_return_slot(owner_id),
+                )
+            )
+        ),
+        "digest-v2",
+    )
+    facts = _facts(
+        anchors=(
+            ExtractedAnchorFact(
+                "owner",
+                "binding",
+                span,
+            ),
+        ),
+        flows=(
+            ExtractedFlowFact(
+                "flow",
+                ExtractedOccurrenceRef("owner"),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.PARAMETER,
+                    "pkg.mod",
+                    "run",
+                    parameter_id,
+                ),
+                LineageRelation.ARGUMENT_TO_PARAMETER,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id="owner",
+            ),
+        ),
+    )
+    original_resolution = _context(
+        artifacts={"pkg.mod::run": owner_id},
+        descriptors={owner_id: descriptor_v1},
+    )
+    materialized = materialize_lineage_source_facts(
+        facts,
+        original_resolution,
+    )
+    assert materialized.manifest.flow_ownership_materialized is True
+    assert materialized.flows[0].target == SemanticEndpoint(
+        owner_id,
+        parameter_slot,
+    )
+    assert materialized.interface_descriptors == (descriptor_v1,)
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        original_resolution,
+    ) is True
+    changed_resolution = _context(
+        artifacts={"pkg.mod::run": owner_id},
+        descriptors={owner_id: descriptor_v2},
+    )
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        changed_resolution,
+    ) is False
+
+
+def test_materialized_lineage_source_rejects_changed_semantic_anchor_binding():
+    span = SourceSpan(1, 0, 1, 1)
+    module_anchor = "occ:v1:module:root:i:0:n:pkg"
+    class_anchor = "occ:v1:class:0:i:0:n:Thing"
+    facts = _facts(
+        anchors=tuple(
+            sorted(
+                (
+                    ExtractedAnchorFact(
+                        module_anchor,
+                        "module",
+                        span,
+                    ),
+                    ExtractedAnchorFact(
+                        class_anchor,
+                        "class",
+                        span,
+                        module_anchor,
+                    ),
+                )
+            )
+        ),
+    )
+    original_resolution = _context(
+        artifacts={"pkg.mod::Thing": "A1/1"},
+    )
+    materialized = materialize_lineage_source_facts(
+        facts,
+        original_resolution,
+    )
+    assert materialized.semantic_anchors == (
+        SemanticAnchorBinding(
+            "A1/1",
+            "pkg.mod::Thing",
+            MaterializedOccurrenceRef(
+                "pkg/mod.py",
+                "sha256:test",
+                class_anchor,
+            ),
+        ),
+    )
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        original_resolution,
+    ) is True
+    changed_resolution = _context(
+        artifacts={"pkg.mod::Thing": "A1/2"},
+    )
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        changed_resolution,
+    ) is False
```
