# CPA10K5R2_FINAL_TERMINAL_EVIDENCE_ONLY

## Scope and restrictions

This report contains only the terminal evidence for the already completed forced-close run and the requested natural shutdown of the measurement monitor/notifier. No analysis was started, no Desktop or MCP restart was performed, and no Contextor process was terminated with `taskkill` or `Stop-Process`.

SOURCE_TEST_FILES_CHANGED=NO
ANALYSIS_START=FORBIDDEN_AND_NOT_PERFORMED
DESKTOP_RESTART=NO
MCP_RESTART=NO
REPORT_SCOPE=current-task-only

Evidence paths:

```text
RAW_LOG=C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\monitor\process_events.jsonl
WORKER_SIGNAL=C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\worker\worker_signal.json
EXTERNAL_BASELINE=C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\external_mcp_before_close.json
DESKTOP_PID=11172
WORKER_PID=6168
MONITOR_PID=9452
NOTIFIER_PID=16164
```

## Phase 1 — raw process-event ordering

The raw log was read without modification. The complete literal events for PID 11172 were:

```text
{"Event":"STOP","ObservedAtUtc":"2026-09-16T19:18:06.399547Z","ProcessId":11172,"ParentProcessId":6188,"ProcessName":"python.exe","CreationDateUtc":null,"ExecutablePath":null,"CommandLine":null}
```

The complete literal events for PID 6168 were:

```text
{"Event":"START","ObservedAtUtc":"2026-09-16T19:16:01.048317Z","ProcessId":6168,"ParentProcessId":4752,"ProcessName":"conhost.exe","CreationDateUtc":"2026-09-16T19:16:01.017816Z","ExecutablePath":"C:\\Windows\\System32\\conhost.exe","CommandLine":"\\??\\C:\\WINDOWS\\system32\\conhost.exe 0x4"}
{"Event":"STOP","ObservedAtUtc":"2026-09-16T19:16:01.889960Z","ProcessId":6168,"ParentProcessId":4752,"ProcessName":"conhost.exe","CreationDateUtc":"2026-09-16T19:16:01.017816Z","ExecutablePath":"C:\\Windows\\System32\\conhost.exe","CommandLine":"\\??\\C:\\WINDOWS\\system32\\conhost.exe 0x4"}
{"Event":"START","ObservedAtUtc":"2026-09-16T19:17:39.250942Z","ProcessId":6168,"ParentProcessId":11172,"ProcessName":"python.exe","CreationDateUtc":"2026-09-16T19:17:39.196474Z","ExecutablePath":"C:\\SpiralProphet\\python\\WPy64-31090\\python-3.10.9.amd64\\python.exe","CommandLine":"\"C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe\" \"-c\" \"from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=11172, pipe_handle=1644)\" \"--multiprocessing-fork\""}
{"Event":"STOP","ObservedAtUtc":"2026-09-16T19:17:42.490941Z","ProcessId":6168,"ParentProcessId":11172,"ProcessName":"python.exe","CreationDateUtc":"2026-09-16T19:17:39.196474Z","ExecutablePath":"C:\\SpiralProphet\\python\\WPy64-31090\\python-3.10.9.amd64\\python.exe","CommandLine":"\"C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe\" \"-c\" \"from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=11172, pipe_handle=1644)\" \"--multiprocessing-fork\""}
```

The relevant worker START is an exact raw match for `worker_signal.json`:

```json
{
  "Event": "START",
  "ObservedAtUtc": "2026-09-16T19:17:39.250942Z",
  "ProcessId": 6168,
  "ParentProcessId": 11172,
  "ProcessName": "python.exe",
  "CreationDateUtc": "2026-09-16T19:17:39.196474Z",
  "ExecutablePath": "C:\\SpiralProphet\\python\\WPy64-31090\\python-3.10.9.amd64\\python.exe",
  "CommandLine": "\"C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe\" \"-c\" \"from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=11172, pipe_handle=1644)\" \"--multiprocessing-fork\""
}
```

Literal worker signal artifact:

```json
{
  "Event": "START",
  "ObservedAtUtc": "2026-09-16T19:17:39.250942Z",
  "ProcessId": 6168,
  "ParentProcessId": 11172,
  "ProcessName": "python.exe",
  "CreationDateUtc": "2026-09-16T19:17:39.196474Z",
  "ExecutablePath": "C:\\SpiralProphet\\python\\WPy64-31090\\python-3.10.9.amd64\\python.exe",
  "CommandLine": "\"C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe\" \"-c\" \"from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=11172, pipe_handle=1644)\" \"--multiprocessing-fork\"",
  "SignalAtUtc": "2026-09-16T19:17:39.266942Z"
}
```

The raw worker STOP is present:

```text
{"Event":"STOP","ObservedAtUtc":"2026-09-16T19:17:42.490941Z","ProcessId":6168,"ParentProcessId":11172,"ProcessName":"python.exe","CreationDateUtc":"2026-09-16T19:17:39.196474Z","ExecutablePath":"C:\\SpiralProphet\\python\\WPy64-31090\\python-3.10.9.amd64\\python.exe","CommandLine":"\"C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe\" \"-c\" \"from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=11172, pipe_handle=1644)\" \"--multiprocessing-fork\""}
```

Ordering:

```text
WORKER_START_UTC=2026-09-16T19:17:39.250942Z
WORKER_STOP_UTC=2026-09-16T19:17:42.490941Z
DESKTOP_STOP_UTC=2026-09-16T19:18:06.399547Z
WORKER_STARTED_BEFORE_DESKTOP_STOP=YES
WORKER_STILL_ACTIVE_AT_DESKTOP_STOP=NO
```

The worker STOP precedes the Desktop STOP by approximately 23.9 seconds. Therefore the required active-worker-at-close predicate is not satisfied.

FORCED_ACTIVE_WORKER_AT_CLOSE_GATE=BLOCKED

## Phase 2 — fresh post-close process evidence

Fresh `Get-CimInstance Win32_Process` evidence after the close and before measurement shutdown:

```text
PID 11172 = MISSING
PID 6168  = MISSING
Processes with ParentProcessId 11172 = NONE
Python/pythonw processes with contextor.core.live_state.runtime = NONE
```

The measurement processes were still alive before Phase 5:

```text
PID 9452:
  ParentProcessId=7652
  CreationDate=2026-09-16T20:48:44.30434+02:00
  Name=python.exe
  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe
  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\monitor\monitor.py C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\monitor 11172 2026-09-16T18:44:44.5522730Z

PID 16164:
  ParentProcessId=13832
  CreationDate=2026-09-16T21:04:34.883068+02:00
  Name=python.exe
  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe
  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\notifier.py
```

DESKTOP_GUI_AFTER_CLOSE=DEAD
CAPTURED_FORCED_WORKER_AFTER_CLOSE=DEAD
DESKTOP_LIVE_SERVICE_AFTER_CLOSE=DEAD
LATE_DESKTOP_CHILD_AFTER_CLOSE=NONE

## Phase 3 — strict external MCP identity comparison

The baseline was read from:

```text
C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\external_mcp_before_close.json
```

Literal baseline metadata:

```text
CapturedAtUtc=2026-09-16T18:47:53.6554776Z
RepoPath=C:\Temp\Contextor_Repo
SelectionRule=literal CommandLine containing -m contextor.mcp_server
ProcessCount=32
Identity=(PID + CreationDateUtc + ExecutablePath + CommandLine)
```

The following are the 32 baseline identities. Every row matched the current process table on the full identity tuple, not only on PID:

```text
PID=4700   CreationDateUtc=2026-09-16T16:16:21.4332300Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=10116  CreationDateUtc=2026-09-16T16:16:21.4617890Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=12208  CreationDateUtc=2026-09-16T16:16:23.4011190Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=11316  CreationDateUtc=2026-09-16T16:16:23.4218230Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=13724  CreationDateUtc=2026-09-16T16:36:52.0120730Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=10452  CreationDateUtc=2026-09-16T16:36:52.0258140Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=3496   CreationDateUtc=2026-09-16T16:52:44.0803100Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=436    CreationDateUtc=2026-09-16T16:52:44.1306960Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=15460  CreationDateUtc=2026-09-16T17:02:57.0447170Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=2324   CreationDateUtc=2026-09-16T17:02:57.1866890Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=12912  CreationDateUtc=2026-09-16T17:08:14.3435260Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=14756  CreationDateUtc=2026-09-16T17:08:14.5012450Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=8412   CreationDateUtc=2026-09-16T17:17:34.0658720Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=8068   CreationDateUtc=2026-09-16T17:17:34.0950930Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=13224  CreationDateUtc=2026-09-16T17:25:52.3364090Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=5864   CreationDateUtc=2026-09-16T17:25:52.3530190Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=7444   CreationDateUtc=2026-09-16T17:32:32.9885890Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=6724   CreationDateUtc=2026-09-16T17:32:33.0049640Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=4848   CreationDateUtc=2026-09-16T17:38:40.9889050Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=12776  CreationDateUtc=2026-09-16T17:38:41.0300920Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=1540   CreationDateUtc=2026-09-16T17:51:22.2656010Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=9640   CreationDateUtc=2026-09-16T17:51:22.2874210Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=7580   CreationDateUtc=2026-09-16T18:04:43.4954730Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=11216  CreationDateUtc=2026-09-16T18:04:43.5576670Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=3800   CreationDateUtc=2026-09-16T18:12:56.7122130Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=11292  CreationDateUtc=2026-09-16T18:12:56.7590390Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=15312  CreationDateUtc=2026-09-16T18:25:46.0373900Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=13244  CreationDateUtc=2026-09-16T18:25:46.3193610Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=14340  CreationDateUtc=2026-09-16T18:35:54.9695310Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=4804   CreationDateUtc=2026-09-16T18:35:55.2297420Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
PID=9548   CreationDateUtc=2026-09-16T18:42:58.0168550Z  ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe                         CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server                         SAME_IDENTITY_ALIVE=YES
PID=6660   CreationDateUtc=2026-09-16T18:42:58.1235000Z  ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe  CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server  SAME_IDENTITY_ALIVE=YES
```

MATCH_COUNT=32
BASELINE_COUNT=32
PREEXISTING_EXTERNAL_MCP_UNTOUCHED=YES

## Phase 4 — unaccounted Contextor-related Python processes

Selection for this count was Python/pythonw processes whose command line contained `contextor`, `main.py --gui`, or multiprocessing worker markers. Exclusions were limited to the 32 exact baseline MCP identities, exact measurement monitor PID 9452, and exact notifier PID 16164.

The nonzero survivors were:

```text
ProcessId=14532 ParentProcessId=9108 CreationDate=2026-09-16T19:54:36+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" C:\Users\DafoO\AppData\Local\Temp\contextor_k5r1_forced_procmon\monitor.py C:\Users\DafoO\AppData\Local\Temp\contextor_k5r1_forced_procmon 8368 2026-09-16T16:14:33.4723590Z
ProcessId=5596 ParentProcessId=9664 CreationDate=2026-09-16T20:57:41+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=11428 ParentProcessId=5596 CreationDate=2026-09-16T20:57:41+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=6072 ParentProcessId=9664 CreationDate=2026-09-16T21:07:29+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=7816 ParentProcessId=6072 CreationDate=2026-09-16T21:07:29+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=12632 ParentProcessId=9664 CreationDate=2026-09-16T21:08:07+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=11180 ParentProcessId=12632 CreationDate=2026-09-16T21:08:08+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=12204 ParentProcessId=9664 CreationDate=2026-09-16T21:08:32+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=7672 ParentProcessId=12204 CreationDate=2026-09-16T21:08:32+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=8832 ParentProcessId=9664 CreationDate=2026-09-16T21:13:43+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=8328 ParentProcessId=8832 CreationDate=2026-09-16T21:13:43+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=9896 ParentProcessId=9664 CreationDate=2026-09-16T21:20:35+02:00 Name=python.exe ExecutablePath=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe CommandLine="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" -u -X utf8 -m contextor.mcp_server
ProcessId=8732 ParentProcessId=9896 CreationDate=2026-09-16T21:20:35+02:00 Name=python.exe ExecutablePath=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe CommandLine="C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -X utf8 -m contextor.mcp_server
```

UNACCOUNTED_CONTEXTOR_PYTHON_PROCESSES=13

No unaccounted survivor was terminated because the contract forbids termination and provides no ownership authority for these identities.

## Phase 5 — natural measurement shutdown

The monitor source contract uses this sentinel path:

```text
C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\monitor\stop.flag
```

Read-only directory evidence before shutdown showed no pre-existing flag file. The canonical flag path was then created solely to request the monitor's natural exit. The notifier sentinel was created at its canonical path:

```text
C:\Users\DafoO\AppData\Local\Temp\contextor_k5r2_final\notifier.stop
```

No `taskkill` or `Stop-Process` was used. After polling for natural exit:

```text
MONITOR_9452_AFTER_STOP=MISSING
NOTIFIER_16164_AFTER_STOP=MISSING
```

Final exact PID check also showed:

```text
PID 11172 = MISSING
PID 6168  = MISSING
PID 9452  = MISSING
PID 16164 = MISSING
```

Final raw-log SHA256:

```text
986046C6BF29B12DF0B456C0F69FFFB96D1957A10E65777FAC7C0D54729DEDCD
```

## Final certifications

```text
FORCED_ACTIVE_WORKER_AT_CLOSE_GATE=BLOCKED
DESKTOP_FORCED_ANALYSIS_POOL_CLEANUP=BLOCKED
DESKTOP_GUI_AFTER_CLOSE=DEAD
DESKTOP_LIVE_SERVICE_AFTER_CLOSE=DEAD
LATE_DESKTOP_CHILD_AFTER_CLOSE=NONE
PREEXISTING_EXTERNAL_MCP_UNTOUCHED=YES
UNACCOUNTED_CONTEXTOR_PYTHON_PROCESSES=13
DESKTOP_RUNTIME_PROCESS_CERTIFICATION=BLOCKED
```

The forced-close cleanup certificate is BLOCKED, not FAIL: the captured worker was dead after close, but raw ordering proves that it had already stopped before the Desktop STOP, so the required active-worker-at-close gate was not proven. The runtime certification is also BLOCKED because the required unaccounted-process count is 13 rather than 0.

ACTUAL_DIFF=DIFFS=NONE for source/test files
STOP=Terminalny odczyt zakończony. Nie rozpoczynaj kolejnych prób K5R.
