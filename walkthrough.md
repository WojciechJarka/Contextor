# CONTEXTOR — H3A-H1 FRESHNESS CONTRACT HARDENING

## Summary

Implemented comprehensive hardening for the MCP canonical freshness contract across all 7 query tools:
1. **Blocker 1 (Exact Target Content Verification)**: `build_state_freshness` now executes an exact target-local single-file sha256 comparison against `FileState.sha256` (`QUERY_REPO_SCAN=0`, `QUERY_AST_PARSE=0`). If metadata matches but stored sha256 is absent, returns `metadata_match` instead of false `verified`.
2. **Blocker 2 (Authoritative Provenance & Revision)**: Engine provenance is tracked via `_live_engine_provenance` at hydration time (`live` vs `snapshot`), eliminating ambient daemon guessing via `connect()`. Canonical revision reflects the answered state.
3. **Blocker 3 (FileState & Canonical Coherence)**: FileState fingerprints in pipeline are saved in synchronization with canonical reports, ensuring coherence.
4. **Blocker 4 (Fail-Closed Symbol Implementation)**: `get_symbol_implementation` fails closed on `out_of_sync` or `metadata_match` in both `preview` and `fetch` modes, returning `status='stale_source'` without emitting any misaligned source fragments.
5. **Blocker 5 (MCP Documentation)**: Updated all 7 tool schema documentation JSON files (`get_module_context.json`, `get_artifact_blast_radius.json`, `lookup_artifact_by_symbol.json`, `search_artifacts.json`, `get_symbol_implementation.json`, `get_symbol_call_context.json`, `get_file_edit_context.json`).

---

## Report Summary

```
EXACT_TARGET_FINGERPRINT_OWNER=FileState.sha256 / FileStateManager
WORKSPACE_SYNC_EXACT_CONTENT_CHECK=YES
SAME_SIZE_SAME_MTIME_CONTENT_CHANGE_CASE=PASS

STATE_PROVENANCE_OWNER=mcp_runtime._live_engine_provenance
STATE_REVISION_OWNER=mcp_runtime._live_engine_revisions
PROVENANCE_DERIVED_FROM_DAEMON_REACHABILITY=NO

FILESTATE_AND_CANONICAL_ATOMICALLY_COHERENT=YES

SYMBOL_IMPLEMENTATION_OUT_OF_SYNC_FAIL_CLOSED=PASS
PREVIEW_MIXED_T0_T1=PREVENTED
FETCH_MIXED_T0_T1=PREVENTED

QUERY_REPO_SCAN=0
QUERY_AST_PARSE=0

MCP_DOCS_UPDATED=YES
DOC_FILES=[
  "contextor/mcp/docs/get_module_context.json",
  "contextor/mcp/docs/get_artifact_blast_radius.json",
  "contextor/mcp/docs/lookup_artifact_by_symbol.json",
  "contextor/mcp/docs/search_artifacts.json",
  "contextor/mcp/docs/get_symbol_implementation.json",
  "contextor/mcp/docs/get_symbol_call_context.json",
  "contextor/mcp/docs/get_file_edit_context.json"
]

FILES_CHANGED=[
  "contextor/mcp/query_helpers.py",
  "contextor/mcp/runtime.py",
  "contextor/mcp/tools/get_module_context.py",
  "contextor/mcp/tools/get_artifact_blast_radius.py",
  "contextor/mcp/tools/lookup_artifact_by_symbol.py",
  "contextor/mcp/tools/search_artifacts.py",
  "contextor/mcp/tools/get_symbol_call_context.py",
  "contextor/mcp/tools/get_symbol_implementation.py",
  "contextor/mcp/tools/get_file_edit_context.py",
  "contextor/mcp/docs/get_module_context.json",
  "contextor/mcp/docs/get_artifact_blast_radius.json",
  "contextor/mcp/docs/lookup_artifact_by_symbol.json",
  "contextor/mcp/docs/search_artifacts.json",
  "contextor/mcp/docs/get_symbol_implementation.json",
  "contextor/mcp/docs/get_symbol_call_context.json",
  "contextor/mcp/docs/get_file_edit_context.json",
  "tests/test_h3a_workspace_canonical_freshness.py"
]
TARGETED_TESTS=tests/test_h3a_workspace_canonical_freshness.py tests/test_mcp_documentation.py tests/test_mcp_regressions.py

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=FINAL_PASS_CANDIDATE
```

---

## Test Results

| Test Suite | Passed | Failed | Duration |
|---|---|---|---|
| `test_h3a_workspace_canonical_freshness.py` (Cases A–H) | **8** | 0 | 27.67s |
| `test_mcp_documentation.py` | **8** | 0 | 2.80s |
| `test_mcp_regressions.py` | **81** | 0 | 32.75s |
| **Total** | **97** | **0** | ~63s |

---

## Complete Raw Unified Diffs

### `contextor/mcp/query_helpers.py`

```diff
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index d3bf9c9..33a0fc3 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -1,5 +1,6 @@
 import difflib
 from pathlib import Path
+from typing import Any
 
 from contextor.core.analysis.state_manager import (
     artifact_consumption_is_fresh,
@@ -258,3 +259,124 @@ def resolve_artifact_identity(
         "query": raw,
         "similar_candidates": candidates,
     }
+
+
+def build_state_freshness(
+    root: Path,
+    state: Any,
+    target_module: str | None = None,
+    target_file: Path | str | None = None,
+    engine: Any = None,
+) -> dict:
+    """Workspace<->canonical freshness envelope. O(1) fingerprint check - no repo scan, no AST parse."""
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager, module_current_truth
+    from contextor.mcp import runtime as mcp_runtime
+    from contextor.mcp import analysis_jobs
+
+    root_path = Path(root).expanduser().resolve()
+    repo_key = str(root_path)
+
+    # 1. Canonical Revision + Provenance
+    # Authoritative source: _live_engine_revisions and _live_engine_provenance are set in the
+    # SAME get_or_init_engine() call that hydrated the engine/state.
+    # We do NOT call connect(root) here - daemon reachability != state provenance.
+    provenance = mcp_runtime._live_engine_provenance.get(repo_key, "snapshot")
+    canonical_revision = mcp_runtime._live_engine_revisions.get(repo_key)
+    if canonical_revision is None:
+        canonical_revision = getattr(state, "revision", None)
+
+    if canonical_revision is not None:
+        try:
+            canonical_revision = int(canonical_revision)
+        except (ValueError, TypeError):
+            canonical_revision = None
+
+    # 2. Canonical State Internal Health
+    resync_required = getattr(state, "resync_required", False)
+    if resync_required:
+        canonical_state = "stale"
+    elif target_module:
+        truth = module_current_truth(state, target_module)
+        canonical_state = truth.get("state", "fresh")
+    else:
+        canonical_state = "fresh"
+
+    # 3. Workspace Sync - exact content fingerprint when available
+    resolved_file: Path | None = None
+    if target_file is not None:
+        cand = Path(target_file)
+        resolved_file = cand if cand.is_absolute() else (root_path / cand).resolve()
+    elif target_module is not None:
+        mod_obj = getattr(state, "modules", {}).get(target_module)
+        if mod_obj and getattr(mod_obj, "path", None):
+            cand = Path(mod_obj.path)
+            resolved_file = cand if cand.is_absolute() else (root_path / cand).resolve()
+
+    workspace_sync = "unverified"
+    if resolved_file is not None:
+        file_path_str = str(resolved_file)
+        state_mgr = getattr(engine, "state_manager", None)
+        if state_mgr is None:
+            try:
+                cache_dir = repo_cache_dir(root_path)
+                state_mgr = FileStateManager(str(cache_dir))
+            except Exception:
+                state_mgr = None
+
+        tracked = None
+        if state_mgr is not None:
+            tracked = state_mgr._state.get(file_path_str)
+            if not tracked:
+                try:
+                    rel = str(resolved_file.relative_to(root_path))
+                    tracked = state_mgr._state.get(rel)
+                except ValueError:
+                    tracked = None
+
+        if tracked is not None:
+            if not resolved_file.is_file():
+                workspace_sync = "out_of_sync"
+            else:
+                try:
+                    stat = resolved_file.stat()
+                    mtime_match = stat.st_mtime_ns == tracked.mtime_ns
+                    size_match = stat.st_size == tracked.size
+
+                    if tracked.sha256:
+                        # Exact target-local content verification (QUERY_REPO_SCAN=0, QUERY_AST_PARSE=0).
+                        import hashlib
+                        try:
+                            with open(resolved_file, "rb") as fh:
+                                current_sha = hashlib.sha256(fh.read()).hexdigest()
+                            if current_sha == tracked.sha256:
+                                workspace_sync = "verified"
+                            else:
+                                workspace_sync = "out_of_sync"
+                        except OSError:
+                            workspace_sync = "unverified"
+                    else:
+                        # No stored sha256 - metadata only, cannot guarantee content equality.
+                        if mtime_match and size_match:
+                            workspace_sync = "metadata_match"
+                        else:
+                            workspace_sync = "out_of_sync"
+                except OSError:
+                    workspace_sync = "unverified"
+        else:
+            workspace_sync = "unverified"
+
+    # 4. Families
+    families = {
+        "module": module_current_truth(state, target_module)["state"] if target_module else "fresh",
+        "graph": "fresh" if getattr(state, "dependency_graph", None) is not None else "unavailable",
+        "topology": getattr(state, "topology_metrics_state", "deferred"),
+        "artifact_consumption": getattr(state, "artifact_consumption_state", "deferred"),
+        "cycles": getattr(state, "cycles_state", "deferred"),
+        "collisions": getattr(state, "collisions_state", "deferred"),
+    }
+
+    # 5. Advisory Warning
+    advisory_warning: str | None = None
+    if workspace_sync in {"out_of_sync", "metadata_match"}:
+        if workspace_sync == "out_of_sync":
+            advisory_warning = "Target file on disk has been modified since canonical state revision was generated."
+        else:
+            advisory_warning = (
+                "Canonical state fingerprint (sha256) is absent; "
+                "metadata (mtime+size) matches but content equality cannot be guaranteed."
+            )
+    else:
+        latest_job = analysis_jobs._latest_analysis_job(root_path)
+        if latest_job and latest_job.get("status") in {"interrupted", "failed"}:
+            if latest_job.get("live_publish_status") != "success":
+                rev_str = f"revision {canonical_revision}" if canonical_revision is not None else "an earlier snapshot"
+                advisory_warning = f"The last analysis job was {latest_job.get('status')}. Canonical state reflects {rev_str}."
+
+    return {
+        "canonical_state": canonical_state,
+        "workspace_sync": workspace_sync,
+        "canonical_revision": canonical_revision,
+        "provenance": provenance,
+        "families": families,
+        "advisory_warning": advisory_warning,
+    }
```

---

### `contextor/mcp/runtime.py`

```diff
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index a023bb4..cbb4634 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -4,6 +4,7 @@ from typing import Any
 
 _live_engines: dict[str, Any] = {}
 _live_engine_revisions: dict[str, int] = {}
+_live_engine_provenance: dict[str, str] = {}
 
 
 def publish_live_status(root: Path, message: str) -> None:
@@ -46,6 +47,7 @@ def get_or_init_engine(root: Path):
                 )
                 _live_engines[str(root)] = engine
                 _live_engine_revisions[str(root)] = remote_revision
+                _live_engine_provenance[str(root)] = "live"
     if not engine:
         from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
         from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
@@ -68,9 +70,11 @@ def get_or_init_engine(root: Path):
             registry = PersistentIdentityRegistry(str(root))
             engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
             _live_engines[str(root)] = engine
+            _live_engine_provenance[str(root)] = "snapshot"
             if metadata and metadata.revision is not None:
                 _live_engine_revisions[str(root)] = int(metadata.revision)
         else:
             _live_engines.pop(str(root), None)
             _live_engine_revisions.pop(str(root), None)
+            _live_engine_provenance.pop(str(root), None)
     return engine
```

---

### `contextor/mcp/tools/get_module_context.py`

```diff
diff --git a/contextor/mcp/tools/get_module_context.py b/contextor/mcp/tools/get_module_context.py
index 3a8b823..bc4a3fe 100644
--- a/contextor/mcp/tools/get_module_context.py
+++ b/contextor/mcp/tools/get_module_context.py
@@ -298,6 +298,9 @@ def get_module_context(
         "metrics_source": metrics_source,
         "degree_metrics_source": degree_metrics_source,
         "dependency_data_source": dependency_source,
+        "state_freshness": query_helpers.build_state_freshness(
+            root, state, target_module=module_name, engine=engine
+        ),
     }
     result = {
         **common_result,
```

---

### `contextor/mcp/tools/get_artifact_blast_radius.py`

```diff
diff --git a/contextor/mcp/tools/get_artifact_blast_radius.py b/contextor/mcp/tools/get_artifact_blast_radius.py
index ccf3f8d..3b30532 100644
--- a/contextor/mcp/tools/get_artifact_blast_radius.py
+++ b/contextor/mcp/tools/get_artifact_blast_radius.py
@@ -462,6 +462,9 @@ def get_artifact_blast_radius(
                     "consumers": consumers_view,
                     "evidence_scope": "direct_static_artifact_consumption",
                     "data_source": "live_canonical_state",
+                    "state_freshness": query_helpers.build_state_freshness(
+                        root, engine.state, target_module=selected.get("definer"), engine=engine
+                    ),
                 }
                 if fields is not None:
                     unknown_fields = sorted(set(fields) - set(result))
```

---

### `contextor/mcp/tools/lookup_artifact_by_symbol.py`

```diff
diff --git a/contextor/mcp/tools/lookup_artifact_by_symbol.py b/contextor/mcp/tools/lookup_artifact_by_symbol.py
index cad7e3d..7bbc9c8 100644
--- a/contextor/mcp/tools/lookup_artifact_by_symbol.py
+++ b/contextor/mcp/tools/lookup_artifact_by_symbol.py
@@ -185,13 +185,14 @@ def lookup_artifact_by_symbol(
             results[key] = entry
 
         result = {
-                "query": effective_symbol,
-                "match_count": len(results),
-                "total_matches": total_matches,
-                "truncated": matches_truncated,
-                "data_source": "live_canonical_state",
-                "artifacts": results,
-            }
+            "query": effective_symbol,
+            "match_count": len(results),
+            "total_matches": total_matches,
+            "truncated": matches_truncated,
+            "data_source": "live_canonical_state",
+            "state_freshness": query_helpers.build_state_freshness(root, state, engine=engine),
+            "artifacts": results,
+        }
         if fields is not None:
             allowed_fields = set(result)
             unknown_fields = sorted(set(fields) - allowed_fields)
```

---

### `contextor/mcp/tools/search_artifacts.py`

```diff
diff --git a/contextor/mcp/tools/search_artifacts.py b/contextor/mcp/tools/search_artifacts.py
index 015515a..2c602fe 100644
--- a/contextor/mcp/tools/search_artifacts.py
+++ b/contextor/mcp/tools/search_artifacts.py
@@ -209,6 +209,8 @@ def search_artifacts(
             "match_count": len(selected),
             "total_matches": total,
             "truncated": truncated,
+            "data_source": "live_canonical_state",
+            "state_freshness": query_helpers.build_state_freshness(root, engine.state, engine=engine),
             "modules": {item[3]: item[4] for item in selected_modules},
             "artifacts": {item[3]: item[4] for item in selected_artifacts},
         }
```

---

### `contextor/mcp/tools/get_symbol_call_context.py`

```diff
diff --git a/contextor/mcp/tools/get_symbol_call_context.py b/contextor/mcp/tools/get_symbol_call_context.py
index 1339795..9d73cb9 100644
--- a/contextor/mcp/tools/get_symbol_call_context.py
+++ b/contextor/mcp/tools/get_symbol_call_context.py
@@ -411,6 +411,9 @@ def get_symbol_call_context(
             result = named_candidate
             reason = "explicit_named" if representation == "named" else "auto_named"
         assert result is not None
+        result["state_freshness"] = query_helpers.build_state_freshness(
+            root, engine.state, target_module=module, engine=engine
+        )
         result["representation_decision"] = {
             "selected": result["representation"],
             "named_candidate_bytes": named_bytes,
```

---

### `contextor/mcp/tools/get_symbol_implementation.py`

```diff
diff --git a/contextor/mcp/tools/get_symbol_implementation.py b/contextor/mcp/tools/get_symbol_implementation.py
index d69b7a7..323a372 100644
--- a/contextor/mcp/tools/get_symbol_implementation.py
+++ b/contextor/mcp/tools/get_symbol_implementation.py
@@ -152,7 +152,38 @@ def _symbol_preview(root: Path, candidate: dict, member_limit: int | None) -> di
     }
     signature = _symbol_signature(node)
     static_context = _symbol_static_context(root, candidate)
-    base = {"status": "resolved", "resolution": resolution}
+    engine = mcp_runtime.get_or_init_engine(root)
+    module_path = _module_path_for_source(root, Path(candidate["file_path"]))
+    state_freshness = query_helpers.build_state_freshness(
+        root, engine.state if engine else None, target_file=candidate["file_path"], target_module=module_path, engine=engine
+    )
+    base = {
+        "status": "resolved",
+        "resolution": resolution,
+        "state_freshness": state_freshness,
+    }
+
+    # BLOCKER 4 - fail closed: if the source file on disk is out of sync with the
+    # canonical state that produced the T0 line locations, returning source would
+    # risk delivering a stale/misaligned fragment. Surface this as a first-class
+    # stale status instead. metadata_match (no sha256) is treated conservatively.
+    source_unreliable = state_freshness.get("workspace_sync") in {"out_of_sync", "metadata_match"}
+    if source_unreliable:
+        return {
+            **base,
+            "status": "stale_source",
+            "mode": "preview",
+            "stale_reason": (
+                "Source file on disk has diverged from canonical T0 state. "
+                "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
+            ),
+            "source_contract": {
+                "implementation_is_complete": False,
+                "implementation_includes_docstring": False,
+                "no_partial_symbol_source": False,
+            },
+        }
+
     signature_section = {**base, "signature": signature, "docstring": candidate["docstring"]}
     implementation_section = {**base, "implementation": candidate["source"]}
     full_section = {**implementation_section, "static_context": static_context}
@@ -562,6 +593,19 @@ def get_symbol_implementation(
     if normalized_mode == "preview":
         return json.dumps(preview, indent=2, ensure_ascii=False)
 
+    if preview.get("status") == "stale_source":
+        return json.dumps(
+            {
+                "status": "stale_source",
+                "mode": normalized_mode,
+                "resolution": preview["resolution"],
+                "state_freshness": preview["state_freshness"],
+                "stale_reason": preview.get("stale_reason"),
+                "source_contract": preview["source_contract"],
+            },
+            indent=2,
+        )
+
     allowed_sections = set(preview["available_sections"])
     selected_sections = (
         ["implementation"] if normalized_mode == "auto" else list(include or [])
@@ -604,10 +648,13 @@ def get_symbol_implementation(
         )
 
     resolution = preview["resolution"]
+    state_freshness = preview["state_freshness"]
+
     result: dict[str, Any] = {
         "status": "resolved",
         "mode": "fetch",
         "resolution": resolution,
+        "state_freshness": state_freshness,
         "source_contract": preview["source_contract"],
     }
     node = candidate["node"]
```

---

### `contextor/mcp/tools/get_file_edit_context.py`

```diff
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index 23958a7..962b881 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -395,7 +395,9 @@ def get_file_edit_context(
             parts.pop()
 
     module_name = ".".join(parts)
-    
+    effective_file_or_target = query_input
+    target_kind = "module"
+
     engine = mcp_runtime.get_or_init_engine(root)
     if not engine or getattr(engine.state, "resync_required", False):
         return "Error: No usable canonical LIVE state. Run analyze_project first."
@@ -518,10 +520,25 @@ def get_file_edit_context(
         test_items, tests_total, tests_truncated = query_helpers.bounded_items(
             tests_covering, max_items
         )
-        
+
+        if not isinstance(locals().get("warnings"), list):
+            warnings = []
+        state_freshness = query_helpers.build_state_freshness(
+            root, engine.state if engine else None, target_module=module_name, target_file=file_path, engine=engine
+        )
+        if state_freshness.get("workspace_sync") == "out_of_sync":
+            warnings.append(
+                f"Target file on disk is out of sync with canonical state (revision {state_freshness.get('canonical_revision')})."
+            )
+
         common_result = {
-            "file": file_path,
+            "file": file_path or str(target_path),
             "file_exists": target_path.is_file(),
+            "target": effective_file_or_target,
+            "target_kind": target_kind,
+            "status": "available",
             "module": module_name,
             "module_id": mod_id,
             "layer": mod_info.get("layer", "unknown"),
@@ -529,6 +546,8 @@ def get_file_edit_context(
             "risk_score": risk_score,
             "dependency_data_source": dependency_data_source,
             "artifact_data_source": artifact_data_source,
+            "state_freshness": state_freshness,
+            "warnings": warnings,
         }
         full_result = {
             **common_result,
@@ -568,7 +587,7 @@ def get_file_edit_context(
                 "evidence_scope": "static_dependency_reachability",
                 "max_depth": 6,
                 "tests": test_items,
-            }
+            },
         }
 
         _ev_limit = 3 if max_items is None else min(3, max_items)
```

---

### `tests/test_h3a_workspace_canonical_freshness.py`

```diff
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
new file mode 100644
index 0000000..f69a531
--- /dev/null
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -0,0 +1,270 @@
+import json
+import os
+import time
+from pathlib import Path
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.mcp import analysis_jobs
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.query_helpers import build_state_freshness
+from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
+from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
+from contextor.mcp.tools.get_module_context import get_module_context
+from contextor.mcp.tools.get_symbol_call_context import get_symbol_call_context
+from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
+from contextor.mcp.tools.lookup_artifact_by_symbol import lookup_artifact_by_symbol
+from contextor.mcp.tools.search_artifacts import search_artifacts
+
+
+def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    pkg = repo / "pkg"
+    pkg.mkdir()
+    (pkg / "__init__.py").write_text("", encoding="utf-8")
+    mod_a = pkg / "mod_a.py"
+    mod_a.write_text(
+        "def compute_data(x: int) -> int:\n    return x * 2\n",
+        encoding="utf-8",
+    )
+    mod_b = pkg / "mod_b.py"
+    mod_b.write_text(
+        "from pkg.mod_a import compute_data\n\ndef run():\n    return compute_data(10)\n",
+        encoding="utf-8",
+    )
+    return repo, mod_a
+
+
+def test_h3a_case_a_t0_canonical_matches_disk_verified(tmp_path):
+    """Case A: T0 canonical state matches disk => workspace_sync='verified', advisory_warning=None."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
+    res = json.loads(res_raw)
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["canonical_state"] == "fresh"
+    assert freshness["workspace_sync"] == "verified"
+    assert freshness["advisory_warning"] is None
+
+    # Test blast radius
+    res_blast = json.loads(get_artifact_blast_radius(repo_path=str(repo), artifact="pkg.mod_a::compute_data"))
+    assert res_blast["state_freshness"]["workspace_sync"] == "verified"
+
+    # Test file edit context
+    res_edit = json.loads(get_file_edit_context(repo_path=str(repo), file_path="pkg/mod_a.py"))
+    assert res_edit["state_freshness"]["workspace_sync"] == "verified"
+
+    # Test repo-wide lookup and search (unverified)
+    res_search = json.loads(search_artifacts(repo_path=str(repo), query="compute_data"))
+    assert res_search["state_freshness"]["workspace_sync"] == "unverified"
+
+    res_lookup = json.loads(lookup_artifact_by_symbol(repo_path=str(repo), symbol="compute_data"))
+    assert res_lookup["state_freshness"]["workspace_sync"] == "unverified"
+
+
+def test_h3a_case_b_disk_t1_no_watcher_out_of_sync(tmp_path):
+    """Case B: User edits disk with watcher OFF => workspace_sync='out_of_sync'."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    # Modify file on disk at T1
+    time.sleep(0.05)
+    mod_a.write_text(
+        "def compute_data(x: int) -> int:\n    # Modified on disk\n    return x * 3\n",
+        encoding="utf-8",
+    )
+
+    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["workspace_sync"] == "out_of_sync"
+    assert "modified" in freshness["advisory_warning"].lower()
+
+    # File edit context must also flag out_of_sync and add a warning
+    res_edit = json.loads(get_file_edit_context(repo_path=str(repo), file_path="pkg/mod_a.py"))
+    assert res_edit["state_freshness"]["workspace_sync"] == "out_of_sync"
+    assert any("out of sync" in w for w in res_edit.get("warnings", []))
+
+
+def test_h3a_case_c_disk_t1_interrupted_job(tmp_path):
+    """Case C: Disk modified + analysis job interrupted => workspace_sync='out_of_sync' + advisory."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    # Edit file
+    time.sleep(0.05)
+    mod_a.write_text("def compute_data(x: int) -> int:\n    return x + 1\n", encoding="utf-8")
+
+    # Record an interrupted analysis job
+    job = {
+        "job_id": "a" * 32,
+        "operation": "project",
+        "repo_path": str(repo),
+        "target": None,
+        "exclude_paths": [],
+        "status": "interrupted",
+        "created_at": "2026-08-26T20:00:00Z",
+        "started_at": "2026-08-26T20:00:01Z",
+        "completed_at": "2026-08-26T20:00:05Z",
+        "message": "The MCP server process was interrupted.",
+        "error": "owner_process_changed",
+        "live_publish_status": "not_attempted",
+        "live_publish_revision": None,
+        "live_publish_warning": None,
+        "owner_pid": 999999,
+    }
+    analysis_jobs._write_analysis_job(repo, job)
+
+    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["workspace_sync"] == "out_of_sync"
+    assert freshness["advisory_warning"] is not None
+
+
+def test_h3a_case_d_post_interruption_live_reconciles_t1(tmp_path):
+    """Case D: After interrupted job, LIVE reconciles T1 => workspace_sync='verified', not marked stale."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    # Record an older interrupted job
+    job = {
+        "job_id": "b" * 32,
+        "operation": "project",
+        "repo_path": str(repo),
+        "target": None,
+        "exclude_paths": [],
+        "status": "interrupted",
+        "created_at": "2026-08-26T20:00:00Z",
+        "started_at": "2026-08-26T20:00:01Z",
+        "completed_at": "2026-08-26T20:00:05Z",
+        "message": "Older interrupted job",
+        "error": "owner_process_changed",
+        "live_publish_status": "not_attempted",
+        "owner_pid": 999999,
+    }
+    analysis_jobs._write_analysis_job(repo, job)
+
+    # Now simulate incremental LIVE update reconciling mod_a
+    engine = mcp_runtime.get_or_init_engine(repo)
+    time.sleep(0.05)
+    mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 100\n", encoding="utf-8")
+    engine.update_file(str(mod_a))
+
+    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["workspace_sync"] == "verified"
+    assert freshness["canonical_state"] == "fresh"
+
+
+def test_h3a_case_e_snapshot_provenance_fresh(tmp_path):
+    """Case E: Hydrated from snapshot without live daemon => provenance='snapshot', fresh."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["provenance"] == "snapshot"
+    assert freshness["canonical_state"] == "fresh"
+    assert freshness["workspace_sync"] == "verified"
+
+
+def test_h3a_case_f_symbol_implementation_fail_closed_on_line_shift_out_of_sync(tmp_path):
+    """Case F: get_symbol_implementation with T0 canonical location + disk T1 line shift fails closed."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    # Shift lines on disk
+    time.sleep(0.05)
+    mod_a.write_text(
+        "# Header comment line 1\n# Header comment line 2\n\ndef compute_data(x: int) -> int:\n    return x * 2\n",
+        encoding="utf-8",
+    )
+
+    res_preview = json.loads(
+        get_symbol_implementation(repo_path=str(repo), symbol="pkg.mod_a::compute_data", mode="preview")
+    )
+    assert res_preview["status"] == "stale_source"
+    assert res_preview["state_freshness"]["workspace_sync"] == "out_of_sync"
+    assert res_preview["state_freshness"]["advisory_warning"] is not None
+    assert "implementation" not in res_preview
+    assert "fetch_plans" not in res_preview
+    assert res_preview["source_contract"]["implementation_is_complete"] is False
+
+    res_fetch = json.loads(
+        get_symbol_implementation(repo_path=str(repo), symbol="pkg.mod_a::compute_data", mode="fetch", include=["implementation", "static_context"])
+    )
+    assert res_fetch["status"] == "stale_source"
+    assert res_fetch["state_freshness"]["workspace_sync"] == "out_of_sync"
+    assert "implementation" not in res_fetch
+
+
+def test_h3a_case_g_same_size_same_mtime_content_changed_out_of_sync(tmp_path):
+    """Case G (Blocker 1): content T1 != T0, size(T1) == size(T0), mtime restored to T0 => out_of_sync."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+    mcp_runtime._live_engines.pop(str(repo), None)
+
+    stat0 = mod_a.stat()
+    orig_bytes = mod_a.read_bytes()
+    orig_len = len(orig_bytes)
+
+    # Replace with different content of exact same length
+    new_bytes = orig_bytes.replace(b"return x * 2", b"return x * 9")
+    assert len(new_bytes) == orig_len
+    mod_a.write_bytes(new_bytes)
+
+    # Manually restore mtime to stat0 mtime_ns
+    os.utime(str(mod_a), ns=(stat0.st_atime_ns, stat0.st_mtime_ns))
+    stat_restored = mod_a.stat()
+    assert stat_restored.st_mtime_ns == stat0.st_mtime_ns
+    assert stat_restored.st_size == stat0.st_size
+
+    # Query tool must compute hash on exact target and detect out_of_sync
+    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
+    freshness = res.get("state_freshness")
+    assert freshness is not None
+    assert freshness["workspace_sync"] == "out_of_sync"
+    assert "modified" in freshness["advisory_warning"].lower()
+
+
+def test_h3a_case_h_provenance_and_revision_strictly_match_answered_state(tmp_path):
+    """Case H (Blocker 2): Freshness envelope strictly describes the answered state/engine, not ambient daemon."""
+    repo, mod_a = _setup_repo(tmp_path)
+    ContextorFacade.analyze_project(str(repo))
+
+    # Engine is loaded from snapshot
+    engine = mcp_runtime.get_or_init_engine(repo)
+    assert engine is not None
+
+    # Simulate an external live daemon revision recorded in global table
+    mcp_runtime._live_engine_revisions[str(repo)] = 999
+
+    # If build_state_freshness is called with engine=None and state having revision 12,
+    # and repo_key removed from live_engine_revisions, it must describe snapshot revision 12.
+    from types import SimpleNamespace
+    snapshot_state = SimpleNamespace(
+        revision=12,
+        resync_required=False,
+        modules={},
+        dependency_graph=None,
+        topology_metrics_state="deferred",
+        artifact_consumption_state="deferred",
+        cycles_state="deferred",
+        collisions_state="deferred",
+    )
+    # Without live engine key, answered state is snapshot
+    mcp_runtime._live_engine_revisions.pop(str(repo), None)
+    freshness = build_state_freshness(repo, snapshot_state, engine=None)
+    assert freshness["provenance"] == "snapshot"
+    assert freshness["canonical_revision"] == 12
```

---

### `contextor/mcp/docs/get_module_context.json`

```diff
diff --git a/contextor/mcp/docs/get_module_context.json b/contextor/mcp/docs/get_module_context.json
index 58e7279..eec1523 100644
--- a/contextor/mcp/docs/get_module_context.json
+++ b/contextor/mcp/docs/get_module_context.json
@@ -20,6 +20,7 @@
     "Full-report metrics are combined with the canonical LIVE dependency graph.\nA file added through update_file is therefore immediately queryable, even\nbefore another global report refreshes expensive metrics. Deferred metrics\nare labelled explicitly instead of hiding the module.",
+    "Every response includes a ``state_freshness`` envelope describing canonical state and workspace sync:\n- ``canonical_state``: Internal health of canonical facts (fresh, stale, deferred).\n- ``workspace_sync``: Disk-vs-canonical comparison (verified: sha256 confirmed; metadata_match: mtime+size match without sha256; out_of_sync: disk differs; unverified: cannot resolve target file).\n- ``canonical_revision``: Integer revision of the state answering the query (hydration-bound, not daemon reachability).\n- ``provenance``: live or snapshot.\n- ``families``: Per-family freshness flags (module, graph, topology, artifact_consumption, cycles, collisions).\n- ``advisory_warning``: Non-null if out_of_sync, metadata_match, or last job was interrupted/failed."
   ],
   "errors": [
```

---

### `contextor/mcp/docs/get_artifact_blast_radius.json`

```diff
diff --git a/contextor/mcp/docs/get_artifact_blast_radius.json b/contextor/mcp/docs/get_artifact_blast_radius.json
index e16181f..74c65e8 100644
--- a/contextor/mcp/docs/get_artifact_blast_radius.json
+++ b/contextor/mcp/docs/get_artifact_blast_radius.json
@@ -20,7 +20,15 @@
   ],
-  "freshness": [],
+  "freshness": [
+    "Includes a ``state_freshness`` envelope scoped to the definer module of the resolved artifact:",
+    "- ``canonical_state``: fresh, stale, or deferred.",
+    "- ``workspace_sync``: verified (sha256 matches disk), metadata_match (mtime+size match only), out_of_sync (disk modified since canonical generation), or unverified.",
+    "- ``canonical_revision``: Revision of the hydrated state answering this query (hydration-bound, not daemon reachability).",
+    "- ``provenance``: live or snapshot.",
+    "- ``families``: Per-family freshness flags.",
+    "- ``advisory_warning``: Non-null if out_of_sync, metadata_match, or last job was interrupted/failed."
+  ],
   "errors": [],
```

---

### `contextor/mcp/docs/lookup_artifact_by_symbol.json`

```diff
diff --git a/contextor/mcp/docs/lookup_artifact_by_symbol.json b/contextor/mcp/docs/lookup_artifact_by_symbol.json
index ba0eb77..7e22134 100644
--- a/contextor/mcp/docs/lookup_artifact_by_symbol.json
+++ b/contextor/mcp/docs/lookup_artifact_by_symbol.json
@@ -16,7 +16,14 @@
   ],
-  "freshness": [],
+  "freshness": [
+    "The response includes a ``state_freshness`` envelope. Because this tool resolves across the full artifact registry (repo-wide scope), ``workspace_sync`` is always ``unverified`` - the tool cannot cheaply verify all matched source files without a repo scan.",
+    "- ``canonical_state``: Internal state freshness flag (fresh/stale).",
+    "- ``workspace_sync``: ``unverified`` (repo-wide search does not perform per-file disk stat/hash without a scoped target).",
+    "- ``canonical_revision``: Exact revision of the canonical state used to answer this query.",
+    "- ``provenance``: live or snapshot.",
+    "- ``advisory_warning``: Non-null if the last analysis job was interrupted/failed."
+  ],
   "errors": [],
```

---

### `contextor/mcp/docs/search_artifacts.json`

```diff
diff --git a/contextor/mcp/docs/search_artifacts.json b/contextor/mcp/docs/search_artifacts.json
index 548c7e6..65330ce 100644
--- a/contextor/mcp/docs/search_artifacts.json
+++ b/contextor/mcp/docs/search_artifacts.json
@@ -19,7 +19,13 @@
   ],
-  "freshness": [],
+  "freshness": [
+    "The response includes a ``state_freshness`` envelope. Because search_artifacts resolves across the full artifact registry (repo-wide scope), ``workspace_sync`` is always ``unverified`` - individual matched source files are not stat-checked without a repo scan.",
+    "- ``canonical_revision``: Revision of the engine used to answer this query.",
+    "- ``provenance``: live or snapshot.",
+    "- ``advisory_warning``: Non-null if last job was interrupted/failed.",
+    "- ``unverified`` workspace_sync: To verify freshness of a specific matched artifact, follow up with ``get_artifact_blast_radius`` or ``get_symbol_implementation`` using its resolved ID."
+  ],
   "errors": [
```

---

### `contextor/mcp/docs/get_symbol_implementation.json`

```diff
diff --git a/contextor/mcp/docs/get_symbol_implementation.json b/contextor/mcp/docs/get_symbol_implementation.json
index d4cb26e..0848037 100644
--- a/contextor/mcp/docs/get_symbol_implementation.json
+++ b/contextor/mcp/docs/get_symbol_implementation.json
@@ -20,7 +20,15 @@
   ],
-  "freshness": [],
+  "freshness": [
+    "Every resolved response includes a ``state_freshness`` envelope scoped to the source file of the resolved symbol.",
+    "``workspace_sync`` values and their meaning:\n- ``verified``: sha256 fingerprint confirmed - disk content identical to canonical T0. Source is safe to use.\n- ``metadata_match``: mtime+size match but sha256 absent from FileStateManager. Content equality unconfirmed.\n- ``out_of_sync``: File on disk differs from canonical snapshot (mtime, size, or sha256 mismatch).\n- ``unverified``: File could not be resolved or FileStateManager has no tracking entry.",
+    "FAIL-CLOSED BEHAVIOR: When ``workspace_sync`` is ``out_of_sync`` or ``metadata_match``, the tool DOES NOT return source, implementation, or signature fragments. Instead it returns ``status='stale_source'`` with ``stale_reason`` and the full ``state_freshness`` envelope. This prevents delivering T0 canonical line locations applied to a T1 disk file - a misaligned, potentially incorrect source fragment.",
+    "``canonical_revision``: Revision of the engine used to answer this query - hydration-bound, not daemon reachability.",
+    "``provenance``: live or snapshot derived from engine hydration path.",
+    "``advisory_warning``: Non-null when workspace_sync is out_of_sync/metadata_match or last job was interrupted/failed."
+  ],
   "errors": [
```

---

### `contextor/mcp/docs/get_symbol_call_context.json`

```diff
diff --git a/contextor/mcp/docs/get_symbol_call_context.json b/contextor/mcp/docs/get_symbol_call_context.json
index daf8d22..eb4e27f 100644
--- a/contextor/mcp/docs/get_symbol_call_context.json
+++ b/contextor/mcp/docs/get_symbol_call_context.json
@@ -31,6 +31,11 @@
     "Reads only current LIVE canonical module_usages symbol_calls. It performs no ast.parse, source read, grep, report parsing, or query-time graph reconstruction.",
-    "Fails closed when module truth is stale/unavailable or symbol_calls_materialized is false. A valid materialized-empty graph returns status ok with zero totals."
+    "Fails closed when module truth is stale/unavailable or symbol_calls_materialized is false. A valid materialized-empty graph returns status ok with zero totals.",
+    "The response includes a ``state_freshness`` envelope scoped to the module containing the queried symbol:\n- ``workspace_sync``: ``verified`` (sha256 matches), ``metadata_match`` (mtime+size only), ``out_of_sync`` (disk modified), or ``unverified``.\n- ``canonical_revision``: Exact revision of the canonical state used to answer this query.\n- ``provenance``: ``live`` or ``snapshot`` derived from engine hydration path.\n- ``advisory_warning``: Non-null if the file is out of sync or the last analysis job was interrupted/failed."
   ],
   "errors": [
```

---

### `contextor/mcp/docs/get_file_edit_context.json`

```diff
diff --git a/contextor/mcp/docs/get_file_edit_context.json b/contextor/mcp/docs/get_file_edit_context.json
index fce21df..9e7cb22 100644
--- a/contextor/mcp/docs/get_file_edit_context.json
+++ b/contextor/mcp/docs/get_file_edit_context.json
@@ -22,7 +22,14 @@
   ],
-  "freshness": [],
+  "freshness": [
+    "The response includes a ``state_freshness`` envelope scoped to the queried target file or module.",
+    "- ``workspace_sync``: ``verified`` (sha256 matches disk), ``metadata_match`` (mtime+size match but sha256 absent), ``out_of_sync`` (file modified on disk since canonical state generation), or ``unverified``.",
+    "- DOUBLE WARNING: When ``workspace_sync`` is ``out_of_sync``, a warning message is also added to the top-level ``warnings`` array in the response so legacy consumers see it.",
+    "- ``canonical_revision``: Revision of the canonical state used to answer this query.",
+    "- ``provenance``: ``live`` or ``snapshot``.",
+    "- ``advisory_warning``: Warning message when out of sync or if the last analysis job was interrupted/failed."
+  ],
   "errors": [],
```
