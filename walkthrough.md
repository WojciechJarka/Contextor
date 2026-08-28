# Contextor runtime LIVE/MCP JSONL trace logger — architectural reconnaissance

Scope: discovery and impact analysis only. No production, test, documentation, or runtime changes were made. No restart, `analyze_project`, `update_file`, or pytest was run.

Contextor MCP was used for architecture, source spans, symbol ownership, callers/consumers, and covering-test discovery. Textual search was used only to confirm literal symbols and paths. Current LIVE canonical evidence reported revision `4449`; `get_project_architecture` returned `data_source=live_canonical_state`, `module_count=314`, and the MCP documentation/tool inventory reports 25 tools.

DESKTOP_SESSION_OWNER={
    FILE: C:\\Temp\\Contextor_Repo\\contextor\\__main__.py
    SYMBOL: main -> _run_gui; ContextorGUI.__init__
    INIT_POINT: contextor.__main__.main dispatches `--gui` to `_run_gui`; ContextorGUI.__init__ creates the Tk controller, loads state, and creates LIVE client/watcher fields. GUI startup calls configure_program_log().
    SHUTDOWN_POINT: ContextorGUI shutdown/close path in contextor/ui/gui.py calls close_cmd_log(); DesktopLiveWatcher.stop() is the watcher lifecycle release.
}

CONTEXTOR_ROOT_OWNER={
    FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\paths.py
    SYMBOL: package_root(), state_dir(), repo_cache_dir()
    EXISTING_LOGS_PATH: state_dir() / "logs" / "contextor-program.log" via program_log_path(); Windows default is `%APPDATA%\\Contextor` unless CONTEXTOR_STATE_DIR overrides it
}

PROCESS_BOUNDARIES={
    DESKTOP: contextor.__main__.main -> _run_gui -> ContextorGUI; Tkinter GUI process owning DesktopLiveWatcher and DesktopLiveEventFeed.
    MCP: contextor.mcp_main.main -> contextor.mcp_server.main; separate MCP stdio/server process with central registration and wrapper telemetry.
    LIVE: contextor.core.live_state.runtime.main -> run_service; separate localhost multiprocessing.connection service owning CanonicalLiveServer, canonical state, revision, and journal.
}

Existing cross-process metadata: LIVE IPC exposes LIVE_PROTOCOL_VERSION=3, endpoint host/port/authkey, revision, activity_seq/seq, timestamp, origin/source, operation, status, and optional file_path/error fields. Desktop and MCP clients connect through LiveStateClient; watcher updates use origin `desktop_watcher`.

ACTIVE_TRACE_DISCOVERY_CANDIDATES=[
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\watcher.py, SYMBOL: DesktopLiveWatcher.__init__/start/poll_once/_handle_poll_error/stop, ROLE: filesystem scan, coalescing/startup reconciliation, update submission, status/error outcome},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py, SYMBOL: CanonicalLiveServer._record_event/request/publish, ROLE: authoritative revision/activity event journal and IPC boundary},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\runtime.py, SYMBOL: run_service/connect/connect_or_start, ROLE: LIVE process lifecycle and client/server startup},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\mcp_server.py, SYMBOL: _instrument_mcp_tool and registration, ROLE: central MCP-call timing/success/error telemetry},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\program_log.py, SYMBOL: program_log_path/configure_program_log/emit_program_log/log_program_event, ROLE: existing process-wide plain-text stdout/stderr mirror},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\ui\\gui.py, SYMBOL: ContextorGUI.__init__/_run_test_suite/analyze/shutdown path, ROLE: Desktop session and UI integration},
]

LIVE_INSTRUMENTATION_POINTS=[
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\watcher.py, SYMBOL: DesktopLiveWatcher.poll_once, EVENT: scan/ping, changed-path detection, update start/end/failure and final changed list, REV_AVAILABLE: returned through update response/event feed, ACTIVITY_SEQ_AVAILABLE: returned by LIVE event journal, PATH_AVAILABLE: YES},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\watcher.py, SYMBOL: DesktopLiveWatcher._emit, EVENT: human-readable watcher status/error, REV_AVAILABLE: only when response-derived, ACTIVITY_SEQ_AVAILABLE: NO direct field, PATH_AVAILABLE: embedded when applicable},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py, SYMBOL: CanonicalLiveServer._record_event, EVENT: LIVE_STATE and MCP_CALL event append, REV_AVAILABLE: YES (`canonical_revision`, `revision`), ACTIVITY_SEQ_AVAILABLE: YES (`seq`), PATH_AVAILABLE: YES when result/request carries file_path},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py, SYMBOL: CanonicalLiveServer.publish, EVENT: publish request boundary, REV_AVAILABLE: YES via server revision/result, ACTIVITY_SEQ_AVAILABLE: YES after record_event, PATH_AVAILABLE: state-dependent},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\mcp\\runtime.py, SYMBOL: publish_live_status, EVENT: MCP status publication, REV_AVAILABLE: via LIVE client event, ACTIVITY_SEQ_AVAILABLE: via LIVE journal, PATH_AVAILABLE: not guaranteed},
    {FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\runtime.py, SYMBOL: run_service, EVENT: service startup/shutdown boundary, REV_AVAILABLE: YES after server initialization, ACTIVITY_SEQ_AVAILABLE: initial/retained server state, PATH_AVAILABLE: repository root},
]

Watcher coalescing has no separate named debounce callback: it is embodied by `poll_once()` comparing `_snapshot`, `_startup_pending`, and the current scan. Authoritative revision/activity publication is owned by `CanonicalLiveServer._record_event`; lease/publication internals remain below the analysis/facade/coordinator path.

MCP_INSTRUMENTATION_OWNER={
    FILE: C:\\Temp\\Contextor_Repo\\contextor\\mcp_server.py
    SYMBOL: _instrument_mcp_tool
    CENTRAL_FOR_ALL_25_TOOLS: YES
    REV_AVAILABLE_WITHOUT_EXTRA_WORK: YES when wrapper reads LIVE-backed response/diagnostics; wrapper is not canonical revision owner
    TIMING_AVAILABLE: YES
}

CANONICAL_REVISION_OWNER={FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py, SYMBOL: CanonicalLiveServer._revision and publish/request handling}
ACTIVITY_SEQUENCE_OWNER={FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py, SYMBOL: CanonicalLiveServer._activity_seq and _record_event}

Revision is canonical-state revision. `_record_event` stores it as `canonical_revision` for LIVE_STATE events and also exposes current server `revision`. Activity sequence is a separate monotonic journal sequence incremented for recorded LIVE/MCP events.

EXISTING_LOGGING={
    FACILITY: contextor.core.program_log
    FILE: C:\\Temp\\Contextor_Repo\\contextor\\core\\program_log.py
    PATH_OWNER: program_log_path() -> state_dir()/logs/contextor-program.log
    CONFIGURATION: configure_program_log() mirrors stdout/stderr process-wide through _TeeStream and emits a startup line
    STRUCTURED_JSONL: NONE found
    STD_LOGGING: one direct logging.getLogger(...).info call in contextor/core/live_state/runtime.py; no global FileHandler/RotatingFileHandler configuration found
}

GUI_TEST_SUITE_LOCATION={
    FILE: C:\\Temp\\Contextor_Repo\\contextor\\ui\\gui.py
    SYMBOL: ContextorGUI.__init__ (button), ContextorGUI._run_test_suite, ContextorGUI.run_test_suite
    OPEN_FOLDER_HELPER: contextor.ui.system_actions.handle_open_output_folder is imported; no dedicated test-log open-folder helper found
    TOOLTIP_MECHANISM: HeaderTooltipManager.bind_tooltip; tooltip says “Run Contextor's complete test suite, including LIVE tests.”
}

GUI execution delegates to contextor.ui.test_runner.run_test_suite, which launches pytest in a separate interpreter and streams output to the GUI log box.

FOCUSED_TESTS=[
    C:\\Temp\\Contextor_Repo\\tests\\test_live_desktop_integration.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_live_watcher_startup_reconciliation.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_live_activity_status.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_live_state_ipc.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_live_e2e_corrections.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_live_job_object.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_program_log.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_gui_live_startup.py,
    C:\\Temp\\Contextor_Repo\\tests\\test_test_runner.py,
]

The focused list is grounded in Contextor `tests_covering` results for watcher, IPC, runtime, GUI, and program-log owners plus direct source confirmation.

EXACT_PRODUCTION_FILES_LIKELY_TOUCHED=[
    C:\\Temp\\Contextor_Repo\\contextor\\core\\program_log.py,
    C:\\Temp\\Contextor_Repo\\contextor\\core\\paths.py,
    C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\watcher.py,
    C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\ipc.py,
    C:\\Temp\\Contextor_Repo\\contextor\\core\\live_state\\runtime.py,
    C:\\Temp\\Contextor_Repo\\contextor\\mcp_server.py,
    C:\\Temp\\Contextor_Repo\\contextor\\ui\\gui.py,
    C:\\Temp\\Contextor_Repo\\contextor\\ui\\test_runner.py,
]

ARCHITECTURAL_BLOCKERS=NONE. Existing logging is plain-text and the LIVE journal is already JSON-safe/in-memory, so ownership boundaries are identifiable. Retention/rotation and cross-process append coordination remain unspecified repository policies.

FILES_CHANGED=NONE
TESTS_RUN=NONE
RESTART_REQUIRED=NO

---

# Compact LLM-friendly LIVE/MCP runtime JSONL trace — implementation closure

TRACE_SCHEMA=contextor-runtime-trace/v1
TRACE_DIRECTORY=package_root()/logs
ACTIVE_POINTER=package_root()/logs/contextor_runtime_active.json
TRACE_FILENAME_EXAMPLE=contextor_runtime_YYYYMMDD_HHMMSS_mmm_<desktop-pid>.jsonl
HEADER_RECORD_COUNT=5
HEADER_IS_VALID_JSONL=YES
LEGEND_SELF_DOCUMENTING=YES
CROSS_PROCESS_SESSION_DISCOVERY=active pointer with atomic replacement and 100ms process-local refresh cache
CROSS_PROCESS_APPEND_STRATEGY=single binary append write per JSONL record (O_APPEND semantics)
MULTIPROCESS_APPEND_VALID_JSON=YES (focused multiprocess append test passed)
TRACE_FAILURE_IS_NON_FATAL=YES
TRACE_PERFORMS_LIVE_IPC=NO
TRACE_READS_CANONICAL_STATE=NO
TRACE_CALCULATES_REVISION=NO
TRACE_MUTATES_REVISION=NO
TRACE_MUTATES_ACTIVITY_SEQ=NO

LIVE_TRACE_EVENTS_IMPLEMENTED=[FS_CHANGE_DETECTED,WATCH_UPDATE_START,WATCH_UPDATE_END,WATCH_UPDATE_FAIL,UPDATE_RECEIVED,CLONE_END,UPDATER_START,UPDATER_END,UPDATER_FAIL,ENGINE_READY,INCREMENTAL_END,SNAPSHOT_SAVE_END,FILE_STATE_SAVE_END,CANONICAL_COMMIT,UPDATE_PUBLISHED,PUBLISH_RECEIVED,CANONICAL_PUBLISH,ACTIVITY_APPEND,SERVICE_START,SERVICE_END]
MCP_TRACE_EVENTS_IMPLEMENTED=[CALL_START,IMPLEMENTATION_END,DIAGNOSTICS_END,TELEMETRY_END,CALL_END,CALL_FAIL]
GUI_TRACE_EVENTS_IMPLEMENTED=[EVENT_BATCH_RECEIVED,ACTIVITY_GAP,STATUS_QUEUED,STATUS_RENDERED]
TRACE_OP_PROPAGATION=PASS
REVISION_TRANSITION_TRACE=PASS
ACTIVITY_SEQ_TRACE=PASS
GUI_MCP_LOGS_BUTTON=PASS
GUI_MCP_LOGS_TOOLTIP=Open the folder containing LIVE and MCP operation logs.
GUI_1250MS_CADENCE_CHANGED=NO
MCP_TOOL_COUNT=25
MCP_WRAPPER_IDENTITY=PASS (functools.wraps preserved)
MCP_DOCS_CHANGE=NO

TRACE_1000_EVENT_MIN_US=510.89
TRACE_1000_EVENT_MEDIAN_US=677.60
TRACE_1000_EVENT_P95_US=1243.24
TRACE_1000_EVENT_MAX_US=35568.63
TRACE_1000_EVENT_BYTES=157569
TRACE_NO_ACTIVE_SESSION_MEDIAN_US=3.91
TRACE_NO_ACTIVE_SESSION_MAX_US=919.11

TESTS_RUN=tests/test_runtime_trace.py; tests/test_mcp_diagnostics.py; tests/test_program_log.py; tests/test_gui_live_startup.py; tests/test_live_desktop_integration.py; tests/test_live_watcher_startup_reconciliation.py
TESTS_PASSED=52
TESTS_FAILED=0 in requested focused sets
ADDITIONAL_RUN_NOTE=An earlier combined run also exposed two pre-existing Windows process-termination failures in tests/test_live_state_ipc.py; no production trace failure was involved and those tests were not changed.
MANUAL_MCP_RESTART_REQUIRED=YES
MANUAL_DESKTOP_LIVE_RESTART_REQUIRED=YES
FILES_CHANGED_THIS_TASK=contextor/core/runtime_trace.py; contextor/core/paths.py; contextor/__main__.py; contextor/core/live_state/watcher.py; contextor/core/live_state/ipc.py; contextor/core/live_state/runtime.py; contextor/mcp_server.py; contextor/ui/gui.py; contextor/ui/system_actions.py; tests/test_runtime_trace.py
COMPLETE_RAW_DIFFS=available via git diff for the files above (walkthrough excluded)
VERDICT=IMPLEMENTATION_PASS_STATIC_ONLY_RESTART_REQUIRED
RUNTIME_FRESHNESS=PASS
R0=4449
R1=4449
FIRST_CALL_MS=113
WARM_INDIVIDUAL_MS=[132,111,114,102,105,92,102,83,100,90]
WARM_MEDIAN_MS=102
REPEATED_COLD_REBUILD_PATTERN=NO
RESPONSE_SEMANTIC_VALID=YES
DIAGNOSTICS_SUMMARY_PRESENT=YES (11/11 responses)
CANONICAL_MUTATION_FROM_QUERY=NO
LIVE_ERROR_DETECTED=NO
OWNER_TEMPORARILY_UNREACHABLE=NO
ACTIVITY_GAP_DETECTED=NO (post-test continuity=continuous, resync_required=false)
FILES_CHANGED=NONE

Runtime evidence came from the running MCP server after restart: Contextor returned the current `get_module_context` implementation with workspace sync verified and canonical revision 4449. The first measured call was 113 ms; the ten immediate repeats ranged from 83 to 132 ms, with a 102 ms median. All responses contained valid module/metrics/state-freshness fields and diagnostics_summary.
