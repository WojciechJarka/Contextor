# CONTEXTOR PY315-M6A — production cutover readiness certification

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP was used first; the requested backend, autostart, LIVE and interpreter-selection implementations were inspected, with canonical revision 960, `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning. Production HEAD `fc9b090f93670287beed964ab7c6bf8eb1f8fead`, clean worktree before this report. Clone HEAD `325537c80fa832b7c7f3a4e7081017861f209d30`, one intended uncommitted correction in `tests/test_full_analysis_coordination.py`; HEADs are **not equal**. The production commit changed only that test and `walkthrough.md` relative to clone HEAD. Corrected test files are byte-identical, SHA-256 `7691552083FF026DD843480EFA61AFBB2720B2F73562E0E2A14EB082AA7EBBA0`. Production Python 3.10.9, clone Python 3.15.2. External resolved lock has 66 exact pins. No production source/test changes were made in M6A.

## GLOBAL_PY315_REGRESSION_CERTIFICATION

DIRECT_EVIDENCE: `C:\Temp\Contextor_PY315_M2_Lab\M5B_final_py315.log` ends with `5388 passed, 66 skipped, 2 warnings in 1199.97s (0:19:59)`. The supplied M6A baseline reports pytest exit code 0 and 0 failures/errors; the log itself records the summary but not an exit-code marker. The 66 skips are 64 optional CPython 3.11–3.14 cases, one POSIX permission case, and one Windows symlink privilege case. Full pytest was not rerun.

## PRODUCTION_BACKEND_IDENTITY

DIRECT_EVIDENCE from read-only `get_backend_status()`: `state=running`, `ready=True`, authenticated MCP readiness confirmed. Record: PID 14936, creation identity `134379138541765783`, instance ID `5ad2b7badf6144859991659bc1393720`, executable `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe`, endpoint `127.0.0.1:8765`. Windows process inspection confirmed PID 14936, parent venv redirector PID 14164, same creation time and executable. Postcheck returned the same PID/creation identity and port 8765 owner. Credentials were not included in this report.

## DESKTOP_LIVE_WORKER_SNAPSHOT

DIRECT_EVIDENCE: Desktop GUI actual owner PID 1700, parent venv redirector 8008, actual executable Python 3.10.9; desktop claim gives process-start identity `134379138581424181` and desktop instance `76a9ad28a2df4d52b9af0cb4836dc597`. Production LIVE actual PID 2372, parent redirector 14308, Python 3.10.9; service instance `512bcf24b6f44bbf9c6321d86ce3d026`, process-start identity `134379138620751313`, lease generation 63 and status `active`. Production LIVE endpoint file identifies PID 2372, host `127.0.0.1`, port 52355, same service instance/generation/start identity. No bearer or owner token was disclosed. Eight `.contextor/mcp_processes/mcp-server-*.json` records exist, but their recorded PIDs were absent; no live worker identity was established from those records. Other visible production-venv redirector/actual pairs include two synthetic LIVE services for user-temp pytest repos (7872/1364 and 14612/8972). Process counts in this observed production-root class inventory: backend 1 redirector + 1 actual, Desktop GUI 1 + 1, production LIVE 1 + 1, residual pytest LIVE 2 + 2, live registered MCP workers 0 confirmed; 10 Python processes total in these classes. Separate clone-owned pytest LIVE processes were outside this production-root count. This snapshot is time-bound; a port or record alone does not prove process ownership without identity correlation.

## AUTOSTART_STATUS

DIRECT_EVIDENCE: read-only `get_backend_autostart_status()` returned `installed=True`, `command_matches=True`. Redacted registered command contains no credential: `C:\Temp\Contextor_Repo\.venv\Scripts\pythonw.exe -u -X utf8 -m contextor.mcp_backend_autostart launch`. `_pythonw_path()` derives that canonical production `.venv` path; no registry write occurred.

## OLD_TEST_DIRECTORY_LOCK

DIRECT_EVIDENCE: `C:\Temp\ctx315full\test_protocol_attach_ignores_b0\repo` still exists. Python 3.15 redirector PID 11908 and actual PID 10320, both created at 18:10:41, still have command lines naming that exact test repo. `openfiles /query` could not inspect local handles (`maintain objects list` not enabled; access denied); Sysinternals `handle.exe` was unavailable. Therefore classification: **LOCK_OWNER_UNKNOWN**. These PIDs are direct candidates, but command-line reference does not prove an open filesystem handle or current WinError 32. No process was killed and no directory was removed. This uncertainty is separate from the 5388-PASS regression verdict.

## OFFLINE_WHEELHOUSE_MANIFEST

DIRECT_EVIDENCE: clone Python 3.15 `pip download --only-binary=:all: --find-links <existing lab wheelhouse> -r <66-pin lock>` completed with exit 0. `C:\Temp\Contextor_PY315_M2_Lab\M6A_offline_wheels` contains exactly 66 wheel files, including `pyyaml-6.0.3-py3-none-any.whl`; no sdist. Exact filename manifest:

```text
annotated_types-0.8.0-py3-none-any.whl
anyio-4.15.1-py3-none-any.whl
attrs-26.1.0-py3-none-any.whl
authlib-1.9.1-py2.py3-none-any.whl
certifi-2026.10.23-py3-none-any.whl
cffi-2.1.1-cp315-cp315-win_amd64.whl
click-8.5.0-py3-none-any.whl
colorama-0.4.6-py2.py3-none-any.whl
cryptography-50.0.2-cp315-abi3.abi3t-win_amd64.whl
cyclopts-5.3.2-py3-none-any.whl
dnspython-2.9.1-py3-none-any.whl
docstring_parser-0.18.0-py3-none-any.whl
email_validator-2.3.0-py3-none-any.whl
exceptiongroup-1.3.1-py3-none-any.whl
fastmcp-2.12.4-py3-none-any.whl
h11-0.16.0-py3-none-any.whl
httpcore-1.0.9-py3-none-any.whl
httpx_sse-0.4.3-py3-none-any.whl
httpx-0.28.1-py3-none-any.whl
idna-3.20-py3-none-any.whl
iniconfig-2.3.1-py3-none-any.whl
isodate-0.7.2-py3-none-any.whl
joserfc-1.7.7-py3-none-any.whl
jsonschema_path-0.4.6-py3-none-any.whl
jsonschema_specifications-2025.9.1-py3-none-any.whl
jsonschema-4.26.0-py3-none-any.whl
lazy_object_proxy-1.13.0-cp315-cp315-win_amd64.whl
markdown_it_py-4.2.0-py3-none-any.whl
markupsafe-3.0.4-cp315-cp315-win_amd64.whl
mcp-1.29.0-py3-none-any.whl
mdurl-0.1.2-py3-none-any.whl
more_itertools-11.2.1-py3-none-any.whl
openapi_core-0.23.1-py3-none-any.whl
openapi_pydantic-0.6.0-py3-none-any.whl
openapi_schema_validator-0.8.1-py3-none-any.whl
openapi_spec_validator-0.8.5-py3-none-any.whl
orjson-3.12.0-cp315-cp315-win_amd64.whl
packaging-26.3-py3-none-any.whl
pathable-0.5.0-py3-none-any.whl
pluggy-1.7.0-py3-none-any.whl
pycparser-3.12-py3-none-any.whl
pydantic_core-2.50.2-cp315-cp315-win_amd64.whl
pydantic_settings-2.16.2-py3-none-any.whl
pydantic-2.14.2-py3-none-any.whl
pygments-2.21.0-py3-none-any.whl
pyjwt-2.15.1-py3-none-any.whl
pyperclip-1.11.0-py3-none-any.whl
pytest-9.1.1-py3-none-any.whl
python_dotenv-1.2.4-py3-none-any.whl
python_multipart-0.0.32-py3-none-any.whl
pywin32-312-cp315-cp315-win_amd64.whl
pyyaml-6.0.3-py3-none-any.whl
referencing-0.37.0-py3-none-any.whl
rfc3339_validator-0.1.4-py2.py3-none-any.whl
rich_rst-2.2.0-py3-none-any.whl
rich-15.0.0-py3-none-any.whl
rpds_py-2026.9.1-cp315-cp315-win_amd64.whl
setuptools-69.5.1-py3-none-any.whl
six-1.17.0-py2.py3-none-any.whl
sse_starlette-3.6.0-py3-none-any.whl
starlette-1.10.0-py3-none-any.whl
typing_extensions-4.16.0-py3-none-any.whl
typing_inspection-0.4.4-py3-none-any.whl
uvicorn-0.54.0-py3-none-any.whl
watchdog-6.0.0-py3-none-win_amd64.whl
werkzeug-3.1.9-py3-none-any.whl
```

## OFFLINE_INSTALL_RESULT

DIRECT_EVIDENCE: fresh external `C:\Temp\Contextor_PY315_M2_Lab\M6A_offline_verify_venv` created with `C:\Python315\python.exe -m venv`; installation used `--no-index --find-links M6A_offline_wheels --only-binary=:all: --no-input -r requirements-resolved.txt`, exit 0. Interpreter CPython 3.15.2. `pip check`: no broken requirements. `import orjson, watchdog, mcp, fastmcp` PASS. `yaml.__with_libyaml__ == False`; setuptools 69.5.1; pytest 9.1.1. Contextor was not installed as a distribution. No Desktop/backend was executed in this venv.

## DEPENDENCY_LOCK_PARITY

DIRECT_EVIDENCE: exact line-by-line parsed lock has 66 unique pins; `importlib.metadata.version` comparison in the new offline venv found **0 mismatches**. `pip check` PASS. A first ad hoc regex check was incorrect because its character class spanned newlines; it was corrected to a strict per-line `fullmatch`, producing the 66/0 result. The offline installation, not wheel availability alone, proves the candidate set for this environment.

## FILESYSTEM_CUTOVER_READINESS

DIRECT_EVIDENCE: canonical `.venv` is `C:\Temp\Contextor_Repo\.venv` on NTFS C:, owner `DESKTOP-OC4AAGQ\DafoO`; no sibling `.venv*` backup directory currently exists. C: free space at inspection: 82,473,082,880 bytes. `pyvenv.cfg` home and running base executable point to `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64`; separate `C:\Python315\python.exe` exists. Autostart names the canonical `.venv\Scripts\pythonw.exe`. Current backend, Desktop and LIVE redirector processes reference the production `.venv`; additional pytest LIVE redirectors also reference it. **INFERENCE:** a sibling rename/backup and fresh venv at the definitive path are feasible in principle after all relevant processes have exited, but actual rename admission, handle release and rollback are REQUIRES_CUTOVER_VERIFICATION. No rename/copy was attempted. Moving a precreated venv into place was not treated as valid.

## LAUNCHER_INTERPRETER_BOUNDARIES

CODE_PATH_PROVED: `run_contextor.bat` uses `%PROJECT_DIR%\.venv\Scripts\python.exe` when present; if missing, its first bootstrap candidate is hardcoded WinPython 3.10.9. `GUI_test_suite_installer.bat` uses existing `%CD%\.venv\Scripts\python.exe`; if absent, it prefers the same 3.10.9 base. `MCP_installer.bat` selects the same 3.10.9 base before PATH when searching for Python. `_backend_python`, `_pythonw_path`, and `_project_venv_python` resolve the production repository `.venv` executables; after a fresh 3.15 venv exists there, those paths target it. The hardcoded 3.10 fallback in the BAT files is a confirmed risk of accidentally recreating a 3.10 environment if the canonical venv is absent. No launcher or installer was run or patched.

## CUTOVER_SAFETY_CONTRACT

Evidence classification for future boundaries, without executing a procedure:

| Boundary | Classification | Evidence/limit |
|---|---|---|
| A Desktop ownership stop | REQUIRES_CUTOVER_VERIFICATION | Desktop PID 1700 and claim identity are known; no stop performed. |
| B identity-checked backend stop | SUPPORTED_BY_SOURCE | `stop_backend` checks owner identity and Windows creation identity, terminates registered owner, waits for exit and cleans owned children. |
| C old backend/LIVE absence | REQUIRES_CUTOVER_VERIFICATION | Current backend/LIVE and extra pytest LIVE processes are active. |
| D intact `.venv` backup | REQUIRES_CUTOVER_VERIFICATION | Same-volume NTFS and free space support feasibility; live handles and rename remain untested. |
| E fresh 3.15 venv at canonical path | REQUIRES_CUTOVER_VERIFICATION | External fresh venv creation proved; canonical-path creation not attempted. |
| F offline-only dependency install | SUPPORTED_BY_TEST | Fresh external 3.15 venv installed all 66 pins with `--no-index`. |
| G interpreter, lock, imports | SUPPORTED_BY_TEST | Offline 3.15.2 venv, 66/0 parity, `pip check` and imports passed; production source imports after cutover remain to verify. |
| H backend interpreter/ownership | REQUIRES_CUTOVER_VERIFICATION | `_backend_python` selects canonical venv; new process identity/readiness untested. |
| I LIVE/worker interpreter parity | REQUIRES_CUTOVER_VERIFICATION | LIVE uses spawning `sys.executable`; new process tree and worker instances untested. |
| J autostart/Desktop/MCP | REQUIRES_CUTOVER_VERIFICATION | Current 3.10 autostart matches; 3.15 integrated state untested. |
| K rollback generation control | REQUIRES_CUTOVER_VERIFICATION | Identity checks exist, but stopping only new identities, restoring backup and health proof are untested. |

## ROLLBACK_SAFETY_CONTRACT

SUPPORTED_BY_SOURCE: backend stop is identity checked and refuses Windows termination without creation identity; stale records are removed without terminating an unrelated PID. REQUIRES_CUTOVER_VERIFICATION: exact new-generation process inventory, safe shutdown of Desktop/LIVE/worker processes, intact backup rename and restore, and verified 3.10 health. BLOCKED_WITH_REASON for unconditional readiness: launcher/installer missing-venv fallback still prefers hardcoded Python 3.10.9, and existing production/test LIVE redirectors remain active; an uncontrolled launcher invocation during the canonical `.venv` gap could recreate the wrong interpreter. No rollback operation was performed.

## PRODUCTION_ISOLATION

Production Python remained 3.10.9. Backend PID 14936 and creation identity `134379138541765783` unchanged; authenticated status stayed ready; port 8765 remained owned by PID 14936. Production LIVE PID 2372 and desktop PID 1700 remained present; no new production LIVE process was created by this task. Production source/test worktree remained clean. Only external wheelhouse, download/install logs and external verification venv were created. No service, process, registry, autostart, launcher, test directory, production venv, source or test mutation occurred.

## MCP_POSTCHECK

DIRECT_EVIDENCE: read-only Contextor MCP `get_module_context` for `contextor.mcp_backend_control` after external work returned canonical revision 960, `canonical_state=fresh`, `workspace_sync=verified`, advisory warning `null`. Production backend readiness remained authenticated.

## FILES_CHANGED

Inside production repository, only `C:\Temp\Contextor_Repo\walkthrough.md` was overwritten. No source/test/docs file changed. External artifacts: `C:\Temp\Contextor_PY315_M2_Lab\M6A_offline_wheels`, `M6A_offline_verify_venv`, `M6A_download.log`, `M6A_offline_install.log`.

## FULL_DIFFS

`ACTUAL_DIFF=DIFFS=NONE` for production and clone source/test/docs. `walkthrough.md` is the report and excluded from the diff requirement.

## REMAINING_UNKNOWN

Actual current handle owner and current lock state of `ctx315full` cannot be proven with available read-only handle tooling; command-line references identify candidates only. Clone HEAD differs from production HEAD though production source logic is unchanged and the corrected test bytes match. Backup rename, complete process shutdown, 3.15 backend/Desktop/LIVE/worker parity and rollback health require a future controlled cutover. The installer fallback remains hardcoded to Python 3.10 when `.venv` is absent. No credential values were intentionally included.

## FINAL_VERDICT

`BLOCKED_WITH_EXACT_EVIDENCE`: offline dependency kit and installation proof pass, and production ownership is identifiable, but unconditional cutover readiness is not certified while active production/test LIVE processes reference `.venv`, launcher/installer fallback can recreate Python 3.10 during a missing-venv interval, and the old test-directory handle owner is unverified. No cutover occurred. STOP.
