# CPA10M8C1H_HTTP_HEADER_HELPER_TIMEOUT_BOUND

STATUS=PASS

FILES_CHANGED=
C:\Temp\Contextor_Repo\contextor\mcp_backend_http_headers.py
C:\Temp\Contextor_Repo\tests\test_mcp_backend_http_headers.py

DIRECT_EVIDENCE:
- Pre-edit Contextor canonical LIVE revision=1418; workspace_sync=verified for the helper module and its test module.
- Contextor confirmed build_backend_http_headers currently calls start_backend(), and its direct caller is main(); the helper's direct static consumer is tests.test_mcp_backend_http_headers.
- Contextor confirmed start_backend signature: def start_backend(*, timeout: float=20.0, probe_timeout: float=2.0) -> BackendStatus. Both requested keyword arguments are supported.
- Contextor blast radius for start_backend includes contextor.mcp_backend_cli, contextor.mcp_backend_http_headers, and tests.test_mcp_backend_control; no lifecycle implementation was changed.
- Exact pre-edit anchors each occurred once. Whole-file comparison confirmed only the requested literal replacements.

IMPLEMENTATION:
- build_backend_http_headers now calls start_backend(timeout=8.0, probe_timeout=1.0).
- The ready-backend fake records both keyword values; the assertions and two lambdas were changed exactly as specified.
- No helper, retry, sleep, process management, lifecycle, secret storage, JSON, stderr, header-format, or configuration behavior was added or changed.

START_BACKEND_TIMEOUT=8.0
START_BACKEND_PROBE_TIMEOUT=1.0
PY_COMPILE=PASS
TARGETED_TESTS=PASS (32 passed, 1 skipped)
TARGETED_TEST_WARNING=AuthlibDeprecationWarning from installed FastMCP dependency
FULL_SUITE_RUN=NO

REAL_BACKEND_STARTED=NO
CODEX_CONFIG_CHANGED=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
PROCESS_TERMINATION_PERFORMED=NO

LIVE_PRE_EDIT_REVISION=1418
LIVE_POST_EDIT_REVISION=1421
LIVE_HELPER_SYNC=verified
LIVE_PUBLICATION=desktop_watcher UPDATED for production helper and test file
POST_EDIT_DIAGNOSTICS=syntax_errors:0; name_collisions:0; cycles:0; freshness:fresh
POST_EDIT_CONTEXTOR_CONSUMER=tests.test_mcp_backend_http_headers

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_RUNTIME_RESTART_REQUIRED=NO
CODEX_RESTART_REQUIRED=NO

FULL_DIFFS:

```diff
diff --git a/contextor/mcp_backend_http_headers.py b/contextor/mcp_backend_http_headers.py
--- a/contextor/mcp_backend_http_headers.py
+++ b/contextor/mcp_backend_http_headers.py
@@ -30,7 +30,10 @@
 def build_backend_http_headers() -> dict[str, str]:
     """Start/reuse the backend and return its bearer Authorization header."""
 
-    status = start_backend()
+    status = start_backend(
+        timeout=8.0,
+        probe_timeout=1.0,
+    )
 
     if not status.ready:
         raise BackendHttpHeadersError(
```

```diff
diff --git a/tests/test_mcp_backend_http_headers.py b/tests/test_mcp_backend_http_headers.py
--- a/tests/test_mcp_backend_http_headers.py
+++ b/tests/test_mcp_backend_http_headers.py
@@ -13,8 +13,17 @@
 ) -> None:
     calls = []
 
-    def fake_start_backend():
-        calls.append("start")
+    def fake_start_backend(
+        *,
+        timeout,
+        probe_timeout,
+    ):
+        calls.append(
+            (
+                timeout,
+                probe_timeout,
+            )
+        )
         return SimpleNamespace(ready=True)
 
     monkeypatch.setattr(
@@ -31,7 +40,12 @@
     assert backend_headers.build_backend_http_headers() == {
         "Authorization": "Bearer test-backend-token",
     }
-    assert calls == ["start"]
+    assert calls == [
+        (
+            8.0,
+            1.0,
+        )
+    ]
 
 
 def test_build_backend_http_headers_rejects_unready_backend(
@@ -40,7 +54,7 @@
     monkeypatch.setattr(
         backend_headers,
         "start_backend",
-        lambda: SimpleNamespace(ready=False),
+        lambda **_kwargs: SimpleNamespace(ready=False),
     )
 
     with pytest.raises(
@@ -56,7 +70,7 @@
     monkeypatch.setattr(
         backend_headers,
         "start_backend",
-        lambda: SimpleNamespace(ready=True),
+        lambda **_kwargs: SimpleNamespace(ready=True),
     )
     monkeypatch.setattr(
         backend_headers,
```
