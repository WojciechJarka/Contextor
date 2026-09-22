CPA10K7F1B_DETERMINISTIC_CONCURRENCY_TEST_REPAIR

STATUS=PASS
HEAD_BEFORE=9ccf183818878ceb2a8ce76ec5c7202a610a5963
HEAD_AFTER=9ccf183818878ceb2a8ce76ec5c7202a610a5963

FILES_CHANGED=
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)

PRODUCTION_DIFF_CHANGED=NO
DETERMINISTIC_BLOCKING_PROOF=PASS; _ObservedRLock marks attempted immediately before acquire and acquired immediately after acquire. The same-root diagnostics reader and update-file probe were both observed attempting while the owning transaction held the repository lock, with acquired=false before release and acquired=true after release. No timed negative wait remains.
UPDATE_FILE_COHERENT_PUBLICATION_PROOF=PASS; the second fake get_or_init_engine publishes new_engine and revision 22 before waiting; the probe remains blocked, then the update completes with UPDATED, live_state_persisted=true, the new engine, and revision 22.
FILE_EDIT_CONTEXT_ORDERING_PROOF=PASS; context_thread starts first and captures engine_one/revision 41, mutator starts only after snapshot_entered, waits at the observed lock, publishes engine_two/revision 42 after release, and the final response still reports captured revision 41.
NEW_SIX_TESTS=PASS; 6 passed, 1 warning.
TEST_MCP_REGRESSIONS_MODULE=PASS; 89 passed, 1 warning.
POST_EDIT_LIVE_REVISION=1328
POST_EDIT_CONTEXTOR=PASS; watcher confirmed revision 1327 UPDATED for tests/test_mcp_regressions.py, revision 1328 UNCHANGED afterward, with syntax_errors=0, name_collisions=0, cycles=0, and attention_required=false. Production symbols remained resolved and workspace_sync=verified at revision 1328.
MCP_SERVER_RESTART_REQUIRED=YES
FULL_SUITE_RUN=NO

EVIDENCE_DISCIPLINE=
- DIRECT_EVIDENCE: exact observed-lock events, pytest results, git status/diff checks, and Contextor LIVE revisions 1327-1328.
- CODE_PATH_PROVED: only the test harness changed; production files have no worktree diff.
- CONTRACT_PROVED: exact helper semantics, thread names, ordering, positive release sequencing, and final safety joins were applied.
- UNKNOWN: MCP server remains unrestarted as required; no runtime restart certification was attempted.

FULL_DIFFS=
```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 5f1e5ec..d4627f3 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -79,0 +80,42 @@ def _patch_empty_registries(monkeypatch):
+class _ObservedRLock:
+    def __init__(self, watched_thread_name: str):
+        self._lock = threading.RLock()
+        self._watched_thread_name = watched_thread_name
+        self.attempted = threading.Event()
+        self.acquired = threading.Event()
+
+    def __enter__(self):
+        watched = (
+            threading.current_thread().name
+            == self._watched_thread_name
+        )
+        if watched:
+            self.attempted.set()
+
+        self._lock.acquire()
+
+        if watched:
+            self.acquired.set()
+
+        return self
+
+    def __exit__(self, exc_type, exc, tb):
+        self._lock.release()
+        return False
+
+
+def _install_observed_cache_lock(
+    monkeypatch,
+    root: Path,
+    watched_thread_name: str,
+):
+    root_key = mcp_runtime._engine_cache_key(root)
+    lock = _ObservedRLock(watched_thread_name)
+    monkeypatch.setitem(
+        mcp_runtime._engine_cache_locks,
+        root_key,
+        lock,
+    )
+    return root_key, lock
+
+
@@ -208 +250,5 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-    root_key = str(root.resolve())
+    root_key, observed_lock = _install_observed_cache_lock(
+        monkeypatch,
+        root,
+        "same-root-reader",
+    )
@@ -212 +257,0 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-    reader_started = threading.Event()
@@ -231 +275,0 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-        reader_started.set()
@@ -257 +301,5 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-    reader_thread = threading.Thread(target=read_summary, args=(root,))
+    reader_thread = threading.Thread(
+        target=read_summary,
+        args=(root,),
+        name="same-root-reader",
+    )
@@ -261,2 +309,3 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-    assert reader_started.wait(timeout=2)
-    assert not reader_done.wait(timeout=0.1)
+    assert observed_lock.attempted.wait(timeout=2)
+    assert observed_lock.acquired.is_set() is False
+    assert reader_done.is_set() is False
@@ -269 +318,2 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
-    assert analysis_errors == []
+    assert observed_lock.acquired.is_set() is True
+    assert reader_done.is_set() is True
@@ -270,0 +321 @@ def test_analysis_refresh_transaction_excludes_same_root_reader(tmp_path, monkey
+    assert analysis_errors == []
@@ -329 +380,5 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    root_key = str(root.resolve())
+    root_key, observed_lock = _install_observed_cache_lock(
+        monkeypatch,
+        root,
+        "same-root-probe",
+    )
@@ -348,3 +402,0 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    probe_started = threading.Event()
-    probe_entered = threading.Event()
-    update_done = threading.Event()
@@ -362,0 +415,2 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
+        mcp_runtime._live_engines[root_key] = new_engine
+        mcp_runtime._live_engine_revisions[root_key] = 22
@@ -380 +433,0 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-        update_done.set()
@@ -383 +435,0 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-        probe_started.set()
@@ -385 +437 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-            probe_entered.set()
+            pass
@@ -388 +440,4 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    probe_thread = threading.Thread(target=probe_transaction)
+    probe_thread = threading.Thread(
+        target=probe_transaction,
+        name="same-root-probe",
+    )
@@ -392,2 +447,2 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    assert probe_started.wait(timeout=2)
-    assert not probe_entered.wait(timeout=0.1)
+    assert observed_lock.attempted.wait(timeout=2)
+    assert observed_lock.acquired.is_set() is False
@@ -395,2 +449,0 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    assert update_done.wait(timeout=2)
-    assert probe_entered.wait(timeout=2)
@@ -401,0 +455 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
+    assert observed_lock.acquired.is_set() is True
@@ -404 +458,2 @@ def test_update_file_refresh_uses_same_root_transaction(tmp_path, monkeypatch):
-    assert mcp_runtime._live_engine_revisions[root_key] == 21
+    assert mcp_runtime._live_engines[root_key] is new_engine
+    assert mcp_runtime._live_engine_revisions[root_key] == 22
@@ -414 +469,5 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    root_key = str(root.resolve())
+    root_key, observed_lock = _install_observed_cache_lock(
+        monkeypatch,
+        root,
+        "post-snapshot-mutator",
+    )
@@ -433 +492 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    mutation_entered = threading.Event()
+    mutation_done = threading.Event()
@@ -448 +507 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-            mutation_entered.set()
+        mutation_done.set()
@@ -469,3 +527,0 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    probe_thread = threading.Thread(target=mutate_after_snapshot)
-    probe_thread.start()
-
@@ -484 +540,8 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    context_thread = threading.Thread(target=read_context)
+    context_thread = threading.Thread(
+        target=read_context,
+        name="snapshot-reader",
+    )
+    mutation_thread = threading.Thread(
+        target=mutate_after_snapshot,
+        name="post-snapshot-mutator",
+    )
@@ -486,0 +550,3 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
+    mutation_thread.start()
+    assert observed_lock.attempted.wait(timeout=2)
+    assert observed_lock.acquired.is_set() is False
@@ -489 +555,4 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    assert mutation_entered.wait(timeout=2)
+    assert mutation_done.wait(timeout=2)
+    assert observed_lock.acquired.is_set() is True
+    assert mcp_runtime._live_engines[root_key] is engine_two
+    assert mcp_runtime._live_engine_revisions[root_key] == 42
@@ -492 +561 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    probe_thread.join(timeout=2)
+    mutation_thread.join(timeout=2)
@@ -495 +564 @@ def test_file_edit_context_binds_engine_and_revision_atomically(tmp_path, monkey
-    assert not probe_thread.is_alive()
+    assert not mutation_thread.is_alive()

```

