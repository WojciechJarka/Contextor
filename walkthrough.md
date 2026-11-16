# SP-T4-I2B2C — lossless existing ImportRef candidates

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first: `get_project_architecture(fields=[])` przed zmianą pokazał revision 1420, canonical_state=fresh, resync_required=false i syntax_errors=0/fresh. `get_module_context` dla `contextor.core.symbol_engine.indexer` oraz `tests.test_p1d3_d2b2_type_only` potwierdził revision 1420 i `workspace_sync=verified`. Git HEAD `87e1c9637f63488895cf1de491fd0077258d1dad`; status przed zmianą: istniejące `M walkthrough.md` po raporcie poprzedniego etapu. Anchory: `indexer.py:2630-2645` (evidence helper i wejście finalizatora); T01 w `tests/test_p1d3_d2b2_type_only.py:2662-2684`. Planowany diff wyłącznie `indexer.py`, schema assertion w T01 i nowe T22–T27 w pliku testowym, oraz raport.

## EXACT IMPLEMENTATION

Przed `_finalize_type_only_imports` utworzono `candidate_imports_by_module={}`. Na samym początku finalizatora, przed sprawdzeniem i zmianą polityki, każdy moduł zawierający co najmniej jeden `ImportRef.type_only=True` zapisuje wszystkie swoje istniejące ImportRef w kolejności, jako tuple `dataclasses.replace(ref, names=list(ref.names))`. Zapis zachowuje liczbę rekordów, pełne istniejące pola ImportRef i niezależne listy `names`. Nie parsuje ponownie AST ani plików i nie wpływa na finalizację. Evidence ma schema_version=2 i deterministycznie sortowaną mapę kandydatów. Oba istniejące zakończenia indexer wywołują tę samą funkcję evidence po finalizacji.

## CANDIDATE CAPTURE

T22: dla bezpiecznego FULL kandydat i finalny ImportRef są równe, zachowują kolejność i pola, a listy `names` są odrębnymi obiektami; końcowa krawędź pozostaje soft. T23: przy lokalnym `typing.py` końcowy `pkg.b.type_only=False`/hard, natomiast zapisany kandydat zachowuje `True`. T24: przy błędnym pominiętym Pythonie ten sam kandydat pozostaje `True`, finalny import jest `False` i hard. T25 używa dwóch wariantów zwykłego aliasowanego importu AST (`import pkg.c as helper` oraz `from pkg.d import Symbol as Alias`), obok markera i chronionego importu. Zapisane trzy ImportRef zgadzają się rekord po rekordzie, w kolejności, z `read_imports` na tych samych źródłach; wszystkie istniejące pola i `names` są równe, a listy `names` niezależne. Alias AST nie jest częścią ImportRef i nie jest asertywnie rekonstruowany.

## EVIDENCE SCHEMA V2

T01 oczekuje teraz schema_version=2 dla projektowego `typing_guard_evidence`. T13 z I2A nadal oczekuje schema_version=1 dla odrębnego `typing_guard_source_evidence`; tej asercji nie zmieniono. Pozostałe pola evidence pozostają bez zmian. T27 potwierdza równość pełnego schema v2 dla inline/process-pool indeksowania identycznych źródeł.

## IMPORTREF SCOPE

CONTRACT_PROVED: `ImportRef` zawiera `module`, `level`, `names`, `is_from_import`, `is_local`, `type_only`, `is_lazy`. Testy porównują każdy rekord całym dataclass equality, zachowują kolejność i sprawdzają osobne listy `names`. Nie przypisują ImportRef nieistniejącego pola `asname`; alias nie jest częścią tego kontraktu.

## LEGACY COMPATIBILITY

Nie dodano odtwarzania syntaktycznej kandydatury dla starego evidence bez pola, schema_version=1 ani mapy candidate. Implementacja kopiuje wyłącznie fakty istniejące w bieżącym indeksowaniu przed finalizacją; nie rekonstruuje kandydatur z końcowego `type_only=False`. Nie zmieniano RepositoryIndex, RepositoryAnalysisState, facade, clone_for_update ani konstruktora API.

## SNAPSHOT ROUNDTRIP

T26 wykonał syntetyczny FULL z `typing.py`, sprawdził końcowe `type_only=False` i zachowaną flagę kandydata `True`, a następnie porównał całe evidence po `load_engine_state` i hydration z evidence tego samego indeksu. Snapshot zachował candidate_imports_by_module.

## TARGETED TESTS

CPython 3.15.2, `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. Uruchomiono tylko T22–T27, T01–T05 oraz T09–T12: `16 passed, 240 deselected` w 6.98 s. `git diff --check` bez błędów whitespace. Nie uruchomiono pełnego pytest.

## MCP POST-CHANGE AUDIT

DIRECT_EVIDENCE: po zmianie Contextor MCP revision **1422**. `get_module_context` dla `indexer` i test module: revision 1422, `workspace_sync=verified`. `get_project_architecture(fields=[])`: canonical_state=fresh, resync_required=false, syntax_errors=0/fresh, 16 hard structural DFS paths/fresh, 1 soft-dependent potential SCC/fresh; cycle_semantics stale. Rodziny module/graph/cycles fresh. Odczyt graph dla indexer zgłosił 63 inbound i 15 outbound module dependencies; próba pełnego wyjścia `get_module_context(compact=false)` zatrzymała się na `confirmation_required` z oszacowaniem 17.1 KiB, więc nie traktuję tego jako potwierdzenia wszystkich krawędzi per-moduł. Nie wykonano FULL rzeczywistego Contextora, MCP update_file, SCC02 ani restartu.

## FINAL_VERDICT

`I2B2C_PASS`: zachowano istniejące kandydackie ImportRef przed finalizacją, schema v2 i snapshot roundtrip; wskazane testy przeszły. Werdykt dotyczy kontraktu ImportRef, nie pełnego AST alias provenance.

## FILES_CHANGED

- `contextor/core/symbol_engine/indexer.py`
- `tests/test_p1d3_d2b2_type_only.py`
- `walkthrough.md` — raport, bez własnego diffu zgodnie z AGENTS.md pkt 10.

Nie zmieniono pozostałych modułów, `issues.md`, `audyt.txt` ani Spiral Prophet.

## FULL_DIFFS

Pełny rzeczywisty diff plików zmienionych w SP-T4-I2B2C:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 97677f7..2c5aa93 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -2628,10 +2628,14 @@ def index_repository(
     completed = 0
 
     global_policy_satisfied = False
+    candidate_imports_by_module = {}
 
     def typing_guard_evidence() -> dict[str, object]:
         return {
-            "schema_version": 1,
+            "schema_version": 2,
+            "candidate_imports_by_module": dict(
+                sorted(candidate_imports_by_module.items())
+            ),
             "source_fingerprints_by_module": dict(sorted(source_fingerprints_by_module.items())),
             "initializer_passivity_by_module": dict(sorted(initializer_passivity_by_module.items())),
             "marker_mutation_by_module": dict(sorted(marker_mutation_by_module.items())),
@@ -2644,6 +2648,20 @@ def index_repository(
 
     def _finalize_type_only_imports() -> None:
         nonlocal global_policy_satisfied
+        for module_id, module in modules.items():
+            if not any(
+                ref.type_only for ref in module.imports
+            ):
+                continue
+
+            candidate_imports_by_module[module_id] = tuple(
+                dataclasses.replace(
+                    ref,
+                    names=list(ref.names),
+                )
+                for ref in module.imports
+            )
+
         typing_shadowed = (
             "typing" in modules
             or "typing.__init__" in modules
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index eec3654..81827c6 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -2663,7 +2663,7 @@ def test_sp_t4_i1_t01_safe_full_evidence(tmp_path, isolated_dirs):
     root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
     index, graph = _index_graph(root)
     evidence = index.typing_guard_evidence
-    assert evidence["schema_version"] == 1
+    assert evidence["schema_version"] == 2
     assert evidence["global_policy_satisfied"] is True
     assert evidence["skipped_source_paths"] == ()
     assert evidence["unindexed_python_sources_present"] is False
@@ -3030,3 +3030,132 @@ def test_sp_t4_i2b1_t21_identical_import_ref_no_graph_plan():
     assert "dependency_graph" not in plan.patch_families
     assert plan.graph_recomputations == ()
 
+
+def _i2b2_candidates(index, module_id="pkg.a"):
+    evidence = index.typing_guard_evidence
+    assert evidence["schema_version"] == 2
+    return evidence["candidate_imports_by_module"][module_id]
+
+
+def test_sp_t4_i2b2c_t22_safe_full_candidate_matches_final_imports(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    index, graph = _index_graph(root)
+    candidate = _i2b2_candidates(index)
+    final_imports = index.modules["pkg.a"].imports
+    assert _i1_guarded_import(index).type_only is True
+    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
+    assert candidate == tuple(final_imports)
+    for before, after in zip(candidate, final_imports):
+        assert before == after
+        assert before.names is not after.names
+
+
+def test_sp_t4_i2b2c_t23_shadow_keeps_pre_finalization_candidate(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
+    )
+    index, graph = _index_graph(root)
+    candidate = _i2b2_candidates(index)
+    final_import = _i1_guarded_import(index)
+    saved_import = next(ref for ref in candidate if ref.module == "pkg.b")
+    assert final_import.type_only is False
+    assert saved_import.type_only is True
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+def test_sp_t4_i2b2c_t24_skipped_keeps_pre_finalization_candidate(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"},
+    )
+    index, graph = _index_graph(root)
+    candidate = _i2b2_candidates(index)
+    final_import = _i1_guarded_import(index)
+    saved_import = next(ref for ref in candidate if ref.module == "pkg.b")
+    assert final_import.type_only is False
+    assert saved_import.type_only is True
+    assert index.typing_guard_evidence["skipped_source_paths"] == ("broken.py",)
+    assert "pkg.b" in graph.hard_edges["pkg.a"]
+
+
+@pytest.mark.parametrize(
+    "ordinary_import",
+    [
+        "import pkg.c as helper\n",
+        "from pkg.d import Symbol as Alias\n",
+    ],
+    ids=["import-alias-not-in-importref", "from-alias-not-in-importref"],
+)
+def test_sp_t4_i2b2c_t25_all_existing_importrefs_in_order(
+    tmp_path, isolated_dirs, ordinary_import,
+):
+    fixture = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": (
+            "from typing import TYPE_CHECKING\n"
+            "if TYPE_CHECKING:\n"
+            "    import pkg.b\n"
+            + ordinary_import
+        ),
+        "pkg/b.py": "pass\n",
+        "pkg/c.py": "pass\n",
+        "pkg/d.py": "pass\n",
+    }
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, _ = _index_graph(root)
+    candidate = _i2b2_candidates(index)
+    extracted, error = indexer.read_imports(root / "pkg/a.py")
+    assert error is None
+    assert len(candidate) == len(extracted) == 3
+    assert candidate == tuple(extracted)
+    assert [ref.module for ref in candidate] == [
+        ref.module for ref in extracted
+    ]
+    for captured, parsed in zip(candidate, extracted):
+        assert captured == parsed
+        assert captured.names == parsed.names
+        assert captured.names is not parsed.names
+    final_imports = index.modules["pkg.a"].imports
+    assert len(final_imports) == 3
+    assert [ref.module for ref in candidate] == [
+        "typing", "pkg.b",
+        "pkg.c" if ordinary_import.startswith("import") else "pkg.d",
+    ]
+    assert all(
+        captured.names is not final.names
+        for captured, final in zip(candidate, final_imports)
+    )
+
+
+def test_sp_t4_i2b2c_t26_snapshot_roundtrip_keeps_rejected_candidates(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
+    )
+    index, _ = _index_graph(root)
+    persisted, engine = _i1_full_engine(root)
+    candidate = _i2b2_candidates(index)
+    assert _i1_guarded_import(index).type_only is False
+    assert next(ref for ref in candidate if ref.module == "pkg.b").type_only is True
+    assert persisted.typing_guard_evidence == index.typing_guard_evidence
+    assert engine.state.typing_guard_evidence == index.typing_guard_evidence
+
+
+def test_sp_t4_i2b2c_t27_inline_process_pool_evidence_parity(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    inline_root = write_synthetic_repository(tmp_path / "inline", _I1_SAFE)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline, _ = _index_graph(inline_root)
+    pool_root = write_synthetic_repository(tmp_path / "pool", _I1_SAFE)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pooled, _ = _index_graph(pool_root)
+    assert inline.typing_guard_evidence["schema_version"] == 2
+    assert pooled.typing_guard_evidence == inline.typing_guard_evidence
+
```
