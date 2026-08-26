# CONTEXTOR — GET_ARTIFACTS_FOR_MODULE DISCOVERY H1 — REPORT
**Date:** 2026-08-26  
**Mode:** DOC ALIAS SEMANTICS CORRECTION  
**Target Repository:** `C:\Temp\Contextor_Repo`  

---

## 1. Discovery & Alias Semantics Verdict

```
DIRECT_SINGLE_CALL_BEHAVIOR_CHANGED=NO
PRODUCTION_CODE_CHANGED=NO
PUBLIC_SIGNATURE_CHANGED=NO
ALIAS_CONFLICT_SEMANTICS=FAIL_CLOSED
DOC_ALIAS_SEMANTICS_MATCH_PRODUCTION=PASS
DISCOVERY_SINGLE_CALL_GUIDANCE_PRESERVED=PASS

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=FINAL_PASS
```

---

## 2. Test Verification

```
tests/mcp/tools/test_get_artifacts_for_module.py (PASSED: 26/26)
tests/mcp/tools/test_public_mcp_docs_parity.py (PASSED)
tests/test_mcp_documentation.py (PASSED)
```

---

## 3. Complete Raw Unified Diffs

### `contextor/mcp/docs/get_artifacts_for_module.json`

```diff
diff --git a/contextor/mcp/docs/get_artifacts_for_module.json b/contextor/mcp/docs/get_artifacts_for_module.json
index def49a0..9790f52 100644
--- a/contextor/mcp/docs/get_artifacts_for_module.json
+++ b/contextor/mcp/docs/get_artifacts_for_module.json
@@ -6,7 +6,7 @@
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
-    "module_name (string, optional, default \"\"): module identifier (accepts module ID e.g. '259/1', dotted module name, or file path).",
+    "module_name (string, optional, default \"\"): module identifier (accepts dotted module name, repository-relative POSIX .py path, Windows .py path, or active module ID).",
     "include_consumers (boolean, default true): includes consumer counts and evidence when true; signatures-only view when false.",
     "symbol_filter (string, optional, default \"\"): filters candidate artifacts by symbol name substring before limits and ranking.",
     "limit (integer or null, default 50): maximum number of artifacts returned; pass null for unbounded (default compact mode caps at 10 items).",
@@ -14,10 +14,10 @@
     "compact (boolean, default true): returns progressive-disclosure summary (up to 10 salience-ranked artifacts with 3 evidence items each) when true; full details when false.",
     "fields (array of strings or null, default null): optional projection list of top-level keys to return; null returns full response.",
     "representation (string, default \"named\"): nested consumer encoding format (\"named\", \"indexed\", or \"auto\").",
-    "module (string or null, optional, default null): alias for module_name."
+    "module (string or null, optional, default null): alias for module_name; either may identify the module. If both are non-empty they must be identical, otherwise a controlled alias-conflict error is returned."
   ],
   "behavior": [
-    "Resolution order:\n1. Exact active module ID via active module registry.\n2. Path-to-dotted normalization and canonical LIVE state lookup.\n3. Bounded fuzzy module suggestions (score >= 0.75, max 5) from active module registry on textual not-found.\n4. Legacy not-found string fallback when query is not found or is a nonexistent module ID.",
+    "Resolution order:\n1. Exact active module ID via active module registry.\n2. Dotted module name or repository-relative source path (POSIX or Windows) resolved directly to canonical LIVE module state without requiring a prior get_module_context call.\n3. Bounded fuzzy module suggestions (score >= 0.75, max 5, suggestion-only) from active module registry on textual not-found.\n4. Persistent registries provide identity only; canonical LIVE state supplies architectural truth.\n5. Legacy not-found string fallback when query is not found or is a nonexistent module ID.",
     "In default compact mode (``compact=True``), returns up to 10 artifacts prioritized by consumer salience (``consumers.total DESC``, then alphabetical) with up to 3 nested consumer evidence items per artifact.",
     "Top-level ``truncated`` is truthful (``artifact_count < total_artifact_count``). When output is truncated by internal compact presentation cap, an executable ``expand`` descriptor is included preserving original requested limits.",
     "For complete lossless views, use ``compact=False, limit=None, evidence_limit=None`` with ``representation='named'`` or ``representation='indexed'``.",
@@ -28,7 +28,7 @@
   "freshness": [],
   "errors": [],
   "usage_notes": [
-    "LLM use: call before changing a module API. Use default compact for instant visibility of highest-impact symbols; expand or request indexed representation for complete blast-radius analysis.",
+    "Call get_artifacts_for_module directly when artifacts are the goal; get_module_context is only needed when module architecture/context is also required. Use default compact for instant visibility of highest-impact symbols; expand or request indexed representation for complete blast-radius analysis.",
     "Resolve indexed consumer module IDs in batch via ``lookup_index_entries``."
   ],
   "examples": []
```

---

### `contextor/mcp/docs/index.json`

```diff
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index f920057..bfc0d5f 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -96,7 +96,7 @@
     {
       "tool": "get_artifacts_for_module",
       "filename": "get_artifacts_for_module.json",
-      "short_description": "Return canonical artifacts exported by one module, optionally with bounded consumer evidence. Persistent registries provide identity only."
+      "short_description": "Return canonical artifacts for a module directly by dotted name, source path or active module ID, with optional bounded consumer evidence. No prior get_module_context lookup is required."
     },
     {
       "tool": "lookup_artifact_by_symbol",
```

---

### `tests/mcp/tools/test_get_artifacts_for_module.py`

```diff
diff --git a/tests/mcp/tools/test_get_artifacts_for_module.py b/tests/mcp/tools/test_get_artifacts_for_module.py
index 81c15d3..cf77c0b 100644
--- a/tests/mcp/tools/test_get_artifacts_for_module.py
+++ b/tests/mcp/tools/test_get_artifacts_for_module.py
@@ -410,3 +410,38 @@ def test_get_artifacts_for_module__original_query_preserved_and_candidate_struct
     assert candidate["module"] == "pkg.services.auth"
     assert candidate["module_id"] == "13/1"
     assert isinstance(candidate["score"], float)
+
+
+def test_get_artifacts_for_module__runtime_description_and_discovery_parity():
+    from contextor import mcp_server
+    from contextor.mcp import documentation
+
+    tool = mcp_server.mcp._tool_manager._tools["get_artifacts_for_module"]
+    index = documentation.load_documentation_index()
+    entry = next(
+        item for item in index["tools"]
+        if item["tool"] == "get_artifacts_for_module"
+    )
+
+    assert tool.description == entry["short_description"]
+    assert tool.fn.__doc__ is None
+    assert len(tool.description.encode("utf-8")) <= 300
+
+    description = tool.description.lower()
+    assert "directly" in description
+    assert "dotted name" in description
+    assert "source path" in description
+    assert "module id" in description
+    assert "no prior get_module_context" in description
+
+    doc = documentation.load_tool_document("get_artifacts_for_module")
+    usage_text = " ".join(doc.get("usage_notes", [])).lower()
+    assert "get_module_context" in usage_text
+    assert "directly" in usage_text
+
+    behavior_text = " ".join(doc.get("behavior", [])).lower()
+    assert "without requiring a prior get_module_context call" in behavior_text
+
+    params_text = " ".join(doc.get("parameters", [])).lower()
+    assert "alias-conflict" in params_text or "conflict" in params_text
+    assert "identical" in params_text
```
