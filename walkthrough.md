# CONTEXTOR PY315-M7B-R1 — runtime acceptance evidence closure

## PREFLIGHT

DIRECT_EVIDENCE: current HEAD `e766bc79e22b6d0dc56fb03d6b83b0bd408cb48a`; worktree clean before this report. Historical M7B PIDs were not reused. Fresh production identity `ctx_8efc50d8`; canonical interpreter CPython 3.15.2 AMD64, `sys.executable=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, base `C:\Python315\python.exe`, prefix canonical. Unique external audit directory `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01` was created; prior acceptance artifacts preserved. No source/test/venv/launcher changes, no pytest rerun or restart.

## MCP_DISCOVERY

Contextor MCP documentation consulted first. Fresh module contexts for `contextor.core.analysis.process_pool_lifecycle`, `contextor.core.live_state.runtime`, `contextor.core.live_state.ipc`, `contextor.mcp_backend_control`, `contextor.mcp_backend_state`, `contextor.mcp_process_registry`: canonical_state=fresh, workspace_sync=verified, revision 962, provenance=live, advisory=null. Exact source: `process_pool_lifecycle.py:295` owns `managed_process_pool` and optionally registers workers; `runtime_lease.py:693-701,937-945,1029` defines generation/lease/desktop claim; `mcp_backend_state.py:582,619` reads backend record/claim; `mcp_process_registry.py:197,229,265,319+` defines identity probe and classification. `read_records()` can remove malformed records, so G4 used direct read-only JSON parsing instead.

## G1_REAL_POOL_WORKER_IDENTITIES

**PASS.** Exact command: set child-only `PYTHONPATH=C:\Temp\Contextor_Repo;C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01`, `PYTHONDONTWRITEBYTECODE=1`, `CONTEXTOR_MCP_PROCESS_REGISTRY=C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\pool-registry`; run canonical Python `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\pool_probe.py`. `pool_worker.hold_worker` was importable under Windows spawn; script had `if __name__ == '__main__'` and `freeze_support()`. It used actual `managed_process_pool(ProcessPoolExecutor,max_workers=2)` and held both tasks until identity inspection. Worker 1: PID 13092, creation FILETIME 134382633081478971, Windows image `C:\Python315\python.exe`, parent PID 13088, CPython 3.15.2 AMD64, reported sys.executable canonical venv, sys._base_executable `C:\Python315\python.exe`, sys.prefix canonical. Worker 2: PID 11372, creation 134382633081598759, same image/version/venv/base/prefix, parent 13088. Both `state=alive` simultaneously. Parent chain for each: worker → actual probe PID 13088, creation 134382633068136630, image `C:\Python315\python.exe` → venv redirector PID 13184, image canonical `.venv\Scripts\python.exe` → pwsh 10444 → Codex 8460. The new probe proves these workers, not the historical M7B pytest worker PIDs. Full output in `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\pool-probe-result.json`.

## G1_PROCESS_CLEANUP

**PASS.** The external release marker was written after identity capture; both futures returned `released_normally=true`; context manager shut down executor. Identity probes after shutdown classified both exact worker PIDs DEAD, and test registry `pool-registry` contained zero JSON records. Probe actual PID 13088 and redirector 13184 were absent on subsequent Windows check. No forced termination, taskkill, or PID-only cleanup.

## G2_LIVE_GENERATION

**PASS.** Direct read-only parse of production generation metadata and lease at paths derived from `RuntimeDomain.from_identity` yielded domain `rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654`, generation status active, number 68, LIVE instance `8e544cd7f6544233afc93b76f75569ed`, PID 12660, creation identity 134382621995634136, endpoint fingerprint `1a6ce38fb1a4c617fcd64ef80fd34f95b00a82ff25012487759e35af143db580`. Generation and lease match each other and `matches_domain=true`. Same values before/after probe.

## G2_LEASE_AND_OWNER_CLAIMS

**PASS.** Desktop claim matches LIVE instance/generation/PID/creation and repository/domain identity. Claimed Desktop PID 10564, creation 134382621927793896; Windows identity probe reports alive, image `C:\Python315\python.exe`, exact creation match. Backend owner claim identifies same Desktop PID/creation/image/desktop instance `62557e79a7b242d4a9e5f471de2b25da` and current backend instance `754d8e4bb23e4590a23d622eb47e0893`. Authenticated `get_backend_status()` returned running/ready before and after; backend PID 11876, creation 134382621854316052, Windows image `C:\Python315\python.exe` match. Owner tokens were neither serialized nor printed. No competing owner in current production domain metadata.

## G2_REPOSITORY_AUTHORITY

**PASS.** `read_repository_identity(C:\Temp\Contextor_Repo)` returned `ctx_8efc50d8`, exact canonical root. `RuntimeDomain.from_identity(...,mode='production')`, generation and lease domain matches; Desktop claim repo/domain IDs match. MCP contexts before/post: revision 962, canonical fresh, workspace verified, live provenance, no advisory. The endpoint fingerprint equality is proved across generation/lease; independent endpoint socket metadata was not read, but MCP authenticated readiness succeeded.

## G3_ACCEPTED_DEPENDENCY_MANIFEST

**PASS.** The accepted manifest is `C:\Temp\Contextor_PY315_M2_Lab\requirements-resolved.txt`, 66 `name==version` entries. M7A-R5 migration journal `...\M7A_R5_runtime_switch\migration.journal.jsonl` records `dependency_parity=pass_66_of_66`; pip install log points to that exact manifest. Manifest SHA-256 `f242ad55febb7c732900a8b7f7fb27ffc027631b2ac33f79be851b76dc617d00`. Its direct requirements source is `requirements-direct.txt`. This is historical baseline attribution, not a newly invented lock.

## G3_EXACT_PIN_COMPARISON

**PASS.** Read-only `importlib.metadata.distributions()` comparison with normalized names: required 66, installed 67, matched 66, missing 0, mismatches 0; only extra distribution `pip==26.2.2`, outside manifest scope. `python -m pip check` exit 0, `No broken requirements found.` Exact command: canonical Python `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\dependency_parity.py`; result `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\dependency-parity.json`. No install or reconfiguration.

## G4_REGISTRY_AUTHORITY

**PASS for current registered-child state.** Active authoritative path came from authenticated backend record: `C:\Users\DafoO\AppData\Roaming\Contextor\mcp_backend\processes` (case-insensitive Windows path). Directory exists; direct `*.json` read-only enumeration returned zero records before and after. Thus no active registered child record, historical record, malformed record or record identity mismatch existed in that exact directory at observation. Empty directory alone does not prove all possible future registrations; the current backend record bound the location. Desktop-owned spawn workers, if any, are not presumed backend registered children.

## G4_PROCESS_IDENTITY_COMPARISON

Backend record instance/PID/creation/image matches Windows; backend host claim matches Desktop; LIVE lease and Desktop claim match actual Windows process identities. With zero current production registry records, record-by-record child classification is vacuous and no PID was deleted or terminated. Isolated G1 worker registry was separate and empty after normal shutdown.

## PRODUCTION_HEALTH_BEFORE_AFTER

Before/after authority snapshots at `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01\authority.before.json` and `authority.after.json`: identical backend 11876, Desktop 10564, LIVE 12660 by PID, creation identity and Windows image; backend instance unchanged and authenticated/ready, LIVE generation 68 unchanged, lease/claims/domain/repo unchanged. Postprobe MCP module contexts fresh/verified/live at revision 962, advisory null. No production restart or authority replacement observed.

## PROCESS_COUNTS_BEFORE_AFTER

Each snapshot listed eight Python/venv processes whose command line referenced Contextor_Repo: the six stable production actual/redirector processes plus one transient external `other` pair. The external `other` pair differed between snapshots (before 8428/13788, after 7824/13896); it was outside the backend/Desktop/LIVE parent chains and absent on later query. Its owner was not established, so it is not counted as production or as a G1 leak. Exact production count remained six; G1 worker PIDs 13092/11372 and probe PID 13088/redirector 13184 exited. No unexplained production growth. Snapshot JSON contains role and process identities without command lines or tokens.

## UNEXERCISED_WORKER_TYPES

This task exercised only the two isolated real ProcessPoolExecutor workers. Historical M7B profile subprocess and targeted tests remain accepted evidence and were not repeated. Production Desktop workers' application tasks, mutation workers, crash/cancellation paths, backend restart and LIVE start/stop remain NOT_EXERCISED by M7B-R1; no claim of their certification.

## FILES_CHANGED

`walkthrough.md` only inside production repository. External evidence files and probe sources are under `C:\Temp\Contextor_PY315_M2_Lab\M7B_acceptance\M7B_R1_20261104_01`. No source, test, launcher, dependency or configuration file changed.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE for production source/test/docs/launcher/dependencies/configuration. The report's own diff is excluded under AGENTS.md.

## REMAINING_UNKNOWN

The transient external `other` Python pairs observed at different times were not attributed to a specific owner; both were outside the stable production parent chains. Their change does not affect G1-G4. No general future process-registration behavior or unexercised worker category is certified.

## FINAL_VERDICT

**PASS_PY315_M7B_RUNTIME_ACCEPTANCE**. G1 PASS: two independently observed 3.15 workers and clean normal exit. G2 PASS: live generation, lease, owner claims, repository identity and authenticated backend coherent before/after. G3 PASS: 66/66 accepted pins. G4 PASS: authoritative active registry inspected, zero current records, no mismatch. Production identities and canonical freshness remained stable. STOP.
