# TASK
P1D1A — exact opt-in indexer worker source capture.

# HEAD_BEFORE
5aedb903d1b9b2196c3286fe9fb40825c240846c; clean source/test tree; new test absent.

# HEAD_AFTER
5aedb903d1b9b2196c3286fe9fb40825c240846c; uncommitted.

# FILES_CHANGED
C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py
C:\Temp\Contextor_Repo\tests\test_indexer_worker_source_capture.py

# ARCHITECTURAL_DEPENDENCIES
CONTRACT_PROVED: Contextor revision 654 resolved _process_single_file as canonical worker, index_repository as intra-module caller, and 255 downstream modules (84 production, 171 tests). read_source_snapshot supplies SourceSnapshot.raw; cache.get and parse_source_snapshot consume that snapshot. index_repository and RepositoryIndex were unchanged.

# T01_T13_RESULTS
DIRECT_EVIDENCE: dedicated pytest command: 13 passed in 3.68s; T01–T13 all passed.

# FOCUSED_NON_REGRESSION
DIRECT_EVIDENCE: tests/test_index_fusion.py tests/test_indexer_profile_evidence.py tests/test_cycle_semantics_selective_source_replay.py tests/test_process_pool_lifecycle.py: 37 passed, 1 third-party AuthlibDeprecationWarning in 29.40s. No full suite.

# EXACT_WORKER_READ_PROVENANCE
CODE_PATH_PROVED: captured bytes are source_snapshot.raw from the worker read. T12 counted one read_source_snapshot call; T02 checked exact bytes and SHA-256.

# CACHE_HIT_SEMANTICS
DIRECT_EVIDENCE: T03 proved warm cache hit with source_parse_called=False and CACHE_SHA256_EQUIVALENT; T04 proved changed bytes and fingerprint are captured on next worker call.

# PROCESS_POOL_IPC_EVIDENCE
DIRECT_EVIDENCE: T10 returned opted-in bytes through managed_reusable_process_pool. The added payload carries no AST object.

# DEFAULT_ZERO_BYTE_TRANSPORT
DIRECT_EVIDENCE: T01 checked cold and warm default results have no source_capture_* keys. Default source_capture_max_bytes=None; existing index_repository calls remain unchanged.

# FAILURE_AND_BUDGET_BEHAVIOR
DIRECT_EVIDENCE: T05 BYTE_LIMIT with no raw bytes; T06 empty source; T07 parse failure, T08 read failure, T13 index failure without raw bytes; T09 optional symbol fact failure retains valid source capture; T11 invalid and >64 MiB limits rejected.

# LIVE_REVISION_BEFORE_AFTER
654 → 654. Contextor after_revision=654: continuity=continuous, resync_required=false, events=[].

# WATCHER_EVENTS
No matching desktop_watcher canonical event observed. No manual update_file called.

# WORKSPACE_SYNC
Contextor post-edit indexer.py: out_of_sync at revision 654. New test symbol resolved, workspace_sync=unverified. LIVE canonical adoption is unverified.

# RUNTIME_ADOPTION_LIMITATION
Tests used fresh Python processes. Existing MCP/Desktop process adoption is UNKNOWN. This worker-origin byte channel does not certify initial FULL index, graph identity, SCC closure, LIVE generation, or one filesystem instant across files.

# RESTART_REQUIREMENTS
No automatic restart. Existing processes may need manual reload/restart before using this worker contract.

# WHITESPACE_CHECK
py_compile passed for both files; git diff --check passed for tracked source; new test has no trailing whitespace and ends with newline. Git only warned about LF-to-CRLF future conversion.

# FULL_DIFFS

## contextor/core/symbol_engine/indexer.py

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 5e86ec5..157963b 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -44,6 +44,7 @@ from contextor.core.reference.index import extract_compact_reference_facts
 from contextor.core.runtime_trace import trace_event
 from contextor.core.source import (
     SourceError,
+    SourceSnapshot,
     parse_source,
     parse_source_snapshot,
     read_source_snapshot,
@@ -330,14 +331,60 @@ def _cache_manager(
     return manager
 
 
+def _worker_source_capture_fields(
+    snapshot: SourceSnapshot,
+    max_bytes: int | None,
+    *,
+    indexed: bool,
+    ast_mode: str,
+) -> dict[str, object]:
+    """Optional payload from the worker's original read.
+
+    No byte copy, filesystem access, or raw transport when
+    capture was not requested.
+    """
+    if max_bytes is None:
+        return {}
+
+    if not indexed:
+        return {
+            "source_capture_status": "INDEX_FAILED",
+        }
+
+    if len(snapshot.raw) > max_bytes:
+        return {
+            "source_capture_status": "BYTE_LIMIT",
+        }
+
+    return {
+        "source_capture_status": "CAPTURED",
+        "source_capture_bytes": snapshot.raw,
+        "source_capture_ast_mode": ast_mode,
+        "source_capture_origin": "INDEXER_WORKER_READ",
+    }
+
+
 def _process_single_file(
     path_str: str,
     root_str: str,
     submitted_monotonic_ns: int | None = None,
     batch_token: str | None = None,
     cache_dir_str: str | None = None,
+    source_capture_max_bytes: int | None = None,
 ) -> dict:
     """Funkcja pomocnicza dla wieloprocesowości."""
+    if (
+        source_capture_max_bytes is not None
+        and (
+            type(source_capture_max_bytes) is not int
+            or not 1 <= source_capture_max_bytes
+            <= 64 * 1024 * 1024
+        )
+    ):
+        raise ValueError(
+            "source_capture_max_bytes out of range"
+        )
+
     path = Path(path_str)
 
     rel = path.relative_to(Path(root_str))
@@ -479,6 +526,14 @@ def _process_single_file(
                 or path.parent == Path(root_str)
                 else None
             ),
+            **(
+                {
+                    "source_capture_status":
+                    "SOURCE_READ_FAILED",
+                }
+                if source_capture_max_bytes is not None
+                else {}
+            ),
             **timing_evidence(),
         }
 
@@ -574,6 +629,12 @@ def _process_single_file(
                     if test_candidate or path.parent == Path(root_str)
                     else None
                 ),
+                **_worker_source_capture_fields(
+                    source_snapshot,
+                    source_capture_max_bytes,
+                    indexed=True,
+                    ast_mode="CACHE_SHA256_EQUIVALENT",
+                ),
                 **timing_evidence(),
             }
 
@@ -598,6 +659,14 @@ def _process_single_file(
                 str(path.parent) if test_candidate or path.parent == Path(root_str)
                 else None
             ),
+            **(
+                {
+                    "source_capture_status":
+                    "SOURCE_PARSE_FAILED",
+                }
+                if source_capture_max_bytes is not None
+                else {}
+            ),
             **timing_evidence(),
         }
 
@@ -908,6 +977,12 @@ def _process_single_file(
             if test_candidate or path.parent == Path(root_str)
             else None
         ),
+        **_worker_source_capture_fields(
+            source_snapshot,
+            source_capture_max_bytes,
+            indexed=(error is None and imports is not None),
+            ast_mode="PARSED_FROM_WORKER_READ",
+        ),
         **timing_evidence(),
     }
 
```

## tests/test_indexer_worker_source_capture.py

```diff
diff --git a/tests/test_indexer_worker_source_capture.py b/tests/test_indexer_worker_source_capture.py
new file mode 100644
index 0000000..f45e07f
--- /dev/null
+++ b/tests/test_indexer_worker_source_capture.py
@@ -0,0 +1,283 @@
+"""P1D1A: source bytes returned by an opted-in indexer worker."""
+
+from __future__ import annotations
+
+import hashlib
+
+import pytest
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    managed_reusable_process_pool,
+    terminate_active_process_pools,
+)
+from contextor.core.paths import repo_cache_dir
+from contextor.core.symbol_engine import indexer
+
+
+def _source(tmp_path, raw=b"import os\nvalue = os.name\n"):
+    root = tmp_path / "repo"
+    root.mkdir()
+    path = root / "sample.py"
+    path.write_bytes(raw)
+    return root, path
+
+
+def _worker(root, path, maximum=None):
+    return indexer._process_single_file(
+        str(path),
+        str(root),
+        source_capture_max_bytes=maximum,
+    )
+
+
+def _assert_capture(result, raw):
+    assert result["error"] is None
+    assert result["source_capture_status"] == "CAPTURED"
+    assert result["source_capture_bytes"] == raw
+    assert type(result["source_capture_bytes"]) is bytes
+    assert result["source_capture_origin"] == (
+        "INDEXER_WORKER_READ"
+    )
+    assert result["source_fingerprint"] == (
+        hashlib.sha256(raw).hexdigest()
+    )
+    assert hashlib.sha256(
+        result["source_capture_bytes"]
+    ).hexdigest() == result["source_fingerprint"]
+
+
+def test_p1d1a_t01_default_result_has_no_capture_payload(
+    tmp_path, isolated_dirs,
+):
+    root, path = _source(tmp_path)
+    cold = _worker(root, path)
+    warm = _worker(root, path)
+
+    for result in (cold, warm):
+        assert result["error"] is None
+        assert not any(
+            key.startswith("source_capture_")
+            for key in result
+        )
+
+
+def test_p1d1a_t02_cold_capture_uses_worker_bytes(
+    tmp_path, isolated_dirs,
+):
+    raw = b"import os\r\nvalue = os.name\r\n"
+    root, path = _source(tmp_path, raw)
+    result = _worker(root, path, 1024)
+
+    _assert_capture(result, raw)
+    assert result["source_parse_called"] is True
+    assert result["source_capture_ast_mode"] == (
+        "PARSED_FROM_WORKER_READ"
+    )
+
+
+def test_p1d1a_t03_warm_capture_labels_cache_equivalence(
+    tmp_path, isolated_dirs,
+):
+    raw = b"import os\nvalue = os.name\n"
+    root, path = _source(tmp_path, raw)
+    first = _worker(root, path)
+    assert first["error"] is None
+
+    warm = _worker(root, path, 1024)
+
+    _assert_capture(warm, raw)
+    assert warm["source_parse_called"] is False
+    assert warm["cache_hit"] is True
+    assert warm["source_capture_ast_mode"] == (
+        "CACHE_SHA256_EQUIVALENT"
+    )
+
+
+def test_p1d1a_t04_source_change_rebinds_capture(
+    tmp_path, isolated_dirs,
+):
+    old = b"import os\nvalue = 1\n"
+    new = b"import os\nvalue = 2\n"
+    root, path = _source(tmp_path, old)
+
+    before = _worker(root, path, 1024)
+    path.write_bytes(new)
+    after = _worker(root, path, 1024)
+
+    _assert_capture(before, old)
+    _assert_capture(after, new)
+    assert before["source_fingerprint"] != (
+        after["source_fingerprint"]
+    )
+
+
+def test_p1d1a_t05_over_budget_never_returns_raw(
+    tmp_path, isolated_dirs,
+):
+    raw = b"import os\nvalue = os.name\n"
+    root, path = _source(tmp_path, raw)
+    result = _worker(root, path, len(raw) - 1)
+
+    assert result["error"] is None
+    assert result["source_capture_status"] == "BYTE_LIMIT"
+    assert "source_capture_bytes" not in result
+    assert "source_capture_ast_mode" not in result
+    assert result["source_fingerprint"] == (
+        hashlib.sha256(raw).hexdigest()
+    )
+
+
+def test_p1d1a_t06_empty_file_is_valid_capture(
+    tmp_path, isolated_dirs,
+):
+    root, path = _source(tmp_path, b"")
+    result = _worker(root, path, 1)
+
+    _assert_capture(result, b"")
+    assert result["imports"] == []
+
+
+def test_p1d1a_t07_parse_error_returns_no_bytes(
+    tmp_path, isolated_dirs,
+):
+    root, path = _source(
+        tmp_path,
+        b"def broken(:\n",
+    )
+    result = _worker(root, path, 1024)
+
+    assert result["error"]
+    assert result["source_capture_status"] == (
+        "SOURCE_PARSE_FAILED"
+    )
+    assert "source_capture_bytes" not in result
+
+
+def test_p1d1a_t08_read_failure_returns_no_bytes(
+    tmp_path, isolated_dirs,
+):
+    root, path = _source(tmp_path)
+    path.unlink()
+
+    result = _worker(root, path, 1024)
+
+    assert result["error"]
+    assert result["source_capture_status"] == (
+        "SOURCE_READ_FAILED"
+    )
+    assert "source_capture_bytes" not in result
+
+
+def test_p1d1a_t09_optional_fact_failure_does_not_forge_source(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    raw = b"import os\nvalue = os.name\n"
+    root, path = _source(tmp_path, raw)
+
+    def fail_symbol_extraction(*args, **kwargs):
+        raise RuntimeError("injected symbol failure")
+
+    monkeypatch.setattr(
+        indexer,
+        "extract_file_symbols",
+        fail_symbol_extraction,
+    )
+
+    result = _worker(root, path, 1024)
+
+    _assert_capture(result, raw)
+    assert result["symbol_facts"]["status"] == "failure"
+
+
+def test_p1d1a_t10_real_process_pool_transports_opted_bytes(
+    tmp_path, isolated_dirs,
+):
+    raw = b"import os\nvalue = os.name\n"
+    root, path = _source(tmp_path, raw)
+
+    try:
+        with managed_reusable_process_pool(
+            "indexer"
+        ) as (executor, _, _):
+            future = executor.submit(
+                indexer._process_single_file,
+                str(path),
+                str(root),
+                None,
+                None,
+                str(repo_cache_dir(root)),
+                1024,
+            )
+            result = future.result(timeout=90)
+
+        _assert_capture(result, raw)
+        assert result["source_capture_ast_mode"] in {
+            "PARSED_FROM_WORKER_READ",
+            "CACHE_SHA256_EQUIVALENT",
+        }
+    finally:
+        terminate_active_process_pools(timeout=1.0)
+
+
+def test_p1d1a_t11_invalid_capture_limits_rejected(
+    tmp_path, isolated_dirs,
+):
+    root, path = _source(tmp_path)
+
+    for maximum in (
+        0,
+        -1,
+        True,
+        False,
+        1.0,
+        64 * 1024 * 1024 + 1,
+    ):
+        with pytest.raises(ValueError):
+            _worker(root, path, maximum)
+
+
+def test_p1d1a_t12_capture_performs_no_second_read(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    raw = b"import os\nvalue = os.name\n"
+    root, path = _source(tmp_path, raw)
+
+    calls = []
+    original = indexer.read_source_snapshot
+
+    def traced(path_arg):
+        calls.append(path_arg)
+        return original(path_arg)
+
+    monkeypatch.setattr(
+        indexer,
+        "read_source_snapshot",
+        traced,
+    )
+
+    result = _worker(root, path, 1024)
+
+    _assert_capture(result, raw)
+    assert len(calls) == 1
+
+
+def test_p1d1a_t13_index_error_cannot_return_capture(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, path = _source(tmp_path)
+
+    monkeypatch.setattr(
+        indexer,
+        "read_imports",
+        lambda *args, **kwargs: (
+            None, "injected import failure"
+        ),
+    )
+
+    result = _worker(root, path, 1024)
+
+    assert result["error"] == "injected import failure"
+    assert result["source_capture_status"] == (
+        "INDEX_FAILED"
+    )
+    assert "source_capture_bytes" not in result
```

# FINAL_VERDICT
PARTIAL: exact patch and targeted test gates pass. LIVE watcher event and workspace_sync verification remain outstanding; stronger canonical source certification is not claimed.