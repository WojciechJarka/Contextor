# CONTEXTOR — SHARED IDENTITY RESOLUTION — F2B: `get_artifacts_for_module`
**Date:** 2026-08-23  
**Target:** `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifacts_for_module.py`  
**Docs:** `C:\Temp\Contextor_Repo\contextor\mcp\docs\get_artifacts_for_module.json`  
**Dedicated Tests:** `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_artifacts_for_module.py`  
**Regression Assert Fix:** `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`  
**Status:** COMPLETED & VERIFIED

---

## 1. CEL I ZAKRES IMPLEMENTACJI

Podłączenie współdzielonego resolvera tożsamości `query_helpers.resolve_module_identity` do publicznego narzędzia MCP `get_artifacts_for_module` z organizacją testów w dedykowanym module `tests/mcp/tools/`.

### Kluczowe założenia:
1. **Dedykowany plik testowy (`tests/mcp/tools/test_get_artifacts_for_module.py`):**
   - Zgodnie z nowym invariantem architektonicznym, wszystkie nowe testy integracyjne tego toola zostały umieszczone w dedykowanym pliku, bez rozrostu monolitu `tests/test_mcp_regressions.py` ani `tests/test_mcp_split_s2c.py`.
2. **Zachowanie istniejących kontraktów i normalizacji:**
   - Aliasy `module_name ↔ module` działają bez zmian (włącznie z error handlingiem dla braku/konfliktu).
   - Normalizacja ścieżek (`.py`, slashe `/` i `\` na Windowsie) do dotted module name działa identycznie dla wejść tekstowych.
3. **Obsługa Exact Active Module ID (`10/1`, `259/1`):**
   - Sprawdzenie RAW inputu przez `query_helpers.resolve_module_identity` przed normalizacją ścieżki.
   - Jeśli to syntaktycznie poprawny, istniejący module ID -> rozwiązanie do kanonicznego modułu i przekazanie do istniejącego downstream pipeline.
   - Jeśli to syntaktycznie poprawny, lecz nieistniejący module ID (np. `9999/1`) -> brak uruchamiania fuzzy, zachowanie kontrolowanego komunikatu legacy not-found.
4. **Wyszukiwanie tekstowe i fallback do Bounded Fuzzy Suggestions:**
   - Standardowy lookup w aktualnym stanie LIVE jest wykonywany jako pierwszy.
   - Dopiero przy rzeczywistym braku modułu w registry/LIVE state wywoływany jest fallback fuzzy.
   - Przy literówkach (w postaci dotted lub ścieżki) zwracana jest ustrukturyzowana odpowiedź:
     ```json
     {
       "status": "not_found",
       "query": "<original_user_input>",
       "similar_candidates": [
         {
           "module": "pkg.services.auth",
           "module_id": "13/1",
           "score": 0.9412
         }
       ],
       "data_source": "active_module_registry"
     }
     ```
   - Sugestie są czysto doradcze (nigdy auto-resolve, brak `artifacts` w odpowiedzi).
   - Przy braku dopasowań spełniających próg `0.75` zwracany jest dokładny legacy komunikat stringowy.
5. **Currentness & Presentation Controls:**
   - Exact module ID weryfikuje aktualność modułu przez `module_truth_unavailable` (fail-closed).
   - Ograniczenia prezentacyjne (`limit`, `evidence_limit`, `compact`, `fields`, `representation`) działają identycznie dla wejść rozwiązywanych przez ID.
6. **Pojedynczy owner polityki fuzzy:**
   - Narzędzie nie importuje `difflib`, nie implementuje lokalnych progów ani regexów ID.

---

## 2. DOKONANE ZMIANY MECHANICZNE

### A. Produkcja (`contextor/mcp/tools/get_artifacts_for_module.py`)
- Pobieranie obu map modułowych `mod_path_to_id, mod_id_to_path` z `query_helpers.read_registries(root)`.
- Rozpoznawanie RAW module ID przed normalizacją ścieżek.
- Dodanie fallbacku `resolve_module_identity` w bloku not-found po nieudanym lookupie tekstowym.

### B. Dokumentacja MCP (`contextor/mcp/docs/get_artifacts_for_module.json`)
- Zaktualizowano sekcję `parameters` i `behavior` o informację o obsłudze exact module ID oraz bounded fuzzy module suggestions.

### C. Dedykowane Testy (`tests/mcp/tools/test_get_artifacts_for_module.py`)
- Utworzono nowy, dedykowany zestaw 20 testów jednostkowo-integracyjnych pokrywających wszystkie wymagane scenariusze.

### D. Korekta Asercji w Monolicie (`tests/test_mcp_regressions.py`)
- Poprawiono asercję obecności parametru `representation` w sygnaturze (uwzględniającą dodany wcześniej alias `module`).

---

## 3. WERYFIKACJA TESTAMI (TARGETED PYTEST)

Uruchomiono zestaw testów:
```powershell
.venv\Scripts\python.exe -m pytest tests/mcp/tools/test_get_artifacts_for_module.py tests/test_mcp_identity_resolution.py tests/test_mcp_documentation.py
```
**Wynik:**
```text
tests\mcp\tools\test_get_artifacts_for_module.py ....................    [ 37%]
tests\test_mcp_identity_resolution.py .........................          [ 84%]
tests\test_mcp_documentation.py ........                                 [100%]
======================== 53 passed, 1 warning in 4.83s ========================
```

Dodatkowo zweryfikowano testy kompatybilności wstecznej:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_mcp_split_s2c.py tests/test_mcp_regressions.py -k "test_get_artifacts_for_module_representation_and_progressive_disclosure"
```
**Wynik:** 39 passed (38 w `test_mcp_split_s2c.py` + 1 w `test_mcp_regressions.py`).

---

## 4. ARCHITECTURAL & BLAST RADIUS VERIFICATION (CONTEXTOR-FIRST)

Weryfikacja Contextor MCP:
- `get_file_edit_context(file_path="contextor/mcp/tools/get_artifacts_for_module.py", mode="minimal")`:
  - Moduł `contextor.mcp.tools.get_artifacts_for_module` (Layer: `adapter`).
  - `outbound_violation_count: 0`, `inbound_violation_count: 0`.
  - Konsumenci (`contextor.mcp_server`, `tests.test_mcp_regressions`, `tests.test_mcp_split_s2c`) pozostają stabilni.

---

## 5. DOKŁADNE DIFFY KODU (UNIFIED DIFFS)

### 1. `contextor/mcp/tools/get_artifacts_for_module.py`
```diff
--- a/contextor/mcp/tools/get_artifacts_for_module.py
+++ b/contextor/mcp/tools/get_artifacts_for_module.py
@@ -72,27 +72,45 @@ def get_artifacts_for_module(
             indent=2,
         )
 
-    # Normalise file-path input to dotted module name.
-    target_path = Path(module_name)
-    if target_path.is_absolute() or module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
-        if target_path.is_absolute():
-            try:
-                rel_path = target_path.relative_to(root)
-            except ValueError:
-                rel_path = target_path
-        else:
-            rel_path = target_path
-
-        parts = list(rel_path.parts)
-        if parts and parts[-1].endswith(".py"):
-            parts[-1] = parts[-1][:-3]
-            if parts[-1] == "__init__":
-                parts.pop()
-
-        module_name = ".".join(parts)
+    effective_module = module_name
 
     try:
         mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
+
+        # 1. RAW Module ID resolution
+        raw_resolution = query_helpers.resolve_module_identity(
+            effective_module,
+            mod_path_to_id,
+            mod_id_to_path,
+        )
+
+        if raw_resolution["status"] == "resolved" and raw_resolution.get("resolution") == "exact_id":
+            module_name = raw_resolution["module"]
+        elif raw_resolution["status"] == "not_found" and raw_resolution.get("query_kind") == "module_id":
+            return (
+                f"Module '{effective_module}' not found in registry or canonical LIVE state. "
+                "Check the module name or run an analysis."
+            )
+        else:
+            # 2. Textual Module Flow: Normalise file-path input to dotted module name.
+            target_path = Path(module_name)
+            if target_path.is_absolute() or module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
+                if target_path.is_absolute():
+                    try:
+                        rel_path = target_path.relative_to(root)
+                    except ValueError:
+                        rel_path = target_path
+                else:
+                    rel_path = target_path
+
+                parts = list(rel_path.parts)
+                if parts and parts[-1].endswith(".py"):
+                    parts[-1] = parts[-1][:-3]
+                    if parts[-1] == "__init__":
+                        parts.pop()
+
+                module_name = ".".join(parts)
+
         engine = mcp_runtime.get_or_init_engine(root)
         if not engine or getattr(engine.state, "resync_required", False):
             return "Error: No usable canonical LIVE state. Run analyze_project first."
@@ -109,9 +127,44 @@ def get_artifacts_for_module(
             mod_compact_id = getattr(live_module, "module_id", None)
             if mod_compact_id is None and isinstance(live_module, dict):
                 mod_compact_id = live_module.get("module_id")
+
+        if not mod_compact_id and live_module is None and not live_artifacts:
+            # 3. Textual Not-Found: shared fuzzy suggestions fallback
+            identity_resolution = query_helpers.resolve_module_identity(
+                module_name,
+                mod_path_to_id,
+                mod_id_to_path,
+            )
+            if identity_resolution["status"] == "resolved":
+                resolved_module = identity_resolution["module"]
+                unavailable = query_helpers.module_truth_unavailable(state, resolved_module)
+                if unavailable:
+                    return json.dumps(unavailable, indent=2)
+                resolved_artifacts = live_artifact_catalog.get(resolved_module, {})
+                resolved_id = mod_path_to_id.get(resolved_module)
+                resolved_live_module = live_modules.get(resolved_module)
+                if resolved_id or resolved_live_module is not None or resolved_artifacts:
+                    module_name = resolved_module
+                    mod_compact_id = resolved_id
+                    live_module = resolved_live_module
+                    live_artifacts = resolved_artifacts
+            elif (
+                identity_resolution["status"] == "not_found"
+                and identity_resolution.get("similar_candidates")
+            ):
+                return json.dumps(
+                    {
+                        "status": "not_found",
+                        "query": effective_module,
+                        "similar_candidates": identity_resolution["similar_candidates"],
+                        "data_source": "active_module_registry",
+                    },
+                    indent=2,
+                )
+
         if not mod_compact_id and live_module is None and not live_artifacts:
             return (
-                f"Module '{module_name}' not found in registry or canonical LIVE state. "
+                f"Module '{effective_module}' not found in registry or canonical LIVE state. "
                 "Check the module name or run an analysis."
             )
```

### 2. `contextor/mcp/docs/get_artifacts_for_module.json`
```diff
--- a/contextor/mcp/docs/get_artifacts_for_module.json
+++ b/contextor/mcp/docs/get_artifacts_for_module.json
@@ -5,7 +5,7 @@
     "[OPTIMIZED] Returns artifacts exported by a module with consumer information and progressive disclosure."
   ],
   "parameters": [
-    "``module_name`` (or alias ``module``) can be:\n- A full dotted module name: 'contextor.ui.gui_parser'\n- A file path relative to the repo root: 'contextor/ui/gui_parser.py'",
+    "``module_name`` (or alias ``module``) can be:\n- An exact active module ID: '259/1'\n- A full dotted module name: 'contextor.ui.gui_parser'\n- A file path relative to the repo root: 'contextor/ui/gui_parser.py'",
     "``include_consumers=True`` includes consumer counts and evidence. Set ``include_consumers=False`` for signatures-only view.",
     "``symbol_filter`` filters candidate artifacts by symbol name substring before limits and ranking.",
     "``limit`` bounds the maximum number of artifacts returned (default 50, pass ``None`` for unbounded). In default compact mode, output is capped at 10 salience-ranked artifacts.",
@@ -16,6 +16,7 @@
     "``representation`` controls nested consumer encoding: ``named`` (default module names), ``indexed`` (compact module IDs resolved via ``lookup_index_entries``), or ``auto`` (stateless negotiation returning decision prompt when identity compression yields substantial token savings)."
   ],
   "behavior": [
+    "Resolution order:\n1. Exact active module ID via active module registry.\n2. Path-to-dotted normalization and canonical LIVE state lookup.\n3. Bounded fuzzy module suggestions (score >= 0.75, max 5) from active module registry on textual not-found.\n4. Legacy not-found string fallback when query is not found or is a nonexistent module ID.",
     "In default compact mode (``compact=True``), returns up to 10 artifacts prioritized by consumer salience (``consumers.total DESC``, then alphabetical) with up to 3 nested consumer evidence items per artifact.",
     "Top-level ``truncated`` is truthful (``artifact_count < total_artifact_count``). When output is truncated by internal compact presentation cap, an executable ``expand`` descriptor is included preserving original requested limits.",
     "For complete lossless views, use ``compact=False, limit=None, evidence_limit=None`` with ``representation='named'`` or ``representation='indexed'``.",
```

### 3. `tests/mcp/tools/test_get_artifacts_for_module.py` [NEW]
```diff
--- /dev/null
+++ b/tests/mcp/tools/test_get_artifacts_for_module.py
@@ -0,0 +1,288 @@
+import json
+from types import SimpleNamespace
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.mcp import query_helpers, runtime as mcp_runtime
+from contextor.mcp.tools.get_artifacts_for_module import get_artifacts_for_module
+
+
+def _setup_test_state(monkeypatch):
+    """Sets up a minimal isolated RepositoryAnalysisState and active registry."""
+    module_obj = SimpleNamespace(module_id="10/1", path="pkg/mod_a.py", imports=[])
+    auth_module_obj = SimpleNamespace(module_id="13/1", path="pkg/services/auth.py", imports=[])
+    state = RepositoryAnalysisState(
+        modules={
+            "pkg.mod_a": module_obj,
+            "pkg.services.auth": auth_module_obj,
+        },
+        artifacts={
+            "pkg.mod_a": {
+                "own_symbols": ["my_func", "extra_func"],
+                "symbols": {
+                    "functions": ["my_func", "extra_func"],
+                },
+                "consumers": {
+                    "my_func": {
+                        "consumer_count": {"total": 2},
+                        "consumers": ["tests.test_1", "tests.test_2"],
+                    },
+                    "extra_func": {
+                        "consumer_count": {"total": 1},
+                        "consumers": ["tests.test_1"],
+                    },
+                },
+            },
+            "pkg.services.auth": {
+                "own_symbols": ["login"],
+                "symbols": {
+                    "functions": ["login"],
+                },
+                "consumers": {
+                    "login": {
+                        "consumer_count": {"total": 1},
+                        "consumers": ["tests.test_1"],
+                    }
+                },
+            },
+        },
+        artifact_consumption={
+            "pkg.mod_a::my_func": {
+                "consumers": ["tests.test_1", "tests.test_2"],
+                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
+            },
+            "pkg.mod_a::extra_func": {
+                "consumers": ["tests.test_1"],
+                "channels": {"tests.test_1": ["direct_calls"]},
+            },
+            "pkg.services.auth::login": {
+                "consumers": ["tests.test_1"],
+                "channels": {"tests.test_1": ["direct_calls"]},
+            },
+        },
+        artifact_consumption_state="fresh",
+    )
+    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
+    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
+    art_path_to_id = {
+        "pkg.mod_a::my_func": "A1/1",
+        "pkg.mod_a::extra_func": "A2/1",
+        "pkg.services.auth::login": "A3/1",
+    }
+    art_id_to_path = {v: k for k, v in art_path_to_id.items()}
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path))
+    return state
+
+
+def test_legacy_dotted_module_success(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module_name="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_legacy_path_normalization_success(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg/mod_a.py",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_module_alias_success(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_module_name_legacy_success(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module_name="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_both_aliases_identical_success(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module_name="pkg.mod_a",
+        module="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_alias_conflict_controlled_error(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module_name="pkg.mod_a",
+        module="pkg.mod_b",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "error"
+    assert res["error"] == "module_name and module must match when both are provided."
+
+
+def test_missing_both_controlled_error(tmp_path):
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+    )
+    res = json.loads(raw)
+    assert res["status"] == "error"
+    assert res["error"] == "module_name or module is required."
+
+
+def test_exact_module_id_via_module_alias(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="10/1",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert res["module_id"] == "10/1"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_exact_module_id_via_legacy_module_name(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module_name="10/1",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert res["module_id"] == "10/1"
+    assert "A1/1" in res["artifacts"]
+
+
+def test_nonexistent_module_id_never_fuzzy(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="9999/1",
+    )
+    assert raw == "Module '9999/1' not found in registry or canonical LIVE state. Check the module name or run an analysis."
+
+
+def test_fuzzy_dotted_typo_suggestions(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg.servces.auth",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "not_found"
+    assert res["query"] == "pkg.servces.auth"
+    assert res["data_source"] == "active_module_registry"
+    assert len(res["similar_candidates"]) > 0
+    top = res["similar_candidates"][0]
+    assert top["module"] == "pkg.services.auth"
+    assert top["module_id"] == "13/1"
+    assert top["score"] >= 0.75
+    assert "artifacts" not in res
+
+
+def test_fuzzy_path_typo_suggestions(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg/servces/auth.py",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "not_found"
+    assert res["query"] == "pkg/servces/auth.py"
+    assert len(res["similar_candidates"]) > 0
+    top = res["similar_candidates"][0]
+    assert top["module"] == "pkg.services.auth"
+    assert top["module_id"] == "13/1"
+    assert top["score"] >= 0.75
+
+
+def test_fuzzy_never_auto_resolves(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg.mod_aa",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "not_found"
+    assert "artifacts" not in res
+    assert len(res["similar_candidates"]) > 0
+
+
+def test_fuzzy_max_five_candidates(tmp_path, monkeypatch):
+    state = RepositoryAnalysisState(
+        artifacts={f"pkg.module_{i}": {"symbols": {}} for i in range(10)},
+        artifact_consumption={},
+        artifact_consumption_state="fresh",
+    )
+    mod_p2i = {f"pkg.module_{i}": f"{100+i}/1" for i in range(10)}
+    mod_i2p = {v: k for k, v in mod_p2i.items()}
+
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_p2i, mod_i2p, {}, {}))
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg.modul_x",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "not_found"
+    assert len(res["similar_candidates"]) <= 5
+
+
+def test_unrelated_query_exact_legacy_fallback(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="completely_unrelated_xyz",
+    )
+    assert raw == "Module 'completely_unrelated_xyz' not found in registry or canonical LIVE state. Check the module name or run an analysis."
+
+
+def test_exact_module_id_currentness_fail_closed(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    monkeypatch.setattr(
+        query_helpers,
+        "module_truth_unavailable",
+        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.mod_a" else None,
+    )
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="10/1",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "stale"
+    assert res["module"] == "pkg.mod_a"
+
+
+def test_exact_module_id_respects_presentation_controls(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="10/1",
+        compact=False,
+        limit=1,
+        representation="named",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    assert res["artifact_count"] == 1
+    assert res["truncated"] is True
+
+
+def test_valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    orig_resolve = query_helpers.resolve_module_identity
+    calls = []
+
+    def tracking_resolver(query, p2i, i2p):
+        calls.append(query)
+        return orig_resolve(query, p2i, i2p)
+
+    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    # RAW ID check is called once with "pkg.mod_a", but fuzzy fallback is NOT called
+    assert len(calls) == 1
+    assert calls[0] == "pkg.mod_a"
+
+
+def test_valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    orig_resolve = query_helpers.resolve_module_identity
+    calls = []
+
+    def tracking_resolver(query, p2i, i2p):
+        calls.append(query)
+        return orig_resolve(query, p2i, i2p)
+
+    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)
+
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg/mod_a.py",
+    )
+    res = json.loads(raw)
+    assert res["module"] == "pkg.mod_a"
+    # RAW ID check is called once with "pkg/mod_a.py", but fuzzy fallback is NOT called
+    assert len(calls) == 1
+    assert calls[0] == "pkg/mod_a.py"
+
+
+def test_original_query_preserved_and_candidate_structure(tmp_path, monkeypatch):
+    _setup_test_state(monkeypatch)
+    raw = get_artifacts_for_module(
+        repo_path=str(tmp_path),
+        module="pkg/servces/auth.py",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "not_found"
+    assert res["query"] == "pkg/servces/auth.py"
+    assert "similar_candidates" in res
+    candidate = res["similar_candidates"][0]
+    assert "module" in candidate
+    assert "module_id" in candidate
+    assert "score" in candidate
+    assert candidate["module"] == "pkg.services.auth"
+    assert candidate["module_id"] == "13/1"
+    assert isinstance(candidate["score"], float)
```

### 4. `tests/test_mcp_regressions.py`
```diff
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -5531,11 +5531,10 @@ def test_get_artifacts_for_module_representation_and_progressive_disclosure(
     from contextor.mcp import representation as mcp_rep
     import inspect
 
-    # 1. Signature check: representation is last parameter, default 'named'
+    # 1. Signature check: representation parameter present with default 'named'
     sig = inspect.signature(gam_tool.get_artifacts_for_module)
-    params = list(sig.parameters.values())
-    assert params[-1].name == "representation"
-    assert params[-1].default == "named"
+    assert "representation" in sig.parameters
+    assert sig.parameters["representation"].default == "named"
 
     # Unsupported representation error
     unsupported = json.loads(
```

---

## 6. STATUS OPERACYJNY

```text
FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifacts_for_module.py
- C:\Temp\Contextor_Repo\contextor\mcp\docs\get_artifacts_for_module.json
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_artifacts_for_module.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py

TESTS=53 passed in tests/mcp/tools/test_get_artifacts_for_module.py, tests/test_mcp_identity_resolution.py, tests/test_mcp_documentation.py (+ 39 compatibility regressions)

DEDICATED_TOOL_TEST_FILE_CREATED=YES
NEW_TESTS_ADDED_TO_MONOLITHIC_REGRESSION_FILE=NO

LEGACY_DOTTED_MODULE_UNCHANGED=PASS
LEGACY_PATH_NORMALIZATION_UNCHANGED=PASS
ALIAS_CONTRACT_UNCHANGED=PASS

EXACT_MODULE_ID=PASS
EXACT_MODULE_ID_LEGACY_PARAM=PASS
MISSING_MODULE_ID_NEVER_FUZZY=PASS

FUZZY_DOTTED_SUGGESTIONS=PASS
FUZZY_PATH_SUGGESTIONS=PASS
FUZZY_NEVER_AUTO_RESOLVES=PASS
FUZZY_MAX_5=PASS
LEGACY_NOT_FOUND_PRESERVED=PASS
ORIGINAL_QUERY_PRESERVED=PASS

CURRENTNESS_FAIL_CLOSED=PASS
PRESENTATION_CONTROLS_UNCHANGED=PASS
LOCAL_FUZZY_IMPLEMENTATION=NO

PUBLIC_SIGNATURE_CHANGED=NO
MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=PASS
```
