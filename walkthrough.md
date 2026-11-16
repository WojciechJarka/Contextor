# SP-T4-I1 — persisted TYPE_ONLY safety evidence

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(fields=[])` przed zmianami: Contextor revision 1406, provenance `live`, canonical_state `fresh`, workspace_sync `unverified`; module/graph/lineage `fresh`, cycle_semantics `stale`. MCP `get_module_context` dla `contextor.core.symbol_engine.indexer`, `contextor.core.analysis.state_manager`, `contextor.core.api.facade`, `contextor.core.analysis.incremental.engine`: revision 1406 i `workspace_sync=verified` dla każdego. HEAD `47a428f61579daa71f02a2087e33fe531a9fa51c`; istniejący status `M issues.md`, `M walkthrough.md`. Przed edycją potwierdzono oba konstruktory `RepositoryIndex` (`indexer.py:2802,3055` w stanie przed zmianą), konstruktor stanu FULL (`facade.py:1289`) i dwa commity przyrostowe (`engine.py:240-327,913-1208`). Planowany zakres: wyłącznie cztery wskazane moduły produkcyjne, `tests/test_p1d3_d2b2_type_only.py`, raport. `issues.md` zachowano.

## EXACT IMPLEMENTATION

W `RepositoryIndex` dodano `typing_guard_evidence: dict[str, object]` z `default_factory=dict`. `index_repository` kopiuje istniejące mapy/fakty do słownika dowodowego po dotychczasowej finalizacji, zarówno inline, jak i process pool. Wspólny istniejący warunek globalny jest zapisany w `global_policy_satisfied`; warunek `parents_proved` i wszystkie jego bramki pozostają. `RepositoryAnalysisState` ma pole serializowane przez istniejący snapshot; FULL przekazuje kopię z indeksu. `IncrementalAnalysisEngine` zeruje dowód przy rzeczywistym commicie stanu lub diagnostyki składni. Wczesne wyjścia bez zapisu nie zostały zmienione. Nie zmieniono `typing_guard.py`, `graph.py`, statusów update, planu refresh ani semantyki hard/soft.

## EVIDENCE SCHEMA

CONTRACT_PROVED i test T01: `schema_version=1`; deterministyczne kopie `source_fingerprints_by_module`, `initializer_passivity_by_module`, `marker_mutation_by_module`, `opaque_effects_by_module`; sortowana repo-relative tuple `skipped_source_paths`; istniejące booleans `unindexed_python_sources_present`, `unindexed_import_artifacts_present`, `global_policy_satisfied`. Mapy marker/opaque mają wpis dla każdego indeksowanego modułu i odpowiadające fingerprinty. Mapa initializer passivity z natury obejmuje tylko moduły `__init__.py`; test sprawdza istniejący `pkg.__init__`. T02 potwierdza `global_policy_satisfied=False` dla lokalnego `typing.py`; T03 to samo dla `broken.py` oraz `skipped_source_paths=('broken.py',)`. T04 potwierdza równość całego słownika dla inline/process pool. `global_policy_satisfied` opisuje globalne bramki FULL, nie indywidualny `parents_proved`. Pusty słownik i brak pola w historycznym snapshotcie nie stanowią PASS; nie wprowadzono interpretacji historycznych obiektów jako dowodu.

## SNAPSHOT ROUNDTRIP

DIRECT_EVIDENCE T05: `ContextorFacade.analyze_project` wykonał FULL tylko na repo syntetycznym; `read_metadata`/`load_engine_state` odczytały zapisany stan z kontrolą repo_id/root_path. `typing_guard_evidence` w zapisanym i zhydratowanym `RepositoryAnalysisState` jest równe dowodowi indeksu tej samej treści. Nie wykonywano FULL rzeczywistych repozytoriów.

## INCREMENTAL INVALIDATION

DIRECT_EVIDENCE T06: rzeczywisty `UPDATED` dla nieszkodliwej zmiany `pkg/c.py` usuwa dowód, zachowuje dotychczasowe `pkg.a` ImportRef.type_only oraz hard/soft grafu. T07: `SYNTAX_ERROR` nowego `broken.py` usuwa dowód i oznacza parse stale bez nowego graph commit; obiekt grafu pozostaje ten sam. T08: wymuszona odmowa w produkcyjnej transakcji rejestru pozostawia dowód, graf i listę modułów stanu bez częściowej zmiany. To test atomowej granicy, nie mock finalizacji lub resolvera.

## TARGETED TESTS

CPython 3.15.2, `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. Pierwszy ukierunkowany przebieg: 7 passed, 1 failed (T01 błędnie założył, że mapa parent passivity obejmuje każdy moduł; źródłowy kontrakt obejmuje inicjalizatory). Po korekcie samej asercji: `13 passed, 219 deselected` w 9.83 s, przez `pytest -q tests/test_p1d3_d2b2_type_only.py -k 'sp_t4_i1_t0 or cold_and_warm_worker_cache_match_type_only_graph or test_inline_and_process_pool_classification_parity or test_inline_and_process_pool_typing_shadow_veto_parity or test_d2b2_r2_parent_source_fingerprint_change_reclassifies_child'`. Obejmuje T01–T08 i pięć istniejących przypadków cold/warm, shadow, process pool, parent fingerprint. `git diff --check` bez błędów whitespace. Pełnego pytest nie uruchomiono.

## MCP POST-CHANGE AUDIT

DIRECT_EVIDENCE: MCP `get_project_architecture(fields=[])` po zmianach: revision 1408, syntax_errors=0/fresh, 16 deduplikowanych DFS paths cykli hard/fresh, 1 potencjalny soft-dependent SCC/fresh; cycle_semantics nadal stale. MCP `get_module_context`: `indexer` i `state_manager` mają `workspace_sync=verified` w revision 1408; `facade` i `incremental.engine` mają `workspace_sync=out_of_sync` w revision 1408, advisory „Target file on disk has been modified since canonical state revision was generated.” Ponowny odczyt tych dwóch nadal zwrócił out_of_sync. Nie wywołano MCP update_file, FULL ani restartu. Stary lub częściowo odświeżony backend nie jest atestacją adopcji kodu; brak świeżego MCP dla dwóch zmienionych modułów blokuje certyfikację FINAL PASS.

## FINAL_VERDICT

`I1_FAIL` jako certyfikacja końcowa z powodu niepotwierdzonego `workspace_sync` dla `facade` i `incremental.engine` po zmianie. Lokalny kontrakt i 13 testów ukierunkowanych przeszły; brak świeżego LIVE dla dwóch modułów nie jest sam w sobie dowodem błędu implementacji. Nie zmieniono klasyfikacji ani grafu w badanych testach. Nie zgłoszono adopcji nowego kodu przez backend runtime.

## FILES_CHANGED

- `contextor/core/symbol_engine/indexer.py`
- `contextor/core/analysis/state_manager.py`
- `contextor/core/api/facade.py`
- `contextor/core/analysis/incremental/engine.py`
- `tests/test_p1d3_d2b2_type_only.py`
- `walkthrough.md` — raport, bez własnego diffu zgodnie z AGENTS.md pkt 10.

`issues.md` był zmodyfikowany przed SP-T4-I1 i pozostał nietknięty. Nie zmieniono `audyt.txt` ani Spiral Prophet.

## FULL_DIFFS

Poniżej pełny rzeczywisty diff plików zmienionych przez SP-T4-I1; diff raportu wyłączony.

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 2992e32..ad9c5f1 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -313,6 +313,7 @@ class IncrementalAnalysisEngine:
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
         self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
         self.state.module_parse_freshness = candidate.module_parse_freshness
+        self.state.typing_guard_evidence = {}
         self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
         self.state.lineage_facts_state = candidate.lineage_facts_state
         self.state.lineage_facts_semantic_version = (
@@ -1127,6 +1128,7 @@ class IncrementalAnalysisEngine:
         if clear_parse_module is not None:
             clear_module_parse_failure(candidate, clear_parse_module)
         self.state.modules = candidate.modules
+        self.state.typing_guard_evidence = {}
         self.state.reexport_facts_by_module = (
             candidate.reexport_facts_by_module
         )
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 34f33b9..0e66e48 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -87,6 +87,7 @@ class AnalysisResult:
 class RepositoryAnalysisState:
     """Canonical runtime state of the repository analysis."""
     modules: Dict[str, Any] = field(default_factory=dict)
+    typing_guard_evidence: dict[str, object] = field(default_factory=dict)
     artifacts: Dict[str, Any] = field(default_factory=dict)
     reexport_facts_by_module: Dict[str, Dict[str, Any]] = field(default_factory=dict)
     dependency_graph: Optional[Any] = None
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 882c00c..aa5eaaf 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1288,6 +1288,7 @@ class ContextorFacade:
                 )
             state = RepositoryAnalysisState(
                 modules=mods,
+                typing_guard_evidence=dict(index.typing_guard_evidence),
                 artifacts=raw_artifacts,
                 reexport_facts_by_module=canonical_reexport_facts,
                 dependency_graph=graph,
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 1939550..97677f7 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -1560,6 +1560,8 @@ class RepositoryIndex:
         dataclasses.field(default_factory=dict)
     )
 
+    typing_guard_evidence: dict[str, object] = dataclasses.field(default_factory=dict)
+
     # Optional original worker-read evidence. Not a publication receipt,
     # generation binding, or cross-file atomic source snapshot.
     original_worker_source_snapshots: dict[str, SourceSnapshot] = (
@@ -2625,7 +2627,23 @@ def index_repository(
 
     completed = 0
 
+    global_policy_satisfied = False
+
+    def typing_guard_evidence() -> dict[str, object]:
+        return {
+            "schema_version": 1,
+            "source_fingerprints_by_module": dict(sorted(source_fingerprints_by_module.items())),
+            "initializer_passivity_by_module": dict(sorted(initializer_passivity_by_module.items())),
+            "marker_mutation_by_module": dict(sorted(marker_mutation_by_module.items())),
+            "opaque_effects_by_module": dict(sorted(opaque_effects_by_module.items())),
+            "skipped_source_paths": tuple(sorted(item.path for item in skipped)),
+            "unindexed_python_sources_present": unindexed_python_sources_present,
+            "unindexed_import_artifacts_present": unindexed_import_artifacts_present,
+            "global_policy_satisfied": global_policy_satisfied,
+        }
+
     def _finalize_type_only_imports() -> None:
+        nonlocal global_policy_satisfied
         typing_shadowed = (
             "typing" in modules
             or "typing.__init__" in modules
@@ -2690,6 +2708,12 @@ def index_repository(
             )
         )
 
+        global_policy_satisfied = (
+            not typing_shadowed
+            and project_marker_safe
+            and project_effects_closed
+        )
+
         for module_id, module in modules.items():
             if not any(
                 import_ref.type_only
@@ -2725,12 +2749,7 @@ def index_repository(
                 )
             )
 
-            if (
-                not typing_shadowed
-                and parents_proved
-                and project_marker_safe
-                and project_effects_closed
-            ):
+            if global_policy_satisfied and parents_proved:
                 continue
 
             modules[module_id] = dataclasses.replace(
@@ -2813,6 +2832,7 @@ def index_repository(
                     source_fingerprints_by_module.items()
                 )
             ),
+            typing_guard_evidence=typing_guard_evidence(),
             **capture_result_fields(),
         )
 
@@ -3066,6 +3086,7 @@ def index_repository(
                 source_fingerprints_by_module.items()
             )
         ),
+        typing_guard_evidence=typing_guard_evidence(),
         **capture_result_fields(),
     )
 
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 5cdb4cf..38eb3eb 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -15,6 +15,11 @@ from pathlib import Path
 import pytest
 
 from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.analysis.state_manager import load_engine_state
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
 from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
 from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
 from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
@@ -2612,3 +2617,150 @@ def test_d2b2_r2_original_worker_reindex_retains_hard_graph(
     assert captured_graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert captured_graph.hard_edges["pkg.b"] == {"pkg.a"}
 
+
+_I1_SAFE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "pass\n",
+    "pkg/c.py": "pass\n",
+}
+
+
+def _i1_full_engine(root):
+    errors, _ = ContextorFacade.analyze_project(str(root))
+    assert not errors
+    metadata = read_metadata(repo_cache_dir(root))
+    assert metadata is not None
+    persisted = load_engine_state(
+        str(repo_cache_dir(root)), metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    hydrated = hydrate_repository_engine(root)
+    assert hydrated is not None
+    return persisted, hydrated.engine
+
+
+def _i1_guarded_import(state):
+    return next(
+        item for item in state.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    )
+
+
+def test_sp_t4_i1_t01_safe_full_evidence(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    index, graph = _index_graph(root)
+    evidence = index.typing_guard_evidence
+    assert evidence["schema_version"] == 1
+    assert evidence["global_policy_satisfied"] is True
+    assert evidence["skipped_source_paths"] == ()
+    assert evidence["unindexed_python_sources_present"] is False
+    assert evidence["unindexed_import_artifacts_present"] is False
+    fingerprints = evidence["source_fingerprints_by_module"]
+    assert fingerprints == index.source_fingerprints_by_module
+    assert set(fingerprints) == set(index.modules)
+    for key in ("marker_mutation_by_module", "opaque_effects_by_module"):
+        facts = evidence[key]
+        assert set(facts) == set(index.modules)
+        assert all(value == (False, fingerprints[name]) for name, value in facts.items())
+    assert set(evidence["initializer_passivity_by_module"]) == {"pkg.__init__"}
+    assert evidence["initializer_passivity_by_module"]["pkg.__init__"] == (
+        True, fingerprints["pkg.__init__"]
+    )
+    assert _i1_guarded_import(index).type_only is True
+    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
+
+
+def test_sp_t4_i1_t02_shadow_policy_false(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"})
+    index, graph = _index_graph(root)
+    assert index.typing_guard_evidence["global_policy_satisfied"] is False
+    assert "typing" in index.modules
+    assert _i1_guarded_import(index).type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+def test_sp_t4_i1_t03_skipped_policy_false(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"})
+    index, graph = _index_graph(root)
+    assert index.typing_guard_evidence["global_policy_satisfied"] is False
+    assert index.typing_guard_evidence["skipped_source_paths"] == ("broken.py",)
+    assert _i1_guarded_import(index).type_only is False
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+def test_sp_t4_i1_t04_inline_pool_evidence_parity(tmp_path, isolated_dirs, monkeypatch):
+    inline_root = write_synthetic_repository(tmp_path / "inline", _I1_SAFE)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline, _ = _index_graph(inline_root)
+    pool_root = write_synthetic_repository(tmp_path / "pool", _I1_SAFE)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pooled, _ = _index_graph(pool_root)
+    assert pooled.typing_guard_evidence == inline.typing_guard_evidence
+
+
+def test_sp_t4_i1_t05_snapshot_roundtrip(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    index, _ = _index_graph(root)
+    persisted, engine = _i1_full_engine(root)
+    assert persisted.typing_guard_evidence == index.typing_guard_evidence
+    assert engine.state.typing_guard_evidence == index.typing_guard_evidence
+
+
+def test_sp_t4_i1_t06_updated_invalidates_evidence(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    persisted, engine = _i1_full_engine(root)
+    assert persisted.typing_guard_evidence["global_policy_satisfied"] is True
+    before_import = _i1_guarded_import(engine.state)
+    before_hard = dict(engine.state.dependency_graph.hard_edges)
+    before_soft = dict(engine.state.dependency_graph.soft_edges)
+    target = root / "pkg/c.py"
+    target.write_text("pass\nVALUE = 2\n", encoding="utf-8")
+    result = engine.update_file(str(target.resolve()))
+    assert result.status == "UPDATED"
+    assert engine.state.typing_guard_evidence == {}
+    assert _i1_guarded_import(engine.state).type_only == before_import.type_only
+    assert engine.state.dependency_graph.hard_edges == before_hard
+    assert engine.state.dependency_graph.soft_edges == before_soft
+
+
+def test_sp_t4_i1_t07_syntax_error_invalidates_evidence(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    persisted, engine = _i1_full_engine(root)
+    assert persisted.typing_guard_evidence["global_policy_satisfied"] is True
+    before_graph = engine.state.dependency_graph
+    target = root / "broken.py"
+    target.write_text("def invalid(:\n", encoding="utf-8")
+    result = engine.update_file(str(target.resolve()))
+    assert result.status == "SYNTAX_ERROR"
+    assert engine.state.typing_guard_evidence == {}
+    assert engine.state.dependency_graph is before_graph
+    assert engine.state.module_parse_freshness["broken"]["state"] == "stale"
+
+
+def test_sp_t4_i1_t08_rejected_transaction_preserves_evidence(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    _, engine = _i1_full_engine(root)
+    evidence_before = dict(engine.state.typing_guard_evidence)
+    graph_before = engine.state.dependency_graph
+    target = root / "new_module.py"
+    target.write_text("pass\n", encoding="utf-8")
+
+    def reject(*args, **kwargs):
+        raise RuntimeError("I1 transaction rejection witness")
+
+    monkeypatch.setattr(engine.registry, "sync_with_workspace", reject)
+    with pytest.raises(RuntimeError, match="I1 transaction rejection witness"):
+        engine.update_file(str(target.resolve()))
+    assert engine.state.typing_guard_evidence == evidence_before
+    assert engine.state.dependency_graph is graph_before
+    assert "new_module" not in engine.state.modules
+
```
