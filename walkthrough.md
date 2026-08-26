# CONTEXTOR — ROUND-TRIP ERGONOMICS R3B-H2 — REPORT
**Date:** 2026-08-26  
**Mode:** EXACT DOC FIELD FIX  

---

## 1. Ergonomics Verdict & Status

```
PRODUCTION_FILES_CHANGED=NONE
FILES_CHANGED=[
  contextor/mcp/docs/get_symbol_call_context.json
]

AUTO_BOUNDED_SIZE_FIELD=_output.full_output_bytes
CONFIRMATION_REQUIRED_SIZE_FIELD=estimated_output_bytes
DOC_RESPONSE_FIELD_PARITY=PASS

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=FINAL_PASS
```

---

## 2. Tests Summary

```
TESTS=[
  tests/test_mcp_documentation.py (PASSED: 7/7),
  tests/mcp/tools/test_public_mcp_docs_parity.py (PASSED: 5/5),
]
```

---

## 3. Raw Unified Diff

```diff
diff --git a/contextor/mcp/docs/get_symbol_call_context.json b/contextor/mcp/docs/get_symbol_call_context.json
index bab0af4..dd570fc 100644
--- a/contextor/mcp/docs/get_symbol_call_context.json
+++ b/contextor/mcp/docs/get_symbol_call_context.json
@@ -22,7 +22,8 @@
     "Named output is permitted only when the complete named candidate is at most 51200 UTF-8 bytes. Larger named candidates automatically select indexed output.",
     "Auto selects indexed below the 51200-byte boundary only when existing shared representation policy saves at least 512 serialized bytes; otherwise it emits named output.",
     "Indexed edges use existing persistent artifact IDs only and expose lookup_index_entries as the batch resolver. No new IDs or graph registry are created.",
-    "After scope, depth, global max_items, and representation selection, the exact final JSON is measured. A payload strictly above 15360 UTF-8 bytes returns compact confirmation_required without graph edges unless allow_large_output is true."
+    "Representation negotiation happens before output auto-bounding: explicit named/indexed and auto selection remain authoritative, named candidates strictly above 51200 bytes force indexed representation, and auto switches to indexed at 512+ bytes savings.",
+    "After representation selection, the exact final JSON is measured against the 15360 UTF-8 byte threshold. When output exceeds 15360 bytes with allow_large_output=false and contains edges, the tool returns the largest deterministic edge prefix fitting within 15360 bytes (embedding _output.auto_bounded=true, full_output_bytes, requested_count, and returned_count). If even one edge cannot fit or returned_edges is zero, compact confirmation_required is returned without graph edges. No BFS, registry lookup, or canonical analysis is repeated for auto-bounding. Passing allow_large_output=true returns the complete original selected candidate."
   ],
   "freshness": [
     "Reads only current LIVE canonical module_usages symbol_calls. It performs no ast.parse, source read, grep, report parsing, or query-time graph reconstruction.",
@@ -33,7 +34,7 @@
   ],
   "usage_notes": [
     "Start with direction, depth=1, and a small max_items. Use expand metadata or retry with a larger bound only when the refactor needs more context.",
-    "For confirmation_required, reduce max_items/depth, narrow direction, select indexed, or repeat the identical request with allow_large_output=true."
+    "When _output.auto_bounded is true, inspect _output.full_output_bytes; when confirmation_required is returned, inspect estimated_output_bytes. In either case, repeat the identical request with allow_large_output=true to receive the complete original selected edge payload, or reduce max_items/depth."
   ],
   "examples": [
     "get_symbol_call_context(repo_path, \"pkg.module::handler\", direction=\"callees\", depth=1, max_items=20, representation=\"auto\")",
```
