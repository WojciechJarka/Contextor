# CONTEXTOR — F2E1 get_symbol_implementation — RUNTIME CERTIFICATION
**Date:** 2026-08-23  
**Mode:** READ-ONLY (LIVE MCP RUNTIME CERTIFICATION)  
**Target:** `get_symbol_implementation`  
**Files Changed By This Step:** NONE  
**Status:** CERTIFIED & VERIFIED (PASS)

---

## 1. RUNTIME CERTIFICATION EVIDENCE (LIVE MCP EXECUTIONS)

### 1. Runtime Freshness & Documentation (`get_mcp_documentation`)
- **Call:** `get_mcp_documentation(tool="get_symbol_implementation")`
- **Output:** Potwierdzono aktualną sygnaturę i dokumentację:
  - Obsługa exact active artifact ID (`A2496/1`), canonical qualified identity (`module::symbol`), plain leaf.
  - Zasada pierwszeństwa ograniczenia plikowego (`file_paths` / `file_path` wins).
  - Wyprowadzanie kanonicznej ścieżki ze stanu modułów LIVE w przypadku braku ograniczenia plikowego dla ID i qualified identity.
  - Bounded scoped fuzzy suggestions (max 5, score >= 0.75, suggestion-only) z `active_artifact_registry`.
  - Missing artifact ID never returns fuzzy suggestions.
  - Progi smart auto: `<=5120 B` fetch / `>5120 B` preview.

### 2. Real Active Artifact Identification
- **Artifact:** `contextor.mcp.query_helpers::resolve_module_identity`
- **Active ID:** `A2496/1`
- **Definer Module:** `contextor.mcp.query_helpers`
- **Canonical Source Path:** `contextor/mcp/query_helpers.py`

### 3. Exact Artifact ID + Explicit Correct File
- **Call:** `get_symbol_implementation(symbol="A2496/1", file_path="contextor/mcp/query_helpers.py")`
- **Output:**
  ```json
  {
    "status": "resolved",
    "mode": "fetch",
    "resolution": {
      "symbol": "resolve_module_identity",
      "file_path": "C:\\Temp\\Contextor_Repo\\contextor\\mcp\\query_helpers.py",
      "kind": "function",
      "lines": {
        "start": 96,
        "end": 159
      }
    },
    "implementation": "def resolve_module_identity(..."
  }
  ```

### 4. Lowercase Artifact ID
- **Call:** `get_symbol_implementation(symbol="a2496/1", file_path="contextor/mcp/query_helpers.py")`
- **Output:** Identyczny kanoniczny sukces `status: "resolved"`, symbol `resolve_module_identity`.

### 5. Exact Artifact ID Without File Constraint (Inferred Canonical LIVE Path)
- **Call:** `get_symbol_implementation(symbol="A2496/1")`
- **Output:** Narzędzie automatycznie wyznaczyło ścieżkę źródłową `contextor/mcp/query_helpers.py` ze stanu kanonicznego LIVE i zwróciło pełną implementację bez konieczności ręcznego podawania `file_path`.

### 6. Exact Artifact ID + Wrong Explicit File
- **Call:** `get_symbol_implementation(symbol="A2496/1", file_path="contextor/core/source.py")`
- **Output:**
  ```json
  {
    "status": "not_found",
    "symbol": "A2496/1",
    "searched_files": [
      "contextor/core/source.py"
    ],
    "message": "Resolved artifact is outside the requested file constraints.",
    "resolved_artifact": "contextor.mcp.query_helpers::resolve_module_identity",
    "artifact_id": "A2496/1",
    "definer_module": "contextor.mcp.query_helpers"
  }
  ```

### 7. Missing Syntactic Artifact ID
- **Call:** `get_symbol_implementation(symbol="A99999/1", file_path="contextor/mcp/query_helpers.py")`
- **Output:** `{"status": "not_found", "symbol": "A99999/1", "message": "Artifact 'A99999/1' not found in the active registry."}` (brak fuzzy, brak pobierania implementacji).

### 8. Qualified Canonical Identity (`module::symbol`)
- **Call A (bez pliku):** `get_symbol_implementation(symbol="contextor.mcp.query_helpers::resolve_module_identity")` -> `status: "resolved"`, inferred path.
- **Call B (z poprawnym plikiem):** `get_symbol_implementation(symbol="contextor.mcp.query_helpers::resolve_module_identity", file_path="contextor/mcp/query_helpers.py")` -> `status: "resolved"`.

### 9. Wrong Qualified Module Prefix (Identity Enforcement)
- **Call:** `get_symbol_implementation(symbol="wrong.module::resolve_module_identity", file_path="contextor/mcp/query_helpers.py")`
- **Output:** `status: "not_found"` z sugestią fuzzy; narzędzie **nie** zwróciło fałszywego sukcesu z podanego pliku.

### 10. Plain Leaf Legacy & Missing Files Fail-Closed
- **Call A (z plikiem):** `get_symbol_implementation(symbol="resolve_module_identity", file_path="contextor/mcp/query_helpers.py")` -> `status: "resolved"`.
- **Call B (bez pliku):** `get_symbol_implementation(symbol="resolve_module_identity")` -> `{"status": "error", "error": "At least one Python source file is required."}`.

### 11. Scoped Fuzzy Typo with Explicit File
- **Call:** `get_symbol_implementation(symbol="resolve_modul_identity", file_path="contextor/mcp/query_helpers.py")`
- **Output:** `status: "not_found"`, `similar_candidates: [{"artifact": "contextor.mcp.query_helpers::resolve_module_identity", "artifact_id": "A2496/1", "score": 0.9778}]`, `data_source: "active_artifact_registry"`.

### 12. Qualified Fuzzy Without File
- **Call:** `get_symbol_implementation(symbol="contextor.mcp.query_helpers::resolve_modul_identity")`
- **Output:** `status: "not_found"` z globalnymi sugestiami z aktywnego rejestru (score >= 0.75, max 5, suggestion-only).

### 13. Auto Pipeline (Preview & Fetch Modes on Artifact ID)
- **Auto (<=5120 B):** Zwraca pełny kod (`mode: "fetch"`).
- **Preview:** `get_symbol_implementation(symbol="A2496/1", mode="preview")` -> `mode: "preview"`, metadane i `fetch_plans`.
- **Explicit Fetch:** `get_symbol_implementation(symbol="A2496/1", mode="fetch", include=["signature"])` -> `mode: "fetch"`, `signature` only.

### 14. File Alias Contract
- `file_path`: PASS
- `file_paths`: PASS
- `file_path` + `file_paths` (merge/dedupe): PASS

---

## 2. STATUS OPERACYJNY

```text
MCP_SERVER_RELOADED=YES
TOOL_RUNTIME_VERSION_CURRENT=YES
TOOL_SCHEMA_CURRENT=YES
TOOL_DOCUMENTATION_CURRENT=YES

TEST_ARTIFACT=contextor.mcp.query_helpers::resolve_module_identity
TEST_ARTIFACT_ID=A2496/1
TEST_SOURCE_PATH=contextor/mcp/query_helpers.py

EXACT_ID_EXPLICIT_FILE_RUNTIME=PASS
LOWERCASE_ID_RUNTIME=PASS
EXACT_ID_NO_FILE_RUNTIME=PASS
ID_WRONG_FILE_FAIL_CLOSED_RUNTIME=PASS
MISSING_ID_NEVER_FUZZY_RUNTIME=PASS

QUALIFIED_IDENTITY_NO_FILE_RUNTIME=PASS
QUALIFIED_IDENTITY_EXPLICIT_FILE_RUNTIME=PASS
WRONG_MODULE_PREFIX_NO_FALSE_SUCCESS_RUNTIME=PASS

PLAIN_LEAF_EXPLICIT_FILE_RUNTIME=PASS
PLAIN_LEAF_NO_FILE_LEGACY_RUNTIME=PASS

SCOPED_FUZZY_RUNTIME=PASS
SCOPED_FUZZY_OUT_OF_SCOPE_EXCLUDED_RUNTIME=PASS
QUALIFIED_FUZZY_NO_FILE_RUNTIME=PASS
FUZZY_MAX_5_RUNTIME=PASS
FUZZY_NEVER_AUTO_RESOLVES_RUNTIME=PASS

AMBIGUITY_RUNTIME=NOT_EXERCISED

AUTO_SMALL_ID_RUNTIME=PASS
EXPLICIT_PREVIEW_ID_RUNTIME=PASS
EXPLICIT_FETCH_ID_RUNTIME=PASS
AUTO_BOUNDARY_RUNTIME=UNIT_CERTIFIED_5120_5121

FILE_ALIAS_RUNTIME=PASS

CURRENTNESS_RUNTIME=NOT_EXERCISED
NO_ENGINE_RUNTIME=NOT_EXERCISED

FILES_CHANGED=NONE
DIFFS=NONE

VERDICT=PASS
```
