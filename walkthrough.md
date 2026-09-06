# Weryfikacja i naprawa trzech failures

## Diagnoza

ROOT_CAUSE=Hipoteza jest potwierdzona tylko dla trzeciego testu. Dwa testy `lookup_index_entries` nie używają `FakeRegistry`; ich lokalny double `catalog_from_registry` miał stary podpis `lambda _root: catalog`, podczas gdy production wywołuje `catalog_from_registry(str(root), module_paths={})`. To powodowało błąd zanim weszła implementacja `catalog_from_registry`, a więc bez `read_transaction`. Test `get_file_edit_context` patchuje `PersistentIdentityRegistry` na `FakeRegistry` implementujący wyłącznie `.transaction()`; production `catalog_from_registry` dochodzi do `with registry.read_transaction()` i zgłasza `AttributeError`.

LOOKUP_RAW_FAILURE_1=Przed zmianą raw result nie był JSON-em: `Error resolving index entries: test_lookup_index_entries_distinguishes_active_recovery_and_missing.<locals>.<lambda>() got an unexpected keyword argument 'module_paths'`.
LOOKUP_RAW_FAILURE_2=Przed zmianą raw result nie był JSON-em: `Error resolving index entries: test_lookup_index_entries_large_output_preflight_gate.<locals>.<lambda>() got an unexpected keyword argument 'module_paths'`.
LOOKUP_CATALOG_READ_TRANSACTION=Oba lookup failures wywoływały nazwany przez tool `catalog_from_registry` (lokalny monkeypatch), lecz wyjątek następował na granicy lambda/signature; nie dochodziły do ciała `catalog_from_registry` ani do `read_transaction`.
FILE_EDIT_RAW_FAILURE=Bezpośrednie `AttributeError: 'FakeRegistry' object has no attribute 'read_transaction'. Did you mean: 'transaction'?` z `contextor.core.report_query.catalog_from_registry` line 111, po wejściu w `with registry.read_transaction()`.

FAKE_REGISTRY_CONTRACT_BEFORE=`FakeRegistry` w `tests/test_mcp_regressions.py` miał `self._state = {}`, `.transaction() -> nullcontext()` oraz `.get_module_id()`; brakowało `.read_transaction()`. W tym pliku był tylko jeden `class FakeRegistry` i jedno jego użycie (patch `PersistentIdentityRegistry` w teście file-edit).
FAKE_REGISTRY_CONTRACT_AFTER=Dodano niezależne `.read_transaction() -> nullcontext()`; `.transaction()` pozostał bez zmian. Ponieważ ten fake nie ładuje, nie alokuje i nie commit-uje stanu (obie ścieżki są no-op context managerami), nowa metoda modeluje read-only semantykę bez aliasowania mutating transaction.
PRODUCTION_CHANGE_REQUIRED=NO

## Zmiana

W dwóch testach lookup double przyjmuje teraz `module_paths=None`, zachowując dotychczasowy zwracany `IndexCatalog`. W teście file-edit `FakeRegistry` implementuje obecny read-only method contract. Nie zmieniono `catalog_from_registry`, żadnego production fallbacku ani invariantu read-only registry.

## Weryfikacja

Pierwszy run dokładnie trzech wskazanych testów: przed zmianą `3 failed`; po zmianie `3 passed, 1 warning`.

FOCUSED_TESTS=Po zmianie: `tests/mcp/tools/test_lookup_index_entries_no_discovery.py`, `tests/mcp/tools/test_minimal_registry_read_path.py`, `tests/mcp/tools/test_get_file_edit_context_syntax.py`, `tests/test_indexed_report_query.py::test_catalog_reads_both_physical_recovery_dictionaries`, `tests/test_persistent_registry.py::test_read_transaction_returns_existing_ids_without_allocating_missing_ids`, `tests/test_persistent_registry.py::test_read_transaction_repairs_in_memory_without_persisting_projection`: `13 passed in 16.01s`. Dodatkowo `git diff --check`: PASS.

DECISION=PASS
FILES_CHANGED=tests/test_mcp_regressions.py
FULL_DIFFS=

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -1109,1 +1109,1 @@
-        lambda _root: catalog,
+        lambda _root, module_paths=None: catalog,
@@ -1136,1 +1136,1 @@
-        lambda _root: catalog,
+        lambda _root, module_paths=None: catalog,
@@ -2869,0 +2870,3 @@
+        def read_transaction(self):
+            return nullcontext()
+
```

FULL_SUITE_RUN_BY_AGENT=NO
