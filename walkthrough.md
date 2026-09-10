# Contextor Stage 1E.1 certification cleanup — minimal facade diff + LIVE retry

STATUS=SEMANTICS_FROZEN_AND_VERIFIED

`lineage_extraction.py` was restored from `c1643dc744156ed960669a795ca149017e2c91ad` and re-patched without a formatter or whole-file rewrite. Its diff relative to BASE contains exactly one import extension and `_visit_Subscript`; no unrelated whitespace or EOL hunk remains. Surface state/helper behavior and the five existing subscript regressions are unchanged.

## Exact minimal facade diff proof

The facade raw diff below is 6 additions / 1 deletion: the required import replacement plus the four-statement `_visit_Subscript` method. No additional facade hunks exist.

## Tests and oracle

* `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q` — 194 passed in 2.78s.
* `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q` — 3 passed in 0.60s.
* `.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q` — 208 passed in 5.49s.
* `git diff --check` — passed after this report replacement.
* The unchanged equivalence suite passed, proving legacy anchors and flows remain byte-for-byte equivalent when surfaces are stripped. No hash regeneration occurred.

## LIVE / Contextor certification

ACTIVE pool was inspected through Contextor MCP documentation and included `get_live_events` and `get_file_edit_context`; no DEFERRED-pool discovery tool was injected in this session. Before cleanup, `get_live_events(after_revision=600)` returned revision 603 with Desktop watcher revisions 601–603, `continuity=continuous`, `resync_required=false`, fresh syntax/collision/cycle diagnostics, and a fresh watcher update for `lineage_extraction.py` at revision 602. Both changed production modules were then LIVE-visible at revision 603 with `syntax_diagnostics=checked_and_none`, `availability=fresh`, and `materialized=true`.

After the minimal cleanup patch, two retries (`after_revision=600` and, after 30 seconds, `after_revision=603`) returned `transient_connection_failure: Existing LIVE owner is temporarily unreachable`. Therefore a newer matching Desktop watcher revision for the cleanup patch cannot be established. `update_file` was not called.

LIVE_CERTIFICATION=BLOCKED_MANUAL_RESTART_REQUIRED

User-side Desktop LIVE/MCP owner restart or reconnect is required before final post-cleanup watcher certification. This is a repeated reachability failure across consecutive attempts. No production semantics were changed beyond the frozen Stage 1E.1 direct-subscript feature.

## Structural certification

Textual verification confirms one `LineageExtractionState()` construction, the sole facade dynamic dispatch, the explicit `_visit_Subscript` hook, and no `ast.walk`/`NodeVisitor` occurrences. `observe_all_subscript_mutation` remains helper-only and has no helper-to-facade back-edge. The last reachable LIVE state reported zero syntax errors, zero collisions, and zero cycles, all fresh; a new graph query is blocked solely by the unreachable LIVE owner.

FILES_CHANGED:

* `contextor/core/analysis/lineage_extraction.py`
* `contextor/core/analysis/lineage_extraction_surfaces.py`
* `tests/analysis/test_lineage_extraction.py`

## COMPLETE raw unified FULL_DIFF relative to BASE

~~~diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index d9215e7..6fdd7a1 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -57,7 +57,7 @@ from contextor.core.analysis.lineage_extraction_visitors import (
     visit_yield,
 )
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
-from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces
+from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces, observe_all_subscript_mutation
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
@@ -197,6 +197,11 @@ class _AnchorExtractor:
     def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
         visit_name(self.state, self.paths, node, owner)
 
+    def _visit_Subscript(self, node: ast.Subscript, owner: str | None, walrus_owner: str | None) -> None:
+        observe_all_subscript_mutation(self.state, node, owner)
+        self._visit(node.value, owner, walrus_owner)
+        self._visit(node.slice, owner, walrus_owner)
+
     def _runtime_bind_target(
         self,
         target: ast.AST,
diff --git a/contextor/core/analysis/lineage_extraction_surfaces.py b/contextor/core/analysis/lineage_extraction_surfaces.py
index a5d71d4..32fbb20 100644
--- a/contextor/core/analysis/lineage_extraction_surfaces.py
+++ b/contextor/core/analysis/lineage_extraction_surfaces.py
@@ -49,6 +49,21 @@ def observe_all_mutation(state: LineageExtractionState, node: ast.Call) -> None:
         state.invalidate_all()


+def observe_all_subscript_mutation(
+    state: LineageExtractionState,
+    node: ast.Subscript,
+    owner: str | None,
+) -> None:
+    if (
+        owner is not None
+        and state._owner_kind.get(owner) == "module"
+        and isinstance(node.ctx, (ast.Store, ast.Del))
+        and isinstance(node.value, ast.Name)
+        and node.value.id == "__all__"
+    ):
+        state.invalidate_all()
+
+
 def record_direct_public_candidates(state: LineageExtractionState, node: ast.AST, owner: str) -> None:
     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
         names = (node.name,)
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index d46e3dc..ff346a8 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -2162,3 +2162,21 @@ def test_stage_1e1_surface_id_escapes_non_identifier_literal_name_deterministica
     surface = first.surfaces[0]
     assert surface.declared_name == "a:b/c"
     assert ":n:a%3Ab%2Fc" in surface.local_id
+
+
+@pytest.mark.parametrize("source", [
+    "__all__ = ['a']\\n__all__[0] = 'x'\\ndef a(): pass\\n",
+    "__all__ = ['a']\\n__all__[:] = ['x']\\ndef a(): pass\\n",
+    "__all__ = ['a']\\n__all__[0] += 'x'\\ndef a(): pass\\n",
+    "__all__ = ['a']\\ndel __all__[0]\\ndef a(): pass\\n",
+])
+def test_stage_1e1_direct_all_subscript_mutation_suppresses_exact_surfaces(source):
+    assert _stage_1c_facts(source).surfaces == ()
+
+
+def test_stage_1e1_reading_all_subscript_preserves_exact_literal_authority():
+    facts = _stage_1c_facts("__all__ = ['a']\\nx = __all__[0]\\ndef a(): pass\\n")
+    surface = facts.surfaces[0]
+    assert surface.declared_name == "a"
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.confidence is LineageConfidence.CONFIRMED
~~~
