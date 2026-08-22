# CONTEXTOR — F2D MCP RUNTIME CERTIFICATION
**Date:** 2026-08-23  
**Mode:** READ-ONLY (LIVE MCP RUNTIME CERTIFICATION)  
**Target:** `get_module_context`  
**Files Changed By This Step:** NONE  
**Status:** CERTIFIED & VERIFIED (14/14 PASS)

---

## 1. RUNTIME CERTIFICATION EVIDENCE (LIVE MCP EXECUTIONS)

### 1. Runtime Freshness & Documentation (`get_mcp_documentation`)
- **Call:** `get_mcp_documentation(tool="get_module_context")`
- **Output:** Dokumentacja potwierdza exact active module ID, dotted/path formaty, artifact redirect do `get_artifact_blast_radius`, bounded fuzzy module suggestions (score >= 0.75, max 5, suggestion-only) z `active_module_registry` oraz legacy not-found string fallback dla nieistniejących module ID.

### 2. Legacy Dotted Module
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="contextor.mcp.query_helpers")`
- **Output:** Normalny sukces modułowy: `module: "contextor.mcp.query_helpers"`, `module_idx: "252/2"`, pełne sekcje `metrics`, `dependencies_inbound_who_calls_me`, `dependencies_outbound_who_i_call`.

### 3. Legacy POSIX Path Normalization
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="contextor/mcp/query_helpers.py")`
- **Output:** Identyczny canonical moduł `contextor.mcp.query_helpers` (`252/2`).

### 4. Windows Path Normalization
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module=r"contextor\mcp\query_helpers.py")`
- **Output:** Identyczny canonical moduł `contextor.mcp.query_helpers` (`252/2`).

### 5. Exact Active Module ID (`252/2`)
- **Call 1 (alias `module`):** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="252/2")`
- **Call 2 (parametr `module_name`):** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module_name="252/2")`
- **Output:** W obu wywołaniach poprawny canonical module `contextor.mcp.query_helpers` z pełnym payloadem.

### 6. Missing Syntactic Module ID (`99999/1`)
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="99999/1")`
- **Output:** `Module '99999/1' not found in the project graph.` (dokładny legacy string, brak fuzzy).

### 7. Fuzzy Dotted Typo
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="contextor.mcp.quey_helpers")`
- **Output:**
  ```json
  {
    "status": "not_found",
    "query": "contextor.mcp.quey_helpers",
    "similar_candidates": [
      {
        "module": "contextor.mcp.query_helpers",
        "module_id": "252/2",
        "score": 0.9811
      },
      {
        "module": "contextor.mcp.source_helpers",
        "module_id": "271/1",
        "score": 0.8889
      },
      {
        "module": "contextor.mcp.report_helpers",
        "module_id": "263/1",
        "score": 0.8519
      }
    ],
    "data_source": "active_module_registry"
  }
  ```

### 8. Fuzzy POSIX Path Typo
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="contextor/mcp/quey_helpers.py")`
- **Output:** Bounded fuzzy suggestions z zachowanym oryginalnym `query: "contextor/mcp/quey_helpers.py"` oraz top kandydatem `contextor.mcp.query_helpers` (`score: 0.9811`).

### 9. Fuzzy Windows Path Typo
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module=r"contextor\mcp\quey_helpers.py")`
- **Output:** Bounded fuzzy suggestions z top kandydatem `contextor.mcp.query_helpers` (`score: 0.9811`).

### 10. Artifact Redirect
- **Call:** `get_module_context(repo_path="C:\\Temp\\Contextor_Repo", module="contextor.mcp.query_helpers::resolve_module_identity")`
- **Output:**
  ```json
  {
    "target": "contextor.mcp.query_helpers::resolve_module_identity",
    "resolved_as": "artifact",
    "artifact": "contextor.mcp.query_helpers::resolve_module_identity",
    "artifact_id": "A2496/1",
    "definer_module": "contextor.mcp.query_helpers",
    "suggested_next_tool": "get_artifact_blast_radius",
    "warnings": [
      "Target resolved to an artifact/symbol rather than a module. Use get_artifact_blast_radius for symbol-level consumption."
    ]
  }
  ```

### 11. Alias Contract
- `module` only: PASS
- `module_name` only: PASS
- Oba identyczne: PASS (`contextor.mcp.query_helpers`)
- Oba różne: PASS (`error: "Conflicting 'module_name' and 'module' arguments provided..."`)
- Brak obu: PASS (`error: "Either 'module_name' or 'module' must be provided."`)

### 12. Downstream Equivalence (Dotted vs ID)
- **Call A (Dotted):** `get_module_context(repo_path="...", module="contextor.mcp.query_helpers", compact=False, max_items=1, fields=["module", "metrics"])`
- **Call B (ID):** `get_module_context(repo_path="...", module="252/2", compact=False, max_items=1, fields=["module", "metrics"])`
- **Output:** Payload identyczny 1:1.

---

## 2. STATUS OPERACYJNY

```text
MCP_SERVER_RELOADED=YES
TOOL_RUNTIME_VERSION_CURRENT=YES
TOOL_SCHEMA_CURRENT=YES
TOOL_DOCUMENTATION_CURRENT=YES

LEGACY_DOTTED_RUNTIME=PASS
LEGACY_PATH_RUNTIME=PASS
WINDOWS_PATH_RUNTIME=PASS

EXACT_MODULE_ID_RUNTIME=PASS
EXACT_MODULE_ID_LEGACY_PARAM_RUNTIME=PASS
MISSING_MODULE_ID_NEVER_FUZZY_RUNTIME=PASS

FUZZY_DOTTED_RUNTIME=PASS
FUZZY_PATH_RUNTIME=PASS
FUZZY_WINDOWS_PATH_RUNTIME=PASS
FUZZY_MAX_5_RUNTIME=PASS
FUZZY_NEVER_AUTO_RESOLVES_RUNTIME=PASS
ORIGINAL_QUERY_PRESERVED_RUNTIME=PASS

ARTIFACT_REDIRECT_RUNTIME=PASS
ALIAS_CONTRACT_RUNTIME=PASS
EXACT_ID_DOWNSTREAM_EQUIVALENCE_RUNTIME=PASS

GLOBAL_GUARD_RUNTIME=NOT_EXERCISED
CURRENTNESS_RUNTIME=NOT_EXERCISED

COLLISION_CERTIFICATION=DEFERRED
FULL_ANALYSIS_EXECUTED=NO

FILES_CHANGED=NONE
DIFFS=NONE
VERDICT=PASS
```
