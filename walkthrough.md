# F2L D1P2 — public registration and documentation

STATUS: BLOCKED

FILES_CHANGED:
- contextor/mcp_server.py
- contextor/mcp/docs/index.json
- contextor/mcp/docs/get_symbol_lineage.json
- contextor/mcp/documentation.py
- contextor/mcp/docs/get_mcp_documentation.json
- tests/test_mcp_documentation.py

REGISTRATION_PROOF: get_symbol_lineage is imported, listed in the public tool tuple after get_symbol_call_context, and registered through register_mcp_tool without a literal description.

PUBLIC_SIGNATURE_PROOF: BLOCKED. The required D1P1 adapter begins with from __future__ import annotations. Python therefore preserves all annotations as strings, and FastMCP exposes str(inspect.signature(tool.fn)) with quoted annotations. The exact D1P2 assertion requires unquoted annotations. Satisfying it would require changing the forbidden D1P1 adapter or changing the explicitly supplied D1P2 test assertion.

DOC_PARITY_PROOF: The indexed JSON entry, matching full per-tool JSON document, and registration have been added atomically. The existing public docs-parity test passes.

INDEX_DESCRIPTION_PROOF: The index short description exactly matches the required public FastMCP description; its assertion passes.

DOCUMENTATION_HINT_PROOF: The default index response now includes the prescribed documentation_hint.

LAZY_DOC_LOAD_PROOF: The default-index test still observes only documentation.INDEX_PATH; get_symbol_lineage lazy-document test confirms index, index, selected document loading order.

LEGACY_SIGNATURE_PROOF: Existing legacy signature coverage passes unchanged.

TESTS_RUN:
- .\.venv\Scripts\python.exe -m pytest -q tests\test_mcp_documentation.py tests\mcp\tools\test_public_mcp_docs_parity.py tests\mcp\tools\test_get_symbol_lineage.py
  Result: 27 passed, 1 failed.
  Failure: test_get_symbol_lineage_is_registered_with_documented_public_signature; quoted annotations from D1P1 future-annotations conflict with required unquoted literal signature.
- .\.venv\Scripts\python.exe -m py_compile contextor\mcp_server.py contextor\mcp\documentation.py tests\test_mcp_documentation.py
  Result: passed
- JSON validation for index.json, get_symbol_lineage.json, and get_mcp_documentation.json
  Result: passed
- git diff --check for the six D1P2 files
  Result: passed

## ACTUAL_DIFF

```diff
contextor/mcp_server.py
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index d9126af..8c5bb61 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -197,6 +197,9 @@ from contextor.mcp.tools.get_source_range import get_source_range as _get_source
 from contextor.mcp.tools.get_symbol_call_context import (
     get_symbol_call_context as _get_symbol_call_context_impl,
 )
+from contextor.mcp.tools.get_symbol_lineage import (
+    get_symbol_lineage as _get_symbol_lineage_impl,
+)
 from contextor.mcp.tools.get_artifacts_for_module import (
     get_artifacts_for_module as _get_artifacts_for_module_impl,
 )
@@ -516,6 +519,7 @@ REGISTERED_MCP_TOOL_NAMES: tuple[str, ...] = (
     "search_source",
     "get_source_range",
     "get_symbol_call_context",
+    "get_symbol_lineage",
     "get_name_collisions",
     "get_mcp_documentation",
     "get_module_blast_radius",
@@ -562,6 +566,10 @@ lookup_artifact_by_symbol = register_mcp_tool(_lookup_artifact_by_symbol_impl, n
 search_source = register_mcp_tool(_search_source_impl, name="search_source")
 get_source_range = register_mcp_tool(_get_source_range_impl, name="get_source_range")
 get_symbol_call_context = register_mcp_tool(_get_symbol_call_context_impl, name="get_symbol_call_context")
+get_symbol_lineage = register_mcp_tool(
+    _get_symbol_lineage_impl,
+    name="get_symbol_lineage",
+)
 get_name_collisions = register_mcp_tool(_get_name_collisions_impl, name="get_name_collisions")
 get_mcp_documentation = register_mcp_tool(_get_mcp_documentation_impl, name="get_mcp_documentation")
 get_module_blast_radius = register_mcp_tool(_get_module_blast_radius_impl, name="get_module_blast_radius")

contextor/mcp/documentation.py
diff --git a/contextor/mcp/documentation.py b/contextor/mcp/documentation.py
index 6b4e0fb..5f0c5eb 100644
--- a/contextor/mcp/documentation.py
+++ b/contextor/mcp/documentation.py
@@ -144,6 +144,10 @@ def query_documentation(
             }
         return {
             "version": index["version"],
+            "documentation_hint": (
+                "For full documentation of a tool, call "
+                "get_mcp_documentation with tool=<tool_name>."
+            ),
             "tools": [
                 {
                     "tool": entry["tool"],

contextor/mcp/docs/index.json
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 77d47e0..df59a38 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -118,6 +118,11 @@
       "filename": "get_symbol_call_context.json",
       "short_description": "Return a bounded callers/callees neighborhood from canonical intra-module symbol-call facts without a repository scan or source-derived call reconstruction."
     },
+    {
+      "tool": "get_symbol_lineage",
+      "filename": "get_symbol_lineage.json",
+      "short_description": "Read canonical static value/data lineage for one exact symbol from LIVE state with bounded progressive disclosure."
+    },
     {
       "tool": "get_name_collisions",
       "filename": "get_name_collisions.json",

diff --git a/contextor/mcp/docs/get_symbol_lineage.json b/contextor/mcp/docs/get_symbol_lineage.json
new file mode 100644
index 0000000..a94852e
--- /dev/null
+++ b/contextor/mcp/docs/get_symbol_lineage.json
@@ -0,0 +1,51 @@
+{
+  "version": "1.0.0",
+  "tool": "get_symbol_lineage",
+  "purpose": [
+    "Return canonical static value/data lineage for one exact symbol from the already-materialized LIVE lineage state without reconstructing lineage from source or loading the complete RepositoryAnalysisState into the MCP process."
+  ],
+  "parameters": [
+    "repo_path (string, required): canonical repository root.",
+    "symbol (string, required): active artifact ID or exact module::symbol identity; plain leaves and fuzzy identities are not accepted.",
+    "mode (auto|preview|fetch, default \"auto\"): progressive disclosure mode. auto evaluates all canonical lineage sections and returns the complete represented payload only when it fits the 5120-byte auto threshold; preview returns section costs without section payloads; fetch requires an explicit non-empty sections list.",
+    "sections (array or null, default null): explicit semantic sections for fetch mode only. Valid names are interface, connections, bindings, parameter_flows, calls_interfaces, returns, state, callbacks, surfaces, and unresolved_dynamic_boundaries.",
+    "representation (named|indexed|auto, default \"auto\"): semantic-owner identity representation. named uses canonical module/artifact names when available; indexed retains canonical owner IDs; auto applies exact serialized-size negotiation.",
+    "allow_large_output (boolean, default false): approve a selected final payload above the shared 15360-byte output threshold."
+  ],
+  "behavior": [
+    "Exact target resolution is canonical and fail-closed. Active artifact IDs and exact module::symbol identities are accepted; unqualified leaves, fuzzy matches, and recovery identities are not promoted to targets.",
+    "The MCP process does not hydrate an IncrementalAnalysisEngine or request a canonical state snapshot. It connects only to an already-running verified LIVE authority and sends one narrow canonical_query request containing the target and planned semantic sections.",
+    "The LIVE owner answers from its already-hydrated canonical RAM lineage state under one server revision lock. Query execution does not parse source, read the persistent identity registry, materialize lineage, or enumerate all lineage slices for exact target lookup.",
+    "Semantic sections are selected before transport. auto and preview request the complete canonical section set; fetch sends only the requested sections in canonical section order.",
+    "Sections describe the target interface, direct cross-source connections, bindings, parameter flows, calls/interfaces, returns, state access, callbacks, surfaces, and unresolved/dynamic boundaries. get_symbol_lineage does not perform recursive lineage traversal.",
+    "Representation applies only to canonical SemanticEndpoint owners. Semantic owners may be module IDs or artifact IDs. Indexed output exposes lookup_index_entries as the resolver for both ID kinds; occurrence and symbolic endpoint identities are not rewritten.",
+    "auto selects indexed representation only when named identities are unavailable or indexed output saves at least 512 serialized bytes; otherwise it emits named output.",
+    "For mode=auto, a represented complete candidate above 5120 UTF-8 bytes becomes a representation-aware preview before the general large-output guard runs. A candidate exactly at 5120 bytes may be returned.",
+    "The selected final response uses the shared 15360-byte output guard. Explicit fetch above that threshold requires allow_large_output=true.",
+    "invalid, not_found, ambiguous, unavailable, and resolved are distinct semantic outcomes. Ambiguous exact identities are returned as candidates and are never guessed."
+  ],
+  "freshness": [
+    "Requires an already-running verified canonical LIVE authority. The tool does not start LIVE and does not fall back to snapshot/disk hydration when LIVE is absent.",
+    "The response freshness envelope is derived from the same canonical RAM revision as the lineage facts. Outer IPC revision, lineage freshness revision, and selected-facts metadata revision must agree or the MCP transport fails closed.",
+    "workspace_sync is unverified in this narrow server-side lineage path because the tool intentionally performs no source-file hash or FileState read. canonical_state still reports retained last-known-good module state and resync requirements from canonical RAM lifecycle metadata.",
+    "The lineage and lineage-query-index families must be fresh with complete semantic anchor bindings for exact target resolution; otherwise the semantic result is unavailable rather than a fabricated not_found."
+  ],
+  "errors": [
+    "Invalid mode, section selection, representation, allow_large_output, repository path, or symbol shape returns a controlled error response before lineage execution where applicable.",
+    "canonical_live_unavailable means no verified running LIVE authority exists; the tool does not start one automatically.",
+    "canonical_live_transport_error and canonical_query_transport_error report authority/IPC transport failure without snapshot fallback.",
+    "canonical_query_response_invalid and canonical_query_revision_mismatch fail closed on malformed or cross-revision narrow responses.",
+    "lineage_response_failed reports a presentation-contract failure after a resolved canonical query.",
+    "Semantic target outcomes invalid, not_found, ambiguous, and unavailable are returned as their own statuses rather than collapsed into transport errors."
+  ],
+  "usage_notes": [
+    "Use mode=\"auto\" first for ordinary symbol inspection. If it returns preview because the complete result exceeds 5120 bytes, request mode=\"fetch\" with only the semantic sections needed for the current decision.",
+    "Use representation=\"auto\" unless stable compact IDs are specifically useful. Indexed semantic-owner IDs can be resolved in batches with lookup_index_entries.",
+    "Use get_symbol_implementation when literal Python signature text, parameter spelling, docstrings, or implementation source is required; get_symbol_lineage intentionally reports canonical semantic lineage rather than reconstructing source syntax.",
+    "Use get_symbol_call_context when the task specifically needs the existing bounded intra-module caller/callee neighborhood. get_symbol_lineage provides broader canonical value/data relationships but does not recursively walk a call graph."
+  ],
+  "examples": [
+    "get_symbol_lineage(repo_path, \"pkg.module::handler\", mode=\"auto\", representation=\"auto\")",
+    "get_symbol_lineage(repo_path, \"A2496/1\", mode=\"fetch\", sections=[\"interface\", \"connections\", \"state\"], representation=\"indexed\")"
+  ]
+}

contextor/mcp/docs/get_mcp_documentation.json
diff --git a/contextor/mcp/docs/get_mcp_documentation.json b/contextor/mcp/docs/get_mcp_documentation.json
index 02a97e3..aed2f55 100644
--- a/contextor/mcp/docs/get_mcp_documentation.json
+++ b/contextor/mcp/docs/get_mcp_documentation.json
@@ -11,9 +11,9 @@
   ],
   "behavior": [
     "1. Passive documentation discovery endpoint: zero repository, LIVE state, or report reads.",
-    "2. When tool, tools, and sections are omitted (default), returns the versioned compact tool index with minimal summaries.",
+    "2. When tool, tools, and sections are omitted (default), returns the versioned compact tool index plus documentation_hint explaining how to fetch one tool's complete documentation.",
     "3. Passing tool selects a single tool's full documentation. Passing tools selects a deterministic subset of tools.",
-    "4. Passing sections restricts returned documentation to the requested sections. Passing sections without tool/tools applies the section filter to every tool in the index.",
+    "4. Passing sections restricts returned documentation to the requested sections for explicitly selected tool(s). Passing sections without tool/tools returns tool_selection_required.",
     "5. Passing conflicting tool and tools parameters returns a controlled diagnostic.",
     "6. Unknown tools or sections return invalid_documentation_query with available options."
   ],
@@ -24,7 +24,7 @@
     "Unknown tools or sections return ``invalid_documentation_query`` with deterministic unknown and available lists."
   ],
   "usage_notes": [
-    "Use the default index for discovery, then request complete documentation only for tools relevant to the current task."
+    "Use the default index and documentation_hint for discovery, then call get_mcp_documentation with tool=<tool_name> to request complete documentation only for tools relevant to the current task."
   ],
   "examples": [
     "Use ``tools=['get_module_context']`` for one complete tool document, or pass selected ``sections`` for a narrower response."

tests/test_mcp_documentation.py
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index 5512ce5..cf32bb2 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -72,7 +72,11 @@ def test_documentation_default_returns_only_index(monkeypatch):
     result = json.loads(mcp_server.get_mcp_documentation.fn())
 
     assert result["version"]
-    assert len(result["tools"]) == 27
+    assert len(result["tools"]) == 28
+    assert result["documentation_hint"] == (
+        "For full documentation of a tool, call "
+        "get_mcp_documentation with tool=<tool_name>."
+    )
     assert loaded == [documentation.INDEX_PATH]
 
 
@@ -164,3 +168,69 @@ def test_documentation_reader_paths_are_package_local(monkeypatch):
     docs_root = documentation.DOCS_DIR.resolve()
     assert read_paths
     assert all(path.parent == docs_root for path in read_paths)
+
+
+def test_get_symbol_lineage_is_registered_with_documented_public_signature():
+    tool = mcp_server.mcp._tool_manager._tools[
+        "get_symbol_lineage"
+    ]
+    index = documentation.load_documentation_index()
+    entry = next(
+        item
+        for item in index["tools"]
+        if item["tool"] == "get_symbol_lineage"
+    )
+
+    assert (
+        tool.description
+        == entry["short_description"]
+        == (
+            "Read canonical static value/data lineage for one "
+            "exact symbol from LIVE state with bounded "
+            "progressive disclosure."
+        )
+    )
+    assert str(inspect.signature(tool.fn)) == (
+        "(repo_path: str, symbol: str, mode: str = 'auto', "
+        "sections: list[str] | None = None, "
+        "representation: str = 'auto', "
+        "allow_large_output: bool = False) -> str"
+    )
+
+
+def test_get_symbol_lineage_documentation_is_lazy_and_complete(
+    monkeypatch,
+):
+    loaded = []
+    original = documentation._read_json
+
+    def tracked(path):
+        loaded.append(path)
+        return original(path)
+
+    monkeypatch.setattr(
+        documentation,
+        "_read_json",
+        tracked,
+    )
+    result = documentation.query_documentation(
+        tool="get_symbol_lineage",
+    )
+
+    assert list(result["tools"]) == [
+        "get_symbol_lineage"
+    ]
+    document = result["tools"][
+        "get_symbol_lineage"
+    ]
+    assert list(document) == list(
+        documentation.DOCUMENTATION_SECTIONS
+    )
+    assert loaded == [
+        documentation.INDEX_PATH,
+        documentation.INDEX_PATH,
+        (
+            documentation.DOCS_DIR
+            / "get_symbol_lineage.json"
+        ),
+    ]
```

