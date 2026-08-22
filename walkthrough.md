# TOKEN EFFICIENCY — STEP A15.3F5: APPLY EXACT FINAL PAIR-AWARE ENVELOPE PATCH

## FILES_CHANGED
1. `C:\Temp\Contextor_Repo\contextor\core\canonical_state_query\runtime.py`
2. `C:\Temp\Contextor_Repo\tests\test_canonical_state_contract.py`

---

## ACTUAL_DIFF
```diff
diff --git a/contextor/core/canonical_state_query/runtime.py b/contextor/core/canonical_state_query/runtime.py
index 05c56d7..c11b01c 100644
--- a/contextor/core/canonical_state_query/runtime.py
+++ b/contextor/core/canonical_state_query/runtime.py
@@ -137,8 +137,13 @@ def validate_request(request: Any) -> tuple[dict[str, Any] | None, dict[str, Any
     if not isinstance(request, dict):
         return None, _error("invalid_request", "Request must be an object.", "$request")
 
+    schema_version_hint = request.get("schema_version")
     language_version = request.get("language_version")
-    if language_version == LANGUAGE_VERSION_V1_1:
+    is_explicit_v1_1_pair = (
+        schema_version_hint == CANONICAL_QUERY_SCHEMA_VERSION_V1_1
+        and language_version == LANGUAGE_VERSION_V1_1
+    )
+    if is_explicit_v1_1_pair:
         allowed_keys = {
             "schema_version",
             "language_version",
diff --git a/tests/test_canonical_state_contract.py b/tests/test_canonical_state_contract.py
index e86e082..03998f5 100644
--- a/tests/test_canonical_state_contract.py
+++ b/tests/test_canonical_state_contract.py
@@ -767,3 +767,52 @@ def test_version_1_1_expand_exact_request_preservation():
     assert orig_req_b == copy_b, "Original request dict must not be mutated"
 
 
+def test_v1_1_evidence_limit_requires_explicit_supported_version_pair_before_envelope_expansion():
+    missing_schema = {
+        "language_version": "1.1",
+        "root": "modules",
+        "filters": [],
+        "select": [],
+        "evidence_limit": 3,
+    }
+    _, err_missing_schema = validate_request(missing_schema)
+    assert err_missing_schema is not None
+    assert err_missing_schema["error"]["code"] == "invalid_request"
+    assert err_missing_schema["error"]["path"] == "evidence_limit"
+    assert err_missing_schema["error"]["details"]["unknown_fields"] == [
+        "evidence_limit"
+    ]
+    missing_language = {
+        "schema_version": "1.1",
+        "root": "modules",
+        "filters": [],
+        "select": [],
+        "evidence_limit": 3,
+    }
+    _, err_missing_language = validate_request(missing_language)
+    assert err_missing_language is not None
+    assert err_missing_language["error"]["code"] == "invalid_request"
+    assert err_missing_language["error"]["path"] == "evidence_limit"
+    assert err_missing_language["error"]["details"]["unknown_fields"] == [
+        "evidence_limit"
+    ]
+    valid_v1_1 = {
+        "schema_version": "1.1",
+        "language_version": "1.1",
+        "root": "modules",
+        "filters": [],
+        "select": ["module_name"],
+        "evidence_limit": 3,
+    }
+    normalized, valid_error = validate_request(valid_v1_1)
+    assert valid_error is None
+    assert normalized is not None
+    assert normalized["evidence_limit"] == 3
+    unknown_v1_1 = {
+        **valid_v1_1,
+        "unsupported_field": True,
+    }
+    _, unknown_error = validate_request(unknown_v1_1)
+    assert unknown_error is not None
+    assert unknown_error["error"]["code"] == "invalid_request"
+    assert unknown_error["error"]["path"] == "unsupported_field"
```

---

## PAIR_AWARE_ENVELOPE_IMPLEMENTED
W `validate_request` (`runtime.py`) wprowadzono ścisły warunek:
`is_explicit_v1_1_pair = (schema_version_hint == CANONICAL_QUERY_SCHEMA_VERSION_V1_1 and language_version == LANGUAGE_VERSION_V1_1)`.
Zbiór `allowed_keys` zawierający `evidence_limit` jest aktywowany wyłącznie wtedy, gdy w żądaniu jawnie podano parę wersji `("1.1", "1.1")`. We wszystkich pozostałych przypadkach (w tym brak `schema_version` przy `language_version="1.1"` lub brak `language_version` przy `schema_version="1.1"`) pole `evidence_limit` jest natychmiast odrzucane z kodem `invalid_request` dla ścieżki `evidence_limit` jako błąd strukturalny w precedencji legacy.

---

## NEW_TEST_ADDED
Dodano test:
`test_v1_1_evidence_limit_requires_explicit_supported_version_pair_before_envelope_expansion`
Weryfikuje:
1. `missing_schema` z `evidence_limit=3` -> `invalid_request` dla `evidence_limit`.
2. `missing_language` z `evidence_limit=3` -> `invalid_request` dla `evidence_limit`.
3. Prawidłowe `valid_v1_1` z `evidence_limit=3` -> sukces walidacji i normalizacji (`evidence_limit=3`).
4. `unknown_v1_1` z nieobsługiwanym polem -> `invalid_request` dla `unsupported_field`.

---

## TARGETED_TEST_RESULT
- Polecenie: `.venv\Scripts\pytest.exe tests\test_canonical_state_contract.py -v`
- Wynik: **33 passed, 0 failed** (100% sukcesu).

---

## CONTEXTOR_POST_CHANGE_EVIDENCE
`get_file_edit_context` dla `runtime.py`:
`module_id="86/1"`, `layer="adapter"`, `public_api.total=2`, `imports.total=3`, `consumers.total=1`.

---

## LIVE_EVENT_EVIDENCE
Zdarzenia `desktop_watcher` w `get_live_events`:
- `revision=1206`: `UPDATED`, `contextor\core\canonical_state_query\runtime.py`
- `revision=1207`: `UPDATED`, `tests\test_canonical_state_contract.py`

---

## UNEXPECTED_SCOPE_CHANGES
`NONE`

---

## MCP_RESTART_REQUIRED=YES

---

## OPEN_P0
0

## OPEN_P1
0

## OPEN_P2
0

## OPEN_P3
0

---

## STEP_VERDICT
`PASS`

---

## NEXT_STEP_PROPOSAL
STEP A15.3 SOURCE CERTIFIED — manual MCP restart required before final runtime certification.
