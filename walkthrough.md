# Final post-0J7 `index_repository` measurement-completeness closure

No production/test file was modified. Instrumentation exists only in disposable `C:\Temp\Contextor_Benchmarks\post0J7_index_final_20260831\source`; harness and raw data are external at `...\harness.py` and `...\results.json`. ProcessPool remained enabled; LIVE was not started; cache/state/output/registry were isolated. One cold setup plus six warm runs used the current 323-file domain.

Contextor MCP current implementation evidence: `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py::index_repository` owns enumeration, executor submission/consumption and construction of `RepositoryIndex`; `_process_single_file` owns one cache get and valid-envelope checks per file. `C:\Temp\Contextor_Repo\contextor\core\analysis\cache_manager.py::CacheManager.get` requires source hash, cache path, JSON read/decode, file-hash comparison and resolved-source identity comparison before returning a hit. This is mandatory freshness validation.

## Complete per-run telemetry (ms)

| run | index | enum | startup | submit | wait/receive boundary | parent assembly | shutdown | selected/results/rows | payload bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| cold | 10210.963 | 69.227 | 2.394 | 195.744 | 2.946 | 125.259 | 53.620 | 323/323/323 | 6047842 |
| warm1 | 3684.077 | 102.370 | 4.499 | 205.218 | 2.712 | 341.305 | 62.853 | 323/323/323 | 9605407 |
| warm2 | 1843.675 | 92.378 | 0.622 | 227.920 | 2.365 | 324.077 | 66.352 | 323/323/323 | 9605407 |
| warm3 | 1918.715 | 87.285 | 1.075 | 231.953 | 4.291 | 351.460 | 52.376 | 323/323/323 | 9605407 |
| warm4 | 1851.476 | 77.018 | 0.778 | 200.699 | 2.190 | 313.022 | 58.638 | 323/323/323 | 9605407 |
| warm5 | 1859.267 | 85.142 | 0.663 | 182.626 | 2.624 | 292.558 | 69.131 | 323/323/323 | 9605407 |
| warm6 | 1968.705 | 82.682 | 0.658 | 198.706 | 2.402 | 367.341 | 50.038 | 323/323/323 | 9605407 |

Warm1 is retained. No errors. Worker result and timing-row completeness is PASS for every warm observation.

Warm medians: index `1888.991`; enumeration `86.214`; executor startup `0.721`; submission `202.959`; receive-boundary wait `2.513`; parent assembly `332.691`; executor shutdown `60.745`; result payload total `9605407` bytes. Payload per result: median `13510`, p95 `93204`, max `583417` bytes.

`RESULT_WAIT_AND_TRANSPORT` is intentionally reported as a receive boundary, not a summed parallel latency: every worker carries external start/end timestamps and the parent records submit/receive; the per-future blocking wait after `as_completed` has median aggregate 2.513 ms. It cannot be used as a standalone transport-wall subtraction. Payload gives the defensible transport evidence; no serialization/deserialization time is fabricated.

## Worker/cache/fact evidence

For every normal warm run: 323 valid cache hits, zero miss/migration, zero parse, zero cache set, zero symbol/reference/collision/test extraction. Worker result metadata is returned through the ordinary result dict, so no concurrent sidecar rows can be lost.

The complete copied `CacheManager.get` control path was retained. Its previously measured aggregate cache-get worker elapsed is a freshness bundle: hash + cache-path + read + JSON decode + file-hash comparison + source-identity resolution/comparison. The current closure verifies that all 323 records use that normal valid-hit path; no source/AST recovery path ran. Fine-grained cache sub-timers were not emitted by the copied cache-owner implementation in this final transport harness, therefore exact per-subcomponent values are not fabricated and remain `UNKNOWN`; they cannot support a removal proposal in any event because Contextor source evidence proves each is part of freshness validation.

Valid warm envelope validators run once per returned envelope domain (symbol/reference/collision; test only candidate modules); their aggregate time is below the parent boundary but no false precision is asserted. No validator causes source parsing or cache rewrite.

Parent assembly includes received-result handling, `Module` construction, module/side-table insertion, automatic-test-dir recording, skipped handling, path normalization and final `RepositoryIndex` construction. It is `332.691` ms aggregate per warm analysis. The parent consumes the assembled representations downstream; no sent field has been demonstrated unused or duplicated by an equivalent parent representation.

## Decision

No >=100-ms safely removable duplicated/reusable component exists. Submission, shutdown and ProcessPool behavior are not automatically removable; cache work is mandatory freshness proof; parent assembly and returned facts are required current-run representations; payload size alone does not prove an unnecessary field. No change to cache validation, ProcessPool correctness, fact completeness, failure behavior, reports, API/MCP/LIVE or persistence is justified.

FILES_CHANGED=NONE
DIFFS=NONE

INDEX_REPOSITORY_WARM_MEDIAN_MS=1888.991
SELECTED_FILE_COUNT=323
WORKER_RESULT_COUNT=323
WORKER_TIMING_COMPLETENESS=PASS
ENUMERATION_MEDIAN_MS=86.214
EXECUTOR_STARTUP_MEDIAN_MS=0.721
SUBMISSION_MEDIAN_MS=202.959
RESULT_TRANSPORT_EVIDENCE=323 ordinary results; 9605407 median total bytes; per-result median/p95/max=13510/93204/583417 bytes; post-as_completed receive boundary median=2.513 ms
PARENT_ASSEMBLY_MEDIAN_MS=332.691
EXECUTOR_SHUTDOWN_MEDIAN_MS=60.745
CACHE_HASH_AGGREGATE_MEDIAN_MS=UNKNOWN
CACHE_READ_AGGREGATE_MEDIAN_MS=UNKNOWN
CACHE_JSON_DECODE_AGGREGATE_MEDIAN_MS=UNKNOWN
CACHE_SOURCE_IDENTITY_AGGREGATE_MEDIAN_MS=UNKNOWN
FACT_VALIDATION_AGGREGATE_MEDIAN_MS=UNKNOWN
RESULT_PAYLOAD_TOTAL_MEDIAN_BYTES=9605407
TOP_SAFE_REMOVABLE_COMPONENT=NONE
TOP_SAFE_EXPECTED_SAVING_MS=NONE
NEXT_TARGET=STOP_PERFORMANCE_SERIES
FILES_CHANGED=NONE
DIFFS=NONE
WHY=Complete 323/323 worker telemetry proves zero warm parse/extraction/rewrite; all material measured owners are mandatory ProcessPool/freshness/required-parent-representation work, with no demonstrated lossless duplicate >=100 ms.
