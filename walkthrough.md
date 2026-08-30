# BOTTLENECKS-0H — POST-0G FULL-ANALYSIS COST REMAP

VERDICT=CURRENT_COST_MAP_READY

Scope was read-only measurement and architectural discovery. No production or test file was modified for 0H. The required disposable benchmark copies and isolated caches were outside the canonical repository and were removed after measurement.

## Protocol and validity

- Benchmark root: `C:\Temp\Contextor_Benchmarks\0H\run2`.
- Pre-benchmark gate passed: the resolved benchmark root was neither equal to nor a descendant of `C:\Temp\Contextor_Repo`.
- Source copy: current source, 316 Python modules.
- LIVE was disconnected in the external harness; cache/output/state were isolated.
- Executor selection was normal production selection; no production executor flag or instrumentation was added.
- Runs: one cold followed by three unchanged-source warm `ContextorFacade.analyze_project` runs.
- All four runs completed with result present, 316 modules, and zero errors.
- Three initial harness attempts with incorrect wrapper/import targets were rejected as harness-contaminated and excluded; they produced no analysis result used below.
- No full pytest run was performed.

## Full-analysis measurements

All values are milliseconds. Warm values are `warm1`, `warm2`, `warm3`; percentage is median divided by the warm total median. Nested rows are shown for attribution and must not be summed as independent costs.

| Stage | warm1 | warm2 | warm3 | median | % warm total |
|---|---:|---:|---:|---:|---:|
| TOTAL_ANALYZE_PROJECT | 13956.944 | 10144.289 | 10829.406 | 10829.406 | 100.00% |
| INDEX_REPOSITORY | 4480.778 | 1305.334 | 1537.160 | 1537.160 | 14.20% |
| COLLISION_FACTS | 1083.290 | 1092.994 | 1117.901 | 1092.994 | 10.10% |
| PACKAGE_ROOT | 8.996 | 7.321 | 7.619 | 7.619 | 0.07% |
| BUILD_GRAPH | 17.705 | 14.257 | 14.025 | 14.257 | 0.13% |
| VALIDATION | 4.463 | 4.048 | 4.549 | 4.463 | 0.04% |
| METRICS_CYCLES_DEBT | 2.480 | 2.722 | 2.623 | 2.623 | 0.02% |
| GLOBAL_PIPELINE | 7049.777 | 6692.937 | 7108.293 | 7049.777 | 65.09% |
| ARTIFACT_PIPELINE_TOTAL | 6395.295 | 6066.395 | 6424.747 | 6395.295 | 59.07% |
| ARTIFACT_USAGE_COLLECTION | 5619.315 | 5313.194 | 5714.753 | 5619.315 | 51.89% |
| COLLECT_MODULE_ARTIFACTS | 4094.280 | 3853.805 | 4245.710 | 4094.280 | 37.80% |
| COMPACT_ARTIFACT | 15.882 | 13.890 | 13.627 | 13.890 | 0.13% |
| COMPACT_STRUCTURE | 6.266 | 4.355 | 3.492 | 4.355 | 0.04% |
| GRAPH_ANALYTICS | 417.658 | 369.279 | 353.591 | 369.279 | 3.41% |
| DEPENDENCY_MATRIX | 395.597 | 43.666 | 40.325 | 43.666 | 0.40% |
| SHARED_CLUSTERS | 302.678 | 326.861 | 295.597 | 302.678 | 2.80% |
| PERSISTENCE | 227.791 | 249.837 | 291.658 | 249.837 | 2.31% |

`ARTIFACT_USAGE_COLLECTION`, `COLLECT_MODULE_ARTIFACTS`, and `ARTIFACT_PIPELINE_TOTAL` are nested. `GLOBAL_PIPELINE` also contains the artifact pipeline. The independent top-level measurements therefore identify artifact collection and repository indexing as the meaningful cost centers; the percentages are attribution percentages, not additive shares.

COLD_TOTAL=29960.400 ms.

The artifact-usage timer was installed on the alias actually used by `artifact_pipeline`; the collect timer was installed on `artifact_usage_report`. This avoids the earlier invalid zero reading from wrapping only the wrong import binding.

## Top-two bounded decomposition

The bounded internal warm diagnostic was one additional uncontaminated warm run and is not part of the three-run medians.

1. `ARTIFACT_USAGE_COLLECTION` / `collect_module_artifacts`:

   - `REFERENCE_INDEX_BUILD=3323.518 ms`.
   - `WORKER_COMPUTE=765.240 ms`.
   - `ARTIFACT_INDEX=8.812 ms`.
   - `SHARED_KEYS=0.585 ms`.
   - `FILTER_SHARED=0.602 ms`.
   - `SHARED_CLUSTERS_BUILD=9.357 ms`.
   - `CORE_CANDIDATES=0.501 ms`.
   - `DISCOVER_TEST_DIRS=162.546 ms`.
   - `TEST_CONTEXT_INDEX=1107.498 ms`.
   - `TEST_CONTEXT_PER_MODULE=178.205 ms` (nested per-module work).

   The reference-index rebuild is approximately 81% of the measured collect median (`3323.518 / 4094.280`) and is the dominant owned subcost. Worker symbol-fact computation is comparatively small after fusion.

2. `INDEX_REPOSITORY`:

   The three representative warm timings were `4480.778`, `1305.334`, and `1537.160 ms`; the median is `1537.160 ms`. Source inspection identifies its owned work as module discovery, cache validation/assembly, and ProcessPool orchestration. A safe external split of spawned worker internals would require changing executor behavior or adding production instrumentation, both outside this task. The bounded evidence is therefore the direct stage timing and its large warm-run variance; no unsupported sub-timing is claimed.

## 0G adaptive-path confirmation

AVAILABLE_FACT_TASKS=316

FALLBACK_PATH_TASKS=0

FAILURES=0

The current all-available artifact stage selected the adaptive serial worker path. The post-fusion artifact computation performed no source parses or source reads for these tasks.

## Comparison

0E baseline full-analysis total: `22431.252 ms`.

Current controlled warm median: `10829.406 ms`.

Delta: `-11601.846 ms` (`-51.72%`).

The user-observed Desktop result of approximately 18 seconds is separate real-world context and is not treated as equivalent to this isolated benchmark protocol.

## Decision and next target

NEXT_TARGET_FILE=`contextor/core/reporting_layer/artifact_usage_report.py`

NEXT_TARGET_SYMBOL=`collect_module_artifacts`

ROOT_COST=The full-analysis artifact path rebuilds a `RepositoryReferenceIndex` inside `collect_module_artifacts` even though the same analysis run already has reference-index-capable data and the artifact path is the dominant remaining cost center.

EXPECTED_CHANGE_SHAPE=Create or retain one run-scoped `RepositoryReferenceIndex` in the full-analysis path and pass it through the artifact pipeline into `generate_artifact_usage_report` and `collect_module_artifacts`. Keep the existing `None` fallback for standalone callers, so only the full-analysis path reuses the run-scoped object. Preserve current available-fact, fallback-extraction, failure-isolation, and artifact assembly behavior.

ESTIMATED_MAX_SAVINGS_MS_PERCENT=3323.518 ms upper-bound attribution, approximately 30.70% of the current warm-total median. This is a removable-cost upper bound, not a measured promise; construction may be required elsewhere and parity validation is mandatory.

REQUIRED_INVARIANTS=

- Artifact, failure, import, graph-membership, and public result semantics remain identical.
- One authoritative run-scoped reference index is reused; no second independent cache and no AST persistence are introduced.
- Standalone callers without a reference index retain the current construction fallback.
- Available symbol-fact tasks remain parse/read free; fallback tasks retain existing extraction semantics.
- Cache, index, Module/API/MCP, LIVE, watcher, FileState, coordinator, and executor contracts remain unchanged.
- Nested timers and progress/checkpoint behavior remain correctly owned.

REQUIRED_TESTS=

- Full-analysis artifact output parity with and without the passed reference index.
- Exactly-once/reuse behavior for the run-scoped reference index.
- Standalone `collect_module_artifacts(..., reference_index=None)` fallback parity.
- Available-fact no-parse/no-source-read regression and fallback failure isolation.
- Existing focused artifact, index-fusion, and report tests only; no full suite.

## Required report fields

FILES_CHANGED=NONE

DIFFS=NONE

The only file written for this 0H report is the repository-root `walkthrough.md`; it is reporting output and is not counted as a production/test file change. Pre-existing 0G/0G1 worktree changes were not altered.

FULL_SUITE_RUN_BY_AGENT=NO

BENCHMARK_DISPOSABLE_DATA=REMOVED
