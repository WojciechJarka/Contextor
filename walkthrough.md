## GET_SYMBOL_IMPLEMENTATION_SELECTION_ERGONOMICS_FIX

STATUS=PARTIAL_DOCUMENTATION_CATALOG_REGRESSION
HEAD_BEFORE=d326b34a8f0d5ff971993f9453ac6303007096c2
HEAD_AFTER=d326b34a8f0d5ff971993f9453ac6303007096c2
FILES_CHANGED=contextor/mcp/query_helpers.py; contextor/mcp/tools/get_symbol_implementation.py; contextor/mcp/docs/get_symbol_implementation.json; tests/mcp/tools/test_get_symbol_implementation.py
PY_COMPILE=PASS
TOOL_TESTS=PASS (52 passed, 1 external deprecation warning)
DOCUMENTATION_TESTS=PARTIAL: tests/test_mcp_documentation.py => 10 passed, 1 failed. Existing contextor_profile_analysis document version is 1.3.0 while HEAD docs/index.json version is 1.0.0; neither file is in scope and neither was changed.
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_LIVE_RESTART_REQUIRED=NO_FOR_THIS_CHANGE
PROFILE_WORKER_RESTART_REQUIRED=NO

CONTRACT=
FETCH_WITHOUT_INCLUDE=FULL_CANONICAL_TOOL_DOCUMENTATION
FETCH_EMPTY_INCLUDE=FULL_CANONICAL_TOOL_DOCUMENTATION
INCLUDE_FUZZY=SHARED_THRESHOLD_MAX5_SUGGESTION_ONLY
MODE_FUZZY=SHARED_THRESHOLD_MAX5_SUGGESTION_ONLY
METHOD_FUZZY=SHARED_THRESHOLD_MAX5_SUGGESTION_ONLY
SYMBOL_FUZZY=UNCHANGED
NO_AUTO_CORRECTION=YES

CONTEXTOR_FIRST_VERIFICATION=LIVE revision 1164: get_file_edit_context minimal confirmed query_helpers.py, get_symbol_implementation.py, and documentation.py fresh with no syntax diagnostics; get_symbol_implementation preview resolved resolve_artifact_identity, get_symbol_implementation, and load_tool_document with workspace_sync=verified. Direct load_tool_document('get_symbol_implementation')=PASS, version=1.0.0.

ACTUAL_DIFF=
diff --git a/contextor/mcp/docs/get_symbol_implementation.json b/contextor/mcp/docs/get_symbol_implementation.json
index a2e76b2..ca18d53 100644
--- a/contextor/mcp/docs/get_symbol_implementation.json
+++ b/contextor/mcp/docs/get_symbol_implementation.json
@@ -8,14 +8,16 @@
     "repo_path (string, required): canonical repository root.",
     "symbol (string, required): target symbol identifier (accepts active artifact ID e.g. 'A2496/1', canonical qualified identity 'module::symbol', or leaf symbol).",
     "file_paths (array of strings or null, optional, default null): explicit candidate file path scope; when omitted, plain leaf symbols resolve through active artifact registry to canonical LIVE module state.",
-    "mode (string, default \"auto\"): operation mode (\"auto\", \"preview\", or \"fetch\").",
-    "include (array of strings or null, optional, default null): explicit sections to fetch in 'fetch' mode (\"signature\", \"docstring\", \"implementation\", \"static_context\", or \"methods\").",
-    "methods (array of strings or null, optional, default null): selected method names to fetch when include contains \"methods\".",
+    "mode (string, default \"auto\"): operation mode (\"auto\", \"preview\", or \"fetch\"). Invalid but similar values remain errors and may include up to five fuzzy similar_candidates; suggestions are never auto-selected.",
+    "include (array of strings or null, optional, default null): explicit sections to fetch in 'fetch' mode (\"signature\", \"docstring\", \"implementation\", \"static_context\", or \"methods\"). A non-empty include selection is required for mode='fetch'. If fetch is called without include, the tool returns its full canonical documentation JSON instead of repeating a selection_required hint. Invalid but similar section values remain errors and return bounded fuzzy similar_candidates without auto-correction.",
+    "methods (array of strings or null, optional, default null): selected method names to fetch when include contains \"methods\". Unknown method names remain errors and may return up to five fuzzy similar_candidates from the resolved class; suggestions are never auto-selected.",
     "member_limit (integer or null, default 50): maximum number of methods to catalogue in class preview; pass null for all methods.",
     "file_path (string or null, optional, default null): singular alias for file_paths."
   ],
   "behavior": [
-    "Resolution & file constraints:\n1. Exact active artifact ID: resolved via active artifact registry. If ``file_paths`` is omitted, the source file is derived from canonical LIVE module state. If ``file_paths`` is supplied, the definer module must be in the specified file scope (explicit file constraint wins).\n2. Canonical qualified identity ('module::symbol'): verified against active registry. If ``file_paths`` is omitted, source file is derived from canonical LIVE module state.\n3. Plain leaf symbol: when ``file_paths`` is omitted, resolves through active artifact registry (exact unique leaf resolves to canonical LIVE source; ambiguity returns controlled candidate metadata without guessing; miss returns fuzzy suggestions). When ``file_paths`` is supplied, searches via exact AST in explicit file scope first.\n4. Bounded fuzzy suggestions (score >= 0.75, max 5, suggestion-only) from active artifact registry on textual miss (scoped to explicit file constraints when provided).\n5. Missing artifact ID never returns fuzzy suggestions."
+    "Resolution & file constraints:\n1. Exact active artifact ID: resolved via active artifact registry. If ``file_paths`` is omitted, the source file is derived from canonical LIVE module state. If ``file_paths`` is supplied, the definer module must be in the specified file scope (explicit file constraint wins).\n2. Canonical qualified identity ('module::symbol'): verified against active registry. If ``file_paths`` is omitted, source file is derived from canonical LIVE module state.\n3. Plain leaf symbol: when ``file_paths`` is omitted, resolves through active artifact registry (exact unique leaf resolves to canonical LIVE source; ambiguity returns controlled candidate metadata without guessing; miss returns fuzzy suggestions). When ``file_paths`` is supplied, searches via exact AST in explicit file scope first.\n4. Bounded fuzzy suggestions (score >= 0.75, max 5, suggestion-only) from active artifact registry on textual miss (scoped to explicit file constraints when provided).\n5. Missing artifact ID never returns fuzzy suggestions.",
+    "Fetch selection ergonomics: mode='fetch' requires a non-empty include list. When include is missing or empty, get_symbol_implementation returns the full validated canonical documentation for this tool so the caller immediately sees the valid selection contract. This documentation fallback applies only to missing fetch include selection; other errors preserve their existing fail-closed status.",
+    "Finite-choice typo handling is suggestion-only. Similar invalid mode, include-section, or class-method values may return candidates using the shared Contextor fuzzy contract (minimum score 0.75, maximum 5 candidates). No candidate is ever auto-selected."
   ],
   "freshness": [
     "Every resolved response includes a ``state_freshness`` envelope scoped to the source file of the resolved symbol.",
@@ -30,7 +32,8 @@
     "When workspace_sync is out_of_sync or metadata_match, both preview and fetch return status='stale_source' without any source fragment. Re-run analyze_project or update_file to refresh canonical state."
   ],
   "usage_notes": [
-    "LLM use: preview first, compare the planned payload sizes, then fetch the\nsmallest complete combination that answers the implementation question.\nAlways check state_freshness.workspace_sync in the preview response before calling fetch.\nIf status='stale_source', do not proceed with implementation reading — refresh canonical state first."
+    "LLM use: mode='auto' is the default single-shot path. For explicit fetch, always pass include, for example include=['implementation'] for the complete AST-bounded symbol source or include=['signature','docstring'] for the smaller contract-only response. If mode='fetch' is called without include, read the returned canonical tool documentation and retry once with a valid explicit include selection; do not repeat the same selection-less fetch call.",
+    "Use mode='preview' when payload cost comparison or class method discovery is useful. Always check state_freshness.workspace_sync in preview responses before fetching. If status='stale_source', do not proceed with implementation reading; refresh canonical state first."
   ],
   "examples": []
 }
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index e2ee217..eeea214 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -12,6 +12,44 @@ FUZZY_MIN_SCORE: float = 0.75
 FUZZY_MAX_CANDIDATES: int = 5
 
 
+def fuzzy_choice_candidates(
+    query: str,
+    choices: list[str] | tuple[str, ...] | set[str],
+) -> list[dict[str, object]]:
+    """Return bounded suggestion-only fuzzy matches for one finite string choice."""
+    normalized_query = str(query).strip().casefold()
+    if not normalized_query:
+        return []
+
+    scored: list[tuple[float, str, float]] = []
+
+    for choice in sorted({str(item) for item in choices}):
+        raw_score = difflib.SequenceMatcher(
+            None,
+            normalized_query,
+            choice.casefold(),
+        ).ratio()
+
+        if raw_score >= FUZZY_MIN_SCORE:
+            scored.append(
+                (
+                    -raw_score,
+                    choice,
+                    raw_score,
+                )
+            )
+
+    scored.sort()
+
+    return [
+        {
+            "value": choice,
+            "score": round(score, 4),
+        }
+        for _, choice, score in scored[:FUZZY_MAX_CANDIDATES]
+    ]
+
+
 def bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
     total = len(items)
     if limit is None:
diff --git a/contextor/mcp/tools/get_symbol_implementation.py b/contextor/mcp/tools/get_symbol_implementation.py
index 7569c56..435a1e3 100644
--- a/contextor/mcp/tools/get_symbol_implementation.py
+++ b/contextor/mcp/tools/get_symbol_implementation.py
@@ -5,6 +5,7 @@ from typing import Any
 
 from contextor.core.source import SourceError, read_source
 from contextor.mcp import query_helpers
+from contextor.mcp.documentation import load_tool_document
 from contextor.mcp import runtime as mcp_runtime
 
 DEFAULT_AUTO_FETCH_THRESHOLD_BYTES = 5120
@@ -266,9 +267,19 @@ def get_symbol_implementation(
     if not root.is_dir():
         return json.dumps({"status": "error", "error": f"Repository path '{root}' does not exist."}, indent=2)
     normalized_mode = mode.strip().lower()
-    if normalized_mode not in {"auto", "preview", "fetch"}:
+    allowed_modes = ("auto", "preview", "fetch")
+
+    if normalized_mode not in set(allowed_modes):
         return json.dumps(
-            {"status": "error", "error": "mode must be 'auto', 'preview', or 'fetch'."},
+            {
+                "status": "error",
+                "error": "mode must be 'auto', 'preview', or 'fetch'.",
+                "invalid_mode": mode,
+                "similar_candidates": query_helpers.fuzzy_choice_candidates(
+                    normalized_mode,
+                    allowed_modes,
+                ),
+            },
             indent=2,
         )
     effective_file_paths = list(file_paths or [])
@@ -623,21 +634,30 @@ def get_symbol_implementation(
     )
     if not selected_sections:
         return json.dumps(
-            {
-                "status": "selection_required",
-                "message": "Fetch requires an explicit include selection. Run preview to compare costs.",
-                "allowed_sections": sorted(allowed_sections),
-            },
+            load_tool_document("get_symbol_implementation"),
             indent=2,
+            ensure_ascii=False,
         )
-    unknown_sections = sorted(set(selected_sections) - allowed_sections)
+    unknown_sections = sorted(
+        set(selected_sections) - allowed_sections
+    )
+
     if unknown_sections:
+        ordered_allowed_sections = sorted(allowed_sections)
+
         return json.dumps(
             {
                 "status": "error",
                 "error": "Unsupported include sections.",
                 "unknown_sections": unknown_sections,
-                "allowed_sections": sorted(allowed_sections),
+                "allowed_sections": ordered_allowed_sections,
+                "similar_candidates": {
+                    section: query_helpers.fuzzy_choice_candidates(
+                        section,
+                        ordered_allowed_sections,
+                    )
+                    for section in unknown_sections
+                },
             },
             indent=2,
         )
@@ -684,14 +704,28 @@ def get_symbol_implementation(
             for child in node.body
             if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
         }
-        unknown_methods = sorted(set(methods or []) - set(available_methods))
+        unknown_methods = sorted(
+            set(methods or []) - set(available_methods)
+        )
+
         if unknown_methods:
+            ordered_available_methods = sorted(
+                available_methods
+            )
+
             return json.dumps(
                 {
                     "status": "error",
                     "error": "Unknown class methods.",
                     "unknown_methods": unknown_methods,
-                    "available_methods": sorted(available_methods),
+                    "available_methods": ordered_available_methods,
+                    "similar_candidates": {
+                        method: query_helpers.fuzzy_choice_candidates(
+                            method,
+                            ordered_available_methods,
+                        )
+                        for method in unknown_methods
+                    },
                 },
                 indent=2,
             )
diff --git a/tests/mcp/tools/test_get_symbol_implementation.py b/tests/mcp/tools/test_get_symbol_implementation.py
index c71b42d..f7fe899 100644
--- a/tests/mcp/tools/test_get_symbol_implementation.py
+++ b/tests/mcp/tools/test_get_symbol_implementation.py
@@ -591,6 +591,295 @@ def test_get_symbol_implementation__exact_id_auto_large_response_uses_existing_p
 
 
 # ============================================================
+# FETCH SELECTION ERGONOMICS
+# ============================================================
+
+
+def test_get_symbol_implementation__fetch_without_include_returns_full_canonical_documentation(
+    tmp_path,
+    monkeypatch,
+):
+    from contextor.mcp.documentation import load_tool_document
+
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_data",
+        file_path="pkg/a.py",
+        mode="fetch",
+    )
+
+    result = json.loads(raw)
+    expected = load_tool_document(
+        "get_symbol_implementation"
+    )
+
+    assert result == expected
+    assert result["tool"] == "get_symbol_implementation"
+    assert "parameters" in result
+    assert "behavior" in result
+    assert "usage_notes" in result
+
+    serialized = json.dumps(result)
+
+    assert "include" in serialized
+    assert "mode='fetch'" in serialized
+    assert "selection_required" not in result
+
+
+def test_get_symbol_implementation__fetch_empty_include_returns_full_canonical_documentation(
+    tmp_path,
+    monkeypatch,
+):
+    from contextor.mcp.documentation import load_tool_document
+
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_data",
+        file_path="pkg/a.py",
+        mode="fetch",
+        include=[],
+    )
+
+    assert json.loads(raw) == load_tool_document(
+        "get_symbol_implementation"
+    )
+
+
+def test_get_symbol_implementation__fetch_include_typo_returns_bounded_fuzzy_candidate(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_data",
+        file_path="pkg/a.py",
+        mode="fetch",
+        include=["implmentation"],
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "error"
+    assert result["error"] == "Unsupported include sections."
+    assert result["unknown_sections"] == [
+        "implmentation"
+    ]
+
+    candidates = result["similar_candidates"][
+        "implmentation"
+    ]
+
+    assert 1 <= len(candidates) <= 5
+    assert candidates[0]["value"] == "implementation"
+    assert candidates[0]["score"] >= 0.75
+    assert "implementation" not in result
+
+
+def test_get_symbol_implementation__fetch_include_unrelated_value_does_not_guess(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_data",
+        file_path="pkg/a.py",
+        mode="fetch",
+        include=["totally_unrelated_xyz"],
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "error"
+    assert result["unknown_sections"] == [
+        "totally_unrelated_xyz"
+    ]
+    assert (
+        result["similar_candidates"][
+            "totally_unrelated_xyz"
+        ]
+        == []
+    )
+
+
+def test_get_symbol_implementation__invalid_mode_typo_returns_bounded_fuzzy_candidate(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_data",
+        file_path="pkg/a.py",
+        mode="fetcc",
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "error"
+    assert result["invalid_mode"] == "fetcc"
+
+    candidates = result["similar_candidates"]
+
+    assert 1 <= len(candidates) <= 5
+    assert candidates[0]["value"] == "fetch"
+    assert candidates[0]["score"] >= 0.75
+
+
+def test_get_symbol_implementation__missing_method_selection_still_uses_existing_selection_required_contract(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="AuthService",
+        file_path="pkg/services/auth.py",
+        mode="fetch",
+        include=["methods"],
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "selection_required"
+    assert "method names" in result["message"]
+    assert "tool" not in result
+
+
+def test_get_symbol_implementation__unknown_method_typo_returns_bounded_fuzzy_candidate(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="AuthService",
+        file_path="pkg/services/auth.py",
+        mode="fetch",
+        include=["methods"],
+        methods=["logn"],
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "error"
+    assert result["error"] == "Unknown class methods."
+    assert result["unknown_methods"] == ["logn"]
+
+    candidates = result["similar_candidates"]["logn"]
+
+    assert 1 <= len(candidates) <= 5
+    assert candidates[0]["value"] == "login"
+    assert candidates[0]["score"] >= 0.75
+
+
+def test_get_symbol_implementation__existing_symbol_fuzzy_contract_remains_bounded_and_suggestion_only(
+    tmp_path,
+    monkeypatch,
+):
+    _setup_symbol_implementation_workspace(
+        tmp_path,
+        monkeypatch,
+    )
+
+    raw = get_symbol_implementation(
+        repo_path=str(tmp_path),
+        symbol="process_dat",
+        file_path="pkg/a.py",
+    )
+
+    result = json.loads(raw)
+
+    assert result["status"] == "not_found"
+    assert 1 <= len(result["similar_candidates"]) <= 5
+    assert (
+        result["similar_candidates"][0]["artifact"]
+        == "pkg.a::process_data"
+    )
+    assert "implementation" not in result
+    assert "resolution" not in result
+
+
+def test_fuzzy_choice_candidates__uses_shared_threshold_order_and_bound():
+    choices = {
+        "implementation",
+        "signature",
+        "docstring",
+        "static_context",
+        "methods",
+        "implementation_extra_1",
+        "implementation_extra_2",
+        "implementation_extra_3",
+        "implementation_extra_4",
+        "implementation_extra_5",
+        "implementation_extra_6",
+    }
+
+    candidates = query_helpers.fuzzy_choice_candidates(
+        "implementatio",
+        choices,
+    )
+
+    assert candidates
+    assert len(candidates) <= query_helpers.FUZZY_MAX_CANDIDATES
+    assert candidates[0]["value"] == "implementation"
+    assert all(
+        candidate["score"] >= query_helpers.FUZZY_MIN_SCORE
+        for candidate in candidates
+    )
+
+    scores = [
+        candidate["score"]
+        for candidate in candidates
+    ]
+
+    assert scores == sorted(
+        scores,
+        reverse=True,
+    )
+
+
+def test_fuzzy_choice_candidates__unrelated_query_returns_empty():
+    assert (
+        query_helpers.fuzzy_choice_candidates(
+            "xyz_totally_unrelated",
+            ["auto", "preview", "fetch"],
+        )
+        == []
+    )
+
+
 # 5. CURRENTNESS & LIVE DEPENDENCY
 # ============================================================
 
@@ -787,5 +1076,3 @@ def test_get_symbol_implementation__runtime_description_parity():
     assert "source is read from disk" in desc
     assert "ambiguous" in desc
 
-
-

## MCP_DOCUMENTATION_CATALOG_VERSION_CONSISTENCY_FIX

STATUS=SUCCESS
FILES_CHANGED=contextor/mcp/docs/contextor_profile_analysis.json
DOCUMENTATION_TESTS=PASS (11 passed, 1 external deprecation warning)
TOOL_TESTS=PASS (52 passed, 1 external deprecation warning)
MCP_SERVER_RESTART_REQUIRED=YES

ACTUAL_DIFF=
diff --git a/contextor/mcp/docs/contextor_profile_analysis.json b/contextor/mcp/docs/contextor_profile_analysis.json
index f369a5f..9683b78 100644
--- a/contextor/mcp/docs/contextor_profile_analysis.json
+++ b/contextor/mcp/docs/contextor_profile_analysis.json
@@ -1,5 +1,5 @@
 {
-  "version": "1.3.0",
+  "version": "1.0.0",
   "tool": "contextor_profile_analysis",
   "purpose": ["Run one repository-wide diagnostic profile through the real production full-analysis path and return a compact, deterministic breakdown of where the analysis spends time and which structured evidence explains known bottlenecks."],
   "parameters": ["repo_path (string, required): canonical repository root to profile.", "exclude_paths (array of strings or null, optional, default null): additional per-run repository-relative exclusions forwarded unchanged to the production full-analysis path."],
