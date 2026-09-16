# CPA10K5B1_ACTIVE_POOL_COUNT_LOCK_CORRECTION

TASK=CPA10K5B1_ACTIVE_POOL_COUNT_LOCK_CORRECTION
MODE=IMPLEMENT_EXACT_AUDITOR_PATCH
SCOPE=contextor/core/analysis/process_pool_lifecycle.py
IMPLEMENTATION_RESULT=PASS

## FILES_CHANGED

Expected and observed source change:

- contextor/core/analysis/process_pool_lifecycle.py

walkthrough.md is excluded from source/test diff accounting. No other source or test file is changed in the current working diff.

FILES_CHANGED_SOURCE_TEST_ONLY=contextor/core/analysis/process_pool_lifecycle.py
OTHER_SOURCE_TEST_DIFF=NONE
TEST_FILES_UNCHANGED=YES

## EXACT_BEFORE_AFTER

Before:

    def active_process_pool_count() -> int:
        with _registry_lock:
            _ensure_process_local_registry_locked()
        return len(_active_executors)

After:

    def active_process_pool_count() -> int:
        with _registry_lock:
            _ensure_process_local_registry_locked()
            return len(_active_executors)

The only semantic source change is the indentation of return len(_active_executors), placing the registry-count read inside _registry_lock.

## LOCK_SCOPE_EVIDENCE

Contextor pre-edit exact implementation resolved active_process_pool_count at lines 42-45 with the return outside the lock.

After the patch, Contextor get_source_range for contextor/core/analysis/process_pool_lifecycle.py lines 42-116 returned status=ok and the exact current disk source. The current ranges are:

- active_process_pool_count: lines 42-45; return len(_active_executors) is indented under with _registry_lock.
- _initialize_mcp_managed_worker: lines 48-75; unchanged.
- managed_process_pool: lines 78-116; unchanged.

The source-range diagnostics were fresh with zero syntax errors, zero name collisions, zero cycles, and attention_required=false.

Post-edit get_symbol_implementation correctly returned stale_source for the modified file because canonical revision 1293 predates this local edit and workspace_sync is out_of_sync. No update_file or analysis refresh was used; the exact current source was verified with get_source_range as required for a read-only local-edit check.

The lock now covers both _ensure_process_local_registry_locked() and len(_active_executors), so the count read is atomic with _register_executor and _unregister_executor under the existing registry lock.

## K5B1_CONTRACT_UNCHANGED

Contextor exact source-range verification confirms no change to:

- _initialize_mcp_managed_worker
- managed_process_pool
- terminate_process_pool
- terminate_active_process_pools
- _registry_pid semantics
- MCP server code
- mcp_process_registry.py
- analysis_jobs.py
- test files
- Desktop K5A code
- profile worker
- LIVE/runtime trace
- Git child code

K5B1_OTHER_PRODUCTION_CODE_UNCHANGED=YES
CURRENT_EXTERNALLY_OWNED_MCP_ROOT_TARGETED=NO
STALE_ORPHAN_MCP_ROOT_RECOVERY=EXISTING_BEHAVIOR

The correction does not alter MCP root ownership or existing stale-orphan recovery. It only restores the active-pool count read under the existing lock.

Previous evidence recovery established the literal K5B1 test names and bodies. This correction changed no tests.

TEST_NAME_DRIFT=NO
TEST_CONTRACT_EXACT=YES

## PY_COMPILE

Command:

    & .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/analysis/process_pool_lifecycle.py

Result: PASS, exit code 0.

PY_COMPILE=PASS

## TESTS

Only the authorized focused test was executed:

    & .\\.venv\\Scripts\\python.exe -m pytest tests/test_process_pool_lifecycle.py -q

Result:

    5 passed in 2.01s

No other tests were run.

FOCUSED_TESTS=PASS

## COMPLETE_DIFF

Complete current diff for contextor/core/analysis/process_pool_lifecycle.py:

    diff --git a/contextor/core/analysis/process_pool_lifecycle.py b/contextor/core/analysis/process_pool_lifecycle.py
    index 5c269cc..e8c26ee 100644
    --- a/contextor/core/analysis/process_pool_lifecycle.py
    +++ b/contextor/core/analysis/process_pool_lifecycle.py
    @@ -42,7 +42,7 @@ def _unregister_executor(executor: Any) -> None:
     def active_process_pool_count() -> int:
         with _registry_lock:
             _ensure_process_local_registry_locked()
    -    return len(_active_executors)
    +        return len(_active_executors)
 
 
     def _initialize_mcp_managed_worker(

The current source/test diff contains no other file.

## CERTIFICATION

ACTIVE_POOL_COUNT_LOCKED=YES
K5B1_OTHER_PRODUCTION_CODE_UNCHANGED=YES
TEST_FILES_UNCHANGED=YES
TEST_NAME_DRIFT=NO
TEST_CONTRACT_EXACT=YES
CURRENT_EXTERNALLY_OWNED_MCP_ROOT_TARGETED=NO
STALE_ORPHAN_MCP_ROOT_RECOVERY=EXISTING_BEHAVIOR
PY_COMPILE=PASS
FOCUSED_TESTS=PASS
STOP_CONDITION=Po tej jednej korekcie, teście i walkthrough.md czekaj na proceduj.
