## CPA10I_INDEXING_SINGLE_SNAPSHOT_WARM_CACHE_FAST_PATH

STATUS=PARTIAL_REGRESSION_BLOCKED
HEAD_BEFORE=92a978d5158cd477c9bb7327b0b9be9f349fe4bb
HEAD_AFTER=92a978d5158cd477c9bb7327b0b9be9f349fe4bb
FILES_CHANGED=contextor/core/source.py; contextor/core/analysis/cache_manager.py; contextor/core/symbol_engine/indexer.py; contextor/core/analysis/profile_analysis.py; contextor/mcp/docs/contextor_profile_analysis.json; tests/test_index_fusion.py; tests/test_indexer_profile_evidence.py; tests/analysis/test_cache_manager_content_hash.py
PY_COMPILE=PASS
FOCUSED_TESTS=PASS (17 passed in 4.03s)
REGRESSION_TESTS=FAIL (226 passed, 7 failed)
PROFILE_RUN=NOT_RUN
PROFILE_WORKER_RESTART_REQUIRED=NO
MCP_SERVER_RESTART_REQUIRED=NO_FOR_FUTURE_PROFILE_EXECUTION
DESKTOP_RUNTIME_RESTART_REQUIRED=YES_BEFORE_DESKTOP_CERTIFICATION

IMPLEMENTATION_CONTRACT=
- one raw-byte snapshot per file task
- cache validation before AST parse
- complete warm hit skips AST parse
- CacheManager get/set reuse supplied snapshot bytes
- cache format unchanged
- lineage SHA-256 semantics unchanged
- incomplete/miss path parses and recomputes required facts

CONTEXTOR_FIRST_VERIFICATION=PASS: documented get_symbol_implementation preview/fetch resolved every required pre-edit symbol at LIVE revision 1153.

REGRESSION_BLOCKER=
- tests/analysis/test_lineage_extraction.py has FakeCache.get/set doubles without required source_bytes keyword support (2 failures).
- tests/test_collision_facts_fusion.py and tests/test_test_context_fusion.py still monkeypatch removed indexer.parse_source_with_fingerprint (5 failures).
- Those files are outside FILES_TO_CHANGE_EXACTLY, so they were not changed.

ACTUAL_DIFF=Not certified: required regression contracts fail. Current git diff contains the eight task-changed files; walkthrough.md excluded.
