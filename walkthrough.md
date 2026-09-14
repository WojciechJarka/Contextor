# CPA7_PUBLIC_MCP_WIRING

## STATUS

SUCCESS.

## BASE_HEAD

`a8972e0b7806eebd89a189302201cc82c990f7e0` (matches EXPECTED_BASE).

## FILES_CHANGED

- contextor/mcp/tools/contextor_profile_analysis.py
- contextor/mcp_server.py
- contextor/mcp/docs/index.json
- contextor/mcp/docs/contextor_profile_analysis.json
- tests/mcp/tools/test_contextor_profile_analysis.py
- tests/test_mcp_documentation.py
- tests/test_live_activity_status.py
- walkthrough.md (this report)

## IMPLEMENTATION

Added public async `contextor_profile_analysis(repo_path, exclude_paths=None) -> str`. It validates the repository, invokes CPA6 through `asyncio.to_thread`, and serializes the profile as indented JSON. It is centrally registered through `register_mcp_tool`.

## TESTS

- Specified pytest command: 15 passed in 6.34s (one external Authlib deprecation warning).
- Specified `py_compile`: passed.
- Specified `git diff --check`: passed.

No full analysis, benchmark, MCP restart, or Desktop/LIVE restart ran.

## PUBLIC_SIGNATURE

`(repo_path: str, exclude_paths: list[str] | None = None) -> str`; central registration keeps `output_schema=None`, therefore correct responses use the existing single TextContent transport.

## REGISTRY_PARITY

`REGISTERED_MCP_TOOL_NAMES` now contains 29 names and matches FastMCP registry coverage. The central telemetry/diagnostics wrapper remains the only registration route.

## DOCS_PARITY

The index contains the new documentation entry directly before final `get_mcp_documentation`; documentation parity test passed.

## LEGACY_ORDER

Git/source comparison proves the first 20 registered-tool entries are byte-for-byte identical to HEAD.

## TRANSPORT_CONTRACT

The coroutine offloads the synchronous runner via `asyncio.to_thread`; invalid roots return an Error string before runner invocation. Runner results remain JSON-as-string. No alternate direct `mcp.tool` registration was added.

## CONTEXTOR_FLOW_VERIFY

Contextor returned `unknown_symbol` for `contextor.mcp_server::contextor_profile_analysis`, expected without LIVE refresh. No full analysis was run. Scoped source verification confirms the only registration is `register_mcp_tool(... output_schema=None)`; CPA1–CPA6 production files were unchanged.

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/mcp_server.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/docs/index.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_mcp_documentation.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_activity_status.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/tools/contextor_profile_analysis.py b/contextor/mcp/tools/contextor_profile_analysis.py
new file mode 100644
index 0000000..97fd0c3
--- /dev/null
+++ b/contextor/mcp/tools/contextor_profile_analysis.py
@@ -0,0 +1,13 @@
+import asyncio
+import json
+from pathlib import Path
+
+from contextor.core.analysis.profile_runner import run_analysis_profile
+
+
+async def contextor_profile_analysis(repo_path: str, exclude_paths: list[str] | None = None) -> str:
+    root = Path(repo_path).expanduser().resolve()
+    if not root.is_dir():
+        return f"Error: Repository path '{root}' does not exist."
+    profile = await asyncio.to_thread(run_analysis_profile, root, exclude_paths=exclude_paths)
+    return json.dumps(profile, indent=2)
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 7d38583..7aa8e40 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -207,6 +207,9 @@ from contextor.mcp.tools.lookup_artifact_by_symbol import (
     lookup_artifact_by_symbol as _lookup_artifact_by_symbol_impl,
 )
 from contextor.mcp.tools.analyze_project import analyze_project as _analyze_project_impl
+from contextor.mcp.tools.contextor_profile_analysis import (
+    contextor_profile_analysis as _contextor_profile_analysis_impl,
+)
 from contextor.mcp.tools.analyze_layer import analyze_layer as _analyze_layer_impl
 from contextor.mcp.tools.analyze_single_file import (
     analyze_single_file as _analyze_single_file_impl,
@@ -524,6 +527,7 @@ REGISTERED_MCP_TOOL_NAMES: tuple[str, ...] = (
     "get_mcp_documentation",
     "get_module_blast_radius",
     "contextor_fact_lineage",
+    "contextor_profile_analysis",
 )
 
 
@@ -574,6 +578,10 @@ get_name_collisions = register_mcp_tool(_get_name_collisions_impl, name="get_nam
 get_mcp_documentation = register_mcp_tool(_get_mcp_documentation_impl, name="get_mcp_documentation")
 get_module_blast_radius = register_mcp_tool(_get_module_blast_radius_impl, name="get_module_blast_radius")
 contextor_fact_lineage = register_mcp_tool(_contextor_fact_lineage_impl, name="contextor_fact_lineage")
+contextor_profile_analysis = register_mcp_tool(
+    _contextor_profile_analysis_impl,
+    name="contextor_profile_analysis",
+)
 
 
 def main():
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index df59a38..2e4ef10 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -138,6 +138,11 @@
       "filename": "contextor_fact_lineage.json",
       "short_description": "Return Contextor self-architecture lineage for one canonical fact family: production, staging, canonical state, lifecycle writers, persistence, hydration, and public projection."
     },
+    {
+      "tool": "contextor_profile_analysis",
+      "filename": "contextor_profile_analysis.json",
+      "short_description": "Run one non-blocking-admission full-analysis diagnostic profile and return critical-path bottlenecks with deterministic structured evidence. Absolute wall time is diagnostic, not benchmark-authoritative."
+    },
     {
       "tool": "get_mcp_documentation",
       "filename": "get_mcp_documentation.json",
diff --git a/contextor/mcp/docs/contextor_profile_analysis.json b/contextor/mcp/docs/contextor_profile_analysis.json
new file mode 100644
index 0000000..37f6bd0
--- /dev/null
+++ b/contextor/mcp/docs/contextor_profile_analysis.json
@@ -0,0 +1,11 @@
+{
+  "version": "1.0.0",
+  "tool": "contextor_profile_analysis",
+  "purpose": ["Run one repository-wide diagnostic profile through the real production full-analysis path and return a compact, deterministic breakdown of where the analysis spends time and which structured evidence explains known bottlenecks."],
+  "parameters": ["repo_path (string, required): canonical repository root to profile.", "exclude_paths (array of strings or null, optional, default null): additional per-run repository-relative exclusions forwarded unchanged to the production full-analysis path."],
+  "behavior": ["1. The MCP coroutine offloads the synchronous profile runner through asyncio.to_thread so the MCP event loop is not blocked by the analysis body.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. Known reason codes are derived only from structured runtime evidence. Unknown causes remain unattributed rather than inferred."],
+  "freshness": ["The tool executes a real full repository analysis and therefore refreshes the same canonical analysis state and LIVE publication path as the normal production full-analysis owner when the run succeeds.", "The returned profile describes only the analysis executed by this call. It is not a historical profiler report and is not persisted as a separate profiling artifact."],
+  "errors": ["A missing or non-directory repo_path returns an Error string before starting the profile runner.", "status=busy with reason_code=full_analysis_busy means another canonical full-analysis writer already owns the repository; retry later rather than treating the result as a performance sample.", "status=incomplete means required structured profile evidence was missing or duplicated.", "status=invalid_evidence means captured timing/evidence contracts were internally inconsistent.", "Unexpected production analysis failures propagate through the normal central MCP wrapper and are not converted into profiler guesses."],
+  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution."],
+  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. A reason_code such as warm_cache_still_parses_source or lineage_reuse_gate_cost is evidence-backed; unattributed means the current structured signals do not justify a stronger causal claim."]
+}
diff --git a/tests/mcp/tools/test_contextor_profile_analysis.py b/tests/mcp/tools/test_contextor_profile_analysis.py
new file mode 100644
index 0000000..962f9f3
--- /dev/null
+++ b/tests/mcp/tools/test_contextor_profile_analysis.py
@@ -0,0 +1,33 @@
+import asyncio
+import json
+from pathlib import Path
+
+import contextor.mcp.tools.contextor_profile_analysis as profile_tool
+
+
+def test_contextor_profile_analysis_offloads_runner_and_serializes_profile(tmp_path: Path, monkeypatch):
+    observed: dict[str, object] = {}
+    def fake_runner(repo_path, *, exclude_paths=None):
+        raise AssertionError("runner must be invoked through asyncio.to_thread")
+    async def fake_to_thread(func, *args, **kwargs):
+        observed["func"] = func
+        observed["args"] = args
+        observed["kwargs"] = kwargs
+        return {"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"}
+    monkeypatch.setattr(profile_tool, "run_analysis_profile", fake_runner)
+    monkeypatch.setattr(profile_tool.asyncio, "to_thread", fake_to_thread)
+    raw = asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), exclude_paths=["generated"]))
+    payload = json.loads(raw)
+    assert observed["func"] is fake_runner
+    assert observed["args"] == (tmp_path.resolve(),)
+    assert observed["kwargs"] == {"exclude_paths": ["generated"]}
+    assert payload == {"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"}
+
+
+def test_contextor_profile_analysis_rejects_missing_repository_before_runner(tmp_path: Path, monkeypatch):
+    missing = tmp_path / "missing"
+    def forbidden_runner(*args, **kwargs):
+        raise AssertionError("invalid repository must not start profiler")
+    monkeypatch.setattr(profile_tool, "run_analysis_profile", forbidden_runner)
+    result = asyncio.run(profile_tool.contextor_profile_analysis(str(missing)))
+    assert result == f"Error: Repository path '{missing.resolve()}' does not exist."
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index 52d93bc..e467432 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -72,7 +72,7 @@ def test_documentation_default_returns_only_index(monkeypatch):
     result = json.loads(mcp_server.get_mcp_documentation.fn())
 
     assert result["version"]
-    assert len(result["tools"]) == 28
+    assert len(result["tools"]) == 29
     assert result["documentation_hint"] == (
         "For full documentation of a tool, call "
         "get_mcp_documentation with tool=<tool_name>."
@@ -170,6 +170,24 @@ def test_documentation_reader_paths_are_package_local(monkeypatch):
     assert all(path.parent == docs_root for path in read_paths)
 
 
+def test_contextor_profile_analysis_is_registered_and_documented():
+    tool = mcp_server.mcp._tool_manager._tools[
+        "contextor_profile_analysis"
+    ]
+    index = documentation.load_documentation_index()
+    entry = next(
+        item
+        for item in index["tools"]
+        if item["tool"] == "contextor_profile_analysis"
+    )
+
+    assert tool.description == entry["short_description"]
+    assert str(inspect.signature(tool.fn, eval_str=True)) == (
+        "(repo_path: str, exclude_paths: list[str] | None = None) -> str"
+    )
+    assert index["tools"][-1]["tool"] == "get_mcp_documentation"
+
+
 def test_get_symbol_lineage_is_registered_with_documented_public_signature():
     tool = mcp_server.mcp._tool_manager._tools[
         "get_symbol_lineage"
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 9d6c6a5..71dfc9e 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -16,7 +16,7 @@ Covers all concrete correctness and evidence requirements:
 13. Central MCP wrapper read-only success
 14. Central MCP wrapper failure re-raise & logging
 15. MCP analyze_project wrapper & canonical publication separation
-16. All 27 registered FastMCP tools coverage & registry synchronization
+16. All 29 registered FastMCP tools coverage & registry synchronization
 17. Real server-to-GUI burst ordering, zero dropped events & zero duplicates
 18. Desktop vs MCP full analysis publication equivalence
 """
@@ -831,10 +831,10 @@ def test_mcp_analyze_project_wrapper_and_canonical_publish_equivalence(live_serv
     assert events[1]["canonical_revision"] == 2
 
 
-def test_all_28_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
+def test_all_29_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
     fastmcp_tool_names = set(mcp._tool_manager._tools.keys())
     assert set(REGISTERED_MCP_TOOL_NAMES) == fastmcp_tool_names
-    assert len(REGISTERED_MCP_TOOL_NAMES) == 28
+    assert len(REGISTERED_MCP_TOOL_NAMES) == 29
 
     calls_emitted = []
 

```

## COMMIT_SHA

Not created (no commit requested).

## RUNTIME_RESTART_REQUIRED

YES. Reload the active MCP runtime before using the public tool. MCP and Desktop/LIVE were not restarted.

