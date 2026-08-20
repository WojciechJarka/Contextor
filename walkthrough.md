# SSOT-CLEANUP-A - FINAL SEMANTIC CLOSURE

## SUMMARY

Trzy wskazane problemy zostaly zamkniete: brak fresh analytics jest jawnie deferred, layer index pochodzi z fresh canonical module layers, a test modules uwzgledniaja canonical layer `tests`. Risk bez fresh producer ma wartosc `null`.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\walkthrough.md`

## IMPLEMENTATION

- `get_project_architecture`: `action_items`, `top_global_hotspots` i `debt_summary` zwracaja `{available:false,state:"deferred",reason:...}` zamiast falszywego fresh-empty.
- `layer_index`: stare `layer_information.layer_index` nie jest odczytywane. Fresh `cached_analytics.module_layers` jest deterministycznie agregowane do `{layer,module_count}`; bez fresh cache family jest deferred.
- `get_file_edit_context`: oba tryby dodaja do naming convention moduly, ktorych fresh canonical `module_layers` ma wartosc `tests`.
- Legacy/full `risk_score`: fresh topology map zwraca wartosc; stale/deferred/missing zwraca `null`, nie `0.0`.

## OUT_OF_SCOPE_FINDINGS

- Brak.

## TARGETED_TESTS

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_mcp_regressions.py -q
```

`65 passed, 1 warning in 26.85s`.

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_mcp_regressions.py tests/test_canonical_state_contract.py tests/test_incremental_local_metrics.py -q
```

`103 passed, 1 warning in 52.20s`. Warning: third-party `AuthlibDeprecationWarning` z `fastmcp`.

## LIVE_VERIFICATION

- Pre-edit revision: `725`.
- Desktop watcher: `mcp_server.py` revision `726` status `UPDATED`; test revisions `727-730` status `UPDATED`.
- Final revision: `732`; sposob aktualizacji: `desktop_watcher`, bez recznego `update_file`.

RESTART MCP

## CONTEXTOR_POST_CHANGE_AUDIT

- implementations: `get_project_architecture` lines 1474-1554 odczytane jako aktualna implementation; `get_file_edit_context` lines 2562-3129 potwierdzone po zmianie.
- consumers: `contextor.mcp_server` ma 7 direct i 7 transitive test consumers.
- blast_radius: MCP adapter oraz regression tests; 103 targeted tests passed.
- dead_or_duplicate_paths: `layer_information.layer_index/hotspots/debt` nie sa current query paths; brak nowego report adaptera.
- canonical_contract: layer index i test classification wymagaja `cached_analytics_state == "fresh"`; risk wymaga `topology_metrics_state == "fresh"`.
- scope_leakage: brak zmian poza trzema wskazanymi problemami.
- final_contextor_verdict: PASS.

## FULL_DIFFS

```diff
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@
-        layer_info = getattr(state, "layer_information", {}) or {}
-        action_items = []
-        layer_index = layer_info.get("layer_index", [])
-        hotspots = []
-        debt_summary = {}
-        
-        collections = {}
-        for key, source_key in (
-            ("action_items", "action_items"),
-            ("layer_index", "layer_index"),
-            ("top_global_hotspots", "top_hotspots"),
-        ):
-            source = {
-                "action_items": action_items,
-                "layer_index": layer_index,
-                "top_hotspots": hotspots,
-            }[source_key]
-            items, total, truncated = _bounded_items(source, max_items)
-            collection = {"total": total, "truncated": truncated}
-            if not compact:
-                collection["items"] = items
-            collections[key] = collection
+        unavailable = {
+            "available": False,
+            "state": "deferred",
+            "reason": "No fresh canonical LIVE producer is available for this analytics family.",
+        }
+        collections = {
+            "action_items": dict(unavailable),
+            "top_global_hotspots": dict(unavailable),
+        }
+        debt_summary = dict(unavailable)
+
+        cached_analytics = getattr(state, "cached_analytics", {}) or {}
+        cached_state = getattr(state, "cached_analytics_state", "deferred")
+        module_layers = (
+            cached_analytics.get("module_layers", {})
+            if cached_state == "fresh" and isinstance(cached_analytics, dict)
+            else None
+        )
+        if isinstance(module_layers, dict):
+            layer_counts: dict[str, int] = {}
+            for layer in module_layers.values():
+                layer_name = str(layer)
+                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
+            layer_items = [
+                {"layer": layer, "module_count": count}
+                for layer, count in sorted(layer_counts.items())
+            ]
+            items, total, truncated = _bounded_items(layer_items, max_items)
+            layer_index = {"available": True, "total": total, "truncated": truncated}
+            if not compact:
+                layer_index["items"] = items
+        else:
+            layer_index = dict(unavailable)
+        collections["layer_index"] = layer_index
@@
             test_modules = {
                 name
                 for name in graph_modules
                 if name.startswith("tests.") or name == "tests" or name.rsplit(".", 1)[-1].startswith("test_")
             }
+            if engine and getattr(engine.state, "cached_analytics_state", "deferred") == "fresh":
+                cached = getattr(engine.state, "cached_analytics", {}) or {}
+                canonical_layers = cached.get("module_layers", {}) if isinstance(cached, dict) else {}
+                test_modules.update(
+                    name for name, layer in canonical_layers.items() if layer == "tests"
+                )
@@
-        risk_score = 0.0
+        risk_score = None
         topology = getattr(state, "topology_analytics", {}) or {}
         if getattr(state, "topology_metrics_state", "deferred") == "fresh":
-            risk_score = (topology.get("module_risk", {}) or {}).get(module_name, 0.0)
+            risk_score = (topology.get("module_risk", {}) or {}).get(module_name)
@@
         test_modules = {
             name
             for name in graph_modules
             if name.startswith("tests.")
             or name == "tests"
             or name.rsplit(".", 1)[-1].startswith("test_")
         }
+        if getattr(state, "cached_analytics_state", "deferred") == "fresh":
+            canonical_layers = cached_analytics.get("module_layers", {}) if isinstance(cached_analytics, dict) else {}
+            test_modules.update(
+                name for name, layer in canonical_layers.items() if layer == "tests"
+            )
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@
 def test_stale_layer_snapshot_is_not_presented_after_incremental_update(
     tmp_path, monkeypatch
 ):
+    from contextor.core.domain.graph import ProjectGraph
+
     state = RepositoryAnalysisState(
-        modules={"provider": SimpleNamespace(module_id="1/1", path="provider.py")},
+        modules={
+            "provider": SimpleNamespace(module_id="1/1", path="provider.py"),
+            "quality.scenario": SimpleNamespace(module_id="2/1", path="quality/scenario.py"),
+        },
         artifacts={"provider": {"own_symbols": []}},
         metrics={"provider": {"betweenness": 0.9, "hub_score": 0.8}},
         topology_analytics={"module_risk": {"provider": 0.95}},
         topology_metrics_state="stale",
+        cached_analytics={
+            "module_layers": {"provider": "core", "quality.scenario": "tests"}
+        },
+        cached_analytics_state="fresh",
+        dependency_graph=ProjectGraph(
+            hard_edges={"quality.scenario": {"provider"}, "provider": set()},
+            soft_edges={},
+        ),
         layer_information={
             "summary_data": {"action_items": ["old action"]},
+            "layer_index": [{"layer": "legacy", "module_count": 99}],
             "hotspots": [{"module": "provider", "score": 0.99}],
             "debt": {"score": 99},
@@
-    architecture = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))
+    architecture = json.loads(
+        mcp_server.get_project_architecture.fn(str(tmp_path), compact=False)
+    )
@@
-    assert architecture["action_items"]["total"] == 0
-    assert architecture["top_global_hotspots"]["total"] == 0
-    assert architecture["debt_summary"] == {}
-    assert edit_context["risk_score"] == 0.0
+    assert architecture["action_items"]["available"] is False
+    assert architecture["top_global_hotspots"]["available"] is False
+    assert architecture["debt_summary"]["available"] is False
+    assert architecture["layer_index"] == {
+        "available": True,
+        "items": [
+            {"layer": "core", "module_count": 1},
+            {"layer": "tests", "module_count": 1},
+        ],
+        "total": 2,
+        "truncated": False,
+    }
+    assert "legacy" not in json.dumps(architecture)
+    assert edit_context["risk_score"] is None
+    assert edit_context["tests_covering"]["tests"][0]["module"] == "quality.scenario"
@@
-    assert architecture["top_global_hotspots"]["total"] == 0
-    assert architecture["debt_summary"] == {}
+    assert architecture["top_global_hotspots"]["available"] is False
+    assert architecture["debt_summary"]["available"] is False
@@
-    assert architecture["action_items"] == {
-        "items": [], "total": 0, "truncated": False,
-    }
-    assert architecture["top_global_hotspots"]["total"] == 0
+    assert architecture["action_items"]["available"] is False
+    assert architecture["top_global_hotspots"]["available"] is False
```

## FINAL_VERDICT

PASS
