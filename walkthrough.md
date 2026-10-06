CPA_REEXPORT_LINEAGE_QUERY_AUDIT_FOCUSED_RETRY

STATUS=STEP_PASS
CLASSIFICATION=CANONICAL_REEXPORT_LINEAGE_QUERY_INTEGRATION_CERTIFIED
HEAD=c11a7d2b539d9c5eeb17e0a7ed25a85ac6a3c655
ACCEPTED_BASELINE=CPA_CANONICAL_REEXPORT_LINEAGE_QUERY_INTEGRATION; preserved except the two named audit findings.

AUDIT_FINDING_1_REGRESSION_TEST
The test `test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch` had `sections=SYMBOL_LINEAGE_SECTION_ORDER`, which matched the selected fixture and no longer exercised the mismatch guard. Restored the requested mismatch with `sections=("interface",)`, leaving the test name and `pytest.raises` unchanged.

AUDIT_FINDING_2_DUPLICATED_STAR_SEMANTICS
`build_reexport_lineage_alias_index` independently repeated the canonical export surface fixed-point, visibility filters and deterministic star winner selection. This duplicated the semantics owned by `contextor.core.reference.shared`.

SHARED_STAR_PROVENANCE
Contextor `search_source` found exactly three `_assemble_export_surface_state(` matches: its definition at `shared.py:335`, and calls at `shared.py:438` and `shared.py:448`; all three are within `shared.py`. No direct caller exists outside that file, so the prompt's unexpected-callsite stop condition was not reached. The shared fixed-point now records `star_sources_by_exporter[exporter][local] = source` only when the existing canonical winner installs that namespace entry. `_assemble_module_export_surfaces` and `_assemble_reexport_map` were mechanically updated to consume the new tuple while preserving their existing outputs.

LINEAGE_QUERY_STAR_PROVENANCE
`index.py` now calls `_assemble_module_export_surfaces_with_star_sources` and installs star hops solely from the returned canonical provenance map. The local `working_surfaces`, `star_winners`, visibility filtering, and fixed-point loop were removed. Direct binding alias generation and chain resolution are unchanged.

FIRST_TEST
Command: `tests/mcp/test_lineage_response.py::test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch`
Result: PASS, 1 passed in 0.80s. This was the first pytest invocation in this retry; it passed before production changes.

ACCEPTANCE_GATE
PASS: `tests/test_completeness_freshness_parity_proof.py::test_reexport_lineage_query_retarget_matches_full_oracle`, 1 passed in 4.81s. Its asserted baseline chain is `c::exported -> b::public_value -> a::foo`; after the `b.py` retarget it is `c::exported -> b::public_value -> a::bar`. The node compares expected target/chain with both fresh full and incremental/live results, and compares selected semantic payload after revision/provenance normalization.

REGRESSION_RUN
The named batch passed 25 tests. It covered exact lineage target, not-found and ambiguity; backend lazy alias index and incomplete re-export domain; response chain and named/indexed equivalence; MCP resolved/cycle/external paths; transitive, package initializer, explicit-star and cycle re-export regressions; RAM-only `__all__` update; and package-init addition propagation.

TEST_RESULTS
- `tests/analysis/test_lineage_live_query.py::test_live_symbol_lineage_query_resolves_reexports_without_source_io`: PASS, 1 passed in 0.62s. Multi-hop bindings, two-hop stars, deterministic multiple-star winner, private star exclusion, direct binding precedence, cycle closure, external unresolved, and guarded zero source/AST access all remain passing.
- Focused regression batch: PASS, 25 passed in 12.53s.
- `git diff --check` on the three changed production/test files: PASS, exit 0.
- No full suite, real-repository full analysis, MCP restart, commit, or push was performed.

FILES_CHANGED_IN_RETRY
- tests/mcp/test_lineage_response.py
- contextor/core/reference/shared.py
- contextor/core/lineage_query/index.py

MCP_RESTART_REQUIRED=YES_AFTER_STEP
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=NO, provided post-restart hydration confirms canonical_state=fresh, lineage=fresh, complete reexport fact domain and resync_required=false; persisted canonical schema/facts did not change.

LIVE_WATCHER
Contextor LIVE was at revision 1547 before edits. Desktop watcher recorded revision 1548 for the test, 1549 for `shared.py`, and 1550 for `index.py`; continuity=continuous, resync_required=false. At revision 1550, syntax errors, name collisions and cycles diagnostics were fresh with count 0 and attention_required=false.

RETRY_PATCH_ONLY
diff --git a/contextor/core/lineage_query/index.py b/contextor/core/lineage_query/index.py
index 8218469..8579e2f 100644
--- a/contextor/core/lineage_query/index.py
+++ b/contextor/core/lineage_query/index.py
@@ -9,7 +9,7 @@ from contextor.core.domain.lineage_facts import (
 )
 from contextor.core.reference.shared import (
     _canonicalize_package_reference_target,
-    _assemble_module_export_surfaces,
+    _assemble_module_export_surfaces_with_star_sources,
 )
 
 
@@ -135,7 +135,10 @@ def build_reexport_lineage_alias_index(
         known_modules.add(exporter)
         known_modules.update(star_sources)
 
-    module_export_surfaces = _assemble_module_export_surfaces(
+    (
+        module_export_surfaces,
+        star_sources_by_exporter,
+    ) = _assemble_module_export_surfaces_with_star_sources(
         dict(reexport_facts_by_module)
     )
     alias_index: dict[str, ReexportLineageHop] = {}
@@ -165,65 +168,12 @@ def build_reexport_lineage_alias_index(
                 )
             )
 
-    # Reproduce the existing export-surface assembler's deterministic
-    # fixed-point ordering to retain the first star source that installs a
-    # visible local. The final visibility set still comes from its canonical
-    # helper above.
-    working_surfaces: dict[str, dict[str, str]] = {}
-    direct_bindings: dict[str, Mapping[str, object]] = {}
-    star_imports: list[tuple[str, str, set[str] | None]] = []
-    for exporter, facts in facts_by_exporter.items():
-        bindings = facts["bindings"]
-        explicit_all = facts.get("explicit_all")
-        if explicit_all is not None and not isinstance(explicit_all, (list, tuple)):
-            raise ValueError("canonical re-export explicit_all is invalid.")
-        allowed = None if explicit_all is None else set(explicit_all)
-        assert isinstance(bindings, Mapping)
-        direct_bindings[exporter] = bindings
-        visible: dict[str, str] = {}
-        for local, target in bindings.items():
-            if not isinstance(local, str) or not isinstance(target, str):
-                raise ValueError("canonical re-export binding is invalid.")
-            if allowed is not None and local not in allowed:
-                continue
-            if allowed is None and local.startswith("_"):
-                continue
-            visible[local] = target
-        working_surfaces[exporter] = visible
-        for source in facts["star_sources"]:
-            star_imports.append((exporter, source, allowed))
-
-    star_winners: dict[tuple[str, str], str] = {}
-    changed = True
-    while changed:
-        changed = False
-        for exporter, source, allowed in star_imports:
-            for local, target in tuple(working_surfaces.get(source, {}).items()):
-                if allowed is not None and local not in allowed:
-                    continue
-                if allowed is None and local.startswith("_"):
-                    continue
-                # A named binding owns its namespace slot even when it is a
-                # self-binding and therefore did not create a binding edge.
-                if local in direct_bindings.get(exporter, {}):
-                    continue
-                winner_key = (exporter, local)
-                if winner_key in star_winners:
-                    continue
-                working_surfaces.setdefault(exporter, {})[local] = target
-                star_winners[winner_key] = source
-                changed = True
-
     for exporter, visible_bindings in module_export_surfaces.items():
-        facts = facts_by_exporter.get(exporter)
-        if facts is None:
-            continue
-        bindings = facts["bindings"]
-        assert isinstance(bindings, Mapping)
         for local in visible_bindings:
-            if local in bindings:
-                continue
-            source = star_winners.get((exporter, local))
+            source = star_sources_by_exporter.get(
+                exporter,
+                {},
+            ).get(local)
             if source is None:
                 continue
             install(
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index ca185c5..2f578ad 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -334,14 +334,23 @@ def _extract_reexport_facts(
 
 def _assemble_export_surface_state(
     reexport_facts_by_module: dict[str, dict[str, Any]],
-) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
+) -> tuple[
+    dict[str, dict[str, str]],
+    dict[str, str],
+    dict[str, dict[str, str]],
+]:
     """
-    Assemble visible module exports and their raw re-export identities.
+    Assemble visible module exports, raw re-export identities, and
+    immediate star-import provenance.
 
     Performs no source or filesystem I/O.
     """
     raw: dict[str, str] = {}
     module_exports: dict[str, dict[str, str]] = {}
+    star_sources_by_exporter: dict[
+        str,
+        dict[str, str],
+    ] = {}
     star_imports: list[
         tuple[str, str, set[str] | None]
     ] = []
@@ -426,16 +435,51 @@ def _assemble_export_surface_state(
                         exporter,
                         {},
                     )[local] = target
+                    star_sources_by_exporter.setdefault(
+                        exporter,
+                        {},
+                    )[local] = source
                     changed = True
 
-    return module_exports, raw
+    return (
+        module_exports,
+        raw,
+        star_sources_by_exporter,
+    )
+
+
+def _assemble_module_export_surfaces_with_star_sources(
+    reexport_facts_by_module: dict[str, dict[str, Any]],
+) -> tuple[
+    dict[str, dict[str, str]],
+    dict[str, dict[str, str]],
+]:
+    """
+    Assemble visible exports together with the immediate source module
+    that installed each star-imported namespace entry.
+    """
+    (
+        module_exports,
+        _raw,
+        star_sources_by_exporter,
+    ) = _assemble_export_surface_state(
+        reexport_facts_by_module
+    )
+
+    return (
+        module_exports,
+        star_sources_by_exporter,
+    )
 
 
 def _assemble_module_export_surfaces(
     reexport_facts_by_module: dict[str, dict[str, Any]],
 ) -> dict[str, dict[str, str]]:
     """Assemble visible local exports and their source target identities."""
-    module_exports, _raw = _assemble_export_surface_state(
+    (
+        module_exports,
+        _star_sources_by_exporter,
+    ) = _assemble_module_export_surfaces_with_star_sources(
         reexport_facts_by_module
     )
     return module_exports
@@ -445,7 +489,11 @@ def _assemble_reexport_map(
     reexport_facts_by_module: dict[str, dict[str, Any]],
 ) -> dict[str, str]:
     """Assemble cycle-safe transitive re-export identities from source facts."""
-    _module_exports, raw = _assemble_export_surface_state(
+    (
+        _module_exports,
+        raw,
+        _star_sources_by_exporter,
+    ) = _assemble_export_surface_state(
         reexport_facts_by_module
     )
 
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index ddcb207..2f354e0 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -609,7 +609,7 @@ def test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch():
         render_symbol_lineage_response(
             selected,
             mode="fetch",
-            sections=SYMBOL_LINEAGE_SECTION_ORDER,
+            sections=("interface",),
             representation="indexed",
         )
 

