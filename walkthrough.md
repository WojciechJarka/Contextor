# CONTEXTOR — SHARED IDENTITY RESOLUTION — F2B CONTROL-FLOW HARDENING
**Date:** 2026-08-23  
**Target 1 (Helper):** `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py`  
**Target 2 (Tool):** `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifacts_for_module.py`  
**Tests 1:** `C:\Temp\Contextor_Repo\tests\test_mcp_identity_resolution.py`  
**Tests 2:** `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_artifacts_for_module.py`  
**Status:** COMPLETED & VERIFIED

---

## 1. CEL I ZAKRES IMPLEMENTACJI

Uszczelnienie przepływu sterowania (control flow) w integracji `get_artifacts_for_module` oraz współdzielonym module `query_helpers`:

### Rozwiązane zagadnienia:
1. **Współdzielony klasyfikator ID (`query_helpers.is_module_id`):**
   - Zmiana prywatnego helpera na publiczne wewnętrzne API MCP `is_module_id(query: str) -> bool`.
   - Klasyfikator wykonuje `raw = query.strip()` i weryfikuje gramatykę `^\d+/\d+$` bez uruchamiania wyszukiwania w registry ani fuzzy scoringu.
2. **Precedens globalnego guardu stanu LIVE:**
   - Sprawdzenie `engine` oraz `resync_required` (`Error: No usable canonical LIVE state. Run analyze_project first.`) jest wykonywane na samym początku `try:`, przed jakimkolwiek sprawdzaniem tożsamości modułu czy zwracaniem komunikatów o braku modułu.
   - Ani istniejący ID, ani nieistniejący ID (`9999/1`) nie omijają tego guardu.
3. **Pre-pass RAW ID wywoływany wyłącznie dla syntaktycznego module ID:**
   - Usunięto bezwarunkowe wywoływanie `resolve_module_identity` na każdym wejściu użytkownika.
   - Jeśli `is_module_id(effective_module)` jest `True`, wywoływany jest resolver ID.
   - Dla wejść tekstowych wykonywana jest normalizacja ścieżki i standardowy lookup LIVE.
   - Dla poprawnych wejść tekstowych (zarówno dotted `pkg.mod_a`, jak i ścieżkowych `pkg/mod_a.py`) liczba wywołań `resolve_module_identity` wynosi dokładnie `0`.
4. **Fuzzy Fallback z normalizacją zapytania:**
   - Resolver fuzzy jest wywoływany dopiero po faktycznym niepowodzeniu normalnego lookupu tekstowego.
   - Dla wejść ścieżkowych z literówką (`pkg/servces/auth.py`) do resolvera przekazywana jest postać znormalizowana (`pkg.servces.auth`), a w odpowiedzi zwracany jest oryginalny input użytkownika (`"query": "pkg/servces/auth.py"`).

---

## 2. DOKONANE ZMIANY MECHANICZNE

### A. Helper (`contextor/mcp/query_helpers.py`)
- Zmieniono `_is_module_id` na `is_module_id` z automatycznym `strip()`.
- Zaktualizowano wywołanie wewnątrz `resolve_module_identity`.

### B. Produkcja (`contextor/mcp/tools/get_artifacts_for_module.py`)
- Przeniesiono globalny guard `engine / resync_required` na początek bloku `try:`.
- Otoczono wywołanie RAW `resolve_module_identity` warunkiem `if query_helpers.is_module_id(effective_module):`.

### C. Testy Jednostkowe Helpera (`tests/test_mcp_identity_resolution.py`)
- Dodano test `test_is_module_id` weryfikujący przypadki pozytywne i negatywne.

### D. Dedykowane Testy Narzędzia (`tests/mcp/tools/test_get_artifacts_for_module.py`)
- Zaktualizowano testy `test_valid_dotted_lookup_does_not_call_fuzzy_fallback` oraz `test_valid_path_lookup_does_not_call_fuzzy_fallback` (asercja braku wywołania resolvera).
- Dodano testy precedensu braku silnika (`engine=None`) i `resync_required=True` dla istniejących i nieistniejących ID.
- Dodano test weryfikujący przekazywanie znormalizowanej postaci do resolvera fuzzy przy zachowaniu oryginalnego zapytania w polu `"query"`.

---

## 3. WERYFIKACJA TESTAMI (TARGETED PYTEST)

Uruchomiono zestaw testów:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_mcp_identity_resolution.py tests/mcp/tools/test_get_artifacts_for_module.py
```
**Wynik:**
```text
tests\test_mcp_identity_resolution.py ..........................         [ 50%]
tests\mcp\tools\test_get_artifacts_for_module.py ....................... [ 96%]
..                                                                       [100%]
============================= 51 passed in 1.20s ==============================
```

Dodatkowo sprawdzono testy dokumentacji i kompatybilności wstecznej:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_mcp_documentation.py tests/test_mcp_split_s2c.py
```
**Wynik:** 46 passed in 4.87s.

---

## 4. ARCHITECTURAL & BLAST RADIUS VERIFICATION (CONTEXTOR-FIRST)

Weryfikacja Contextor MCP:
- `get_file_edit_context(file_path="contextor/mcp/tools/get_artifacts_for_module.py", mode="minimal")`:
  - Warstwa: `adapter`, `outbound_violation_count: 0`, `inbound_violation_count: 0`.
- `get_file_edit_context(file_path="contextor/mcp/query_helpers.py", mode="minimal")`:
  - Warstwa: `adapter`, brak naruszeń warstwowych, stabilna powierzchnia konsumentów.

---

## 5. DOKŁADNE DIFFY KODU (UNIFIED DIFFS)

### 1. `contextor/mcp/query_helpers.py`
```diff
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -79,10 +79,9 @@ def canonical_symbol_catalog(module_data: dict) -> dict[str, str]:
     return result
 
 
-def _is_module_id(query: str) -> bool:
-    if "/" not in query or query.startswith(("A", "a")):
-        return False
-    parts = query.split("/")
+def is_module_id(query: str) -> bool:
+    raw = query.strip()
+    parts = raw.split("/")
     return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
 
 
@@ -107,7 +106,7 @@ def resolve_module_identity(
         }
 
     # 1. Module ID lookup
-    if _is_module_id(raw):
+    if is_module_id(raw):
         exact_name = mod_id_to_path.get(raw)
         if exact_name:
             return {
```

### 2. `contextor/mcp/tools/get_artifacts_for_module.py`
```diff
--- a/contextor/mcp/tools/get_artifacts_for_module.py
+++ b/contextor/mcp/tools/get_artifacts_for_module.py
@@ -76,21 +76,24 @@ def get_artifacts_for_module(
 
     try:
         mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
+        engine = mcp_runtime.get_or_init_engine(root)
+        if not engine or getattr(engine.state, "resync_required", False):
+            return "Error: No usable canonical LIVE state. Run analyze_project first."
 
-        # 1. RAW Module ID resolution
-        raw_resolution = query_helpers.resolve_module_identity(
-            effective_module,
-            mod_path_to_id,
-            mod_id_to_path,
-        )
-
-        if raw_resolution["status"] == "resolved" and raw_resolution.get("resolution") == "exact_id":
-            module_name = raw_resolution["module"]
-        elif raw_resolution["status"] == "not_found" and raw_resolution.get("query_kind") == "module_id":
-            return (
-                f"Module '{effective_module}' not found in registry or canonical LIVE state. "
-                "Check the module name or run an analysis."
+        # 1. RAW Module ID resolution via shared classifier
+        if query_helpers.is_module_id(effective_module):
+            raw_resolution = query_helpers.resolve_module_identity(
+                effective_module,
+                mod_path_to_id,
+                mod_id_to_path,
             )
+            if raw_resolution["status"] == "resolved" and raw_resolution.get("resolution") == "exact_id":
+                module_name = raw_resolution["module"]
+            elif raw_resolution["status"] == "not_found" and raw_resolution.get("query_kind") == "module_id":
+                return (
+                    f"Module '{effective_module}' not found in registry or canonical LIVE state. "
+                    "Check the module name or run an analysis."
+                )
         else:
             # 2. Textual Module Flow: Normalise file-path input to dotted module name.
             target_path = Path(module_name)
@@ -111,9 +114,6 @@ def get_artifacts_for_module(
 
                 module_name = ".".join(parts)
 
-        engine = mcp_runtime.get_or_init_engine(root)
-        if not engine or getattr(engine.state, "resync_required", False):
-            return "Error: No usable canonical LIVE state. Run analyze_project first."
         state = engine.state
         unavailable = query_helpers.module_truth_unavailable(state, module_name)
         if unavailable:
```

### 3. `tests/test_mcp_identity_resolution.py`
```diff
--- a/tests/test_mcp_identity_resolution.py
+++ b/tests/test_mcp_identity_resolution.py
@@ -5,6 +5,7 @@ import pytest
 from contextor.mcp.query_helpers import (
     FUZZY_MIN_SCORE,
     FUZZY_MAX_CANDIDATES,
+    is_module_id,
     resolve_module_identity,
     resolve_artifact_identity,
 )
@@ -385,3 +386,20 @@ def test_resolver_signatures_locked():
     ]
     for param in art_sig.parameters.values():
         assert param.default is inspect.Parameter.empty
+
+
+def test_is_module_id():
+    # True
+    assert is_module_id("259/1") is True
+    assert is_module_id(" 259/1 ") is True
+    assert is_module_id("10/1") is True
+    assert is_module_id("0/0") is True
+
+    # False
+    assert is_module_id("A259/1") is False
+    assert is_module_id("259") is False
+    assert is_module_id("259/abc") is False
+    assert is_module_id("pkg/mod.py") is False
+    assert is_module_id("pkg.mod") is False
+    assert is_module_id("") is False
+    assert is_module_id("259/1/2") is False
```

### 4. `tests/mcp/tools/test_get_artifacts_for_module.py`
```diff
--- a/tests/mcp/tools/test_get_artifacts_for_module.py
+++ b/tests/mcp/tools/test_get_artifacts_for_module.py
@@ -295,14 +295,11 @@ def test_exact_module_id_respects_presentation_controls(tmp_path, monkeypatch):
 
 def test_valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
     _setup_test_state(monkeypatch)
-    orig_resolve = query_helpers.resolve_module_identity
-    calls = []
 
-    def tracking_resolver(query, p2i, i2p):
-        calls.append(query)
-        return orig_resolve(query, p2i, i2p)
+    def fail_if_called(*_args, **_kwargs):
+        raise AssertionError("resolve_module_identity should NOT have been called for valid dotted module!")
 
-    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)
+    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)
 
     raw = get_artifacts_for_module(
         repo_path=str(tmp_path),
@@ -310,13 +307,26 @@ def test_valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch)
     )
     res = json.loads(raw)
     assert res["module"] == "pkg.mod_a"
-    # RAW ID check is called once with "pkg.mod_a", but fuzzy fallback is NOT called
-    assert len(calls) == 1
-    assert calls[0] == "pkg.mod_a"
 
 
 def test_valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
     _setup_test_state(monkeypatch)
+
+    def fail_if_called(*_args, **_kwargs):
+        raise AssertionError("resolve_module_identity should NOT have been called for valid path lookup!")
+
+    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg/mod_a.py",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+
+
+def test_fuzzy_miss_calls_resolver_with_normalized_query(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
     orig_resolve = query_helpers.resolve_module_identity
     calls = []
 
@@ -328,13 +338,59 @@ def test_valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
 
     raw = get_artifacts_for_module(
         repo_path=str(tmp_path),
-        module="pkg/mod_a.py",
+        module="pkg/servces/auth.py",
     )
     res = json.loads(raw)
-    assert res["module"] == "pkg.mod_a"
-    # RAW ID check is called once with "pkg/mod_a.py", but fuzzy fallback is NOT called
+    assert res["status"] == "not_found"
+    assert res["query"] == "pkg/servces/auth.py"
     assert len(calls) == 1
-    assert calls[0] == "pkg/mod_a.py"
+    assert calls[0] == "pkg.servces.auth"
+
+
+def test_missing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="9999/1",
+    )
+    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."
+
+
+def test_missing_id_with_resync_required_returns_global_error(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    monkeypatch.setattr(
+        mcp_runtime,
+        "get_or_init_engine",
+        lambda _root: SimpleNamespace(state=SimpleNamespace(resync_required=True)),
+    )
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="9999/1",
+    )
+    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."
+
+
+def test_existing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="10/1",
+    )
+    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."
+
+
+def test_usable_live_with_missing_id_preserves_legacy_not_found(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="9999/1",
+    )
+    assert raw == "Module '9999/1' not found in registry or canonical LIVE state. Check the module name or run an analysis."
 
 
 def test_original_query_preserved_and_candidate_structure(tmp_path, monkeypatch):
```

---

## 6. STATUS OPERACYJNY

```text
FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifacts_for_module.py
- C:\Temp\Contextor_Repo\tests\test_mcp_identity_resolution.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_artifacts_for_module.py

TESTS=51 passed in tests/test_mcp_identity_resolution.py, tests/mcp/tools/test_get_artifacts_for_module.py (+ 46 documentation & split regressions)

SHARED_IS_MODULE_ID=PASS
RESOLVER_SIGNATURES_UNCHANGED=PASS

VALID_DOTTED_RESOLVER_CALLS=0
VALID_PATH_RESOLVER_CALLS=0
FUZZY_ONLY_AFTER_TEXTUAL_LOOKUP_MISS=PASS
FUZZY_PATH_USES_NORMALIZED_QUERY=PASS
ORIGINAL_QUERY_PRESERVED=PASS

EXACT_MODULE_ID=PASS
MISSING_MODULE_ID_NEVER_FUZZY=PASS

NO_ENGINE_PRECEDENCE=PASS
RESYNC_REQUIRED_PRECEDENCE=PASS
EXACT_ID_CANNOT_BYPASS_LIVE_GUARD=PASS

NEW_TESTS_ADDED_TO_MONOLITHIC_FILES=NO

PUBLIC_MCP_SCHEMA_CHANGED=NO
MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=PASS
```
