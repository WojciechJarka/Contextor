# CPA_STALE_LEGACY_CONSUMER_TARGET_FIX

STATUS=PASS
HEAD_BEFORE=31904374e530d84c5a672609e1245d7507784a44
HEAD_AFTER=31904374e530d84c5a672609e1245d7507784a44
WORKTREE_STATE_BEFORE=Only walkthrough.md was already modified; both requested source/test files were clean.
WORKTREE_STATE_AFTER=Modified: contextor/core/analysis/state_manager.py, tests/test_completeness_freshness_parity_proof.py, walkthrough.md. No other files changed.
LIVE_REVISION_BEFORE=1594
LIVE_REVISION_AFTER=1598

IMPLEMENTATION_RESULT=canonical_artifact_consumption_targets now treats non-empty own_symbols as authoritative, symbols dict as authoritative even when empty, structurally available empty own_symbols as an empty domain, and consumers as fallback only for true legacy payloads. prepare_source_update and consumers copying were not changed.
ROOT_CAUSE_CONFIRMED=YES. The previous implementation fell through to consumers when modern target-domain fields existed but represented an empty symbol domain, resurrecting stale targets.

FILES_CHANGED
- contextor/core/analysis/state_manager.py
- tests/test_completeness_freshness_parity_proof.py

FULL_DIFFS
```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index e2ed0fc..4e30e53 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -592,8 +592,14 @@ def canonical_artifact_consumption_targets(
     artifacts: dict[str, Any] | None,
 ) -> set[str]:
     """
-    Computes the exact set of expected canonical target keys (f"{module_path}::{symbol}")
-    from defined symbols in artifacts fact dictionaries.
+    Computes the exact set of expected canonical target keys
+    (f"{module_path}::{symbol}") from defined symbols in artifact
+    fact dictionaries.
+
+    Modern symbol-domain fields are authoritative even when empty.
+    The consumers mapping is used only as a compatibility fallback
+    for legacy artifact payloads that do not expose a modern symbol
+    domain.
     """
     targets: set[str] = set()
     if not isinstance(artifacts, dict):
@@ -603,29 +609,33 @@ def canonical_artifact_consumption_targets(
         if not isinstance(module_path, str) or not isinstance(module_data, dict):
             continue
 
-        # 1. Check own_symbols if available
+        # 1. Non-empty own_symbols is the strongest modern target-domain source.
         own_symbols = module_data.get("own_symbols")
-        if isinstance(own_symbols, (list, set, tuple)) and own_symbols:
+        own_symbols_available = isinstance(own_symbols, (list, set, tuple))
+        if own_symbols_available and own_symbols:
             for sym in own_symbols:
                 if isinstance(sym, str) and sym:
                     targets.add(f"{module_path}::{sym}")
             continue
 
-        # 2. Check symbols dict if available
+        # 2. A symbols dict is authoritative even when it defines zero targets.
+        #    Empty modern symbol facts must not fall through to stale consumers.
         symbols = module_data.get("symbols")
         if isinstance(symbols, dict):
-            has_syms = False
             for cat in ("classes", "functions", "methods", "globals"):
                 cat_syms = symbols.get(cat, [])
                 if isinstance(cat_syms, (list, set, tuple)):
                     for sym in cat_syms:
                         if isinstance(sym, str) and sym:
                             targets.add(f"{module_path}::{sym}")
-                            has_syms = True
-            if has_syms:
-                continue
+            continue
+
+        # 3. Structurally available empty own_symbols also authoritatively means
+        #    that this module currently defines no canonical artifact targets.
+        if own_symbols_available:
+            continue
 
-        # 3. Fallback for legacy format where only consumers dict is present
+        # 4. Compatibility fallback for true legacy consumers-only payloads.
         consumers_by_symbol = module_data.get("consumers", {})
         if isinstance(consumers_by_symbol, dict):
             for symbol, entry in consumers_by_symbol.items():
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 5cb0e90..f8e2bac 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -14,7 +14,12 @@ import pytest
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine, IncrementalUpdateResult
 from contextor.core.analysis.incremental.preparation import prepare_source_update
 from contextor.core.analysis.refresh_planner import RefreshPlanner, _find_dependent_consumers
-from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
+from contextor.core.analysis.state_manager import (
+    FileDelta,
+    FileStateManager,
+    RepositoryAnalysisState,
+    canonical_artifact_consumption_targets,
+)
 from contextor.core.analysis.incremental.plan_executor import _resolve_canonical_target_key
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.domain.module import Module
@@ -2504,3 +2509,103 @@ def test_named_package_local_import_update_matches_full_oracle(
     ) == {"api_imports", "direct_calls"}
     oracle = _build_full_static_state(tmp_path)
     _assert_full_parity(engine.state, oracle)
+
+
+def test_canonical_target_domain_does_not_resurrect_stale_consumers_from_modern_empty_symbols():
+    artifacts = {
+        "api": {
+            "symbols": {
+                "classes": [],
+                "functions": [],
+                "methods": [],
+                "globals": [],
+            },
+            "own_symbols": set(),
+            "consumers": {
+                "VALUE": {
+                    "consumers": [],
+                    "channels": {},
+                }
+            },
+        }
+    }
+
+    assert canonical_artifact_consumption_targets(artifacts) == set()
+
+
+def test_canonical_target_domain_preserves_consumers_only_legacy_fallback():
+    artifacts = {
+        "legacy": {
+            "consumers": {
+                "foo": {
+                    "consumers": [],
+                    "channels": {},
+                }
+            }
+        }
+    }
+
+    assert canonical_artifact_consumption_targets(artifacts) == {
+        "legacy::foo"
+    }
+
+
+def test_content_change_removes_obsolete_consumption_target_and_matches_full_oracle(tmp_path):
+    f_provider = tmp_path / "a.py"
+    f_provider.write_text(
+        "def foo():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+
+    f_api = tmp_path / "api.py"
+    f_api.write_text(
+        "VALUE = 1\n",
+        encoding="utf-8",
+    )
+
+    f_consumer = tmp_path / "consumer.py"
+    f_consumer.write_text(
+        "from api import public\n"
+        "public()\n",
+        encoding="utf-8",
+    )
+
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+
+    engine.update_file(str(f_provider))
+    engine.update_file(str(f_api))
+    engine.update_file(str(f_consumer))
+
+    assert "api::VALUE" in engine.state.artifact_consumption
+
+    f_api.write_text(
+        "from a import foo as public\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(str(f_api))
+    oracle = _build_full_static_state(tmp_path)
+
+    assert result.artifact_consumption_state == "fresh"
+
+    assert "api::VALUE" not in oracle.artifact_consumption
+    assert "api::VALUE" not in engine.state.artifact_consumption
+
+    assert "a::foo" in oracle.artifact_consumption
+    assert "a::foo" in engine.state.artifact_consumption
+
+    assert (
+        engine.state.artifact_consumption["a::foo"]
+        == oracle.artifact_consumption["a::foo"]
+    )
+
+    _assert_full_parity(engine.state, oracle)
```

NEW_TESTS
- test_canonical_target_domain_does_not_resurrect_stale_consumers_from_modern_empty_symbols
- test_canonical_target_domain_preserves_consumers_only_legacy_fallback
- test_content_change_removes_obsolete_consumption_target_and_matches_full_oracle

TARGETED_TEST_RESULTS
- New tests: 3 passed in 13.65s.
- Required regressions: 6 passed in 20.22s.
- git diff --check (source/test files, before embedding full diffs in walkthrough): passed.
- Full pytest suite and full repository analysis were not run.

OBSOLETE_TARGET_REGRESSION=PASS; artifact_consumption_state=fresh; api::VALUE absent from incremental state and fresh-full oracle.
LEGACY_FALLBACK_REGRESSION=PASS; consumers-only legacy payload still yields legacy::foo.
THREE_WAY_EXPECTED_FULL_LIVE=PASS; the reproducer test confirms api::VALUE is absent, a::foo is present and equal to fresh-full, and _assert_full_parity passes. Desktop LIVE is canonical_state=fresh at revision 1598.

CONTEXTOR_POST_EDIT_VERIFICATION=PASS; get_symbol_implementation and get_artifact_blast_radius report canonical_state=fresh, workspace_sync=verified, canonical_revision=1598, provenance=live, and artifact_consumption=fresh. Updated artifact blast radius shows 6 direct static consumers including the edited test module. Call context retains the two direct callers build_canonical_artifact_consumption and validate_canonical_artifact_consumption_coverage (plus artifact_consumption_is_fresh at depth 2). The source file syntax diagnostic is checked_and_none. get_live_events was continuous with resync_required=false and reported desktop_watcher updates for both allowed files; state_manager events were revisions 1595, 1597, 1598 and the test event was revision 1596. The latest state_manager event had blast_radius_state=deferred, while the subsequent direct Contextor queries returned fresh canonical families.
MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_RUNTIME_RESTART_REQUIRED=NO

UNKNOWN=Contextor consumer evidence is static and does not establish completeness for dynamic Python usage. No other task-specific uncertainty was observed.