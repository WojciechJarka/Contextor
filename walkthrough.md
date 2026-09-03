# Final stage evidence

DECISION=NO_GO_FULL_ANALYSIS_OPTIMAL

MCP: facade/reuse ownership confirmed at LIVE revision 206; state fresh; continuity continuous and resync false. Harness: `C:\Temp\Contextor_Benchmarks\final_full_profile_20260903\stage_profile.py`, normal ProcessPool disposable copy, boundary-only `perf_counter_ns` wrappers, no repository mutation.

```powershell
& C:\Temp\Contextor_Repo\.venv\Scripts\python.exe C:\Temp\Contextor_Benchmarks\final_full_profile_20260903\stage_profile.py
```

Seed (not authority): 6597.120 ms. Accepted instrumented warm runs: 6979.029, 6875.196, 6745.188 ms; median 6875.196 ms. Post-profile uninstrumented validation: 6891.538 ms, 0.24% from instrumented median (<10%), so stage timing is accepted.

Reuse control each warm: module domain=328, errors=0, extraction=0, baseline=0, reuse=1, final facts/manifest current-domain contract preserved. Raw median stage rows (inclusive, do not sum): index_repository 1 / 2058.101 ms; FileStateManager.update_state 328 / 133.583 ms; FileStateManager._compute_hash 328 / 92.092 ms; build_module_usage_baseline_with_reuse 1 / 538.502 ms; save_engine_state 1 / 410.319 ms. Pipeline/report/analytics wrappers were not reached through their current imported aliases in this low-overhead harness, so no invented current owner timing is reported.

Source lifecycle: current FileState SHA=328 calls; parent `parse_source`, `Module.ast_tree`, extractor and full baseline=0 in every warm due strict reuse. The remaining index worker hash is captured in index inclusive cost. Parent AST attribution is therefore `PARENT_AST_TOTAL=0`, `UNATTRIBUTED=0`; no AST materialization remains after reuse in this run.

>=200ms audit: index_repository 2058.101ms: NO_GO, worker source/cache freshness has no exact equivalent current-run producer. reuse helper 538.502ms: NO_GO, required SHA/path/version/materialization/domain validation; no duplicate producer. save state 410.319ms: NO_GO, one revision-bound atomic persistence owner; no duplicate save. Hash/update are below 200ms; worker cache hash and FileState SHA have distinct algorithms/boundaries (cache freshness vs revision-bound SHA), hence NO_GO even if both read source. No owner has an exact equivalent producer plus measurable removable >=300ms/3% median.

History background only: 22.156s pre-fusion; 17.507s post-fusion; 14.974s profiling; 7.018s controlled strict reuse; current stage-run median 6.875s. Different harnesses are not A/B.

FILES_CHANGED=NONE

DIFFS=NONE

FULL_SUITE_RUN_BY_AGENT=NO

