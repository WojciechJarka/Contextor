# CPA10M4B2_REMOVE_DUPLICATE_TRACE_KEY

STATUS=FINAL_PASS

## Scope

FILES_CHANGED:
- `contextor/core/runtime_trace.py`

REPORT_FILE=C:\Temp\Contextor_Repo\walkthrough.md
BASELINE_HEAD=0dac424c3c1bfb001b095d0c10ebf10a44b767c4
PRE_EDIT_WORKTREE=clean
ONLY_RUNTIME_TRACE_CHANGED=YES
INDEXER_CHANGED=NO
TESTS_CHANGED=NO

The only source edit removes the second identical `collision_extract_calls` entry from `trace_event`'s `key_map.update`. No indexer or test file was changed in this task.

## Static verification

Relevant nonblank key entries are in the required order:
- `collision_extract_calls`
- `collision_extract_sum_ms`
- `test_extract_calls`

The existing blank separator was preserved; no formatting change was made beyond deleting the duplicate line.

DUPLICATE_COLLISION_EXTRACT_CALLS_KEY=NO
EXACT_NONBLANK_SEQUENCE=PASS

## Validation

PY_COMPILE=PASS
PY_COMPILE_COMMAND=`.venv\Scripts\python.exe -m py_compile contextor\core\runtime_trace.py`

TARGETED_TESTS=PASS
TARGETED_TEST_COMMAND=`.venv\Scripts\python.exe -m pytest -q tests/test_runtime_trace.py::test_canonical_writer_analysis_trace_is_self_describing_and_durable tests/test_indexer_profile_evidence.py`
TARGETED_TEST_RESULT=`4 passed in 1.42s`

FULL_SUITE_RUN=NO

## Contextor LIVE

LIVE_PUBLICATION_REVISION=1391
LIVE_PUBLICATION_ORIGIN=desktop_watcher
WORKSPACE_SYNC=verified
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
CANONICAL_REVISION=1391

`get_file_edit_context` reported fresh canonical state, verified workspace sync, fresh diagnostics, and no warnings.

## Restart and Git

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_M4C=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_OPERATIONS=READ_ONLY
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

## ACTUAL_DIFF / FULL_DIFF

Complete diff for the only source file changed by this task:
```diff
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 94bced1..56e1ef2 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1834,7 +1834,6 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
                 "reference_extract_calls": "reference_extract_calls",
                 "reference_extract_sum_ms": "reference_extract_sum_ms",
 
-                "collision_extract_calls": "collision_extract_calls",
                 "collision_extract_calls": "collision_extract_calls",
                 "collision_extract_sum_ms": "collision_extract_sum_ms",
```

