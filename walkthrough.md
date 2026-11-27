# GRAPH-R15-I2 — CORRECTED REGRESSION FIXTURES

## PREFLIGHT

**DIRECT_EVIDENCE** — Contextor MCP przed edycją: revision 1591; test atomowości, helpery i reader miały canonical state fresh oraz workspace_sync=verified. Aktualny HEAD w lokalnym repo: 0afc5618d8bfa14ad996e31fed9c1e2445e93988; początkowy git status był czysty.

**DIRECT_EVIDENCE** — aktualny test incremental kończył się na linii 216, funkcją test_failed_candidate_report_before_publication_is_atomic. _real_baseline(tmp_path: Path, sources: dict[str, str]) -> _Baseline jest na liniach 54–82. _assert_failed_update_atomic(baseline: _Baseline, case: str, acknowledgement_calls: int) -> None jest na liniach 89–134.

**CONTRACT_PROVED** — locked_committed_snapshot(cache_dir, *, expected_repo_id, expected_root_path) w contextor/core/live_state/store.py:2039–2057 jest context managerem, który yield-uje load_snapshot(...), zwalniając lock w finally. load_snapshot zwraca (payload, metadata) w linii 2609. Testowe unpack jako (state, metadata) jest zgodne z kontraktem.

**DIRECT_EVIDENCE** — zmieniono tylko dwa pliki testowe zgodnie z poleceniem; kod produkcyjny pozostał bez zmian.

## LITERAL_EDITS

**DIRECT_EVIDENCE** — na końcu test_incremental_failed_commit_atomicity.py dodano dosłownie dwa wskazane testy. Utworzono tests/test_full_analysis_source_fingerprint_atomicity.py z literalną treścią I2; użyto unikalnych ALPHA_VALUE, BETA_VALUE i CONSUMER_VALUE zgodnie z poprawionym poleceniem.

**CONTRACT_PROVED** — unikalne nazwy eliminują NAME_COLLISION z poprzedniego fixture. Pierwsza stabilna pełna analiza obecnego testu przeszła, zwróciła result i utworzyła metadata_before.

## INCREMENTAL_UPDATED_RACE

**DIRECT_EVIDENCE** — test_source_change_after_prepare_rejects_updated_commit przeszedł w przebiegu całego obu plików: 6 passed, 1 failed.

**CONTRACT_PROVED** — test po prawdziwym prepare_source_update zmienia provider.py, oczekuje RuntimeError i wywołuje _assert_failed_update_atomic. Helper porównuje canonical state object/projekcję, FileState, usage manifest, registry checkpoint i committed metadata. Końcowe has_changed(source) sprawdza, że aktualne źródło wymaga dalszej analizy.

## INCREMENTAL_NOOP_RACE

**DIRECT_EVIDENCE** — test_source_change_after_prepare_rejects_semantic_noop przeszedł w tym samym przebiegu.

**CONTRACT_PROVED** — wariant przygotowany zawiera tylko zmianę komentarza; test potwierdza brak dodanych importów. Po przygotowaniu wrapper zapisuje inny source, test oczekuje RuntimeError, pełnego rollbacku przez _assert_failed_update_atomic i has_changed(source)=true.

## FULL_ANALYSIS_RACE

**DIRECT_EVIDENCE** — stabilny przebieg testu przeszedł: run_full_analysis_exclusive zwrócił wynik bez errors, a read_metadata zwrócił metadata_before. W drugiej analizie oryginalny index_repository zakończył indeksowanie A, ale asercja w change_source_after_index zawiodła, zanim funkcja zapisała B.

Dokładna różnica:
- indeksatorowy fingerprint dla consumer: 528300f273c1bf48c40999cb76c0805a49c13b80346fd22b6a1d27c14653b3e6;
- oczekiwany hashlib.sha256(source_a.encode("utf-8")).hexdigest(): 342ef58a364b1e379e3b8530048a0376111225d947455686e3bb6c28205e3853;
- bajty pliku consumer.py w Windows fixture: 69-6D-70-6F-72-74-20-64-65-70-5F-61-6C-70-68-61-0D-0A-43-4F-4E-53-55-4D-45-52-5F-56-41-4C-55-45-20-3D-20-64-65-70-5F-61-6C-70-68-61-2E-41-4C-50-48-41-5F-56-41-4C-55-45-0D-0A.

Plik ma CRLF (0D 0A) po Path.write_text na Windows, natomiast source_a.encode("utf-8") zawiera LF (0A). SHA256 rzeczywistych bajtów pliku, odczytany przez Get-FileHash, jest równy fingerprintowi indeksatora. To wyjaśnia asercję: oczekiwane dane nie są tymi samymi bajtami, które zapisano na dysk.

**DIRECT_EVIDENCE** — błąd wystąpił w test_full_analysis_source_fingerprint_atomicity.py:77, wewnątrz change_source_after_index. Wywołanie testu jest w linii 95. Ponieważ asercja jest przed source.write_text(source_b), B nie zostało zapisane przez wrapper; oczekiwany RuntimeError z produkcyjnego guardu nie wystąpił.

**CODE_PATH_PROVED** — wyjątek z wrappera przerwał wywołanie index_repository przed powrotem do facade. Test nie doszedł do asercji metadata_after ani do locked_committed_snapshot. Nie klasyfikuję tego przebiegu jako weryfikacji starej committed generation ani jako potwierdzenia PASS wyścigu A→B.

**DIRECT_EVIDENCE** — zgodnie z poleceniem nie zmieniałem produkcji ani asercji, aby uzyskać PASS.

## ROLLBACK_VERIFICATION

**DIRECT_EVIDENCE** — oba incremental race’y przeszły. Ich helper porównał state/FileState/manifest/registry/metadata z baseline oraz potwierdził, że plik źródłowy nadal wymaga analizy.

**UNKNOWN** — asercje pełnego testu porównujące metadata_before z metadata_after oraz walidowany snapshot nie zostały osiągnięte z powodu wcześniejszego SHA assertion failure.

## COMMITTED_GENERATION

**DIRECT_EVIDENCE** — stabilny przebieg full analysis w teście utworzył bazową committed metadata w izolowanym cache pod tmp_path. Drugi przebieg przerwał się w opakowaniu indeksatora przed powrotem do facade.

**CODE_PATH_PROVED** — stos błędu wskazuje facade.py:785 → opakowany index_repository. Dalszy kod pełnej analizy, w tym guard przed save_engine_state, nie został osiągnięty.

**UNKNOWN** — test nie odczytał metadata ani snapshotu po przerwanym drugim wywołaniu, więc pozostaje niezweryfikowane asercjami testu, że generation zachowała state_id/revision oraz stare imports/graph.

**DIRECT_EVIDENCE** — nowy test ustawia cache/output/state/registry w tmp_path. Test startup reconciliation tworzy repo i cache pod tmp_path (source: tests/test_live_watcher_startup_reconciliation.py:424–441). Nie uruchamiano aktywnego LIVE ownera ani listenera i nie mutowano aktywnego LIVE/store.

## TARGETED_PYTEST

**DIRECT_EVIDENCE** — dokładne wymagane polecenie:
.venv/Scripts/python.exe -m pytest -q tests/test_incremental_failed_commit_atomicity.py tests/test_full_analysis_source_fingerprint_atomicity.py

Wynik: **6 passed, 1 failed, 2 warnings in 19.83s**. Dwie warnings to deprecations authlib/httpx. Jedyny failure: SHA assertion w pełnym teście, tests/test_full_analysis_source_fingerprint_atomicity.py:77; wywołany z linii 95.

**DIRECT_EVIDENCE** — dokładne wymagane polecenie:
.venv/Scripts/python.exe -m pytest -q tests/test_live_watcher_startup_reconciliation.py::test_full_analysis_publishes_current_filestate_generation

Wynik: **1 passed in 1.90s**.

**DIRECT_EVIDENCE** — nie uruchomiono FULL suite, restartu ani testu na aktywnym LIVE.

## POST_CHANGE_MCP

**DIRECT_EVIDENCE** — Contextor MCP wykazał watcher events revisions 1592 i 1593 dla dwóch zmienionych plików; oba UPDATED z origin desktop_watcher. Revision końcowa 1593, continuity continuous, resync_required=false.

**DIRECT_EVIDENCE** — dla obu testów get_file_edit_context potwierdził canonical_state=fresh, workspace_sync=verified, revision 1593 oraz syntax_diagnostics checked_and_none z errors=[]. Test pełnej analizy jest obecny w canonical public_api.

**DIRECT_EVIDENCE** — get_symbol_call_context dla incremental UPDATED i NOOP zwrócił po dwa callees: _real_baseline oraz _assert_failed_update_atomic. Dla testu full projekcja call context zwróciła 0 krawędzi w zakresie intra_module; nie traktuję pustej projekcji jako dowodu braku wywołań w kodzie.

## FULL_DIFFS

FILES_CHANGED:
- tests/test_incremental_failed_commit_atomicity.py
- tests/test_full_analysis_source_fingerprint_atomicity.py
- walkthrough.md (raport; jego self-diff nie jest zamieszczany)

ACTUAL_DIFF — kompletny rzeczywisty diff obu plików testowych:

~~~diff
diff --git a/tests/test_incremental_failed_commit_atomicity.py b/tests/test_incremental_failed_commit_atomicity.py
index 68fde3e..3147664 100644
--- a/tests/test_incremental_failed_commit_atomicity.py
+++ b/tests/test_incremental_failed_commit_atomicity.py
@@ -214,3 +214,111 @@ def test_failed_candidate_report_before_publication_is_atomic(tmp_path, monkeypa
     assert report_calls, "The candidate derived-report boundary was not reached"
     assert not acknowledgements, "FileState acknowledgement preceded candidate report failure"
     _assert_failed_update_atomic(baseline, "CASE_D", len(acknowledgements))
+
+def test_source_change_after_prepare_rejects_updated_commit(
+    tmp_path, monkeypatch
+):
+    baseline = _real_baseline(
+        tmp_path,
+        {
+            "provider.py": "PROVIDER_VALUE = 1\n",
+            "consumer.py": "from provider import PROVIDER_VALUE\n",
+        },
+    )
+    source = baseline.root / "provider.py"
+    source.write_text(
+        "PROVIDER_VALUE = 1\nNEW_OWN_SYMBOL = 2\n",
+        encoding="utf-8",
+    )
+
+    from contextor.core.analysis.incremental import engine as engine_module
+
+    original_prepare = engine_module.prepare_source_update
+    preparation_calls = []
+
+    def change_source_after_prepare(*args, **kwargs):
+        prepared = original_prepare(*args, **kwargs)
+        preparation_calls.append(prepared)
+        assert not prepared.has_error
+        source.write_text(
+            "import consumer\nPROVIDER_VALUE = 3\n",
+            encoding="utf-8",
+        )
+        return prepared
+
+    monkeypatch.setattr(
+        engine_module,
+        "prepare_source_update",
+        change_source_after_prepare,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="Source changed during incremental analysis",
+    ):
+        baseline.engine.update_file(str(source))
+
+    assert len(preparation_calls) == 1
+    _assert_failed_update_atomic(
+        baseline,
+        "SOURCE_CHANGED_AFTER_PREPARE_UPDATED",
+        1,
+    )
+    assert baseline.engine.state_manager.has_changed(
+        str(source)
+    )
+
+
+def test_source_change_after_prepare_rejects_semantic_noop(
+    tmp_path, monkeypatch
+):
+    baseline = _real_baseline(
+        tmp_path,
+        {
+            "provider.py": "PROVIDER_VALUE = 1\n",
+            "consumer.py": "from provider import PROVIDER_VALUE\n",
+        },
+    )
+    source = baseline.root / "provider.py"
+    source.write_text(
+        "PROVIDER_VALUE = 1\n# semantic no-op\n",
+        encoding="utf-8",
+    )
+
+    from contextor.core.analysis.incremental import engine as engine_module
+
+    original_prepare = engine_module.prepare_source_update
+    preparation_calls = []
+
+    def change_source_after_prepare(*args, **kwargs):
+        prepared = original_prepare(*args, **kwargs)
+        preparation_calls.append(prepared)
+        assert not prepared.has_error
+        source.write_text(
+            "import consumer\nPROVIDER_VALUE = 3\n",
+            encoding="utf-8",
+        )
+        return prepared
+
+    monkeypatch.setattr(
+        engine_module,
+        "prepare_source_update",
+        change_source_after_prepare,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="Source changed during incremental analysis",
+    ):
+        baseline.engine.update_file(str(source))
+
+    assert len(preparation_calls) == 1
+    assert preparation_calls[0].delta.imports_added == []
+    _assert_failed_update_atomic(
+        baseline,
+        "SOURCE_CHANGED_AFTER_PREPARE_NOOP",
+        1,
+    )
+    assert baseline.engine.state_manager.has_changed(
+        str(source)
+    )
diff --git a/tests/test_full_analysis_source_fingerprint_atomicity.py b/tests/test_full_analysis_source_fingerprint_atomicity.py
new file mode 100644
index 0000000..89579aa
--- /dev/null
+++ b/tests/test_full_analysis_source_fingerprint_atomicity.py
@@ -0,0 +1,119 @@
+"""Regression tests for full-analysis source fingerprint integrity."""
+
+from __future__ import annotations
+
+import hashlib
+import importlib
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.full_analysis_coordinator import (
+    run_full_analysis_exclusive,
+)
+from contextor.core.live_state.store import (
+    locked_committed_snapshot,
+    read_metadata,
+)
+from contextor.core.paths import repo_cache_dir
+
+
+def test_full_analysis_rejects_source_change_after_indexing(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    monkeypatch.setenv(
+        "CONTEXTOR_CACHE_DIR", str(tmp_path / "cache")
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_OUTPUT_DIR", str(tmp_path / "output")
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR", str(tmp_path / "state")
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_REGISTRY_DIR", str(tmp_path / "registry")
+    )
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+    root = tmp_path / "repo"
+    root.mkdir()
+
+    (root / "dep_alpha.py").write_text(
+        "ALPHA_VALUE = 1\n", encoding="utf-8"
+    )
+    (root / "dep_beta.py").write_text(
+        "BETA_VALUE = 2\n", encoding="utf-8"
+    )
+    source = root / "consumer.py"
+    source_a = (
+        "import dep_alpha\n"
+        "CONSUMER_VALUE = dep_alpha.ALPHA_VALUE\n"
+    )
+    source_b = (
+        "import dep_beta\n"
+        "CONSUMER_VALUE = dep_beta.BETA_VALUE\n"
+    )
+    source.write_text(source_a, encoding="utf-8")
+
+    errors, result = run_full_analysis_exclusive(
+        root, timeout=30.0
+    )
+    assert not errors, errors
+    assert result is not None
+
+    cache = repo_cache_dir(root)
+    metadata_before = read_metadata(cache)
+    assert metadata_before is not None
+
+    facade_module = importlib.import_module(
+        "contextor.core.api.facade"
+    )
+    original_index = facade_module.index_repository
+    indexed_results = []
+
+    def change_source_after_index(*args, **kwargs):
+        indexed = original_index(*args, **kwargs)
+        indexed_results.append(indexed)
+        assert indexed.source_fingerprints_by_module[
+            "consumer"
+        ] == hashlib.sha256(
+            source_a.encode("utf-8")
+        ).hexdigest()
+        source.write_text(source_b, encoding="utf-8")
+        return indexed
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        change_source_after_index,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="Source changed during full analysis: consumer",
+    ):
+        run_full_analysis_exclusive(root, timeout=30.0)
+
+    assert len(indexed_results) == 1
+    assert source.read_text(encoding="utf-8") == source_b
+
+    metadata_after = read_metadata(cache)
+    assert metadata_after == metadata_before
+
+    with locked_committed_snapshot(
+        cache,
+        expected_repo_id=metadata_before.repo_id,
+        expected_root_path=str(root),
+    ) as (state, metadata):
+        assert metadata.revision == metadata_before.revision
+        assert metadata.state_id == metadata_before.state_id
+        assert {
+            imp.module
+            for imp in state.modules["consumer"].imports
+        } == {"dep_alpha"}
+        assert "dep_alpha" in state.dependency_graph.hard_edges[
+            "consumer"
+        ]
+        assert "dep_beta" not in state.dependency_graph.hard_edges[
+            "consumer"
+        ]
~~~

## CONCLUSIONS

**DIRECT_EVIDENCE** — oba incremental race’y PASS z rollback assertions; test startup reconciliation PASS. Post-change Contextor źródła są fresh, zsynchronizowane i bez syntax errors.

**BLOCKED_SEMANTIC_INTEGRITY** — pełny race test pozostaje FAIL na porównaniu fingerprintu z source_a.encode("utf-8"). Na Windows Path.write_text zapisał CRLF; indeksatorowy SHA zgadza się z rzeczywistymi bajtami consumer.py, a oczekiwany SHA dotyczy bajtów LF. Test nie wykonał mutacji A→B ani końcowych asercji committed generation. Zgodnie z instrukcją nie poprawiałem asercji ani produkcji.

**UNKNOWN** — poprzednia committed generation nie została sprawdzona po drugim wywołaniu, bo test przerwał się przed tym kodem. Nie ma podstaw do PASS pełnej regresji ani do deklaracji, że ten test zweryfikował odmowę publikacji.

**FINAL_STATUS** — dwa testy incremental oraz wskazany test startup przeszły; pełny race test nie przeszedł z powodu wykazanego CRLF/LF mismatch. Testy pozostawiono dokładnie w poleconej treści.
