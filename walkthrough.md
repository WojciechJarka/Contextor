# L11_LIVE_CAPTURE_ADMISSION_COMMIT_ACK_DISCOVERY

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\walkthrough.md` — bieżący raport. Plik raportowy wyłączony z rozliczenia zmian source/test/docs.
- Source/test/docs zmienione w tym zadaniu: NONE.

## ACTUAL_DIFF

ACTUAL_DIFF=DIFFS=NONE dla source/test/docs. `git status --short` i `git diff --stat` zwróciły pusty wynik przed zapisem raportu i w końcowym sprawdzeniu przed zapisem.

## SOURCE_SYNC

DIRECT_EVIDENCE: Contextor MCP `get_symbol_implementation(mode=fetch,include=[implementation])` dla właścicieli watchera, kolejki, guardu, commitu, dziennika i klienta zwrócił `workspace_sync=verified`, `canonical_state=fresh`, `implementation_is_complete=true` (rewizja 328). Duże metody `DesktopLiveWatcher.poll_once` i `CanonicalLiveServer._execute_update_file` pobrano przez kompletne, stykające się zakresy `get_source_range`. `get_file_edit_context` dla watcher.py, ipc.py, runtime.py i koordynatora także zwrócił verified. Nie uznano preview/truncation za pełne źródło.

## RUNTIME_AUTHORITY_IDENTITY

RUNTIME_OBSERVED z read-only `contextor.core.live_state.runtime.connect(...).authority_status()`: repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`, runtime_domain_id `rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654`, service_instance_id `97079e0033404620ab8403ca300abc2b`, lease_generation 17, service PID 4064, process_start_identity `134362069262172779`, revision 328. Osobny odczyt Win32_Process potwierdził PID 4064 jako python.exe uruchomiony 2026-10-11 17:42:06 czasu lokalnego i Desktop PID 5328 jako python.exe uruchomiony 17:42:01. Aktywny trace SID `d-5328-20261011_154204_448`. Użyty plik trace: `C:\Users\DafoO\AppData\Roaming\Contextor\logs\contextor_runtime_20261011_154204_448_5328.jsonl`. Nie odczytano ani nie ujawniono authkey.

## LIVE_EVENT_WINDOW

Publiczny `get_live_events(limit=null)` zwrócił `confirmation_required` przy estymacji 46,416 bajtów, a `limit=20` także przekroczył limit narzędzia. Dlatego pełne zachowane okno pobrano przez istniejący, **read-only** `LiveStateClient.get_events(after_seq=0,limit=None)`, bez tworzenia zdarzenia. Wynik bezpośredniego IPC: activity_epoch `25edf50d6ac746bf99fd3731e1fd330f`, revision/latest_revision 328, latest_seq 152, earliest_retained_seq 1, earliest_retained_revision 328, total=returned=152, truncated=false, activity_continuity=continuous, activity_resync_required=false, resync_required=false. Czas pierwszego i ostatniego rekordu: 2026-10-11T15:41:41.191+00:00 i 2026-10-11T20:26:49.192755+00:00. Kategorie: AUTHORITY=11, MCP_CALL=140, LIVE_STATE=1.

Jedyny retained canonical event: seq 88, 2026-10-11T19:59:56.080536+00:00, operation=`update_file`, revision/canonical_revision=328, status=`UPDATED`, trace_op=`u-5328-5`, path=`C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`, origin/source=`desktop_watcher`, affected_modules=`tests.test_live_e2e_corrections`. Event nie ma `origin_verified`, job_id ani idempotency_key.

## EVENT_TRUNCATION_AND_CONTINUITY

Całe aktualnie retained okno, od seq 1 do 152, odczytano bez truncation. `get_live_events(after_revision=327)` zwrócił jeden event rewizji 328 i `continuity=continuous`, `resync_required=false`. Rewizja 327 nie jest sama retained jako canonical event (`earliest_retained_revision=328`), ale cursor 327 jest ciągły względem 328. Część MCP_CALL powstała podczas bieżącego audytu; nie oznacza zmian canonical revision. Dziennik jest pamięciowy i retencyjny, a trace diagnostyczny jest osobnym dowodem. Wystąpienie `confirmation_required` na warstwie MCP to limit rozmiaru odpowiedzi, nie truncation dziennika LIVE.

## OPERATION_CORRELATION_MATRIX

| Stage | Dokładny dowód runtime | UTC | Op/path/revision | Proces | Klasyfikacja |
|---|---|---|---|---|---|
| A — watcher capture | trace line 14541 `FS_CHANGE_DETECTED`, następnie 14542 `WATCH_UPDATE_START` | 19:59:29.723 / .749 | `u-5328-5`, `tests/test_live_e2e_corrections.py`, observed rev 327, kind modify, mtime_ns 1791748755602904100 | Desktop PID 5328 | RUNTIME_OBSERVED; procesowy ślad watchera |
| B — writer admission | trace line 14543 `CANONICAL_WRITER_ADMISSION_ACQUIRED` | 19:59:29.860 | ten sam op, absolutny path, job `mu-89a3d4723aaa4af4ad6d82bfc3c9f5fc`, idempotency `96cee7f69a3c41f5af9a9c0ddaddd5bb`, queue_order 1, accepted_revision 327, started_revision 327; repo_id `ctx_8efc50d8`, owner `live_mutation_worker`, writer_kind `live_mutation` | LIVE PID 4064 | RUNTIME_OBSERVED; OS writer admission |
| C — durable + RAM commit | trace lines 14560-14566: `PERSIST_START`, `SNAPSHOT_SAVE_END`, `FILE_STATE_SAVE_END`, `PERSIST_END`, `CANONICAL_COMMIT`, `ACTIVITY_APPEND`, `UPDATE_PUBLISHED`; journal seq 88 | 19:59:48.459–19:59:56.096 | ten sam op/path; rev 327→328, seq 88, status UPDATED | LIVE PID 4064 | RUNTIME_OBSERVED; CODE_PATH_PROVED commit po persister success |
| D — watcher terminal ACK | trace line 14570 `WATCH_UPDATE_END`; GUI seq 88 queue/render lines 14568-14569 | 19:59:56.862 (GUI .724/.742) | ten sam op/path, rev 328, seq 88, status UPDATED | Desktop PID 5328 | RUNTIME_OBSERVED; CODE_PATH_PROVED watcher emit po `mutation_status` completed/ok |

Z aktywnego logu: dokładnie 29 rekordów z `op=u-5328-5`, po jednym z każdego wymienionego etapu, w liniach 14541–14570 (bez numeru 14567). Dwa PID i jeden SID. Żaden rekord tego op nie zgłasza `UPDATE_FAIL`, `WATCH_UPDATE_FAIL` ani innego terminalnego błędu. Zbieżność nie opiera się tylko na czasie/path/origin: `trace_op` utworzony w watcherze przechodzi przez `_PendingMutationIntent` i request do serwera; admission log ma ten op wraz z job/idempotency/queue; commit i event seq 88 mają ten op; watcher ACK używa `job.trace_op` i exact `response.revision/seq`. Source path i PID/SID są dodatkowymi kontrolami.

## WATCHER_CAPTURE

CODE_PATH_PROVED: `_LiveFilesystemEventHandler.on_modified` enqueue'uje ścieżkę. `DesktopLiveWatcher.poll_once` po drain/revalidation tworzy `new_trace_operation("u")`, emituje `FS_CHANGE_DETECTED` i `WATCH_UPDATE_START`, oblicza source hash, tworzy `_PendingMutationIntent(idempotency_key=uuid.uuid4().hex,trace_op=op,...)`, po czym `submit_update_file`. RUNTIME_OBSERVED: A w trace z PID 5328. Pole `discovery="watchdog"` w call site nie jest akceptowane przez `runtime_trace.trace_event` key_map, więc nie pojawia się w JSONL; sam event i PID są obserwowalne. Fakt rzeczywistego wykrycia przez watcher wynika z wykonanej metody i trace, nie z samego `origin` w journalu.

## WRITER_ADMISSION

CODE_PATH_PROVED: `CanonicalMutationCoordinator.submit` waliduje idempotency_key, deduplikuje po nim, tworzy job_id/queue_order/accepted_revision. `_run` ustawia running i started_revision oraz przekazuje request do `_execute_queued_update_file`. Ten wchodzi w `_repository_mutation_guard`, który wywołuje `acquire_full_analysis(...writer_kind="live_mutation")` z trace fields job/op/idempotency/revision. `_canonical_writer_admission` zdobywa procesowy i OS lock, emituje ACQUIRED i zwalnia gate dopiero po zdobyciu właściwego writer lease. RUNTIME_OBSERVED: B z job i realnym server PID. Samo `accepted` response nie jest zapisane w trace; job/admission i późniejszy commit dowodzą zaakceptowanego wykonania tej operacji.

## CANONICAL_COMMIT

CODE_PATH_PROVED: `_execute_update_file` clone'uje previous state, wywołuje updater na candidate, ustala expected_revision=previous+1, wywołuje persister, a dopiero po jego sukcesie pod `self._lock` zamienia `self._state` i `self._revision`. Następnie zapisuje event i zwraca `status=ok,revision,seq,result`. RUNTIME_OBSERVED: PERSIST_END przed CANONICAL_COMMIT 327→328, event seq 88 i UPDATE_PUBLISHED UPDATED. Persister error nie prowadzi do RAM commit. Live event jest po commit. Dodatkowy read-only `read_metadata(repo_cache_dir(root))` potwierdził trwałe metadata: repo_id `ctx_8efc50d8`, revision 328, state_id `20261011_103015`, state_file `engine_state.r328.d87d0566949f4035bdc211e2746ae295.pkl`, file_state_file `file_state.r328.d87d0566949f4035bdc211e2746ae295.json`. Nie wykonywano zapisu ani snapshot hydration dla audytu.

## WATCHER_ACK

CODE_PATH_PROVED: `_poll_inflight_updates` odpytuje `mutation_status(job_id)`; `queued/running` nie są terminalnym ACK. Tylko `state=completed`, `response.status=ok` i akceptowany result.status aktualizują snapshot watchera i emitują `WATCH_UPDATE_END` z `job.trace_op`, `response.revision`, `response.seq`. RUNTIME_OBSERVED: ACK op `u-5328-5`, rev 328, seq 88, status UPDATED z Desktop PID 5328, po server commit. Log ACK nie zawiera job_id; powiązanie job→trace_op jest CODE_PATH_PROVED przez `_inflight_updates[job_id]`. GUI STATUS_QUEUED/RENDERED to prezentacja eventu seq 88, nie samo potwierdzenie watchera.

## ORIGIN_VERIFICATION

`origin="desktop_watcher"` w journalu jest source/request metadata przepisywanym przez `_record_event`; brak `origin_verified` dla update_file. Nie jest to samodzielny dowód capture ani uwierzytelnionej tożsamości pisarza. Wniosek o prawdziwym watcher capture opiera się na logu Desktop PID 5328 z `FS_CHANGE_DETECTED` i `WATCH_UPDATE_END`, op korelowanym z server PID 4064 oraz source path i rewizją. IPC authkey chroni transport, lecz nie dowodzi, że dowolne pole `origin` pochodzi od watchera. G2E `origin_verified=False` odnosi się do opt-in `already_installed` publish ACK; to osobna ścieżka od badanego update_file.

## REVISION_AND_OPERATION_IDENTITY

Capture rev 327; admission accepted_revision=327 i started_revision=327; PERSIST_END rev 328; CANONICAL_COMMIT rev0=327 rev1=328; journal seq 88/canonical_revision 328; watcher ACK rev 328/seq 88. `_poll_inflight_updates` bierze rev/seq z terminalnej odpowiedzi job, nie z bieżącego ping. Source pozwala na kolejkę, w której started_revision różni się od accepted_revision, ale tutaj były równe. `trace_op` jest korelatorem diagnostycznym, a nie kryptograficznym tokenem; jego wartość była przekazywana w request. Suma śladów procesu Desktop i servera + job metadata + revision/seq stanowi dowód tej konkretnej operacji.

## RECONNECT_RETRY_AND_IDEMPOTENCY

CODE_PATH_PROVED: timeout/lost response prowadzi do `_ambiguous_updates` i zachowania `_PendingMutationIntent` z tym samym idempotency_key/trace_op; retry submit w koordynatorze zwraca istniejący job, jeśli retained. `mutation_status` zwraca queued/running/completed/failed z job metadata i terminal response. Nieznany/pruned job powoduje ponowne enqueue i revalidation, nie ACK sukcesu. Reconnect `_recover_client` ma osobny recovery op i endpoint identity. Opt-in `already_installed` ACK dotyczy publish, nie watcher update. Dla op `u-5328-5` nie zaobserwowano reconnect/retry/duplicate/UNKNOWN; zbadano ich kontrakt kodowy i testy. Brak odpowiedzi nie jest traktowany jako udany commit.

## EXISTING_REGRESSION_COVERAGE

| Test i dokładna lokalizacja | Rzeczywiste asercje | Poziom |
|---|---|---|
| `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py:2225-2270` | realny lokalny server/client i watcher, trzy ręczne enqueue dla create/edit/delete, revision=3, updates=3, status messages | MULTI-COMPONENT INTEGRATION; nie realny Desktop observer ani pełny trace |
| `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py:2273-2304` | failed mutation status usuwa inflight, requeue, brak completed | UNIT CONTRACT |
| `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py:489-558` | admission trace op/path/job/idempotency/queue/revisions, whitelisting i prawdziwy OS lease | MULTI-COMPONENT INTEGRATION |
| `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py:636-648` | duplicate idempotency_key zwraca ten sam job_id | UNIT/IPC CONTRACT |
| `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py:1355-1420` | realny updater/persister trace op przez persist i commit, snapshot/FileState revision parity | MULTI-COMPONENT INTEGRATION |
| `C:\Temp\Contextor_Repo\tests\test_watcher_recovery_admission.py:143-177` | completed job podczas recovery nie certyfikuje starej baseline; requeue | UNIT CONTRACT |
| `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py:1096-1158` | mocked reconnect po zerwanym ping, update po podmianie klienta | UNIT/MOCKED INTEGRATION |
| `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py:648-721` | full-analysis publish `already_installed` opt-in, origin_verified=false, lease held | OTHER PATH / COMPATIBILITY |

Contextor `get_file_edit_context` wskazał statycznych konsumentów i testy pokrywające watcher.py (14), ipc.py (70), runtime.py (65) i koordynator (86), lecz te liczby są dependency reachability, nie dowodem asercji. Nie znaleziono pojedynczego testu, który asertuje realny Desktop capture→admission→durable commit→watcher ACK; tę lukę testową odróżniono od znalezionego realnego runtime chain.

## RUNTIME_EVIDENCE_VS_TEST_EVIDENCE

RUNTIME_OBSERVED: kompletny op `u-5328-5` z rzeczywistych procesów i trwałego trace, pełny nieobcięty LIVE event seq 88. TEST_PROVED: fragmenty kontraktu wymienione wyżej. CODE_PATH_PROVED: propagacja op/job i warunki terminalnego ACK. Nie wykonano pytest w tym read-only discovery, bo rzeczywisty łańcuch runtime był dostępny i test execution nie było potrzebne do jego ustalenia.

## MISSING_CORRELATION_FIELDS

Brak krytycznego pola uniemożliwiającego korelację op `u-5328-5`. Ograniczenia schematu: journal update_file nie emituje `origin_verified`, job_id, idempotency_key, queue_order, accepted_revision ani started_revision; ACK trace nie emituje job_id/idempotency_key; capture trace nie emituje job_id (powstaje dopiero przy submit). Admission trace zawiera job/idempotency/queue/revisions. Exact op/path/rev/seq i procesowy trace zamykają tę konkretną korelację. Nie należy uogólniać tego na przyszły przypadek, gdy trace segment nie jest dostępny.

## COMPLETE_RELEVANT_SOURCE_FRAGMENTS

Źródła poniżej są pełnymi implementacjami symboli lub kompletnymi, stykającymi się zakresami dużych metod. Wszystkie pobrane z Contextor przy verified source. Brak preview/truncated jako źródła kompletnego.

### DesktopLiveWatcher._poll_inflight_updates — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:592-665

```python
    def _poll_inflight_updates(self) -> list[str]:
        completed: list[str] = []
        for job_id, job in list(self._inflight_updates.items()):
            try:
                status = self.client.mutation_status(job_id)
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                recovered = self._recover_client(exc)
                if recovered is None:
                    continue
                try:
                    status = self.client.mutation_status(job_id)
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    continue
            state = status.get("state") if isinstance(status, dict) else None
            if state in {"queued", "running"}:
                continue
            self._inflight_updates.pop(job_id, None)
            if state == "completed":
                response = status.get("response")
                result = response.get("result") if isinstance(response, dict) else None
                result_status = getattr(result, "status", None)
                if isinstance(response, dict) and response.get("status") == "ok" and result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}:
                    def trust_completed_path() -> bool:
                        if job.observed_state is None:
                            self._snapshot.pop(job.path, None)
                        else:
                            self._snapshot[job.path] = job.observed_state
                        return True

                    if self._admit_recovery_action(trust_completed_path) is RECOVERY_DEFERRED:
                        self._enqueue_path(job.path, wake=False)
                    completed.append(job.path)
                    from contextor.core.runtime_trace import trace_event
                    try:
                        relative = Path(job.path).resolve().relative_to(self.root).as_posix()
                    except ValueError:
                        relative = job.path
                    trace_event("LIVE", "WATCH_UPDATE_END", op=job.trace_op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0)
                    if result_status == "SYNTAX_ERROR":
                        line = getattr(result, "line_number", None)
                        column = getattr(result, "column_number", None)
                        position = f" line {line}, column {column}" if line and column else ""
                        self._emit(f"LIVE syntax error: {Path(job.path).name}{position}: {getattr(result, 'error', 'syntax error')}")
                    elif result_status == "RECOVERED":
                        self._emit(f"LIVE syntax recovery: {Path(job.path).name}")
                    else:
                        self._emit(f"LIVE update successful: {Path(job.path).name}")
                    continue
            if isinstance(status, dict) and status.get("error") in {"unknown_mutation_job", "invalid_mutation_job_id"}:
                self._ambiguous_updates.add(job.path)
                self._pending_intents.setdefault(
                    job.path,
                    _PendingMutationIntent(
                        idempotency_key=job.idempotency_key,
                        path=job.path,
                        trace_op=job.trace_op,
                        observed_state=job.observed_state,
                        started_at=job.started_at,
                        observed_sha256=job.observed_sha256,
                    ),
                )
            from contextor.core.runtime_trace import trace_event
            try:
                relative = Path(job.path).resolve().relative_to(self.root).as_posix()
            except ValueError:
                relative = job.path
            trace_event(
                "LIVE", "WATCH_UPDATE_FAIL", op=job.trace_op, repo=str(self.root),
                path=relative, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0,
                err=(status.get("error", "malformed mutation status") if isinstance(status, dict) else "malformed mutation status"),
            )
            self._requeue_paths([job.path])
            self._emit(f"LIVE update failed; deferring watcher update: {Path(job.path).name}")
        return completed
```


### DesktopLiveWatcher._enqueue_path — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:441-451

```python
    def _enqueue_path(self, raw_path: str | Path, *, wake: bool = True) -> None:
        path = self._normalize_watch_path(raw_path)
        if path is None:
            return
        with self._pending_lock:
            if path in self._pending_set:
                return
            self._pending_paths.append(path)
            self._pending_set.add(path)
            if wake:
                self._wake.set()
```


### DesktopLiveWatcher._run_event_worker — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:297-319

```python
    def _run_event_worker(self) -> None:
        while not self._stop.is_set():
            signaled = self._wake.wait(1.0)
            if self._stop.is_set():
                break
            if signaled:
                if self._stop.wait(self.interval):
                    break
            else:
                try:
                    self._check_observer_health()
                except (OSError, RuntimeError, EOFError) as exc:
                    self._handle_poll_error(exc)
            if self._has_pending_paths() or self._has_inflight_updates():
                try:
                    self.poll_once()
                except (OSError, RuntimeError, EOFError) as exc:
                    self._handle_poll_error(exc)
                if signaled:
                    try:
                        self._check_observer_health()
                    except (OSError, RuntimeError, EOFError) as exc:
                        self._handle_poll_error(exc)
```


### CanonicalMutationCoordinator.submit — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:157-217

```python
    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            request_dict = dict(request)
        except (TypeError, ValueError):
            request_dict = {}
        file_path = request_dict.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            return {"status": "error", "error": "invalid_file_path"}
        idempotency_key = request_dict.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            return {"status": "error", "error": "invalid_idempotency_key"}

        with self._condition:
            if self._recovery_verification_fenced:
                return {
                    "status": "error",
                    "error": "recovery_verification_in_progress",
                    "accepted": False,
                }
            existing_job_id = self._idempotency_jobs.get(idempotency_key)
            if existing_job_id is not None:
                existing_job = self._jobs.get(existing_job_id)
                if existing_job is not None:
                    return {
                        "status": "accepted",
                        "accepted": True,
                        "job_id": existing_job.job_id,
                        "queue_order": existing_job.queue_order,
                        "accepted_revision": existing_job.accepted_revision,
                        "state": existing_job.state,
                    }
                del self._idempotency_jobs[idempotency_key]
            if not self._accepting:
                return {
                    "status": "error",
                    "error": "canonical_mutation_queue_closed",
                }

            self._queue_order += 1
            job_id = "mu-" + uuid.uuid4().hex
            accepted_revision = int(self._revision_reader())
            job = _MutationJob(
                job_id=job_id,
                queue_order=self._queue_order,
                request=request_dict,
                accepted_revision=accepted_revision,
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = job
            self._idempotency_jobs[idempotency_key] = job_id
            self._queue.append(job_id)
            self._ensure_started_locked()
            self._condition.notify_all()
            return {
                "status": "accepted",
                "accepted": True,
                "job_id": job_id,
                "queue_order": job.queue_order,
                "accepted_revision": accepted_revision,
                "state": job.state,
            }
```


### CanonicalMutationCoordinator._run — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:284-347

```python
    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and not self._stop:
                    self._condition.wait()
                if self._stop and not self._queue:
                    return
                job_id = self._queue.popleft()
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                if job.state == "cancelled":
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                    continue
                job.state = "running"
                job.started_revision = int(self._revision_reader())
                execution_request = dict(job.request)
                execution_request.update(
                    {
                        "job_id": job.job_id,
                        "queue_order": job.queue_order,
                        "accepted_revision": job.accepted_revision,
                        "started_revision": job.started_revision,
                    }
                )

            try:
                response = self._executor(execution_request)
            except Exception as exc:
                response = {
                    "status": "error",
                    "error": "canonical_mutation_execution_failed",
                    "detail": str(exc),
                }
                with self._condition:
                    job.state = "failed"
                    job.response = response
                    job.error = str(exc)
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                continue

            with self._condition:
                if isinstance(response, dict) and response.get("status") == "ok":
                    job.state = "completed"
                    job.response = response
                else:
                    job.state = "failed"
                    if isinstance(response, dict):
                        job.response = response
                        error = response.get("error")
                        job.error = str(error) if error is not None else "canonical_mutation_invalid_response"
                    else:
                        job.response = {
                            "status": "error",
                            "error": "canonical_mutation_invalid_response",
                        }
                        job.error = "canonical_mutation_invalid_response"
                final_revision = job.response.get("revision") if job.response else None
                if isinstance(final_revision, int) and not isinstance(final_revision, bool):
                    job.final_revision = final_revision
                self._prune_terminal_locked()
                self._condition.notify_all()
```


### _repository_mutation_guard — C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1263-1303

```python
def _repository_mutation_guard(root: Path):
    @contextlib.contextmanager
    def guard(request: Mapping[str, Any], stop_event: threading.Event):
        from contextor.core.analysis.full_analysis_coordinator import (
            acquire_full_analysis,
            release_full_analysis,
        )

        origin = request.get("origin")
        if origin is None:
            origin = request.get("source")

        admission_trace_fields = {
            "op": request.get("trace_op"),
            "path": request.get("file_path"),
            "job_id": request.get("job_id"),
            "idempotency_key": request.get("idempotency_key"),
            "queue_order": request.get("queue_order"),
            "accepted_revision": request.get("accepted_revision"),
            "started_revision": request.get("started_revision"),
            "origin": origin,
        }

        lease = acquire_full_analysis(
            root,
            owner="live_mutation_worker",
            writer_kind="live_mutation",
            timeout=(
                0.0
                if request.get("operation") == "update_file"
                else None
            ),
            is_cancelled=stop_event.is_set,
            admission_trace_fields=admission_trace_fields,
        )
        try:
            yield
        finally:
            release_full_analysis(lease)

    return guard
```


### CanonicalMutationCoordinator.status — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:243-270

```python
    def status(self, job_id: Any) -> dict[str, Any]:
        if not isinstance(job_id, str) or not job_id:
            return {"status": "error", "error": "invalid_mutation_job_id"}

        with self._condition:
            job = self._jobs.get(job_id)
            if job is None:
                return {
                    "status": "error",
                    "error": "unknown_mutation_job",
                    "job_id": job_id,
                }
            response: dict[str, Any] = {
                "status": "ok",
                "job_id": job.job_id,
                "queue_order": job.queue_order,
                "accepted_revision": job.accepted_revision,
                "state": job.state,
            }
            if job.started_revision is not None:
                response["started_revision"] = job.started_revision
            if job.final_revision is not None:
                response["final_revision"] = job.final_revision
            if job.error is not None:
                response["error"] = job.error
            if job.response is not None:
                response["response"] = copy.deepcopy(job.response)
            return response
```


### LiveStateClient.submit_update_file — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2597-2611

```python
    def submit_update_file(
        self,
        file_path: str,
        *,
        origin: str = "unknown",
        trace_op: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "submit_update_file",
            file_path=file_path,
            origin=origin,
            trace_op=trace_op,
            idempotency_key=idempotency_key,
        )
```


### LiveStateClient.mutation_status — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2613-2614

```python
    def mutation_status(self, job_id: str) -> dict[str, Any]:
        return self.request("mutation_status", job_id=job_id)
```


### LiveStateClient.get_events — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2653-2667

```python
    def get_events(
        self,
        *,
        after_revision: int | None = None,
        after_seq: int | None = None,
        limit: int | None = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "get_events",
            after_revision=after_revision,
            after_seq=after_seq,
            limit=limit,
            category=category,
        )
```


### CanonicalLiveServer._record_event — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:852-934

```python
    def _record_event(
        self,
        operation: str,
        request: dict[str, Any],
        result: Any = None,
        *,
        category: str = "LIVE_STATE",
    ) -> dict[str, Any]:
        """Keep a small, JSON-safe event journal for Desktop status and MCP polling."""
        from datetime import datetime, timezone

        self._activity_seq += 1
        source = str(request.get("origin") or request.get("source") or "unknown")

        canonical_rev = self._revision if category == "LIVE_STATE" else None

        event: dict[str, Any] = {
            "seq": self._activity_seq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "operation": operation,
            "source": source,
            "origin": source,
            "canonical_revision": canonical_rev,
            "revision": self._revision,
            "status": (
                getattr(result, "status", "PUBLISHED")
                if not isinstance(result, dict)
                else result.get("status", "PUBLISHED")
            ) if category == "LIVE_STATE" else ("SUCCESS" if request.get("success", True) else "FAILED"),
        }
        trace_op = request.get("trace_op")
        if trace_op is not None:
            event["trace_op"] = str(trace_op)

        if category == "MCP_CALL":
            event["tool"] = str(request.get("tool", ""))
            event["success"] = bool(request.get("success", True))
            if request.get("error"):
                event["error"] = str(request["error"])
            event["message"] = request.get("message") or f"MCP tool: {event['tool']}"
        else:
            file_path = getattr(result, "file_path", request.get("file_path")) if not isinstance(result, dict) else result.get("file_path", request.get("file_path"))
            if file_path is not None:
                event["file_path"] = str(file_path)
            for name in ("error", "line_number", "column_number"):
                value = getattr(result, name, None) if not isinstance(result, dict) else result.get(name)
                if value is not None:
                    event[name] = value
            blast_radius_state = (
                getattr(result, "blast_radius_state", None)
                if not isinstance(result, dict)
                else result.get("blast_radius_state")
            )
            if blast_radius_state is not None:
                event["blast_radius_state"] = blast_radius_state
            affected = (
                getattr(result, "affected_modules", None)
                if not isinstance(result, dict)
                else result.get("affected_modules")
            )
            if affected is not None:
                total = len(affected)
                event["affected_modules"] = {
                    "total": total,
                    "truncated": total > 20,
                    "items": list(affected[:20]),
                }
            diagnostic_changes = request.get("diagnostic_changes")
            if isinstance(diagnostic_changes, Mapping):
                event["diagnostic_changes"] = copy.deepcopy(diagnostic_changes)
            if request.get("message") is not None:
                event["message"] = str(request["message"])

        self._events.append(event)
        del self._events[:-self._retention]
        _safe_trace_event(
            "LIVE", "ACTIVITY_APPEND", op=trace_op,
            rev=self._revision, seq=self._activity_seq,
            category=category, operation=operation,
            status=event.get("status"),
        )
        return event
```


### CanonicalLiveServer._execute_queued_update_file — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1874-1882

```python
    def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
        trace_op = _safe_trace_op(request, "u")
        if trace_op is not None:
            request = {**request, "trace_op": trace_op}

        if self._mutation_guard is None:
            return self._execute_update_file(request, allow_recovery_fence=True)
        with self._mutation_guard(request, self._stop):
            return self._execute_update_file(request, allow_recovery_fence=True)
```


### LiveStateClient.request — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2477-2512

```python
    def request(
        self, operation: str, *, timeout: float = 30.0, **payload: Any
    ) -> dict[str, Any]:
        started = time.monotonic()
        try:
            connection = Client(
                self.endpoint.address,
                family="AF_INET",
                authkey=self.endpoint.authkey,
            )
            try:
                connection.send({"operation": operation, **payload})
                import multiprocessing.connection as mpc
                ready = mpc.wait([connection], timeout=timeout)
                if not ready:
                    raise TimeoutError(
                        "Canonical LIVE service did not respond within "
                        f"{timeout:g}s for op={operation}"
                    )
                response = connection.recv()
            finally:
                connection.close()
        except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
            _safe_trace_event(
                "LIVE", "LIVE_IPC_FAILURE",
                side="client", operation_or_request_type=operation,
                host=getattr(self.endpoint, "host", self.endpoint.address[0]),
                port=getattr(self.endpoint, "port", self.endpoint.address[1]),
                exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            raise
        if not isinstance(response, dict):
            raise RuntimeError("Canonical LIVE service returned an invalid response.")
        return response
```


### DesktopLiveWatcher._recover_client — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:350-420

```python
    def _recover_client(self, trigger_exc: BaseException | None = None) -> LiveStateClient | None:
        """Attempt to reconnect or restart LIVE on genuine connection failure."""
        started = time.monotonic()
        prior_endpoint = getattr(self.client, "endpoint", None)
        try:
            from contextor.core.runtime_trace import new_trace_operation, trace_event

            recovery_operation_id = new_trace_operation("wr")
            trace_event(
                "LIVE", "LIVE_WATCHER_RECOVERY_START", op=recovery_operation_id,
                reason="connection_failure",
                prior_endpoint_fingerprint=(prior_endpoint.fingerprint() if prior_endpoint is not None else None),
                prior_service_pid=getattr(prior_endpoint, "pid", None),
                recovery_operation_id=recovery_operation_id,
                exception_class=(type(trigger_exc).__name__ if trigger_exc is not None else None),
                errno=(getattr(trigger_exc, "errno", None) if trigger_exc is not None else None),
                winerror=(getattr(trigger_exc, "winerror", None) if trigger_exc is not None else None),
                error=(str(trigger_exc)[:500] if trigger_exc is not None else None),
            )
        except Exception:
            recovery_operation_id = None
        try:
            from .runtime import connect_or_start

            new_client = connect_or_start(
                self.root,
                owner_pid=self.owner_pid,
                owner_token=self.owner_token,
                desktop_instance_id=self.desktop_instance_id,
                client_kind="desktop" if self.desktop_instance_id is not None else "protocol",
                timeout=10.0,
            )
            self.client = new_client
            if self.on_reconnect is not None:
                self.on_reconnect(new_client)
            try:
                from contextor.core.runtime_trace import trace_event

                new_endpoint = new_client.endpoint
                trace_event(
                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
                    result=(
                        "reconnected_same_endpoint"
                        if prior_endpoint is not None and new_endpoint == prior_endpoint
                        else "connected_changed_endpoint"
                    ),
                    new_endpoint_fingerprint=new_endpoint.fingerprint(),
                    new_service_pid=new_endpoint.pid,
                    lease_generation=new_endpoint.lease_generation,
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                    recovery_operation_id=recovery_operation_id,
                )
            except Exception:
                pass
            return new_client
        except Exception as exc:
            try:
                from contextor.core.runtime_trace import trace_event

                trace_event(
                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
                    result="failed",
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                    exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                    recovery_operation_id=recovery_operation_id,
                )
            except Exception:
                pass
            self._emit(f"LIVE recovery failed: {exc}")
            return None
```


### DesktopLiveEventFeed.poll_once — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:1198-1315

```python
    def poll_once(self) -> None:
        if not self._poll_lock.acquire(blocking=False):
            return

        try:
            gap_reported = False

            while True:
                try:
                    response = self.client.get_events(
                        after_seq=self._last_seq,
                        limit=100,
                    )
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    return

                if response.get("status") != "ok":
                    return

                current_epoch = response.get("activity_epoch")
                previous_epoch = self._activity_epoch
                if current_epoch is not None and previous_epoch is not None and current_epoch != previous_epoch:
                    previous_cursor = self._last_seq
                    self._activity_epoch = str(current_epoch)
                    self._last_seq = 0
                    try:
                        from contextor.core.runtime_trace import trace_event
                        trace_event(
                            "GUI", "ACTIVITY_EPOCH_RESET",
                            previous_cursor=previous_cursor,
                            expected_seq=previous_cursor + 1,
                            received_first_seq=response.get("earliest_retained_seq"),
                            received_last_seq=response.get("latest_seq"),
                            previous_epoch=previous_epoch,
                            current_epoch=current_epoch,
                        )
                    except Exception:
                        pass
                    continue
                if current_epoch is not None and self._activity_epoch is None:
                    self._activity_epoch = str(current_epoch)

                if response.get("activity_resync_required") and not gap_reported:
                    from datetime import datetime, timezone

                    self._emit_status(
                        "[LIVE] Activity stream gap detected; some status events were not retained",
                        event={
                            "category": "ACTIVITY",
                            "operation": "activity_gap",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    try:
                        from contextor.core.runtime_trace import trace_event
                        seqs = [item.get("seq") for item in response.get("events", []) if isinstance(item, dict) and isinstance(item.get("seq"), int)]
                        trace_event(
                            "GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap",
                            previous_cursor=self._last_seq,
                            expected_seq=self._last_seq + 1,
                            received_first_seq=min(seqs) if seqs else response.get("earliest_retained_seq"),
                            received_last_seq=max(seqs) if seqs else response.get("latest_seq"),
                            previous_epoch=self._activity_epoch,
                            current_epoch=response.get("activity_epoch"),
                        )
                    except Exception:
                        pass
                    gap_reported = True

                events = response.get("events", [])
                if events:
                    try:
                        from contextor.core.runtime_trace import trace_event
                        seqs = [item.get("seq") for item in events if isinstance(item, dict) and isinstance(item.get("seq"), int)]
                        trace_event("GUI", "EVENT_BATCH_RECEIVED", count=len(events), rev=response.get("revision"), seq=response.get("latest_seq"), first_seq=min(seqs) if seqs else None, last_seq=max(seqs) if seqs else None)
                    except Exception:
                        pass

                previous_cursor = self._last_seq

                for event in events:
                    seq = event.get("seq")

                    # Defensive duplicate protection.
                    if isinstance(seq, int) and seq <= self._last_seq:
                        continue

                    key = self._authority_key(event) if event.get("category") == "AUTHORITY" else None
                    message = None if key is not None and key in self._replayed_authority_keys else self._message(event)
                    if message:
                        self._emit_status(message, event)

                    if isinstance(seq, int):
                        self._last_seq = seq
                        if key is not None:
                            self._replayed_authority_keys.discard(key)

                # No more pages.
                if not response.get("truncated", False):
                    break

                # Fail closed against an impossible/non-progressing page.
                # Never spin forever and never jump to latest_seq.
                if self._last_seq == previous_cursor:
                    from datetime import datetime, timezone

                    self._emit_status(
                        "[LIVE] Activity stream pagination stalled",
                        event={
                            "category": "ACTIVITY",
                            "operation": "activity_pagination_stalled",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    break

        finally:
            self._poll_lock.release()
```


### _LiveFilesystemEventHandler.on_modified — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:96-98

```python
    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)
```


### CanonicalMutationCoordinator.__init__ — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:128-146

```python
    def __init__(
        self,
        executor: Callable[[dict[str, Any]], dict[str, Any]],
        revision_reader: Callable[[], int],
        *,
        retention: int = _MUTATION_JOB_RETENTION,
    ):
        self._executor = executor
        self._revision_reader = revision_reader
        self._retention = retention
        self._condition = threading.Condition()
        self._queue: deque[str] = deque()
        self._jobs: OrderedDict[str, _MutationJob] = OrderedDict()
        self._idempotency_jobs: dict[str, str] = {}
        self._thread: threading.Thread | None = None
        self._accepting = True
        self._stop = False
        self._queue_order = 0
        self._recovery_verification_fenced = False
```


### _select_admission_trace_fields — C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py:67-77

```python
def _select_admission_trace_fields(
    fields: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if fields is None:
        return {}

    return {
        name: fields[name]
        for name in _ADMISSION_TRACE_FIELD_NAMES
        if name in fields and fields[name] is not None
    }
```


### _canonical_writer_admission — C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py:121-205

```python
@contextmanager
def _canonical_writer_admission(
    *,
    lock_file: Path,
    key: str,
    repo_id: str,
    owner: str,
    writer_kind: str,
    deadline: float | None,
    poll_interval: float,
    is_cancelled: Callable[[], bool] | None,
    admission_trace_fields: Mapping[str, Any] | None,
):
    trace_fields = _select_admission_trace_fields(
        admission_trace_fields
    )
    process_lock = _get_admission_lock(key)
    started = time.monotonic()
    _acquire_process_lock_until(
        process_lock,
        deadline=deadline,
        poll_interval=poll_interval,
        is_cancelled=is_cancelled,
        cancel_message=(
            "Canonical writer admission cancelled while waiting for local gate."
        ),
        timeout_message=(
            "Timed out waiting for canonical writer admission gate for "
            f"{repo_id}"
        ),
    )
    fd = -1
    os_locked = False
    admission_path = lock_file.with_name("canonical_writer.admission.lock")
    try:
        fd = _prepare_lock_fd(admission_path)
        while True:
            if is_cancelled and is_cancelled():
                raise AnalysisCancelled(
                    "Canonical writer admission cancelled while waiting for "
                    "repository gate."
                )
            if _try_lock_fd(fd):
                os_locked = True
                break
            if deadline is not None and time.monotonic() >= deadline:
                raise FullAnalysisBusyError(
                    "Timed out waiting for canonical writer admission gate for "
                    f"{repo_id}"
                )
            time.sleep(min(max(poll_interval, 0.01), 0.25))
        trace_event(
            "ANALYSIS",
            "CANONICAL_WRITER_ADMISSION_ACQUIRED",
            repo_id=repo_id,
            owner=owner,
            writer_kind=writer_kind,
            wait_ms=(time.monotonic() - started) * 1000.0,
            **trace_fields,
        )
        yield
    finally:
        try:
            if fd >= 0:
                if os_locked:
                    _unlock_fd(fd)
                else:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
        finally:
            try:
                process_lock.release()
            except RuntimeError:
                pass
            if os_locked:
                trace_event(
                    "ANALYSIS",
                    "CANONICAL_WRITER_ADMISSION_RELEASED",
                    repo_id=repo_id,
                    owner=owner,
                    writer_kind=writer_kind,
                    **trace_fields,
                )
```


### acquire_full_analysis — C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py:410-588

```python
def acquire_full_analysis(
    repo_path: str | Path,
    *,
    owner: str = "desktop_analysis",
    writer_kind: str = "full_analysis",
    timeout: float | None = None,
    poll_interval: float = 0.25,
    is_cancelled: Callable[[], bool] | None = None,
    log: Callable[[str], None] | None = None,
    admission_trace_fields: Mapping[str, Any] | None = None,
) -> FullAnalysisLease:
    """
    Acquire exclusive single-writer lease for full repository analysis.
    Blocks if another process or thread holds the lease until released,
    timed out, or cancelled.
    """
    if writer_kind not in {
        "full_analysis",
        "live_mutation",
        "startup_publish",
        "local_incremental",
        "scoped_analysis",
    }:
        raise ValueError(
            "writer_kind must be 'full_analysis', 'live_mutation', "
            "'startup_publish', 'local_incremental', or 'scoped_analysis'"
        )

    lock_file, key, repo_id = _resolve_lock_path(repo_path)
    proc_lock = _get_process_lock(key)

    start_time = time.monotonic()
    deadline = (
        start_time + timeout
        if timeout is not None
        else None
    )

    with _canonical_writer_admission(
        lock_file=lock_file,
        key=key,
        repo_id=repo_id,
        owner=str(owner),
        writer_kind=writer_kind,
        deadline=deadline,
        poll_interval=poll_interval,
        is_cancelled=is_cancelled,
        admission_trace_fields=admission_trace_fields,
    ):
        _acquire_process_lock_until(
            proc_lock,
            deadline=deadline,
            poll_interval=poll_interval,
            is_cancelled=is_cancelled,
            cancel_message="Full analysis cancelled while waiting for local lock.",
            timeout_message=(
                "Timed out waiting for in-process full analysis lock for "
                f"{repo_id}"
            ),
        )
        fd = -1
        logged_waiting = False
        logged_recovery = False
        orphan_recovery_deadline: float | None = None
        unknown_owner_deadline: float | None = None
        try:
            fd = _prepare_lock_fd(lock_file)

            while True:
                if is_cancelled and is_cancelled():
                    raise AnalysisCancelled(
                        "Full analysis cancelled while waiting for repository lease."
                    )

                previous_metadata = _read_lease_metadata(fd)
                if previous_metadata is None:
                    previous_metadata = _read_lease_metadata_file(
                        _lease_metadata_path(lock_file)
                    )
                if _try_lock_fd(fd):
                    previous_owner_state, previous_owner_reason = _lease_owner_state(
                        previous_metadata
                    )
                    if previous_owner_state == "orphaned" and not logged_recovery:
                        _log_orphan_recovery(
                            log,
                            repo_id,
                            previous_owner_reason,
                        )
                        logged_recovery = True
                    token = uuid.uuid4().hex

                    owner_image, owner_process_start_identity, _ = _process_identity(
                        os.getpid()
                    )

                    metadata = {
                        "pid": os.getpid(),
                        "token": token,
                        "owner": str(owner),
                        "repo_id": str(repo_id),
                        "timestamp": time.time(),
                    }
                    if owner_image:
                        metadata["executable"] = owner_image
                    if owner_process_start_identity is not None:
                        metadata["process_start_identity"] = owner_process_start_identity

                    _write_lease_metadata_file(
                        _lease_metadata_path(lock_file),
                        metadata,
                    )

                    # Metadata is diagnostic only.
                    # OS lock ownership is authoritative.
                    os.ftruncate(fd, 0)
                    os.lseek(fd, 0, os.SEEK_SET)
                    os.write(
                        fd,
                        json.dumps(metadata).encode("utf-8"),
                    )
                    os.fsync(fd)

                    # Ensure byte 0 remains inside the locked file after metadata write.
                    os.lseek(fd, 0, os.SEEK_SET)

                    lease = FullAnalysisLease(
                        repo_key=key,
                        token=token,
                        owner=str(owner),
                        lock_path=str(lock_file),
                        repo_id=str(repo_id),
                        lock_fd=fd,
                        owner_pid=os.getpid(),
                        owner_process_start_identity=owner_process_start_identity,
                    )
                    fd = -1
                    return lease

                if not logged_waiting:
                    if log:
                        log(f"Waiting for full analysis lease on repository {repo_id}...")
                        owner_state, owner_reason = _lease_owner_state(previous_metadata)
                        if owner_state == "active":
                            log("Full analysis lease has a valid active owner " f"({owner_reason}).")
                        elif owner_state == "unknown":
                            log("Full analysis lease owner could not be verified; " f"continuing to wait ({owner_reason}).")
                    logged_waiting = True

                owner_state, owner_reason = _lease_owner_state(previous_metadata)
                if owner_state == "orphaned":
                    unknown_owner_deadline = None
                    if orphan_recovery_deadline is None:
                        orphan_recovery_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
                    if not logged_recovery:
                        _log_orphan_recovery(log, repo_id, owner_reason)
                        logged_recovery = True
                    if time.monotonic() >= orphan_recovery_deadline:
                        raise FullAnalysisBusyError(f"Timed out recovering orphaned full analysis lease for {repo_id}")
                elif owner_state == "unknown":
                    orphan_recovery_deadline = None
                    if unknown_owner_deadline is None:
                        unknown_owner_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
                    if time.monotonic() >= unknown_owner_deadline:
                        raise FullAnalysisBusyError(f"Timed out waiting because full analysis lease owner could not be verified for {repo_id}")
                else:
                    orphan_recovery_deadline = None
                    unknown_owner_deadline = None
                if deadline is not None and time.monotonic() >= deadline:
                    raise FullAnalysisBusyError(f"Repository {repo_id} is currently locked for full analysis")
                time.sleep(min(max(poll_interval, 0.01), 0.25))
        except Exception:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            proc_lock.release()
            raise
```


### release_full_analysis — C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py:591-610

```python
def release_full_analysis(
    lease: FullAnalysisLease,
) -> None:
    """Release the full analysis lease."""
    if not isinstance(
        lease,
        FullAnalysisLease,
    ):
        return

    try:
        _unlock_fd(lease.lock_fd)
    finally:
        proc_lock = _get_process_lock(
            lease.repo_key
        )
        try:
            proc_lock.release()
        except RuntimeError:
            pass
```


### CanonicalMutationCoordinator._prune_terminal_locked — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:272-282

```python
    def _prune_terminal_locked(self) -> None:
        terminal = {"completed", "failed", "cancelled"}
        while sum(job.state in terminal for job in self._jobs.values()) > self._retention:
            for job_id, job in self._jobs.items():
                if job.state in terminal:
                    del self._jobs[job_id]
                    if self._idempotency_jobs.get(job.idempotency_key) == job_id:
                        del self._idempotency_jobs[job.idempotency_key]
                    break
            else:
                break
```


### DesktopLiveWatcher._candidate_requires_update — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:552-576

```python
    def _candidate_requires_update(
        self,
        path: str,
        current: dict[str, tuple[int, int]],
        snapshot: dict | None = None,
        trusted_manager=None,
    ) -> bool | None:
        """Revalidate a queued path against the generation held after the lease wait."""
        if snapshot is None:
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                return None
        manager = trusted_manager if trusted_manager is not None else self._trusted_file_state(snapshot)
        if manager is None:
            self._startup_requires_resync = True
            return None
        if path not in current:
            return path in manager.tracked_paths()
        state = snapshot.get("state")
        modules = getattr(state, "modules", {})
        return (
            manager.has_changed(path)
            or self._module_name(Path(path)) not in modules
        )
```


### DesktopLiveWatcher.poll_once, contiguous part 1 — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:667-820

```python
    def poll_once(self) -> list[str]:
        if self._recovery_rebaseline_pending:
            if self._recovery_is_active():
                return []
            try:
                live_snapshot = self.client.snapshot()
                if not isinstance(live_snapshot, dict) or live_snapshot.get("status") != "ok":
                    return []
                state = live_snapshot.get("state")
                revision = live_snapshot.get("revision")
                state_id = getattr(state, "state_id", None)
                modules = getattr(state, "modules", None)
                if (
                    isinstance(revision, bool)
                    or not isinstance(revision, int)
                    or revision < 1
                    or getattr(state, "revision", None) != revision
                    or not isinstance(state_id, str)
                    or not state_id
                    or not isinstance(modules, dict)
                ):
                    return []
                manager = self._trusted_file_state(live_snapshot)
                if manager is None:
                    return []
                current_scan = self._scan()
                pending = set(self._startup_pending)
                pending.update(self._pending_intents)
                pending.update(self._ambiguous_updates)
                pending.update(
                    path for path in current_scan
                    if manager.has_changed(path)
                    or self._module_name(Path(path)) not in modules
                )
                for tracked_path in manager.tracked_paths():
                    normalized = self._normalize_watch_path(tracked_path)
                    if normalized is not None and normalized not in current_scan:
                        pending.add(normalized)
            except Exception:
                return []
            # Every path above was compared with the verified LIVE generation.
            # Commit the local scan only after preserving all outstanding work.
            self._snapshot = current_scan
            self._startup_pending = sorted(pending)
            for pending_path in self._startup_pending:
                self._enqueue_path(pending_path, wake=False)
            self._recovery_rebaseline_pending = False
        reconciled = self._poll_inflight_updates()
        if self._recovery_is_active():
            return reconciled
        changed = self._drain_pending()
        using_startup_pending = not changed and bool(self._startup_pending)
        if using_startup_pending:
            changed = list(self._startup_pending)
        if not changed and not self._startup_requires_resync:
            return reconciled
        current: dict[str, tuple[int, int]] = {}
        for path in changed:
            try:
                stat = Path(path).stat()
                current[path] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
        ping_started = time.monotonic()
        try:
            status = self.client.ping()
        except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
            self._emit("LIVE: connection lost; recovering...")
            if self._recover_client(exc) is None:
                raise
            status = self.client.ping()
        ping_ms = (time.monotonic() - ping_started) * 1000.0

        if not status.get("available"):
            self._requeue_paths(changed)
            self._emit("LIVE: no snapshot; waiting for analysis")
            return reconciled
        if self._startup_requires_resync:
            if self._startup_resync_attempted:
                self._requeue_paths(changed)
                return reconciled
            self._startup_resync_attempted = True
            if self.on_resync is None:
                self._requeue_paths(changed)
                self._emit("LIVE: canonical baseline requires resync")
                return reconciled
            try:
                outcome = self.on_resync()
                if not self._resync_completed(outcome):
                    self._requeue_paths(changed)
                    self._emit("LIVE: startup resync failed; baseline remains untrusted")
                    return []
            except Exception as exc:
                self._requeue_paths(changed)
                self._emit(f"LIVE: startup resync failed: {exc}")
                return reconciled
            current = self._scan()
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                self._requeue_paths(changed)
                self._emit("LIVE: startup resync baseline could not be verified")
                return reconciled
            if self._trusted_file_state(snapshot) is None:
                self._requeue_paths(changed)
                self._emit("LIVE: startup resync baseline remains untrusted")
                return []
            self._snapshot = current
            self._startup_pending = self._startup_reconciliation_paths(current)
            self._startup_requires_resync = False
            self._requeue_paths(self._startup_pending)
            return reconciled
        deferred: list[str] = []
        try:
            batch_snapshot = self.client.snapshot()
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled
        batch_manager = self._trusted_file_state(batch_snapshot)
        if batch_manager is None:
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled

        try:
            candidate_decisions = {
                path: self._candidate_requires_update(
                    path, current, batch_snapshot, batch_manager
                )
                for path in changed
            }
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled

        for path_index, path in enumerate(changed):
            if self._recovery_is_active():
                deferred.extend(changed[path_index:])
                break
            from contextor.core.runtime_trace import new_trace_operation, trace_event

            op = new_trace_operation("u")
            old_present = path in self._snapshot
            current_present = path in current
            kind = "create" if not old_present and current_present else "delete" if old_present and not current_present else "modify"
            relative = None
            try:
                relative = Path(path).resolve().relative_to(self.root).as_posix()
            except ValueError:
                pass
            mtime_ns = current.get(path, (None, None))[0]
            trace_event(
```


### DesktopLiveWatcher.poll_once, contiguous part 2 — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:821-973

```python
                "LIVE", "FS_CHANGE_DETECTED", op=op, repo=str(self.root),
                path=relative, kind=kind, rev=status.get("revision"),
                discovery="watchdog", ping_ms=ping_ms, mtime_ns=mtime_ns,
            )
            self._emit(f"Updating LIVE: {Path(path).name}")
            update_started = time.monotonic()
            trace_event("LIVE", "WATCH_UPDATE_START", op=op, repo=str(self.root), path=relative)
            was_ambiguous = path in self._ambiguous_updates
            try:
                candidate_requires_update = candidate_decisions[path]
                if candidate_requires_update is None:
                    deferred.append(path)
                    if was_ambiguous:
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                if not candidate_requires_update:
                    def accept_unchanged_path() -> bool:
                        self._pending_intents.pop(path, None)
                        if was_ambiguous:
                            self._ambiguous_updates.discard(path)
                        if path in current:
                            self._snapshot[path] = current[path]
                        else:
                            self._snapshot.pop(path, None)
                        return True

                    admitted = self._admit_recovery_action(accept_unchanged_path)
                    if admitted is RECOVERY_DEFERRED:
                        deferred.extend(changed[path_index:])
                        break
                    if was_ambiguous:
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
                    reconciled.append(path)
                    continue
                current_state = current.get(path)
                current_sha256: str | None = None
                if current_state is not None:
                    try:
                        file_state = batch_manager.get_current_file_state(
                            path, compute_hash=True
                        )
                        post_hash_state = batch_manager.get_current_file_state(
                            path, compute_hash=False
                        )
                    except OSError:
                        file_state = None
                        post_hash_state = None
                    if (
                        file_state is None
                        or (
                            file_state.mtime_ns,
                            file_state.size,
                        )
                        != current_state
                        or not file_state.sha256
                        or post_hash_state is None
                        or (
                            post_hash_state.mtime_ns,
                            post_hash_state.size,
                        )
                        != current_state
                    ):
                        deferred.append(path)
                        self._emit(
                            "LIVE: mutation identity capture unavailable; deferring watcher update"
                        )
                        continue
                    current_sha256 = file_state.sha256
                pending_intent = self._pending_intents.get(path)
                current_inflight = next(
                    (
                        job
                        for job in self._inflight_updates.values()
                        if job.path == path
                        and job.observed_state == current_state
                        and job.observed_sha256 == current_sha256
                    ),
                    None,
                )
                if current_inflight is not None:
                    if pending_intent is not None:
                        def clear_duplicate_intent() -> bool:
                            self._pending_intents.pop(path, None)
                            self._ambiguous_updates.discard(path)
                            return True

                        admitted = self._admit_recovery_action(clear_duplicate_intent)
                        if admitted is RECOVERY_DEFERRED:
                            deferred.extend(changed[path_index:])
                            break
                    continue
                if pending_intent is None:
                    pending_intent = _PendingMutationIntent(
                        idempotency_key=uuid.uuid4().hex,
                        path=path,
                        trace_op=op,
                        observed_state=current_state,
                        started_at=update_started,
                        observed_sha256=current_sha256,
                    )
                    self._pending_intents[path] = pending_intent
                response = self._admit_recovery_action(
                    lambda: self.client.submit_update_file(
                        path,
                        origin="desktop_watcher",
                        trace_op=pending_intent.trace_op,
                        idempotency_key=pending_intent.idempotency_key,
                    )
                )
                if response is RECOVERY_DEFERRED:
                    deferred.extend(changed[path_index:])
                    break
                if was_ambiguous:
                    self._ambiguous_updates.discard(path)
                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                self._ambiguous_updates.add(path)
                trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
                deferred.append(path)
                continue
            job_id = response.get("job_id") if isinstance(response, dict) else None
            if (
                not isinstance(response, dict)
                or response.get("status") != "accepted"
                or response.get("accepted") is not True
                or not isinstance(job_id, str)
                or not job_id
            ):
                deferred.append(path)
                self._emit("LIVE: update submission was not accepted; deferring watcher update")
                continue
            self._pending_intents.pop(path, None)
            self._inflight_updates[job_id] = _WatcherMutationJob(
                job_id,
                pending_intent.path,
                pending_intent.trace_op,
                pending_intent.idempotency_key,
                pending_intent.observed_state,
                pending_intent.started_at,
                pending_intent.observed_sha256,
            )
            if (
                current.get(path) != pending_intent.observed_state
                or current_sha256 != pending_intent.observed_sha256
            ):
                deferred.append(path)
        if deferred:
            self._requeue_paths(deferred)
        elif self._startup_pending and set(self._startup_pending).issubset(set(changed)):
            self._startup_pending = []
        return reconciled + self._poll_inflight_updates()
```


### CanonicalLiveServer._execute_update_file, contiguous part 1 — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1884-2020

```python
    def _execute_update_file(
        self, request: dict[str, Any], *, allow_recovery_fence: bool = False
    ) -> dict[str, Any]:
        if (
            not allow_recovery_fence
            and self._mutation_coordinator.recovery_verification_active()
        ):
            return {
                "status": "error",
                "error": "recovery_verification_in_progress",
                "accepted": False,
            }
        with self._mutation_execution_lock:
            if (
                not allow_recovery_fence
                and self._mutation_coordinator.recovery_verification_active()
            ):
                return {
                    "status": "error",
                    "error": "recovery_verification_in_progress",
                    "accepted": False,
                }
            with self._lock:
                if self._state is None or self._updater is None:
                    return {
                        "status": "error",
                        "error": "live_state_unavailable",
                    }
                previous_state = self._state
                previous_revision = self._revision
                expected_revision = previous_revision + 1
                updater = self._updater
                persister = self._persister

            file_path = str(request.get("file_path", ""))
            trace_op = _safe_trace_op(request, "u")
            if trace_op is not None:
                request = {**request, "trace_op": trace_op}
            _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)

            try:
                candidate_state = _clone_state_for_update(previous_state)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
                return {
                    "status": "error",
                    "error": "canonical_state_clone_failed",
                    "revision": previous_revision,
                    "expected_revision": expected_revision,
                    "detail": str(exc),
                }
            _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)

            # IMPORTANT: updater operates ONLY on candidate_state.
            # It must never receive previous_state/self._state directly.
            _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
            updater_started = time.monotonic()
            try:
                with _trace_operation_context(trace_op):
                    result = updater(candidate_state, file_path)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
                raise
            _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))

            try:
                state_rev = _extract_state_revision(candidate_state)
            except ValueError:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "invalid_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if state_rev is None:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": None,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev == previous_revision:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev < previous_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "non_monotonic_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev > expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            # Final parity proof before commit.
            if _extract_state_revision(candidate_state) != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "canonical_revision_binding_failed",
```


### CanonicalLiveServer._execute_update_file, contiguous part 2 — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2021-2148

```python
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if persister is not None:
                _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
                try:
                    with _trace_operation_context(trace_op):
                        persister(candidate_state, expected_revision)
                except Exception as exc:
                    from .store import SnapshotRevisionConflict

                    status = (
                        "canonical_persistence_revision_conflict"
                        if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
                        else "canonical_persistence_failed"
                    )
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
                    response = {
                        "status": "error",
                        "error": status,
                        "revision": previous_revision,
                        "expected_revision": expected_revision,
                    }
                    persisted_revision = getattr(exc, "current_revision", None)
                    if persisted_revision is not None:
                        response["persisted_revision"] = persisted_revision
                        response["resync_required"] = True
                    return response
                _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)

            with self._lock:
                if self._revision != previous_revision or self._state is not previous_state:
                    _safe_trace_event(
                        "LIVE",
                        "UPDATE_FAIL",
                        op=trace_op,
                        path=file_path,
                        rev=self._revision,
                        status="canonical_revision_changed_during_update",
                        expected_revision=expected_revision,
                    )
                    return {
                        "status": "error",
                        "error": "canonical_revision_changed_during_update",
                        "revision": self._revision,
                        "expected_revision": expected_revision,
                    }

                # ATOMIC COMMIT BOUNDARY.
                # Nothing above this line may replace/mutate active canonical ownership.
                self._state = candidate_state
                self._revision = expected_revision
                _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)

                try:
                    diagnostic_delta = _build_diagnostic_delta(
                        previous_state, self._state
                    )
                except Exception:
                    diagnostic_delta = []
                diagnostic_payload = _bounded_diagnostic_payload(diagnostic_delta)
                event_request = dict(request)
                # Request payload is untrusted metadata: only the committed-state
                # comparison may publish diagnostic evidence.
                event_request.pop("diagnostic_changes", None)
                if diagnostic_payload is not None:
                    event_request["diagnostic_changes"] = diagnostic_payload

                evt = self._record_event(
                    "update_file",
                    event_request,
                    result,
                    category="LIVE_STATE",
                )
                committed_revision = self._revision
                committed_seq = evt["seq"]

            _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=committed_revision, seq=committed_seq, status=getattr(result, "status", None))
            origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
            trace_common = {
                "repo": self._authority_identity.get("root_path"),
                "repo_id": self._authority_identity.get("repo_id"),
                "origin": origin,
                "diagnostic_total": len(diagnostic_delta),
                "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
            }
            for change in diagnostic_delta:
                event_name = _diagnostic_trace_event_name(change)
                if event_name is None:
                    continue
                trace_fields = {
                    **trace_common,
                    "diagnostic_kind": change["diagnostic_kind"],
                    "diagnostic_key": change["diagnostic_key"],
                }
                if "source_path" in change:
                    trace_fields["path"] = change["source_path"]
                if change["diagnostic_kind"] == "syntax":
                    trace_fields.update(
                        error=change["message"],
                        line_number=change["line_number"],
                        column_number=change["column_number"],
                    )
                elif change["diagnostic_kind"] == "collision":
                    for field in (
                        "collision_kind",
                        "collision_artifact_type",
                        "collision_symbol",
                        "collision_is_identical",
                        "collision_nodes",
                    ):
                        trace_fields[field] = change[field]
                else:
                    trace_fields["cycle_nodes"] = change["cycle_nodes"]
                _safe_trace_event(
                    "LIVE", event_name, op=trace_op, rev=committed_revision, **trace_fields
                )

            return {
                "status": "ok",
                "activity_epoch": self._activity_epoch,
                "revision": committed_revision,
                "result": result,
                "seq": committed_seq,
            }
```


## ABSOLUTE_SOURCE_PATHS

- `C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`
- `C:\Temp\Contextor_Repo\contextor\core\runtime_trace.py`
- `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`
- `C:\Temp\Contextor_Repo\tests\test_watcher_recovery_admission.py`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`
- `C:\Users\DafoO\AppData\Roaming\Contextor\logs\contextor_runtime_20261011_154204_448_5328.jsonl`

## TARGETED_TEST_RESULTS

NOT_RUN in this read-only task. Existing named test source and asercje zweryfikowano; rzeczywisty runtime proof jest silniejszy niż fixture. Nie uruchomiono pełnego suite, analizy repo ani update_file.

## PROVED_DEFECTS

NONE dla badanej operacji. Brak `origin_verified` w update event to ograniczenie atrybucji pola origin; obserwowany łańcuch ma niezależne procesowe trace capture i ACK. Nie ma dowodu błędnego commitu, ownership, ACK ani replay.

## UNRESOLVED_EVIDENCE_GAPS

- Nie ma jednego zautomatyzowanego testu real runtime E2E dla wszystkich czterech etapów; obecne testy obejmują fragmenty.
- Journal i ACK trace pomijają niektóre identyfikatory job; dla op `u-5328-5` op/path/rev/seq + kod i process identity wystarczają. Bez aktywnego trace sama publiczna odpowiedź `get_live_events` byłaby niewystarczająca.
- `trace_op` nie jest kryptograficznym dowodem autorstwa. Realny Desktop PID i source trace są podstawą przypisania tej konkretnej operacji watcherowi.
- Nie weryfikowano przyszłych retry/UNKNOWN w żywym runtime ani długoterminowej retencji logów; ich zachowanie jest CODE_PATH_PROVED/TEST_PROVED, nie RUNTIME_OBSERVED.
- Dane z trace są diagnostyczne i best-effort; znalezienie pełnego chain nie dowodzi, że każdy przyszły chain będzie kompletnie logowany.

## LIVE_REVISION_BEFORE_AFTER

Przed: 328. Po końcowym Contextor MCP check: 328. Jedna retained mutation revision 328; brak nowego canonical commit podczas audytu. `get_live_events(after_revision=327)` continuous, one event. cycles.count=0, availability=fresh.

## WORKSPACE_SYNC_POSTCHECK

Końcowe `get_symbol_implementation` dla `_poll_inflight_updates`: status resolved, implementation complete, workspace_sync=verified, canonical_state=fresh, revision 328. `git status --short` i `git diff --stat`: empty przed zapisem raportu. Jedynym zapisem tego zadania jest walkthrough.md.

## RESYNC_REQUIRED

false; activity_resync_required=false w pełnym retained IPC window; publiczne `get_live_events(after_revision=327)` także false.

## RESTART_REQUIRED

NO. Żadnego kodu źródłowego/testowego nie edytowano. Nie restartowano MCP, LIVE ani Desktop.

## FINAL_VERDICT

**L11_COMPLETE_RUNTIME_PROOF_FOUND** — dla rzeczywistej operacji `u-5328-5` zachowany, nieobcięty trace i event LIVE potwierdzają capture→writer admission→durable/canonical commit→watcher terminal ACK, z tym samym op, path, procesami, rewizją 327→328 i seq 88. Ten werdykt dotyczy jednej konkretnej obserwowanej operacji.

