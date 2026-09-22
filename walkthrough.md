CPA10K7F1C_SAME_ROOT_HYDRATION_PROOF_REPAIR

STATUS=PASS
FILES_CHANGED=
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)
PRODUCTION_DIFF_CHANGED=NO
SAME_ROOT_BLOCKING_PROOF=PASS; _ObservedRLock was installed for the canonical root and watched thread second-hydrator. While the first FakeEngine hydration was held, attempted=True and acquired=False before release; builds==1 at that point. After release, acquired=True, both threads terminated, errors==[], builds==1, results length==2, and both results were the same engine.
SIX_CONCURRENCY_TESTS=PASS; 6 passed, 1 warning.
TEST_MCP_REGRESSIONS_MODULE=PASS; 89 passed, 1 warning.
POST_EDIT_LIVE_REVISION=1329
MCP_SERVER_RESTART_REQUIRED=YES
FULL_SUITE_RUN=NO

FULL_DIFFS=
```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index d4627f3..cd25568 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -125 +125,5 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    root_key = str(root.resolve())
+    root_key, observed_lock = _install_observed_cache_lock(
+        monkeypatch,
+        root,
+        "second-hydrator",
+    )
@@ -130 +133,0 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    second_get_entered = threading.Event()
@@ -133 +135,0 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    second_thread_id = [None]
@@ -173,9 +174,0 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    real_get_or_init_engine = mcp_runtime.get_or_init_engine
-
-    def wrapped_get_or_init_engine(candidate_root):
-        if threading.get_ident() == second_thread_id[0]:
-            second_get_entered.set()
-        return real_get_or_init_engine(candidate_root)
-
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", wrapped_get_or_init_engine)
-
@@ -193 +185,0 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-        second_thread_id[0] = threading.get_ident()
@@ -195 +187,3 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-            results.append(mcp_runtime.get_or_init_engine(root))
+            results.append(
+                mcp_runtime.get_or_init_engine(root)
+            )
@@ -199 +193,4 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    second = threading.Thread(target=hydrate_second)
+    second = threading.Thread(
+        target=hydrate_second,
+        name="second-hydrator",
+    )
@@ -201 +198,4 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
-    assert second_get_entered.wait(timeout=2)
+    assert observed_lock.attempted.wait(timeout=2)
+    assert observed_lock.acquired.is_set() is False
+    assert len(builds) == 1
+
@@ -207,0 +208 @@ def test_same_root_double_hydration_is_serialized(tmp_path, monkeypatch):
+    assert observed_lock.acquired.is_set() is True

```

