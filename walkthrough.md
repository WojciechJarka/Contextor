# CONTEXTOR — ROUND-TRIP ERGONOMICS RUNTIME CERTIFICATION H1 — FINAL CLOSURE REPORT
**Date:** 2026-08-26  
**Mode:** RUNTIME-ONLY VERIFICATION  
**Target Repository:** `C:\Temp\Contextor_Repo`  

---

## 1. Registered FastMCP Metadata Evidence (Client-Visible Schemas)

**Registered Metadata Source:** Client-visible tool schemas in `C:\Users\DafoO\.gemini\antigravity-ide\mcp\contextor\`

```
REGISTERED_METADATA_SOURCE=client_registered_tool_schemas (C:\Users\DafoO\.gemini\antigravity-ide\mcp\contextor)
REGISTERED_DESCRIPTION_QUERY_PROJECTION=PASS
REGISTERED_DESCRIPTION_SYMBOL_IMPLEMENTATION=PASS
REGISTERED_DESCRIPTION_ANALYSIS_STATUS=PASS
REGISTERED_SCHEMAS_FRESH=PASS
```

### Exact Client-Visible Schema Content

#### 1. `query_canonical_projection.json`
```json
{
  "name": "query_canonical_projection",
  "description": "Query canonical LIVE data. Basic request: root=modules|artifacts|dependencies, filters=[{field,operator,value}] (flat AND; []=all), select=[...] ([]=all). Omit both version fields for 1.0/1.0; use describe_canonical_state only for full/v1.1 discovery.",
  "parameters": {
    "properties": {
      "repo_path": {"type": "string"},
      "request": {"additionalProperties": true, "type": "object"}
    },
    "required": ["repo_path", "request"],
    "type": "object"
  }
}
```

#### 2. `get_symbol_implementation.json`
```json
{
  "name": "get_symbol_implementation",
  "description": "Preview or fetch one exact AST-bounded symbol implementation. Unique plain leaves may resolve through canonical LIVE identity; explicit file scope remains supported. Source is read from disk and ambiguous matches are never guessed.",
  "parameters": {
    "properties": {
      "file_path": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
      "file_paths": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": null},
      "include": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": null},
      "member_limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 50},
      "methods": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": null},
      "mode": {"default": "auto", "type": "string"},
      "repo_path": {"type": "string"},
      "symbol": {"type": "string"}
    },
    "required": ["repo_path", "symbol"],
    "type": "object"
  }
}
```

#### 3. `get_analysis_status.json`
```json
{
  "name": "get_analysis_status",
  "description": "Return durable analysis-job status, coverage and LIVE publication state. Explicit job_id is authoritative; when omitted, multiple queued/running jobs return bounded ambiguous_job candidates instead of guessing.",
  "parameters": {
    "properties": {
      "allow_large_output": {"default": false, "type": "boolean"},
      "job_id": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
      "max_skipped_files": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 10},
      "repo_path": {"type": "string"}
    },
    "required": ["repo_path"],
    "type": "object"
  }
}
```

---

## 2. R3B — Real Oversized `get_symbol_call_context` Auto-Bounding Evidence

### Setup & Analysis
- **Temp Repository:** `%TEMP%\contextor_runtime_cert_r3b`
- **Module:** `sample.py` with 600 intra-module helper calls from `root()`.
- **Analysis Job ID:** `94db967c51cf49b788754f5edf8c9c1d`
- **Analysis Status:** `completed` (Live publish status: `success`, revision: 3)

### Metrics Comparison

| Metric | Bounded Call (`allow_large_output=false`) | Full Lossless Call (`allow_large_output=true`) | Status |
| :--- | :--- | :--- | :--- |
| **Status** | `ok` | `ok` | MATCH |
| **Selected Representation** | `indexed` | `indexed` | STABLE |
| **`_output.auto_bounded`** | `true` | *absent* | PASS |
| **`_output.warning_threshold_bytes`** | `15360` | *N/A* | PASS |
| **`_output.bounded_collection`** | `"edges"` | *N/A* | PASS |
| **Returned Edges** | `98` | `600` | BOUNDED |
| **Returned Serialized Bytes** | `15273 B` (<= 15360 B) | `87709 B` | PASS |
| **Full Output Bytes Match** | `_output.full_output_bytes = 87709` | Actual bytes = `87709` | EXACT MATCH |
| **Deterministic Edge Prefix** | Exact 98/98 prefix | Full 600 items | PASS |

```
R3B_SELECTED_REPRESENTATION=indexed
R3B_FULL_OUTPUT_BYTES=87709
R3B_BOUNDED_OUTPUT_BYTES=15273
R3B_BOUNDED_RETURNED_EDGES=98
R3B_FULL_RETURNED_EDGES=600
R3B_EXACT_EDGE_PREFIX=PASS
R3B_REPRESENTATION_STABLE_ACROSS_ALLOW_FLAG=PASS
R3B_FULL_OUTPUT_BYTES_EXACT=PASS
R3B_AUTO_BOUNDING=PASS
```

---

## 3. R6 — SHA-256 Direct Read-Only Mutation Proof

- **Temp Repository:** `%TEMP%\contextor_runtime_cert_r6_h1`
- **Job A (queued):** `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json`
  - SHA-256 Before: `c06ade4b716b8535dfd8ec4f83bd3d9959a16fc70c84a60a3f6b39a51924a43c`
  - SHA-256 After: `c06ade4b716b8535dfd8ec4f83bd3d9959a16fc70c84a60a3f6b39a51924a43c` (EXACT MATCH)
- **Job B (running):** `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.json`
  - SHA-256 Before: `90e0a8c7986439d2c7ff6b5aadacf28ce7befe856b0b22ea4a48aeba8c262a36`
  - SHA-256 After: `90e0a8c7986439d2c7ff6b5aadacf28ce7befe856b0b22ea4a48aeba8c262a36` (EXACT MATCH)

```
R6_AMBIGUOUS_JOB=PASS
R6_JOB_A_FILE_UNCHANGED=PASS
R6_JOB_B_FILE_UNCHANGED=PASS
R6_AMBIGUITY_BYTE_MUTATION=NO
```

---

## 4. H1 Public Runtime Call Trace

### `CALL_H1_1`
- **TOOL:** `analyze_project`
- **KEY_ARGS:** `{"repo_path": "<temp_repo_r3b>"}`
- **STATUS:** `queued`
- **KEY_FIELDS:** `job_id: "94db967c51cf49b788754f5edf8c9c1d"`, `operation: "project"`.
- **BYTES:** `450 B`
- **PURPOSE:** Launch non-blocking architectural analysis for temporary 600-helper intra-module repository.

### `CALL_H1_2`
- **TOOL:** `get_analysis_status`
- **KEY_ARGS:** `{"repo_path": "<temp_repo_r3b>", "job_id": "94db967c51cf49b788754f5edf8c9c1d"}`
- **STATUS:** `completed`
- **KEY_FIELDS:** `status: "completed"`, `live_publish_status: "success"`, `live_publish_revision: 3`.
- **BYTES:** `530 B`
- **PURPOSE:** Confirm completion and canonical LIVE state publication for temp repository.

### `CALL_H1_3`
- **TOOL:** `get_symbol_call_context`
- **KEY_ARGS:** `{"repo_path": "<temp_repo_r3b>", "symbol": "sample::root", "direction": "both", "depth": 1, "max_items": null, "representation": "auto", "allow_large_output": false}`
- **STATUS:** `ok`
- **KEY_FIELDS:** `_output.auto_bounded: true`, `_output.full_output_bytes: 87709`, `_output.warning_threshold_bytes: 15360`, `_output.bounded_collection: "edges"`, `_output.returned_count: 98`, `representation: "indexed"`, `representation_decision.selected: "indexed"`.
- **BYTES:** `15273 B`
- **PURPOSE:** Verify real R3B single-shot auto-bounding on >15360 B intra-module symbol-call graph.

### `CALL_H1_4`
- **TOOL:** `get_symbol_call_context`
- **KEY_ARGS:** `{"repo_path": "<temp_repo_r3b>", "symbol": "sample::root", "direction": "both", "depth": 1, "max_items": null, "representation": "auto", "allow_large_output": true}`
- **STATUS:** `ok`
- **KEY_FIELDS:** `_output` absent, `returned_edges: 600`, `total_edges: 600`, `representation: "indexed"`, `representation_decision.selected: "indexed"`, exact response bytes = `87709 B`.
- **BYTES:** `87709 B`
- **PURPOSE:** Verify lossless retrieval under `allow_large_output=true` with stable representation and exact byte parity.

### `CALL_H1_5`
- **TOOL:** `get_analysis_status`
- **KEY_ARGS:** `{"repo_path": "<temp_repo_r6_h1>", "job_id": null}`
- **STATUS:** `ambiguous_job`
- **KEY_FIELDS:** `status: "ambiguous_job"`, `job_id: null`, `active_job_count: 2`, `len(active_jobs): 2`.
- **BYTES:** `620 B`
- **PURPOSE:** Execute ambiguous status call against SHA-256 hashed durable jobs to prove read-only non-mutating behavior.

---

## 5. Final Closure Verdict

```
REGISTERED_MCP_METADATA_FRESH=PASS
R3B_RUNTIME_AUTO_BOUNDING=PASS
R3B_REPRESENTATION_STABLE=PASS
R3B_PREFIX_EXACT=PASS
R3B_FULL_BYTES_EXACT=PASS
R6_AMBIGUOUS_DURABLE_STATE_UNCHANGED=PASS

CODE_CHANGED=NO
CONTEXTOR_REPO_CHANGED=NO

RUNTIME_H1_VERDICT=FINAL_PASS
OVERALL_RUNTIME_VERDICT=FINAL_PASS
ROUND_TRIP_ERGONOMICS_RUNTIME=5/5_CERTIFIED
OPEN_RUNTIME_FINDINGS=[]
MCP_RUNTIME_FRESH=YES
LIVE_RESTART_REQUIRED=NO
```
