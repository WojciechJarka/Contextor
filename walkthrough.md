# CPA2_INDEXER_PROFILE_EVIDENCE

## STATUS

SUCCESS. Added structured parent-side indexer evidence. Critical-path ownership remains unchanged: only FULL_ANALYSIS_STAGE_END(stage="indexing").elapsed_ms represents indexing wall time.

## FILES_CHANGED

- contextor/core/symbol_engine/indexer.py
- contextor/core/runtime_trace.py
- tests/test_runtime_trace.py
- tests/test_indexer_profile_evidence.py
- walkthrough.md (this report)

## IMPLEMENTATION

- _process_single_file now returns parse/cache/lineage evidence for every normal result and parse-SourceError result. Parse still precedes cache.get; cache is not queried after parse failure.
- index_repository has one shared record_file_task_evidence(result), invoked exactly once in inline and ProcessPool parent collection.
- New parent-only ANALYSIS/FULL_ANALYSIS_INDEX_EVIDENCE has operation=indexing_file_tasks, execution mode, counts/cache facts, and aggregate per-file task sums. It deliberately has no elapsed_ms.
- Existing FULL_ANALYSIS_LINEAGE_EXTRACTION retains its elapsed_ms, result string, and top-10 compatibility; it now carries timing_semantics=aggregate_file_task_not_critical_path, lineage_extract_calls, and lineage_cache_hits.
- Runtime trace whitelist/header expose every new field. Each *_sum_ms header description says aggregate per-file task milliseconds; not critical-path wall. Header ANALYSIS events include FULL_ANALYSIS_INDEX_EVIDENCE.

## TESTS

tests/test_indexer_profile_evidence.py and tests/test_runtime_trace.py: 16 passed in 13.57s.

py_compile passed for all four changed Python files. git diff --check passed. No full pytest, full analysis, or benchmark ran.

## EVIDENCE_CONTRACT

| Signal | Meaning |
| --- | --- |
| FULL_ANALYSIS_STAGE_END(indexing).elapsed_ms | CRITICAL_PATH wall, unchanged owner |
| FULL_ANALYSIS_INDEX_EVIDENCE.*_sum_ms | Aggregate per-file task diagnostic time; NOT critical-path wall |
| FULL_ANALYSIS_LINEAGE_EXTRACTION.elapsed_ms | Existing aggregate file-task/worker sum; explicitly NOT critical-path wall |
| source_parse_calls with warm cache | Parse occurred before cache lookup |
| cache_hits, lineage_cache_hits, lineage_extract_calls | Structured cache/extraction evidence; no result-string parsing |

Focused warm-cache proof: two cached files report source_parse_calls=2, cache_hits=2, lineage_cache_hits=2, lineage_extract_calls=0. Cold proof confirms the lineage extraction event’s explicit noncritical timing semantic.

## CONTEXTOR_FLOW_VERIFY

Contextor post-edit call contexts show one index_repository -> _process_single_file relationship, existing parent collection coverage for inline and ProcessPool, and trace_event as the canonical ordinary runtime-event append owner. No new indexer/cache owner, child-process trace_event, ContextVar propagation, or trace-session lifecycle was added.

Contextor reports workspace_sync=out_of_sync at canonical revision 1094 because the modified files deliberately diverge from the source snapshot. No analysis was run to refresh it.

## DIFFS

### contextor/core/symbol_engine/indexer.py

- Added parse/cache monotonic measurements and boolean result evidence.
- Replaced lineage-only recorder with shared parent record_file_task_evidence.
- Added parent-only emit_index_profile_evidence for inline and ProcessPool.
- Preserved the existing lineage event, result string, and top-10 data.

### contextor/core/runtime_trace.py

- Added event-field whitelist/header descriptions and FULL_ANALYSIS_INDEX_EVIDENCE header declaration.

### tests/test_runtime_trace.py

- Extended self-describing header contract.

### tests/test_indexer_profile_evidence.py

- Added warm-cache and cold-lineage focused evidence tests.

## COMMIT_SHA

2d1296d20725a3829d2062dc0a5c7459e3ec46e8 (existing HEAD; no commit created).

## RUNTIME_RESTART_REQUIRED

YES. Reload the active MCP runtime only before later real CPA use. No MCP, Desktop, or LIVE restart was performed.

Awaiting proceduj.
