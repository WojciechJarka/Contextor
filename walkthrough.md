# CONTEXTOR — F2G2 search_artifacts RUNTIME CERTIFICATION
**Date:** 2026-08-26  
**Mode:** READ-ONLY (LIVE MCP RUNTIME CERTIFICATION)  
**Target:** `search_artifacts`  
**Files Changed By This Step:** NONE  
**Status:** CERTIFIED & VERIFIED (FINAL_PASS)

---

## 1. RUNTIME CERTIFICATION EVIDENCE (LIVE MCP EXECUTIONS)

### 1. Runtime Freshness & Public Schema (`get_mcp_documentation`)
- **Call:** `get_mcp_documentation(tool="search_artifacts")`
- **Output:** Potwierdzono nową sygnaturę i opis toola:
  - `repo_path: str`
  - `search_term: str | None = None` (opcjonalny parametr zapytania, `""` to match-all, brak automatycznego usuwania whitespace)
  - `limit: int | None = 20` (`None` dla wyszukiwania nieograniczonego, `max_items` niewspierany)
  - `evidence_limit: int | None = 20`
  - `compact: bool = True`
  - `fields: list[str] | None = None`
  - `query: str | None = None` (alias dla `search_term`, wymagana zgodność dokładna, gdy oba są podane)

### 2. Dual Search Consistency (`search_term` vs `query`)
- **Call A:** `search_artifacts(search_term="query_helpers")`
  - `match_count: 1`, `total_matches: 1`, `query: "query_helpers"`, znaleziono moduł `contextor.mcp.query_helpers`.
- **Call B:** `search_artifacts(query="query_helpers")`
  - `match_count: 1`, `total_matches: 1`, `query: "query_helpers"`, identyczny wynik.

### 3. Both Parameters Provided & Matching
- **Call:** `search_artifacts(search_term="query_helpers", query="query_helpers")`
- **Output:** `status: "ok"`, `match_count: 1`, `total_matches: 1`, normalny sukces wyszukiwania.

### 4. Conflicting Parameters Fail-Closed
- **Call:** `search_artifacts(search_term="query_helpers", query="runtime")`
- **Output:**
  ```json
  {
    "status": "error",
    "error": "search_term and query must match when both are provided."
  }
  ```

### 5. Missing Both Parameters Fail-Closed
- **Call:** `search_artifacts()`
- **Output:**
  ```json
  {
    "status": "error",
    "error": "search_term or query is required."
  }
  ```

### 6. Empty Alias Match-All (`query=""`)
- **Call:** `search_artifacts(query="", limit=1)`
- **Output:** `query: ""`, `total_matches: 2984`, `match_count: 1`, `truncated: true`.

### 7. Whitespace Literal Preservation
- **Call:** `search_artifacts(query="   ")`
- **Output:** `"No live modules or artifacts found matching '   '."` (literalne wyszukiwanie spacji, brak spłaszczenia do pustego ciągu).

### 8. Limit Sanity (`limit=None`)
- **Call:** `search_artifacts(query="", limit=None)`
- **Output:** `query: ""`, `match_count: 2984`, `total_matches: 2984`, `truncated: false` (`match_count == total_matches`).

---

## 2. STATUS OPERACYJNY

```text
RUNTIME_SCHEMA_FRESH=YES
QUERY_ALIAS_RUNTIME=PASS
BOTH_SAME_RUNTIME=PASS
CONFLICT_RUNTIME=PASS
MISSING_BOTH_RUNTIME=PASS
EMPTY_QUERY_RUNTIME=PASS
WHITESPACE_RUNTIME=PASS
LIMIT_NONE_RUNTIME=PASS

FILES_CHANGED=NONE
DIFFS=NONE

VERDICT=FINAL_PASS
```
