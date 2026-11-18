# SP-T4-I2B5-I3G — FULL GRAPH PRECONDITION

## PREFLIGHT

- DIRECT_EVIDENCE: Przed zmianą HEAD wynosił `b4f2626902d2786325e82bfadc1748e112b45d75`; `git status --short --branch` pokazywał czysty working tree (`main...origin/main`).
- DIRECT_EVIDENCE: Contextor LIVE przed zmianą: revision `1440`, provenance `live`, canonical_state `fresh`, `resync_required=false`.
- DIRECT_EVIDENCE: Na revision 1440 oba pliki docelowe miały `workspace_sync=verified` i syntax diagnostics `checked_and_none`, `errors=[]`.
- CODE_PATH_PROVED: W `plan_executor.py` bezpośrednio po istniejącym ValueError dla braku `dependency_graph` znajdowało się `path = Path(file_path)`; dokładny anchor pasował. T58 kończył plik testowy; nowy test został dopisany za nim.
- DIRECT_EVIDENCE: Nie uruchamiano FULL, restartu ani MCP `update_file`. Nie zmieniano plików poza dozwoloną listą.

## EXACT_IMPLEMENTATION

- CODE_PATH_PROVED: W `contextor/core/analysis/incremental/plan_executor.py:1165-1171` dodano dokładnie wskazany warunek po istniejącym guardzie `dependency_graph` i przed utworzeniem ścieżki/candidate. Żaden istniejący warunek nie został zmieniony.
- CODE_PATH_PROVED: Na końcu `tests/test_p1d3_d2b2_type_only.py` dodano dokładny test `test_sp_t4_i2b5_i3g_t59_full_graph_requires_modules`. Istniejące testy nie były edytowane.
- DIRECT_EVIDENCE: Zmiana używa wyłącznie ogólnych wartości kontraktu planu `force_full_graph`, `modules` i `dependency_graph`; nie dodaje nazw modułów ani wyjątków specyficznych dla repozytorium.

## FULL_GRAPH_PRECONDITIONS

- CODE_PATH_PROVED: Istniejący guard nadal wymaga `dependency_graph`, gdy `force_full_graph=True`; nowy guard dodatkowo wymaga wtedy `modules`. Oba błędy powstają przed przygotowaniem candidate.
- CODE_PATH_PROVED: Przy nieusuniętym module `candidate.modules[delta.module_path]` jest aktualizowane wyłącznie wtedy, gdy `"modules" in plan.patch_families` (`plan_executor.py:1233`). Pełna budowa grafu przekazuje `candidate.modules` do `build_graph` (`plan_executor.py:1418-1421`). T59 pokrywa przypadek planu zawierającego wyłącznie `dependency_graph`.
- DIRECT_EVIDENCE: Warunki istniejącej gałęzi pełnej budowy dla usunięcia/nowego modułu nie zostały zmienione. Nowy guard dotyczy wyłącznie jawnego `force_full_graph`.
- INFERENCE — REVIEW LIMIT: Sama obecność rodziny `modules` dowodzi, że executor wejdzie w ścieżkę aktualizacji modułu dla bieżącego `delta.module_path`; nie dowodzi kompletności payloadu ani reklasyfikacji wszystkich innych modułów. Ten wąski patch realizuje wskazany warunek requestu i nie certyfikuje globalnej świeżości wszystkich modułów przy zmianie globalnej polityki.

## TARGETED_TESTS

- DIRECT_EVIDENCE: Interpreter: repo `.venv`, CPython 3.15.2.
- DIRECT_EVIDENCE: Uruchomiono wyłącznie T59, T57-T58 oraz T52-T56:
  `python -m pytest -q tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i3g_t59_full_graph_requires_modules tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i3_t57_executor_graph_switch tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i3_t58_invalid_graph_request tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i2_t52_no_graph_delta tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i2_t53_local_import_delta tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i2_t54_unrelated_import_delta tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i2_t55_module_membership tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i2_t56_preserve_plan_contract`
- DIRECT_EVIDENCE: Wynik: `12 passed in 5.21s`. Nie uruchamiano pełnego pytest.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Desktop watcher zgłosił `plan_executor.py` jako UPDATED na revision 1441 oraz `tests/test_p1d3_d2b2_type_only.py` jako UPDATED na revision 1442. Feed miał `continuity=continuous`, `resync_required=false`.
- DIRECT_EVIDENCE: Po zmianie LIVE revision 1442, provenance `live`, canonical_state `fresh`, `resync_required=false`.
- DIRECT_EVIDENCE: Oba pliki na revision 1442 miały `workspace_sync=verified`; ich syntax diagnostics: `checked_and_none`, `errors=[]`. Globalne syntax diagnostics: 0, `fresh`.
- DIRECT_EVIDENCE: Rodziny graph, topology i structural cycles były `fresh`. Rodzina `cycle_semantics` pozostała `stale`; nie jest to stan rodziny structural cycles.
- UNKNOWN: Synchronizacja źródeł z LIVE nie poświadcza adopcji zmienionego kodu przez już działający proces; adopcji runtime nie badano i nie wykonywano restartu.
- DIRECT_EVIDENCE: Nie użyto MCP `update_file`.

## FINAL_VERDICT

I2B5_I3G_PASS — wskazany guard i T59 są obecne, wskazane testy przechodzą, a oba pliki są zsynchronizowane z aktualnym LIVE. Werdykt dotyczy wyłącznie precondition `force_full_graph`; nie certyfikuje kompletności reklasyfikacji modułów przy zmianie globalnej polityki ani adopcji kodu przez proces.

## FILES_CHANGED

- `contextor/core/analysis/incremental/plan_executor.py` — pełny diff poniżej.
- `tests/test_p1d3_d2b2_type_only.py` — pełny diff poniżej.
- `walkthrough.md` — raport nadpisany; self-diff pominięty zgodnie z konwencją raportowania.

## FULL_DIFFS

### `contextor/core/analysis/incremental/plan_executor.py`

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index c27a8ff..18dfa10 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1164,0 +1165,7 @@ def execute_refresh_plan(
+    if (
+        force_full_graph
+        and "modules" not in plan.patch_families
+    ):
+        raise ValueError(
+            "Full graph rebuild requires modules patch"
+        )
```

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 829a0e8..195f368 100644
@@ -4368,0 +4369,31 @@ def test_sp_t4_i2b5_i3_t58_invalid_graph_request(
+
+def test_sp_t4_i2b5_i3g_t59_full_graph_requires_modules(
+    tmp_path,
+):
+    from contextor.core.analysis.incremental import (
+        plan_executor as executor,
+    )
+    from contextor.core.analysis.state_manager import FileDelta
+    from contextor.core.domain.refresh_plan import RefreshPlan
+
+    plan = RefreshPlan(
+        patch_families=("dependency_graph",),
+    )
+
+    with pytest.raises(
+        ValueError,
+        match="Full graph rebuild requires modules patch",
+    ):
+        executor.execute_refresh_plan(
+            state=RepositoryAnalysisState(),
+            delta=FileDelta(module_path="pkg.a"),
+            usage_delta=None,
+            plan=plan,
+            new_imports=[],
+            new_artifacts={},
+            new_usage=None,
+            root_path=tmp_path,
+            file_path=str(tmp_path / "a.py"),
+            force_full_graph=True,
+        )
```
