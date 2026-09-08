FILES_CHANGED=
contextor/ui/single_instance.py
contextor/ui/gui.py
tests/test_gui_single_instance.py
TESTS_RUN=
.\.venv\Scripts\python.exe -m pytest -q tests/test_gui_single_instance.py tests/test_runtime_trace.py
.\.venv\Scripts\python.exe -m py_compile contextor/ui/single_instance.py contextor/__main__.py contextor/ui/gui.py contextor/core/runtime_trace.py
TEST_RESULTS=
10 passed in 3.26s
PYTEST_EXIT_CODE=0
PYCOMPILE_EXIT_CODE=0
ACTUAL_DIFF=
diff --git a/contextor/ui/single_instance.py b/contextor/ui/single_instance.py
new file mode 100644
index 0000000..02e79e6
--- /dev/null
+++ b/contextor/ui/single_instance.py
@@ -0,0 +1,84 @@
+"""Windows-user-session Desktop admission and activation signalling."""
+
+from __future__ import annotations
+
+import ctypes
+import os
+from ctypes import wintypes
+from typing import Callable
+
+MUTEX_NAME = "Local\\Contextor.Desktop.Singleton.v1"
+ACTIVATE_EVENT_NAME = "Local\\Contextor.Desktop.Activate.v1"
+ERROR_ALREADY_EXISTS = 183
+WAIT_OBJECT_0 = 0x00000000
+WAIT_TIMEOUT = 0x00000102
+_ACTIVATION_POLL_MS = 100
+
+def _kernel32():
+    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
+    kernel.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
+    kernel.CreateEventW.restype = wintypes.HANDLE
+    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
+    kernel.CreateMutexW.restype = wintypes.HANDLE
+    kernel.SetEvent.argtypes = [wintypes.HANDLE]
+    kernel.SetEvent.restype = wintypes.BOOL
+    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
+    kernel.WaitForSingleObject.restype = wintypes.DWORD
+    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
+    kernel.CloseHandle.restype = wintypes.BOOL
+    return kernel
+
+class DesktopSingleInstance:
+    def __init__(self, mutex=None, event=None, *, primary: bool = True, kernel=None) -> None:
+        self._mutex, self._event, self._kernel = mutex, event, kernel
+        self._closed = False
+        self.is_primary = primary
+
+    @classmethod
+    def acquire(cls) -> "DesktopSingleInstance":
+        if os.name != "nt":
+            return cls()
+        kernel = _kernel32()
+        event = kernel.CreateEventW(None, False, False, ACTIVATE_EVENT_NAME)
+        if not event:
+            return cls(kernel=kernel)
+        ctypes.set_last_error(0)
+        mutex = kernel.CreateMutexW(None, False, MUTEX_NAME)
+        mutex_error = ctypes.get_last_error()
+        if not mutex:
+            kernel.CloseHandle(event)
+            return cls(kernel=kernel)
+        return cls(mutex, event, primary=mutex_error != ERROR_ALREADY_EXISTS, kernel=kernel)
+
+    def signal_existing(self) -> None:
+        if os.name == "nt" and not self._closed and self._kernel is not None and self._event:
+            self._kernel.SetEvent(self._event)
+
+    def register_activation(self, root, callback: Callable[[], None]) -> None:
+        if not self.is_primary or os.name != "nt" or self._closed or self._kernel is None or not self._event:
+            return
+        def poll_activation() -> None:
+            if self._closed or not self._event:
+                return
+            result = self._kernel.WaitForSingleObject(self._event, 0)
+            if result == WAIT_OBJECT_0:
+                callback()
+            elif result != WAIT_TIMEOUT:
+                return
+            if not self._closed:
+                try:
+                    root.after(_ACTIVATION_POLL_MS, poll_activation)
+                except Exception:
+                    pass
+        root.after(0, poll_activation)
+
+    def close(self) -> None:
+        if self._closed:
+            return
+        self._closed = True
+        if os.name == "nt" and self._kernel is not None:
+            for handle in (self._event, self._mutex):
+                if handle:
+                    self._kernel.CloseHandle(handle)
+        self._event = self._mutex = None
+

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 377e0e6..1e1bb55 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1217,9 +1217,25 @@ class ContextorGUI:
         self.root.destroy()
 
 
-def run():
+def run(*, single_instance=None):
     root = tk.Tk()
     # The controller registers itself on the widget tree, which keeps it
     # alive for the lifetime of the window; no local reference needed.
     ContextorGUI(root)
+    if single_instance is not None:
+        def activate_existing_window():
+            root.deiconify()
+            try:
+                root.state("normal")
+                root.lift()
+                root.attributes("-topmost", True)
+                root.after(100, lambda: root.attributes("-topmost", False))
+                root.focus_force()
+                try:
+                    root.bell()
+                except Exception:
+                    pass
+            except Exception:
+                pass
+        single_instance.register_activation(root, activate_existing_window)
     root.mainloop()

diff --git a/tests/test_gui_single_instance.py b/tests/test_gui_single_instance.py
new file mode 100644
index 0000000..9819e47
--- /dev/null
+++ b/tests/test_gui_single_instance.py
@@ -0,0 +1,74 @@
+from __future__ import annotations
+
+import contextor.__main__ as entry
+from contextor.ui import single_instance
+
+
+def test_secondary_desktop_short_circuits_before_gui_startup(monkeypatch):
+    calls = []
+
+    class Guard:
+        is_primary = False
+
+        def signal_existing(self):
+            calls.append("signal")
+
+        def close(self):
+            calls.append("close")
+
+    monkeypatch.setattr(
+        single_instance.DesktopSingleInstance,
+        "acquire",
+        classmethod(lambda cls: Guard()),
+    )
+    assert entry._run_gui() == 0
+    assert calls == ["signal", "close"]
+
+
+def test_primary_activation_is_repeatable_and_polled_on_gui_thread(monkeypatch):
+    calls, scheduled = [], []
+
+    class Kernel:
+        def __init__(self):
+            self.results = [single_instance.WAIT_OBJECT_0, single_instance.WAIT_TIMEOUT, single_instance.WAIT_OBJECT_0]
+        def WaitForSingleObject(self, _event, timeout):
+            assert timeout == 0
+            return self.results.pop(0)
+        def CloseHandle(self, _handle):
+            return True
+
+    class Root:
+        def after(self, delay, callback):
+            scheduled.append((delay, callback))
+
+    monkeypatch.setattr(single_instance.os, "name", "nt")
+    guard = single_instance.DesktopSingleInstance(mutex=11, event=22, primary=True, kernel=Kernel())
+    guard.register_activation(Root(), lambda: calls.append("activate"))
+    assert scheduled[0][0] == 0
+    for expected in (["activate"], ["activate"], ["activate", "activate"]):
+        _, poll = scheduled.pop(0)
+        poll()
+        assert calls == expected
+    guard.close()
+
+
+def test_close_stops_future_activation_poll(monkeypatch):
+    scheduled = []
+
+    class Kernel:
+        def WaitForSingleObject(self, _event, _timeout):
+            raise AssertionError("poll must not reach kernel after close")
+        def CloseHandle(self, _handle):
+            return True
+
+    class Root:
+        def after(self, delay, callback):
+            scheduled.append((delay, callback))
+
+    monkeypatch.setattr(single_instance.os, "name", "nt")
+    guard = single_instance.DesktopSingleInstance(mutex=11, event=22, primary=True, kernel=Kernel())
+    guard.register_activation(Root(), lambda: None)
+    _, poll = scheduled.pop(0)
+    guard.close()
+    poll()
+    assert scheduled == []

