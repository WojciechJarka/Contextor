# Canonical ModuleUsageFacts lifecycle hardening — Stage 2 implementation

Facade resolved through Contextor MCP and edited at:
`C:\Temp\Contextor_Repo\contextor\core\api\facade.py`.

## Implemented change

- Added private `_build_module_usage_baseline(modules)` in `contextor.core.reference.engine`.
- It calls the unchanged producer as `extract_module_usage_facts(module_id, module.ast_tree, imports=module.imports)`: no global target symbols, reexports, source reads, or AST parses.
- It rejects an unmaterialized slice and enforces exact domain coverage.
- `ContextorFacade.analyze_project` builds the baseline from its existing `mods` local immediately before `RepositoryAnalysisState`, passes `modules=mods` and `module_usages=module_usages`, then follows the existing persistence/LIVE publication path.
- Incremental production files were not changed. Existing `prepare_source_update` continues to call `extract_module_usage_facts(module_path, parsed_tree, imports=new_imports)`.

## Test evidence

Command:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_module_usage_facts.py tests/test_canonical_reference_projection.py tests/test_symbol_call_facts.py
```

Result: `49 passed in 56.60s`.

The new hydration regression proves `extract_module_usage_facts` was called 0 times during hydrate/load after full analysis, validates complete current-domain materialization, and the existing no-fallback canonical builder regression passed in the same focused set.

## LIVE evidence

Post-edit `get_live_events` returned `transient_connection_failure`: existing LIVE owner temporarily unreachable, no events and no revision available. No `update_file` call was made. Pre-edit revision was not captured before the approved edit, so watcher/revision advancement is not certified in this task. This does not affect the focused code/test evidence. A user-owned fresh full repository analysis remains required to seed the currently running old canonical state with the new full baseline.

Manual restart: none. MCP restart: no.

## Complete raw unified diff

```diff
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/reference/engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_canonical_reference_projection.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_module_usage_facts.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 26fdd2a..d78017e 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -500,6 +500,9 @@ class ContextorFacade:
             raw_artifacts = getattr(analysis_result, "artifacts", {}) or {}
             canonical_consumption = build_canonical_artifact_consumption(raw_artifacts)
 
+            from contextor.core.reference.engine import _build_module_usage_baseline
+            module_usages = _build_module_usage_baseline(mods)
+
             # Exact canonical coverage trust gate (no truthiness)
             consumption_valid = validate_canonical_artifact_consumption_coverage(
                 canonical_consumption,
@@ -507,13 +510,14 @@ class ContextorFacade:
             )
 
             state = RepositoryAnalysisState(
-                modules=getattr(analysis_result, "modules", {}),
+                modules=mods,
                 artifacts=raw_artifacts,
                 dependency_graph=graph,
                 trie=getattr(analysis_result, "trie", None),
                 package_root=getattr(analysis_result, "package_root", ""),
                 artifact_consumption=canonical_consumption,
                 artifact_consumption_state="fresh" if consumption_valid else "stale",
+                module_usages=module_usages,
                 metrics=metrics,
                 topology_analytics=topology_analytics,
                 topology_metrics_state="fresh",
diff --git a/contextor/core/reference/engine.py b/contextor/core/reference/engine.py
index 37f511e..94c147e 100644
--- a/contextor/core/reference/engine.py
+++ b/contextor/core/reference/engine.py
@@ -764,6 +764,36 @@ def extract_module_usage_facts(
     )
 
 
+def _build_module_usage_baseline(modules) -> dict[str, ModuleUsageFacts]:
+    """Build the complete materialized usage baseline from current module ASTs."""
+    baseline = {}
+
+    for module_id, module in modules.items():
+        facts = extract_module_usage_facts(
+            module_id,
+            module.ast_tree,
+            imports=module.imports,
+        )
+
+        if (
+            not facts.symbol_calls_materialized
+            or not facts.reference_evidence_materialized
+        ):
+            raise RuntimeError(
+                "Canonical ModuleUsageFacts baseline unavailable for current module "
+                f"{module_id}"
+            )
+
+        baseline[module_id] = facts
+
+    if set(baseline) != set(modules):
+        raise RuntimeError(
+            "Canonical ModuleUsageFacts baseline does not cover the current module domain"
+        )
+
+    return baseline
+
+
 # ==========================================================
 # CANONICAL REFERENCE PROJECTION
 # ==========================================================
diff --git a/tests/test_canonical_reference_projection.py b/tests/test_canonical_reference_projection.py
index b23c0ca..9c0c2a4 100644
--- a/tests/test_canonical_reference_projection.py
+++ b/tests/test_canonical_reference_projection.py
@@ -139,6 +139,39 @@ def test_golden_parity_matrix(multi_channel_repo):
     assert summarize_api_consumers(canonical_consumers) == summarize_api_consumers(legacy_consumers)
 
 
+def test_full_analysis_persists_materialized_usage_without_hydration_backfill(tmp_path):
+    root = tmp_path / "pkg"
+    root.mkdir()
+    (root / "__init__.py").write_text("", encoding="utf-8")
+    (root / "provider.py").write_text("def value():\n    return 1\n", encoding="utf-8")
+    (root / "consumer.py").write_text(
+        "from pkg.provider import value\n\ndef use():\n    return value()\n",
+        encoding="utf-8",
+    )
+
+    ContextorFacade.analyze_project(str(tmp_path))
+
+    from contextor.core.reference import engine as reference_engine
+    original = reference_engine.extract_module_usage_facts
+    calls = {"count": 0}
+
+    def tracked(*args, **kwargs):
+        calls["count"] += 1
+        return original(*args, **kwargs)
+
+    with patch.object(reference_engine, "extract_module_usage_facts", side_effect=tracked):
+        hydrated = hydrate_repository_engine(str(tmp_path))
+
+    state = hydrated.engine.state
+    assert calls["count"] == 0
+    assert set(state.module_usages) == set(state.modules)
+    assert all(
+        facts.symbol_calls_materialized
+        and facts.reference_evidence_materialized
+        for facts in state.module_usages.values()
+    )
+
+
 def test_zero_io_and_zero_ast_parses_during_canonical_projection(multi_channel_repo):
     td, state, graph = multi_channel_repo
     symbols = [
diff --git a/tests/test_module_usage_facts.py b/tests/test_module_usage_facts.py
index 3a55ff6..1c1e201 100644
--- a/tests/test_module_usage_facts.py
+++ b/tests/test_module_usage_facts.py
@@ -14,7 +14,10 @@ from contextor.core.analysis.state_manager import FileStateManager, RepositoryAn
 from contextor.core.domain.module import Module
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.live_state.store import load_snapshot, save_snapshot
-from contextor.core.reference.engine import extract_module_usage_facts
+from contextor.core.reference.engine import (
+    _build_module_usage_baseline,
+    extract_module_usage_facts,
+)
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
 
@@ -184,3 +187,38 @@ def test_state_lifecycle_and_snapshot_persistence(tmp_path):
     assert hasattr(loaded_state, "module_usages")
     assert "mod_x" in loaded_state.module_usages
     assert loaded_state.module_usages["mod_x"].imports == ("sys",)
+
+
+def test_build_module_usage_baseline_materializes_current_module_domain(tmp_path):
+    first = tmp_path / "first.py"
+    second = tmp_path / "second.py"
+    first.write_text("def caller():\n    return callee()\n\ndef callee():\n    return 1\n", encoding="utf-8")
+    second.write_text("value = 2\n", encoding="utf-8")
+    modules = {
+        "first": Module("first", "first.py", str(first), []),
+        "second": Module("second", "second.py", str(second), []),
+    }
+
+    result = _build_module_usage_baseline(modules)
+
+    assert set(result) == set(modules)
+    assert all(
+        facts.symbol_calls_materialized
+        and facts.reference_evidence_materialized
+        for facts in result.values()
+    )
+    assert result["first"].symbol_calls == (
+        ("first::caller", "first::callee", 2, "direct"),
+    )
+
+
+def test_build_module_usage_baseline_fails_closed_when_current_ast_is_unavailable(tmp_path):
+    unavailable = Module(
+        "unavailable",
+        "unavailable.py",
+        str(tmp_path / "missing.py"),
+        [],
+    )
+
+    with pytest.raises(RuntimeError, match="baseline unavailable"):
+        _build_module_usage_baseline({"unavailable": unavailable})
```

FULL_SEED_USAGE_BASELINE=IMPLEMENTED
FULL_SEED_INCREMENTAL_EXTRACTOR_PARITY=PASS
GLOBAL_TARGET_SYMBOLS_ADDED=NO
GLOBAL_REEXPORTS_ADDED=NO
FULL_SEED_USAGE_DOMAIN_COMPLETE=YES
FULL_SEED_SYMBOL_CALLS_MATERIALIZED=YES
FULL_SEED_REFERENCE_EVIDENCE_MATERIALIZED=YES
HYDRATION_USAGE_EXTRACTION_COUNT=0
ADDITIONAL_SOURCE_READS_BY_BASELINE=0
ADDITIONAL_AST_PARSE_BY_BASELINE=0
INCREMENTAL_CODE_CHANGED=NO
SCHEMA_CHANGE_REQUIRED=NO
MCP_CONTRACT_CHANGE_REQUIRED=NO
MCP_RESTART_REQUIRED=NO
FULL_REPOSITORY_REANALYSIS_REQUIRED=YES
TARGETED_TESTS=PASS
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\reference\engine.py; C:\Temp\Contextor_Repo\contextor\core\api\facade.py; C:\Temp\Contextor_Repo\tests\test_module_usage_facts.py; C:\Temp\Contextor_Repo\tests\test_canonical_reference_projection.py
NEXT_TARGET=residual canonical LIVE completeness audit

Wait for proceduj.

