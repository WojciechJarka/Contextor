# L37_L38_GATE_F_PUBLICATION_STATUS_CONTRACT

## CURRENT_HEAD

Pre-edit HEAD: `05c0672a841664e9ade586a56164b5ca83d33337`. Production and test files were clean; only the previous `walkthrough.md` report was modified.

## PRE_EDIT_CONTEXTOR_EVIDENCE

Contextor MCP documentation, symbol implementations, call context and blast radius were used first. `ContextorFacade.analyze_project`, `analyze_single_file`, `ContextorGUI._start_live_watcher_blocking`, `_request_full_analysis_recovery` and `LiveStateClient.publish` resolved at canonical revision 20 with `workspace_sync=verified`. Direct static consumers of `analyze_single_file`: CLI, MCP jobs, MCP worker, GUI and five test modules. Git/source verification followed.

## PLANNED_MODIFICATIONS_BEFORE_EDIT

- C:\Temp\Contextor_Repo\contextor\core\api\facade.py: classify FULL accepted/recovery-required distinctly and expose optional structured scoped publication result while preserving `str` return.
- C:\Temp\Contextor_Repo\contextor\ui\gui.py: handle startup `resync_required` first; wire scoped publication result to watcher/recovery decision.
- C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py: distinguish accepted recovery-required publication in completed job message; retain revision/warning pass-through.
- C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json: document new public status and accepted revision semantics.
- Focused regressions in C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py, `tests\test_gui_live_startup.py`, `tests\test_live_single_file_reuse.py`, and one focused durable MCP job/status test file selected after checking existing fixtures.

This is an intermediate source ownership checkpoint. Final results and full diffs will replace this report after implementation.
