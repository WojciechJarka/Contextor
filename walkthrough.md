# SP-R6 — CPython compilability validation

## PREFLIGHT

Contextor MCP FIRST: self snapshot repo_path C:/Temp/Contextor_Repo, revision 1402, provenance=snapshot, aggregate canonical_state=fresh, workspace_sync=unverified, cycle_semantics=stale. Przed zmianą get_module_context dla contextor.core.source i contextor.core.symbol_engine.indexer zwróciło revision 1402 oraz workspace_sync=verified. contextor_fact_lineage(syntax_diagnostics) potwierdziło oddzielne drogi FULL i incremental do kanonicznej diagnostyki i projekcji get_file_edit_context. Spiral Prophet LIVE nie przełączono. Odczytowy HEAD Contextora: 11b59fe4769784b31180bb6982a0594a852545be, status przed zmianą czysty. Dokładne kotwice source.py:95, indexer.py:81,951-982,1406-1422, wskazane testy i cztery wpisy issues.md odpowiadały zadaniu; nie stwierdzono SOURCE_DRIFT.

## ZMIANY IMPLEMENTACJI

- contextor/core/source.py: po jedynym ast.parse w parse_source_snapshot dodano compile(tree, path, "exec", dont_inherit=True, optimize=0) w istniejącym try. Wyjątki SyntaxError, ValueError, RecursionError nadal przechodzą przez SourceError z dotychczasowymi współrzędnymi. Nie ma exec, ponownego odczytu, drugiego AST, kompilacji tekstu ani zapisu .pyc.
- contextor/core/symbol_engine/indexer.py: SOURCE_COMPILABILITY_SEMANTICS_VERSION=1 jest osobnym polem cache. Brak pola, niecałkowity typ lub inna wartość unieważnia cache przed ścieżką zwrotu bez parsowania. Nowa ekstrakcja zapisuje pole. Dotychczasowe wersje faktów, CacheManager, hash i fingerprint pozostały bez zmian.
- tests/test_syntax_diagnostics_full_analysis.py: nowy indeks trzech źródeł i osobny cykl LIVE: błąd compile, SYNTAX_ERROR, naprawa, RECOVERED.
- tests/test_index_fusion.py: symulowany kompletny historyczny cache powiązany z nowymi bajtami nie omija walidacji; nowy poprawny cache pomija parser przy identycznych bajtach.
- issues.md: po przejściu testów literalnie zastąpiono wyłącznie opis zagadnienia „Walidacja AST a kompilowalność CPython”. Trzy pozostałe zagadnienia zachowano.

## DOWODY KOMPILACJI I BRAKU WYKONANIA

W SP-R5 na CPython 3.15.2, ast.parse przyjmował poprawny future, misplaced future i return poza funkcją; compile(AST) oraz compile(source) przyjmowały wyłącznie poprawny wariant. Nowy parser kompiluje już utworzony AST i odrzuca dwa błędne warianty. Testy indeksu potwierdzają lokalizację błędów na liniach 2 i 1. Samo compile tworzy obiekt kodu, lecz go nie wykonuje; ścieżka source.py nie wywołuje exec ani importu analizowanego modułu. Dowód dotyczy tej ścieżki i uruchomionych regresji, nie runtime wszystkich analizowanych projektów.

## COLD / WARM CACHE

Zimna ścieżka indexer.py czyta jeden snapshot bajtów, następnie wywołuje parse_source_snapshot. Nowy compile(AST) używa tego AST. Historyczny cache bez source_compilability_semantics_version, nawet po dopasowaniu do nowych bajtów przez CacheManager.set(source_bytes=...), zostaje odrzucony; plik trafia do skipped. Poprawny nowy cache zapisuje wersję 1, a ponowny odczyt tych samych bajtów nie wywołuje parse_source_snapshot. Testy te potwierdziły przejście przez walidację po unieważnieniu i utrzymanie szybkiej ścieżki dla kompletnego cache.

## FULL / INCREMENTAL LIVE W TESTACH

Test indeksu i build_syntax_diagnostics_from_index: valid.py jest w modules, bad_future.py i bad_return.py są w skipped oraz mają checked_with_errors; rodzina fresh. Test na _live_syntax_fixture: po błędnym future update_file zwrócił SYNTAX_ERROR z checked_with_errors, a po przywróceniu poprawnego kodu RECOVERED z checked_and_none. Istniejące testy potwierdzają jeden odczyt raw source, pojedynczy ast.parse na zimnej ścieżce, brak parse przy warm hit i atomowość diagnostyki LIVE. Nie uruchamiano FULL na Spiral Prophet.

## WYNIKI TESTÓW

CPython 3.15.2, pytest 9.1.1, polecenie: .venv/Scripts/python.exe -m pytest tests/test_syntax_diagnostics_full_analysis.py tests/test_index_fusion.py tests/test_no_double_parse.py -rs. Wynik: 33 passed in 8.03s. Inne testy nie były uruchamiane. Nie wykonywano pełnego pytest.

## MCP POST-CHANGE AUDIT I GRANICA ADOPCJI

Po zmianie get_module_context oraz get_file_edit_context dla contextor.core.source i contextor.core.symbol_engine.indexer zwróciły revision 1402, provenance=snapshot, workspace_sync=out_of_sync z ostrzeżeniem „Target file on disk has been modified since canonical state revision was generated.” syntax_diagnostics pokazało historyczne checked_and_none. MCP może odczytać oba moduły, lecz snapshot nie odzwierciedla nowego kodu; audyt aktualnej implementacji przez MCP jest NOT_AVAILABLE. Lokalny interpreter uruchomił aktualny kod w testach. Adopcja przez właściwy backend i ponowna diagnostyka rzeczywistego Spiral Prophet pozostają NIEUSTALONE; nie oznaczono FINAL PASS LIVE. Nie wywołano update_file, FULL, SCC02 ani restartu.

## FILES_CHANGED

- C:/Temp/Contextor_Repo/contextor/core/source.py
- C:/Temp/Contextor_Repo/contextor/core/symbol_engine/indexer.py
- C:/Temp/Contextor_Repo/tests/test_syntax_diagnostics_full_analysis.py
- C:/Temp/Contextor_Repo/tests/test_index_fusion.py
- C:/Temp/Contextor_Repo/issues.md
- C:/Temp/Contextor_Repo/walkthrough.md — wyłącznie raport; jego własny diff nie jest rekurencyjnie dublowany.

tests/test_no_double_parse.py, audyt.txt i Spiral Prophet nie zostały zmienione. Bez commit, push i stagingu.

## FULL_DIFFS

Poniżej pełny rzeczywisty git diff względem HEAD dla wszystkich zmienionych plików produkcyjnych, testowych i issues.md:

~~~diff
diff --git a/contextor/core/source.py b/contextor/core/source.py
index b871508..adb03a2 100644
--- a/contextor/core/source.py
+++ b/contextor/core/source.py
@@ -93,6 +93,13 @@ def parse_source_snapshot(
 
     try:
         tree = ast.parse(source, filename=str(path))
+        compile(
+            tree,
+            str(path),
+            "exec",
+            dont_inherit=True,
+            optimize=0,
+        )
     except SyntaxError as exc:
         location = f"line {exc.lineno}"
         if exc.offset is not None:
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 0b3f54a..1939550 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -79,6 +79,7 @@ REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
 IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 10
+SOURCE_COMPILABILITY_SEMANTICS_VERSION = 1
 _IMPORTABLE_BINARY_SUFFIXES = tuple(
     sorted(
         frozenset(BYTECODE_SUFFIXES)
@@ -955,6 +956,12 @@ def _process_single_file(
             is not int
             or cached_data.get("import_classification_semantics_version")
             != IMPORT_CLASSIFICATION_SEMANTICS_VERSION
+            or type(cached_data.get(
+                "source_compilability_semantics_version"
+            )) is not int
+            or cached_data[
+                "source_compilability_semantics_version"
+            ] != SOURCE_COMPILABILITY_SEMANTICS_VERSION
             or type(cached_data.get("imports")) is not list
             or any(
                 type(imp) is not dict
@@ -1410,6 +1417,9 @@ def _process_single_file(
             "import_classification_semantics_version": (
                 IMPORT_CLASSIFICATION_SEMANTICS_VERSION
             ),
+            "source_compilability_semantics_version": (
+                SOURCE_COMPILABILITY_SEMANTICS_VERSION
+            ),
             "typing_guard_initializer_passive": (
                 typing_guard_initializer_passive
             ),
diff --git a/issues.md b/issues.md
index 2b03e30..17d3c0c 100644
--- a/issues.md
+++ b/issues.md
@@ -42,19 +42,26 @@ Nie zatwierdzono implementacji.
 
 ### Walidacja AST a kompilowalność CPython
 
-Audyt Spiral Prophet ujawnił moduł
-core.validators.event.event_actor_validator,
-który pozostaje w kanonicznym indeksie,
-mimo że CPython compile odrzuca jego źródło
-z powodu nieprawidłowego położenia instrukcji
-from __future__ import annotations.
-Dotychczasowa diagnostyka oparta na ast.parse
-nie wykrywa tego przypadku, a plik nie wystąpił
-wśród zgłoszonych skipped_files.
-Należy osobno zweryfikować kontrakt diagnostyki
-składni, zakres kontroli kompilowalności oraz
-spójność faktów FULL i LIVE.
-Nie zatwierdzono jeszcze implementacji.
+Audyt Spiral Prophet wykazał rozbieżność między
+ast.parse a kompilowalnością CPython dla modułu
+core.validators.event.event_actor_validator.
+
+W SP-R5 potwierdzono także obejście parsera
+przez kompletny historyczny cache oraz wspólną
+ścieżkę parsera dla indeksowania i incremental.
+
+Wdrożono walidację compile(AST) bez wykonywania
+kodu i bez ponownego parsowania źródła.
+Wprowadzono osobną wersję semantyki walidacji
+źródła, która odrzuca wcześniejsze wpisy cache.
+
+Wyniki regresji produkcyjnych i testów są
+dokumentowane w walkthrough.md bieżącego zadania.
+
+Do zamknięcia pozostaje potwierdzenie adopcji
+nowego kodu przez właściwy backend oraz
+ponownej diagnostyki rzeczywistego repozytorium
+Spiral Prophet. Nie oznaczono jako FINAL PASS LIVE.
 
 ### Wywołania metod przez pola instancji
 
diff --git a/tests/test_index_fusion.py b/tests/test_index_fusion.py
index bc892dc..2bffe94 100644
--- a/tests/test_index_fusion.py
+++ b/tests/test_index_fusion.py
@@ -168,6 +168,63 @@ def test_new_format_cache_hit_reuses_cached_facts_without_ast_parse(
     assert result.lineage_facts_by_source["module.py"].source_key == "module.py"
 
 
+def test_legacy_cache_cannot_bypass_compilability(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("value = 1\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+
+    legacy = dict(_cache_payload(root, source)["data"])
+    legacy.pop("source_compilability_semantics_version")
+    bad_source = b"import os\nfrom __future__ import annotations\n"
+    source.write_bytes(bad_source)
+    CacheManager(str(root)).set(source, legacy, source_bytes=bad_source)
+
+    parse_calls = []
+    original_parse = indexer.parse_source_snapshot
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_snapshot",
+        lambda snapshot, path: (
+            parse_calls.append(path) or original_parse(snapshot, path)
+        ),
+    )
+    result = indexer.index_repository(str(root))
+
+    assert len(parse_calls) == 1
+    assert "module" not in result.modules
+    assert len(result.skipped) == 1
+    assert result.skipped[0].path == "module.py"
+    assert "from __future__ imports must occur at the beginning of the file" in result.skipped[0].reason
+
+
+def test_compilability_cache_version_warm_hit_skips_parse(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("value = 1\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+    assert _cache_payload(root, source)["data"]["source_compilability_semantics_version"] == 1
+
+    parse_calls = []
+    original_parse = indexer.parse_source_snapshot
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_snapshot",
+        lambda snapshot, path: (
+            parse_calls.append(path) or original_parse(snapshot, path)
+        ),
+    )
+    result = indexer.index_repository(str(root))
+
+    assert "module" in result.modules
+    assert parse_calls == []
+    assert _cache_payload(root, source)["data"]["source_compilability_semantics_version"] == 1
+
+
 def test_source_change_invalidates_symbol_facts_then_complete_warm_hit_skips_ast_parse(
     tmp_path, isolated_dirs, monkeypatch
 ):
diff --git a/tests/test_syntax_diagnostics_full_analysis.py b/tests/test_syntax_diagnostics_full_analysis.py
index 4b5c65b..bf4edd8 100644
--- a/tests/test_syntax_diagnostics_full_analysis.py
+++ b/tests/test_syntax_diagnostics_full_analysis.py
@@ -148,6 +148,37 @@ def test_real_index_repository_materializes_source_scoped_syntax_facts(tmp_path,
     assert "module_name" not in facts["broken.py"]
 
 
+def test_index_rejects_source_that_ast_parses_but_cpython_cannot_compile(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    (repo / "valid.py").write_text(
+        "from __future__ import annotations\nvalue: list[int] = []\n",
+        encoding="utf-8",
+    )
+    (repo / "bad_future.py").write_text(
+        "import os\nfrom __future__ import annotations\n",
+        encoding="utf-8",
+    )
+    (repo / "bad_return.py").write_text("return 1\n", encoding="utf-8")
+
+    index = index_repository(str(repo))
+    diagnostics, family_state = build_syntax_diagnostics_from_index(index)
+
+    assert set(index.modules) == {"valid"}
+    skipped = {entry.path: entry for entry in index.skipped}
+    assert set(skipped) == {"bad_future.py", "bad_return.py"}
+    assert skipped["bad_future.py"].line_number == 2
+    assert skipped["bad_return.py"].line_number == 1
+    assert family_state == "fresh"
+    assert diagnostics["valid.py"] == {"status": "checked_and_none", "errors": []}
+    assert diagnostics["bad_future.py"]["status"] == "checked_with_errors"
+    assert diagnostics["bad_future.py"]["errors"][0]["line_number"] == 2
+    assert diagnostics["bad_return.py"]["status"] == "checked_with_errors"
+    assert diagnostics["bad_return.py"]["errors"][0]["line_number"] == 1
+
+
 def test_real_facade_materializes_real_index_syntax_facts(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -270,6 +301,44 @@ def test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic(
         server.close()
 
 
+def test_live_rejects_compile_error_and_recovers(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    source, server, _ = _live_syntax_fixture(tmp_path)
+    try:
+        source.write_text(
+            "import os\nfrom __future__ import annotations\n",
+            encoding="utf-8",
+        )
+        invalid = server._dispatch({
+            "operation": "update_file",
+            "file_path": str(source),
+            "origin": "desktop_watcher",
+        })
+        assert invalid["result"].status == "SYNTAX_ERROR"
+        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
+            "status": "checked_with_errors",
+            "errors": [{
+                "message": "from __future__ imports must occur at the beginning of the file",
+                "line_number": 2,
+                "column_number": 1,
+            }],
+        }
+
+        source.write_text("def value():\n    return 2\n", encoding="utf-8")
+        repaired = server._dispatch({
+            "operation": "update_file",
+            "file_path": str(source),
+            "origin": "desktop_watcher",
+        })
+        assert repaired["result"].status == "RECOVERED"
+        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
+            "status": "checked_and_none",
+            "errors": [],
+        }
+    finally:
+        server.close()
+
+
 def test_incremental_update_does_not_promote_unmaterialized_syntax_family(tmp_path, monkeypatch):
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
     source, server, _ = _live_syntax_fixture(tmp_path, family_state="not_materialized")
~~~

Nie wykonano zmian w pozostałych plikach produkcji i testów. Walkthrough.md jest bieżącym raportem i jego własny diff nie jest rekurencyjnie powielany.
