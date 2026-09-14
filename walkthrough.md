# CPA8D_EXACT_PROFILE_TIMELINE

## STATUS

SUCCESS.

## HEAD

`40be6957a7b30820daa5cee8ccf6f064fa1fc6e0` — matches EXPECTED_HEAD.

## PROFILE_ANALYSIS_TIMELINE

| Time UTC | Domain | Event | Operation | Details |
| --- | --- | --- | --- | --- |
| 21:15:52.938 | MCP | CALL_START | m-5704-5 | tool=contextor_profile_analysis, PID 5704, TID 15244 |
| 21:15:52.947 | ANALYSIS | CANONICAL_WRITER_ADMISSION_ACQUIRED | profile-5704-6 | owner=mcp_analysis, wait_ms=0.0 |
| 21:15:52.977 | ANALYSIS | CANONICAL_WRITER_ADMISSION_RELEASED | profile-5704-6 | admission released |
| 21:15:52.977 | ANALYSIS | FULL_ANALYSIS_LEASE_ACQUIRED | profile-5704-6 | wait_ms=47.0000000204891 |
| 21:16:02.530 | ANALYSIS | FULL_ANALYSIS_STAGE_END | profile-5704-6 | stage=identity_and_setup, elapsed_ms=9546.999999962281 |

## COMPLETED_STAGES

- identity_and_setup: 9546.999999962281 ms

## LAST_COMPLETED_STAGE

`identity_and_setup`, 9546.999999962281 ms.

## INDEX_EVIDENCE_IF_PRESENT

Absent.

## LINEAGE_EVIDENCE_IF_PRESENT

Absent.

## FULL_ANALYSIS_TERMINAL

Absent: no `FULL_ANALYSIS_BODY_END` or `FULL_ANALYSIS_END` exists for `profile-5704-6`.

## MCP_TERMINAL

Absent: only MCP `CALL_START` exists for `m-5704-5`; no `IMPLEMENTATION_END`, `DIAGNOSTICS_END`, `TELEMETRY_END`, `CALL_END`, or `CALL_FAIL` exists.

## OS_LOCK_STATE

`OS_LOCK_HELD_BY_OTHER_PROCESS=true`.

## OWNER_PROCESS_STATE

Lease metadata identifies `owner=mcp_analysis`, PID 5704, and token `db07cd5803874e95864c6001f372851b`. PID 5704 is alive at the matching process start identity `134338937640301652`; image: `C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe`.

## CLASSIFICATION

`ANALYSIS_STILL_RUNNING`.

## IMPLICATION

CPA8B passed identity/setup; it must not be labelled as a hang in that phase. The previous absence of stages was caused by filtering ANALYSIS events on `owner`, a field stage events do not carry. No profile, analysis, update, test, restart, or code change was performed.

