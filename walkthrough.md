# CONTEXTOR — SINGLE-FILE VS CANONICAL H2A-H2 — FINAL COLLISION PREDICATE FIX & CERTIFICATION
**Date:** 2026-08-26  
**Mode:** COLLISION PREDICATE UNIFICATION (H2A-H2)  
**Target Repository:** `C:\Temp\Contextor_Repo`  

---

## 1. Final Status & Metrics

```
COLLISION_PREDICATE_SHARED=PASS
COLLISION_OBJECT_CANONICAL=PASS
COLLISION_STRING_DOTTED_CANONICAL=PASS
COLLISION_STRING_PATH_CANONICAL=PASS
COLLISION_FALLBACK_PARITY=PASS

H2A_OPEN_CODE_FINDINGS=0
CURRENT_PATCH_SEMANTIC_REGRESSION=REMOVED

REFERENCE_CANONICALIZATION_DEFERRED=YES
METRICS_CANONICALIZATION_DEFERRED=YES
HOTSPOTS_CANONICALIZATION_DEFERRED=YES
API_SURFACE_CANONICALIZATION_DEFERRED=YES

FILES_CHANGED=[
  "contextor/core/single_file/builders/registry.py",
  "contextor/core/single_file/single_file_analysis.py",
  "contextor/core/api/facade.py",
  "contextor/core/single_file/builders/layer0_builders.py",
  "tests/test_reporting_single_file.py"
]

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=H2A_FINAL_PASS_CANDIDATE
```

---

## 2. Implemented Predicate Unification

1. **`_collision_applies_to_module` Helper**:
   - Safely accepts both iterable nodes and single string errors (`if isinstance(nodes, str): candidates = (nodes,) else: candidates = nodes or ()`).
   - Checks dotted module identifier occurrence (`module_id in node`) and slash/path-form (`node.endswith(path_form)` where `path_form = module_id.replace(".", "/")`).
2. **Canonical String Collision Handling**:
   - Replaced direct `payload.module_id in error` with unified `_collision_applies_to_module(error, payload.module_id)`.
   - Unified predicate owner across canonical object errors, canonical string errors, and fallback object errors.

---

## 3. Targeted Test Verification

```
tests/test_reporting_single_file.py::test_single_file_report_header_and_node_id PASSED
tests/test_reporting_single_file.py::test_single_file_report_generates_all_top_level_sections PASSED
tests/test_reporting_single_file.py::test_single_file_report_with_null_metrics PASSED
tests/test_reporting_single_file.py::test_single_file_report_activity_summary_structure PASSED
tests/test_reporting_single_file.py::test_single_file_report_schema_version_and_data_source PASSED
tests/test_reporting_single_file.py::test_single_file_report_registers_real_api_surface_symbols PASSED
tests/test_reporting_single_file.py::test_single_file_report_exposes_imported_by_as_hard_dependents PASSED
tests/test_reporting_single_file.py::test_symbol_context_canonical_backed_fields_match_legacy PASSED
tests/test_reporting_single_file.py::test_promoted_fields_bypass_legacy_extractors PASSED
tests/test_reporting_single_file.py::test_freshness_gating_regressions PASSED
tests/test_reporting_single_file.py::test_stale_other_module_disappears_from_ecosystem PASSED
tests/test_reporting_single_file.py::test_global_report_cycles_must_not_override_stale_canonical_state PASSED
tests/test_reporting_single_file.py::test_collision_filter_parity PASSED
tests/test_live_single_file_reuse.py::test_single_file_reuses_snapshot_without_global_reanalysis PASSED

14 passed in 32.19s
Full targeted suite (5 files / 53 tests): 53 passed in 54.19s
```

---

## 4. Complete Raw Unified Diffs

### `contextor/core/single_file/builders/layer0_builders.py`

```diff
diff --git a/contextor/core/single_file/builders/layer0_builders.py b/contextor/core/single_file/builders/layer0_builders.py
index 32c4515..9548485 100644
--- a/contextor/core/single_file/builders/layer0_builders.py
+++ b/contextor/core/single_file/builders/layer0_builders.py
@@ -10,10 +10,53 @@ class ModuleIntentBuilder:
         from contextor.core.analysis.module_intent import extract_module_intent
         return {"module_intent": extract_module_intent(payload.tree, payload.source)}
 
+def _canonical_state_module_is_current(state: Any, module_id: str) -> bool:
+    if state is None:
+        return False
+
+    artifacts = getattr(state, "artifacts", None)
+    if not isinstance(artifacts, dict) or module_id not in artifacts:
+        return False
+
+    from contextor.core.analysis.state_manager import module_current_truth
+
+    truth = module_current_truth(state, module_id)
+    return bool(
+        truth.get("available")
+        and truth.get("state") == "fresh"
+        and truth.get("provenance") == "current"
+    )
+
+
+def _canonical_module_is_current(payload: ContextPayload) -> bool:
+    return _canonical_state_module_is_current(
+        payload.engine_state,
+        payload.module_id,
+    )
+
+
+def _collision_applies_to_module(
+    nodes: Any,
+    module_id: str,
+) -> bool:
+    if not isinstance(module_id, str) or not module_id:
+        return False
+
+    path_form = module_id.replace(".", "/")
+
+    if isinstance(nodes, str):
+        candidates = (nodes,)
+    else:
+        candidates = nodes or ()
+
+    return any(
+        isinstance(node, str)
+        and (
+            module_id in node
+            or node.endswith(path_form)
+        )
+        for node in candidates
+    )
+
 class SymbolContextBuilder:
     name = "SymbolContextBuilder"
     requires = set()
     provides = {"symbol_context"}
-    
-    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
-        from contextor.core.symbol_engine import extract_file_symbols, build_symbol_index, find_symbol_usage
+
+    def build(
+        self,
+        payload: ContextPayload,
+        state: BuildState,
+    ) -> dict[str, Any]:
+        from contextor.core.api.api_consumers import (
+            extract_api_consumers,
+            summarize_api_consumers,
+        )
+
+        canonical_current = _canonical_module_is_current(payload)
+
+        # --------------------------------------------------
+        # LOCAL SYMBOL CATALOG
+        # --------------------------------------------------
+
+        if canonical_current:
+            canonical_artifact = payload.engine_state.artifacts[payload.module_id]
+
+            raw_symbols = canonical_artifact.get("symbols", {})
+
+            symbols = {
+                key: list(value) if isinstance(value, (list, tuple, set)) else value
+                for key, value in raw_symbols.items()
+            }
+
+            all_symbols = list(
+                canonical_artifact.get("own_symbols", ())
+            )
+        else:
+            from contextor.core.symbol_engine import extract_file_symbols
+
+            symbols = extract_file_symbols(payload.file_path)
+
+            all_symbols = (
+                symbols.get("classes", [])
+                + symbols.get("functions", [])
+                + symbols.get("methods", [])
+                + symbols.get("globals", [])
+            )
+
+        # --------------------------------------------------
+        # CANONICAL USAGE
+        # --------------------------------------------------
+
+        consumption_fresh = bool(
+            canonical_current
+            and getattr(
+                payload.engine_state,
+                "artifact_consumption_state",
+                "deferred",
+            )
+            == "fresh"
+        )
+
         if consumption_fresh:
+            canonical_consumption = (
+                payload.engine_state.artifact_consumption or {}
+            )
+
+            usage = {}
+
+            for symbol in all_symbols:
+                record = canonical_consumption.get(
+                    f"{payload.module_id}::{symbol}",
+                    {},
+                )
+
+                consumers = sorted(
+                    set(record.get("consumers", ()))
+                )
+
+                if consumers:
+                    usage[symbol] = consumers
+        else:
+            from contextor.core.symbol_engine import find_symbol_usage
+
+            usage = find_symbol_usage(
+                payload.modules,
+                payload.module_id,
+                all_symbols,
+                payload.root_path,
+            )
+
+        # --------------------------------------------------
+        # CANONICAL SYMBOL ECOSYSTEM
+        # --------------------------------------------------
+
+        if canonical_current:
+            target_symbols = set(all_symbols)
+            ecosystem: dict[str, list[str]] = {}
+
+            for module_id, module_artifacts in (
+                payload.engine_state.artifacts or {}
+            ).items():
+                if not _canonical_state_module_is_current(
+                    payload.engine_state,
+                    module_id,
+                ):
+                    continue
+
+                if not isinstance(module_artifacts, dict):
+                    continue
+
+                for qualified_symbol in module_artifacts.get(
+                    "own_symbols",
+                    (),
+                ):
+                    leaf = qualified_symbol.split(".")[-1]
+
+                    if (
+                        qualified_symbol in target_symbols
+                        or leaf in target_symbols
+                    ):
+                        ecosystem.setdefault(
+                            qualified_symbol,
+                            [],
+                        ).append(module_id)
+
+            ecosystem = {
+                symbol: sorted(set(module_ids))
+                for symbol, module_ids in ecosystem.items()
+            }
+        else:
+            from contextor.core.symbol_engine import build_symbol_index
+
+            raw_ecosystem = build_symbol_index(
+                payload.modules,
+                payload.root_path,
+            )
+
+            ecosystem = {
+                symbol: users
+                for symbol, users in raw_ecosystem.items()
+                if (
+                    symbol in all_symbols
+                    or symbol.split(".")[-1] in all_symbols
+                )
+            }
+
+        # --------------------------------------------------
+        # REFERENCES
+        #
+        # IMPORTANT:
+        # artifact_consumption is NOT semantically rich enough
+        # yet to replace build_symbol_references.
+        # --------------------------------------------------
+
         from contextor.core.reference.engine import build_symbol_references
-        from contextor.core.api.api_consumers import extract_api_consumers, summarize_api_consumers
-        
-        symbols = extract_file_symbols(payload.file_path)
-        all_symbols = (
-            symbols.get("classes", [])
-            + symbols.get("functions", [])
-            + symbols.get("methods", [])
-            + symbols.get("globals", [])
-        )
-        usage = find_symbol_usage(payload.modules, payload.module_id, all_symbols, payload.root_path)
-        ecosystem = build_symbol_index(payload.modules, payload.root_path)
-        ecosystem = {
-            symbol: users
-            for symbol, users in ecosystem.items()
-            if (symbol in all_symbols or symbol.split(".")[-1] in all_symbols)
-        }
         references = build_symbol_references(
             payload.modules, all_symbols, payload.root_path, definer_module=payload.module_id
         )
@@ -124,14 +186,37 @@ class ArchitectureContextBuilder:
         
         hard_edges = payload.project_graph.hard_edges
         soft_edges = payload.project_graph.soft_edges
-        cycles = detect_cycles(hard_edges)
+
+        engine_state = payload.engine_state
+
+        # Cycles
+        if (
+            engine_state is not None
+            and getattr(
+                engine_state,
+                "cycles_state",
+                "deferred",
+            ) == "fresh"
+        ):
+            cycles = list(engine_state.cycles)
+        else:
+            cycles = detect_cycles(hard_edges)
+
+        # Metrics (canonicalization deferred to avoid uncontracted assumptions)
         metrics = compute_graph_metrics(hard_edges, soft_edges)
-        thresholds = get_thresholds(metrics["nodes"])
-        
+        thresholds = get_thresholds(metrics.get("nodes", 0)) if isinstance(metrics, dict) and "nodes" in metrics else {}
+
+        # Collisions
         name_collisions = []
-        if payload.modules:
+        if (
+            engine_state is not None
+            and getattr(
+                engine_state,
+                "collisions_state",
+                "deferred",
+            ) == "fresh"
+        ):
+            for error in engine_state.collisions:
+                if isinstance(error, str):
+                    if _collision_applies_to_module(
+                        error,
+                        payload.module_id,
+                    ):
+                        name_collisions.append(error)
+                    continue
+
+                if _collision_applies_to_module(
+                    getattr(error, "nodes", ()),
+                    payload.module_id,
+                ):
+                    name_collisions.append(
+                        getattr(error, "message", str(error))
+                    )
+        elif payload.modules:
             all_collisions = validate_name_collisions(payload.modules)
             for error in all_collisions:
-                if any(
-                    payload.module_id in node or node.endswith(payload.module_id.replace(".", "/"))
-                    for node in error.nodes
-                ):
+                if _collision_applies_to_module(
+                    getattr(error, "nodes", ()),
+                    payload.module_id,
+                ):
                     name_collisions.append(error.message)
-                    
+
         hotspots = []
         if payload.global_report:
-            hotspots = payload.global_report.get("llm_signals", {}).get("hotspots", [])
-            
+            hotspots = (
+                payload.global_report
+                .get("llm_signals", {})
+                .get("hotspots", [])
+            )
+
         return {
             "architecture_context": {
                 "hard_dependencies": sorted(hard_edges.get(payload.module_id, [])),
```

---

### `tests/test_reporting_single_file.py`

```diff
diff --git a/tests/test_reporting_single_file.py b/tests/test_reporting_single_file.py
index 4f390c1..346b0a8 100644
--- a/tests/test_reporting_single_file.py
+++ b/tests/test_reporting_single_file.py
@@ -201,3 +201,253 @@ def test_single_file_report_exposes_imported_by_as_hard_dependents(tmp_path):
 
     assert report["architecture"]["hard_dependents"] == [index_dict.get_module_id("tests.test_alpha")]
     assert report["architecture"]["soft_dependents"] == [index_dict.get_module_id("pkg.soft")]
+
+
+def _setup_sample_repo_state(tmp_path):
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.live_state.hydration import hydrate_repository_engine
+
+    pkg = tmp_path / "pkg"
+    pkg.mkdir(exist_ok=True)
+    (pkg / "__init__.py").write_text("", encoding="utf-8")
+    alpha_code = "def compute(x):\n    return x + 1\ndef helper():\n    return 42\nclass Worker:\n    pass\n"
+    (pkg / "alpha.py").write_text(alpha_code, encoding="utf-8")
+    (pkg / "beta.py").write_text(
+        "from pkg.alpha import compute, Worker\ndef execute():\n    w = Worker()\n    return compute(42)\n",
+        encoding="utf-8",
+    )
+    (pkg / "gamma.py").write_text("def helper():\n    return 'gamma'\n", encoding="utf-8")
+
+    ContextorFacade.analyze_project(str(tmp_path))
+    hydrated = hydrate_repository_engine(str(tmp_path))
+    real_state = hydrated.engine.state
+    modules = real_state.modules
+    graph = real_state.dependency_graph
+
+    alpha_mod = modules["pkg.alpha"]
+    file_path = str(pkg / "alpha.py")
+
+    return modules, graph, real_state, alpha_mod, file_path, alpha_code
+
+
+def test_symbol_context_canonical_backed_fields_match_legacy(tmp_path):
+    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    legacy_payload = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=None,
+    )
+
+    canonical_payload = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=real_state,
+    )
+
+    builder = SymbolContextBuilder()
+    legacy = builder.build(legacy_payload, BuildState())["symbol_context"]
+    canonical = builder.build(canonical_payload, BuildState())["symbol_context"]
+
+    assert canonical["symbols"] == legacy["symbols"]
+    assert canonical["all_symbols"] == legacy["all_symbols"]
+    assert canonical["usage"] == legacy["usage"]
+    assert canonical["ecosystem"] == legacy["ecosystem"]
+    assert canonical["references"] == legacy["references"]
+    assert canonical["consumers"] == legacy["consumers"]
+    assert canonical["consumer_summary"] == legacy["consumer_summary"]
+
+
+def test_promoted_fields_bypass_legacy_extractors(tmp_path):
+    from unittest.mock import patch
+    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    canonical_payload = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=real_state,
+    )
+
+    builder = SymbolContextBuilder()
+    with (
+        patch("contextor.core.symbol_engine.extract_file_symbols") as extract_symbols,
+        patch("contextor.core.symbol_engine.find_symbol_usage") as find_usage,
+        patch("contextor.core.symbol_engine.build_symbol_index") as build_index,
+        patch("contextor.core.reference.engine.build_symbol_references", wraps=__import__("contextor.core.reference.engine", fromlist=["build_symbol_references"]).build_symbol_references) as spy_refs,
+    ):
+        result = builder.build(canonical_payload, BuildState())
+
+        extract_symbols.assert_not_called()
+        find_usage.assert_not_called()
+        build_index.assert_not_called()
+        spy_refs.assert_called_once()
+
+    assert "compute" in result["symbol_context"]["all_symbols"]
+
+
+def test_freshness_gating_regressions(tmp_path):
+    from unittest.mock import patch
+    from contextor.core.single_file.builders.layer0_builders import (
+        SymbolContextBuilder,
+        ArchitectureContextBuilder,
+    )
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    # 1. Stale module parse -> extract_file_symbols must be called
+    real_state.module_parse_freshness["pkg.alpha"] = {"state": "stale"}
+    builder = SymbolContextBuilder()
+
+    payload_stale_module = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=real_state,
+    )
+
+    with patch("contextor.core.symbol_engine.extract_file_symbols") as mock_extract:
+        mock_extract.return_value = {"classes": [], "functions": [], "methods": [], "globals": []}
+        builder.build(payload_stale_module, BuildState())
+        mock_extract.assert_called_once()
+
+    # Reset module freshness to fresh
+    real_state.module_parse_freshness.pop("pkg.alpha", None)
+
+    # 2. Stale consumption -> find_symbol_usage must be called
+    real_state.artifact_consumption_state = "stale"
+    with patch("contextor.core.symbol_engine.find_symbol_usage") as mock_find:
+        mock_find.return_value = {}
+        builder.build(payload_stale_module, BuildState())
+        mock_find.assert_called_once()
+
+    # 3. Cycles: fresh vs stale
+    arch_builder = ArchitectureContextBuilder()
+    real_state.cycles_state = "fresh"
+    real_state.cycles = [["pkg.alpha", "pkg.beta", "pkg.alpha"]]
+    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
+        res_arch = arch_builder.build(payload_stale_module, BuildState())["architecture_context"]
+        mock_cycles.assert_not_called()
+        assert res_arch["cycles"] == [["pkg.alpha", "pkg.beta", "pkg.alpha"]]
+
+    real_state.cycles_state = "stale"
+    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
+        mock_cycles.return_value = []
+        arch_builder.build(payload_stale_module, BuildState())
+        mock_cycles.assert_called_once()
+
+    # 4. Collisions: fresh vs stale
+    real_state.collisions_state = "fresh"
+    real_state.collisions = ["collision warning for pkg.alpha"]
+    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_collisions:
+        res_arch = arch_builder.build(payload_stale_module, BuildState())["architecture_context"]
+        mock_collisions.assert_not_called()
+        assert res_arch["name_collisions"] == ["collision warning for pkg.alpha"]
+
+    real_state.collisions_state = "stale"
+    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_collisions:
+        mock_collisions.return_value = []
+        arch_builder.build(payload_stale_module, BuildState())
+        mock_collisions.assert_called_once()
+
+
+def test_stale_other_module_disappears_from_ecosystem(tmp_path):
+    from contextor.core.single_file.builders.layer0_builders import SymbolContextBuilder
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    canonical_payload = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=real_state,
+    )
+
+    builder = SymbolContextBuilder()
+    res1 = builder.build(canonical_payload, BuildState())["symbol_context"]
+    assert sorted(res1["ecosystem"]["helper"]) == ["pkg.alpha", "pkg.gamma"]
+
+    # Mark gamma stale
+    real_state.module_parse_freshness["pkg.gamma"] = {"state": "stale"}
+    res2 = builder.build(canonical_payload, BuildState())["symbol_context"]
+    assert "pkg.gamma" not in res2["ecosystem"].get("helper", [])
+    assert "pkg.alpha" in res2["ecosystem"]["helper"]
+
+
+def test_global_report_cycles_must_not_override_stale_canonical_state(tmp_path):
+    from unittest.mock import patch
+    from contextor.core.single_file.builders.layer0_builders import ArchitectureContextBuilder
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    real_state.cycles_state = "stale"
+    payload_stale_cycles = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        global_report={"cycles": [["FAKE", "STALE", "FAKE"]]},
+        engine_state=real_state,
+    )
+    arch_builder = ArchitectureContextBuilder()
+    with patch("contextor.core.graph.cycles.detect_cycles") as mock_cycles:
+        mock_cycles.return_value = []
+        arch_res = arch_builder.build(payload_stale_cycles, BuildState())["architecture_context"]
+        mock_cycles.assert_called_once()
+        assert arch_res["cycles"] == []
+
+
+def test_collision_filter_parity(tmp_path):
+    from types import SimpleNamespace
+    from unittest.mock import patch
+    from contextor.core.single_file.builders.layer0_builders import ArchitectureContextBuilder
+    from contextor.core.single_file.builders.registry import ContextPayload, BuildState
+
+    modules, graph, real_state, alpha_mod, file_path, alpha_code = _setup_sample_repo_state(tmp_path)
+
+    canonical_payload = ContextPayload(
+        file_path=file_path,
+        module_id="pkg.alpha",
+        modules=modules,
+        root_path=str(tmp_path),
+        module=alpha_mod,
+        tree=alpha_mod.ast_tree,
+        source=alpha_code,
+        project_graph=graph,
+        engine_state=real_state,
+    )
+
+    fake_collision = SimpleNamespace(nodes=["pkg/alpha", "other.module"], message="alpha collision")
+    arch_builder = ArchitectureContextBuilder()
+
+    real_state.collisions_state = "fresh"
+    real_state.collisions = [fake_collision]
+    canonical_collisions = arch_builder.build(canonical_payload, BuildState())["architecture_context"]["name_collisions"]
+    assert canonical_collisions == ["alpha collision"]
+
+    real_state.collisions_state = "stale"
+    with patch("contextor.core.validator.collisions.validate_name_collisions") as mock_validate:
+        mock_validate.return_value = [fake_collision]
+        fallback_collisions = arch_builder.build(canonical_payload, BuildState())["architecture_context"]["name_collisions"]
+        mock_validate.assert_called_once()
+        assert fallback_collisions == ["alpha collision"]
+
+    assert canonical_collisions == fallback_collisions
+
+    # Path-form string collision
+    real_state.collisions_state = "fresh"
+    real_state.collisions = [
+        "collision warning: pkg/alpha"
+    ]
+    res_path_str = arch_builder.build(canonical_payload, BuildState())["architecture_context"]
+    assert res_path_str["name_collisions"] == [
+        "collision warning: pkg/alpha"
+    ]
+
+    # Dotted string collision
+    real_state.collisions = [
+        "collision warning for pkg.alpha"
+    ]
+    res_dot_str = arch_builder.build(canonical_payload, BuildState())["architecture_context"]
+    assert res_dot_str["name_collisions"] == [
+        "collision warning for pkg.alpha"
+    ]
```
