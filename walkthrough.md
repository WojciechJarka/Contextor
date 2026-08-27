# CONTEXTOR — RUNTIME DOCS/SCHEMA SMOKE REPORT

## 1. Runtime Smoke Verification

```
MCP_RUNTIME_FRESH=YES
TOOL_VISIBLE=YES

PARAMETERS_PRESENT=[
  repo_path,
  symbol_name,
  limit,
  evidence_limit,
  compact,
  fields,
  symbol
]

STALE_PARAMETERS_PRESENT=[]

SYMBOL_DEFAULT=null
SYMBOL_NAME_DEFAULT=""
LIMIT_DEFAULT=20
EVIDENCE_LIMIT_DEFAULT=20
COMPACT_DEFAULT=true
FIELDS_DEFAULT=null

RUNTIME_DOCS_PARITY=PASS
CODE_CHANGES=NONE
TESTS_RUN=NONE
VERDICT=FINAL_PASS
```

---

## 2. Runtime Details

- **MCP Documentation Tool (`get_mcp_documentation`):** Confirmed parameters and defaults match 1-to-1 with live runtime.
- **MCP Schema (`lookup_artifact_by_symbol.json`):**
  - `repo_path`: `string` (required)
  - `symbol_name`: `string`, default `""`
  - `limit`: `integer | null`, default `20`
  - `evidence_limit`: `integer | null`, default `20`
  - `compact`: `boolean`, default `true`
  - `fields`: `array[string] | null`, default `null`
  - `symbol`: `string | null`, default `null`
  - Stale parameters `max_items` and `artifact`: **ABSENT**
