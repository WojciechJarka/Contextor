## CPA10I_REGRESSION_TEST_CONTRACT_MIGRATION

STATUS=PARTIAL_REGRESSION_BLOCKED
HEAD_BEFORE=832cf884af9c01fecdac94c6cda4d26f637b0934
HEAD_AFTER=832cf884af9c01fecdac94c6cda4d26f637b0934
FILES_CHANGED=tests/analysis/test_lineage_extraction.py; tests/test_collision_facts_fusion.py; tests/test_test_context_fusion.py

DISCOVERY=Contextor LIVE revision 1170 resolved parse_source_snapshot, CacheManager.get/set, and index_repository with workspace_sync=verified. Cache get/set require keyword-only source_bytes. Complete current-schema cache returns before parse; cache-miss/incomplete paths call indexer.parse_source_snapshot(snapshot, path).

TESTS_CHANGED_FILES=PASS (217 passed in 10.34s)
REGRESSION_SELECTION=BLOCKED (224 passed, 2 failed in 13.81s)
REGRESSION_COMMAND=& .\.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_collision_facts_fusion.py tests/test_reference_fusion_integration.py tests/test_test_context_fusion.py
REGRESSION_BLOCKER=tests/test_reference_fusion_integration.py has two remaining stale indexer.parse_source_with_fingerprint monkeypatch seams: test_warm_reference_hit_parses_once_for_lineage_and_zero_reference_extraction; test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm. This file is outside FILES_TO_CHANGE_EXACTLY and was not edited.
PROFILE_RUN=NOT_RUN
GIT_DIFF_CHECK=PASS (no whitespace errors; only CRLF conversion warnings)
PRODUCTION_DIFF_EXTENDED=NO (git diff --name-only HEAD contains only the three allowed test files and walkthrough.md)

ACTUAL_DIFF=
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index b98527a..1a6877d 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1227,8 +1227,8 @@ def test_full_index_transports_transient_lineage_on_cache_miss_and_hit(tmp_path,
     source.write_text("value = 1\n", encoding="utf-8")
     class FakeCache:
         def __init__(self): self.data = None
-        def get(self, _path): return self.data
-        def set(self, _path, data): self.data = data
+        def get(self, _path, *, source_bytes): return self.data
+        def set(self, _path, data, *, source_bytes): self.data = data
     cache = FakeCache()
     monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: cache)
     first = indexer_module._process_single_file(str(source), str(tmp_path))
@@ -1242,8 +1242,8 @@ def test_repository_index_collects_source_keyed_transient_lineage(tmp_path, monk
     (tmp_path / "pkg.py").write_text("value = 1\n", encoding="utf-8")
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
     class FakeCache:
-        def get(self, _path): return None
-        def set(self, _path, _data): return None
+        def get(self, _path, *, source_bytes): return None
+        def set(self, _path, _data, *, source_bytes): return None
     monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: FakeCache())
     result = indexer_module.index_repository(str(tmp_path))
     assert set(result.lineage_facts_by_source) == {"pkg.py"}
diff --git a/tests/test_collision_facts_fusion.py b/tests/test_collision_facts_fusion.py
index b3c8899..14a75ac 100644
--- a/tests/test_collision_facts_fusion.py
+++ b/tests/test_collision_facts_fusion.py
@@ -54,7 +54,7 @@ def test_cold_index_facts_match_repository_extraction_and_materialize_all_fields
         assert isinstance(fact["code"], str)
 
 
-def test_warm_current_schema_parses_once_for_lineage_and_zero_collision_extraction(
+def test_warm_current_schema_skips_ast_parse_and_collision_extraction(
     tmp_path, isolated_dirs, monkeypatch
 ):
     _serial(monkeypatch)
@@ -63,21 +63,19 @@ def test_warm_current_schema_parses_once_for_lineage_and_zero_collision_extracti
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
 
     parse_calls = []
-    original_parse = indexer.parse_source_with_fingerprint
-
     def forbidden(*args, **kwargs):
         raise AssertionError("unexpected warm extraction")
 
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or original_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or (_ for _ in ()).throw(AssertionError("unexpected warm AST parse"))),
     )
     monkeypatch.setattr(indexer, "extract_module_collision_facts", forbidden)
     warm = indexer.index_repository(str(root))
 
     assert warm.collision_facts_by_module["module"][0]["name"] == "public"
-    assert len(parse_calls) == 1
+    assert parse_calls == []
 
 
 def test_missing_collision_field_migrates_once_and_preserves_other_fact_families(
@@ -93,12 +91,12 @@ def test_missing_collision_field_migrates_once_and_preserves_other_fact_families
 
     parse_calls = []
     collision_calls = []
-    real_parse = indexer.parse_source_with_fingerprint
+    real_parse = indexer.parse_source_snapshot
     real_extract = indexer.extract_module_collision_facts
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or real_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or real_parse(snapshot, path)),
     )
     monkeypatch.setattr(
         indexer,
@@ -162,11 +160,11 @@ def test_schema_mismatch_and_source_change_reextract_once(tmp_path, isolated_dir
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
 
     parse_calls = []
-    real_parse = indexer.parse_source_with_fingerprint
+    real_parse = indexer.parse_source_snapshot
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or real_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or real_parse(snapshot, path)),
     )
     mismatched = indexer.index_repository(str(root))
     assert len(parse_calls) == 1
diff --git a/tests/test_test_context_fusion.py b/tests/test_test_context_fusion.py
index 9e50808..54bec75 100644
--- a/tests/test_test_context_fusion.py
+++ b/tests/test_test_context_fusion.py
@@ -86,7 +86,7 @@ def test_case():
     assert facts["has_assertions"] is expected[2]
 
 
-def test_cold_then_current_schema_warm_has_one_lineage_parse_per_source_and_zero_test_fact_visitor(
+def test_cold_then_current_schema_warm_skips_ast_parse_and_test_fact_visitor(
     tmp_path, isolated_dirs, monkeypatch
 ):
     root = tmp_path / "repo"
@@ -96,22 +96,16 @@ def test_cold_then_current_schema_warm_has_one_lineage_parse_per_source_and_zero
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     parse_calls = []
     visitor_calls = []
-    original_parse = indexer.parse_source_with_fingerprint
     original_extract = indexer._extract_test_file_facts
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or original_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or (_ for _ in ()).throw(AssertionError("unexpected warm AST parse"))),
     )
     monkeypatch.setattr(indexer, "_extract_test_file_facts", lambda tree: (visitor_calls.append(tree) or original_extract(tree)))
 
     warm = indexer.index_repository(str(root))
-    assert set(parse_calls) == {
-        root / "pkg" / "mod.py",
-        root / "tests" / "conftest.py",
-        source,
-    }
-    assert all(parse_calls.count(path) == 1 for path in parse_calls)
+    assert parse_calls == []
     assert visitor_calls == []
     assert str(source.resolve()) in warm.test_facts_by_path
 
@@ -129,11 +123,11 @@ def test_non_candidate_cache_record_is_not_migrated(tmp_path, isolated_dirs, mon
     CacheManager(str(root)).set(source, {"imports": [], "error": None})
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     calls = []
-    original = indexer.parse_source_with_fingerprint
+    original = indexer.parse_source_snapshot
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (calls.append(path) or original(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (calls.append(path) or original(snapshot, path)),
     )
 
     result = indexer.index_repository(str(root))
@@ -151,13 +145,23 @@ def test_missing_schema_and_source_change_invalidate_test_facts(tmp_path, isolat
     data["test_facts"]["schema_version"] = 0
     CacheManager(str(root)).set(source, data)
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls = []
+    original_parse = indexer.parse_source_snapshot
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or original_parse(snapshot, path)),
+    )
     migrated = indexer.index_repository(str(root))
+    assert parse_calls == [source]
     assert migrated.test_facts_by_path[str(source.resolve())]["has_assertions"] is True
     assert _cache_data(root, source)["test_facts"]["schema_version"] == indexer.TEST_FACTS_SCHEMA_VERSION
 
     source.write_text("from pkg.mod import Target\nassert Target\nvalue = 2\n", encoding="utf-8")
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls.clear()
     changed = indexer.index_repository(str(root))
+    assert parse_calls == [source]
     assert changed.test_facts_by_path[str(source.resolve())]["names"]
     assert first.test_facts_by_path[str(source.resolve())] != changed.test_facts_by_path[str(source.resolve())]

## GET_SYMBOL_IMPLEMENTATION_FULL_PARAMETER_CONTRACT_HARDENING

STATUS=SUCCESS
HEAD_BEFORE=5027f840ffa329bdbe3184603763b57b837918b3
HEAD_AFTER=5027f840ffa329bdbe3184603763b57b837918b3
FILES_CHANGED=contextor/mcp/tools/get_symbol_implementation.py; contextor/mcp/docs/get_symbol_implementation.json; contextor/mcp/docs/index.json; tests/mcp/tools/test_get_symbol_implementation.py; tests/test_mcp_documentation.py
PY_COMPILE=PASS
TOOL_TESTS=PASS (56 passed, 1 external deprecation warning)
DOCUMENTATION_TESTS=PASS (12 passed, 1 external deprecation warning)
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_LIVE_RESTART_REQUIRED=NO
PROFILE_WORKER_RESTART_REQUIRED=NO

CONTRACT=
ALL_REACHABLE_NON_SYMBOL_PARAMETER_ERRORS_SHOW_FULL_DOCS=YES
PARAMETER_CONTRACT_ERROR=YES
MODE_FULL_DOCS=YES
FETCH_MISSING_INCLUDE_DOCS=YES
INVALID_INCLUDE_DOCS=YES
INVALID_COMBINATION_DOCS=YES
INVALID_FILE_SCOPE_DOCS=YES
INVALID_MEMBER_LIMIT_DOCS=YES
SYMBOL_MISS_DOCS=NO
METHOD_NAME_MISS_DOCS=NO
NO_AUTO_CORRECTION=YES

UNKNOWN_ARGUMENT_NAME_BOUNDARY=FastMCP boundary; no registration architecture change in this task.

CONTEXTOR_FIRST_VERIFICATION=LIVE revision 1173: get_symbol_implementation.py and documentation.py fresh, syntax_diagnostics checked_and_none, no warnings; get_mcp_documentation confirmed current canonical documentation.

ACTUAL_DIFF=
diff --git a/contextor/mcp/docs/get_symbol_implementation.json b/contextor/mcp/docs/get_symbol_implementation.json
index ca18d53..9261b51 100644
--- a/contextor/mcp/docs/get_symbol_implementation.json
+++ b/contextor/mcp/docs/get_symbol_implementation.json
@@ -5,17 +5,20 @@
     "[OPTIMIZED] Resolves one class, function, or method from explicit source\nfiles and returns its exact AST-bounded implementation on demand."
   ],
   "parameters": [
-    "repo_path (string, required): canonical repository root.",
-    "symbol (string, required): target symbol identifier (accepts active artifact ID e.g. 'A2496/1', canonical qualified identity 'module::symbol', or leaf symbol).",
-    "file_paths (array of strings or null, optional, default null): explicit candidate file path scope; when omitted, plain leaf symbols resolve through active artifact registry to canonical LIVE module state.",
-    "mode (string, default \"auto\"): operation mode (\"auto\", \"preview\", or \"fetch\"). Invalid but similar values remain errors and may include up to five fuzzy similar_candidates; suggestions are never auto-selected.",
-    "include (array of strings or null, optional, default null): explicit sections to fetch in 'fetch' mode (\"signature\", \"docstring\", \"implementation\", \"static_context\", or \"methods\"). A non-empty include selection is required for mode='fetch'. If fetch is called without include, the tool returns its full canonical documentation JSON instead of repeating a selection_required hint. Invalid but similar section values remain errors and return bounded fuzzy similar_candidates without auto-correction.",
-    "methods (array of strings or null, optional, default null): selected method names to fetch when include contains \"methods\". Unknown method names remain errors and may return up to five fuzzy similar_candidates from the resolved class; suggestions are never auto-selected.",
-    "member_limit (integer or null, default 50): maximum number of methods to catalogue in class preview; pass null for all methods.",
-    "file_path (string or null, optional, default null): singular alias for file_paths."
+    "repo_path (string, required): canonical repository root. It must resolve to an existing directory. An invalid repo_path returns the full canonical tool documentation plus parameter_contract_error.",
+    "symbol (string, required): target symbol identifier (accepts active artifact ID e.g. 'A2496/1', canonical qualified identity 'module::symbol', or leaf symbol). Symbol-name misses are intentionally handled by identity/fuzzy lookup and do not trigger parameter-documentation fallback.",
+    "file_paths (array of strings or null, optional, default null): explicit candidate Python source-file scope. Empty path strings, nonexistent files, paths outside repo_path, and non-Python files are invalid parameter contracts and return the full canonical tool documentation plus parameter_contract_error.",
+    "mode (string, default \"auto\"): operation mode. The only valid values are \"auto\", \"preview\", and \"fetch\". There is no mode=\"full\", \"complete\", \"source\", or other undocumented mode. To return the complete AST-bounded symbol implementation explicitly, use mode=\"fetch\" with include=[\"implementation\"]. Any invalid mode returns the full canonical tool documentation plus parameter_contract_error; bounded fuzzy suggestions are advisory only and are never auto-selected.",
+    "include (array of strings or null, optional, default null): valid only with mode=\"fetch\". Valid sections are \"signature\", \"docstring\", \"implementation\", \"static_context\", and \"methods\". Explicit fetch requires a non-empty include list. \"implementation\" and \"methods\" are mutually exclusive. Any invalid include value or combination returns the full canonical tool documentation plus parameter_contract_error and bounded fuzzy suggestions when available.",
+    "methods (array of strings or null, optional, default null): valid only with mode=\"fetch\" when include contains \"methods\". include=[\"methods\"] requires explicit method names. Unknown method names are treated as symbol-name misses and return bounded method-name fuzzy suggestions rather than documentation fallback.",
+    "member_limit (integer or null, default 50): maximum number of class methods to catalogue in preview; null means all. Negative values are invalid and return the full canonical tool documentation plus parameter_contract_error.",
+    "file_path (string or null, optional, default null): singular alias for file_paths. A non-null value must be a non-empty Python source path inside repo_path. Invalid explicit paths return the full canonical tool documentation plus parameter_contract_error."
   ],
   "behavior": [
     "Resolution & file constraints:\n1. Exact active artifact ID: resolved via active artifact registry. If ``file_paths`` is omitted, the source file is derived from canonical LIVE module state. If ``file_paths`` is supplied, the definer module must be in the specified file scope (explicit file constraint wins).\n2. Canonical qualified identity ('module::symbol'): verified against active registry. If ``file_paths`` is omitted, source file is derived from canonical LIVE module state.\n3. Plain leaf symbol: when ``file_paths`` is omitted, resolves through active artifact registry (exact unique leaf resolves to canonical LIVE source; ambiguity returns controlled candidate metadata without guessing; miss returns fuzzy suggestions). When ``file_paths`` is supplied, searches via exact AST in explicit file scope first.\n4. Bounded fuzzy suggestions (score >= 0.75, max 5, suggestion-only) from active artifact registry on textual miss (scoped to explicit file constraints when provided).\n5. Missing artifact ID never returns fuzzy suggestions.",
+    "Parameter-contract hardening: every invalid non-symbol parameter value or invalid parameter combination that reaches get_symbol_implementation returns the complete canonical documentation in the same response together with parameter_contract_error. The response tells the caller which parameter was invalid, why it was invalid, and instructs the caller to retry once using documented names, values, and combinations instead of repeating the same call.",
+    "Valid mode combinations: mode='auto' accepts no include or methods override; mode='preview' accepts no include or methods override; mode='fetch' requires a non-empty include list. include=['implementation'] fetches the complete AST-bounded symbol. include=['methods'] requires methods=[...] and applies only to class symbols. 'implementation' and 'methods' cannot be selected together.",
+    "Caller parameter names are exactly repo_path, symbol, file_paths, mode, include, methods, member_limit, and file_path. Do not invent additional argument names. Unknown argument names are rejected by the MCP/FastMCP input boundary before the Python tool body can produce its documentation fallback.",
     "Fetch selection ergonomics: mode='fetch' requires a non-empty include list. When include is missing or empty, get_symbol_implementation returns the full validated canonical documentation for this tool so the caller immediately sees the valid selection contract. This documentation fallback applies only to missing fetch include selection; other errors preserve their existing fail-closed status.",
     "Finite-choice typo handling is suggestion-only. Similar invalid mode, include-section, or class-method values may return candidates using the shared Contextor fuzzy contract (minimum score 0.75, maximum 5 candidates). No candidate is ever auto-selected."
   ],
@@ -32,7 +35,7 @@
     "When workspace_sync is out_of_sync or metadata_match, both preview and fetch return status='stale_source' without any source fragment. Re-run analyze_project or update_file to refresh canonical state."
   ],
   "usage_notes": [
-    "LLM use: mode='auto' is the default single-shot path. For explicit fetch, always pass include, for example include=['implementation'] for the complete AST-bounded symbol source or include=['signature','docstring'] for the smaller contract-only response. If mode='fetch' is called without include, read the returned canonical tool documentation and retry once with a valid explicit include selection; do not repeat the same selection-less fetch call.",
+    "LLM use: start with the documented public signature only. Do not invent modes, sections, or argument names. mode='auto' is the default single-shot path. For the complete implementation use mode='fetch', include=['implementation']. If a response contains parameter_contract_error, read the full documentation already present in that same response and retry once with the documented contract; never repeat the same invalid call.",
     "Use mode='preview' when payload cost comparison or class method discovery is useful. Always check state_freshness.workspace_sync in preview responses before fetching. If status='stale_source', do not proceed with implementation reading; refresh canonical state first."
   ],
   "examples": []
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 2e4ef10..89d5c4c 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -55,7 +55,7 @@
     {
       "tool": "get_symbol_implementation",
       "filename": "get_symbol_implementation.json",
-      "short_description": "Preview or fetch one exact AST-bounded symbol implementation. Unique plain leaves may resolve through canonical LIVE identity; explicit file scope remains supported. Source is read from disk and ambiguous matches are never guessed."
+      "short_description": "Fetch one exact AST-bounded symbol. Modes: auto|preview|fetch; full source = mode=fetch with include=['implementation']. Use only documented argument names. Invalid non-symbol parameter contracts return full tool documentation."
     },
     {
       "tool": "get_file_edit_context",
diff --git a/contextor/mcp/tools/get_symbol_implementation.py b/contextor/mcp/tools/get_symbol_implementation.py
index 435a1e3..55f6f0b 100644
--- a/contextor/mcp/tools/get_symbol_implementation.py
+++ b/contextor/mcp/tools/get_symbol_implementation.py
@@ -11,6 +11,45 @@ from contextor.mcp import runtime as mcp_runtime
 DEFAULT_AUTO_FETCH_THRESHOLD_BYTES = 5120
 
 
+_FETCH_SECTIONS = (
+    "signature",
+    "docstring",
+    "implementation",
+    "static_context",
+    "methods",
+)
+
+_MODES = (
+    "auto",
+    "preview",
+    "fetch",
+)
+
+
+def _parameter_contract_response(
+    *,
+    parameter: str,
+    invalid_value: Any,
+    reason: str,
+    similar_candidates: Any = None,
+) -> str:
+    document = dict(load_tool_document("get_symbol_implementation"))
+    parameter_error: dict[str, Any] = {
+        "parameter": parameter,
+        "invalid_value": invalid_value,
+        "reason": reason,
+        "retry_instruction": (
+            "Read the documentation in this response and retry once "
+            "using only documented parameter names, values, and "
+            "combinations. Do not repeat the same invalid call."
+        ),
+    }
+    if similar_candidates is not None:
+        parameter_error["similar_candidates"] = similar_candidates
+    document["parameter_contract_error"] = parameter_error
+    return json.dumps(document, indent=2, ensure_ascii=False)
+
+
 def _resolve_symbol_source_paths(root: Path, file_paths: list[str]) -> list[Path]:
     """Resolve explicit Python source paths while retaining repository scope."""
     resolved: list[Path] = []
@@ -265,23 +304,86 @@ def get_symbol_implementation(
 
 
     if not root.is_dir():
-        return json.dumps({"status": "error", "error": f"Repository path '{root}' does not exist."}, indent=2)
+        return _parameter_contract_response(
+            parameter="repo_path",
+            invalid_value=repo_path,
+            reason=(
+                f"Repository path '{root}' does not exist "
+                "or is not a directory."
+            ),
+        )
     normalized_mode = mode.strip().lower()
-    allowed_modes = ("auto", "preview", "fetch")
-
-    if normalized_mode not in set(allowed_modes):
-        return json.dumps(
-            {
-                "status": "error",
-                "error": "mode must be 'auto', 'preview', or 'fetch'.",
-                "invalid_mode": mode,
-                "similar_candidates": query_helpers.fuzzy_choice_candidates(
-                    normalized_mode,
-                    allowed_modes,
-                ),
-            },
-            indent=2,
+    if normalized_mode not in set(_MODES):
+        return _parameter_contract_response(
+            parameter="mode",
+            invalid_value=mode,
+            reason=(
+                "mode must be exactly one of: 'auto', 'preview', or "
+                "'fetch'. There is no mode='full'. For the complete "
+                "AST-bounded implementation use mode='fetch' with "
+                "include=['implementation']."
+            ),
+            similar_candidates=query_helpers.fuzzy_choice_candidates(
+                normalized_mode, _MODES
+            ),
         )
+    if member_limit is not None and member_limit < 0:
+        return _parameter_contract_response(
+            parameter="member_limit", invalid_value=member_limit,
+            reason="member_limit must be null or an integer greater than or equal to 0.",
+        )
+    if file_path is not None and not file_path.strip():
+        return _parameter_contract_response(
+            parameter="file_path", invalid_value=file_path,
+            reason="file_path must be null or a non-empty Python source path.",
+        )
+    if file_paths is not None:
+        blank_file_paths = [item for item in file_paths if not item.strip()]
+        if blank_file_paths:
+            return _parameter_contract_response(
+                parameter="file_paths", invalid_value=file_paths,
+                reason="file_paths may be null or a list of non-empty Python source paths.",
+            )
+    if normalized_mode in {"auto", "preview"}:
+        if include is not None:
+            return _parameter_contract_response(
+                parameter="include", invalid_value=include,
+                reason="include is valid only with mode='fetch'. Do not pass include to mode='auto' or mode='preview'.",
+            )
+        if methods is not None:
+            return _parameter_contract_response(
+                parameter="methods", invalid_value=methods,
+                reason="methods is valid only with mode='fetch' and include=['methods'].",
+            )
+    if normalized_mode == "fetch":
+        selected_fetch_sections = list(include or [])
+        if not selected_fetch_sections:
+            return _parameter_contract_response(
+                parameter="include", invalid_value=include,
+                reason="mode='fetch' requires a non-empty include list. For the complete symbol implementation use include=['implementation'].",
+            )
+        unknown_fetch_sections = sorted(set(selected_fetch_sections) - set(_FETCH_SECTIONS))
+        if unknown_fetch_sections:
+            return _parameter_contract_response(
+                parameter="include", invalid_value=include,
+                reason="include contains unsupported fetch sections.",
+                similar_candidates={section: query_helpers.fuzzy_choice_candidates(section, _FETCH_SECTIONS) for section in unknown_fetch_sections},
+            )
+        if "implementation" in selected_fetch_sections and "methods" in selected_fetch_sections:
+            return _parameter_contract_response(
+                parameter="include", invalid_value=include,
+                reason="'implementation' and 'methods' are mutually exclusive fetch selections. Fetch the complete class with include=['implementation'], or selected class methods with include=['methods'] and methods=[...].",
+            )
+        if "methods" in selected_fetch_sections and not methods:
+            return _parameter_contract_response(
+                parameter="methods", invalid_value=methods,
+                reason="include=['methods'] requires explicit method names in methods=[...]. Use mode='preview' first if method discovery is needed.",
+            )
+        if methods is not None and "methods" not in selected_fetch_sections:
+            return _parameter_contract_response(
+                parameter="methods", invalid_value=methods,
+                reason="methods may be supplied only when include contains 'methods'.",
+            )
     effective_file_paths = list(file_paths or [])
     if file_path and file_path not in effective_file_paths:
         effective_file_paths.append(file_path)
@@ -314,7 +416,7 @@ def get_symbol_implementation(
                 try:
                     explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
                 explicit_modules = {
                     normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                     for p in explicit_paths
@@ -351,7 +453,7 @@ def get_symbol_implementation(
                 try:
                     search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
         elif identity["status"] == "not_found" and identity.get("query_kind") == "artifact_id":
             return json.dumps(
                 {
@@ -380,7 +482,7 @@ def get_symbol_implementation(
                 try:
                     explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
                 explicit_modules = {
                     normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                     for p in explicit_paths
@@ -417,13 +519,13 @@ def get_symbol_implementation(
                 try:
                     search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
         else:
             if effective_file_paths:
                 try:
                     explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
                 explicit_modules = {
                     normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                     for p in explicit_paths
@@ -480,7 +582,7 @@ def get_symbol_implementation(
             try:
                 search_paths = _resolve_symbol_source_paths(root, effective_file_paths)
             except ValueError as exc:
-                return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
         else:
             mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _get_registries()
             identity = query_helpers.resolve_artifact_identity(raw_symbol, art_path_to_id, art_id_to_path)
@@ -501,7 +603,7 @@ def get_symbol_implementation(
                 try:
                     search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                 except ValueError as exc:
-                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
+                    return _parameter_contract_response(parameter="file_path/file_paths", invalid_value=effective_file_paths, reason=str(exc))
             elif identity["status"] == "ambiguous":
                 return json.dumps(
                     {
@@ -632,50 +734,22 @@ def get_symbol_implementation(
     selected_sections = (
         ["implementation"] if normalized_mode == "auto" else list(include or [])
     )
-    if not selected_sections:
-        return json.dumps(
-            load_tool_document("get_symbol_implementation"),
-            indent=2,
-            ensure_ascii=False,
-        )
-    unknown_sections = sorted(
+    unavailable_sections = sorted(
         set(selected_sections) - allowed_sections
     )
-
-    if unknown_sections:
-        ordered_allowed_sections = sorted(allowed_sections)
-
-        return json.dumps(
-            {
-                "status": "error",
-                "error": "Unsupported include sections.",
-                "unknown_sections": unknown_sections,
-                "allowed_sections": ordered_allowed_sections,
-                "similar_candidates": {
-                    section: query_helpers.fuzzy_choice_candidates(
-                        section,
-                        ordered_allowed_sections,
-                    )
-                    for section in unknown_sections
-                },
-            },
-            indent=2,
-        )
-    if "implementation" in selected_sections and "methods" in selected_sections:
-        return json.dumps(
-            {
-                "status": "error",
-                "error": "implementation and methods are mutually exclusive.",
-            },
-            indent=2,
-        )
-    if "methods" in selected_sections and not methods:
-        return json.dumps(
-            {
-                "status": "selection_required",
-                "message": "Fetching methods requires explicit method names from preview.methods.items.",
+    if unavailable_sections:
+        return _parameter_contract_response(
+            parameter="include",
+            invalid_value=include,
+            reason=(
+                "The requested include section is not available for the resolved symbol kind."
+            ),
+            similar_candidates={
+                section: query_helpers.fuzzy_choice_candidates(
+                    section, sorted(allowed_sections)
+                )
+                for section in unavailable_sections
             },
-            indent=2,
         )
 
     resolution = preview["resolution"]
diff --git a/tests/mcp/tools/test_get_symbol_implementation.py b/tests/mcp/tools/test_get_symbol_implementation.py
index f7fe899..2a86c8a 100644
--- a/tests/mcp/tools/test_get_symbol_implementation.py
+++ b/tests/mcp/tools/test_get_symbol_implementation.py
@@ -618,7 +618,7 @@ def test_get_symbol_implementation__fetch_without_include_returns_full_canonical
         "get_symbol_implementation"
     )
 
-    assert result == expected
+    _assert_parameter_documentation_response(result, parameter="include")
     assert result["tool"] == "get_symbol_implementation"
     assert "parameters" in result
     assert "behavior" in result
@@ -650,9 +650,8 @@ def test_get_symbol_implementation__fetch_empty_include_returns_full_canonical_d
         include=[],
     )
 
-    assert json.loads(raw) == load_tool_document(
-        "get_symbol_implementation"
-    )
+    result = json.loads(raw)
+    _assert_parameter_documentation_response(result, parameter="include")
 
 
 def test_get_symbol_implementation__fetch_include_typo_returns_bounded_fuzzy_candidate(
@@ -674,13 +673,8 @@ def test_get_symbol_implementation__fetch_include_typo_returns_bounded_fuzzy_can
 
     result = json.loads(raw)
 
-    assert result["status"] == "error"
-    assert result["error"] == "Unsupported include sections."
-    assert result["unknown_sections"] == [
-        "implmentation"
-    ]
-
-    candidates = result["similar_candidates"][
+    _assert_parameter_documentation_response(result, parameter="include")
+    candidates = result["parameter_contract_error"]["similar_candidates"][
         "implmentation"
     ]
 
@@ -709,12 +703,9 @@ def test_get_symbol_implementation__fetch_include_unrelated_value_does_not_guess
 
     result = json.loads(raw)
 
-    assert result["status"] == "error"
-    assert result["unknown_sections"] == [
-        "totally_unrelated_xyz"
-    ]
+    _assert_parameter_documentation_response(result, parameter="include")
     assert (
-        result["similar_candidates"][
+        result["parameter_contract_error"]["similar_candidates"][
             "totally_unrelated_xyz"
         ]
         == []
@@ -739,10 +730,9 @@ def test_get_symbol_implementation__invalid_mode_typo_returns_bounded_fuzzy_cand
 
     result = json.loads(raw)
 
-    assert result["status"] == "error"
-    assert result["invalid_mode"] == "fetcc"
+    _assert_parameter_documentation_response(result, parameter="mode")
 
-    candidates = result["similar_candidates"]
+    candidates = result["parameter_contract_error"]["similar_candidates"]
 
     assert 1 <= len(candidates) <= 5
     assert candidates[0]["value"] == "fetch"
@@ -768,9 +758,7 @@ def test_get_symbol_implementation__missing_method_selection_still_uses_existing
 
     result = json.loads(raw)
 
-    assert result["status"] == "selection_required"
-    assert "method names" in result["message"]
-    assert "tool" not in result
+    _assert_parameter_documentation_response(result, parameter="methods")
 
 
 def test_get_symbol_implementation__unknown_method_typo_returns_bounded_fuzzy_candidate(
@@ -1072,7 +1060,58 @@ def test_get_symbol_implementation__runtime_description_parity():
     tool = mcp_server.mcp._tool_manager._tools["get_symbol_implementation"]
     assert tool.fn.__doc__ is None
     desc = tool.description.lower()
-    assert "plain leaves" in desc
-    assert "source is read from disk" in desc
-    assert "ambiguous" in desc
+    assert "auto|preview|fetch" in desc
+    assert "include=['implementation']" in desc
+    assert "documented argument names" in desc
+
+
+def _assert_parameter_documentation_response(result, *, parameter):
+    assert result["tool"] == "get_symbol_implementation"
+    assert result["version"] == "1.0.0"
+    for key in ("purpose", "parameters", "behavior", "freshness", "errors", "usage_notes", "examples"):
+        assert key in result
+    assert result["parameter_contract_error"]["parameter"] == parameter
+    assert "reason" in result["parameter_contract_error"]
+    assert "Do not repeat the same invalid call." in result["parameter_contract_error"]["retry_instruction"]
 
+
+def test_get_symbol_implementation__mode_full_returns_documentation(tmp_path, monkeypatch):
+    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
+    result = json.loads(get_symbol_implementation(repo_path=str(tmp_path), symbol="process_data", file_path="pkg/a.py", mode="full"))
+    _assert_parameter_documentation_response(result, parameter="mode")
+    assert result["parameter_contract_error"]["invalid_value"] == "full"
+
+
+def test_get_symbol_implementation__unrelated_invalid_mode_returns_documentation(tmp_path, monkeypatch):
+    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
+    result = json.loads(get_symbol_implementation(repo_path=str(tmp_path), symbol="process_data", file_path="pkg/a.py", mode="banana"))
+    _assert_parameter_documentation_response(result, parameter="mode")
+    assert result["parameter_contract_error"]["similar_candidates"] == []
+
+
+def test_get_symbol_implementation__invalid_combinations_return_documentation(tmp_path, monkeypatch):
+    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
+    cases = [
+        ({"mode":"auto", "include":["implementation"]}, "include"),
+        ({"mode":"preview", "methods":["login"]}, "methods"),
+        ({"mode":"fetch", "include":["implementation","methods"], "methods":["login"]}, "include"),
+        ({"mode":"fetch", "include":["methods"]}, "methods"),
+        ({"mode":"fetch", "include":["signature"], "methods":["login"]}, "methods"),
+    ]
+    for kwargs, parameter in cases:
+        symbol = "AuthService" if "methods" in kwargs.get("include", []) or kwargs.get("methods") else "process_data"
+        result = json.loads(get_symbol_implementation(repo_path=str(tmp_path), symbol=symbol, file_path="pkg/services/auth.py" if symbol == "AuthService" else "pkg/a.py", **kwargs))
+        _assert_parameter_documentation_response(result, parameter=parameter)
+
+
+def test_get_symbol_implementation__invalid_scalar_and_file_scope_return_documentation(tmp_path, monkeypatch):
+    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
+    cases = [
+        (dict(repo_path=str(tmp_path), symbol="AuthService", file_path="pkg/services/auth.py", member_limit=-1), "member_limit"),
+        (dict(repo_path=str(tmp_path), symbol="process_data", file_path="   "), "file_path"),
+        (dict(repo_path=str(tmp_path), symbol="process_data", file_path="pkg/missing.py"), "file_path/file_paths"),
+        (dict(repo_path=str(tmp_path / "missing"), symbol="anything"), "repo_path"),
+    ]
+    for kwargs, parameter in cases:
+        result = json.loads(get_symbol_implementation(**kwargs))
+        _assert_parameter_documentation_response(result, parameter=parameter)
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index e467432..701b728 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -80,6 +80,20 @@ def test_documentation_default_returns_only_index(monkeypatch):
     assert loaded == [documentation.INDEX_PATH]
 
 
+def test_get_symbol_implementation_description_prevents_undocumented_modes():
+    index = documentation.load_documentation_index()
+    entry = next(
+        item
+        for item in index["tools"]
+        if item["tool"] == "get_symbol_implementation"
+    )
+    description = entry["short_description"]
+    assert "auto|preview|fetch" in description
+    assert "include=['implementation']" in description
+    assert "Use only documented argument names" in description
+    assert len(description.encode("utf-8")) <= 300
+
+
 def test_single_tool_and_section_filters_load_only_selected_document(monkeypatch):
     loaded = []
     original = documentation._read_json
