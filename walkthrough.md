# CONTEXTOR_P1D2A_BOUNDED_ORIGINAL_INDEXER_CAPTURE_HANDOFF

## HEAD_BEFORE
DIRECT_EVIDENCE: `78c386611245a475f436f2ca3938390b60f4fc69`. Pre-existing worktree modification was `walkthrough.md` only. Exact source anchors and absence of the new test path were checked before applying the patch.

## HEAD_AFTER
DIRECT_EVIDENCE: `78c386611245a475f436f2ca3938390b60f4fc69`. No commit or Git mutation was made.

## PATCH_APPLICATION
DIRECT_EVIDENCE: Architect-authored patch extracted verbatim from the supplied attachment. `git apply --check -` returned 0; `git apply -` returned 0. The inspected actual diffs below are limited to the two specified production/test paths. No source outside the literal patch was changed.

## FILES_CHANGED
- `contextor/core/symbol_engine/indexer.py`
- `tests/test_indexer_original_capture_handoff.py` (new)
- `walkthrough.md` (this report; excluded from source/test actual diffs)

## ACTUAL_DIFF

### `contextor/core/symbol_engine/indexer.py`
```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 157963b..e3d9488 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -12,6 +12,7 @@ Builds stable module_id against project root.
 
 import ast
 import dataclasses
+import hashlib
 import os
 import re
 import time
@@ -1045,13 +1046,116 @@ class RepositoryIndex:
         dataclasses.field(default_factory=dict)
     )
 
+    # Optional original worker-read evidence. Not a publication receipt,
+    # generation binding, or cross-file atomic source snapshot.
+    original_worker_source_snapshots: dict[str, SourceSnapshot] = (
+        dataclasses.field(default_factory=dict)
+    )
+    original_worker_ast_modes: dict[str, str] = (
+        dataclasses.field(default_factory=dict)
+    )
+    original_worker_capture_status: str = "NOT_REQUESTED"
+    original_worker_capture_reason: str | None = None
+
 
 def index_repository(
-    root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
+    root: str,
+    excludes: list[str] = None,
+    extra_ignored_dirs: set = None,
+    progress_callback=None,
+    *,
+    source_capture_module_ids: frozenset[str] | None = None,
 ) -> RepositoryIndex:
+    """Buduje indeks modułów projektu wraz z listą pominiętych plików.
+
+    Optional evidence is not a coherent cross-file snapshot and does
+    not authorize canonical publication. Default indexing transports no
+    raw source bytes beyond the worker.
     """
-    Buduje indeks modułów projektu wraz z listą pominiętych plików.
-    """
+    if source_capture_module_ids is None:
+        selected_captures = frozenset()
+    elif (
+        type(source_capture_module_ids) is not frozenset
+        or any(
+            type(name) is not str or not name
+            for name in source_capture_module_ids
+        )
+        or len(source_capture_module_ids) > 16
+    ):
+        raise ValueError("source_capture_module_ids must be <=16 module names")
+    else:
+        selected_captures = source_capture_module_ids
+
+    # At most 16 selected results of 2 MiB each (32 MiB raw payload).
+    # This does not bound unrelated indexing memory overhead.
+    capture_per_source_max = 2 * 1024 * 1024
+    captures: dict[str, SourceSnapshot] = {}
+    capture_modes: dict[str, str] = {}
+    capture_errors: dict[str, str] = {}
+
+    def capture_limit(path: Path) -> int | None:
+        module_id = ".".join(path.relative_to(root_path).with_suffix("").parts)
+        return capture_per_source_max if module_id in selected_captures else None
+
+    def record_capture(result: dict, path: Path) -> None:
+        if not selected_captures:
+            return
+        module_id = ".".join(path.relative_to(root_path).with_suffix("").parts)
+        if module_id not in selected_captures:
+            return
+        if (
+            result.get("module_id") != module_id
+            or result.get("path") != str(path.relative_to(root_path))
+            or result.get("absolute_path") != str(path.resolve())
+        ):
+            capture_errors[module_id] = "WORKER_IDENTITY_MISMATCH"
+            return
+        if (
+            result.get("error") is not None
+            or result.get("source_capture_status") != "CAPTURED"
+        ):
+            status = result.get("source_capture_status")
+            capture_errors[module_id] = (
+                status if type(status) is str and status else "INDEX_FAILED"
+            )
+            return
+        raw = result.get("source_capture_bytes")
+        fingerprint = result.get("source_fingerprint")
+        mode = result.get("source_capture_ast_mode")
+        if (
+            type(raw) is not bytes
+            or len(raw) > capture_per_source_max
+            or type(fingerprint) is not str
+            or hashlib.sha256(raw).hexdigest() != fingerprint
+            or result.get("source_capture_origin") != "INDEXER_WORKER_READ"
+            or mode not in (
+                "PARSED_FROM_WORKER_READ",
+                "CACHE_SHA256_EQUIVALENT",
+            )
+        ):
+            capture_errors[module_id] = "INVALID_WORKER_CAPTURE"
+            return
+        captures[module_id] = SourceSnapshot(raw=raw, source_fingerprint=fingerprint)
+        capture_modes[module_id] = mode
+
+    def capture_result_fields() -> dict[str, object]:
+        if not selected_captures:
+            return {}
+        missing = selected_captures - captures.keys()
+        if missing or capture_errors:
+            # No partially successful source cohort may escape this index.
+            return {
+                "original_worker_capture_status": "UNAVAILABLE",
+                "original_worker_capture_reason": (
+                    capture_errors[sorted(capture_errors)[0]]
+                    if capture_errors else "SELECTED_MODULE_NOT_INDEXED"
+                ),
+            }
+        return {
+            "original_worker_source_snapshots": dict(sorted(captures.items())),
+            "original_worker_ast_modes": dict(sorted(capture_modes.items())),
+            "original_worker_capture_status": "ALL_SELECTED_CAPTURED_NON_ATOMIC",
+        }
 
     index_started = time.monotonic()
     root_path = Path(root).resolve()
@@ -1828,8 +1932,13 @@ def index_repository(
             res = _process_single_file(
                 str(path),
                 str(root_path),
+                **(
+                    {"source_capture_max_bytes": capture_limit(path)}
+                    if selected_captures else {}
+                ),
             )
             record_file_task_evidence(res)
+            record_capture(res, path)
             if res["error"]:
                 line_number, column_number = _syntax_error_location(res["error"])
                 skipped.append(
@@ -1881,6 +1990,7 @@ def index_repository(
                     source_fingerprints_by_module.items()
                 )
             ),
+            **capture_result_fields(),
         )
 
     pool_scope_started = time.monotonic()
@@ -1921,6 +2031,10 @@ def index_repository(
                 time.monotonic_ns(),
                 worker_batch_token,
                 resolved_cache_dir,
+                *(
+                    (capture_limit(p),)
+                    if selected_captures else ()
+                ),
             ): p
             for p in files_to_process
         }
@@ -1971,6 +2085,7 @@ def index_repository(
                     parent_result_received_monotonic_ns
                 ),
             )
+            record_capture(res, futures[future])
 
             if res["error"]:
                 line_number, column_number = (
@@ -2124,6 +2239,7 @@ def index_repository(
                 source_fingerprints_by_module.items()
             )
         ),
+        **capture_result_fields(),
     )
```

### `tests/test_indexer_original_capture_handoff.py`
```diff
diff --git a/tests/test_indexer_original_capture_handoff.py b/tests/test_indexer_original_capture_handoff.py
new file mode 100644
index 0000000..24e28cd
--- /dev/null
+++ b/tests/test_indexer_original_capture_handoff.py
@@ -0,0 +1,140 @@
+"""P1D2A: bounded original-worker capture handoff, not publication."""
+
+from __future__ import annotations
+
+import hashlib
+
+import pytest
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
+from contextor.core.symbol_engine import indexer
+
+
+@pytest.fixture(autouse=True)
+def _inline_by_default(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(b"import os\nvalue = os.name\n")
+    (root / "b.py").write_bytes(b"other = 2\n")
+    return root
+
+
+def _index(root, *selected):
+    return indexer.index_repository(
+        str(root), source_capture_module_ids=frozenset(selected),
+    )
+
+
+def test_p1d2a_t01_default_remains_capture_free(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    result = indexer.index_repository(str(root))
+    assert result.original_worker_capture_status == "NOT_REQUESTED"
+    assert result.original_worker_source_snapshots == {}
+    assert result.original_worker_ast_modes == {}
+    assert result.original_worker_capture_reason is None
+
+
+def test_p1d2a_t02_only_selected_original_worker_bytes(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    result = _index(root, "a")
+    assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    assert result.original_worker_capture_reason is None
+    assert set(result.original_worker_source_snapshots) == {"a"}
+    assert set(result.original_worker_ast_modes) == {"a"}
+    raw = (root / "a.py").read_bytes()
+    snap = result.original_worker_source_snapshots["a"]
+    assert snap.raw == raw
+    assert snap.source_fingerprint == hashlib.sha256(raw).hexdigest()
+    assert snap.source_fingerprint == result.source_fingerprints_by_module["a"]
+    assert result.original_worker_ast_modes["a"] in {
+        "PARSED_FROM_WORKER_READ", "CACHE_SHA256_EQUIVALENT",
+    }
+    assert "b" in result.modules
+
+
+def test_p1d2a_t03_warm_cache_keeps_equivalent_mode(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    indexer.index_repository(str(root))
+    result = _index(root, "a")
+    assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    assert result.original_worker_ast_modes["a"] == "CACHE_SHA256_EQUIVALENT"
+
+
+def test_p1d2a_t04_missing_selected_module_no_partial_data(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    result = _index(root, "a", "missing")
+    assert result.original_worker_capture_status == "UNAVAILABLE"
+    assert result.original_worker_capture_reason == "SELECTED_MODULE_NOT_INDEXED"
+    assert result.original_worker_source_snapshots == {}
+    assert result.original_worker_ast_modes == {}
+
+
+def test_p1d2a_t05_byte_limit_fails_closed(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    (root / "big.py").write_bytes(b"#" + b"a" * (2 * 1024 * 1024) + b"\n")
+    result = _index(root, "a", "big")
+    assert result.original_worker_capture_status == "UNAVAILABLE"
+    assert result.original_worker_capture_reason == "BYTE_LIMIT"
+    assert result.original_worker_source_snapshots == {}
+    assert result.original_worker_ast_modes == {}
+
+
+def test_p1d2a_t06_invalid_selector_rejected(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    invalid = [
+        "a",
+        frozenset({""}),
+        frozenset({"a", 7}),
+        frozenset(f"x{i}" for i in range(17)),
+    ]
+    for selected in invalid:
+        with pytest.raises(ValueError):
+            indexer.index_repository(str(root), source_capture_module_ids=selected)
+
+
+def test_p1d2a_t07_forged_worker_capture_rejected(tmp_path, isolated_dirs, monkeypatch):
+    root = _repo(tmp_path)
+    original = indexer._process_single_file
+
+    def forged(*args, **kwargs):
+        result = original(*args, **kwargs)
+        if result["module_id"] == "a":
+            result["source_capture_bytes"] = b"forged"
+        return result
+
+    monkeypatch.setattr(indexer, "_process_single_file", forged)
+    result = _index(root, "a")
+    assert result.original_worker_capture_status == "UNAVAILABLE"
+    assert result.original_worker_capture_reason == "INVALID_WORKER_CAPTURE"
+    assert result.original_worker_source_snapshots == {}
+
+
+def test_p1d2a_t08_selected_parse_failure_no_partial_data(tmp_path, isolated_dirs):
+    root = _repo(tmp_path)
+    (root / "broken.py").write_bytes(b"def oops(:\n    pass\n")
+    result = _index(root, "a", "broken")
+    assert result.original_worker_capture_status == "UNAVAILABLE"
+    assert result.original_worker_capture_reason == "SOURCE_PARSE_FAILED"
+    assert result.original_worker_source_snapshots == {}
+
+
+def test_p1d2a_t09_real_pool_capture(tmp_path, isolated_dirs, monkeypatch):
+    root = _repo(tmp_path)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    terminate_active_process_pools(timeout=1.0)
+    try:
+        result = _index(root, "a")
+        assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+        raw = (root / "a.py").read_bytes()
+        assert result.original_worker_source_snapshots["a"].raw == raw
+        assert result.original_worker_source_snapshots["a"].source_fingerprint == (
+            result.source_fingerprints_by_module["a"]
+        )
+    finally:
+        terminate_active_process_pools(timeout=1.0)
```

## NEW_TESTS
DIRECT_EVIDENCE: 9 P1D2A tests in the new file. The required combined focused pytest invocation passed all 52 tests in 16.66 s. P1D2A coverage includes default no-capture, selected bytes, warm cache mode, missing selection, 2 MiB limit, selector validation, forged bytes, parse failure and real process-pool transport. No failures.

## FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_indexer_original_capture_handoff.py tests/test_indexer_worker_source_capture.py tests/test_cycle_semantics_selective_worker_capture.py tests/test_index_fusion.py` returned 0: **52 passed in 16.66 s**. File counts from test function definitions: new P1D2A 9, P1D1A 13, P1D1B 17, index fusion 13; total 52. No additional test was run. These are isolated test fixtures, not FULL analysis of the user repository.

## PY_COMPILE
DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py tests/test_indexer_original_capture_handoff.py` returned 0 for both files.

## WHITESPACE
DIRECT_EVIDENCE: `git diff --check -- contextor/core/symbol_engine/indexer.py` returned 0. `git diff --no-index --check -- /dev/null tests/test_indexer_original_capture_handoff.py` emitted no whitespace diagnostics (exit 1 is the expected new-file difference). Final repo-wide `git diff --check` returned 1 only for `walkthrough.md:48,150,191`: these are single-space context lines in the mandatory verbatim ACTUAL_DIFF code block. No production/test whitespace diagnostic was reported. The pre-existing Stage 1 report was overwritten.

## CANONICAL_LIVE_READS
DIRECT_EVIDENCE: Read-only `get_live_events(after_revision=670)` returned continuous events at revision 671 (`desktop_watcher`, `UPDATED`, `contextor/core/symbol_engine/indexer.py`) and 672 (`desktop_watcher`, `UPDATED`, `tests/test_indexer_original_capture_handoff.py`), with `resync_required=false`. After both events, Contextor `get_symbol_implementation(mode=preview)` resolved `index_repository` at lines 1061-2243 and P1D2A T01 at lines 34-40, each at canonical revision 672 with `workspace_sync=verified`. The returned cycle_semantics family remained stale; freshness of that unrelated family was not required. Earlier search at revision 671 had not yet indexed the new test; the revision-672 read resolved it.

## SOURCE_CAPTURE_AUTHORITY_LIMITS
CODE_PATH_PROVED: Capture is opt-in via `source_capture_module_ids`, default is capture-free. At most 16 selected module IDs and 2 MiB per selected worker payload yield a 32 MiB selected-raw-payload bound per indexing call; this does not bound total process peak memory. Failure or incomplete selection returns `UNAVAILABLE` without partial snapshots. Successful handoff is labeled `ALL_SELECTED_CAPTURED_NON_ATOMIC`. Warm cache mode is explicitly `CACHE_SHA256_EQUIVALENT`. No cross-file atomic transaction, canonical receipt, FULL end-to-end generation binding, active LIVE adoption or SAFE claim follows from this patch. The opt-in was not wired into facade/FULL or canonical publication.

## UNVERIFIED_RUNTIME_ADOPTION
UNKNOWN: Contextor watcher indexing and verified disk source demonstrate canonical indexing of the changed files, not adoption of the edited Python implementation by an already running process. No restart, reload, active-code introspection or LIVE behavior probe was performed.

## FINAL_VERDICT
CONTRACT_PROVED by the 52 passing focused tests and CODE_PATH_PROVED by the exact patch: bounded optional original-worker capture handoff works in isolated inline and process-pool test paths. DIRECT_EVIDENCE confirms canonical watcher indexing at revision 672. Runtime adoption and future publication authority remain UNKNOWN. STOP after P1D2A exact patch and tests.
