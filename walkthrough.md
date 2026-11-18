# SP-T4-I2B5-I4B-I1 — literalna integracja

## PREFLIGHT

- **DIRECT_EVIDENCE:** HEAD przed zmianą: `378e4bc84140be2e65f936e271b8e4d0910b646f`; `git status --short` był pusty.
- **DIRECT_EVIDENCE:** Contextor MCP przed zmianą zwracał canonical revision `1447`, `provenance=live`, `canonical_state=fresh`; `engine.py` miał `workspace_sync=verified`. Diagnostyka składni: 0 błędów, fresh. Graph i cycles: fresh; cycles=16. `cycle_semantics=stale`.
- **DIRECT_EVIDENCE:** dokładne anchory w źródle przed edycją: `Path` był już importowany; `Module` i oba helpery nie były importowane. Deletion: `plan_refresh` kończył się w okolicy linii 648, po nim następował `INCREMENTAL_APPLY_START`. Add/update: `plan_refresh` w okolicy 766, semantic no-op zajmował linie 774–819, następnie `INCREMENTAL_APPLY_START` i wywołanie executora. Sygnatura `_apply_delta_and_commit` zawierała `clear_parse_module` w linii 929, a wywołanie executora nie przekazywało jeszcze trzech wartości. Publikacja modułów w linii 1130 zerowała evidence w linii 1131.
- **DIRECT_EVIDENCE:** `source_path` jest wyliczany jako kanoniczna ścieżka Python z `rel_path`; `PreparedSourceUpdate` zawiera `typing_guard_source_evidence`. Sygnatura `execute_refresh_plan` przyjmuje `force_full_graph`, `classified_modules` i `updated_typing_guard_evidence`.
- **CODE_PATH_PROVED:** istniejący helper waliduje baseline schema-v2, aktualizuje dowody zmienionego modułu, odtwarza zapisane kandydatury `ImportRef` i wywołuje wspólny klasyfikator. Istniejący planner rozszerza rodziny grafu i żąda pełnego build grafu przy zmianie membership albo klasyfikacji importu poza zmienionym modułem. Ten patch tylko podłącza te istniejące mechanizmy.
- **INFERENCE:** nie widać hardkodowania repozytorium, nazw testów ani liczby cykli w dodanym kodzie; identyfikatory i ścieżki pochodzą z bieżącego update.

## EXACT IMPLEMENTATION

- Dodano import `Module` i importy `reclassify_incremental_type_only` oraz `plan_type_only_graph_refresh`; istniejącego `Path` nie duplikowano.
- Deletion tworzy płytki `provisional`, usuwa z niego `module_path`, wywołuje reclassyfikację z `deleted=True`, przepuszcza wynik przez planner i przekazuje trzy wartości do `_apply_delta_and_commit`.
- Add/update, po dotychczasowym semantic no-op, tworzy `provisional`. Nowy `Module` jest tworzony tylko wtedy, gdy początkowy plan zawiera rodzinę `modules`. Potem helper otrzymuje bieżące `new_imports` i source evidence v1 z `prep`; planner aktualizuje plan; executor dostaje wynik planu i trzy wartości.
- `_apply_delta_and_commit` przekazuje argumenty bez transformacji do `execute_refresh_plan`.
- Normalna publikacja przypisuje `candidate.typing_guard_evidence` do canonical state. Kolejność pozostałych publikowanych pól pozostaje bez zmian.
- `_commit_syntax_candidate`, semantic no-op, parse-error, helper, executor, RefreshPlanner i FULL indexer nie zostały zmienione. Nie edytowano testów.

## TARGETED TESTS

Interpreter: `.venv\Scripts\python.exe`, **Python 3.15.2**. Uruchomiono wyłącznie poniższe siedem node IDs, jednym wywołaniem pytest z `--tb=long`:

```text
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t62_engine_global_reclassification
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t63_consecutive_updates
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t64_deletion_restores_soft
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i1_t06_updated_invalidates_evidence
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i1_t07_syntax_error_invalidates_evidence
tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i1_t08_rejected_transaction_preserves_evidence
```

Wyniki:

| Test | Wynik |
|---|---|
| T62 — globalna reclassyfikacja przez publiczne `update_file` | PASS |
| T63 — kolejne commity schema-v2 | PASS |
| T64 — deletion przywraca soft edge | PASS |
| T65 — niepoprawny baseline fail-closed | PASS |
| T06 — `updated_invalidates_evidence` | FAIL |
| T07 — błąd składni | PASS |
| T08 — odrzucona transakcja | PASS |

Zachowany wynik pytest dla T06 (pytest włączył sześć pozostałych testów i zakończył z `1 failed, 6 passed in 11.10s`):

```text
F..                                                                  [100%]
================================== FAILURES ===================================
_______________ test_sp_t4_i1_t06_updated_invalidates_evidence ________________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1283/test_sp_t4_i1_t06_updated_inva0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1283/test_sp_t4_i1_t06_updated_inva0')

    def test_sp_t4_i1_t06_updated_invalidates_evidence(tmp_path, isolated_dirs):
        root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
        persisted, engine = _i1_full_engine(root)
        assert persisted.typing_guard_evidence["global_policy_satisfied"] is True
        before_import = _i1_guarded_import(engine.state)
        before_hard = dict(engine.state.dependency_graph.hard_edges)
        before_soft = dict(engine.state.dependency_graph.soft_edges)
        target = root / "pkg/c.py"
        target.write_text("pass\nVALUE = 2\n", encoding="utf-8")
        result = engine.update_file(str(target.resolve()))
        assert result.status == "UPDATED"
>       assert engine.state.typing_guard_evidence == {}
E       AssertionError: assert {'schema_vers...0a2f2')}, ...} == {}
E         
E         Left contains 10 more items:
E         {'candidate_imports_by_module': {'pkg.a': (ImportRef(module='typing',
                                                              level=0,
                                                              names=['TYPE_CHECKING'],
                                                              is_from_import=True,
                                                              is_local=False,...
E         
E         ...Full output truncated (37 lines hidden), use '-vv' to show

tests\\test_p1d3_d2b2_type_only.py:2733: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i1_t06_updated_invalidates_evidence
1 failed, 6 passed in 11.10s
```

- **DIRECT_EVIDENCE:** jedyna awaria to istniejąca asercja `typing_guard_evidence == {}` po udanym update. Zmiana zachowuje teraz evidence candidate; assertion otrzymał schema-v2 z wpisami zamiast pustego słownika.
- **INFERENCE:** ta asercja może reprezentować wcześniejszy kontrakt zerowania evidence i jest niespójna z nowym wymaganiem trwałego evidence. Nie zmieniano jej ani nie maskowano wyniku.
- Nie uruchamiano pełnego pytest ani FULL.

## MCP POST-CHANGE AUDIT

- **DIRECT_EVIDENCE:** event `desktop_watcher`, `operation=update_file`, `status=UPDATED` dla `engine.py`; revision `1448`, continuity `continuous`, `resync_required=false`, `resync_reason=null`.
- **DIRECT_EVIDENCE:** Contextor MCP odczytał zmieniony symbol przy revision `1448`, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified`.
- **DIRECT_EVIDENCE:** syntax diagnostics `0`, fresh. Graph/module/topology/artifact-consumption/cycles/collisions/lineage families fresh. Cycles: 16, fresh; active warning count 16, warning view fresh. `cycle_semantics=stale`.
- Source sync i watcher event potwierdzają indeksację źródła. Nie stanowią dowodu, że istniejący proces załadował nowy kod; runtime adoption nie była osobno weryfikowana. Restartu nie wykonywano.
- `git diff --check -- contextor/core/analysis/incremental/engine.py` nie zgłosił błędów whitespace. Całościowy check wskazał końcowe spacje wyłącznie w zachowanym wyjściu pytest i pustych liniach dosłownego unified diff w tym raporcie. Git wyświetlił ostrzeżenie o konwersji LF→CRLF przy przyszłym zapisie pliku.

## FINAL VERDICT

**IMPLEMENTATION_APPLIED; VALIDATION_PARTIAL.** T62–T65, T07 i T08 przeszły. T06 pozostał czerwony na asercji wymagającej pustego evidence; zgodnie z poleceniem nie zmieniano testu ani kodu naprawczego. Nie deklaruję pełnego PASS przy nieprzechodzącym wskazanym teście.

## FILES_CHANGED

- `contextor/core/analysis/incremental/engine.py` — jedyny zmieniony plik produkcyjny/testowy. `walkthrough.md` jest wymaganym artefaktem raportu i nie jest tu liczony jako plik produkcyjny/testowy.

## FULL_DIFFS

### `contextor/core/analysis/incremental/engine.py`

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index ad9c5f1..a0a0740 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -7,6 +7,7 @@ from pathlib import Path
 from typing import Optional, List, Set, Dict, Iterable, Tuple, Any
 
 from contextor.core.domain.graph import ProjectGraph
+from contextor.core.domain.module import Module
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
 from contextor.core.cycle_semantics.lifecycle import (
     invalidate_cycle_semantics,
@@ -37,6 +38,10 @@ from contextor.core.analysis.incremental.plan_executor import (
     _prepare_candidate_state,
     execute_refresh_plan,
 )
+from contextor.core.analysis.incremental.type_only_policy import (
+    reclassify_incremental_type_only,
+    plan_type_only_graph_refresh,
+)
 from contextor.core.analysis.state_manager import (
     artifact_consumption_is_fresh,
     canonical_python_source_path,
@@ -646,6 +651,28 @@ class IncrementalAnalysisEngine:
                     module_usages=self.state.module_usages,
                     collision_facts_changed=collision_facts_changed,
                 )
+                provisional = dict(self.state.modules)
+                provisional.pop(module_path, None)
+
+                classified_modules, updated_evidence = (
+                    reclassify_incremental_type_only(
+                        provisional,
+                        previous_modules=self.state.modules,
+                        previous_evidence=self.state.typing_guard_evidence,
+                        changed_module_id=module_path,
+                        changed_source_path=source_path,
+                        changed_imports=[],
+                        changed_source_evidence=None,
+                        deleted=True,
+                    )
+                )
+
+                plan, force_full_graph = plan_type_only_graph_refresh(
+                    plan,
+                    changed_module_id=module_path,
+                    previous_modules=self.state.modules,
+                    classified_modules=classified_modules,
+                )
                 _trace_incremental_phase(
                     "INCREMENTAL_APPLY_START",
                     result=(
@@ -662,6 +689,9 @@ class IncrementalAnalysisEngine:
                     syntax_source_path=source_path,
                     remove_syntax_fact=True,
                     clear_parse_module=module_path,
+                    force_full_graph=force_full_graph,
+                    classified_modules=classified_modules,
+                    updated_typing_guard_evidence=updated_evidence,
                 )
                 blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                 affected_modules = sorted(affected_set) if blast_radius_complete else []
@@ -817,6 +847,38 @@ class IncrementalAnalysisEngine:
                     },
                 )
 
+            provisional = dict(self.state.modules)
+
+            if "modules" in plan.patch_families:
+                path = Path(file_path)
+                provisional[module_path] = Module(
+                    module_id=module_path,
+                    path=str(path.relative_to(self.root_path)),
+                    absolute_path=str(path.resolve()),
+                    imports=list(new_imports),
+                )
+
+            classified_modules, updated_evidence = (
+                reclassify_incremental_type_only(
+                    provisional,
+                    previous_modules=self.state.modules,
+                    previous_evidence=self.state.typing_guard_evidence,
+                    changed_module_id=module_path,
+                    changed_source_path=source_path,
+                    changed_imports=new_imports,
+                    changed_source_evidence=(
+                        prep.typing_guard_source_evidence
+                    ),
+                )
+            )
+
+            plan, force_full_graph = plan_type_only_graph_refresh(
+                plan,
+                changed_module_id=module_path,
+                previous_modules=self.state.modules,
+                classified_modules=classified_modules,
+            )
+
             # 3. Apply and Commit driven by RefreshPlan
             _trace_incremental_phase(
                 "INCREMENTAL_APPLY_START",
@@ -835,6 +897,9 @@ class IncrementalAnalysisEngine:
                 syntax_source_path=source_path,
                 syntax_fact=checked_and_none,
                 clear_parse_module=module_path,
+                force_full_graph=force_full_graph,
+                classified_modules=classified_modules,
+                updated_typing_guard_evidence=updated_evidence,
             )
 
             if plan.refresh_completeness == "requires_resync":
@@ -927,6 +992,9 @@ class IncrementalAnalysisEngine:
         syntax_fact: Dict[str, Any] | None = None,
         remove_syntax_fact: bool = False,
         clear_parse_module: str | None = None,
+        force_full_graph: bool = False,
+        classified_modules: dict[str, Module] | None = None,
+        updated_typing_guard_evidence: dict[str, object] | None = None,
     ) -> tuple[Set[str], bool, dict]:
         """
         Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
@@ -949,6 +1017,9 @@ class IncrementalAnalysisEngine:
                 file_path=file_path,
                 new_collision_facts=new_collision_facts,
                 new_reexport_facts=new_reexport_facts,
+                force_full_graph=force_full_graph,
+                classified_modules=classified_modules,
+                updated_typing_guard_evidence=updated_typing_guard_evidence,
             )
         except Exception as exc:
             _trace_incremental_phase(
@@ -1128,7 +1199,9 @@ class IncrementalAnalysisEngine:
         if clear_parse_module is not None:
             clear_module_parse_failure(candidate, clear_parse_module)
         self.state.modules = candidate.modules
-        self.state.typing_guard_evidence = {}
+        self.state.typing_guard_evidence = (
+            candidate.typing_guard_evidence
+        )
         self.state.reexport_facts_by_module = (
             candidate.reexport_facts_by_module
         )
```
