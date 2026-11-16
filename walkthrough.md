# SP-T4-I2A — incremental TYPE_ONLY source evidence

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first: `get_project_architecture(fields=[])` dla Contextora: LIVE revision 1415, canonical_state fresh, resync_required=false, module/graph/lineage fresh, cycle_semantics stale. `get_module_context` dla `contextor.core.analysis.incremental.preparation`, `contextor.core.symbol_engine.indexer`, `contextor.core.cycle_semantics.typing_guard`, `tests.test_p1d3_d2b2_type_only`: revision 1415 i `workspace_sync=verified` dla wszystkich. Git HEAD `ffd65ea2a2ac69f3271921c354b1bdc3b5bc94d6`, status czysty. Anchory przed edycją: `PreparedSourceUpdate` w `preparation.py:25-47`, `prepare_source_update` w `:147-332`, udane `read_imports` w `:229-262`, końcowy konstruktor w `:318-333`; predykaty FULL w `indexer.py:320-645,1142-1158` i passivity w `typing_guard.py:313`. Zaplanowano diff tylko w `preparation.py`, `tests/test_p1d3_d2b2_type_only.py` i raporcie.

## EXACT IMPLEMENTATION

W `PreparedSourceUpdate` dodano końcowe, keyword-only `typing_guard_source_evidence: dict[str, object] | None` z `default=None`. Po udanym `read_imports` nowy słownik powstaje z istniejącego `parsed_tree` oraz `parsed_input.source_fingerprint`, przy użyciu tych samych trzech predykatów co FULL. Pole trafia wyłącznie do końcowego udanego konstruktora; wcześniejsze ścieżki błędu zachowują `None`. Nie zmieniono istniejących call sites, pól FileDelta, planowania RefreshPlan, grafu, finalizacji type_only ani definicji predykatów.

## SOURCE EVIDENCE

CONTRACT_PROVED: słownik zawiera dokładnie `schema_version=1`, `source_fingerprint`, `initializer_passive`, `marker_mutation`, `opaque_effects`. `initializer_passive` jest sprawdzane tylko dla nazwy modułu kończącej się `.__init__`. T13 potwierdza bezpieczny moduł: SHA-256 identyczny z bajtami źródła, marker_mutation=False, opaque_effects=False. T14 potwierdza mutację `typing.TYPE_CHECKING=True` oraz zgodność z mapą predykatu w syntetycznym FULL. T15 potwierdza pasywny i niepasywny initializer. T16: zmiana `if TYPE_CHECKING` na `if True` daje nowy fingerprint i `ImportRef.type_only` z True na False przy tych samych nazwach importów; `FileDelta.imports_added` pozostaje równe. To fakty przygotowania, bez twierdzenia o końcowej klasyfikacji/opublikowaniu incremental.

## AST REUSE

CODE_PATH_PROVED: `parse_source_with_fingerprint` jest wołane raz w udanej ścieżce (`preparation.py:167`); to samo `parsed_tree` przechodzi do `read_imports`, predykatów, symboli, kolizji i usage. T13 używa licznika wywołań parsera i przechwytuje argument `tree` w rzeczywistym `read_imports`: dokładnie jedno parsowanie i identyczna instancja AST. Kod produkcyjny nie dodaje odczytu źródła, `ast.parse` ani wykonania analizowanego kodu. Niezależny syntetyczny FULL w T14 jest porównaniem testowym, a nie ponownym parsowaniem wewnątrz `prepare_source_update`.

## TARGETED TESTS

CPython 3.15.2, `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`: wyłącznie T13–T16 oraz T01, T05, T09, T10: `8 passed, 232 deselected` w 3.26 s. Polecenie: `pytest -q tests/test_p1d3_d2b2_type_only.py -k 'sp_t4_i2a_t13 or sp_t4_i2a_t14 or sp_t4_i2a_t15 or sp_t4_i2a_t16 or sp_t4_i1_t01 or sp_t4_i1_t05 or sp_t4_i1c_t09 or sp_t4_i1c_t10'`. `git diff --check` bez błędów whitespace. Nie uruchomiono pełnego pytest.

## MCP POST-CHANGE AUDIT

DIRECT_EVIDENCE: MCP `get_project_architecture(fields=[])` po zmianach: LIVE revision 1417, resync_required=false, syntax_errors=0/fresh, hard cycles=16 deduplikowanych DFS paths/fresh, soft-dependent potential SCC=1/fresh; cycle_semantics stale. `get_module_context` w revision 1416: preparation/indexer/typing_guard `workspace_sync=verified`, test file początkowo `out_of_sync`; ponowny odczyt test file w revision 1417 `workspace_sync=verified`. Nie wywołano FULL rzeczywistego repo, MCP update_file, SCC02 ani restartu. LIVE revision i synchronizacja źródła nie są atestacją loaded-code backendu. Brak zmiany liczby cykli jest obserwacją odczytową, nie dowodem ogólnej semantyki grafu.

## FINAL_VERDICT

`I2A_PASS` dla literalnego przekazania source evidence i wskazanych testów. Dotyczy wyniku lokalnego kodu oraz odczytowej zgodności źródeł LIVE; adopcja nowego kodu przez proces backendu pozostaje nieatestowana.

## FILES_CHANGED

- `contextor/core/analysis/incremental/preparation.py`
- `tests/test_p1d3_d2b2_type_only.py`
- `walkthrough.md` — raport, bez własnego diffu zgodnie z AGENTS.md pkt 10.

Nie zmieniono `indexer.py`, `typing_guard.py`, `issues.md`, `audyt.txt` ani Spiral Prophet.

## FULL_DIFFS

Pełny rzeczywisty diff plików zmienionych w SP-T4-I2A:

```diff
diff --git a/contextor/core/analysis/incremental/preparation.py b/contextor/core/analysis/incremental/preparation.py
index 5287885..438ccc8 100644
--- a/contextor/core/analysis/incremental/preparation.py
+++ b/contextor/core/analysis/incremental/preparation.py
@@ -8,7 +8,7 @@ Source preparation and semantic delta construction for incremental updates:
 - PreparedModuleUpdate contract
 """
 
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Optional, List, Set, Dict, Any, Tuple
 
@@ -39,6 +39,10 @@ class PreparedSourceUpdate:
     error_message: Optional[str] = None
     line_number: Optional[int] = None
     column_number: Optional[int] = None
+    typing_guard_source_evidence: dict[str, object] | None = field(
+        default=None,
+        kw_only=True,
+    )
 
     @property
     def has_error(self) -> bool:
@@ -257,6 +261,29 @@ def prepare_source_update(
             error_message=str(exc),
         )
 
+    from contextor.core.symbol_engine.indexer import (
+        _possible_project_typing_marker_mutation,
+        _project_typing_opaque_effects,
+    )
+    from contextor.core.cycle_semantics.typing_guard import (
+        _typing_guard_passive_initializer,
+    )
+
+    typing_guard_source_evidence = {
+        "schema_version": 1,
+        "source_fingerprint": parsed_input.source_fingerprint,
+        "initializer_passive": (
+            module_path.endswith(".__init__")
+            and _typing_guard_passive_initializer(parsed_tree)
+        ),
+        "marker_mutation": (
+            _possible_project_typing_marker_mutation(parsed_tree)
+        ),
+        "opaque_effects": (
+            _project_typing_opaque_effects(parsed_tree)
+        ),
+    }
+
     # 3. Extract symbols & artifacts
     try:
         from contextor.core.reporting_layer.artifact_usage_report import (
@@ -327,6 +354,7 @@ def prepare_source_update(
         collision_facts_changed=collision_facts_changed,
         extracted_lineage_facts=extracted_lineage_facts,
         new_reexport_facts=new_reexport_facts,
+        typing_guard_source_evidence=typing_guard_source_evidence,
     )
 
 
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 44d610a..81c074e 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import ast
+import hashlib
 import importlib.util
 import json
 import pickle
@@ -16,6 +17,7 @@ from pathlib import Path
 import pytest
 
 from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.analysis.incremental import preparation
 from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state.hydration import hydrate_repository_engine
@@ -2799,3 +2801,102 @@ def test_sp_t4_i1c_t12_valid_evidence_copy():
     candidate.typing_guard_evidence["global_policy_satisfied"] = False
     assert state.typing_guard_evidence["global_policy_satisfied"] is True
 
+
+def _i2a_prepare(path: Path, module_path: str):
+    return preparation.prepare_source_update(
+        file_path=path,
+        module_path=module_path,
+        is_new=True,
+        old_module=None,
+        old_artifacts=None,
+        old_usage=None,
+    )
+
+
+def test_sp_t4_i2a_t13_safe_source_evidence(tmp_path, monkeypatch):
+    source = (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    )
+    path = tmp_path / "a.py"
+    path.write_text(source, encoding="utf-8")
+    parse_calls = []
+    import_trees = []
+    original_parse = preparation.parse_source_with_fingerprint
+    original_read_imports = indexer.read_imports
+
+    def recorded_parse(file_path):
+        parsed = original_parse(file_path)
+        parse_calls.append(parsed)
+        return parsed
+
+    def recorded_read_imports(file_path, *, tree=None):
+        import_trees.append(tree)
+        return original_read_imports(file_path, tree=tree)
+
+    monkeypatch.setattr(preparation, "parse_source_with_fingerprint", recorded_parse)
+    monkeypatch.setattr(indexer, "read_imports", recorded_read_imports)
+    prepared = _i2a_prepare(path, "pkg.a")
+    assert not prepared.has_error
+    assert len(parse_calls) == 1
+    assert import_trees == [parse_calls[0].tree]
+    evidence = prepared.typing_guard_source_evidence
+    assert evidence["schema_version"] == 1
+    assert evidence["source_fingerprint"] == hashlib.sha256(path.read_bytes()).hexdigest()
+    assert evidence["initializer_passive"] is False
+    assert evidence["marker_mutation"] is False
+    assert evidence["opaque_effects"] is False
+
+
+def test_sp_t4_i2a_t14_marker_mutation_matches_full_predicate(tmp_path):
+    path = tmp_path / "other.py"
+    path.write_text("import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8")
+    prepared = _i2a_prepare(path, "pkg.other")
+    assert not prepared.has_error
+    evidence = prepared.typing_guard_source_evidence
+    assert evidence["marker_mutation"] is True
+    full_index, _ = _index_graph(tmp_path)
+    assert full_index.typing_guard_evidence["marker_mutation_by_module"]["other"][0] is True
+
+
+def test_sp_t4_i2a_t15_initializer_passivity(tmp_path):
+    path = tmp_path / "__init__.py"
+    path.write_text("pass\n", encoding="utf-8")
+    passive = _i2a_prepare(path, "pkg.__init__")
+    assert not passive.has_error
+    assert passive.typing_guard_source_evidence["initializer_passive"] is True
+    path.write_text("import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8")
+    active = _i2a_prepare(path, "pkg.__init__")
+    assert not active.has_error
+    assert active.typing_guard_source_evidence["initializer_passive"] is False
+    assert active.typing_guard_source_evidence["source_fingerprint"] != (
+        passive.typing_guard_source_evidence["source_fingerprint"]
+    )
+
+
+def test_sp_t4_i2a_t16_guard_change_same_import_names(tmp_path):
+    path = tmp_path / "a.py"
+    guarded = (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    )
+    path.write_text(guarded, encoding="utf-8")
+    before = _i2a_prepare(path, "pkg.a")
+    path.write_text(guarded.replace("if TYPE_CHECKING:", "if True:"), encoding="utf-8")
+    after = _i2a_prepare(path, "pkg.a")
+    assert not before.has_error and not after.has_error
+    before_import = next(item for item in before.new_imports if item.module == "pkg.b")
+    after_import = next(item for item in after.new_imports if item.module == "pkg.b")
+    assert before_import.type_only is True
+    assert after_import.type_only is False
+    assert before.delta.imports_added == after.delta.imports_added
+    assert before.typing_guard_source_evidence["source_fingerprint"] != (
+        after.typing_guard_source_evidence["source_fingerprint"]
+    )
+    assert after.typing_guard_source_evidence["marker_mutation"] is False
+    assert after.typing_guard_source_evidence["opaque_effects"] is False
+
```
