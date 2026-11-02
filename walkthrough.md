# CONTEXTOR PY315-M7B — current runtime acceptance rerun

## PREFLIGHT

Current HEAD `0ce4899cb6c6dfe645d1df6df353dd2d67aa9511`, different from historical M7B baseline. Initial worktree clean. Existing `M7B_acceptance` contained prior artifacts, preserved; new isolated subdirectory `rerun_2026_11_02` used. No production source/test/dependency/interpreter mutation.

## PRODUCTION_RUNTIME_BASELINE

Production repo `C:\Temp\Contextor_Repo`; canonical Python 3.15.2 AMD64, sys.prefix canonical `.venv`, sys._base_executable `C:\Python315\python.exe`, pyvenv.cfg version 3.15.2. `pip check`: no broken requirements. `pip list` contained 67 installed distributions; exact 66-pin comparison was not performed. Production process snapshot in `processes.before.json`.

## MCP_DISCOVERY

Contextor MCP documentation for get_module_context read first. All 10 specified module contexts returned canonical_state=fresh, workspace_sync=verified, revision 962, provenance=live, advisory=null. Exact source verified: process_pool_lifecycle manages process-local pools; profile_worker JSON probe schema; profile tool uses async subprocess + registry; process registry identity probe; backend control authenticated readiness; LIVE runtime/IPC ownership. This is targeted ownership discovery, not a full call-graph audit.

## CANONICAL_INTERPRETER_IDENTITY

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` reports 3.15.2, sys.prefix canonical, sys._base_executable `C:\Python315\python.exe`. Windows actual production executables were `C:\Python315\python.exe`, with separate canonical venv redirectors.

## BACKEND_IDENTITY

Authenticated `get_backend_status()` before/after: state=running, ready=True, instance `a42eccc4a6fe4a89a193fae38ba6f61c`, actual PID 2900, creation identity 134379993012170631. Redirector PID 7508 -> actual PID 2900; 127.0.0.1:8765 recorded. No competing backend observed in process snapshot.

## DESKTOP_IDENTITY

Redirector PID 15872 -> actual PID 6172; actual executable `C:\Python315\python.exe`, command role main.py --gui; creation 2026-11-01 10:34:56.057216 +01:00. Same identity before/after.

## LIVE_IDENTITY

Redirector PID 15296 -> actual PID 13924; parent actual Desktop PID 6172; actual executable `C:\Python315\python.exe`; creation 2026-11-01 10:34:59.724633 +01:00. Same identity before/after. A separate pre-existing LIVE pair 9540/14216 associated with an earlier test remained untouched; it is not counted as production.

## PRODUCTION_AUTHORITY_STATE

MCP module contexts returned live/fresh/verified revision 962 before and after. Backend authenticated. Current LIVE lease generation, service instance and Desktop claim were not independently decoded in this rerun; authority coherence beyond module freshness remains UNKNOWN.

## TARGETED_TEST_SELECTION

Inspected exact eight requested test nodes. Real pool test creates two ProcessPoolExecutor workers and asserts alive then terminated. Reusable pool tests use fake executor in pytest process. HTTP runner uses ephemeral loopback port. Profile lifecycle tests patch subprocess creation. Registry test probes its own PID. Launcher guard copies scripts to pytest tmp_path and checks exit before application work. Environment paths redirected only in pytest child to unique external state/cache/output/registry/process-registry directories; `PYTHONDONTWRITEBYTECODE=1`, basetemp external, cacheprovider disabled.

## TARGETED_PYTEST_RESULTS

Exact command: canonical Python `-m pytest -q` with the eight specified node IDs, `--tb=short -p no:cacheprovider --basetemp` external. Result: **13 passed, 2 upstream Authlib warnings, 0 fail, 0 skip** in 6.42s. Seven nodes contributed one case each; `test_guarded_launcher_exits_before_application_work` contributed six parameter cases. Node results:

|Node|Result|Assertion evidence|
|---|---|---|
|tests/test_process_pool_lifecycle.py::test_real_process_pool_workers_are_force_terminated|PASS|Two executor processes alive, terminate count 2, both dead|
|tests/test_process_pool_lifecycle.py::test_reusable_process_pool_preserves_generation_between_leases|PASS|Fake executor same generation reused|
|tests/test_process_pool_lifecycle.py::test_reusable_process_pool_exception_invalidates_generation|PASS|Fake executor shutdown/invalidation|
|tests/test_mcp_persistent_http_runner.py::test_persistent_http_server_exits_normally_and_releases_ephemeral_port|PASS|Ephemeral HTTP server exits/releases port|
|tests/test_mcp_profile_worker_lifecycle.py::test_profile_worker_registers_and_removes_record|PASS|Mock registration/removal|
|tests/test_mcp_profile_worker_lifecycle.py::test_profile_worker_cancellation_uses_same_cleanup_path|PASS|Mock cancellation cleanup|
|tests/test_mcp_process_registry.py::test_probe_current_process_is_alive|PASS|Own PID identity alive|
|tests/test_py315_launcher_migration_guard.py::test_guarded_launcher_exits_before_application_work|6 PASS|Guard exit 86, no application marker|

A second run of only the real pool node yielded 1 PASS, solely to attempt actual worker PID/image capture. Evidence files `pytest.log`, `pool-identity-result.json`.

## REAL_PROCESS_POOL_EVIDENCE

The test implementation at lines 149-184 positively asserts two real ProcessPoolExecutor workers are alive and then dead; first selected run PASS and focused repeat PASS. The external WMI sampler captured pytest redirector PID 7556 and actual pytest PID 5020 (`C:\Python315\python.exe`) but did **not** capture the short-lived pool worker PIDs/images. Preexisting Desktop workers 7756/11520/6224/6684 were excluded by parent identity. Therefore `INTERPRETER_IDENTITY_NOT_PROVEN` for the two test pool workers despite lifecycle assertion PASS. No worker PID/creation/executable is invented.

## REAL_PROFILE_SUBPROCESS_PROBE

Schema verified from `core/analysis/profile_worker.py`: exact seven fields `repo_path,mode,scope,presets,samples,warmup,result_view` for probe. Synthetic repo and historical summary fixture under external workspace. First child exit 1 due missing PYTHONPATH; second exit 0 but response status failed because summary fixture absent; after adding an isolated 45-byte JSON summary, final child exit 0 and JSON response schema `contextor-atomic-profile/v1`, status=ok, successful=1, failed=0, read_bytes count=1, no FULL. Final redirector PID 18124, creation `/Date(1793656597687)/`, exe canonical venv; actual child PID 12848, creation `/Date(1793656597744)/`, exe `C:\Python315\python.exe`, parent 18124. Both dead after completion. Earlier attempts PID 7532,9788,17772 also confirmed exited. `profile-probe-result.json` holds full result. Response consistency historical_unverified is expected for reports.summary and not LIVE authority evidence.

## MCP_PROCESS_REGISTRY_BEFORE_AFTER

Production registry directory listing contained no record files before the tests; no newly visible record file after. Isolated test registry was separate. No stale record was deleted. Full record-content authority audit not performed.

## PROCESS_COUNTS_BEFORE_AFTER

Exact production snapshot comparison by PID + creation timestamp + executable returned no difference. Production: 3 actual + 3 redirectors; four existing Desktop-owned spawn workers. Separate old test LIVE pair: 1 actual + 1 redirector, unchanged. Final synthetic profile and pytest PIDs absent. No unexplained process growth. `processes.before.json` and `processes.after.json` external.

## PRODUCTION_POST_TEST_HEALTH

Authenticated backend remained same instance/PID/creation and ready. Desktop/LIVE process pairs unchanged; canonical 3.15.2 unchanged. Three MCP module contexts fresh/live/verified revision 962, advisory null after tests. No runtime restart observed. Repo identity from baseline not independently reread in final postcheck; exact LIVE lease/claim generation not independently checked.

## CANONICAL_FRESHNESS

Before and after MCP contexts for process_pool_lifecycle, contextor_profile_analysis and live_state.runtime returned canonical_state=fresh, provenance=live, revision 962, advisory=null.

## WORKSPACE_SYNC

Those three specific module contexts reported workspace_sync=verified. This does not certify unqueried files; no source/test changes were made.

## SOURCE_INTEGRITY

HEAD `0ce4899cb6c6dfe645d1df6df353dd2d67aa9511` before/after. Worktree clean before report. No source/test/launcher/dependency edits, no restart, no production cache/state mutation observed. Old Python 3.10 backup untouched.

## UNEXERCISED_WORKER_TYPES

Actual profile subprocess exercised and identity confirmed. Actual ProcessPoolExecutor test workers exercised with cleanup assertions, but interpreter image/creation identity not captured. Production Desktop-owned workers observed but no application task submitted. Production mutation worker, backend restart worker, LIVE start/stop, and crash/cancellation real subprocess paths NOT_EXERCISED; profile cancellation selected test was mocked.

## FILES_CHANGED

`walkthrough.md` only inside production repository (this report). External artifacts under `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\rerun_2026_11_02`.

## FULL_DIFFS

FULL_DIFFS=NONE for production source/test/docs; walkthrough.md report diff excluded by contract.

## REMAINING_UNKNOWN

Real pool worker actual PID/image/creation identity; exact 66/66 pin comparison (pip check passed, 67 installed distributions); LIVE generation/lease/claim and repository ID final independent check; complete production MCP registry content authority. These prevent full PASS. No evidence of process leak or runtime inconsistency.

## FINAL_VERDICT

**PARTIAL_PY315_M7B_UNEXERCISED_WORKERS**. Mandatory targeted tests and real profile subprocess passed; production process snapshot and MCP freshness stable. Real pool worker interpreter identity was not proven and some production authority details were not independently revalidated. STOP.
