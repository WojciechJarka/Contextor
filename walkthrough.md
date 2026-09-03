# Pipeline attribution completion

DECISION=NO_GO_FULL_ANALYSIS_OPTIMAL

MCP/current textual binding map: facade owns module-level alias `execute_global_pipeline`; `execute_global_pipeline` performs a local runtime import of `build_artifact_pipeline` from `contextor.core.reporting_engine.artifact_pipeline`. Harness patched those exact consumer/runtime lookup bindings, not producer-only aliases.

Raw boundary-only warm observations (`pipeline_attribution.py`, disposable ProcessPool copy):

| run | total ms | pipeline count/ms | artifact bundle count/ms | modules/errors/extract/baseline |
|---|---:|---:|---:|---|
| 1 | 10271.290 | 1 / 3064.331 | 1 / 2208.629 | 328/0/0/0 |
| 2 | 6724.691 | 1 / 2705.813 | 1 / 1919.217 | 328/0/0/0 |
| 3 | 6786.663 | 1 / 2643.717 | 1 / 1996.001 | 328/0/0/0 |
| median | 6786.663 | 1 / 2705.813 | 1 / 1996.001 | reuse correct |

Inclusive nested timings are not summed. Stage-profile medians remain index 2058.101ms, reuse 538.502ms, persistence 410.319ms. Top-level residual after index/pipeline/reuse/persistence is about 1074ms; it is facade/report finalization and overlapping canonical stages, so it is not asserted as an independent duplicate.

>=200ms owners: index repository (required worker freshness, no equivalent producer); execute_global_pipeline (required report orchestration, no equivalent producer); build_artifact_pipeline (required report bundle/output, no fact-equivalent second producer); canonical reuse validator (required version/path/SHA/domain trust); save engine state (single revision-bound atomic snapshot). Exact equivalent producer identity proof is NO for every owner, measured removable wall 0, verdict NO_GO. No report child was separately callable from the current producer boundary without entering inner builders; artifact bundle is the lowest stable boundary.

Reuse regression controls all passed: domain 328, errors 0, fresh extractor 0, full baseline 0, parent AST total 0.

FILES_CHANGED=NONE

DIFFS=NONE

FULL_SUITE_RUN_BY_AGENT=NO

