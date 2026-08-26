# CONTEXTOR — REMAINING MCP ERGONOMICS — E2 STATUS / LIVE EVENTS / UPDATE_FILE
**Date:** 2026-08-26  
**Mode:** IMPLEMENTATION (DOCUMENTATION & CONTRACT TESTS ONLY)  
**Target Docs:** `contextor/mcp/docs/update_file.json`, `contextor/mcp/docs/get_analysis_status.json`, `contextor/mcp/docs/get_live_events.json`  
**Test Target:** `tests/mcp/tools/test_status_live_update_contracts.py`  
**Status:** IMPLEMENTED, VALIDATED & VERIFIED (PASS)

---

## 1. CEL I ZAKRES ZMIAN

1. **Brak zmian w kodzie produkcyjnym (`PRODUCTION_FILES_CHANGED=NONE`):**
   - Wszystkie sygnatury runtime pozostają w 100% zachowane:
     - `get_analysis_status(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str`
     - `get_live_events(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str`
     - `update_file(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str`
2. **Dokumentacja Publiczna MCP:**
   - W `update_file.json`: dodano kompletny opis parametrów (`repo_path`, `file_path`, `max_items`, `compact`, `fields`) oraz opis workflow LIVE (desktop watcher path vs manual incremental publication path, semantykę `semantic_diff` oraz sygnał `runtime_restart_required`).
   - W `get_analysis_status.json`: jawnie wyeksponowano `repo_path` (required) oraz defaulty parametrów.
   - W `get_live_events.json`: jawnie wyeksponowano `repo_path` (required) oraz semantykę bufora zdarzeń.
3. **Nowe Testy Kontraktowe:**
   - Utworzono `tests/mcp/tools/test_status_live_update_contracts.py` (9 testów weryfikujących sygnatury oraz kompletność dokumentacji parametrów i zachowań).

---

## 2. WERYFIKACJA TESTAMI (TEST EXECUTION EVIDENCE)

- Walidacja składni JSON (`python -m json.tool` dla 3 plików docs): **PASS**
- `tests/mcp/tools/test_status_live_update_contracts.py`: **9 passed**
- `tests/test_mcp_documentation.py` & `tests/test_mcp_split_s2c.py`: **46 passed** (łącznie 55 passed)

---

## 3. DOKŁADNE DIFFY DOKUMENTACJI I TESTÓW (COMPLETE UNIFIED DIFFS)

### 1. `contextor/mcp/docs/update_file.json`
```diff
--- a/contextor/mcp/docs/update_file.json
+++ b/contextor/mcp/docs/update_file.json
@@ -4,8 +4,19 @@
   "purpose": [
     "[OPTIMIZED] Incremental architectural update for a modified file.\nUpdates the canonical state and graph structure in real-time. When the\nshared LIVE service is available, the update executes in its owner process\nso desktop and MCP observe the same revision; otherwise the hydrated local\nengine remains a fallback. Requires a completed project analysis."
   ],
-  "parameters": [],
-  "behavior": [],
+  "parameters": [
+    "repo_path (string, required): canonical repository root.",
+    "file_path (string, required): repository-relative or accepted absolute target file path processed by the existing incremental/LIVE update path.",
+    "max_items (integer or null, default 30): maximum number of bounded semantic-diff items emitted where applicable; null preserves existing unbounded semantics.",
+    "compact (boolean, default true): controls existing compact semantic-diff/result shaping.",
+    "fields (array of strings or null, default null): optional existing response projection; null returns the normal response shape."
+  ],
+  "behavior": [
+    "1. When the desktop app is running, its file watcher owns the update workflow. Do not call update_file directly; instead, poll get_live_events from the previous revision and confirm the corresponding desktop_watcher event.",
+    "2. When the desktop app / shared LIVE watcher is not running, update_file serves as the manual incremental publication path following a file edit.",
+    "3. Incremental analysis updates the in-memory canonical state and emits semantic_diff for added/removed symbols, signature changes, and AST body fingerprints (bodies_changed). Semantic-diff describes architectural delta and does not replace line-level code diffs.",
+    "4. If the update modifies running MCP server implementation files and signals runtime_restart_required: true, the MCP server process requires a manual restart before runtime certification."
+  ],
   "freshness": [],
   "errors": [
     "Semantic-diff and affected-modules collections always expose ``total`` and\n``truncated``. The default compact response omits ``items``; set\n``compact=False`` for bounded symbol/signature/affected-module evidence.\n``max_items`` is the per-collection limit; pass ``None`` to return all\nrequested evidence without truncation. ``fields`` projects top-level\nresponse keys after compact shaping. Stable fields include ``status``,\n``file_path``, graph/metrics state fields, ``affected_modules`` (containing\nthe module-level reverse blast radius when ``blast_radius_state == \"fresh\"``),\n``live_state_persisted``, ``semantic_diff`` and\n``runtime_restart_required``; ``delta`` and runtime warning fields are\nconditional. Invalid projections return the current allowlist."
```

### 2. `contextor/mcp/docs/get_analysis_status.json`
```diff
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -5,9 +5,10 @@
     "Return durable status for a non-blocking MCP analysis job."
   ],
   "parameters": [
-    "``job_id`` (string or null, default ``null``): specific 32-character job identifier or omit to inspect the latest job.",
-    "``max_skipped_files`` (integer or null, default ``10``): maximum skipped file entries in analysis_coverage; pass ``null`` for unlimited.",
-    "``allow_large_output`` (boolean, default ``false``): override to approve emission of outputs exceeding the 15 KiB warning threshold."
+    "repo_path (string, required): canonical repository root.",
+    "job_id (string or null, optional, default null): specific 32-character job identifier or omit to inspect the latest job.",
+    "max_skipped_files (integer or null, optional, default 10): maximum skipped file entries in analysis_coverage; pass null for unlimited.",
+    "allow_large_output (boolean, optional, default false): override to approve emission of outputs exceeding the 15 KiB warning threshold."
   ],
   "behavior": [
     "Returns durable status for the specified or latest analysis job without any cardinality hard limit.\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nOutput > 15 KiB with ``allow_large_output=false`` acts as an agent-controlled context\nsafety preflight and returns ``status: 'confirmation_required'`` with exact current-snapshot\npredicted UTF-8 byte size and retry instructions.\nPassing ``allow_large_output=true`` returns the complete lossless status response.\nFor running jobs, note that status and progress may advance between preflight and retry."
```

### 3. `contextor/mcp/docs/get_live_events.json`
```diff
--- a/contextor/mcp/docs/get_live_events.json
+++ b/contextor/mcp/docs/get_live_events.json
@@ -5,8 +5,9 @@
     "Return revisioned desktop/MCP LIVE events since a known revision."
   ],
   "parameters": [
-    "``after_revision`` (integer or null, default ``null``): filter events strictly newer than this revision integer; omit for initial/latest polling.",
-    "``limit`` (integer or null, default ``20``): maximum retained events to return; pass ``null`` for all retained events."
+    "repo_path (string, required): canonical repository root.",
+    "after_revision (integer or null, optional, default null): filter events strictly newer than this revision integer; omit for initial/latest polling.",
+    "limit (integer or null, optional, default 20): maximum retained events to return; pass null for all retained events."
   ],
   "behavior": [
     "MCP cannot push unsolicited messages into an idle model; this bounded,\nrevisioned feed is the reliable pull mechanism for continuous LIVE state.\nEvents are an ephemeral in-RAM notification feed (retaining the most recent 100 events),\nnot a full history or append-only source of truth. The canonical LIVE state is authoritative.\nThe response exposes explicit continuity metadata: ``latest_revision``,\n``earliest_retained_revision`` (or ``null`` if buffer empty), ``continuity``\n(``'not_requested'``, ``'continuous'``, or ``'gap'``), ``resync_required`` (boolean),\nand ``resync_reason`` (``'event_retention_gap'``, ``'revision_discontinuity'``, or ``null``).\nWhen ``resync_required=true``, the caller cursor lost continuity with the retained event window;\nthe caller must perform a canonical state resync (e.g. query_canonical_projection or\nget_project_architecture) rather than assuming returned events represent a complete sequential delta.\n``limit=None`` returns all retained matching events (up to 100), not the full history.\n``truncated`` indicates truncation solely due to the requested ``limit``, not retention loss."
```

### 4. `tests/mcp/tools/test_status_live_update_contracts.py` (NEW FILE)
```python
import inspect
import json
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def test_status_live_update_contracts__get_analysis_status_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_analysis_status"].fn))
    assert sig == "(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str"


def test_status_live_update_contracts__get_live_events_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_live_events"].fn))
    assert sig == "(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str"


def test_status_live_update_contracts__update_file_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["update_file"].fn))
    assert sig == "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str"


def test_status_live_update_contracts__get_analysis_status_docs_complete():
    doc = _load_doc("get_analysis_status")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "job_id (string or null, optional, default null)" in params_text
    assert "max_skipped_files (integer or null, optional, default 10)" in params_text
    assert "allow_large_output (boolean, optional, default false)" in params_text


def test_status_live_update_contracts__get_live_events_docs_complete():
    doc = _load_doc("get_live_events")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "after_revision (integer or null, optional, default null)" in params_text
    assert "limit (integer or null, optional, default 20)" in params_text


def test_status_live_update_contracts__update_file_docs_complete():
    doc = _load_doc("update_file")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "file_path (string, required)" in params_text
    assert "max_items (integer or null, default 30)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text


def test_status_live_update_contracts__update_file_docs_describe_desktop_watcher_path():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "desktop_watcher" in combined
    assert "get_live_events" in combined


def test_status_live_update_contracts__update_file_docs_describe_manual_incremental_path():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "semantic_diff" in combined
    assert "bodies_changed" in combined


def test_status_live_update_contracts__update_file_docs_describe_runtime_restart_signal():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", [] + doc.get("errors", [])))
    assert "runtime_restart_required" in combined
```

---

## 4. STATUS OPERACYJNY

```text
PRODUCTION_FILES_CHANGED=NONE

FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\mcp\docs\update_file.json
- C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json
- C:\Temp\Contextor_Repo\contextor\mcp\docs\get_live_events.json
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_status_live_update_contracts.py

TESTS:
- tests/mcp/tools/test_status_live_update_contracts.py: 9 passed
- tests/test_mcp_documentation.py & tests/test_mcp_split_s2c.py: 46 passed

GET_ANALYSIS_STATUS_ERGONOMICS=PASS
GET_LIVE_EVENTS_ERGONOMICS=PASS
UPDATE_FILE_ERGONOMICS=PASS

MCP_RESTART_REQUIRED=NO
LIVE_RESTART_REQUIRED=NO

VERDICT=PASS
```
