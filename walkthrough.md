# CPA_GUI_RESTART_BACKEND_CANCELLATION_GATE

STATUS=SAFE_NO_CODE_CHANGE
CANCELLATION_VERDICT=RESTART_TASK_IS_EFFECTIVELY_NON_CANCELLABLE

## CONTEXTOR_EVIDENCE

- Full `contextor.ui.progress_widget::run_with_progress` fetched with `mode="fetch"`, `include=["implementation"]`; implementation is complete, `canonical_state=fresh`, `workspace_sync=verified`, `canonical_revision=1606`, provenance `live`.
- Full `contextor.ui.gui::ContextorGUI._restart_backend` fetched at the same verified revision. It passes `stop_button=self.stop_btn`; its task accepts `progress_callback` but does not call it or inspect `progress_bar.is_cancelled`.
- `ContextorGUI.stop_analysis` (`contextor/ui/gui.py:567-569`) only assigns `self.progress_bar.is_cancelled = True`.
- `_setup_actions` (`contextor/ui/gui.py:421-476`) binds the shared Stop button to `stop_analysis`.
- The GUI operations that also use `run_with_progress` (`_run_test_suite`, `analyze`, `analyze_layer`, `analyze_single`) reset `progress_bar.is_cancelled = False` before starting. The restart callback also resets it before dispatch.

## LITERAL_EXECUTION_PATH

`ContextorGUI._restart_backend` (`contextor/ui/gui.py:683-790`) sets the cancellation flag to false and calls `run_with_progress` with the lifecycle task and shared Stop button.

`run_with_progress` (`contextor/ui/progress_widget.py:132-315`) disables the requested busy buttons and enables `stop_button`. Clicking Stop invokes `stop_analysis`, which sets the flag only. The worker introspects the restart task and supplies a `progress_callback`; that callback would return false after the flag is set, but the restart task never invokes it. `run_with_progress` does not poll the flag independently, interrupt the worker, or inspect the flag after the task returns.

Therefore a Stop click during restart does not interrupt `get_backend_status`, `stop_backend`, stopped-state confirmation, or `start_backend`. A normal task return enters the worker's `else` branch, sets `task_done`, and queues `finish_success` with `root.after`. The cancellation terminal branch is entered only if the task raises `AnalysisCancelled`; this restart task has no such raise/checkpoint. The stop flag alone cannot skip `on_success` or display the cancelled result.

The progress display and busy-button states are reset only inside terminal UI callbacks after the task body has returned or raised. Thus they cannot be restored while the backend lifecycle task is still executing. The returned `task_done` event is set before the queued UI callback, but `_restart_backend` does not use it to restore UI state.

The flag remains true after a Stop click and successful restart because `reset_progress_display` does not clear it. This does not change the restart result; the current GUI operation entry points reset the flag before their next run.

## VERIFICATION

- Focused pytest command: `& .\.venv\Scripts\python.exe -m pytest tests/test_gui_backend_restart.py tests/test_progress_widget.py`
- Result: 15 passed, 1 Authlib deprecation warning.
- In-memory targeted Stop reproduction exercised the actual `_restart_backend` callback and `run_with_progress` with a deterministic inline worker. It set the shared cancellation flag during the task and observed, in order: Stop flag set, `stop_backend`, stopped confirmation, `start_backend`, progress reset, success UI callback. Result: PASS. No repository file was written by this reproduction.
- No full repository pytest suite was run.

## RESULT

The current path does not produce the suspected GUI-versus-lifecycle divergence: Stop is ignored by this task, the lifecycle completes, and success/error is reported only after its terminal result. Based on the requested gate, no source or test change is needed.

FILES_CHANGED=NONE
DIFFS=NONE
REPORT_ONLY=walkthrough.md
