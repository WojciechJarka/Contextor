# Stage 5A — CanonicalMutationCoordinator

STATUS=PASS
IMPLEMENTATION=COMPLETED
SCOPE=STAGE_5A_ONLY
RUNTIME_MUTATION=NONE
DESKTOP_WATCHER_MIGRATION=NOT_PERFORMED
MCP_MIGRATION=NOT_PERFORMED
FACADE_MIGRATION=NOT_PERFORMED
RUNTIME_LIFECYCLE_CHANGE=NOT_PERFORMED
PUBLIC_DOC_CHANGE=NONE
TRACE_SCHEMA_CHANGE=NONE

## IMPLEMENTATION

Stage 5A ustanawia jedną, lazy-start kolejkę canonical mutation execution w CanonicalLiveServer, bez migracji istniejących callerów. CanonicalMutationCoordinator posiada dokładnie jednego daemon workera (contextor-live-mutation-worker), FIFO job queue, bounded terminal retention oraz jawne stany queued, running, completed, failed, cancelled.

Nowe wewnętrzne operacje IPC:

- submit_update_file wykonuje szybki enqueue/ACK z job_id, queue_order i accepted_revision;
- mutation_status zwraca bezpieczny snapshot joba bez ujawniania request/internal object;
- LiveStateClient.submit_update_file i mutation_status są addytywnymi metodami wewnętrznymi;
- istniejący LiveStateClient.update_file pozostał synchroniczny i nadal deleguje do request("update_file").

Koordynator nie startuje w konstruktorze serwera. Worker powstaje przy pierwszym zaakceptowanym submit. Zamknięcie odrzuca nowe submit, anuluje queued jobs, nie anuluje aktywnego joba siłowo i wykonuje bounded join.

## LOCKING_AND_OWNERSHIP

- CanonicalLiveServer nadal jest jedynym właścicielem _state, _revision, activity journalu i canonical events.
- self._mutation_execution_lock serializuje wszystkie canonical update executions z publish.
- _execute_update_file bierze self._lock tylko do sprawdzenia availability i przechwycenia previous_state, previous_revision, expected_revision, updatera i persistera.
- Clone, updater, revision validation i persistence wykonują się poza self._lock.
- Krótka commit section ponownie bierze self._lock, sprawdza jednocześnie self._revision == previous_revision oraz self._state is previous_state, a dopiero potem wykonuje atomic swap i event construction.
- _execute_publish ma lock order mutation_execution_lock -> self._lock, więc queued update i publish nie są równoległymi writerami.
- FullAnalysisLease nie został przeniesiony do coordinatora; to jest zakres Stage 5B.
- Watcher, runtime, MCP, facade, public docs i runtime trace nie zostały zmienione.

## QUEUE_CONTRACT

submit:

- wymaga niepustego string file_path;
- kopiuje request przez dict(request);
- nadaje mu-<uuid>, monotoniczny queue_order i accepted_revision;
- nie zmienia canonical revision, activity sequence, journalu ani LIVE eventów;
- po zamknięciu zwraca canonical_mutation_queue_closed.

status:

- invalid job id zwraca invalid_mutation_job_id;
- nieznany job zwraca unknown_mutation_job;
- znany job zwraca tylko publiczny snapshot pól joba;
- response, error, start revision i final revision są dołączane wyłącznie, gdy istnieją.

Worker:

- pobiera FIFO joby;
- ustawia running i started_revision bez uruchamiania drugiego workera;
- wykonuje executor poza condition lock;
- przechwytuje wyjątki executora jako canonical_mutation_execution_failed bez śmierci workera;
- traktuje nie-OK lub malformed response jako failed;
- przycina tylko najstarsze terminal records ponad retention; queued/running nigdy nie są usuwane.

## READ_ONLY_RESPONSIVENESS

Nowe submit_update_file nie czeka na updater ani persister. Ponieważ _dispatch routuje submit/status/update/publish przed generic with self._lock, server accept loop może obsługiwać reader IPC podczas kosztownego workera.

Focused real-server test z prawdziwym serve_forever i połączeniami LiveStateClient potwierdza responsywność ping, snapshot, authority_status i get_events podczas zablokowanego updatera. Reader widzi wyłącznie ostatni committed state/revision i nie widzi niecommitted eventu.

## ATOMICITY

Zachowano dotychczasowe revision validation, COW, persistence conflict shapes, trace operation propagation, diagnostic freshness i stripping caller-supplied diagnostic_changes.

Nowa kontrola przed expose:

canonical_revision_changed_during_update jest zwracane fail-closed, gdy podczas compute/persist zmienił się revision albo identity aktywnego state. W tej gałęzi nie ma canonical update event ani diagnostic event.

Candidate pozostaje niewidoczny podczas slow persistence. Atomic swap, bounded diagnostic payload, _record_event i seq są wykonywane dopiero po successful persistence i krótkiej commit section. UPDATE_PUBLISHED oraz diagnostyczne trace events są emitowane po zwolnieniu state lock, ale wciąż w obrębie jednego mutation execution gate.

## LEGACY_COMPATIBILITY

Produkcja nadal używa istniejącego synchronicznego update_file. Nie zmieniono watcher.py, runtime.py, contextor/mcp/tools/update_file.py ani facade.py. Dzięki temu migracja callerów i przeniesienie FullAnalysisLease pozostają wyraźnie odłożone do Stage 5B.

Existing IPC tests dla bezpośredniego _dispatch({"operation": "update_file", ...}) przechodzą bez osłabiania asercji. Existing publish behavior i response/revision semantics pozostają zachowane.

## TEST_RESULTS

Wykonano:

.\.venv\Scripts\python.exe -m pytest -q tests\test_live_mutation_coordinator.py tests\test_live_state_ipc.py tests\test_live_activity_status.py tests\test_runtime_trace.py

Wynik:

145 passed, 1 warning in 111.67s

Warning jest istniejącym AuthlibDeprecationWarning z zależności FastMCP/Authlib.

Wykonano również:

.\.venv\Scripts\python.exe -m py_compile contextor\core\live_state\ipc.py tests\test_live_mutation_coordinator.py tests\test_live_state_ipc.py

Wynik: PASS.

git diff --check: PASS; Git zgłasza wyłącznie informacyjne ostrzeżenie o normalizacji LF do CRLF.

Nie wykonano full pytest, Desktop restart, real LIVE E2E, analyze_project ani MCP update_file.

## FILES_CHANGED

Zmienione w Stage 5A:

- contextor/core/live_state/ipc.py
- tests/test_live_mutation_coordinator.py

Bez zmian:

- tests/test_live_state_ipc.py
- contextor/core/live_state/watcher.py
- contextor/core/live_state/runtime.py
- contextor/mcp/tools/update_file.py
- contextor/core/api/facade.py
- contextor/mcp/docs/*
- contextor/core/runtime_trace.py

## PREEXISTING_WORKTREE_CHANGES

walkthrough.md miał modyfikację przed rozpoczęciem Stage 5A i został celowo nadpisany wymaganym raportem. Jego własny diff jest wyłączony z poniższych raw diffs. Nie wykonano reset/checkout i nie naruszono innych zmian użytkownika.

## DIFFS

PRODUCTION_FILES_CHANGED=1
TEST_FILES_CHANGED=1
REPORT_FILE_EXCLUDED=walkthrough.md
FORBIDDEN_FILES_CHANGED=NONE

Poniżej znajdują się pełne raw unified diffs każdego zmienionego pliku produkcyjnego/testowego.

## FINAL_HANDOFF

Stage 5A jest ukończony statusem PASS. Infrastruktura kolejki jest obecna, jedynym wykonawcą submitowanych queued updates jest coordinator workera, reader IPC pozostaje responsywny, commit jest atomowy, publish współdzieli writer gate, a legacy caller contract pozostaje synchroniczny. Migracja watcher/MCP/facade i ownership FullAnalysisLease nie została antycypowana ani wykonana.

## FULL_RAW_DIFFS

### contextor/core/live_state/ipc.py

```diff
warning: in the working copy of 'contextor/core/live_state/ipc.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index ee7e50f..6d4217e 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -6 +6 @@ import copy
-from collections import OrderedDict
+from collections import OrderedDict, deque
@@ -92,0 +93,2 @@ _DIAGNOSTIC_JOURNAL_LIMIT = 3
+_MUTATION_JOB_RETENTION = 256
+_MUTATION_WORKER_JOIN_TIMEOUT = 2.0
@@ -106,0 +109,198 @@ class CanonicalPersistenceConflict(RuntimeError):
+@dataclass
+class _MutationJob:
+    job_id: str
+    queue_order: int
+    request: dict[str, Any]
+    accepted_revision: int
+    state: str = "queued"
+    started_revision: int | None = None
+    final_revision: int | None = None
+    response: dict[str, Any] | None = None
+    error: str | None = None
+
+
+class CanonicalMutationCoordinator:
+    def __init__(
+        self,
+        executor: Callable[[dict[str, Any]], dict[str, Any]],
+        revision_reader: Callable[[], int],
+        *,
+        retention: int = _MUTATION_JOB_RETENTION,
+    ):
+        self._executor = executor
+        self._revision_reader = revision_reader
+        self._retention = retention
+        self._condition = threading.Condition()
+        self._queue: deque[str] = deque()
+        self._jobs: OrderedDict[str, _MutationJob] = OrderedDict()
+        self._thread: threading.Thread | None = None
+        self._accepting = True
+        self._stop = False
+        self._queue_order = 0
+
+    def _ensure_started_locked(self) -> None:
+        if self._thread is None:
+            self._thread = threading.Thread(
+                target=self._run,
+                name="contextor-live-mutation-worker",
+                daemon=True,
+            )
+            self._thread.start()
+
+    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
+        try:
+            request_dict = dict(request)
+        except (TypeError, ValueError):
+            request_dict = {}
+        file_path = request_dict.get("file_path")
+        if not isinstance(file_path, str) or not file_path:
+            return {"status": "error", "error": "invalid_file_path"}
+
+        with self._condition:
+            if not self._accepting:
+                return {
+                    "status": "error",
+                    "error": "canonical_mutation_queue_closed",
+                }
+
+            self._queue_order += 1
+            job_id = "mu-" + uuid.uuid4().hex
+            accepted_revision = int(self._revision_reader())
+            job = _MutationJob(
+                job_id=job_id,
+                queue_order=self._queue_order,
+                request=request_dict,
+                accepted_revision=accepted_revision,
+            )
+            self._jobs[job_id] = job
+            self._queue.append(job_id)
+            self._ensure_started_locked()
+            self._condition.notify_all()
+            return {
+                "status": "accepted",
+                "accepted": True,
+                "job_id": job_id,
+                "queue_order": job.queue_order,
+                "accepted_revision": accepted_revision,
+                "state": job.state,
+            }
+
+    def status(self, job_id: Any) -> dict[str, Any]:
+        if not isinstance(job_id, str) or not job_id:
+            return {"status": "error", "error": "invalid_mutation_job_id"}
+
+        with self._condition:
+            job = self._jobs.get(job_id)
+            if job is None:
+                return {
+                    "status": "error",
+                    "error": "unknown_mutation_job",
+                    "job_id": job_id,
+                }
+            response: dict[str, Any] = {
+                "status": "ok",
+                "job_id": job.job_id,
+                "queue_order": job.queue_order,
+                "accepted_revision": job.accepted_revision,
+                "state": job.state,
+            }
+            if job.started_revision is not None:
+                response["started_revision"] = job.started_revision
+            if job.final_revision is not None:
+                response["final_revision"] = job.final_revision
+            if job.error is not None:
+                response["error"] = job.error
+            if job.response is not None:
+                response["response"] = copy.deepcopy(job.response)
+            return response
+
+    def _prune_terminal_locked(self) -> None:
+        terminal = {"completed", "failed", "cancelled"}
+        while sum(job.state in terminal for job in self._jobs.values()) > self._retention:
+            for job_id, job in self._jobs.items():
+                if job.state in terminal:
+                    del self._jobs[job_id]
+                    break
+            else:
+                break
+
+    def _run(self) -> None:
+        while True:
+            with self._condition:
+                while not self._queue and not self._stop:
+                    self._condition.wait()
+                if self._stop and not self._queue:
+                    return
+                job_id = self._queue.popleft()
+                job = self._jobs.get(job_id)
+                if job is None:
+                    continue
+                if job.state == "cancelled":
+                    self._prune_terminal_locked()
+                    self._condition.notify_all()
+                    continue
+                job.state = "running"
+                job.started_revision = int(self._revision_reader())
+
+            try:
+                response = self._executor(job.request)
+            except Exception as exc:
+                response = {
+                    "status": "error",
+                    "error": "canonical_mutation_execution_failed",
+                    "detail": str(exc),
+                }
+                with self._condition:
+                    job.state = "failed"
+                    job.response = response
+                    job.error = str(exc)
+                    self._prune_terminal_locked()
+                    self._condition.notify_all()
+                continue
+
+            with self._condition:
+                if isinstance(response, dict) and response.get("status") == "ok":
+                    job.state = "completed"
+                    job.response = response
+                else:
+                    job.state = "failed"
+                    if isinstance(response, dict):
+                        job.response = response
+                        error = response.get("error")
+                        job.error = str(error) if error is not None else "canonical_mutation_invalid_response"
+                    else:
+                        job.response = {
+                            "status": "error",
+                            "error": "canonical_mutation_invalid_response",
+                        }
+                        job.error = "canonical_mutation_invalid_response"
+                final_revision = job.response.get("revision") if job.response else None
+                if isinstance(final_revision, int) and not isinstance(final_revision, bool):
+                    job.final_revision = final_revision
+                self._prune_terminal_locked()
+                self._condition.notify_all()
+
+    def close(self, *, join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT) -> None:
+        with self._condition:
+            self._accepting = False
+            self._stop = True
+            for job_id in self._queue:
+                job = self._jobs.get(job_id)
+                if job is None or job.state != "queued":
+                    continue
+                job.state = "cancelled"
+                job.error = "canonical_mutation_queue_closed"
+                job.response = {
+                    "status": "error",
+                    "error": "canonical_mutation_queue_closed",
+                    "job_id": job_id,
+                }
+            self._queue.clear()
+            self._prune_terminal_locked()
+            self._condition.notify_all()
+            thread = self._thread
+
+        if thread is not None and thread is not threading.current_thread():
+            thread.join(timeout=join_timeout)
+
+
@@ -506,0 +707,5 @@ class CanonicalLiveServer:
+        self._mutation_execution_lock = threading.Lock()
+        self._mutation_coordinator = CanonicalMutationCoordinator(
+            self._execute_update_file,
+            self._read_revision,
+        )
@@ -531,0 +737,4 @@ class CanonicalLiveServer:
+    def _read_revision(self) -> int:
+        with self._lock:
+            return self._revision
+
@@ -936,42 +1145,3 @@ class CanonicalLiveServer:
-    def _dispatch(self, request: Any) -> dict[str, Any]:
-        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
-            return {"status": "error", "error": "invalid_request"}
-        operation = request["operation"]
-
-        # Desktop authority callbacks cross the RuntimeLease/observability
-        # boundary and may synchronously emit back into record_authority_event.
-        # Dispatch them outside the server state lock.
-        if operation == "desktop_claim_status":
-            return self._dispatch_desktop_claim_status()
-        if operation == "claim_desktop":
-            return self._dispatch_claim_desktop(request)
-        if operation == "release_desktop_claim":
-            return self._dispatch_release_desktop_claim(request)
-
-        with self._lock:
-            if operation == "ping":
-                return {
-                    "status": "ok",
-                    "protocol_version": LIVE_PROTOCOL_VERSION,
-                    "revision": self._revision,
-                    "available": self._state is not None,
-                }
-            if operation == "authority_status":
-                if not self._authority_identity:
-                    return {"status": "error", "error": "authority_identity_unavailable"}
-                return {
-                    "status": "ok",
-                    "protocol_version": LIVE_PROTOCOL_VERSION,
-                    "revision": self._revision,
-                    "repo_id": self._authority_identity.get("repo_id"),
-                    "root_path": self._authority_identity.get("root_path"),
-                    "runtime_domain_id": self._authority_identity.get("runtime_domain_id"),
-                    "service_instance_id": self._authority_identity.get("service_instance_id"),
-                    "lease_generation": self._authority_identity.get("lease_generation"),
-                    "service_pid": self._authority_identity.get("service_pid"),
-                    "process_start_identity": self._authority_identity.get("process_start_identity"),
-                    "endpoint_fingerprint": self.endpoint.fingerprint(),
-                }
-            if operation == "snapshot":
-                return {"status": "ok", "revision": self._revision, "state": self._state}
-            if operation == "publish":
+    def _execute_publish(self, request: dict[str, Any]) -> dict[str, Any]:
+        with self._mutation_execution_lock:
+            with self._lock:
@@ -1031,5 +1201,4 @@ class CanonicalLiveServer:
-            if operation in {"status", "record_activity", "mcp_call"}:
-                cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
-                evt = self._record_event(operation, request, category=cat)
-                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
-            if operation == "update_file":
+
+    def _execute_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
+        with self._mutation_execution_lock:
+            with self._lock:
@@ -1041 +1209,0 @@ class CanonicalLiveServer:
-
@@ -1045,18 +1213,2 @@ class CanonicalLiveServer:
-                file_path = str(request.get("file_path", ""))
-                trace_op = _safe_trace_op(request, "u")
-                if trace_op is not None:
-                    request = {**request, "trace_op": trace_op}
-                _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
-
-                try:
-                    candidate_state = _clone_state_for_update(previous_state)
-                except Exception as exc:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
-                    return {
-                        "status": "error",
-                        "error": "canonical_state_clone_failed",
-                        "revision": previous_revision,
-                        "expected_revision": expected_revision,
-                        "detail": str(exc),
-                    }
-                _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
+                updater = self._updater
+                persister = self._persister
@@ -1064,11 +1216,5 @@ class CanonicalLiveServer:
-                # IMPORTANT: updater operates ONLY on candidate_state.
-                # It must never receive previous_state/self._state directly.
-                _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
-                updater_started = time.monotonic()
-                try:
-                    with _trace_operation_context(trace_op):
-                        result = self._updater(candidate_state, file_path)
-                except Exception as exc:
-                    _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
-                    raise
-                _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
+            file_path = str(request.get("file_path", ""))
+            trace_op = _safe_trace_op(request, "u")
+            if trace_op is not None:
+                request = {**request, "trace_op": trace_op}
+            _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)
@@ -1076,11 +1222,12 @@ class CanonicalLiveServer:
-                try:
-                    state_rev = _extract_state_revision(candidate_state)
-                except ValueError:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
-                    return {
-                        "status": "error",
-                        "error": "invalid_canonical_revision",
-                        "revision": previous_revision,
-                        "candidate_revision": _raw_state_revision(candidate_state),
-                        "expected_revision": expected_revision,
-                    }
+            try:
+                candidate_state = _clone_state_for_update(previous_state)
+            except Exception as exc:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
+                return {
+                    "status": "error",
+                    "error": "canonical_state_clone_failed",
+                    "revision": previous_revision,
+                    "expected_revision": expected_revision,
+                    "detail": str(exc),
+                }
+            _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)
@@ -1088,11 +1235,11 @@ class CanonicalLiveServer:
-                if state_rev is None:
-                    if not _bind_state_revision(candidate_state, expected_revision):
-                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
-                        return {
-                            "status": "error",
-                            "error": "canonical_revision_binding_failed",
-                            "revision": previous_revision,
-                            "candidate_revision": None,
-                            "expected_revision": expected_revision,
-                        }
-                    state_rev = expected_revision
+            # IMPORTANT: updater operates ONLY on candidate_state.
+            # It must never receive previous_state/self._state directly.
+            _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
+            updater_started = time.monotonic()
+            try:
+                with _trace_operation_context(trace_op):
+                    result = updater(candidate_state, file_path)
+            except Exception as exc:
+                _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
+                raise
+            _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))
@@ -1100,11 +1247,11 @@ class CanonicalLiveServer:
-                elif state_rev == previous_revision:
-                    if not _bind_state_revision(candidate_state, expected_revision):
-                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
-                        return {
-                            "status": "error",
-                            "error": "canonical_revision_binding_failed",
-                            "revision": previous_revision,
-                            "candidate_revision": state_rev,
-                            "expected_revision": expected_revision,
-                        }
-                    state_rev = expected_revision
+            try:
+                state_rev = _extract_state_revision(candidate_state)
+            except ValueError:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
+                return {
+                    "status": "error",
+                    "error": "invalid_canonical_revision",
+                    "revision": previous_revision,
+                    "candidate_revision": _raw_state_revision(candidate_state),
+                    "expected_revision": expected_revision,
+                }
@@ -1112,2 +1259,3 @@ class CanonicalLiveServer:
-                elif state_rev < previous_revision:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
+            if state_rev is None:
+                if not _bind_state_revision(candidate_state, expected_revision):
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
@@ -1116 +1264 @@ class CanonicalLiveServer:
-                        "error": "non_monotonic_canonical_revision",
+                        "error": "canonical_revision_binding_failed",
@@ -1118 +1266 @@ class CanonicalLiveServer:
-                        "candidate_revision": state_rev,
+                        "candidate_revision": None,
@@ -1120,0 +1269 @@ class CanonicalLiveServer:
+                state_rev = expected_revision
@@ -1122,2 +1271,3 @@ class CanonicalLiveServer:
-                elif state_rev > expected_revision:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
+            elif state_rev == previous_revision:
+                if not _bind_state_revision(candidate_state, expected_revision):
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
@@ -1126 +1276 @@ class CanonicalLiveServer:
-                        "error": "canonical_revision_discontinuity",
+                        "error": "canonical_revision_binding_failed",
@@ -1130,0 +1281 @@ class CanonicalLiveServer:
+                state_rev = expected_revision
@@ -1132,3 +1283,56 @@ class CanonicalLiveServer:
-                elif state_rev != expected_revision:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
-                    return {
+            elif state_rev < previous_revision:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
+                return {
+                    "status": "error",
+                    "error": "non_monotonic_canonical_revision",
+                    "revision": previous_revision,
+                    "candidate_revision": state_rev,
+                    "expected_revision": expected_revision,
+                }
+
+            elif state_rev > expected_revision:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
+                return {
+                    "status": "error",
+                    "error": "canonical_revision_discontinuity",
+                    "revision": previous_revision,
+                    "candidate_revision": state_rev,
+                    "expected_revision": expected_revision,
+                }
+
+            elif state_rev != expected_revision:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
+                return {
+                    "status": "error",
+                    "error": "canonical_revision_discontinuity",
+                    "revision": previous_revision,
+                    "candidate_revision": state_rev,
+                    "expected_revision": expected_revision,
+                }
+
+            # Final parity proof before commit.
+            if _extract_state_revision(candidate_state) != expected_revision:
+                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
+                return {
+                    "status": "error",
+                    "error": "canonical_revision_binding_failed",
+                    "revision": previous_revision,
+                    "candidate_revision": _raw_state_revision(candidate_state),
+                    "expected_revision": expected_revision,
+                }
+
+            if persister is not None:
+                _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
+                try:
+                    with _trace_operation_context(trace_op):
+                        persister(candidate_state, expected_revision)
+                except Exception as exc:
+                    from .store import SnapshotRevisionConflict
+
+                    status = (
+                        "canonical_persistence_revision_conflict"
+                        if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
+                        else "canonical_persistence_failed"
+                    )
+                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
+                    response = {
@@ -1136 +1340 @@ class CanonicalLiveServer:
-                        "error": "canonical_revision_discontinuity",
+                        "error": status,
@@ -1138 +1341,0 @@ class CanonicalLiveServer:
-                        "candidate_revision": state_rev,
@@ -1140,0 +1344,6 @@ class CanonicalLiveServer:
+                    persisted_revision = getattr(exc, "current_revision", None)
+                    if persisted_revision is not None:
+                        response["persisted_revision"] = persisted_revision
+                        response["resync_required"] = True
+                    return response
+                _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
@@ -1142,3 +1351,11 @@ class CanonicalLiveServer:
-                # Final parity proof before commit.
-                if _extract_state_revision(candidate_state) != expected_revision:
-                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
+            with self._lock:
+                if self._revision != previous_revision or self._state is not previous_state:
+                    _safe_trace_event(
+                        "LIVE",
+                        "UPDATE_FAIL",
+                        op=trace_op,
+                        path=file_path,
+                        rev=self._revision,
+                        status="canonical_revision_changed_during_update",
+                        expected_revision=expected_revision,
+                    )
@@ -1147,3 +1364,2 @@ class CanonicalLiveServer:
-                        "error": "canonical_revision_binding_failed",
-                        "revision": previous_revision,
-                        "candidate_revision": _raw_state_revision(candidate_state),
+                        "error": "canonical_revision_changed_during_update",
+                        "revision": self._revision,
@@ -1153,27 +1368,0 @@ class CanonicalLiveServer:
-                if self._persister is not None:
-                    _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
-                    try:
-                        with _trace_operation_context(trace_op):
-                            self._persister(candidate_state, expected_revision)
-                    except Exception as exc:
-                        from .store import SnapshotRevisionConflict
-
-                        status = (
-                            "canonical_persistence_revision_conflict"
-                            if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
-                            else "canonical_persistence_failed"
-                        )
-                        _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
-                        response = {
-                            "status": "error",
-                            "error": status,
-                            "revision": previous_revision,
-                            "expected_revision": expected_revision,
-                        }
-                        persisted_revision = getattr(exc, "current_revision", None)
-                        if persisted_revision is not None:
-                            response["persisted_revision"] = persisted_revision
-                            response["resync_required"] = True
-                        return response
-                    _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)
-
@@ -1206,8 +1395,20 @@ class CanonicalLiveServer:
-                _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=self._revision, seq=evt["seq"], status=getattr(result, "status", None))
-                origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
-                trace_common = {
-                    "repo": self._authority_identity.get("root_path"),
-                    "repo_id": self._authority_identity.get("repo_id"),
-                    "origin": origin,
-                    "diagnostic_total": len(diagnostic_delta),
-                    "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
+                committed_revision = self._revision
+                committed_seq = evt["seq"]
+
+            _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=committed_revision, seq=committed_seq, status=getattr(result, "status", None))
+            origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
+            trace_common = {
+                "repo": self._authority_identity.get("root_path"),
+                "repo_id": self._authority_identity.get("repo_id"),
+                "origin": origin,
+                "diagnostic_total": len(diagnostic_delta),
+                "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
+            }
+            for change in diagnostic_delta:
+                event_name = _diagnostic_trace_event_name(change)
+                if event_name is None:
+                    continue
+                trace_fields = {
+                    **trace_common,
+                    "diagnostic_kind": change["diagnostic_kind"],
+                    "diagnostic_key": change["diagnostic_key"],
@@ -1215,30 +1416,7 @@ class CanonicalLiveServer:
-                for change in diagnostic_delta:
-                    event_name = _diagnostic_trace_event_name(change)
-                    if event_name is None:
-                        continue
-                    trace_fields = {
-                        **trace_common,
-                        "diagnostic_kind": change["diagnostic_kind"],
-                        "diagnostic_key": change["diagnostic_key"],
-                    }
-                    if "source_path" in change:
-                        trace_fields["path"] = change["source_path"]
-                    if change["diagnostic_kind"] == "syntax":
-                        trace_fields.update(
-                            error=change["message"],
-                            line_number=change["line_number"],
-                            column_number=change["column_number"],
-                        )
-                    elif change["diagnostic_kind"] == "collision":
-                        for field in (
-                            "collision_kind",
-                            "collision_artifact_type",
-                            "collision_symbol",
-                            "collision_is_identical",
-                            "collision_nodes",
-                        ):
-                            trace_fields[field] = change[field]
-                    else:
-                        trace_fields["cycle_nodes"] = change["cycle_nodes"]
-                    _safe_trace_event(
-                        "LIVE", event_name, op=trace_op, rev=self._revision, **trace_fields
+                if "source_path" in change:
+                    trace_fields["path"] = change["source_path"]
+                if change["diagnostic_kind"] == "syntax":
+                    trace_fields.update(
+                        error=change["message"],
+                        line_number=change["line_number"],
+                        column_number=change["column_number"],
@@ -1245,0 +1424,27 @@ class CanonicalLiveServer:
+                elif change["diagnostic_kind"] == "collision":
+                    for field in (
+                        "collision_kind",
+                        "collision_artifact_type",
+                        "collision_symbol",
+                        "collision_is_identical",
+                        "collision_nodes",
+                    ):
+                        trace_fields[field] = change[field]
+                else:
+                    trace_fields["cycle_nodes"] = change["cycle_nodes"]
+                _safe_trace_event(
+                    "LIVE", event_name, op=trace_op, rev=committed_revision, **trace_fields
+                )
+
+            return {
+                "status": "ok",
+                "activity_epoch": self._activity_epoch,
+                "revision": committed_revision,
+                "result": result,
+                "seq": committed_seq,
+            }
+
+    def _dispatch(self, request: Any) -> dict[str, Any]:
+        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
+            return {"status": "error", "error": "invalid_request"}
+        operation = request["operation"]
@@ -1246,0 +1452,20 @@ class CanonicalLiveServer:
+        # Desktop authority callbacks cross the RuntimeLease/observability
+        # boundary and may synchronously emit back into record_authority_event.
+        # Dispatch them outside the server state lock.
+        if operation == "desktop_claim_status":
+            return self._dispatch_desktop_claim_status()
+        if operation == "claim_desktop":
+            return self._dispatch_claim_desktop(request)
+        if operation == "release_desktop_claim":
+            return self._dispatch_release_desktop_claim(request)
+        if operation == "submit_update_file":
+            return self._mutation_coordinator.submit(request)
+        if operation == "mutation_status":
+            return self._mutation_coordinator.status(request.get("job_id"))
+        if operation == "update_file":
+            return self._execute_update_file(request)
+        if operation == "publish":
+            return self._execute_publish(request)
+
+        with self._lock:
+            if operation == "ping":
@@ -1249 +1474,10 @@ class CanonicalLiveServer:
-                    "activity_epoch": self._activity_epoch,
+                    "protocol_version": LIVE_PROTOCOL_VERSION,
+                    "revision": self._revision,
+                    "available": self._state is not None,
+                }
+            if operation == "authority_status":
+                if not self._authority_identity:
+                    return {"status": "error", "error": "authority_identity_unavailable"}
+                return {
+                    "status": "ok",
+                    "protocol_version": LIVE_PROTOCOL_VERSION,
@@ -1251,2 +1485,8 @@ class CanonicalLiveServer:
-                    "result": result,
-                    "seq": evt["seq"],
+                    "repo_id": self._authority_identity.get("repo_id"),
+                    "root_path": self._authority_identity.get("root_path"),
+                    "runtime_domain_id": self._authority_identity.get("runtime_domain_id"),
+                    "service_instance_id": self._authority_identity.get("service_instance_id"),
+                    "lease_generation": self._authority_identity.get("lease_generation"),
+                    "service_pid": self._authority_identity.get("service_pid"),
+                    "process_start_identity": self._authority_identity.get("process_start_identity"),
+                    "endpoint_fingerprint": self.endpoint.fingerprint(),
@@ -1253,0 +1494,6 @@ class CanonicalLiveServer:
+            if operation == "snapshot":
+                return {"status": "ok", "revision": self._revision, "state": self._state}
+            if operation in {"status", "record_activity", "mcp_call"}:
+                cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
+                evt = self._record_event(operation, request, category=cat)
+                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
@@ -1389,0 +1636 @@ class CanonicalLiveServer:
+        self._mutation_coordinator.close()
@@ -1512,0 +1760,17 @@ class LiveStateClient:
+    def submit_update_file(
+        self,
+        file_path: str,
+        *,
+        origin: str = "unknown",
+        trace_op: str | None = None,
+    ) -> dict[str, Any]:
+        return self.request(
+            "submit_update_file",
+            file_path=file_path,
+            origin=origin,
+            trace_op=trace_op,
+        )
+
+    def mutation_status(self, job_id: str) -> dict[str, Any]:
+        return self.request("mutation_status", job_id=job_id)
+
```

### tests/test_live_mutation_coordinator.py

```diff
warning: in the working copy of 'tests/test_live_mutation_coordinator.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_live_mutation_coordinator.py b/tests/test_live_mutation_coordinator.py
new file mode 100644
index 0000000..8541684
--- /dev/null
+++ b/tests/test_live_mutation_coordinator.py
@@ -0,0 +1,426 @@
+import threading
+import time
+from contextlib import contextmanager
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
+from contextor.core.live_state.ipc import CanonicalMutationCoordinator
+from contextor.core.live_state.store import SnapshotRevisionConflict
+
+
+pytestmark = pytest.mark.live
+
+
+def _diagnostic_state():
+    return SimpleNamespace(
+        revision=0,
+        syntax_diagnostics_state="fresh",
+        syntax_diagnostics_by_path={},
+        collisions_state="fresh",
+        collisions=[],
+        cycles_state="fresh",
+        cycles=[],
+    )
+
+
+@contextmanager
+def _running_server(server):
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    try:
+        yield LiveStateClient(server.endpoint)
+    finally:
+        server.close()
+        thread.join(timeout=3)
+        assert not thread.is_alive()
+
+
+def _wait_for_terminal(client, job_id, timeout=3.0):
+    deadline = time.monotonic() + timeout
+    while time.monotonic() < deadline:
+        status = client.mutation_status(job_id)
+        if status.get("state") in {"completed", "failed", "cancelled"}:
+            return status
+        time.sleep(0.01)
+    raise AssertionError(f"mutation job did not become terminal: {job_id}")
+
+
+def test_submit_ack_is_immediate_and_does_not_publish_revision():
+    started = threading.Event()
+    release = threading.Event()
+
+    def updater(state, path):
+        started.set()
+        assert release.wait(timeout=3)
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
+    with _running_server(server) as client:
+        assert server._mutation_coordinator._thread is None
+        started_at = time.monotonic()
+        accepted = client.submit_update_file("blocked.py", origin="test")
+        elapsed = time.monotonic() - started_at
+
+        assert elapsed < 0.5
+        assert accepted["status"] == "accepted"
+        assert accepted["accepted"] is True
+        assert accepted["state"] == "queued"
+        assert accepted["accepted_revision"] == 0
+        assert accepted["job_id"].startswith("mu-")
+        assert started.wait(timeout=1)
+        assert server._revision == 0
+        assert server._activity_seq == 0
+        assert client.get_events(after_revision=0)["total"] == 0
+
+        release.set()
+        terminal = _wait_for_terminal(client, accepted["job_id"])
+        assert terminal["state"] == "completed"
+        assert terminal["final_revision"] == 1
+
+
+def test_read_only_ipc_remains_responsive_while_queued_mutation_runs():
+    started = threading.Event()
+    release = threading.Event()
+    authority = {
+        "repo_id": "repo-id",
+        "root_path": "C:/repo",
+        "runtime_domain_id": "domain-id",
+        "service_instance_id": "service-id",
+        "lease_generation": 3,
+        "service_pid": 123,
+        "process_start_identity": "start-id",
+    }
+
+    def updater(state, path):
+        started.set()
+        assert release.wait(timeout=3)
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        authority_identity=authority,
+    )
+    with _running_server(server) as client:
+        accepted = client.submit_update_file("slow.py", origin="test")
+        assert started.wait(timeout=1)
+        reader = LiveStateClient(server.endpoint)
+
+        calls = [
+            ("ping", reader.ping),
+            ("snapshot", reader.snapshot),
+            ("authority_status", reader.authority_status),
+            ("get_events", lambda: reader.get_events(after_revision=0)),
+        ]
+        for name, call in calls:
+            started_at = time.monotonic()
+            response = call()
+            elapsed = time.monotonic() - started_at
+            assert elapsed < 1.0, name
+            assert response["status"] == "ok"
+            if name == "snapshot":
+                assert response["revision"] == 0
+                assert response["state"].files == []
+            if name == "get_events":
+                assert response["revision"] == 0
+                assert response["events"] == []
+
+        release.set()
+        terminal = _wait_for_terminal(reader, accepted["job_id"])
+        assert terminal["state"] == "completed"
+        assert terminal["final_revision"] == 1
+        assert reader.snapshot()["state"].files == ["slow.py"]
+        assert reader.get_events(after_revision=0)["total"] == 1
+
+
+def test_queued_mutations_are_fifo_and_strictly_serial():
+    first_started = threading.Event()
+    release_first = threading.Event()
+    active = 0
+    max_active = 0
+    active_lock = threading.Lock()
+    start_order = []
+
+    def updater(state, path):
+        nonlocal active, max_active
+        with active_lock:
+            active += 1
+            max_active = max(max_active, active)
+            start_order.append(path)
+        try:
+            if path == "a.py":
+                first_started.set()
+                assert release_first.wait(timeout=3)
+            state.files.append(path)
+            return {"status": "UPDATED", "file_path": path}
+        finally:
+            with active_lock:
+                active -= 1
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
+    with _running_server(server) as client:
+        first = client.submit_update_file("a.py", origin="test")
+        assert first_started.wait(timeout=1)
+        second = client.submit_update_file("b.py", origin="test")
+        release_first.set()
+
+        first_status = _wait_for_terminal(client, first["job_id"])
+        second_status = _wait_for_terminal(client, second["job_id"])
+        assert first_status["state"] == "completed"
+        assert second_status["state"] == "completed"
+        assert start_order == ["a.py", "b.py"]
+        assert max_active == 1
+        assert first_status["final_revision"] == 1
+        assert second_status["final_revision"] == 2
+        assert client.snapshot()["state"].files == ["a.py", "b.py"]
+
+
+def test_candidate_is_invisible_during_slow_persistence():
+    persist_started = threading.Event()
+    release_persist = threading.Event()
+
+    def updater(state, path):
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    def persister(state, revision):
+        assert state.files == ["persist.py"]
+        assert revision == 1
+        persist_started.set()
+        assert release_persist.wait(timeout=3)
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        persister=persister,
+    )
+    with _running_server(server) as client:
+        accepted = client.submit_update_file("persist.py", origin="test")
+        assert persist_started.wait(timeout=1)
+        snapshot = LiveStateClient(server.endpoint).snapshot()
+        assert snapshot["revision"] == 0
+        assert snapshot["state"].files == []
+        assert server._activity_seq == 0
+
+        release_persist.set()
+        terminal = _wait_for_terminal(client, accepted["job_id"])
+        assert terminal["state"] == "completed"
+        snapshot = client.snapshot()
+        assert snapshot["revision"] == 1
+        assert snapshot["state"].files == ["persist.py"]
+
+
+def test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged(monkeypatch):
+    import contextor.core.runtime_trace as runtime_trace
+
+    trace_events = []
+    monkeypatch.setattr(
+        runtime_trace,
+        "trace_event",
+        lambda *args, **kwargs: trace_events.append((args, kwargs)),
+    )
+
+    initial = _diagnostic_state()
+
+    def updater(state, _path):
+        state.syntax_diagnostics_by_path = {
+            "bad.py": {
+                "status": "checked_with_errors",
+                "errors": [{"message": "bad", "line_number": 1, "column_number": 0}],
+            }
+        }
+        return {"status": "UPDATED", "file_path": "bad.py"}
+
+    def persister(_state, revision):
+        raise SnapshotRevisionConflict(9, revision)
+
+    server = CanonicalLiveServer(initial, updater=updater, persister=persister)
+    with _running_server(server) as client:
+        accepted = client.submit_update_file("bad.py", origin="test")
+        terminal = _wait_for_terminal(client, accepted["job_id"])
+        assert terminal["state"] == "failed"
+        assert terminal["response"]["error"] == "canonical_persistence_revision_conflict"
+        assert server._state is initial
+        assert server._revision == 0
+        assert server._activity_seq == 0
+        assert client.get_events(after_revision=0)["events"] == []
+        assert not any(
+            args[1].startswith("LIVE_DIAGNOSTIC_") for args, _kwargs in trace_events
+        )
+
+
+def test_worker_survives_failed_job_and_executes_next_job():
+    first_started = threading.Event()
+
+    def updater(state, path):
+        if path == "bad.py":
+            first_started.set()
+            raise RuntimeError("first failed")
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
+    with _running_server(server) as client:
+        first = client.submit_update_file("bad.py", origin="test")
+        assert first_started.wait(timeout=1)
+        second = client.submit_update_file("good.py", origin="test")
+        first_status = _wait_for_terminal(client, first["job_id"])
+        second_status = _wait_for_terminal(client, second["job_id"])
+
+        assert first_status["state"] == "failed"
+        assert first_status["response"]["error"] == "canonical_mutation_execution_failed"
+        assert "first failed" in first_status["error"]
+        assert second_status["state"] == "completed"
+        assert second_status["final_revision"] == 1
+        assert client.snapshot()["state"].files == ["good.py"]
+
+
+def test_publish_and_queued_update_are_single_writer_serialized():
+    update_started = threading.Event()
+    release_update = threading.Event()
+    publish_done = threading.Event()
+    publish_response = []
+
+    def updater(state, path):
+        update_started.set()
+        assert release_update.wait(timeout=3)
+        state.value = 1
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(value=0, files=[], revision=0), updater=updater
+    )
+    try:
+        accepted = server._mutation_coordinator.submit({"file_path": "update.py"})
+        assert update_started.wait(timeout=1)
+
+        def publish():
+            publish_response.append(
+                server._execute_publish(
+                    {"operation": "publish", "state": SimpleNamespace(value=2, files=[])}
+                )
+            )
+            publish_done.set()
+
+        publish_thread = threading.Thread(target=publish)
+        publish_thread.start()
+        assert not publish_done.wait(timeout=0.1)
+
+        release_update.set()
+        deadline = time.monotonic() + 2
+        update_status = server._mutation_coordinator.status(accepted["job_id"])
+        while (
+            update_status.get("state") not in {"completed", "failed", "cancelled"}
+            and time.monotonic() < deadline
+        ):
+            time.sleep(0.01)
+            update_status = server._mutation_coordinator.status(accepted["job_id"])
+        publish_thread.join(timeout=2)
+        assert not publish_thread.is_alive()
+        assert update_status["state"] == "completed"
+        assert update_status["final_revision"] == 1
+        assert publish_response == [{"status": "ok", "revision": 2, "seq": 2}]
+        assert server._revision == 2
+        assert server._state.value == 2
+    finally:
+        server.close()
+
+
+def test_coordinator_close_cancels_queued_not_active_job():
+    first_started = threading.Event()
+    release_first = threading.Event()
+
+    def executor(request):
+        if request["file_path"] == "first.py":
+            first_started.set()
+            assert release_first.wait(timeout=3)
+        return {"status": "ok", "revision": 1}
+
+    coordinator = CanonicalMutationCoordinator(lambda request: executor(request), lambda: 0)
+    first = coordinator.submit({"file_path": "first.py"})
+    assert first_started.wait(timeout=1)
+    second = coordinator.submit({"file_path": "second.py"})
+
+    coordinator.close(join_timeout=0.05)
+    cancelled = coordinator.status(second["job_id"])
+    assert cancelled["state"] == "cancelled"
+    assert cancelled["error"] == "canonical_mutation_queue_closed"
+    assert cancelled["response"] == {
+        "status": "error",
+        "error": "canonical_mutation_queue_closed",
+        "job_id": second["job_id"],
+    }
+    assert coordinator.submit({"file_path": "third.py"}) == {
+        "status": "error",
+        "error": "canonical_mutation_queue_closed",
+    }
+
+    release_first.set()
+    deadline = time.monotonic() + 2
+    while time.monotonic() < deadline:
+        if coordinator.status(first["job_id"]).get("state") == "completed":
+            break
+        time.sleep(0.01)
+    assert coordinator.status(first["job_id"])["state"] == "completed"
+    coordinator.close(join_timeout=0.1)
+
+
+def test_unknown_and_invalid_mutation_job_status_fail_closed():
+    coordinator = CanonicalMutationCoordinator(lambda _request: {"status": "ok"}, lambda: 0)
+    try:
+        assert coordinator.status(None) == {
+            "status": "error",
+            "error": "invalid_mutation_job_id",
+        }
+        assert coordinator.status("") == {
+            "status": "error",
+            "error": "invalid_mutation_job_id",
+        }
+        assert coordinator.status("mu-missing") == {
+            "status": "error",
+            "error": "unknown_mutation_job",
+            "job_id": "mu-missing",
+        }
+        assert coordinator.submit({"file_path": ""}) == {
+            "status": "error",
+            "error": "invalid_file_path",
+        }
+    finally:
+        coordinator.close()
+
+
+def test_legacy_update_file_contract_remains_synchronous_and_unchanged():
+    started = threading.Event()
+    release = threading.Event()
+
+    def updater(state, path):
+        started.set()
+        assert release.wait(timeout=3)
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
+    with _running_server(server) as client:
+        response_box = []
+        call_thread = threading.Thread(
+            target=lambda: response_box.append(client.update_file("legacy.py"))
+        )
+        call_thread.start()
+        assert started.wait(timeout=1)
+        assert not response_box
+        assert server._revision == 0
+        release.set()
+        call_thread.join(timeout=2)
+        assert not call_thread.is_alive()
+        assert response_box == [{
+            "status": "ok",
+            "activity_epoch": response_box[0]["activity_epoch"],
+            "revision": 1,
+            "result": {"status": "UPDATED", "file_path": "legacy.py"},
+            "seq": 1,
+        }]
```
