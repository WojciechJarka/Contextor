# CONTEXTOR — MCP UX MICRO-FIX 5: `get_artifact_blast_radius` ALIAS (`artifact_name` & `artifact`) & MODULE REDIRECT
**Date:** 2026-08-23  
**Target:** `C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifact_blast_radius.py`  
**Status:** COMPLETED & VERIFIED

---

## 1. CEL I ZAŁOŻENIA REFAKTORYZACJI

Optymalizacja ergonomii wywołania narzędzia `get_artifact_blast_radius`:
1. **Alias parametru `artifact`:**
   - Obsługa `artifact: str | None = None` równolegle z legacy `artifact_name: str = ""`.
   - Normalizacja po `.strip()`.
   - Walidacja konfliktu: gdy oba są podane i niepuste, muszą być identyczne po `.strip()`; w przeciwnym razie zwracany jest kontrolowany błąd:
     ```json
     {
       "status": "error",
       "error": "artifact_name and artifact must match when both are provided."
     }
     ```
   - Walidacja wymaganej wartości: gdy brak obu lub oba są puste -> `{"status": "error", "error": "artifact_name or artifact is required."}`.
2. **Strukturalny `suggested_next_call` przy rozwiązaniu celu jako moduł:**
   - Gdy cel rozwiąże się do poziomu modułu (`top.get("kind") == "module"`), do odpowiedzi diagnostycznej dodawany jest maszynowo czytelny obiekt `suggested_next_call`:
     ```json
     "suggested_next_tool": "get_module_context",
     "suggested_next_call": {
         "tool": "get_module_context",
         "arguments": {
             "module": target_module
         }
     }
     ```
   - Zachowano wszystkie pozostałe pola odpowiedzi diagnostycznej (`resolved_as`, `module`, `module_id`, `artifact_candidates`, `warnings`).
   - Brak automatycznego dispatchu tool→tool; jest to wyłącznie podpowiedź kolejnego wywołania dla klienta MCP.

---

## 2. DOKONANE ZMIANY MECHANICZNE

### A. Produkcja (`contextor/mcp/tools/get_artifact_blast_radius.py`)
1. **Sygnatura:**
   ```python
   def get_artifact_blast_radius(
       repo_path: str,
       artifact_name: str = "",
       max_items: int | None = 30,
       compact: bool = True,
       fields: list[str] | None = None,
       representation: str = "named",
       artifact: str | None = None,
   ) -> str:
   ```
2. **Normalizacja i walidacja aliasu:**
   ```python
   root = Path(repo_path).expanduser().resolve()

   normalized_artifact_name = artifact_name.strip()
   normalized_artifact = artifact.strip() if artifact is not None else ""

   if (
       normalized_artifact_name
       and normalized_artifact
       and normalized_artifact_name != normalized_artifact
   ):
       return json.dumps(
           {
               "status": "error",
               "error": "artifact_name and artifact must match when both are provided.",
           },
           indent=2,
       )

   artifact_name = normalized_artifact or normalized_artifact_name
   if not artifact_name:
       return json.dumps(
           {
               "status": "error",
               "error": "artifact_name or artifact is required.",
           },
           indent=2,
       )
   ```
3. **Strukturalny redirect modułu:**
   ```python
                           "suggested_next_tool": "get_module_context",
                           "suggested_next_call": {
                               "tool": "get_module_context",
                               "arguments": {
                                   "module": target_module,
                               },
                           },
                           "artifact_candidates": {
   ```

### B. Dokumentacja MCP (`contextor/mcp/docs/get_artifact_blast_radius.json`)
- Zaktualizowano opis sekcji `parameters` o informację o aliasie `artifact`.
- Zaktualizowano sekcję `behavior` o informację o `suggested_next_call` przy rozwiązaniu celu jako moduł.

### C. Testy Regresyjne (`tests/test_mcp_split_s2c.py`, `tests/test_mcp_documentation.py`, `tests/test_mcp_regressions.py`)
- Zaktualizowano sygnatury w `_EXPECTED_SIGNATURES`, `LEGACY_SIGNATURES` oraz asercję `param_names` w `test_mcp_regressions.py`.
- Dodano 8 dedykowanych testów regresyjnych w `tests/test_mcp_split_s2c.py`:
  1. `test_get_artifact_blast_radius_legacy_artifact_name`
  2. `test_get_artifact_blast_radius_alias_artifact`
  3. `test_get_artifact_blast_radius_matching_both`
  4. `test_get_artifact_blast_radius_conflicting_alias_returns_error`
  5. `test_get_artifact_blast_radius_missing_both_returns_error`
  6. `test_get_artifact_blast_radius_module_redirect_preserves_structure_and_suggested_next_call`
  7. `test_get_artifact_blast_radius_regular_artifact_does_not_contain_module_redirect`
  8. `test_get_artifact_blast_radius_preserves_max_items_compact_and_representation`

---

## 3. WERYFIKACJA TESTAMI (TARGETED PYTEST)

Uruchomiono celowane testy regresyjne:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_mcp_split_s2c.py tests/test_mcp_documentation.py -k blast_radius tests/test_mcp_regressions.py
```
**Wynik:** `34 passed in test_mcp_split_s2c.py & test_mcp_documentation.py, 6 passed in test_mcp_regressions.py` (100% sukcesu).

---

## 4. ARCHITECTURAL & BLAST RADIUS VERIFICATION (CONTEXTOR-FIRST)

Weryfikacja przez Contextor MCP:
1. `get_file_edit_context(file_path="contextor/mcp/tools/get_artifact_blast_radius.py", mode="minimal")`:
   - Moduł `contextor.mcp.tools.get_artifact_blast_radius` (Layer: `adapter`).
   - `outbound_violation_count: 0`, `inbound_violation_count: 0`.
   - Konsumenci: `contextor.mcp_server`, `tests.test_mcp_regressions`, `tests.test_mcp_split_s2c`.
2. `get_artifact_blast_radius(artifact_name="contextor.mcp.tools.get_artifact_blast_radius::get_artifact_blast_radius")`:
   - Konsumenci: `contextor.mcp_server`, `tests.test_mcp_regressions`, `tests.test_mcp_split_s2c`.
   - Potwierdzono brak naruszeń granic architektonicznych i stabilność pozostałych kontraktów.

---

## 5. DOKŁADNE DIFFY KODU (UNIFIED DIFFS)

### 1. `contextor/mcp/tools/get_artifact_blast_radius.py`
```diff
--- a/contextor/mcp/tools/get_artifact_blast_radius.py
+++ b/contextor/mcp/tools/get_artifact_blast_radius.py
@@ -190,11 +190,12 @@ def _consumers_collection_view(
 
 def get_artifact_blast_radius(
     repo_path: str,
-    artifact_name: str,
+    artifact_name: str = "",
     max_items: int | None = 30,
     compact: bool = True,
     fields: list[str] | None = None,
     representation: str = "named",
+    artifact: str | None = None,
 ) -> str:
     if representation not in _ALLOWED_REPRESENTATIONS:
         return json.dumps(
@@ -206,6 +207,33 @@ def get_artifact_blast_radius(
             indent=2,
         )
     root = Path(repo_path).expanduser().resolve()
+
+    normalized_artifact_name = artifact_name.strip()
+    normalized_artifact = artifact.strip() if artifact is not None else ""
+
+    if (
+        normalized_artifact_name
+        and normalized_artifact
+        and normalized_artifact_name != normalized_artifact
+    ):
+        return json.dumps(
+            {
+                "status": "error",
+                "error": "artifact_name and artifact must match when both are provided.",
+            },
+            indent=2,
+        )
+
+    artifact_name = normalized_artifact or normalized_artifact_name
+    if not artifact_name:
+        return json.dumps(
+            {
+                "status": "error",
+                "error": "artifact_name or artifact is required.",
+            },
+            indent=2,
+        )
+
     try:
         mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
         engine = mcp_runtime.get_or_init_engine(root)
@@ -533,6 +561,12 @@ def get_artifact_blast_radius(
                             "module": target_module,
                             "module_id": target_module_id,
                             "suggested_next_tool": "get_module_context",
+                            "suggested_next_call": {
+                                "tool": "get_module_context",
+                                "arguments": {
+                                    "module": target_module,
+                                },
+                            },
                             "artifact_candidates": {
                                 "total": total,
                                 "items": items,
```

### 2. `contextor/mcp/docs/get_artifact_blast_radius.json`
```diff
--- a/contextor/mcp/docs/get_artifact_blast_radius.json
+++ b/contextor/mcp/docs/get_artifact_blast_radius.json
@@ -5,10 +5,10 @@
     "[OPTIMIZED] Resolves direct, evidence-backed consumers of an artifact.\nUses canonical LIVE artifact and symbol-consumption facts. It does not\nread output reports and does not claim that dynamic Python usage can be\nproven exact."
   ],
   "parameters": [
-    "``consumers`` always contains ``total`` and ``truncated`` (true whenever fewer identities are present than ``total``). The default compact response (``compact=True``) provides bounded named evidence up to 3 consumers (or ``max_items`` if smaller) in ``evidence``; set ``compact=False`` for full items up to ``max_items`` in ``items``.\nPass ``compact=False, max_items=None, representation='named'`` for lossless named consumers, or ``representation='indexed'`` for lossless indexed consumers.\n``representation`` controls encoding of consumers: ``named`` (default, full module names),\n``indexed`` (compact module IDs with metadata indicating ``resolve_via=\"lookup_index_entries\"``, fails closed without mixed identities if mapping is incomplete),\nor ``auto`` (stateless byte-based negotiation returning direct named for compact requests or when byte savings do not justify negotiation, and a structured ``representation_decision_required`` union with exact candidate sizes and directly executable retry ``options`` when material serialized byte savings are detected).\n``options`` in decision responses contains directly executable kwargs for ``get_artifact_blast_radius`` (e.g. ``options.indexed`` preserves explicit ``fields`` and does not contain ``resolve_via``).\n``expand`` provides exact continuation parameters when truncated, preserving the requested representation and explicit ``fields`` projection.\n``fields`` projects top-level keys after representation shaping; omitting ``consumers`` skips consumer negotiation entirely. Allowed values are ``artifact``, ``artifact_id``, ``kind``, ``definer``, ``architecture``, ``downstream_module_reachability``, ``consumers``, ``evidence_scope``, and ``data_source``."
+    "Supply ``artifact_name`` or alias ``artifact``.\n``consumers`` always contains ``total`` and ``truncated`` (true whenever fewer identities are present than ``total``). The default compact response (``compact=True``) provides bounded named evidence up to 3 consumers (or ``max_items`` if smaller) in ``evidence``; set ``compact=False`` for full items up to ``max_items`` in ``items``.\nPass ``compact=False, max_items=None, representation='named'`` for lossless named consumers, or ``representation='indexed'`` for lossless indexed consumers.\n``representation`` controls encoding of consumers: ``named`` (default, full module names),\n``indexed`` (compact module IDs with metadata indicating ``resolve_via=\"lookup_index_entries\"``, fails closed without mixed identities if mapping is incomplete),\nor ``auto`` (stateless byte-based negotiation returning direct named for compact requests or when byte savings do not justify negotiation, and a structured ``representation_decision_required`` union with exact candidate sizes and directly executable retry ``options`` when material serialized byte savings are detected).\n``options`` in decision responses contains directly executable kwargs for ``get_artifact_blast_radius`` (e.g. ``options.indexed`` preserves explicit ``fields`` and does not contain ``resolve_via``).\n``expand`` provides exact continuation parameters when truncated, preserving the requested representation and explicit ``fields`` projection.\n``fields`` projects top-level keys after representation shaping; omitting ``consumers`` skips consumer negotiation entirely. Allowed values are ``artifact``, ``artifact_id``, ``kind``, ``definer``, ``architecture``, ``downstream_module_reachability``, ``consumers``, ``evidence_scope``, and ``data_source``."
   ],
   "behavior": [
-    "Candidate, consumer & reachability semantics:\n  - If a module name or module ID is passed, returns a structured diagnostic with deterministic public-first ranked artifact candidates defined by that module.\n  - ``consumers``: Direct static symbol consumers with confirmed references.\n  - ``architecture``:\n      * ``definer_layer``: Canonical architectural layer of the defining module.\n      * ``consumer_layers``: Sorted list of unique known canonical layers of direct consumers.\n      * ``same_module_consumer_count``: Unique direct consumers in the same module.\n      * ``same_layer_consumer_count``: Unique direct consumers in the same layer (excluding same-module).\n      * ``cross_layer_consumer_count``: Unique direct NON-TEST consumers whose canonical layer differs from ``definer_layer``.\n      * ``test_consumer_count``: Unique direct consumers whose canonical layer is \"tests\".\n      * ``cross_layer_consumers``: Boolean indicating if ``cross_layer_consumer_count > 0``.\n      * ``cross_layer_sample``: Bounded sample of cross-layer production consumers (excluding tests).\n  - ``downstream_module_reachability``:\n      Conservative module-level downstream reachability seeded by confirmed direct symbol consumer modules.\n      It does not represent transitive symbol-to-symbol consumption."
+    "Candidate, consumer & reachability semantics:\n  - If a module name or module ID is passed, returns a structured diagnostic with deterministic public-first ranked artifact candidates defined by that module and ``suggested_next_call`` to ``get_module_context``.\n  - ``consumers``: Direct static symbol consumers with confirmed references.\n  - ``architecture``:\n      * ``definer_layer``: Canonical architectural layer of the defining module.\n      * ``consumer_layers``: Sorted list of unique known canonical layers of direct consumers.\n      * ``same_module_consumer_count``: Unique direct consumers in the same module.\n      * ``same_layer_consumer_count``: Unique direct consumers in the same layer (excluding same-module).\n      * ``cross_layer_consumer_count``: Unique direct NON-TEST consumers whose canonical layer differs from ``definer_layer``.\n      * ``test_consumer_count``: Unique direct consumers whose canonical layer is \"tests\".\n      * ``cross_layer_consumers``: Boolean indicating if ``cross_layer_consumer_count > 0``.\n      * ``cross_layer_sample``: Bounded sample of cross-layer production consumers (excluding tests).\n  - ``downstream_module_reachability``:\n      Conservative module-level downstream reachability seeded by confirmed direct symbol consumer modules.\n      It does not represent transitive symbol-to-symbol consumption."
   ],
   "freshness": [],
   "errors": [],
```

### 3. `tests/test_mcp_documentation.py`
```diff
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -18,1 +18,1 @@ LEGACY_SIGNATURES = {
-    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named') -> str",
+    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', artifact: str | None = None) -> str",
```

### 4. `tests/test_mcp_split_s2c.py`
```diff
--- a/tests/test_mcp_split_s2c.py
+++ b/tests/test_mcp_split_s2c.py
@@ -39,1 +39,1 @@ _EXPECTED_SIGNATURES = {
-    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named') -> str",
+    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', artifact: str | None = None) -> str",
@@ -403,0 +403,143 @@ def test_get_artifacts_for_module_preserves_limit_compact_and_representation(tmp
+
+def _setup_blast_radius_state(monkeypatch):
+    from types import SimpleNamespace
+    from contextor.core.analysis.state_manager import RepositoryAnalysisState
+    from contextor.mcp import query_helpers, runtime as mcp_runtime
+
+    state = RepositoryAnalysisState(
+        artifacts={
+            "pkg.mod_a": {
+                "own_symbols": ["my_func"],
+                "symbols": {
+                    "functions": ["my_func"],
+                },
+                "consumers": {
+                    "my_func": {
+                        "consumer_count": {"total": 2},
+                        "consumers": ["tests.test_1", "tests.test_2"],
+                    }
+                },
+            },
+        },
+        artifact_consumption={
+            "pkg.mod_a::my_func": {
+                "consumers": ["tests.test_1", "tests.test_2"],
+                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
+            }
+        },
+        artifact_consumption_state="fresh",
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    monkeypatch.setattr(
+        query_helpers,
+        "read_registries",
+        lambda _root: ({"pkg.mod_a": "M1"}, {"M1": "pkg.mod_a"}, {"pkg.mod_a::my_func": "A1"}, {"A1": "pkg.mod_a::my_func"}),
+    )
+    return state
+
+
+def test_get_artifact_blast_radius_legacy_artifact_name(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact_name="pkg.mod_a::my_func",
+    )
+    res = json.loads(raw)
+    assert res["artifact"] == "pkg.mod_a::my_func"
+
+
+def test_get_artifact_blast_radius_alias_artifact(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact="pkg.mod_a::my_func",
+    )
+    res = json.loads(raw)
+    assert res["artifact"] == "pkg.mod_a::my_func"
+
+
+def test_get_artifact_blast_radius_matching_both(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact_name="pkg.mod_a::my_func",
+        artifact="pkg.mod_a::my_func",
+    )
+    res = json.loads(raw)
+    assert res["artifact"] == "pkg.mod_a::my_func"
+
+
+def test_get_artifact_blast_radius_conflicting_alias_returns_error(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact_name="pkg.mod_a::my_func",
+        artifact="different",
+    )
+    res = json.loads(raw)
+    assert res["status"] == "error"
+    assert res["error"] == "artifact_name and artifact must match when both are provided."
+
+
+def test_get_artifact_blast_radius_missing_both_returns_error(tmp_path):
+    import json
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+    )
+    res = json.loads(raw)
+    assert res["status"] == "error"
+    assert res["error"] == "artifact_name or artifact is required."
+
+
+def test_get_artifact_blast_radius_module_redirect_preserves_structure_and_suggested_next_call(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact="pkg.mod_a",
+    )
+    res = json.loads(raw)
+    assert res["resolved_as"] == "module"
+    assert res["module"] == "pkg.mod_a"
+    assert res["module_id"] == "M1"
+    assert res["suggested_next_tool"] == "get_module_context"
+    assert res["suggested_next_call"] == {
+        "tool": "get_module_context",
+        "arguments": {"module": "pkg.mod_a"},
+    }
+    assert "artifact_candidates" in res
+    assert res["artifact_candidates"]["total"] == 1
+
+
+def test_get_artifact_blast_radius_regular_artifact_does_not_contain_module_redirect(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact="pkg.mod_a::my_func",
+    )
+    res = json.loads(raw)
+    assert "resolved_as" not in res
+    assert "suggested_next_tool" not in res
+    assert "suggested_next_call" not in res
+
+
+def test_get_artifact_blast_radius_preserves_max_items_compact_and_representation(tmp_path, monkeypatch):
+    import json
+    _setup_blast_radius_state(monkeypatch)
+    raw = get_artifact_blast_radius(
+        repo_path=str(tmp_path),
+        artifact="pkg.mod_a::my_func",
+        compact=False,
+        max_items=1,
+        representation="named",
+    )
+    res = json.loads(raw)
+    assert res["consumers"]["total"] == 2
+    assert res["consumers"]["truncated"] is True
+    assert len(res["consumers"]["items"]) == 1
```

### 5. `tests/test_mcp_regressions.py`
```diff
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -5008,1 +5008,1 @@ def test_blast_radius_consumer_representation_and_progressive_disclosure(
-    assert param_names == ["repo_path", "artifact_name", "max_items", "compact", "fields", "representation"]
+    assert param_names == ["repo_path", "artifact_name", "max_items", "compact", "fields", "representation", "artifact"]
```

---

## 6. STATUS OPERACYJNY

```text
FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_artifact_blast_radius.py
- C:\Temp\Contextor_Repo\contextor\mcp\docs\get_artifact_blast_radius.json
- C:\Temp\Contextor_Repo\tests\test_mcp_split_s2c.py
- C:\Temp\Contextor_Repo\tests\test_mcp_documentation.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py

TESTS=34 passed in test_mcp_split_s2c.py & test_mcp_documentation.py, 6 passed in test_mcp_regressions.py
MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO
VERDICT=PASS
```
