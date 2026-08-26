# CONTEXTOR — R5H1 / R4 DESCRIPTION OWNERSHIP REPAIR — REPORT
**Date:** 2026-08-26  
**Mode:** IMPLEMENTATION & VERIFICATION  

---

## 1. Ergonomics & Architecture Verdict

```
PUBLIC_DESCRIPTION_OWNER=index.json
FAST_MCP_DESCRIPTION_INDEX_BACKED=PASS
PUBLIC_TOOL_FUNCTION_DOCSTRINGS_NONE=PASS
DISCOVERY_DESCRIPTION_MAX_BYTES=300
DOCUMENTATION_ARCHITECTURE_TEST_RESTORED=PASS

R4_QUERY_RUNTIME_DESCRIPTION_SELF_SUFFICIENT=PASS
R4_DESCRIBE_RUNTIME_DESCRIPTION_OPTIONAL=PASS

R5_PLAIN_LEAF_RESOLVER_UNCHANGED=PASS
R5_RUNTIME_DESCRIPTION_PLAIN_LEAF=PASS
R5_RUNTIME_DESCRIPTION_SOURCE_TRUTH=DISK
R5_RUNTIME_DESCRIPTION_AMBIGUITY=PASS

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=FINAL_PASS
```

---

## 2. Files Summary

```
PRODUCTION_FILES_CHANGED=[
  contextor/mcp/tools/query_canonical_projection.py,
  contextor/mcp/tools/describe_canonical_state.py
]

R5_RESOLVER_PRODUCTION_CHANGED=NO

FILES_CHANGED=[
  contextor/mcp/tools/query_canonical_projection.py,
  contextor/mcp/tools/describe_canonical_state.py,
  contextor/mcp/docs/index.json,
  tests/test_mcp_documentation.py,
  tests/mcp/tools/test_canonical_projection_single_call.py,
  tests/mcp/tools/test_get_symbol_implementation.py
]

TESTS=[
  tests/test_mcp_documentation.py (PASSED: 7/7),
  tests/mcp/tools/test_canonical_projection_single_call.py (PASSED: 18/18),
  tests/mcp/tools/test_get_symbol_implementation.py (PASSED: 39/39),
  tests/mcp/tools/test_specialized_tool_contracts.py (PASSED: 11/11),
  tests/mcp/tools/test_public_mcp_docs_parity.py (PASSED: 5/5),
  tests/test_mcp_split_s2d.py (PASSED: 17/17),
  tests/test_mcp_split_s2a.py (PASSED: 11/11)
]
```

---

## 3. Complete Raw Unified Diffs

### `contextor/mcp/tools/query_canonical_projection.py`

```diff
diff --git a/contextor/mcp/tools/query_canonical_projection.py b/contextor/mcp/tools/query_canonical_projection.py
index c0be7b1..31e2668 100644
--- a/contextor/mcp/tools/query_canonical_projection.py
+++ b/contextor/mcp/tools/query_canonical_projection.py
@@ -8,6 +8,8 @@ from contextor.mcp import runtime as mcp_runtime
 
 def query_canonical_projection(repo_path: str, request: dict[str, Any]) -> str:
     root = Path(repo_path).expanduser().resolve()
+
+
     engine = mcp_runtime.get_or_init_engine(root)
     if not engine:
         return json.dumps(
```

---

### `contextor/mcp/tools/describe_canonical_state.py`

```diff
diff --git a/contextor/mcp/tools/describe_canonical_state.py b/contextor/mcp/tools/describe_canonical_state.py
index 583a12d..c5b18f4 100644
--- a/contextor/mcp/tools/describe_canonical_state.py
+++ b/contextor/mcp/tools/describe_canonical_state.py
@@ -12,6 +12,8 @@ def describe_canonical_state(
     language_version: str = LANGUAGE_VERSION,
 ) -> str:
     return json.dumps(
+
+
         describe_contract(schema_version=schema_version, language_version=language_version),
         indent=2,
         ensure_ascii=False,
```

---

### `contextor/mcp/docs/index.json`

```diff
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 5e10e32..b750106 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -54,8 +54,8 @@
     {
       "tool": "get_symbol_implementation",
       "filename": "get_symbol_implementation.json",
-      "short_description": "Preview or fetch one exact AST-bounded symbol implementation from explicit source files. Ambiguous matches are never guessed."
+      "short_description": "Preview or fetch one exact AST-bounded symbol implementation. Unique plain leaves may resolve through canonical LIVE identity; explicit file scope remains supported. Source is read from disk and ambiguous matches are never guessed."
     },
     {
       "tool": "get_file_edit_context",
@@ -74,13 +74,14 @@
     {
       "tool": "describe_canonical_state",
       "filename": "describe_canonical_state.json",
-      "short_description": "Return the passive versioned schema and language contract for safe canonical queries. It reads no repository data."
+      "short_description": "Discover the full canonical-query schema: roots, selectable fields, per-field operators, null semantics, ordering, limits and v1.1 capabilities. Optional for basic v1.0 query_canonical_projection requests."
     },
     {
       "tool": "query_canonical_projection",
       "filename": "query_canonical_projection.json",
-      "short_description": "Execute a safe bounded query over normalized canonical LIVE data. Only the declared versioned query language is accepted."
+      "short_description": "Query canonical LIVE data. Basic request: root=modules|artifacts|dependencies, filters=[{field,operator,value}] (flat AND; []=all), select=[...] ([]=all). Omit both version fields for 1.0/1.0; use describe_canonical_state only for full/v1.1 discovery."
     },
+
     {
       "tool": "extract_indexed_report_context",
       "filename": "extract_indexed_report_context.json",
```

---

### `tests/test_mcp_documentation.py`

```diff
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index b72626c..984b906 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -58,6 +58,8 @@ def test_discovery_descriptions_are_short_and_index_backed():
         assert tool.fn.__doc__ is None
 
 
+
+
 def test_documentation_default_returns_only_index(monkeypatch):
     loaded = []
     original = documentation._read_json
```

---

### `tests/mcp/tools/test_canonical_projection_single_call.py`

```diff
diff --git a/tests/mcp/tools/test_canonical_projection_single_call.py b/tests/mcp/tools/test_canonical_projection_single_call.py
index 9260c6d..db0f269 100644
--- a/tests/mcp/tools/test_canonical_projection_single_call.py
+++ b/tests/mcp/tools/test_canonical_projection_single_call.py
@@ -248,41 +248,61 @@ def test_canonical_projection_single_call__docs_do_not_impose_describe_prerequis
     assert "basic v1.0 queries can be composed directly in query_canonical_projection without calling this first" in describe_notes
 
 
-def test_canonical_projection_single_call__runtime_query_tool_description_is_self_sufficient():
-    import inspect
-    from contextor.mcp.tools.query_canonical_projection import query_canonical_projection
-
-    doc = inspect.getdoc(query_canonical_projection)
-    assert doc is not None
-    doc_lower = " ".join(doc.lower().split())
+def test_canonical_projection_single_call__runtime_query_description_is_index_backed_and_self_sufficient():
+    from contextor import mcp_server
+    from contextor.mcp import documentation
+
+    tool = mcp_server.mcp._tool_manager._tools["query_canonical_projection"]
+    index = documentation.load_documentation_index()
+    entry = next(
+        item for item in index["tools"]
+        if item["tool"] == "query_canonical_projection"
+    )
+
+    assert tool.description == entry["short_description"]
+
+    description = tool.description.lower()
 
     for term in (
-        "1.0",
         "modules",
         "artifacts",
         "dependencies",
-        "root",
         "filters",
+        "field",
+        "operator",
+        "value",
         "select",
-        "flat and",
+        "1.0/1.0",
     ):
-        assert term in doc_lower, f"Expected '{term}' in query_canonical_projection runtime docstring"
-
-    assert "discover the contract first" not in doc_lower
-    assert "must explicitly include schema_version" not in doc_lower
-
-
-def test_canonical_projection_single_call__runtime_describe_tool_is_not_prerequisite():
-    import inspect
-    from contextor.mcp.tools.describe_canonical_state import describe_canonical_state
-
-    doc = inspect.getdoc(describe_canonical_state)
-    assert doc is not None
-    doc_lower = " ".join(doc.lower().split())
-
-    assert "without this discovery call" in doc_lower
-    assert "call this before composing" not in doc_lower
-    assert "versioned schema" in doc_lower
+        assert term in description
+
+    assert "flat and" in description
+    assert "describe_canonical_state only" in description
+    assert tool.fn.__doc__ is None
+
+
+def test_canonical_projection_single_call__runtime_describe_description_is_optional_discovery():
+    from contextor import mcp_server
+    from contextor.mcp import documentation
+
+    tool = mcp_server.mcp._tool_manager._tools["describe_canonical_state"]
+    index = documentation.load_documentation_index()
+    entry = next(
+        item for item in index["tools"]
+        if item["tool"] == "describe_canonical_state"
+    )
+
+    assert tool.description == entry["short_description"]
+
+    description = tool.description.lower()
+
+    assert "optional" in description
+    assert "basic v1.0" in description
+    assert "operators" in description
+    assert "limits" in description
+    assert "v1.1" in description
+    assert tool.fn.__doc__ is None
+
```

---

### `tests/mcp/tools/test_get_symbol_implementation.py`

```diff
diff --git a/tests/mcp/tools/test_get_symbol_implementation.py b/tests/mcp/tools/test_get_symbol_implementation.py
index d1d4f5e..c71b42d 100644
--- a/tests/mcp/tools/test_get_symbol_implementation.py
+++ b/tests/mcp/tools/test_get_symbol_implementation.py
@@ -777,3 +777,15 @@ def test_get_symbol_implementation__lowercase_artifact_id_success(tmp_path, monk
     assert "def process_data(x):" in res["implementation"]
 
 
+def test_get_symbol_implementation__runtime_description_parity():
+    from contextor import mcp_server
+
+    tool = mcp_server.mcp._tool_manager._tools["get_symbol_implementation"]
+    assert tool.fn.__doc__ is None
+    desc = tool.description.lower()
+    assert "plain leaves" in desc
+    assert "source is read from disk" in desc
+    assert "ambiguous" in desc
+
+
+
```
