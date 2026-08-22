# CONTEXTOR — MCP UX MICRO-FIX: `lookup_artifact_by_symbol` ALIAS CONFLICT VALIDATION
**Date:** 2026-08-22  
**Target:** `C:\Temp\Contextor_Repo\contextor\mcp\tools\lookup_artifact_by_symbol.py`  
**Status:** COMPLETED & VERIFIED

---

## 1. CEL I ZAŁOŻENIA WALIDACJI

Dodanie walidacji spójności, gdy podano jednocześnie oba parametry `symbol_name` oraz `symbol`:
- Gdy oba są podane i niepuste, ich znormalizowane wartości muszą być identyczne (`normalized_symbol_name == normalized_symbol`).
- Gdy wartości się różnią -> zwracany jest kontrolowany błąd:
  ```json
  {
    "status": "error",
    "error": "symbol_name and symbol must match when both are provided."
  }
  ```
- Gdy oba są identyczne (np. `symbol_name="my_func", symbol="my_func"`) -> zapytanie wykonuje się normalnie bez błędu.

---

## 2. DOKONANE ZMIANY MECHANICZNE

### A. Produkcja (`contextor/mcp/tools/lookup_artifact_by_symbol.py`)
```python
    root = Path(repo_path).expanduser().resolve()
    normalized_symbol_name = symbol_name.strip()
    normalized_symbol = symbol.strip() if symbol is not None else ""

    if normalized_symbol_name and normalized_symbol and normalized_symbol_name != normalized_symbol:
        return json.dumps(
            {
                "status": "error",
                "error": "symbol_name and symbol must match when both are provided.",
            },
            indent=2,
        )

    effective_symbol = normalized_symbol or normalized_symbol_name
    if not effective_symbol:
        return json.dumps(
            {
                "status": "error",
                "error": "symbol_name or symbol is required.",
            },
            indent=2,
        )
```

### B. Testy Regresyjne (`tests/test_mcp_split_s2c.py`)
Dodano testy:
1. `test_lookup_artifact_by_symbol_matching_both_symbol_name_and_symbol` (`symbol_name="my_func", symbol="my_func"` -> działa normalnie).
2. `test_lookup_artifact_by_symbol_conflicting_symbol_name_and_symbol_returns_error` (`symbol_name="my_func", symbol="different"` -> zwraca błąd o niezgodności aliasów).

---

## 3. WERYFIKACJA TESTAMI (TARGETED PYTEST)

Uruchomiono celowane testy:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_mcp_split_s2c.py tests/test_mcp_documentation.py
```
**Wynik:** `19 passed, 1 warning in 3.99s` (100% sukcesu).

---

## 4. ARCHITECTURAL & BLAST RADIUS VERIFICATION (CONTEXTOR-FIRST)

Weryfikacja przez Contextor MCP:
- `get_file_edit_context(file_path="contextor/mcp/tools/lookup_artifact_by_symbol.py", mode="minimal")`:
  - `outbound_violation_count: 0`, `inbound_violation_count: 0`.
  - Konsumenci: `contextor.mcp_server`, `tests.test_mcp_split_s2c`.
- `get_artifact_blast_radius(artifact_name="contextor.mcp.tools.lookup_artifact_by_symbol::lookup_artifact_by_symbol")`:
  - Potwierdzono brak naruszenia architektury i brak zmian w powierzchni produkcyjnej.

---

## 5. DOKŁADNE DIFFY KODU (UNIFIED DIFFS)

### 1. `contextor/mcp/tools/lookup_artifact_by_symbol.py`
```diff
--- a/contextor/mcp/tools/lookup_artifact_by_symbol.py
+++ b/contextor/mcp/tools/lookup_artifact_by_symbol.py
@@ -16,7 +16,19 @@ def lookup_artifact_by_symbol(
     symbol: str | None = None,
 ) -> str:
     root = Path(repo_path).expanduser().resolve()
-    effective_symbol = (symbol or symbol_name).strip()
+    normalized_symbol_name = symbol_name.strip()
+    normalized_symbol = symbol.strip() if symbol is not None else ""
+
+    if normalized_symbol_name and normalized_symbol and normalized_symbol_name != normalized_symbol:
+        return json.dumps(
+            {
+                "status": "error",
+                "error": "symbol_name and symbol must match when both are provided.",
+            },
+            indent=2,
+        )
+
+    effective_symbol = normalized_symbol or normalized_symbol_name
     if not effective_symbol:
         return json.dumps(
             {
```

### 2. `tests/test_mcp_split_s2c.py`
```diff
--- a/tests/test_mcp_split_s2c.py
+++ b/tests/test_mcp_split_s2c.py
@@ -243,4 +243,30 @@ def test_lookup_artifact_by_symbol_preserves_limit_and_compact_semantics(tmp_pa
     assert entry["consumers"]["total"] == 2
     assert entry["consumers"]["truncated"] is True
     assert len(entry["consumers"]["items"]) == 1
+
+
+def test_lookup_artifact_by_symbol_matching_both_symbol_name_and_symbol(tmp_path, monkeypatch):
+    import json
+    _setup_lookup_state(monkeypatch)
+    raw = lookup_artifact_by_symbol(
+        repo_path=str(tmp_path),
+        symbol_name="my_func",
+        symbol="my_func",
+    )
+    res = json.loads(raw)
+    assert res["query"] == "my_func"
+    assert "pkg.mod_a::my_func" in res["artifacts"]
+
+
+def test_lookup_artifact_by_symbol_conflicting_symbol_name_and_symbol_returns_error(tmp_path, monkeypatch):
+    import json
+    _setup_lookup_state(monkeypatch)
+    raw = lookup_artifact_by_symbol(
+        repo_path=str(tmp_path),
+        symbol_name="my_func",
+        symbol="different",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "error"
+    assert res["error"] == "symbol_name and symbol must match when both are provided."
```

---

## 6. STATUS OPERACYJNY

```text
FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\mcp\tools\lookup_artifact_by_symbol.py
- C:\Temp\Contextor_Repo\tests\test_mcp_split_s2c.py

TESTS=19 passed, 1 warning in 3.99s
VERDICT=PASS
```
