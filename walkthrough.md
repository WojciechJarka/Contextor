# CPA10M7B1_REUSABLE_INDEXER_POOL_LIFECYCLE_PRIMITIVE

STATUS=FINAL_PASS

## SOURCE_GATE
SOURCE_DRIFT_GATE=PASS
PRE_EDIT_CONTEXTOR_WORKSPACE_SYNC=verified
PRE_EDIT_CANONICAL_REVISION=1404
PRE_EDIT_REQUIRED_ANCHORS=PASS
PRE_EDIT_GIT_SOURCE_AND_TEST_FILES_CLEAN=YES

## IMPLEMENTATION
REUSABLE_POOL_SCOPE=PROCESS_LOCAL_KEYED
REUSABLE_POOL_KEY=indexer
NORMAL_LEASE_EXIT_TERMINATES_REUSABLE_POOL=NO
EXCEPTION_ESCAPE_INVALIDATES_REUSABLE_POOL=YES
REGISTRY_SCOPE_CHANGE_ROTATES_REUSABLE_POOL=YES
TERMINATE_ACTIVE_POOLS_DROPS_REUSABLE_GENERATION=YES
LEGACY_MANAGED_POOL_SEMANTICS_CHANGED=NO
INDEXER_WIRED_TO_REUSABLE_POOL=NO
ARTIFACT_USAGE_POOL_CHANGED=NO

## VALIDATION
PY_COMPILE=PASS
PY_COMPILE_COMMAND=.venv\Scripts\python.exe -m py_compile contextor\core\analysis\process_pool_lifecycle.py tests\test_process_pool_lifecycle.py
FIRST_TEST_GATE=PASS
FIRST_TEST_GATE_RESULT=8 passed in 1.77s
TARGETED_TESTS=PASS
TARGETED_TEST_COMMAND=.venv\Scripts\python.exe -m pytest -q tests/test_process_pool_lifecycle.py tests/test_mcp_child_process_cleanup.py tests/test_full_analysis_coordination.py
TARGETED_TEST_RESULT=33 passed in 26.67s; 1 dependency deprecation warning
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
PROFILE_RUN_COUNT=0
PROCESS_COUNT_EXPERIMENT_RUN=NO

## CONTEXTOR_LIVE
DESKTOP_WATCHER_PUBLICATION=PASS
LIVE_EVENTS_REVISION_1405_1406=CONTINUOUS
LIVE_EVENTS_RESYNC_REQUIRED=NO
SOURCE_FILE_WORKSPACE_SYNC=verified
TEST_FILE_WORKSPACE_SYNC=verified
CANONICAL_REVISION=1406
SOURCE_FILE_SYNTAX_DIAGNOSTICS=FRESH_ZERO
TEST_FILE_SYNTAX_DIAGNOSTICS=FRESH_ZERO
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
DIAGNOSTICS_FRESHNESS=FRESH_FOR_BOTH_FILES
SOURCE_EVENT_BLAST_RADIUS=DEFERRED
POST_PUBLICATION_CANONICAL_PROJECTIONS=FRESH
NEW_PRIMITIVE_DIRECT_CONSUMERS=tests.test_process_pool_lifecycle
LEGACY_MANAGED_PROCESS_POOL_DIRECT_CONSUMERS=contextor.core.reporting_layer.artifact_usage_report, contextor.core.symbol_engine.indexer, tests.test_process_pool_lifecycle

## RESTART
MCP_SERVER_RESTART_REQUIRED_BEFORE_M7B2=YES
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_M7B2=YES
RESTART_PERFORMED=NO

## CHANGE_CONTROL
FILES_CHANGED=contextor/core/analysis/process_pool_lifecycle.py; tests/test_process_pool_lifecycle.py
REPORT_FILE=walkthrough.md
ACTUAL_DIFF=COMPLETE_FULL_DIFFS_INCLUDED
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
GIT_MUTATION_PERFORMED=NO

## COMPLETE_FULL_DIFFS
diff --git a/contextor/core/analysis/process_pool_lifecycle.py b/contextor/core/analysis/process_pool_lifecycle.py
index e8c26ee..92549ff 100644
--- a/contextor/core/analysis/process_pool_lifecycle.py
+++ b/contextor/core/analysis/process_pool_lifecycle.py
@@ -17,0 +18,6 @@ _active_executors: dict[int, Any] = {}
+_reusable_executors: dict[str, Any] = {}
+_reusable_registry_values: dict[str, str | None] = {}
+_reusable_generations: dict[str, int] = {}
+_reusable_use_locks: dict[str, threading.RLock] = {}
+_reusable_generation_counter = 0
+
@@ -20,0 +27 @@ def _ensure_process_local_registry_locked() -> None:
+    global _reusable_generation_counter
@@ -26,0 +34,5 @@ def _ensure_process_local_registry_locked() -> None:
+    _reusable_executors.clear()
+    _reusable_registry_values.clear()
+    _reusable_generations.clear()
+    _reusable_use_locks.clear()
+    _reusable_generation_counter = 0
@@ -47,0 +60,204 @@ def active_process_pool_count() -> int:
+def _reusable_pool_use_lock(
+    pool_key: str,
+) -> threading.RLock:
+    if not pool_key:
+        raise ValueError(
+            "Reusable process-pool key must be non-empty."
+        )
+
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+
+        lock = _reusable_use_locks.get(
+            pool_key
+        )
+
+        if lock is None:
+            lock = threading.RLock()
+            _reusable_use_locks[
+                pool_key
+            ] = lock
+
+        return lock
+
+
+def _drop_reusable_executor(
+    pool_key: str,
+    executor: Any,
+) -> None:
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+
+        if (
+            _reusable_executors.get(
+                pool_key
+            )
+            is not executor
+        ):
+            return
+
+        _reusable_executors.pop(
+            pool_key,
+            None,
+        )
+        _reusable_registry_values.pop(
+            pool_key,
+            None,
+        )
+        _reusable_generations.pop(
+            pool_key,
+            None,
+        )
+        _active_executors.pop(
+            id(executor),
+            None,
+        )
+
+
+def _create_reusable_process_pool(
+    pool_key: str,
+    registry_value: str | None,
+) -> tuple[Any, int]:
+    global _reusable_generation_counter
+
+    factory_kwargs: dict[str, Any] = {}
+
+    if registry_value:
+        factory_kwargs[
+            "initializer"
+        ] = _initialize_mcp_managed_worker
+
+        factory_kwargs[
+            "initargs"
+        ] = (
+            os.getpid(),
+            None,
+            (),
+        )
+
+    executor = ProcessPoolExecutor(
+        **factory_kwargs
+    )
+
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+
+        _reusable_generation_counter += 1
+        generation = (
+            _reusable_generation_counter
+        )
+
+        _active_executors[
+            id(executor)
+        ] = executor
+
+        _reusable_executors[
+            pool_key
+        ] = executor
+
+        _reusable_registry_values[
+            pool_key
+        ] = registry_value
+
+        _reusable_generations[
+            pool_key
+        ] = generation
+
+    return executor, generation
+
+
+@contextmanager
+def managed_reusable_process_pool(
+    pool_key: str,
+) -> Iterator[tuple[Any, bool, int]]:
+    """
+    Lease one process-local reusable ProcessPoolExecutor.
+
+    Normal context exit preserves the executor and its workers.
+
+    Any exception escaping the lease invalidates and terminates that
+    generation so the next lease must create a fresh executor.
+
+    A change of CONTEXTOR_MCP_PROCESS_REGISTRY also rotates the
+    generation before reuse, preventing workers registered under one
+    registry scope from silently surviving into another scope.
+    """
+
+    use_lock = _reusable_pool_use_lock(
+        pool_key
+    )
+
+    with use_lock:
+        registry_value = os.environ.get(
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        )
+
+        with _registry_lock:
+            _ensure_process_local_registry_locked()
+
+            executor = (
+                _reusable_executors.get(
+                    pool_key
+                )
+            )
+
+            previous_registry_value = (
+                _reusable_registry_values.get(
+                    pool_key
+                )
+            )
+
+            generation = (
+                _reusable_generations.get(
+                    pool_key
+                )
+            )
+
+        if (
+            executor is not None
+            and previous_registry_value
+            != registry_value
+        ):
+            terminate_process_pool(
+                executor
+            )
+
+            _drop_reusable_executor(
+                pool_key,
+                executor,
+            )
+
+            executor = None
+            generation = None
+
+        reused = executor is not None
+
+        if executor is None:
+            executor, generation = (
+                _create_reusable_process_pool(
+                    pool_key,
+                    registry_value,
+                )
+            )
+
+        assert generation is not None
+
+        try:
+            yield (
+                executor,
+                reused,
+                generation,
+            )
+        except BaseException:
+            terminate_process_pool(
+                executor
+            )
+
+            _drop_reusable_executor(
+                pool_key,
+                executor,
+            )
+
+            raise
+
+
@@ -215 +431,8 @@ def terminate_active_process_pools(
-        executors = tuple(_active_executors.values())
+        executors = tuple(
+            _active_executors.values()
+        )
+
+    target_ids = {
+        id(executor)
+        for executor in executors
+    }
@@ -217,0 +441 @@ def terminate_active_process_pools(
+
@@ -222,0 +447,32 @@ def terminate_active_process_pools(
+
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+
+        for executor_id in target_ids:
+            _active_executors.pop(
+                executor_id,
+                None,
+            )
+
+        for (
+            pool_key,
+            executor,
+        ) in tuple(
+            _reusable_executors.items()
+        ):
+            if id(executor) not in target_ids:
+                continue
+
+            _reusable_executors.pop(
+                pool_key,
+                None,
+            )
+            _reusable_registry_values.pop(
+                pool_key,
+                None,
+            )
+            _reusable_generations.pop(
+                pool_key,
+                None,
+            )
+
@@ -228,0 +485 @@ __all__ = [
+    "managed_reusable_process_pool",
diff --git a/tests/test_process_pool_lifecycle.py b/tests/test_process_pool_lifecycle.py
index d0ba52b..fba84ae 100644
--- a/tests/test_process_pool_lifecycle.py
+++ b/tests/test_process_pool_lifecycle.py
@@ -6,0 +7,2 @@ import time
+import pytest
+
@@ -229,0 +232,211 @@ def test_desktop_close_force_terminates_process_local_pools(
+
+
+def test_reusable_process_pool_preserves_generation_between_leases(
+    monkeypatch,
+):
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+
+    created = []
+
+    def factory(**_kwargs):
+        executor = _FakeExecutor()
+        created.append(executor)
+        return executor
+
+    monkeypatch.setattr(
+        lifecycle,
+        "ProcessPoolExecutor",
+        factory,
+    )
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        first_executor,
+        first_reused,
+        first_generation,
+    ):
+        assert first_reused is False
+        assert lifecycle.active_process_pool_count() == 1
+
+    assert first_executor.shutdown_calls == []
+    assert lifecycle.active_process_pool_count() == 1
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        second_executor,
+        second_reused,
+        second_generation,
+    ):
+        assert second_reused is True
+        assert second_executor is first_executor
+        assert second_generation == first_generation
+
+    assert len(created) == 1
+    assert lifecycle.active_process_pool_count() == 1
+
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+    assert lifecycle.active_process_pool_count() == 0
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        third_executor,
+        third_reused,
+        third_generation,
+    ):
+        assert third_reused is False
+        assert third_executor is not first_executor
+        assert third_generation > first_generation
+
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+
+def test_reusable_process_pool_exception_invalidates_generation(
+    monkeypatch,
+):
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+
+    created = []
+
+    def factory(**_kwargs):
+        executor = _FakeExecutor()
+        created.append(executor)
+        return executor
+
+    monkeypatch.setattr(
+        lifecycle,
+        "ProcessPoolExecutor",
+        factory,
+    )
+
+    with pytest.raises(RuntimeError):
+        with lifecycle.managed_reusable_process_pool(
+            "indexer",
+        ) as (
+            first_executor,
+            first_reused,
+            first_generation,
+        ):
+            assert first_reused is False
+            raise RuntimeError("boom")
+
+    assert first_executor.shutdown_calls == [
+        (False, True)
+    ]
+    assert lifecycle.active_process_pool_count() == 0
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        second_executor,
+        second_reused,
+        second_generation,
+    ):
+        assert second_reused is False
+        assert second_executor is not first_executor
+        assert second_generation > first_generation
+
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+
+def test_reusable_process_pool_rotates_when_registry_scope_changes(
+    monkeypatch,
+    tmp_path,
+):
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+    created = []
+
+    def factory(**kwargs):
+        executor = _FakeExecutor()
+        executor.factory_kwargs = kwargs
+        created.append(executor)
+        return executor
+
+    monkeypatch.setattr(
+        lifecycle,
+        "ProcessPoolExecutor",
+        factory,
+    )
+
+    first_registry = str(
+        tmp_path / "registry-a"
+    )
+    second_registry = str(
+        tmp_path / "registry-b"
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        first_registry,
+    )
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        first_executor,
+        first_reused,
+        first_generation,
+    ):
+        assert first_reused is False
+
+    assert (
+        first_executor.factory_kwargs[
+            "initializer"
+        ]
+        is lifecycle._initialize_mcp_managed_worker
+    )
+
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        second_registry,
+    )
+
+    with lifecycle.managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        second_executor,
+        second_reused,
+        second_generation,
+    ):
+        assert second_reused is False
+        assert second_executor is not first_executor
+        assert second_generation > first_generation
+
+    assert first_executor.shutdown_calls == [
+        (False, True)
+    ]
+
+    assert len(created) == 2
+    assert lifecycle.active_process_pool_count() == 1
+
+    lifecycle.terminate_active_process_pools(
+        timeout=0.01,
+    )
+
+    assert lifecycle.active_process_pool_count() == 0
