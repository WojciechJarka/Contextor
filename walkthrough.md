# PersistentIdentityRegistry read transaction repair

DECISION=PASS

## Transaction-mode contract

`_in_transaction` now means only an active scope. `_transaction_mode` is `read` or `write`.

- An outer write sets `write`; nested writes share its generation and existing commit/persistence path.
- An outer read sets `read`, recovers/loads, and releases without commit.
- A write inside a read raises `RuntimeError("Cannot enter write transaction inside read transaction.")` before caller-body mutation.
- A read inside a write views the write generation without changing outer commit behavior.
- Existing IDs resolve in either mode. Missing module/artifact IDs allocate only in `write`; read returns `None` with no slots/maps/recovery mutation.

`_repair_kind` remains in `_load_all`: read exposes its repaired in-memory projection. The regression verifies no read-only commit of that projection.

## Focused validation

```text
.venv\Scripts\python.exe -m pytest -q tests/test_persistent_registry.py tests/mcp/tools/test_minimal_registry_read_path.py tests/test_indexed_report_query.py
```

Result: `46 passed in 9.73s`.

Coverage: existing/missing IDs in read; exact state non-mutation; write allocation and reload persistence; controlled write-inside-read rejection; read-inside-write view; and repair projection without persistence. Existing interrupted-transaction recovery coverage remains in `tests/test_persistent_registry.py`; persistence protocol was not changed.

Fresh minimal invariants: `read_transaction count=1`, `mutating transaction count=0`, `discover_module_paths count=0`, `response parity=true` (focused canonical fixture returns the expected `pkg/module.py`).

`git diff --check` passed (only existing LF-to-CRLF warnings).

## LIVE evidence

Contextor MCP `get_live_events` after revision 234 returned `status=transient_connection_failure`, reason `Existing LIVE owner is temporarily unreachable`. No new runtime-performance certification is asserted.

MCP_RESTART_REQUIRED=YES

LIVE_RESTART_REQUIRED=NO

RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=YES

FILES_CHANGED

```text
contextor/core/reporting_engine/persistent_registry.py
tests/test_persistent_registry.py
```

## COMPLETE RAW UNIFIED DIFF

```diff
diff --git a/contextor/core/reporting_engine/persistent_registry.py b/contextor/core/reporting_engine/persistent_registry.py
index 9008bd3..d4e90d9 100644
--- a/contextor/core/reporting_engine/persistent_registry.py
+++ b/contextor/core/reporting_engine/persistent_registry.py
@@ -32,6 +32,7 @@ class PersistentIdentityRegistry:
         self._state = {}
         self._in_transaction = False
+        self._transaction_mode: str | None = None
         self._lock_file_obj = None
@@ -198,11 +199,16 @@ class PersistentIdentityRegistry:
     def transaction(self):
         if self._in_transaction:
+            if self._transaction_mode != "write":
+                raise RuntimeError(
+                    "Cannot enter write transaction inside read transaction."
+                )
             yield
             return
         self._lock()
         self._in_transaction = True
+        self._transaction_mode = "write"
@@ -251,6 +257,7 @@ class PersistentIdentityRegistry:
         finally:
+            self._transaction_mode = None
             self._in_transaction = False
             self._unlock()
@@ -263,12 +270,14 @@ class PersistentIdentityRegistry:
         self._lock()
         self._in_transaction = True
+        self._transaction_mode = "read"
         try:
             self._recover_transaction()
             self._load_all()
             yield
         finally:
+            self._transaction_mode = None
             self._in_transaction = False
             self._unlock()
@@ -311,7 +320,7 @@ class PersistentIdentityRegistry:
-        if self._in_transaction:
+        if self._transaction_mode == "write":
             new_id = self._allocate_slot("module")
@@ -327,7 +336,7 @@ class PersistentIdentityRegistry:
-        if self._in_transaction:
+        if self._transaction_mode == "write":
             new_id = self._allocate_slot("artifact")
diff --git a/tests/test_persistent_registry.py b/tests/test_persistent_registry.py
index ab5ce09..394d01c 100644
--- a/tests/test_persistent_registry.py
+++ b/tests/test_persistent_registry.py
@@ -1,6 +1,7 @@
 import os
 import json
 import shutil
+import copy
 import pytest
@@ -200,3 +201,62 @@ def test_registry_repairs_reverse_only_entries_into_recovery(temp_repo):
+def test_read_transaction_returns_existing_ids_without_allocating_missing_ids(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        module_id = registry.get_module_id("existing.py")
+        artifact_id = registry.get_artifact_id("existing::symbol")
+    with registry.read_transaction():
+        before = copy.deepcopy(registry._state)
+        assert registry.get_module_id("existing.py") == module_id
+        assert registry.get_artifact_id("existing::symbol") == artifact_id
+        assert registry.get_module_id("missing.py") is None
+        assert registry.get_artifact_id("missing::symbol") is None
+        assert registry._state == before
+
+def test_write_transaction_allocates_and_persists_missing_ids(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        module_id = registry.get_module_id("new.py")
+        artifact_id = registry.get_artifact_id("new::symbol")
+    reloaded = PersistentIdentityRegistry(temp_repo)
+    assert reloaded.get_module_id("new.py") == module_id
+    assert reloaded.get_artifact_id("new::symbol") == artifact_id
+
+def test_write_transaction_nested_in_read_transaction_fails_without_mutation(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.read_transaction():
+        before = copy.deepcopy(registry._state)
+        with pytest.raises(RuntimeError, match="Cannot enter write transaction inside read transaction\\."):
+            with registry.transaction():
+                pass
+        assert registry.get_module_id("missing.py") is None
+        assert registry.get_artifact_id("missing::symbol") is None
+        assert registry._state == before
+
+def test_read_transaction_nested_in_write_transaction_views_current_generation(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        module_id = registry.get_module_id("current.py")
+        artifact_id = registry.get_artifact_id("current::symbol")
+        with registry.read_transaction():
+            assert registry.get_module_id("current.py") == module_id
+            assert registry.get_artifact_id("current::symbol") == artifact_id
+    reloaded = PersistentIdentityRegistry(temp_repo)
+    assert reloaded.get_module_id("current.py") == module_id
+    assert reloaded.get_artifact_id("current::symbol") == artifact_id
+
+def test_read_transaction_repairs_in_memory_without_persisting_projection(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        registry._state["module_registry"]["id_to_path"]["9/3"] = "orphan.py"
+    registry_file = registry.files["module_registry"]
+    before = registry_file.read_bytes()
+    with registry.read_transaction():
+        assert "9/3" not in registry._state["module_registry"]["id_to_path"]
+        assert registry._state["module_recovery"]["9/3"]["path"] == "orphan.py"
+        assert registry._state["module_slots"]["9"] == 3
+    assert registry_file.read_bytes() == before
```

FULL_SUITE_RUN_BY_AGENT=NO
