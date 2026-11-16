# SP-T4-I1C — legacy state and constructor compatibility

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first: `get_project_architecture(fields=[])` dla Contextora zwrócił LIVE revision 1413, provenance `live`, canonical_state `fresh`, workspace_sync `unverified`, resync_required=false. `get_module_context` dla `contextor.core.analysis.state_manager` i `tests.test_p1d3_d2b2_type_only` potwierdził revision 1413, `workspace_sync=verified`. Git HEAD `b24374db9508b55041c9a995aeb628511c30bb47`, status czysty. Diff SP-T4-I1 był w tym HEAD, nie stanowił bieżącej modyfikacji. Dokładne anchory: deklaracja `typing_guard_evidence` w `state_manager.py:90`, pętla `for state_field in fields(self)` w `:174`, istniejące T05–T08 w `tests/test_p1d3_d2b2_type_only.py:2708-2766`.

## EXACT TWO-FIX CORRECTION

W `RepositoryAnalysisState` zmieniono wyłącznie deklarację pola na `field(default_factory=dict, kw_only=True)` bez przesuwania pozostałych pól. Na początku istniejącej pętli `clone_for_update` dodano literalną gałąź dla `typing_guard_evidence`: `getattr(..., None)`, płytka kopia tylko gdy `type(evidence) is dict`, w przeciwnym razie `{}`, następnie `continue`. Reszta pętli i pozostałe pola pozostały bez zmian. Nie zmieniono klasyfikacji importów ani grafu.

## LEGACY SNAPSHOT CONTRACT

DIRECT_EVIDENCE T10: po usunięciu pola z `__dict__` instancji, `pickle.dumps`/`pickle.loads` zachowuje jego brak, a `clone_for_update()` zwraca kandydata z pustym, niezaufanym słownikiem. T11: niepoprawna wartość typu `str` również daje `{}` w kandydacie. T12: poprawny dict jest równy wartościowo i ma odrębną zewnętrzną tożsamość; mutacja kopii nie zmienia oryginału. Brak pola nie oznacza PASS.

## POSITIONAL CONSTRUCTOR CONTRACT

DIRECT_EVIDENCE T09: `RepositoryAnalysisState(modules, artifacts)` nadal przypisuje argument drugi do `artifacts`, a `typing_guard_evidence` inicjalizuje jako `{}`. To weryfikuje kontrakt zgodności pozycyjnej bez zmiany kolejności pól.

## TARGETED TESTS

CPython 3.15.2 w `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. Uruchomiono wyłącznie T09–T12 oraz T05–T08: `8 passed, 228 deselected` w 7.83 s. Polecenie: `pytest -q tests/test_p1d3_d2b2_type_only.py -k 'sp_t4_i1c_t09 or sp_t4_i1c_t10 or sp_t4_i1c_t11 or sp_t4_i1c_t12 or sp_t4_i1_t05 or sp_t4_i1_t06 or sp_t4_i1_t07 or sp_t4_i1_t08'`. `git diff --check` bez błędów whitespace. Nie uruchomiono pełnego pytest.

## MCP POST-CHANGE AUDIT

DIRECT_EVIDENCE: `get_live_events(after_revision=1413)` wykazał `desktop_watcher` `UPDATED` dla `state_manager.py` w revision 1414, continuity=continuous i resync_required=false. Następny odczyt MCP `get_project_architecture(fields=[])`: LIVE revision **1415**, canonical_state fresh, resync_required=false, syntax_errors=0/fresh, hard cycles=16 deduplikowanych ścieżek DFS/fresh, soft-dependent potential SCC=1/fresh, cycle_semantics stale. `get_module_context` dla czterech modułów SP-T4-I1 (`indexer`, `state_manager`, `facade`, `incremental.engine`) zwrócił revision 1415 i `workspace_sync=verified` dla każdego. Odczytowe metadata kanonicznego snapshotu na dysku: repo_id `ctx_8efc50d8`, state_id `20261113_150814`, revision 1415. `get_project_architecture` nie expose state_id, więc state_id jest dowodem z metadanych dyskowych, nie z tego MCP response. Zgodny revision i workspace_sync nie są atestacją loaded-code backendu. `PENDING_LIVE_SYNC=NO` w zakresie synchronizacji źródła czterech modułów.

## FINAL_VERDICT

`I1C_PASS`: oba literalne kontrakty i osiem wskazanych testów przeszły. Status LIVE osobno: revision 1415, wszystkie cztery moduły `workspace_sync=verified`, bez potwierdzenia adopcji loaded-code przez proces MCP/LIVE.

## FILES_CHANGED

- `contextor/core/analysis/state_manager.py`
- `tests/test_p1d3_d2b2_type_only.py`
- `walkthrough.md` — tylko raport, bez własnego diffu zgodnie z AGENTS.md pkt 10.

`issues.md`, `audyt.txt`, Spiral Prophet i inne pliki produkcyjne/testowe: bez zmian.

## FULL_DIFFS

Pełny rzeczywisty diff plików zmienionych w SP-T4-I1C:

```diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 0e66e48..b0a5e61 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -87,7 +87,10 @@ class AnalysisResult:
 class RepositoryAnalysisState:
     """Canonical runtime state of the repository analysis."""
     modules: Dict[str, Any] = field(default_factory=dict)
-    typing_guard_evidence: dict[str, object] = field(default_factory=dict)
+    typing_guard_evidence: dict[str, object] = field(
+        default_factory=dict,
+        kw_only=True,
+    )
     artifacts: Dict[str, Any] = field(default_factory=dict)
     reexport_facts_by_module: Dict[str, Dict[str, Any]] = field(default_factory=dict)
     dependency_graph: Optional[Any] = None
@@ -172,6 +175,14 @@ class RepositoryAnalysisState:
         candidate.cycle_optional_source_publication = None
 
         for state_field in fields(self):
+            if state_field.name == "typing_guard_evidence":
+                evidence = getattr(self, "typing_guard_evidence", None)
+                candidate.typing_guard_evidence = (
+                    copy.copy(evidence)
+                    if type(evidence) is dict
+                    else {}
+                )
+                continue
             value = getattr(
                 self,
                 state_field.name,
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 38eb3eb..44d610a 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -5,6 +5,7 @@ from __future__ import annotations
 import ast
 import importlib.util
 import json
+import pickle
 import py_compile
 import subprocess
 import sys
@@ -15,7 +16,7 @@ from pathlib import Path
 import pytest
 
 from contextor.core.analysis.cache_manager import CacheManager
-from contextor.core.analysis.state_manager import load_engine_state
+from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state.hydration import hydrate_repository_engine
 from contextor.core.live_state.store import read_metadata
@@ -2764,3 +2765,37 @@ def test_sp_t4_i1_t08_rejected_transaction_preserves_evidence(
     assert engine.state.dependency_graph is graph_before
     assert "new_module" not in engine.state.modules
 
+
+def test_sp_t4_i1c_t09_positional_constructor():
+    modules = {"sample": object()}
+    artifacts = {"sample": {}}
+    state = RepositoryAnalysisState(modules, artifacts)
+    assert state.modules is modules
+    assert state.artifacts is artifacts
+    assert state.typing_guard_evidence == {}
+
+
+def test_sp_t4_i1c_t10_legacy_missing_field_roundtrip():
+    state = RepositoryAnalysisState()
+    del state.typing_guard_evidence
+    restored = pickle.loads(pickle.dumps(state))
+    assert "typing_guard_evidence" not in restored.__dict__
+    candidate = restored.clone_for_update()
+    assert candidate.typing_guard_evidence == {}
+
+
+def test_sp_t4_i1c_t11_malformed_evidence():
+    state = RepositoryAnalysisState(typing_guard_evidence="invalid")
+    candidate = state.clone_for_update()
+    assert candidate.typing_guard_evidence == {}
+
+
+def test_sp_t4_i1c_t12_valid_evidence_copy():
+    evidence = {"schema_version": 1, "global_policy_satisfied": True}
+    state = RepositoryAnalysisState(typing_guard_evidence=evidence)
+    candidate = state.clone_for_update()
+    assert candidate.typing_guard_evidence == evidence
+    assert candidate.typing_guard_evidence is not state.typing_guard_evidence
+    candidate.typing_guard_evidence["global_policy_satisfied"] = False
+    assert state.typing_guard_evidence["global_policy_satisfied"] is True
+
```
