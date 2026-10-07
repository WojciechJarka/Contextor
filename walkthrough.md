# CPA_BACKEND_OWNER_LEASE_IMPLEMENTATION_CONTEXT

DATA=2026-10-07
SCOPE=DISCOVERY/RETRIEVAL ONLY
REPOSITORY=C:\Temp\Contextor_Repo
CURRENT_HEAD=2f98c4a884f945e37796fdcfb13c971833123f56
SOURCE_TREE_STATUS_BEFORE_REPORT=CLEAN
FILES_CHANGED=NONE
DIFFS=NONE
TESTS_EXECUTED=NO

## Evidence provenance

- Contextor MCP canonical LIVE revision: 1606.
- Fetched symbol implementations report `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`.
- The targeted `get_symbol_lineage` projections for `start_backend`, `connect_or_start`, `claim_desktop`, and `RuntimeLeaseManager._new_lease` report complete/metadata-consistent lineage. Their lineage envelopes report `workspace_sync=unverified`; use them only as graph evidence. The executable code evidence below comes from verified symbol fetches and exact Contextor source ranges.
- Call-context evidence is bounded to intra-module edges. Cross-module direct consumers below come from Contextor artifact consumer projections and the resolved source implementations.
- No tests were run, no source/test/docs files were changed, no repository-wide analysis was run.

## Direct answers A-I

### A. Gdzie powstaje backend `instance_id`

`contextor.mcp_backend_state::PersistentBackendLease.acquire` tworzy `PersistentBackendRecord` i ustawia `instance_id=uuid.uuid4().hex`. Jest to identyfikator instancji procesu backendu, nie zewnętrznego hosta. Rekord dodatkowo przechowuje PID, executable i process creation time.

### B. Kto dziś posiada lifetime lock

Lock `%CONTEXTOR_STATE_DIR%/mcp_backend/backend.lock` (domyślnie `%APPDATA%/Contextor/mcp_backend/backend.lock`) jest nabywany przez `PersistentBackendLease.acquire`, wywołane w procesie Contextor MCP `mcp_server.main` z rolą `persistent-backend`. Uchwyt pozostaje otwarty do `PersistentBackendLease.release` w ścieżce `finally` / `atexit`, a przy zakończeniu procesu system operacyjny zwalnia blokadę pliku. To nie jest lock Desktop/EXTERNAL_HOST.

### C. Co utrzymuje persistent backend przy życiu

Po `start_backend`, proces jest uruchamiany jako osobny `python -u -m contextor.mcp_main` z stdin/stdout/stderr skierowanymi do `DEVNULL` i flagą Windows breakaway/no-window. Proces sam przejmuje lifetime lock, zapisuje `backend.json` i czeka w `asyncio.run(_run())` na `mcp.run_http_async(...)`. Nie ma w tym backend lifecycle owner lease, host PID, host token ani okresowego heartbeat/watchdog.

### D. Jak backend wykrywa własny shutdown

W widocznym lifecycle backend nie ma pętli wykrywającej utratę hosta. Jawne zatrzymanie wykonuje zewnętrzny `stop_backend`: sprawdza dokładną tożsamość procesu z rekordu, wywołuje identity-scoped terminację i czeka na wyjście procesu. Naturalny exit/awaria procesu uruchamia kod końcowy `mcp_server.main`, który czyści procesy potomne i zwalnia backend lease. Po twardym zakończeniu procesowym rekord może pozostać; kolejny `get_backend_status` klasyfikuje go jako stale po sprawdzeniu PID/creation identity/executable.

### E. Czy backend ma okresową pętlę/heartbeat

Nie znaleziono backendowej pętli owner heartbeat/watchdog w lifecycle implementation. Persisted backend ma rekord i OS lifetime lock; `mcp_server.main` czeka na HTTP server. Helpery do readiness polling są wyłącznie w starterze/control process. LIVE ma osobną owner watchdog (poniżej); nie jest używany przez persistent MCP backend.

### F. Trwała tożsamość klienta w HTTP MCP

Widoczny Contextor HTTP auth weryfikuje wyłącznie bearer token. `verify_token` zwraca zawsze ten sam `client_id="contextor-local"`, `scopes=[]`, `claims={}`, bez expiry i bez per-host ID. `build_backend_http_headers` tworzy tylko nagłówek `Authorization: Bearer <token>`. W kontrolowanym lifecycle nie znaleziono trwałego EXTERNAL_HOST identity poza współdzielonym sekretem. Ewentualny MCP transport/session metadata nie jest wiązany z backend owner record.

### G. Czy backend może obsługiwać wiele EXTERNAL_HOST

CODE_PATH_PROVED: backend jest współdzielony przez wiele wywołujących `start_backend` (gotowy backend jest zwracany bez spawnowania nowego), a auth nie identyfikuje hosta osobno. INFERENCE: warstwa lifecycle nie ma single-host admission/claim i nie blokuje wielu HTTP MCP klientów posiadających ten sam bearer. Jednoczesna współpraca różnych hostów nie ma osobnego targeted testu w zebranym katalogu, więc nie klasyfikuję jej jako bezpośrednio certyfikowanej.

### H. Jak LIVE rozwiązuje utratę Desktop ownera; co jest reusable

- GUI tworzy własne `owner_token` i `desktop_instance_id` jako losowe UUID. Dla desktopowego połączenia przekazuje PID, owner token, desktop instance ID i process-start identity.
- `connect_or_start` uruchamia proces LIVE z argumentami owner PID/token/Desktop identity albo dołącza do istniejącej instancji.
- Po gotowości `run_service` uruchamia watchdog sprawdzający owner PID co 0,75 s. Na Windows otwiera process handle i czeka na śmierć tego konkretnego procesu; poza Windows sprawdza PID przez `_is_pid_alive`. Po utracie ownera wywołuje `server.close()`.
- Finalizacja LIVE domyka serwer/mutation worker, zwalnia dokładny lease albo go fence'uje i usuwa endpoint tylko dla rozwiązanej własności.
- Desktop claim przechowuje service instance/generation oraz Desktop ID, PID i start identity. Przy nowym claimie LIVE weryfikuje istniejący Desktop PID/start identity; stary claim może zostać atomowo zastąpiony, a unknown probe jest fail-closed.
- Token Desktop jest używany przez GUI close path do autoryzacji jawnego `shutdown`; watchdog cykliczny monitoruje PID, nie porównuje owner token ani Desktop ID.
- W runtime_lease jest `refresh_heartbeat`, ale Contextor call-context i consumer catalog nie wskazały statycznych callerów, a zebrany pełny `run_service` nie zawiera jego wywołania ani okresowego heartbeat.

### I. Testy dowodzące singleton/reuse/stale/termination

Zebrane nazwy testów i zakres ich kontraktu są w końcowej sekcji `TESTS_RELEVANT_TO_OWNER_LEASE`. Szczególnie backend: same/cross process singleton lifetime lease, rejection drugiego persistent servera, reuse gotowego backendu, stale-record cleanup oraz stop ograniczony exact recorded identity. LIVE ma testy PID reuse, fencing stale generation, replacement dead Desktop claim oraz zachowania GUI close dla owner/unowned client. Testy zostały tylko zindeksowane w Contextor; nie były uruchamiane.

## Direct callers, consumers, state and test index

| Symbol / ABSOLUTE_PATH | Bezpośredni production callers / consumer evidence | Współdzielony stan / lock / pliki | Zebrane targeted tests |
|---|---|---|---|
| `PersistentBackendRecord`, `PersistentBackendLease`, `read_backend_record`, `_write_record`, `remove_backend_record_if_exact`, `_BackendLifetimeLock` — `C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py` | `PersistentBackendLease.acquire` jest wołane przez `contextor.mcp_server.main`; release jest wykonywane z `finally` i `atexit`. Record jest tworzony przez acquire, czytany przez control, usuwany przez lease release/control. Contextor konsumenci: `contextor.mcp_server`, `contextor.mcp_backend_control`, testy state/shared/control. | `backend.json`, `backend.lock`; per-process thread-lock registry + OS file lock; atomic JSON replace. | `tests.test_mcp_backend_state`, `tests.test_mcp_shared_backend_server_mode`, `tests.test_mcp_backend_control`. |
| `_BackendControlLock`, `start_backend`, `_spawn_backend_process`, `_wait_for_ready_backend`, `get_backend_status`, `stop_backend` — `C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py` | `start_backend`: `mcp_backend_autostart.launch_backend_autostart`, `mcp_backend_cli.main`, `ContextorGUI._restart_backend`. `get_backend_status` / `stop_backend`: CLI i GUI restart; start/stop używają statusu wewnętrznie. Spawn/wait są callee start_backend. | `control.lock` serializuje start/stop; `backend.json`, `backend.lock`, `processes/`, token; spawn Popen i identity record. | `tests.test_mcp_backend_control`, CLI, autostart, GUI restart, state/shared server-mode. |
| Process registry identity/termination — `C:\\Temp\\Contextor_Repo\\contextor\\mcp_process_registry.py` | Backend status/stop call `record_matches_process`, `process_identity`, and `terminate_registered_process` through control helpers; server cleanup uses registry process functions. | Process records under backend `processes/`; fields include PID, executable, creation time, parent PID/create time. | `tests.test_mcp_backend_control`, `tests.test_mcp_child_process_cleanup`. |
| Auth/token/readiness — `mcp_backend_secret.py`, `mcp_backend_http_headers.py`, `mcp_server.py`, `mcp_backend_control.py` | Control start pobiera/utworzy token; status/probe weryfikuje token; HTTP client headers przekazują bearer; mcp_server buduje verifier z env. | `token.json`, `token.lock`; token jest chroniony w rekordzie; environment backendu przekazuje sekret do procesu, nie argv. | `tests.test_mcp_backend_secret`, `tests.test_mcp_shared_backend_server_mode`, `tests.test_mcp_backend_control`, `tests.test_mcp_backend_cli`. |
| Persistent server & finalization — `C:\Temp\Contextor_Repo\contextor\mcp_server.py`, `mcp_main.py` | Control spawnuje `-m contextor.mcp_main`; `mcp_main.main` deleguje do `mcp_server.main`. | HTTP host/port, backend lease/record/lock, child process registry, `atexit` and `finally` cleanup. | `tests.test_mcp_shared_backend_server_mode`, `tests.test_mcp_backend_state`. |
| Autostart & CLI — `mcp_backend_autostart.py`, `mcp_backend_cli.py`, `__main__.py` | OS Run registration launches `pythonw -u -X utf8 -m contextor.mcp_backend_autostart launch`; launcher calls `start_backend`. `contextor.__main__.main` routes `backend start/status/stop` to CLI. | OS Run key/value for autostart; same backend state/control files as above. | `tests.test_mcp_backend_autostart`, `tests.test_mcp_backend_cli`. |
| Desktop startup & backend control — `C:\Temp\Contextor_Repo\contextor\ui\gui.py`, `contextor\__main__.py` | Normal GUI startup: `ContextorGUI.__init__ -> root.after -> _start_post_paint_tasks -> _start_live_watcher`; blocking LIVE connect calls `connect_or_start`. Contextor consumer evidence lists GUI as consumer of start/status/stop; source shows only explicit `ContextorGUI._restart_backend` calls these lifecycle functions. Normal startup callbacks found here perform cache cleanup and LIVE attach, not persistent backend start/status. | GUI keeps owner token/Desktop ID and LIVE clients/watchers in memory; backend control uses separate user state files. | `tests.test_gui_backend_restart`, `tests.test_gui_live_startup`, `tests.test_live_desktop_integration`. |
| LIVE lease/generation/claim — `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py`, `runtime_domain.py`, `runtime.py`, `ipc.py` | GUI’s `_start_live_watcher_blocking` calls `connect_or_start`; runtime spawns `run_service); run_service acquires lease, binds endpoint, creates Desktop claim and installs callbacks; IPC claim/release routes to lease manager. | `repo_cache_dir(root)/authority_lease.<domain_id>.json`, `authority_generation.<domain_id>.json`, `desktop_claim.<domain_id>.json`, `live_endpoint.json`; lock: `lock_root/authority.<domain_id>.lock`. | `tests.live_state.test_runtime_lease`, `tests.live_state.test_runtime_domain`, `tests.test_live_authority_bootstrap`, `tests.test_live_state_ipc`, `tests.test_live_desktop_integration`, `tests.test_gui_live_startup`. |

## Runtime paths and locks

### Persistent MCP backend

- `state_dir()` = `CONTEXTOR_STATE_DIR` or platform user config root. Windows default: `%APPDATA%\Contextor`.
- `backend_state_dir()` = `state_dir()/mcp_backend`.
- Record: `backend.json`.
- Lifetime OS lock: `backend.lock` (owned by backend process through `PersistentBackendLease`).
- Management serialization lock: `control.lock` (acquired around start/stop control operations; not held for backend lifetime).
- Child process registry: `processes/`.
- Persistent bearer record and token-creation lock: `token.json`, `token.lock`.
- Backend state/secret files are shared among cooperating Contextor processes under the user-level state directory. The backend record is written atomically; release removes it only if the exact current record equals the lease’s expected record.

### LIVE authority

- `RuntimeDomain.create` defaults production `cache_root` to `repo_cache_dir(repo_root)`, `lock_root` to `cache_root/runtime`, and IPC endpoint root to `cache_root`.
- Registered repository cache is `app_cache_dir()/repositories/<repo_id>`; app cache is `CONTEXTOR_CACHE_DIR` or Windows `%LOCALAPPDATA%\Contextor\cache`. Before identity registration, legacy repo-key cache path is used.
- `endpoint_file(root)` is `repo_cache_dir(root)/live_endpoint.json`.
- Lease, generation, claim and lock paths are domain-scoped as listed above. Domain lock uses OS file lock plus in-process thread guard. This is LIVE state and is not shared backend state.

## Full implementations fetched through Contextor

The following are complete AST-bounded symbol bodies returned at canonical revision 1606 with verified workspace sync, except where the evidence note above explicitly marks lineage-only response as unverified. Paths and symbol line spans accompany each body.

### Backend record, lease, record I/O and lifetime lock

### contextor.mcp_backend_state::PersistentBackendRecord

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::PersistentBackendRecord
SOURCE_LINES=lines 97-268

```python
@dataclass(
    frozen=True,
    slots=True,
)
class PersistentBackendRecord:
    schema_version: int
    instance_id: str
    server_role: str
    transport: str
    host: str
    port: int
    pid: int
    executable: str
    creation_time: int | None
    process_registry: str
    started_at: float

    def __post_init__(self) -> None:
        if (
            self.schema_version
            != BACKEND_RECORD_SCHEMA_VERSION
        ):
            raise BackendRecordError(
                "unsupported backend record schema_version"
            )

        object.__setattr__(
            self,
            "instance_id",
            _text(
                self.instance_id,
                "instance_id",
            ),
        )

        if self.server_role != BACKEND_SERVER_ROLE:
            raise BackendRecordError(
                "backend record server_role is invalid"
            )

        if self.transport != BACKEND_TRANSPORT:
            raise BackendRecordError(
                "backend record transport is invalid"
            )

        object.__setattr__(
            self,
            "host",
            _text(
                self.host,
                "host",
            ),
        )

        port = _positive_int(
            self.port,
            "port",
        )

        if port > 65535:
            raise BackendRecordError(
                "port must be at most 65535"
            )

        object.__setattr__(
            self,
            "pid",
            _positive_int(
                self.pid,
                "pid",
            ),
        )

        object.__setattr__(
            self,
            "executable",
            _text(
                self.executable,
                "executable",
            ),
        )

        if self.creation_time is not None:
            object.__setattr__(
                self,
                "creation_time",
                _positive_int(
                    self.creation_time,
                    "creation_time",
                ),
            )

        object.__setattr__(
            self,
            "process_registry",
            _canonical_path(
                self.process_registry,
                "process_registry",
            ),
        )

        if (
            isinstance(
                self.started_at,
                bool,
            )
            or not isinstance(
                self.started_at,
                (int, float),
            )
        ):
            raise BackendRecordError(
                "started_at must be a timestamp"
            )

        started_at = float(
            self.started_at
        )

        if (
            not math.isfinite(
                started_at
            )
            or started_at < 0
        ):
            raise BackendRecordError(
                "started_at must be a finite non-negative timestamp"
            )

        object.__setattr__(
            self,
            "started_at",
            started_at,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "server_role": self.server_role,
            "transport": self.transport,
            "host": self.host,
            "port": self.port,
            "pid": self.pid,
            "executable": self.executable,
            "creation_time": self.creation_time,
            "process_registry": self.process_registry,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "PersistentBackendRecord":
        if (
            not isinstance(
                payload,
                Mapping,
            )
            or set(payload)
            != _RECORD_FIELDS
        ):
            raise BackendRecordError(
                "backend record fields do not match schema"
            )

        return cls(
            **dict(payload)
        )

```

### contextor.mcp_backend_state::PersistentBackendLease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::PersistentBackendLease
SOURCE_LINES=lines 572-687

```python
class PersistentBackendLease:
    def __init__(
        self,
        record: PersistentBackendRecord,
        lifetime_lock: _BackendLifetimeLock,
    ) -> None:
        self.record = record
        self._lifetime_lock = (
            lifetime_lock
        )
        self._released = False

    @classmethod
    def acquire(
        cls,
        *,
        host: str,
        port: int,
        transport: str,
        process_registry: str | Path,
        timeout: float = 0.0,
    ) -> "PersistentBackendLease":
        lifetime_lock = (
            _BackendLifetimeLock(
                backend_lock_path(),
                timeout=timeout,
            )
        )

        lifetime_lock.__enter__()

        try:
            (
                image,
                creation_time,
                alive,
            ) = process_identity(
                os.getpid()
            )

            if not alive:
                raise BackendStateError(
                    "current persistent backend process identity is unavailable"
                )

            record = PersistentBackendRecord(
                schema_version=(
                    BACKEND_RECORD_SCHEMA_VERSION
                ),
                instance_id=(
                    uuid.uuid4().hex
                ),
                server_role=(
                    BACKEND_SERVER_ROLE
                ),
                transport=transport,
                host=host,
                port=port,
                pid=os.getpid(),
                executable=(
                    image
                    or sys.executable
                ),
                creation_time=(
                    int(creation_time)
                    if creation_time
                    is not None
                    else None
                ),
                process_registry=str(
                    Path(
                        process_registry
                    )
                    .expanduser()
                    .resolve(
                        strict=False
                    )
                ),
                started_at=time.time(),
            )

            _write_record(
                record
            )

            return cls(
                record,
                lifetime_lock,
            )

        except BaseException:
            lifetime_lock.__exit__(
                None,
                None,
                None,
            )
            raise

    def release(
        self,
    ) -> None:
        if self._released:
            return

        self._released = True

        try:
            remove_backend_record_if_exact(
                self.record
            )
        finally:
            self._lifetime_lock.__exit__(
                None,
                None,
                None,
            )

```

### contextor.mcp_backend_state::_BackendLifetimeLock

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::_BackendLifetimeLock
SOURCE_LINES=lines 422-569

```python
class _BackendLifetimeLock(
    AbstractContextManager[
        "_BackendLifetimeLock"
    ]
):
    def __init__(
        self,
        path: Path,
        *,
        timeout: float,
    ) -> None:
        self.path = path
        self.timeout = max(
            0.0,
            float(timeout),
        )
        self._thread_lock = (
            _thread_lock_for(
                path
            )
        )
        self._file: Any = None

    def __enter__(
        self,
    ) -> "_BackendLifetimeLock":
        if not self._thread_lock.acquire(
            timeout=self.timeout
        ):
            raise BackendAlreadyRunning(
                "persistent backend lifetime lock is already held"
            )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._file = (
                self.path.open(
                    "a+b"
                )
            )

            if (
                self.path.stat().st_size
                == 0
            ):
                self._file.write(
                    b"0"
                )
                self._file.flush()

            deadline = (
                time.monotonic()
                + self.timeout
            )

            while True:
                try:
                    self._file.seek(0)

                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(
                            self._file.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )

                    else:
                        import fcntl

                        fcntl.flock(
                            self._file.fileno(),
                            fcntl.LOCK_EX
                            | fcntl.LOCK_NB,
                        )

                    return self

                except (
                    OSError,
                    BlockingIOError,
                ) as exc:
                    if (
                        time.monotonic()
                        >= deadline
                    ):
                        raise BackendAlreadyRunning(
                            "persistent backend lifetime lock is already held"
                        ) from exc

                    time.sleep(
                        0.01
                    )

        except Exception:
            self._close()
            self._thread_lock.release()
            raise

    def _close(
        self,
    ) -> None:
        if self._file is None:
            return

        try:
            self._file.seek(0)

            if os.name == "nt":
                import msvcrt

                msvcrt.locking(
                    self._file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )

            else:
                import fcntl

                fcntl.flock(
                    self._file.fileno(),
                    fcntl.LOCK_UN,
                )

        except OSError:
            pass

        try:
            self._file.close()
        finally:
            self._file = None

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:
        try:
            self._close()
        finally:
            self._thread_lock.release()

```

### contextor.mcp_backend_state::backend_state_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::backend_state_dir
SOURCE_LINES=lines 271-275

```python
def backend_state_dir() -> Path:
    return (
        state_dir()
        / "mcp_backend"
    )

```

### contextor.mcp_backend_state::backend_record_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::backend_record_path
SOURCE_LINES=lines 278-282

```python
def backend_record_path() -> Path:
    return (
        backend_state_dir()
        / "backend.json"
    )

```

### contextor.mcp_backend_state::backend_lock_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::backend_lock_path
SOURCE_LINES=lines 285-289

```python
def backend_lock_path() -> Path:
    return (
        backend_state_dir()
        / "backend.lock"
    )

```

### contextor.mcp_backend_state::read_backend_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::read_backend_record
SOURCE_LINES=lines 337-371

```python
def read_backend_record(
) -> PersistentBackendRecord | None:
    try:
        payload = json.loads(
            backend_record_path().read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError:
        return None

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise BackendRecordError(
            "persistent backend record is malformed"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise BackendRecordError(
            "persistent backend record must be an object"
        )

    return (
        PersistentBackendRecord
        .from_dict(
            payload
        )
    )

```

### contextor.mcp_backend_state::_write_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::_write_record
SOURCE_LINES=lines 292-334

```python
def _write_record(
    record: PersistentBackendRecord,
) -> None:
    target = backend_record_path()

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = target.with_name(
        f".{target.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        with temporary.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            json.dump(
                record.to_dict(),
                stream,
                sort_keys=True,
                separators=(",", ":"),
            )

            stream.flush()

            os.fsync(
                stream.fileno()
            )

        os.replace(
            temporary,
            target,
        )

    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

```

### contextor.mcp_backend_state::remove_backend_record_if_exact

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::remove_backend_record_if_exact
SOURCE_LINES=lines 374-392

```python
def remove_backend_record_if_exact(
    expected: PersistentBackendRecord,
) -> bool:
    try:
        current = (
            read_backend_record()
        )
    except BackendRecordError:
        return False

    if current != expected:
        return False

    try:
        backend_record_path().unlink()
    except FileNotFoundError:
        return False

    return True

```

### contextor.mcp_backend_state::_thread_lock_for

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py
SYMBOL=contextor.mcp_backend_state::_thread_lock_for
SOURCE_LINES=lines 405-419

```python
def _thread_lock_for(
    path: Path,
) -> threading.Lock:
    key = os.path.normcase(
        str(path)
    )

    with _THREAD_LOCKS_GUARD:
        return (
            _THREAD_LOCKS
            .setdefault(
                key,
                threading.Lock(),
            )
        )

```


### Backend control, spawn, readiness, identity and process cleanup

### contextor.mcp_backend_control::_BackendControlLock

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_BackendControlLock
SOURCE_LINES=lines 274-419

```python
class _BackendControlLock(
    AbstractContextManager[
        "_BackendControlLock"
    ]
):
    def __init__(
        self,
        path: Path,
        *,
        timeout: float,
    ) -> None:
        self.path = path
        self.timeout = max(
            0.0,
            float(timeout),
        )
        self._thread_lock = (
            _thread_lock_for(
                path
            )
        )
        self._file: Any = None

    def __enter__(
        self,
    ) -> "_BackendControlLock":
        if not self._thread_lock.acquire(
            timeout=self.timeout
        ):
            raise BackendControlError(
                "persistent backend control lock is busy"
            )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._file = self.path.open(
                "a+b"
            )

            if (
                self.path.stat().st_size
                == 0
            ):
                self._file.write(
                    b"0"
                )
                self._file.flush()

            deadline = (
                time.monotonic()
                + self.timeout
            )

            while True:
                try:
                    self._file.seek(0)

                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(
                            self._file.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )

                    else:
                        import fcntl

                        fcntl.flock(
                            self._file.fileno(),
                            fcntl.LOCK_EX
                            | fcntl.LOCK_NB,
                        )

                    return self

                except (
                    OSError,
                    BlockingIOError,
                ) as exc:
                    if (
                        time.monotonic()
                        >= deadline
                    ):
                        raise BackendControlError(
                            "persistent backend control lock is busy"
                        ) from exc

                    time.sleep(
                        0.01
                    )

        except Exception:
            self._close()
            self._thread_lock.release()
            raise

    def _close(
        self,
    ) -> None:
        if self._file is None:
            return

        try:
            self._file.seek(0)

            if os.name == "nt":
                import msvcrt

                msvcrt.locking(
                    self._file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )

            else:
                import fcntl

                fcntl.flock(
                    self._file.fileno(),
                    fcntl.LOCK_UN,
                )

        except OSError:
            pass

        try:
            self._file.close()
        finally:
            self._file = None

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:
        try:
            self._close()
        finally:
            self._thread_lock.release()

```

### contextor.mcp_backend_control::backend_control_lock_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::backend_control_lock_path
SOURCE_LINES=lines 108-112

```python
def backend_control_lock_path() -> Path:
    return (
        backend_state_dir()
        / "control.lock"
    )

```

### contextor.mcp_backend_control::start_backend

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::start_backend
SOURCE_LINES=lines 676-771

```python
def start_backend(
    *,
    timeout: float = 20.0,
    probe_timeout: float = 2.0,
) -> BackendStatus:
    with _BackendControlLock(
        backend_control_lock_path(),
        timeout=timeout,
    ):
        token = (
            get_or_create_backend_token()
        )

        current = (
            get_backend_status(
                probe_timeout=probe_timeout,
            )
        )

        if current.ready:
            return current

        if (
            current.state == "unready"
            and current.record is not None
        ):
            deadline = (
                time.monotonic()
                + max(
                    0.0,
                    float(timeout),
                )
            )

            while (
                time.monotonic()
                < deadline
            ):
                current = (
                    get_backend_status(
                        probe_timeout=probe_timeout,
                    )
                )

                if current.ready:
                    return current

                if (
                    current.state
                    != "unready"
                ):
                    break

                time.sleep(
                    0.05
                )

            if (
                current.state
                == "unready"
            ):
                raise BackendControlError(
                    "an existing persistent backend owner "
                    "is alive but did not become ready"
                )

        _cleanup_stale_backend_record(
            current
        )

        process = (
            _spawn_backend_process(
                token
            )
        )

        identity_record = (
            _spawn_identity_record(
                process
            )
        )

        try:
            return (
                _wait_for_ready_backend(
                    process,
                    timeout=timeout,
                    probe_timeout=probe_timeout,
                )
            )

        except BaseException:
            _cleanup_spawned_process(
                identity_record
            )
            raise

```

### contextor.mcp_backend_control::_spawn_backend_process

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_spawn_backend_process
SOURCE_LINES=lines 490-562

```python
def _spawn_backend_process(
    token: str,
) -> subprocess.Popen:
    interpreter = (
        _backend_python()
    )

    cmd = [
        str(interpreter),
        "-u",
        "-m",
        "contextor.mcp_main",
    ]

    kwargs = {
        "cwd": str(
            package_root()
        ),
        "env": (
            _backend_environment(
                token
            )
        ),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if sys.platform != "win32":
        return subprocess.Popen(
            cmd,
            creationflags=0,
            **kwargs,
        )

    base_flags = getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0,
    )

    primary_flags = (
        base_flags
        | _CREATE_BREAKAWAY_FROM_JOB
    )

    try:
        return subprocess.Popen(
            cmd,
            creationflags=primary_flags,
            **kwargs,
        )

    except OSError as exc:
        if (
            getattr(
                exc,
                "winerror",
                None,
            )
            != 5
        ):
            raise

        try:
            return subprocess.Popen(
                cmd,
                creationflags=base_flags,
                **kwargs,
            )

        except Exception as fallback_exc:
            raise fallback_exc from exc

```

### contextor.mcp_backend_control::_wait_for_ready_backend

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_wait_for_ready_backend
SOURCE_LINES=lines 614-673

```python
def _wait_for_ready_backend(
    process: subprocess.Popen,
    *,
    timeout: float,
    probe_timeout: float,
) -> BackendStatus:
    deadline = (
        time.monotonic()
        + max(
            0.0,
            float(timeout),
        )
    )

    last_status = BackendStatus(
        state="stopped",
        ready=False,
        detail="backend startup has not published state yet",
        record=None,
    )

    while (
        time.monotonic()
        < deadline
    ):
        last_status = (
            get_backend_status(
                probe_timeout=probe_timeout,
            )
        )

        if last_status.ready:
            return last_status

        if (
            process.poll()
            is not None
        ):
            final_status = (
                get_backend_status(
                    probe_timeout=probe_timeout,
                )
            )

            if final_status.ready:
                return final_status

            raise BackendControlError(
                "persistent backend process exited "
                "before authenticated readiness"
            )

        time.sleep(
            0.05
        )

    raise BackendControlError(
        "persistent backend did not become "
        "authenticated and ready before timeout"
    )

```

### contextor.mcp_backend_control::get_backend_status

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::get_backend_status
SOURCE_LINES=lines 182-244

```python
def get_backend_status(
    *,
    probe_timeout: float = 2.0,
) -> BackendStatus:
    record = read_backend_record()

    if record is None:
        return BackendStatus(
            state="stopped",
            ready=False,
            detail="no persistent backend record",
            record=None,
        )

    if not _record_process_matches(
        record
    ):
        return BackendStatus(
            state="stale",
            ready=False,
            detail=(
                "persistent backend record does not "
                "match a live process identity"
            ),
            record=record,
        )

    token = read_backend_token()

    if token is None:
        return BackendStatus(
            state="unready",
            ready=False,
            detail=(
                "backend owner is live but bearer "
                "token is unavailable"
            ),
            record=record,
        )

    if not _probe_backend(
        record,
        token,
        timeout=probe_timeout,
    ):
        return BackendStatus(
            state="unready",
            ready=False,
            detail=(
                "backend owner is live but authenticated "
                "MCP readiness was not confirmed"
            ),
            record=record,
        )

    return BackendStatus(
        state="running",
        ready=True,
        detail=(
            "authenticated Contextor MCP backend is ready"
        ),
        record=record,
    )

```

### contextor.mcp_backend_control::stop_backend

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::stop_backend
SOURCE_LINES=lines 915-998

```python
def stop_backend(
    *,
    timeout: float = 5.0,
) -> BackendStatus:
    with _BackendControlLock(
        backend_control_lock_path(),
        timeout=timeout,
    ):
        record = (
            read_backend_record()
        )

        if record is None:
            return BackendStatus(
                state="stopped",
                ready=False,
                detail="no persistent backend record",
                record=None,
            )

        if not (
            _backend_owner_identity_matches(
                record
            )
        ):
            remove_backend_record_if_exact(
                record
            )

            return BackendStatus(
                state="stopped",
                ready=False,
                detail=(
                    "stale persistent backend record "
                    "was removed without terminating "
                    "any process"
                ),
                record=None,
            )

        if (
            sys.platform == "win32"
            and record.creation_time is None
        ):
            raise BackendControlError(
                "refusing to terminate backend without "
                "Windows process creation identity"
            )

        terminated = (
            terminate_registered_process(
                record.to_dict()
            )
        )

        if not terminated:
            raise BackendControlError(
                "identity-checked backend termination "
                "was not accepted"
            )

        if not _wait_for_owner_exit(
            record,
            timeout=timeout,
        ):
            raise BackendControlError(
                "persistent backend process remained "
                "alive after identity-checked termination"
            )

        _cleanup_owned_registry_children(
            record
        )

        remove_backend_record_if_exact(
            record
        )

        return BackendStatus(
            state="stopped",
            ready=False,
            detail="persistent backend stopped",
            record=None,
        )

```

### contextor.mcp_backend_control::_probe_backend

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_probe_backend
SOURCE_LINES=lines 167-179

```python
def _probe_backend(
    record: PersistentBackendRecord,
    token: str,
    *,
    timeout: float,
) -> bool:
    return asyncio.run(
        _probe_backend_async(
            record,
            token,
            timeout=timeout,
        )
    )

```

### contextor.mcp_backend_control::_probe_backend_async

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_probe_backend_async
SOURCE_LINES=lines 133-164

```python
async def _probe_backend_async(
    record: PersistentBackendRecord,
    token: str,
    *,
    timeout: float,
) -> bool:
    try:
        async with Client(
            _backend_endpoint(record),
            auth=token,
            timeout=timeout,
            init_timeout=timeout,
        ) as client:
            initialized = (
                client.initialize_result
            )

            if initialized is None:
                return False

            if (
                initialized.serverInfo.name
                != BACKEND_SERVER_NAME
            ):
                return False

            return bool(
                await client.ping()
            )

    except Exception:
        return False

```

### contextor.mcp_backend_control::_backend_owner_identity_matches

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_backend_owner_identity_matches
SOURCE_LINES=lines 774-810

```python
def _backend_owner_identity_matches(
    record: PersistentBackendRecord,
) -> bool:
    (
        image,
        creation_time,
        alive,
    ) = process_identity(
        record.pid
    )

    if not alive:
        return False

    if (
        record.creation_time is not None
        and creation_time is not None
        and int(
            record.creation_time
        )
        != int(
            creation_time
        )
    ):
        return False

    if (
        image
        and record.executable
        and Path(image).name.casefold()
        != Path(
            record.executable
        ).name.casefold()
    ):
        return False

    return True

```

### contextor.mcp_backend_control::_wait_for_owner_exit

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_wait_for_owner_exit
SOURCE_LINES=lines 880-912

```python
def _wait_for_owner_exit(
    record: PersistentBackendRecord,
    *,
    timeout: float,
) -> bool:
    deadline = (
        time.monotonic()
        + max(
            0.0,
            float(timeout),
        )
    )

    while (
        time.monotonic()
        < deadline
    ):
        if not (
            _backend_owner_identity_matches(
                record
            )
        ):
            return True

        time.sleep(
            0.05
        )

    return not (
        _backend_owner_identity_matches(
            record
        )
    )

```

### contextor.mcp_backend_control::_spawn_identity_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_spawn_identity_record
SOURCE_LINES=lines 565-588

```python
def _spawn_identity_record(
    process: subprocess.Popen,
) -> dict[str, Any] | None:
    (
        image,
        creation_time,
        alive,
    ) = process_identity(
        process.pid
    )

    if not alive:
        return None

    return {
        "pid": process.pid,
        "executable": (
            image
            or str(
                _backend_python()
            )
        ),
        "creation_time": creation_time,
    }

```

### contextor.mcp_backend_control::_cleanup_owned_registry_children

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_cleanup_owned_registry_children
SOURCE_LINES=lines 813-877

```python
def _cleanup_owned_registry_children(
    record: PersistentBackendRecord,
) -> None:
    directory = Path(
        record.process_registry
    )

    for (
        record_path,
        child,
    ) in read_records(
        directory
    ):
        try:
            parent_pid = int(
                child.get(
                    "parent_pid"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if parent_pid != record.pid:
            continue

        if (
            record.creation_time
            is not None
        ):
            expected_parent_creation = (
                child.get(
                    "parent_creation_time"
                )
            )

            if (
                expected_parent_creation
                is None
            ):
                continue

            try:
                if int(
                    expected_parent_creation
                ) != int(
                    record.creation_time
                ):
                    continue

            except (
                TypeError,
                ValueError,
            ):
                continue

        terminate_registered_process(
            child
        )

        remove_record(
            record_path
        )

```

### backend_process_registry_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=backend_process_registry_dir
SOURCE_LINES=lines 101-105

```python
def backend_process_registry_dir() -> Path:
    return (
        backend_state_dir()
        / "processes"
    )

```


### Shared process registry identity and termination helpers

### process_identity

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py
SYMBOL=process_identity
SOURCE_LINES=79-91

```python
def process_identity(pid: int) -> tuple[str | None, int | None, bool]:
    if sys_platform_is_windows():
        return _windows_process_identity(pid)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return None, None, False
    image = None
    try:
        image = str(Path(f"/proc/{pid}/exe").resolve(strict=True))
    except OSError:
        pass
    return image, None, True

```

### record_matches_process

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py
SYMBOL=record_matches_process
SOURCE_LINES=150-166

```python
def record_matches_process(record: dict[str, Any]) -> bool:
    try:
        pid = int(record["pid"])
    except (KeyError, TypeError, ValueError):
        return False
    image, creation_time, alive = process_identity(pid)
    if not alive:
        return False
    expected_image = str(record.get("executable") or "")
    if image and expected_image:
        if Path(image).name.casefold() != Path(expected_image).name.casefold():
            return False
    expected_creation = record.get("creation_time")
    if expected_creation is not None and creation_time is not None:
        if int(expected_creation) != creation_time:
            return False
    return True

```

### terminate_registered_process

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py
SYMBOL=terminate_registered_process
SOURCE_LINES=169-245

```python
def terminate_registered_process(
    record: dict[str, Any],
) -> bool:
    if not record_matches_process(record):
        return False
    pid = int(record["pid"])
    if sys_platform_is_windows():
        try:
            subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    str(pid),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5.0,
            )
        except Exception:
            pass
        _, _, alive = process_identity(pid)
        if not alive:
            return True
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.TerminateProcess.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
        ]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [
            wintypes.HANDLE,
        ]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(
            0x0001,
            False,
            pid,
        )
        if not handle:
            return False
        try:
            terminated = bool(
                kernel32.TerminateProcess(
                    handle,
                    1,
                )
            )
            if terminated:
                kernel32.WaitForSingleObject(
                    handle,
                    2000,
                )
            return terminated
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False

```

### register_process

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py
SYMBOL=register_process
SOURCE_LINES=98-122

```python
def register_process(
    directory: Path,
    *,
    pid: int,
    parent_pid: int,
    kind: str,
    executable: str,
) -> Path:
    image, creation_time, _ = process_identity(pid)
    _, parent_creation_time, _ = process_identity(parent_pid)
    record = {
        "pid": pid,
        "parent_pid": parent_pid,
        "kind": kind,
        "executable": image or executable,
        "creation_time": creation_time,
        "parent_creation_time": parent_creation_time,
        "registered_at": time.time(),
    }
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{kind}-{pid}.json"
    temporary = directory / f".{kind}-{pid}-{os.getpid()}.tmp"
    temporary.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    temporary.replace(target)
    return target

```


### HTTP authentication, bearer storage, request header and autostart helpers

### contextor.mcp_server::_build_mcp_auth_from_environment

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_build_mcp_auth_from_environment
SOURCE_LINES=lines 528-549

```python
def _build_mcp_auth_from_environment(
    transport: str,
) -> TokenVerifier | None:
    if transport not in _HTTP_TRANSPORTS:
        return None

    token = os.environ.get(
        "CONTEXTOR_MCP_TOKEN"
    )

    if (
        token is None
        or len(token) < _MIN_MCP_TOKEN_LENGTH
        or token != token.strip()
    ):
        raise RuntimeError(
            "Streamable HTTP Contextor MCP requires "
            "CONTEXTOR_MCP_TOKEN containing at least "
            "32 non-whitespace-surrounded characters."
        )

    return _ContextorBearerTokenVerifier(token)

```

### contextor.mcp_server::_process_directory_from_environment

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_process_directory_from_environment
SOURCE_LINES=lines 951-963

```python
def _process_directory_from_environment() -> Path:
    configured = os.environ.get(
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    )

    if configured:
        return Path(
            configured
        ).expanduser().resolve()

    return registry_dir(
        Path.cwd().resolve()
    )

```

### contextor.mcp_server::_server_role_from_environment

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_server_role_from_environment
SOURCE_LINES=lines 936-948

```python
def _server_role_from_environment() -> str:
    role = os.environ.get(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "host-owned",
    ).strip().lower()

    if role not in _SERVER_ROLES:
        raise RuntimeError(
            "Unsupported CONTEXTOR_MCP_SERVER_ROLE: "
            f"{role!r}"
        )

    return role

```

### contextor.mcp_server::_mcp_transport_from_environment

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_mcp_transport_from_environment
SOURCE_LINES=lines 474-490

```python
def _mcp_transport_from_environment() -> str:
    transport = os.environ.get(
        "CONTEXTOR_MCP_TRANSPORT",
        "stdio",
    ).strip().lower()

    if transport not in {
        "stdio",
        "http",
        "streamable-http",
    }:
        raise RuntimeError(
            "Unsupported CONTEXTOR_MCP_TRANSPORT: "
            f"{transport!r}"
        )

    return transport

```

### contextor.mcp_server::_register_server_root

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_register_server_root
SOURCE_LINES=lines 966-979

```python
def _register_server_root(
    process_directory: Path,
    role: str,
) -> Path | None:
    if role == "persistent-backend":
        return None

    return register_process(
        process_directory,
        pid=os.getpid(),
        parent_pid=os.getppid(),
        kind="mcp-server",
        executable=sys.executable,
    )

```

### contextor.mcp_server::_cleanup_owned_processes

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_cleanup_owned_processes
SOURCE_LINES=lines 608-617

```python
def _cleanup_owned_processes(directory: Path, owner_pid: int) -> None:
    """Stop registered child processes still owned by this server."""
    for record_path, record in read_records(directory):
        try:
            is_child = int(record.get("parent_pid")) == owner_pid
        except (TypeError, ValueError):
            is_child = False
        if is_child:
            terminate_registered_process(record)
            remove_record(record_path)

```

### contextor.mcp_server::_cleanup_orphaned_processes

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_cleanup_orphaned_processes
SOURCE_LINES=lines 582-605

```python
def _cleanup_orphaned_processes(directory: Path) -> None:
    """Stop only registered MCP/Git processes whose recorded parent is gone."""
    # Two passes handle a stale server and one of its Git children regardless
    # of filesystem iteration order: pass one stops the server, pass two the child.
    for _ in range(2):
        stopped_process = False
        for record_path, record in read_records(directory):
            if not record_matches_process(record):
                remove_record(record_path)
                continue
            try:
                parent_pid = int(record["parent_pid"])
            except (KeyError, TypeError, ValueError):
                remove_record(record_path)
                continue
            _, parent_creation_time, parent_alive = process_identity(parent_pid)
            expected_parent_creation = record.get("parent_creation_time")
            if expected_parent_creation is not None and parent_creation_time is not None:
                parent_alive = int(expected_parent_creation) == parent_creation_time
            if not parent_alive:
                stopped_process = terminate_registered_process(record) or stopped_process
                remove_record(record_path)
        if not stopped_process:
            break

```

### contextor.mcp_backend_control::_backend_environment

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_backend_environment
SOURCE_LINES=lines 450-487

```python
def _backend_environment(
    token: str,
) -> dict[str, str]:
    env = dict(
        os.environ
    )

    env[
        "CONTEXTOR_MCP_TRANSPORT"
    ] = _BACKEND_TRANSPORT

    env[
        "CONTEXTOR_MCP_SERVER_ROLE"
    ] = "persistent-backend"

    env[
        "CONTEXTOR_MCP_HOST"
    ] = BACKEND_HOST

    env[
        "CONTEXTOR_MCP_PORT"
    ] = str(
        BACKEND_PORT
    )

    env[
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    ] = str(
        backend_process_registry_dir()
        .expanduser()
        .resolve()
    )

    env[
        "CONTEXTOR_MCP_TOKEN"
    ] = token

    return env

```

### contextor.mcp_backend_control::_backend_endpoint

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_backend_endpoint
SOURCE_LINES=lines 115-122

```python
def _backend_endpoint(
    record: PersistentBackendRecord,
) -> str:
    return (
        f"http://{record.host}:"
        f"{record.port}"
        f"{BACKEND_MCP_PATH}"
    )

```

### contextor.mcp_backend_control::BackendStatus

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::BackendStatus
SOURCE_LINES=lines 57-98

```python
@dataclass(
    frozen=True,
    slots=True,
)
class BackendStatus:
    state: BackendState
    ready: bool
    detail: str
    record: PersistentBackendRecord | None

    @property
    def endpoint(
        self,
    ) -> str | None:
        if self.record is None:
            return None

        return (
            f"http://{self.record.host}:"
            f"{self.record.port}"
            f"{BACKEND_MCP_PATH}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "state": self.state,
            "ready": self.ready,
            "detail": self.detail,
            "endpoint": self.endpoint,
            "pid": (
                None
                if self.record is None
                else self.record.pid
            ),
            "instance_id": (
                None
                if self.record is None
                else self.record.instance_id
            ),
        }

```

### contextor.mcp_backend_control::BackendStatus.to_dict

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::BackendStatus.to_dict
SOURCE_LINES=lines 80-98

```python
    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "state": self.state,
            "ready": self.ready,
            "detail": self.detail,
            "endpoint": self.endpoint,
            "pid": (
                None
                if self.record is None
                else self.record.pid
            ),
            "instance_id": (
                None
                if self.record is None
                else self.record.instance_id
            ),
        }

```

### contextor.mcp_backend_secret::BackendSecretRecord

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::BackendSecretRecord
SOURCE_LINES=lines 47-145

```python
@dataclass(
    frozen=True,
    slots=True,
)
class BackendSecretRecord:
    schema_version: int
    protection: str
    protected_data: str
    created_at: float

    def __post_init__(self) -> None:
        if self.schema_version != TOKEN_RECORD_SCHEMA_VERSION:
            raise BackendSecretRecordError(
                "unsupported backend token schema_version"
            )

        if self.protection not in {
            _WINDOWS_PROTECTION,
            _POSIX_PROTECTION,
        }:
            raise BackendSecretRecordError(
                "unsupported backend token protection"
            )

        if (
            not isinstance(self.protected_data, str)
            or not self.protected_data
            or self.protected_data != self.protected_data.strip()
        ):
            raise BackendSecretRecordError(
                "protected_data must be non-empty base64 text"
            )

        try:
            base64.b64decode(
                self.protected_data.encode("ascii"),
                validate=True,
            )
        except (
            UnicodeEncodeError,
            ValueError,
        ) as exc:
            raise BackendSecretRecordError(
                "protected_data is not valid base64"
            ) from exc

        if (
            isinstance(self.created_at, bool)
            or not isinstance(
                self.created_at,
                (int, float),
            )
        ):
            raise BackendSecretRecordError(
                "created_at must be a timestamp"
            )

        created_at = float(self.created_at)

        if (
            not math.isfinite(created_at)
            or created_at < 0
        ):
            raise BackendSecretRecordError(
                "created_at must be a finite non-negative timestamp"
            )

        object.__setattr__(
            self,
            "created_at",
            created_at,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "protection": self.protection,
            "protected_data": self.protected_data,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "BackendSecretRecord":
        if (
            not isinstance(payload, Mapping)
            or set(payload) != _TOKEN_FIELDS
        ):
            raise BackendSecretRecordError(
                "backend token fields do not match schema"
            )

        return cls(
            **dict(payload)
        )

```

### contextor.mcp_backend_secret::get_or_create_backend_token

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::get_or_create_backend_token
SOURCE_LINES=lines 836-858

```python
def get_or_create_backend_token(
) -> str:
    with _BackendSecretLock(
        backend_token_lock_path()
    ):
        existing = (
            read_backend_token()
        )

        if existing is not None:
            return existing

        token = (
            _new_backend_token()
        )

        _write_secret_record(
            _encode_secret_record(
                token
            )
        )

        return token

```

### contextor.mcp_backend_secret::read_backend_token

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::read_backend_token
SOURCE_LINES=lines 822-833

```python
def read_backend_token(
) -> str | None:
    record = (
        _read_secret_record()
    )

    if record is None:
        return None

    return _decode_secret_record(
        record
    )

```

### contextor.mcp_backend_secret::backend_token_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::backend_token_path
SOURCE_LINES=lines 148-152

```python
def backend_token_path() -> Path:
    return (
        backend_state_dir()
        / "token.json"
    )

```

### contextor.mcp_backend_secret::backend_token_lock_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::backend_token_lock_path
SOURCE_LINES=lines 155-159

```python
def backend_token_lock_path() -> Path:
    return (
        backend_state_dir()
        / "token.lock"
    )

```

### contextor.mcp_backend_secret::_read_secret_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::_read_secret_record
SOURCE_LINES=lines 579-619

```python
def _read_secret_record(
) -> BackendSecretRecord | None:
    path = backend_token_path()

    try:
        _assert_posix_secret_permissions(
            path
        )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError:
        return None

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise BackendSecretRecordError(
            "persistent backend token record is malformed"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise BackendSecretRecordError(
            "persistent backend token record must be an object"
        )

    return (
        BackendSecretRecord
        .from_dict(
            payload
        )
    )

```

### contextor.mcp_backend_secret::_write_secret_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py
SYMBOL=contextor.mcp_backend_secret::_write_secret_record
SOURCE_LINES=lines 485-576

```python
def _write_secret_record(
    record: BackendSecretRecord,
) -> None:
    directory = (
        _ensure_secret_directory()
    )

    target = backend_token_path()
    temporary = target.with_name(
        f".{target.name}.{uuid.uuid4().hex}.tmp"
    )

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = None

    try:
        fd = os.open(
            temporary,
            flags,
            0o600,
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            fd = None

            json.dump(
                record.to_dict(),
                stream,
                sort_keys=True,
                separators=(",", ":"),
            )

            stream.flush()
            os.fsync(
                stream.fileno()
            )

        os.replace(
            temporary,
            target,
        )

        if os.name != "nt":
            os.chmod(
                target,
                0o600,
            )

            directory_fd = None

            try:
                directory_fd = os.open(
                    directory,
                    os.O_RDONLY,
                )

                os.fsync(
                    directory_fd
                )

            except OSError:
                pass

            finally:
                if (
                    directory_fd
                    is not None
                ):
                    os.close(
                        directory_fd
                    )

    finally:
        if fd is not None:
            os.close(
                fd
            )

        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

```

### contextor.mcp_backend_http_headers::build_backend_http_headers

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_http_headers.py
SYMBOL=contextor.mcp_backend_http_headers::build_backend_http_headers
SOURCE_LINES=lines 27-41

```python
def build_backend_http_headers() -> dict[str, str]:
    """Return the persistent backend bearer Authorization header."""

    token = (
        get_or_create_backend_token()
    )

    if not token:
        raise BackendHttpHeadersError(
            "persistent Contextor MCP backend bearer token is unavailable"
        )

    return {
        "Authorization": f"Bearer {token}",
    }

```

### contextor.mcp_backend_autostart::install_backend_autostart

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py
SYMBOL=contextor.mcp_backend_autostart::install_backend_autostart
SOURCE_LINES=lines 201-223

```python
def install_backend_autostart(
) -> BackendAutostartStatus:
    command = (
        backend_autostart_command()
    )

    _write_run_value(
        command
    )

    status = (
        get_backend_autostart_status()
    )

    if (
        not status.installed
        or not status.command_matches
    ):
        raise BackendAutostartError(
            "Contextor backend autostart registration was not verified"
        )

    return status

```

### contextor.mcp_backend_autostart::backend_autostart_command

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py
SYMBOL=contextor.mcp_backend_autostart::backend_autostart_command
SOURCE_LINES=lines 80-91

```python
def backend_autostart_command() -> str:
    return subprocess.list2cmdline(
        [
            str(_pythonw_path()),
            "-u",
            "-X",
            "utf8",
            "-m",
            "contextor.mcp_backend_autostart",
            "launch",
        ]
    )

```

### contextor.mcp_backend_autostart::get_backend_autostart_status

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py
SYMBOL=contextor.mcp_backend_autostart::get_backend_autostart_status
SOURCE_LINES=lines 180-198

```python
def get_backend_autostart_status(
) -> BackendAutostartStatus:
    expected = (
        backend_autostart_command()
    )
    configured = (
        _read_run_value()
    )

    return BackendAutostartStatus(
        installed=(
            configured is not None
        ),
        command_matches=(
            configured == expected
        ),
        expected_command=expected,
        configured_command=configured,
    )

```



### Server, lifecycle dispatch, CLI and package entrypoints

### contextor.mcp_server::main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::main
SOURCE_LINES=lines 982-1126

```python
def main():
    """Entry point for the MCP server."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(
            encoding="utf-8"
        )
        sys.stderr.reconfigure(
            encoding="utf-8"
        )

    import asyncio

    transport = (
        _mcp_transport_from_environment()
    )

    if transport != _MCP_BOOTSTRAP_TRANSPORT:
        raise RuntimeError(
            "CONTEXTOR_MCP_TRANSPORT changed after "
            "FastMCP construction; transport and auth "
            "must be selected before importing "
            "contextor.mcp_server."
        )

    role = _server_role_from_environment()

    if (
        role == "persistent-backend"
        and transport not in _HTTP_TRANSPORTS
    ):
        raise RuntimeError(
            "persistent-backend role requires "
            "Streamable HTTP transport."
        )

    process_directory = (
        _process_directory_from_environment()
    )

    http_host = None
    http_port = None

    if transport in _HTTP_TRANSPORTS:
        http_host = os.environ.get(
            "CONTEXTOR_MCP_HOST",
            "127.0.0.1",
        )

        http_port = int(
            os.environ.get(
                "CONTEXTOR_MCP_PORT",
                "8765",
            )
        )

    backend_lease = None

    if role == "persistent-backend":
        backend_lease = (
            PersistentBackendLease.acquire(
                host=http_host,
                port=http_port,
                transport="streamable-http",
                process_registry=process_directory,
            )
        )

        atexit.register(
            backend_lease.release
        )

    try:
        _cleanup_orphaned_processes(
            process_directory
        )

        previous_registry = os.environ.get(
            "CONTEXTOR_MCP_PROCESS_REGISTRY"
        )

        os.environ[
            "CONTEXTOR_MCP_PROCESS_REGISTRY"
        ] = str(process_directory)

        server_record = _register_server_root(
            process_directory,
            role,
        )

        cleanup_done = False

        def _shutdown_cleanup() -> None:
            nonlocal cleanup_done

            if cleanup_done:
                return

            cleanup_done = True

            try:
                _shutdown_mcp_owned_processes(
                    process_directory,
                    os.getpid(),
                )
            finally:
                if server_record is not None:
                    remove_record(
                        server_record
                    )

                if previous_registry is None:
                    os.environ.pop(
                        "CONTEXTOR_MCP_PROCESS_REGISTRY",
                        None,
                    )
                else:
                    os.environ[
                        "CONTEXTOR_MCP_PROCESS_REGISTRY"
                    ] = previous_registry

        atexit.register(
            _shutdown_cleanup
        )

        async def _run():
            if transport in _HTTP_TRANSPORTS:
                await mcp.run_http_async(
                    transport="streamable-http",
                    host=http_host,
                    port=http_port,
                    show_banner=False,
                )
            else:
                await mcp.run_stdio_async()

        try:
            asyncio.run(
                _run()
            )
        finally:
            _shutdown_cleanup()

    finally:
        if backend_lease is not None:
            backend_lease.release()

```

### contextor.mcp_server::_shutdown_mcp_owned_processes

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_server.py
SYMBOL=contextor.mcp_server::_shutdown_mcp_owned_processes
SOURCE_LINES=lines 620-642

```python
def _shutdown_mcp_owned_processes(
    directory: Path,
    owner_pid: int,
    *,
    timeout: float = 1.5,
) -> None:
    from contextor.mcp import analysis_jobs
    analysis_jobs.request_analysis_shutdown(
        timeout=timeout,
    )
    terminate_active_process_pools(
        timeout=timeout,
    )
    analysis_jobs.request_analysis_shutdown(
        timeout=timeout,
    )
    _cleanup_owned_processes(
        directory,
        owner_pid,
    )
    _cleanup_orphaned_processes(
        directory,
    )

```

### contextor.mcp_backend_autostart::launch_backend_autostart

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py
SYMBOL=contextor.mcp_backend_autostart::launch_backend_autostart
SOURCE_LINES=lines 242-253

```python
def launch_backend_autostart() -> bool:
    try:
        status = start_backend(
            timeout=AUTOSTART_START_TIMEOUT,
            probe_timeout=AUTOSTART_PROBE_TIMEOUT,
        )
    except BackendControlError:
        return False

    return bool(
        status.ready
    )

```

### contextor.mcp_backend_autostart::main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py
SYMBOL=contextor.mcp_backend_autostart::main
SOURCE_LINES=lines 288-338

```python
def main(
    argv: list[str] | None = None,
) -> int:
    args = (
        _build_parser()
        .parse_args(argv)
    )

    if args.command == "launch":
        return (
            0
            if launch_backend_autostart()
            else 1
        )

    try:
        if args.command == "install":
            status = (
                install_backend_autostart()
            )
        elif args.command == "remove":
            status = (
                remove_backend_autostart()
            )
        else:
            status = (
                get_backend_autostart_status()
            )

    except BackendAutostartError as exc:
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 1

    _emit_status(
        status
    )

    if args.command == "status":
        return (
            0
            if (
                status.installed
                and status.command_matches
            )
            else 1
        )

    return 0

```

### contextor.mcp_backend_cli::main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_cli.py
SYMBOL=contextor.mcp_backend_cli::main
SOURCE_LINES=lines 63-90

```python
def main(
    argv: list[str] | None = None,
) -> int:
    args = _build_parser().parse_args(argv)

    try:
        if args.command == "start":
            status = start_backend()

        elif args.command == "status":
            status = get_backend_status()

        else:
            status = stop_backend()

    except BackendControlError as exc:
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 1

    _emit_status(status)

    if args.command == "status":
        return 0 if status.ready else 1

    return 0

```

### contextor.__main__::main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\__main__.py
SYMBOL=contextor.__main__::main
SOURCE_LINES=lines 78-118

```python
def main(argv: list[str] | None = None) -> int:
    """
    Application entry point.
    """

    argv = list(sys.argv[1:] if argv is None else argv)

    if "--gui" in argv:
        return _run_gui()

    # '--cli' is accepted for symmetry with '--gui' and documentation,
    # but CLI is the default mode.
    cli_argv = [
        arg
        for arg in argv
        if arg != "--cli"
    ]

    if (
        len(cli_argv) >= 2
        and cli_argv[0] == "backend"
        and cli_argv[1]
        in {
            "start",
            "status",
            "stop",
        }
    ):
        from contextor.mcp_backend_cli import (
            main as backend_cli_main,
        )

        return backend_cli_main(
            cli_argv[1:]
        )

    from contextor.cli import main as cli_main

    return cli_main(
        cli_argv
    )

```

### contextor.mcp_main::main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_main.py
SYMBOL=contextor.mcp_main::main
SOURCE_LINES=lines 4-7

```python
def main() -> None:
    from contextor.mcp_server import main as run_server

    run_server()

```

### contextor.mcp_backend_control::_record_process_matches

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_record_process_matches
SOURCE_LINES=lines 125-130

```python
def _record_process_matches(
    record: PersistentBackendRecord,
) -> bool:
    return record_matches_process(
        record.to_dict()
    )

```

### contextor.mcp_backend_control::_cleanup_stale_backend_record

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
SYMBOL=contextor.mcp_backend_control::_cleanup_stale_backend_record
SOURCE_LINES=lines 602-611

```python
def _cleanup_stale_backend_record(
    status: BackendStatus,
) -> None:
    if (
        status.state == "stale"
        and status.record is not None
    ):
        remove_backend_record_if_exact(
            status.record
        )

```

### contextor.core.paths::state_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\paths.py
SYMBOL=contextor.core.paths::state_dir
SOURCE_LINES=lines 310-324

```python
def state_dir() -> Path:
    """
    Directory holding user-level UI state and exclude configuration.

    Kept out of the installation directory, which may be read-only.

    Override with the CONTEXTOR_STATE_DIR environment variable.
    """

    return _env_dir("CONTEXTOR_STATE_DIR") or _platform_dir(
        "APPDATA",
        "Contextor",
        "XDG_CONFIG_HOME",
        Path(".config") / "contextor",
    )

```


### Desktop initialization, LIVE attachment, backend restart and close

### ContextorGUI.__init__

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI.__init__
SOURCE_LINES=lines 88-139

```python
    def __init__(self, root):
        self.root = root
        self.root.title("Contextor")

        self.state = load_state()
        gui_pos = self.state.get("gui_pos", "")
        if gui_pos:
            self.root.geometry(gui_pos)
        self.root.minsize(680, 560)

        self.theme_mode = self.state.get("theme", "light")
        if self.theme_mode not in theme.MODES:
            self.theme_mode = "light"
        apply_theme(self.root, self.theme_mode)

        self.repo_path_var = tk.StringVar(value=self.state.get("repository", "").replace("\\", "/"))
        self.layer_path_var = tk.StringVar(value=self.state.get("layer", "").replace("\\", "/"))
        self.file_path_var = tk.StringVar(
            value=self.state.get("python_file", "").replace("\\", "/")
        )
        self._selected_live_repo_path = self.repo_path_var.get()
        self._repo_path_trace_id = self.repo_path_var.trace_add(
            "write",
            self._sync_selected_live_repository_path,
        )

        self.exclude_win = None
        self.repo_builder_win = None
        self.parser_win = None
        self.owner_token = uuid.uuid4().hex
        self.desktop_instance_id = uuid.uuid4().hex
        self.live_client = None
        self.live_clients = {}
        self.live_watcher = None
        self.live_event_feed = None
        self.live_watchers = {}
        self.live_event_feeds = {}
        self._live_start_retry_attempt = 0
        self._live_start_retry_after_id = None
        self.live_status_var = tk.StringVar(value="LIVE: waiting for analysis")
        self.repo_id_var = tk.StringVar(value="Repo ID: unregistered")
        self._live_status_queue: Queue[str] = Queue()
        self._live_status_draining = False
        self.last_live_state: dict[str, Any] | None = None

        self._closing = False
        self._live_start_lock = threading.Lock()
        self._live_start_inflight: set[str] = set()
        self._live_start_threads: dict[str, threading.Thread] = {}
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, self._start_post_paint_tasks)

```

### ContextorGUI._start_post_paint_tasks

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI._start_post_paint_tasks
SOURCE_LINES=lines 141-156

```python
    def _start_post_paint_tasks(self):
        if getattr(self, "_closing", False):
            return
        self._set_live_status("LIVE: initializing in background")
        def cleanup_worker():
            try:
                cache_cleanup = prune_startup_caches()
                if any(section["errors"] for section in cache_cleanup.values()):
                    self._set_live_status("LIVE: cache cleanup incomplete")
            except Exception as exc:
                self._set_live_status(f"LIVE: cache cleanup failed: {exc}")
        threading.Thread(target=cleanup_worker, name="contextor-startup-cache-cleanup", daemon=True).start()
        self._check_stale_excludes()
        repo_path = self.repo_path_var.get()
        if repo_path and Path(repo_path).is_dir():
            self._start_live_watcher(repo_path)

```

### ContextorGUI._start_live_watcher

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI._start_live_watcher
SOURCE_LINES=lines 1006-1036

```python
    def _start_live_watcher(self, path, initial_seq: int | None = None):
        if getattr(self, "_closing", False):
            return
        try:
            path_key = str(Path(path).expanduser().resolve())
        except Exception:
            path_key = str(path)
        lock = getattr(self, "_live_start_lock", None)
        if lock is None:
            lock = self._live_start_lock = threading.Lock()
        inflight = getattr(self, "_live_start_inflight", None)
        if inflight is None:
            inflight = self._live_start_inflight = set()
        threads = getattr(self, "_live_start_threads", None)
        if threads is None:
            threads = self._live_start_threads = {}
        with lock:
            if getattr(self, "_closing", False) or path_key in inflight:
                return
            inflight.add(path_key)
        def runner():
            try:
                ContextorGUI._start_live_watcher_blocking(self, path, initial_seq=initial_seq)
            finally:
                with lock:
                    inflight.discard(path_key)
                    threads.pop(path_key, None)
        thread = threading.Thread(target=runner, name="contextor-live-desktop-start", daemon=True)
        with lock:
            threads[path_key] = thread
        thread.start()

```

### ContextorGUI._start_live_watcher_blocking

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI._start_live_watcher_blocking
SOURCE_LINES=lines 1038-1281

```python
    def _start_live_watcher_blocking(self, path, initial_seq: int | None = None):
        """Connect and retain one independent LIVE watcher per repository ID."""
        if getattr(self, "_closing", False):
            return
        try:
            identity = ContextorGUI._refresh_repo_identity(self, path)
        except RepositoryIdentityError as exc:
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status(f"LIVE identity error: {exc}")
            return
        if identity is None:
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status("LIVE: repository not registered; run an analysis")
            return
        watchers = getattr(self, "live_watchers", None)
        if watchers is None:
            watchers = self.live_watchers = {}
        feeds = getattr(self, "live_event_feeds", None)
        if feeds is None:
            feeds = self.live_event_feeds = {}
        clients = getattr(self, "live_clients", None)
        if clients is None:
            clients = self.live_clients = {}

        existing_watcher = watchers.get(identity.repo_id)
        if existing_watcher is not None:
            existing_client = clients.get(identity.repo_id)
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_watcher = existing_watcher
                self.live_event_feed = feeds.get(identity.repo_id)
                if existing_client is not None:
                    self.live_client = existing_client
                self._set_live_status(
                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
                )
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
            return

        try:
            connect_kwargs = {
                "owner_pid": os.getpid(),
                "owner_token": getattr(self, "owner_token", None),
            }
            import inspect

            parameters = inspect.signature(connect_or_start).parameters
            if "desktop_instance_id" in parameters:
                connect_kwargs["desktop_instance_id"] = getattr(self, "desktop_instance_id", None)
            if "client_kind" in parameters:
                connect_kwargs["client_kind"] = "desktop"
            client = connect_or_start(path, **connect_kwargs)
            clients[identity.repo_id] = client
            if getattr(self, "_closing", False):
                return
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_client = client
            cache = migrate_legacy_snapshot(path)
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
        except SecondDesktopActive as exc:
            self._live_start_retry_attempt = 0
            self._live_start_retry_after_id = None
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status(f"LIVE: {exc}")
            return
        except (OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError) as exc:
            if getattr(self, "_closing", False):
                return
            current_attempt = getattr(self, "_live_start_retry_attempt", 0) + 1
            self._live_start_retry_attempt = current_attempt
            if current_attempt < LIVE_START_MAX_ATTEMPTS:
                delay_idx = min(current_attempt - 1, len(LIVE_START_RETRY_DELAYS_MS) - 1)
                delay_ms = LIVE_START_RETRY_DELAYS_MS[delay_idx]
                if ContextorGUI._is_selected_live_repository(self, path):
                    self._set_live_status(
                        f"LIVE connection delayed; retrying ({current_attempt + 1}/{LIVE_START_MAX_ATTEMPTS})..."
                    )
                if hasattr(self, "root") and hasattr(self.root, "after"):
                    self._live_start_retry_after_id = self.root.after(
                        delay_ms, lambda: ContextorGUI._start_live_watcher(self, path, initial_seq=initial_seq)
                    )
                return
            self._live_start_retry_attempt = 0
            self._live_start_retry_after_id = None
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status(f"LIVE connection error: {exc}")
            return

        from contextor.core.analysis.state_manager import load_engine_state

        state = load_engine_state(
            str(cache),
            "",
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )
        if state is not None:
            current = client.snapshot() if hasattr(client, "snapshot") else {}
            state_revision = getattr(state, "revision", None)
            live_state = current.get("state") if isinstance(current, dict) else None
            live_revision = current.get("revision") if isinstance(current, dict) else None
            state_id = getattr(state, "state_id", None)
            if state_revision is not None and live_revision == int(state_revision):
                if state_id and getattr(live_state, "state_id", None) == state_id:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        self._set_live_status("LIVE: shared state attached; watcher active")
                else:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        self._set_live_status("LIVE: generation conflict; analysis required")
                    return
            else:
                startup_lease = None
                try:
                    startup_lease = acquire_full_analysis(
                        path,
                        owner="desktop_startup_publish",
                        writer_kind="startup_publish",
                        timeout=0.0,
                        poll_interval=0.01,
                    )
                except FullAnalysisBusyError:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        self._set_live_status(
                            "LIVE: canonical writer busy; cache publish skipped"
                        )
                else:
                    try:
                        published = client.publish(
                            state,
                            origin="desktop_analysis",
                        )
                    finally:
                        release_full_analysis(startup_lease)
                    if (
                        isinstance(published, dict)
                        and published.get("status") == "ok"
                    ):
                        if ContextorGUI._is_selected_live_repository(self, path):
                            self._set_live_status(
                                "LIVE: shared state published; watcher active"
                            )
                    else:
                        if ContextorGUI._is_selected_live_repository(self, path):
                            self._set_live_status(
                                "LIVE: shared state attach failed; analysis required"
                            )
        else:
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status("LIVE: no snapshot; waiting for analysis")
        existing_watcher = watchers.get(identity.repo_id)
        if existing_watcher is not None:
            existing_client = clients.get(identity.repo_id)
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_watcher = existing_watcher
                self.live_event_feed = feeds.get(identity.repo_id)
                if existing_client is not None:
                    self.live_client = existing_client
                self._set_live_status(
                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
                )
            return

        def status_callback(message, event=None, name=identity.repo_name):
            if not ContextorGUI._is_selected_live_repository(self, path):
                return
            if event is None and (message.startswith("LIVE update successful:") or message.startswith("Updating LIVE:")):
                return
            cat = event.get("category", "LIVE_STATE") if isinstance(event, dict) else "LIVE_STATE"
            if message.startswith("[LIVE] "):
                body = message[7:]
                msg = f"[LIVE] [{name}] {body}"
            elif message.startswith("[MCP] "):
                body = message[6:]
                msg = f"[MCP] [{name}] {body}"
            else:
                msg = f"[{name}] {message}"
            self._set_live_status(msg, category=cat, event=event)

        def on_reconnect(new_client):
            self.live_clients[identity.repo_id] = new_client
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_client = new_client
            feed = feeds.get(identity.repo_id)
            if feed is not None:
                feed.client = new_client

        def on_resync():
            from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
            return run_full_analysis_exclusive(
                path,
                owner="desktop_analysis",
                timeout=30.0,
            )

        if getattr(self, "_closing", False):
            return
        watcher = DesktopLiveWatcher(
            path,
            client,
            owner_pid=os.getpid(),
            owner_token=getattr(self, "owner_token", None),
            desktop_instance_id=getattr(self, "desktop_instance_id", None),
            on_status=status_callback,
            on_reconnect=on_reconnect,
            on_resync=on_resync,
        )
        if initial_seq is not None:
            feed = DesktopLiveEventFeed(
                client,
                status_callback,
                initial_seq=initial_seq,
            )
            if hasattr(feed, "poll_once"):
                feed.poll_once()
        else:
            feed = DesktopLiveEventFeed(
                client,
                status_callback,
            )

        watchers[identity.repo_id] = watcher
        feeds[identity.repo_id] = feed
        if ContextorGUI._is_selected_live_repository(self, path):
            self.live_watcher = watcher
            self.live_event_feed = feed
        if hasattr(feed, "replay_authority_events"):
            feed.replay_authority_events()
        if getattr(self, "_closing", False):
            return
        watcher.start()
        feed.start()

```

### ContextorGUI._restart_backend

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI._restart_backend
SOURCE_LINES=lines 683-790

```python
    def _restart_backend(self):
        """
        Restart the persistent MCP backend without blocking the Tk main loop.
        """

        operation_title = "Restart Backend"

        def _identity(status):
            record = status.record
            if record is None:
                return None

            return (
                record.instance_id,
                record.pid,
                record.creation_time,
            )

        def task(log=None, progress_callback=None):
            before = get_backend_status(
                probe_timeout=2.0,
            )
            before_identity = _identity(before)

            stop_backend(
                timeout=5.0,
            )

            stopped = get_backend_status(
                probe_timeout=0.5,
            )

            if (
                stopped.state != "stopped"
                or stopped.ready
                or stopped.record is not None
            ):
                raise RuntimeError(
                    "persistent MCP backend did not reach a confirmed stopped state"
                )

            after = start_backend(
                timeout=20.0,
                probe_timeout=2.0,
            )

            if not after.ready or after.record is None:
                raise RuntimeError(
                    "new persistent MCP backend did not become authenticated and ready"
                )

            after_identity = _identity(after)

            if (
                before_identity is not None
                and after_identity == before_identity
            ):
                raise RuntimeError(
                    "backend restart returned the previous backend process identity"
                )

            return before, after

        def on_success(result):
            before, after = result

            old_pid = (
                "none"
                if before.record is None
                else str(before.record.pid)
            )
            old_instance = (
                "none"
                if before.record is None
                else before.record.instance_id
            )

            messagebox.showinfo(
                "MCP backend restarted",
                (
                    "Persistent MCP backend restarted successfully.\n\n"
                    f"Old PID: {old_pid}\n"
                    f"Old instance: {old_instance}\n"
                    f"New PID: {after.record.pid}\n"
                    f"New instance: {after.record.instance_id}\n"
                    f"Endpoint: {after.endpoint}"
                ),
            )

        def on_error(exc):
            messagebox.showerror(
                operation_title,
                f"Backend restart failed.\n\n{exc}",
            )

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=self._busy_buttons(),
            log_box=self.log_box,
            cpu_indicator=self.cpu_indicator,
            stop_button=self.stop_btn,
        )

```

### ContextorGUI.on_closing

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\ui\gui.py
SYMBOL=ContextorGUI.on_closing
SOURCE_LINES=lines 1441-1554

```python
    def on_closing(self):
        import re
        import time

        self._closing = True
        close_cmd_log()

        # Route Desktop shutdown through the same cancellation path as Stop
        # analyze so an active full-analysis lease reaches its existing
        # coordinator finally/release before this process exits.
        if hasattr(self, "progress_bar"):
            self.progress_bar.is_cancelled = True

        full_analysis_done = getattr(self, "_full_analysis_done", None)
        if full_analysis_done is not None and not full_analysis_done.is_set():
            # Wait only for the task body. The daemon worker is allowed to
            # finish UI callbacks after this bound; process exit remains the
            # safe fallback for a task that ignores cooperative cancellation.
            full_analysis_done.wait(timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS)

        terminate_active_process_pools(
            timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS,
        )

        if (
            full_analysis_done is not None
            and not full_analysis_done.is_set()
        ):
            full_analysis_done.wait(
                timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS
            )

        if getattr(self, "_live_start_retry_after_id", None) is not None:
            if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                try:
                    self.root.after_cancel(self._live_start_retry_after_id)
                except Exception:
                    pass
            self._live_start_retry_after_id = None
        self._live_start_retry_attempt = 0

        watchers = list(getattr(self, "live_watchers", {}).values())
        feeds = list(getattr(self, "live_event_feeds", {}).values())
        for watcher in watchers:
            watcher.stop()
        for feed in feeds:
            feed.stop()

        clients = list(getattr(self, "live_clients", {}).values())
        live_client = getattr(self, "live_client", None)
        if live_client is not None and live_client not in clients:
            clients.append(live_client)

        gui_owner_token = getattr(self, "owner_token", None)
        gui_desktop_id = getattr(self, "desktop_instance_id", None)
        for client in clients:
            is_owner = getattr(client, "is_owner", False)
            client_token = getattr(client, "owner_token", None)
            service_pid = getattr(client, "service_pid", None)

            if (
                gui_desktop_id is not None
                and getattr(client, "desktop_instance_id", None) == gui_desktop_id
                and hasattr(client, "release_desktop_claim")
            ):
                try:
                    desktop_identity = getattr(client, "desktop_process_identity", None)
                    if desktop_identity is not None:
                        client.release_desktop_claim(gui_desktop_id, desktop_identity)
                except Exception:
                    pass

            can_shutdown = (
                is_owner is True
                and gui_owner_token is not None
                and client_token is not None
                and client_token == gui_owner_token
                and service_pid is not None
            )
            if not can_shutdown:
                continue

            try:
                client.request("shutdown", timeout=1.5)
            except Exception:
                pass
            if service_pid is not None:
                from contextor.core.live_state.runtime import _is_pid_alive, _terminate_pid_tree

                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    if not _is_pid_alive(service_pid):
                        break
                    time.sleep(0.05)
                if _is_pid_alive(service_pid):
                    _terminate_pid_tree(service_pid)

        geom = self.root.geometry()
        m = re.match(r"^(\d+x\d+)([+-]?\d+)([+-]?\d+)$", geom.replace("+-", "-"))
        if m:
            size = m.group(1)
            x, y = max(0, int(m.group(2))), max(0, int(m.group(3)))
            pos = f"{size}+{x}+{y}"
        else:
            pos = ""

        save_state(
            gui_pos=pos,
            theme=self.theme_mode,
            repository=self.repo_path_var.get(),
            layer=self.layer_path_var.get(),
            python_file=self.file_path_var.get(),
        )
        self.root.destroy()

```


### LIVE lease/generation and IPC owner claim implementations

### contextor.core.live_state.runtime_lease::RuntimeLease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLease
SOURCE_LINES=lines 366-494

```python
@dataclass(frozen=True, slots=True)
class RuntimeLease:
    schema_version: int
    repo_id: str
    runtime_domain_id: str
    mode: RuntimeMode
    repo_root: str
    repo_root_fingerprint: str
    service_instance_id: str
    lease_generation: int
    service_pid: int
    process_start_identity: str
    endpoint_fingerprint: str | None
    started_at: float
    last_heartbeat_at: float
    owner_token: str | None
    resource_root_fingerprints: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_LEASE_SCHEMA_VERSION:
            raise RuntimeLeaseError("unsupported RuntimeLease schema_version")
        if self.mode not in ("production", "test"):
            raise RuntimeLeaseError("mode must be production or test")
        for field in ("repo_id", "runtime_domain_id", "service_instance_id"):
            object.__setattr__(self, field, _non_empty_text(getattr(self, field), field=field))
        object.__setattr__(self, "repo_root", _canonical_path_text(self.repo_root, field="repo_root"))
        object.__setattr__(
            self,
            "repo_root_fingerprint",
            _non_empty_text(self.repo_root_fingerprint, field="repo_root_fingerprint"),
        )
        object.__setattr__(self, "lease_generation", _positive_int(self.lease_generation, field="lease_generation"))
        object.__setattr__(self, "service_pid", _positive_int(self.service_pid, field="service_pid"))
        object.__setattr__(
            self,
            "process_start_identity",
            _non_empty_text(self.process_start_identity, field="process_start_identity"),
        )
        object.__setattr__(self, "started_at", _timestamp(self.started_at, field="started_at"))
        object.__setattr__(self, "last_heartbeat_at", _timestamp(self.last_heartbeat_at, field="last_heartbeat_at"))
        if self.last_heartbeat_at < self.started_at:
            raise RuntimeLeaseError("last_heartbeat_at cannot precede started_at")
        if self.endpoint_fingerprint is not None:
            object.__setattr__(
                self,
                "endpoint_fingerprint",
                _non_empty_text(self.endpoint_fingerprint, field="endpoint_fingerprint"),
            )
        if self.owner_token is not None:
            object.__setattr__(self, "owner_token", _non_empty_text(self.owner_token, field="owner_token"))
        fingerprints = tuple(self.resource_root_fingerprints)
        if tuple(name for name, _ in fingerprints) != _RESOURCE_KEYS:
            raise RuntimeLeaseError("resource_root_fingerprints do not match schema")
        fingerprints = tuple(
            (name, _non_empty_text(value, field=f"resource_root_fingerprints.{name}"))
            for name, value in fingerprints
        )
        object.__setattr__(self, "resource_root_fingerprints", fingerprints)
        if dict(fingerprints)["repo_root"] != self.repo_root_fingerprint:
            raise RuntimeLeaseError("repo_root_fingerprint does not match resource fingerprints")

    def matches_domain(self, domain: RuntimeDomain) -> bool:
        return (
            self.repo_id == domain.repo_id
            and self.runtime_domain_id == domain.domain_id
            and self.mode == domain.mode
            and self.repo_root == _canonical_path_text(domain.repo_root, field="repo_root")
            and self.resource_root_fingerprints == _domain_resource_fingerprints(domain)
        )

    def owner_tuple(self) -> tuple[str, int]:
        return self.service_instance_id, self.lease_generation

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_id": self.repo_id,
            "runtime_domain_id": self.runtime_domain_id,
            "mode": self.mode,
            "repo_root": self.repo_root,
            "repo_root_fingerprint": self.repo_root_fingerprint,
            "service_instance_id": self.service_instance_id,
            "lease_generation": self.lease_generation,
            "service_pid": self.service_pid,
            "process_start_identity": self.process_start_identity,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "started_at": self.started_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "owner_token": self.owner_token,
            "resource_root_fingerprints": _fingerprints_to_dict(self.resource_root_fingerprints),
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RuntimeLease":
        if not isinstance(payload, Mapping) or set(payload) != _LEASE_FIELDS:
            raise RuntimeLeaseError("RuntimeLease payload fields do not match schema")
        return cls(
            schema_version=payload["schema_version"],
            repo_id=payload["repo_id"],
            runtime_domain_id=payload["runtime_domain_id"],
            mode=payload["mode"],
            repo_root=payload["repo_root"],
            repo_root_fingerprint=payload["repo_root_fingerprint"],
            service_instance_id=payload["service_instance_id"],
            lease_generation=payload["lease_generation"],
            service_pid=payload["service_pid"],
            process_start_identity=payload["process_start_identity"],
            endpoint_fingerprint=payload["endpoint_fingerprint"],
            started_at=payload["started_at"],
            last_heartbeat_at=payload["last_heartbeat_at"],
            owner_token=payload["owner_token"],
            resource_root_fingerprints=_fingerprints_from_payload(payload["resource_root_fingerprints"]),
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "RuntimeLease":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except (TypeError, ValueError) as exc:
                raise RuntimeLeaseError("invalid RuntimeLease JSON") from exc
        else:
            value = payload
        if not isinstance(value, Mapping):
            raise RuntimeLeaseError("RuntimeLease payload must be an object")
        return cls.from_dict(value)

```

### contextor.core.live_state.runtime_lease::ProcessIdentity

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::ProcessIdentity
SOURCE_LINES=lines 215-247

```python
@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    """PID plus a process-start token; PID alone is never sufficient."""

    pid: int
    process_start_identity: str
    executable_fingerprint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pid", _positive_int(self.pid, field="pid"))
        object.__setattr__(
            self,
            "process_start_identity",
            _non_empty_text(self.process_start_identity, field="process_start_identity"),
        )
        if self.executable_fingerprint is not None:
            object.__setattr__(
                self,
                "executable_fingerprint",
                _non_empty_text(self.executable_fingerprint, field="executable_fingerprint"),
            )

    @classmethod
    def current(cls, pid: int | None = None) -> "ProcessIdentity":
        current_pid = os.getpid() if pid is None else _positive_int(pid, field="pid")
        try:
            image, creation_time, alive = _process_identity(current_pid)
        except Exception as exc:  # pragma: no cover - platform probe boundary
            raise RuntimeLeaseError("process identity probe failed") from exc
        if not alive or creation_time is None:
            raise RuntimeLeaseError("current process identity is unavailable")
        executable = _path_fingerprint(image) if image else None
        return cls(current_pid, str(creation_time), executable)

```

### contextor.core.live_state.runtime_lease::AuthorityGenerationRecord

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::AuthorityGenerationRecord
SOURCE_LINES=lines 497-690

```python
@dataclass(frozen=True, slots=True)
class AuthorityGenerationRecord:
    schema_version: int
    repo_id: str
    runtime_domain_id: str
    mode: RuntimeMode
    repo_root: str
    repo_root_fingerprint: str
    last_lease_generation: int
    last_service_instance_id: str | None
    service_pid: int | None
    process_start_identity: str | None
    endpoint_fingerprint: str | None
    status: GenerationStatus
    fenced_service_instance_id: str | None
    fenced_lease_generation: int | None
    updated_at: float
    resource_root_fingerprints: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.schema_version != AUTHORITY_GENERATION_SCHEMA_VERSION:
            raise RuntimeLeaseError("unsupported authority-generation schema_version")
        if self.mode not in ("production", "test"):
            raise RuntimeLeaseError("mode must be production or test")
        for field in ("repo_id", "runtime_domain_id"):
            object.__setattr__(self, field, _non_empty_text(getattr(self, field), field=field))
        object.__setattr__(self, "repo_root", _canonical_path_text(self.repo_root, field="repo_root"))
        object.__setattr__(
            self,
            "repo_root_fingerprint",
            _non_empty_text(self.repo_root_fingerprint, field="repo_root_fingerprint"),
        )
        object.__setattr__(
            self,
            "last_lease_generation",
            _positive_int(self.last_lease_generation, field="last_lease_generation", allow_zero=True),
        )
        if self.status not in ("never_acquired", "reserved", "active", "released", "fenced"):
            raise RuntimeLeaseError("invalid authority-generation status")
        for field in ("last_service_instance_id", "fenced_service_instance_id", "process_start_identity"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _non_empty_text(value, field=field))
        if self.service_pid is not None:
            object.__setattr__(self, "service_pid", _positive_int(self.service_pid, field="service_pid"))
        if self.endpoint_fingerprint is not None:
            object.__setattr__(
                self,
                "endpoint_fingerprint",
                _non_empty_text(self.endpoint_fingerprint, field="endpoint_fingerprint"),
            )
        current_identity_complete = (
            self.last_service_instance_id is not None
            and self.service_pid is not None
            and self.process_start_identity is not None
        )
        if self.status == "never_acquired":
            if self.last_lease_generation != 0 or any(
                value is not None
                for value in (
                    self.last_service_instance_id,
                    self.service_pid,
                    self.process_start_identity,
                    self.endpoint_fingerprint,
                    self.fenced_service_instance_id,
                    self.fenced_lease_generation,
                )
            ):
                raise RuntimeLeaseError("never_acquired generation must have no owner or fence identity")
        else:
            if self.last_lease_generation == 0 or not current_identity_complete:
                raise RuntimeLeaseError("generation status requires complete current owner identity")
        fence_pair_complete = self.fenced_service_instance_id is not None and self.fenced_lease_generation is not None
        if self.status in ("reserved", "active") and (
            self.fenced_service_instance_id is not None or self.fenced_lease_generation is not None
        ):
            raise RuntimeLeaseError("reserved/active generation cannot carry a fence pair")
        if self.status in ("released", "fenced") and not fence_pair_complete:
            raise RuntimeLeaseError("released/fenced generation requires a complete fence pair")
        if fence_pair_complete and (
            self.fenced_service_instance_id != self.last_service_instance_id
            or self.fenced_lease_generation != self.last_lease_generation
        ):
            raise RuntimeLeaseError("fence pair must match the durable owner generation")
        if self.fenced_lease_generation is not None:
            object.__setattr__(
                self,
                "fenced_lease_generation",
                _positive_int(self.fenced_lease_generation, field="fenced_lease_generation"),
            )
        object.__setattr__(self, "updated_at", _timestamp(self.updated_at, field="updated_at"))
        fingerprints = tuple(self.resource_root_fingerprints)
        if tuple(name for name, _ in fingerprints) != _RESOURCE_KEYS:
            raise RuntimeLeaseError("resource_root_fingerprints do not match schema")
        object.__setattr__(
            self,
            "resource_root_fingerprints",
            tuple(
                (name, _non_empty_text(value, field=f"resource_root_fingerprints.{name}"))
                for name, value in fingerprints
            ),
        )
        if dict(self.resource_root_fingerprints)["repo_root"] != self.repo_root_fingerprint:
            raise RuntimeLeaseError("repo_root_fingerprint does not match resource fingerprints")

    @classmethod
    def initial(cls, domain: RuntimeDomain, *, now: float | None = None) -> "AuthorityGenerationRecord":
        fingerprints = _domain_resource_fingerprints(domain)
        return cls(
            schema_version=AUTHORITY_GENERATION_SCHEMA_VERSION,
            repo_id=domain.repo_id,
            runtime_domain_id=domain.domain_id,
            mode=domain.mode,
            repo_root=_canonical_path_text(domain.repo_root, field="repo_root"),
            repo_root_fingerprint=dict(fingerprints)["repo_root"],
            last_lease_generation=0,
            last_service_instance_id=None,
            service_pid=None,
            process_start_identity=None,
            endpoint_fingerprint=None,
            status="never_acquired",
            fenced_service_instance_id=None,
            fenced_lease_generation=None,
            updated_at=time.time() if now is None else now,
            resource_root_fingerprints=fingerprints,
        )

    def matches_domain(self, domain: RuntimeDomain) -> bool:
        return (
            self.repo_id == domain.repo_id
            and self.runtime_domain_id == domain.domain_id
            and self.mode == domain.mode
            and self.repo_root == _canonical_path_text(domain.repo_root, field="repo_root")
            and self.resource_root_fingerprints == _domain_resource_fingerprints(domain)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_id": self.repo_id,
            "runtime_domain_id": self.runtime_domain_id,
            "mode": self.mode,
            "repo_root": self.repo_root,
            "repo_root_fingerprint": self.repo_root_fingerprint,
            "last_lease_generation": self.last_lease_generation,
            "last_service_instance_id": self.last_service_instance_id,
            "service_pid": self.service_pid,
            "process_start_identity": self.process_start_identity,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "status": self.status,
            "fenced_service_instance_id": self.fenced_service_instance_id,
            "fenced_lease_generation": self.fenced_lease_generation,
            "updated_at": self.updated_at,
            "resource_root_fingerprints": _fingerprints_to_dict(self.resource_root_fingerprints),
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityGenerationRecord":
        if not isinstance(payload, Mapping) or set(payload) != _GENERATION_FIELDS:
            raise RuntimeLeaseError("authority-generation payload fields do not match schema")
        return cls(
            schema_version=payload["schema_version"],
            repo_id=payload["repo_id"],
            runtime_domain_id=payload["runtime_domain_id"],
            mode=payload["mode"],
            repo_root=payload["repo_root"],
            repo_root_fingerprint=payload["repo_root_fingerprint"],
            last_lease_generation=payload["last_lease_generation"],
            last_service_instance_id=payload["last_service_instance_id"],
            service_pid=payload["service_pid"],
            process_start_identity=payload["process_start_identity"],
            endpoint_fingerprint=payload["endpoint_fingerprint"],
            status=payload["status"],
            fenced_service_instance_id=payload["fenced_service_instance_id"],
            fenced_lease_generation=payload["fenced_lease_generation"],
            updated_at=payload["updated_at"],
            resource_root_fingerprints=_fingerprints_from_payload(payload["resource_root_fingerprints"]),
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "AuthorityGenerationRecord":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except (TypeError, ValueError) as exc:
                raise RuntimeLeaseError("invalid authority-generation JSON") from exc
        else:
            value = payload
        if not isinstance(value, Mapping):
            raise RuntimeLeaseError("authority-generation payload must be an object")
        return cls.from_dict(value)

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.acquire

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.acquire
SOURCE_LINES=lines 1363-1441

```python
    def acquire(self) -> RuntimeLease:
        self._emit_authority(
            "RUNTIME_LEASE_ACQUIRE",
            decision="REQUEST",
            status="REQUESTED",
            reason="authority lease acquisition requested",
        )
        while True:
            with self._lock():
                record = self._read_generation()
                live = self._read_live_lease()
                if live is None:
                    if record.status == "active":
                        self._emit_authority(
                            "RUNTIME_LEASE_RECOVERY_REQUIRED",
                            decision="REJECT_TAKEOVER",
                            status="RECOVERY_REQUIRED",
                            reason="active durable authority has no live lease",
                        )
                        raise LeaseRecoveryRequired(
                            "active durable authority has no live lease; recovery is required before takeover"
                        )
                    return self._allocate_next_locked(record)
                if record.status in {"released", "fenced"}:
                    same_fenced = (
                        record.fenced_service_instance_id == live.service_instance_id
                        and record.fenced_lease_generation == live.lease_generation
                    )
                    same_released = (
                        record.last_service_instance_id == live.service_instance_id
                        and record.last_lease_generation == live.lease_generation
                    )
                    same_identity = (
                        record.service_pid == live.service_pid
                        and record.process_start_identity == live.process_start_identity
                        and record.endpoint_fingerprint == live.endpoint_fingerprint
                    )
                    if not (same_fenced or same_released) or not same_identity:
                        raise ForeignLeaseError("fenced/released live lease does not match durable record")
                    self._remove_desktop_claim_if_owner(live)
                    self._remove_live_lease()
                    return self._allocate_next_locked(record)
                self._validate_live_record_parity(record, live)
                observed_record = record
                observed_live = live

            evidence = self.liveness_verifier.verify(observed_live)

            with self._lock():
                current_record = self._read_generation()
                current_live = self._read_live_lease()
                if current_record != observed_record or current_live != observed_live:
                    continue
                if evidence.status is LivenessStatus.LIVE:
                    self._emit_authority(
                        "RUNTIME_LEASE_TAKEOVER_REJECT",
                        service_instance_id=observed_live.service_instance_id,
                        lease_generation=observed_live.lease_generation,
                        process_id=observed_live.service_pid,
                        decision="REJECT_LIVE",
                        status="LIVE",
                        reason=evidence.reason,
                    )
                    raise LeaseAlreadyHeld(evidence.reason)
                if not evidence.confirmed_stale:
                    self._emit_authority(
                        "RUNTIME_LEASE_TAKEOVER_REJECT",
                        service_instance_id=observed_live.service_instance_id,
                        lease_generation=observed_live.lease_generation,
                        process_id=observed_live.service_pid,
                        decision="REJECT_AMBIGUOUS",
                        status=evidence.status.value.upper(),
                        reason=evidence.reason,
                    )
                    raise LeaseLivenessUnknown(
                        f"authority takeover rejected: {evidence.status.value}: {evidence.reason}"
                    )
                fenced = self._fence_stale_lease(current_record, current_live)
                return self._allocate_next_locked(fenced)

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.release

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.release
SOURCE_LINES=lines 1574-1596

```python
    def release(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
        with self._lock():
            current, record = self._assert_current_owner(lease)
            fenced = replace(
                record,
                status="released",
                fenced_service_instance_id=current.service_instance_id,
                fenced_lease_generation=current.lease_generation,
                updated_at=self._now(),
            )
            self._write_generation(fenced)
            self._remove_desktop_claim_if_owner(lease)
            self._inject("before_release_live_remove")
            self._remove_live_lease()
            self._emit_authority(
                "RUNTIME_LEASE_RELEASE",
                service_instance_id=current.service_instance_id,
                lease_generation=current.lease_generation,
                decision="RELEASE",
                status="RELEASED",
                reason="clean authority shutdown",
            )
            return fenced

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.refresh_heartbeat

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.refresh_heartbeat
SOURCE_LINES=lines 1461-1468

```python
    def refresh_heartbeat(self, lease: RuntimeLease, *, now: float | None = None) -> RuntimeLease:
        with self._lock():
            current, _record = self._assert_current_owner(lease)
            refreshed = replace(current, last_heartbeat_at=self._now() if now is None else _timestamp(now, field="now"))
            if refreshed.last_heartbeat_at < refreshed.started_at:
                raise RuntimeLeaseError("heartbeat cannot precede lease start")
            self._write_live_lease(refreshed)
            return refreshed

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.claim_desktop

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.claim_desktop
SOURCE_LINES=lines 1042-1197

```python
    def claim_desktop(
        self,
        lease: RuntimeLease,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        desktop_id = _non_empty_text(desktop_instance_id, field="desktop_instance_id")
        if not isinstance(desktop_process_identity, ProcessIdentity):
            raise RuntimeLeaseError("desktop_process_identity must be ProcessIdentity")
        for _attempt in range(3):
            with self._lock():
                current, record = self._assert_current_owner(lease)
                claim = self._read_desktop_claim_unlocked()
                if claim is None:
                    new_claim = {
                        "schema_version": DESKTOP_CLAIM_SCHEMA_VERSION,
                        "repo_id": self.domain.repo_id,
                        "runtime_domain_id": self.domain.domain_id,
                        "service_instance_id": current.service_instance_id,
                        "lease_generation": current.lease_generation,
                        "service_pid": current.service_pid,
                        "process_start_identity": current.process_start_identity,
                        "desktop_instance_id": desktop_id,
                        "desktop_pid": desktop_process_identity.pid,
                        "desktop_process_start_identity": desktop_process_identity.process_start_identity,
                    }
                    _atomic_write_json(desktop_claim_path(self.domain), new_claim)
                    self._emit_authority(
                        "DESKTOP_CLAIM_ACQUIRE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="ACQUIRE",
                        status="ACTIVE",
                        reason="desktop claim created",
                    )
                    return new_claim
                if (
                    claim["service_instance_id"] == current.service_instance_id
                    and claim["lease_generation"] == current.lease_generation
                    and claim["desktop_instance_id"] == desktop_id
                    and claim["desktop_pid"] == desktop_process_identity.pid
                    and claim["desktop_process_start_identity"] == desktop_process_identity.process_start_identity
                ):
                    self._emit_authority(
                        "DESKTOP_CLAIM_ACQUIRE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="IDEMPOTENT",
                        status="ACTIVE",
                        reason="desktop claim already owned by requester",
                    )
                    return claim
                observed_claim = dict(claim)
                observed_authority = (
                    current.service_instance_id,
                    current.lease_generation,
                    current.service_pid,
                    current.process_start_identity,
                    current.endpoint_fingerprint,
                    record.status,
                    record.endpoint_fingerprint,
                )

            try:
                _image, creation_time, alive = _process_identity(observed_claim["desktop_pid"])
            except Exception as exc:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process identity is unknown",
                    error=str(exc),
                )
                raise LeaseLivenessUnknown("desktop claim process identity is unknown") from exc
            if alive and creation_time is not None and str(creation_time) == observed_claim["desktop_process_start_identity"]:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT",
                    status="LIVE",
                    reason="desktop claim process is live",
                )
                raise DesktopClaimAlreadyHeld("repository already active in another Contextor Desktop")
            if alive and creation_time is None:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process start identity is unknown",
                )
                raise LeaseLivenessUnknown("desktop claim process start identity is unknown")
            if alive:
                claim_is_stale = True
            elif alive is False:
                claim_is_stale = True
            else:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process liveness is unknown",
                )
                raise LeaseLivenessUnknown("desktop claim process liveness is unknown")

            with self._lock():
                current, record = self._assert_current_owner(lease)
                reread_claim = self._read_desktop_claim_unlocked()
                reread_authority = (
                    current.service_instance_id,
                    current.lease_generation,
                    current.service_pid,
                    current.process_start_identity,
                    current.endpoint_fingerprint,
                    record.status,
                    record.endpoint_fingerprint,
                )
                if reread_claim != observed_claim or reread_authority != observed_authority:
                    continue
                if claim_is_stale:
                    replacement = dict(observed_claim)
                    replacement.update(
                        desktop_instance_id=desktop_id,
                        desktop_pid=desktop_process_identity.pid,
                        desktop_process_start_identity=desktop_process_identity.process_start_identity,
                    )
                    _atomic_write_json(desktop_claim_path(self.domain), replacement)
                    self._emit_authority(
                        "DESKTOP_CLAIM_REPLACE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="REPLACE_STALE",
                        status="ACTIVE",
                        reason="previous desktop claim is stale or PID identity mismatched",
                    )
                    return replacement
        self._emit_authority(
            "DESKTOP_CLAIM_REJECT",
            decision="REJECT_RACE",
            status="UNKNOWN",
            reason="desktop claim changed during liveness verification",
        )
        raise LeaseLivenessUnknown("desktop claim changed during liveness verification")

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.release_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.release_desktop_claim
SOURCE_LINES=lines 1199-1233

```python
    def release_desktop_claim(
        self,
        lease: RuntimeLease,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> None:
        desktop_id = _non_empty_text(desktop_instance_id, field="desktop_instance_id")
        if not isinstance(desktop_process_identity, ProcessIdentity):
            raise RuntimeLeaseError("desktop_process_identity must be ProcessIdentity")
        with self._lock():
            current, _record = self._assert_current_owner(lease)
            claim = self._read_desktop_claim_unlocked()
            if claim is None:
                return
            if not (
                claim["service_instance_id"] == current.service_instance_id
                and claim["lease_generation"] == current.lease_generation
                and claim["desktop_instance_id"] == desktop_id
                and claim["desktop_pid"] == desktop_process_identity.pid
                and claim["desktop_process_start_identity"] == desktop_process_identity.process_start_identity
            ):
                raise LeaseNotOwner("desktop claim is not owned by this Desktop and authority generation")
            try:
                desktop_claim_path(self.domain).unlink()
            except FileNotFoundError:
                pass
            self._emit_authority(
                "DESKTOP_CLAIM_RELEASE",
                service_instance_id=current.service_instance_id,
                lease_generation=current.lease_generation,
                process_id=desktop_process_identity.pid,
                decision="RELEASE",
                status="RELEASED",
                reason="exact desktop claim owner released",
            )

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.fence_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.fence_owner
SOURCE_LINES=lines 1517-1572

```python
    def fence_owner(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
        """Fail-closed an exact owner after bootstrap failure without touching a newer owner."""
        if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
            raise LeaseNotOwner("lease does not belong to this runtime domain")
        with self._lock():
            current = self._read_live_lease()
            record = self._read_generation()
            exact_record = (
                record.last_service_instance_id == lease.service_instance_id
                and record.last_lease_generation == lease.lease_generation
                and record.service_pid == lease.service_pid
                and record.process_start_identity == lease.process_start_identity
            )
            if not exact_record:
                raise LeaseNotOwner("refusing to fence a newer or foreign authority generation")
            if current is not None and (
                not self._same_owner(current, lease)
                or current.service_pid != lease.service_pid
                or current.process_start_identity != lease.process_start_identity
            ):
                raise LeaseNotOwner("refusing to fence a newer or foreign live owner")
            if record.status in {"released", "fenced"}:
                self._remove_desktop_claim_if_owner(lease)
                if current is not None:
                    self._remove_live_lease()
                self._emit_authority(
                    "RUNTIME_LEASE_FENCE",
                    service_instance_id=lease.service_instance_id,
                    lease_generation=lease.lease_generation,
                    decision="FENCE_ALREADY_RESOLVED",
                    status=record.status.upper(),
                    reason="authority generation was already resolved",
                )
                return record
            if record.status not in {"reserved", "active"}:
                raise LeaseNotOwner("authority generation is not fenceable")
            fenced = replace(
                record,
                status="fenced",
                fenced_service_instance_id=lease.service_instance_id,
                fenced_lease_generation=lease.lease_generation,
                updated_at=self._now(),
            )
            self._write_generation(fenced)
            self._remove_desktop_claim_if_owner(lease)
            if current is not None:
                self._remove_live_lease()
            self._emit_authority(
                "RUNTIME_LEASE_FENCE",
                service_instance_id=lease.service_instance_id,
                lease_generation=lease.lease_generation,
                decision="FENCE_OWNER",
                status="FENCED",
                reason="bootstrap failure fenced exact owner",
            )
            return fenced

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager._assert_current_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager._assert_current_owner
SOURCE_LINES=lines 1443-1459

```python
    def _assert_current_owner(self, lease: RuntimeLease) -> tuple[RuntimeLease, AuthorityGenerationRecord]:
        if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
            raise LeaseNotOwner("lease does not belong to this runtime domain")
        current = self._read_live_lease()
        record = self._read_generation()
        if current is None or not self._same_owner(current, lease):
            raise LeaseNotOwner("service instance/generation is not the current live owner")
        if (
            record.status != "active"
            or record.last_lease_generation != lease.lease_generation
            or record.last_service_instance_id != lease.service_instance_id
            or record.service_pid != current.service_pid
            or record.process_start_identity != current.process_start_identity
            or record.endpoint_fingerprint != current.endpoint_fingerprint
        ):
            raise LeaseNotOwner("service instance/generation has been durably fenced")
        return current, record

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager.read_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager.read_desktop_claim
SOURCE_LINES=lines 1029-1040

```python
    def read_desktop_claim(self, lease: RuntimeLease | None = None) -> dict[str, Any] | None:
        """Read the authority-owned Desktop admission claim, if current and valid."""
        with self._lock():
            claim = self._read_desktop_claim_unlocked()
            if claim is not None and lease is not None and not (
                claim["service_instance_id"] == lease.service_instance_id
                and claim["lease_generation"] == lease.lease_generation
                and claim["service_pid"] == lease.service_pid
                and claim["process_start_identity"] == lease.process_start_identity
            ):
                return None
            return claim

```

### contextor.core.live_state.runtime_lease::RuntimeLeaseManager._fence_stale_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::RuntimeLeaseManager._fence_stale_lease
SOURCE_LINES=lines 1279-1305

```python
    def _fence_stale_lease(
        self,
        record: AuthorityGenerationRecord,
        lease: RuntimeLease,
    ) -> AuthorityGenerationRecord:
        if record.last_lease_generation != lease.lease_generation or record.last_service_instance_id != lease.service_instance_id:
            raise ForeignLeaseError("stale lease does not match durable generation record")
        fenced = replace(
            record,
            status="fenced",
            fenced_service_instance_id=lease.service_instance_id,
            fenced_lease_generation=lease.lease_generation,
            updated_at=self._now(),
        )
        self._write_generation(fenced)
        self._inject("after_fence_persist")
        self._remove_desktop_claim_if_owner(lease)
        self._remove_live_lease()
        self._emit_authority(
            "RUNTIME_LEASE_FENCE",
            service_instance_id=lease.service_instance_id,
            lease_generation=lease.lease_generation,
            decision="FENCE_STALE",
            status="FENCED",
            reason="confirmed_stale_authority",
        )
        return fenced

```

### contextor.core.live_state.runtime_lease::_DomainFileLock

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::_DomainFileLock
SOURCE_LINES=lines 757-834

```python
class _DomainFileLock(AbstractContextManager["_DomainFileLock"]):
    """OS-backed domain lock with an in-process guard for same-process threads."""

    def __init__(self, path: Path, *, timeout: float) -> None:
        self.path = path
        self.timeout = timeout
        self._thread_lock = _thread_lock_for(path)
        self._file: Any = None

    def __enter__(self) -> "_DomainFileLock":
        if not self._thread_lock.acquire(timeout=self.timeout):
            raise LeaseBusyError("timed out waiting for domain lock")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            open_deadline = time.monotonic() + self.timeout
            while True:
                try:
                    self._file = self.path.open("a+b")
                    break
                except PermissionError as exc:
                    if time.monotonic() >= open_deadline:
                        raise LeaseBusyError("timed out opening cross-process domain lock") from exc
                    time.sleep(0.01)
            if self.path.stat().st_size == 0:
                self._file.seek(0)
                self._file.write(b"0")
                self._file.flush()
            self._file.seek(0)
            self._acquire_os_lock()
            return self
        except Exception:
            self._close()
            self._thread_lock.release()
            raise

    def _acquire_os_lock(self) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (OSError, BlockingIOError) as exc:
                if time.monotonic() >= deadline:
                    raise LeaseBusyError("timed out waiting for cross-process domain lock") from exc
                time.sleep(0.01)

    def _close(self) -> None:
        if self._file is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._file.close()
            finally:
                self._file = None

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self._close()
        finally:
            self._thread_lock.release()

```

### contextor.core.live_state.runtime_lease::domain_lock_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=contextor.core.live_state.runtime_lease::domain_lock_path
SOURCE_LINES=lines 705-706

```python
def domain_lock_path(domain: RuntimeDomain) -> Path:
    return domain.lock_root / f"authority.{domain.domain_id}.lock"

```

### connect_or_start

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=connect_or_start
SOURCE_LINES=lines 859-1036

```python
def connect_or_start(
    repo_path: str | Path,
    *,
    owner_pid: int | None = None,
    owner_token: str | None = None,
    desktop_instance_id: str | None = None,
    desktop_process_start_identity: str | None = None,
    client_kind: str = "protocol",
    timeout: float = DEFAULT_CONNECT_TIMEOUT,
    cold_start_timeout: float = DEFAULT_COLD_START_TIMEOUT,
) -> LiveStateClient:
    root = Path(repo_path).expanduser().resolve()
    identity = require_repository_identity(root)
    if client_kind == "desktop" and not isinstance(desktop_instance_id, str):
        raise ValueError("desktop_instance_id is required for Desktop admission")
    desktop_process_identity = None
    if client_kind == "desktop":
        desktop_pid = owner_pid if owner_pid is not None else os.getpid()
        if owner_pid is None:
            owner_pid = desktop_pid
        if desktop_process_start_identity is None:
            desktop_process_identity = ProcessIdentity.current(desktop_pid)
        else:
            desktop_process_identity = ProcessIdentity(desktop_pid, desktop_process_start_identity)
    domain = _production_domain(identity)
    manager = RuntimeLeaseManager(
        domain,
        liveness_verifier=AuthorityLivenessVerifier(domain),
    )
    try:
        endpoint = _read_endpoint(root, strict=True)
    except EndpointSchemaError as exc:
        if endpoint_file(root).exists() and not isinstance(exc.__cause__, PermissionError):
            raise
        endpoint = None
    if endpoint is not None and not _endpoint_matches_domain(endpoint, domain):
        raise EndpointSchemaError("LIVE endpoint belongs to another repository or runtime domain")

    existing = _verified_existing_client(
        root,
        identity,
        domain,
        manager,
        desktop_instance_id=desktop_instance_id,
        owner_token=owner_token,
    )
    if existing is not None:
        if client_kind == "desktop":
            return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
        return existing

    record = manager.read_generation()
    live = manager.read_live_lease()
    if live is None and record.status == "active":
        raise LeaseRecoveryRequired(
            "active durable authority has no live lease; recovery is required before startup"
        )

    target = endpoint_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    start_lock = target.with_name("live_service_start.lock")
    effective_startup_budget = max(timeout, cold_start_timeout)
    deadline = time.monotonic() + effective_startup_budget
    lock_fd = None
    while time.monotonic() < deadline:
        existing = _verified_existing_client(
            root,
            identity,
            domain,
            manager,
            desktop_instance_id=desktop_instance_id,
            owner_token=owner_token,
        )
        if existing is not None:
            if client_kind == "desktop":
                return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
            return existing
        try:
            lock_fd = os.open(start_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - start_lock.stat().st_mtime > effective_startup_budget:
                    start_lock.unlink()
            except FileNotFoundError:
                pass
            time.sleep(0.05)
    if lock_fd is None:
        raise TimeoutError(f"Could not claim Canonical LIVE startup lock for {root}")

    proc = None
    try:
        existing = _verified_existing_client(
            root,
            identity,
            domain,
            manager,
            desktop_instance_id=desktop_instance_id,
            owner_token=owner_token,
        )
        if existing is not None:
            if client_kind == "desktop":
                return _admit_desktop(existing, str(desktop_instance_id), desktop_process_identity)
            return existing

        cmd = [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(root)]
        if owner_pid is not None:
            cmd.extend(["--owner-pid", str(owner_pid)])
        if owner_token is not None:
            cmd.extend(["--owner-token", str(owner_token)])
        if desktop_instance_id is not None:
            cmd.extend(["--desktop-instance-id", str(desktop_instance_id)])
        if client_kind == "desktop" and desktop_process_identity is not None:
            cmd.extend(["--desktop-process-start-identity", desktop_process_identity.process_start_identity])

        from contextor.core.paths import package_root

        env = dict(os.environ)
        pkg_root = str(package_root())
        if "PYTHONPATH" in env and env["PYTHONPATH"]:
            if pkg_root not in env["PYTHONPATH"].split(os.pathsep):
                env["PYTHONPATH"] = f"{pkg_root}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = pkg_root

        from contextor.core.runtime_trace import AuthorityEventEmitter

        AuthorityEventEmitter(
            runtime_domain_id=domain.domain_id,
            repo_id=identity.repo_id,
            logs_root=domain.logs_root,
        ).emit(
            "RUNTIME_AUTHORITY_START",
            source="runtime_startup_coordinator",
            status="STARTING",
            decision="START",
            reason="authority service process spawn admitted",
        )
        cmd.append("--authority-start-recorded")
        proc = _spawn_runtime_subprocess(cmd, root, env)
        spawn_deadline = time.monotonic() + effective_startup_budget
        while time.monotonic() < spawn_deadline:
            client = _verified_existing_client(
                root,
                identity,
                domain,
                manager,
                desktop_instance_id=desktop_instance_id,
                owner_token=owner_token,
            )
            if client is not None:
                if client_kind == "desktop":
                    try:
                        return _admit_desktop(client, str(desktop_instance_id), desktop_process_identity)
                    except SecondDesktopActive:
                        if proc is not None and _is_pid_alive(proc.pid):
                            _terminate_pid_tree(proc.pid)
                        raise
                return client
            if proc.poll() is not None:
                raise RuntimeError(
                    f"Canonical LIVE service process exited prematurely with code {proc.returncode} for {root}"
                )
            time.sleep(0.05)
        if proc is not None and _is_pid_alive(proc.pid):
            _terminate_pid_tree(proc.pid)
        raise TimeoutError(
            f"Canonical LIVE service startup and authority bootstrap timed out after {effective_startup_budget}s for {root}"
        )
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            start_lock.unlink()
        except FileNotFoundError:
            pass

```

### _admit_desktop

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=_admit_desktop
SOURCE_LINES=lines 632-661

```python
def _admit_desktop(
    client: LiveStateClient,
    desktop_instance_id: str,
    desktop_process_identity: ProcessIdentity,
) -> LiveStateClient:
    try:
        claim_status = client.desktop_claim_status()
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        raise RuntimeError(f"Desktop admission authority is unavailable: {exc}") from exc
    if claim_status.get("status") != "ok":
        raise RuntimeError(
            str(claim_status.get("error") or "Desktop admission claim status was unavailable")
        )
    try:
        _validated_desktop_claim(claim_status, client.endpoint)
    except (EndpointSchemaError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Desktop admission claim status is invalid: {exc}") from exc
    try:
        response = client.claim_desktop(desktop_instance_id, desktop_process_identity)
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        raise RuntimeError(f"Desktop admission authority is unavailable: {exc}") from exc
    if response.get("status") == "ok" and response.get("claimed") is True:
        client.is_owner = True
        client.desktop_instance_id = desktop_instance_id
        client.desktop_claim = response.get("desktop_claim")
        client.desktop_process_identity = desktop_process_identity
        return client
    if response.get("error") == "second_desktop_active":
        raise SecondDesktopActive("repository already active in another Contextor Desktop")
    raise RuntimeError(str(response.get("error") or "Desktop admission claim was rejected"))

```

### _validated_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=_validated_desktop_claim
SOURCE_LINES=lines 342-378

```python
def _validated_desktop_claim(status: Mapping[str, Any], endpoint: LiveEndpoint) -> dict[str, Any] | None:
    claim = status.get("desktop_claim")
    if claim is None:
        return None
    if not isinstance(claim, Mapping):
        raise EndpointSchemaError("desktop_claim_status desktop_claim is malformed")
    required = {
        "runtime_domain_id",
        "service_instance_id",
        "lease_generation",
        "desktop_instance_id",
        "desktop_pid",
        "desktop_process_start_identity",
    }
    if not required.issubset(set(claim)):
        raise EndpointSchemaError("desktop_claim_status desktop_claim fields are malformed")
    if (
        claim["runtime_domain_id"] != endpoint.runtime_domain_id
        or claim["service_instance_id"] != endpoint.service_instance_id
        or int(claim["lease_generation"]) != endpoint.lease_generation
        or not isinstance(claim["desktop_instance_id"], str)
        or not claim["desktop_instance_id"].strip()
        or isinstance(claim["desktop_pid"], bool)
        or not isinstance(claim["desktop_pid"], int)
        or claim["desktop_pid"] <= 0
        or not isinstance(claim["desktop_process_start_identity"], str)
        or not claim["desktop_process_start_identity"].strip()
    ):
        raise EndpointSchemaError("desktop_claim_status desktop_claim identity does not match endpoint")
    return {
        "runtime_domain_id": str(claim["runtime_domain_id"]),
        "service_instance_id": str(claim["service_instance_id"]),
        "lease_generation": int(claim["lease_generation"]),
        "desktop_instance_id": claim["desktop_instance_id"].strip(),
        "desktop_pid": int(claim["desktop_pid"]),
        "desktop_process_start_identity": claim["desktop_process_start_identity"].strip(),
    }

```

### AuthorityLivenessVerifier.verify

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=AuthorityLivenessVerifier.verify
SOURCE_LINES=lines 387-515

```python
    def verify(self, lease: RuntimeLease) -> LivenessResult:
        def finish(result: LivenessResult, endpoint: LiveEndpoint | None = None, exc: BaseException | None = None) -> LivenessResult:
            fields = {
                "status": result.status.value,
                "process_alive": result.process_alive,
                "process_identity_matches": result.process_identity_matches,
                "endpoint_available": result.endpoint_available,
                "endpoint_matches": result.endpoint_matches,
                "reason": result.reason,
                "service_pid": lease.service_pid,
                "lease_generation": lease.lease_generation,
            }
            fields.update(_trace_endpoint_fields(endpoint))
            fields.update(_trace_exception_fields(exc))
            _safe_trace_event("LIVE", "LIVE_LIVENESS_RESULT", **fields)
            return result
        try:
            _image, creation_time, alive = _process_identity(lease.service_pid)
        except Exception as exc:  # pragma: no cover - platform probe boundary
            return finish(LivenessResult(
                LivenessStatus.UNKNOWN,
                None,
                None,
                None,
                None,
                f"process identity probe failed: {exc}",
            ), exc=exc)
        process_matches = bool(alive and creation_time is not None and str(creation_time) == lease.process_start_identity)
        process_stale = (not alive) or (creation_time is not None and not process_matches)
        try:
            endpoint = _read_endpoint(self.domain.repo_root, strict=True)
        except EndpointSchemaError as exc:
            endpoint = None
            endpoint_reason = str(exc)
        else:
            endpoint_reason = "endpoint metadata unavailable"

        if endpoint is None:
            if process_stale:
                return finish(LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=False,
                    reason=f"process is stale and authority endpoint is unavailable or invalid: {endpoint_reason}",
                    endpoint_evidence_verified=True,
                ), endpoint)
            return finish(LivenessResult(
                LivenessStatus.UNKNOWN,
                bool(alive),
                process_matches,
                False,
                None,
                f"authority endpoint is unavailable: {endpoint_reason}",
            ), endpoint)

        endpoint_matches = _endpoint_matches_domain(endpoint, self.domain) and (
            endpoint.service_instance_id == lease.service_instance_id
            and endpoint.lease_generation == lease.lease_generation
            and endpoint.pid == lease.service_pid
            and endpoint.process_start_identity == lease.process_start_identity
        )
        try:
            status = LiveStateClient(endpoint).authority_status()
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
            try:
                _endpoint_image, endpoint_creation, endpoint_alive = _process_identity(endpoint.pid)
            except Exception:
                endpoint_alive = None
                endpoint_creation = None
            endpoint_is_dead = endpoint_alive is False
            if not endpoint_matches and process_stale and endpoint_is_dead:
                return finish(LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=None,
                    reason=f"stale process and dead mismatched authority endpoint: {exc}",
                    endpoint_evidence_verified=True,
                ), endpoint, exc)
            if endpoint_matches and process_stale and endpoint_is_dead:
                return finish(LivenessResult.stale(
                    process_alive=bool(alive),
                    process_identity_matches=process_matches,
                    endpoint_available=False,
                    endpoint_matches=True,
                    reason=f"stale process and dead authority endpoint: {exc}",
                    endpoint_evidence_verified=True,
                ), endpoint, exc)
            return finish(LivenessResult(
                LivenessStatus.UNKNOWN,
                bool(alive),
                process_matches,
                True,
                endpoint_matches,
                f"authority status unavailable: {exc}",
            ), endpoint, exc)

        status_matches = _status_matches_endpoint(status, endpoint)
        if not endpoint_matches:
            if status_matches:
                return finish(LivenessResult(
                    LivenessStatus.FOREIGN_LIVE,
                    bool(alive),
                    process_matches,
                    True,
                    False,
                    "authenticated LIVE endpoint belongs to another service instance or generation",
                    False,
                ), endpoint)
            return finish(LivenessResult(
                LivenessStatus.AMBIGUOUS,
                bool(alive),
                process_matches,
                True,
                False,
                "mismatched endpoint responded but did not prove a coherent authority identity",
                False,
            ), endpoint)
        if process_matches and status_matches:
            return finish(LivenessResult.live("exact process identity and authority status match"), endpoint)
        return finish(LivenessResult(
            LivenessStatus.UNKNOWN,
            bool(alive),
            process_matches,
            True,
            status_matches,
            "authority status did not prove the exact live owner",
        ), endpoint)

```

### _verified_existing_client

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=_verified_existing_client
SOURCE_LINES=lines 518-613

```python
def _verified_existing_client(
    root: Path,
    identity,
    domain: RuntimeDomain,
    manager: RuntimeLeaseManager,
    *,
    desktop_instance_id: str | None = None,
    owner_token: str | None = None,
) -> LiveStateClient | None:
    started = time.monotonic()

    def reject(reason_code: str, endpoint: LiveEndpoint | None = None, exc: BaseException | None = None, **fields: object) -> None:
        event_fields = {
            "reason_code": reason_code,
            "elapsed_ms": (time.monotonic() - started) * 1000.0,
        }
        event_fields.update(_trace_endpoint_fields(endpoint))
        event_fields.update(fields)
        event_fields.update(_trace_exception_fields(exc))
        _safe_trace_event("LIVE", "LIVE_CONNECT_REJECT", **event_fields)
    try:
        endpoint = _read_endpoint(root, strict=True)
    except EndpointSchemaError as exc:
        if isinstance(exc.__cause__, PermissionError):
            reject("ENDPOINT_SCHEMA_INVALID", exc=exc)
            return None
        reject("ENDPOINT_SCHEMA_INVALID", exc=exc)
        raise
    if endpoint is None:
        reject("ENDPOINT_MISSING")
        return None
    if not _endpoint_matches_domain(endpoint, domain):
        reject("DOMAIN_MISMATCH", endpoint)
        return None
    try:
        live = manager.read_live_lease()
        record = manager.read_generation()
        if (
            live is not None
            and record.status == "active"
            and live.service_instance_id == endpoint.service_instance_id
            and live.lease_generation == endpoint.lease_generation
            and live.service_pid == endpoint.pid
            and live.process_start_identity == endpoint.process_start_identity
            and live.endpoint_fingerprint == endpoint.fingerprint()
            and record.endpoint_fingerprint is None
        ):
            manager.reconcile_endpoint_binding(live, endpoint.fingerprint())
    except Exception as exc:
        reject("LEASE_MISMATCH", endpoint, exc)
        return None
    try:
        image, creation_time, alive = _process_identity(endpoint.pid)
    except Exception as exc:
        reject("PROCESS_IDENTITY_MISMATCH", endpoint, exc)
        return None
    if not alive or creation_time is None or str(creation_time) != endpoint.process_start_identity:
        reject("PROCESS_IDENTITY_MISMATCH", endpoint, pid_alive=bool(alive))
        return None
    try:
        status = LiveStateClient(endpoint).authority_status()
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        reject("AUTHORITY_STATUS_TRANSPORT_ERROR", endpoint, exc, pid_alive=True)
        return None
    if not _status_matches_endpoint(status, endpoint):
        reject("AUTHORITY_STATUS_MISMATCH", endpoint, pid_alive=True)
        return None
    try:
        lease = manager.read_live_lease()
        record = manager.read_generation()
    except Exception as exc:
        reject("LEASE_MISMATCH", endpoint, exc, pid_alive=True)
        return None
    if lease is None or record.status != "active":
        reject("LEASE_MISMATCH", endpoint, pid_alive=True)
        return None
    if (
        lease.service_instance_id != endpoint.service_instance_id
        or lease.lease_generation != endpoint.lease_generation
        or lease.service_pid != endpoint.pid
        or lease.process_start_identity != endpoint.process_start_identity
        or lease.endpoint_fingerprint != endpoint.fingerprint()
        or record.last_service_instance_id != lease.service_instance_id
        or record.last_lease_generation != lease.lease_generation
        or record.endpoint_fingerprint != endpoint.fingerprint()
    ):
        reject("LEASE_MISMATCH", endpoint, pid_alive=True)
        return None
    client = LiveStateClient(
        endpoint,
        is_owner=False,
        service_pid=endpoint.pid,
        owner_pid=endpoint.owner_pid,
        owner_token=endpoint.owner_token,
    )
    return client

```

### CanonicalLiveServer._dispatch_claim_desktop

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._dispatch_claim_desktop
SOURCE_LINES=lines 975-1068

```python
    def _dispatch_claim_desktop(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if request.get("client_kind") != "desktop":
            return {
                "status": "error",
                "error": "desktop_claim_requires_desktop_client",
            }

        desktop_id = request.get("desktop_instance_id")
        if not isinstance(desktop_id, str) or not desktop_id.strip():
            return {
                "status": "error",
                "error": "desktop_instance_id_required",
            }
        desktop_id = desktop_id.strip()

        desktop_pid = request.get("desktop_pid")
        desktop_start = request.get("desktop_process_start_identity")
        if (
            isinstance(desktop_pid, bool)
            or not isinstance(desktop_pid, int)
            or desktop_pid <= 0
            or not isinstance(desktop_start, str)
            or not desktop_start.strip()
        ):
            return {
                "status": "error",
                "error": "desktop_process_identity_required",
            }
        desktop_start = desktop_start.strip()

        if not self._claim_identity_matches_request(request):
            return {
                "status": "error",
                "error": "desktop_claim_identity_mismatch",
            }

        try:
            if self._desktop_claim_acquirer is not None:
                # External authority callback outside self._lock.
                claim = self._desktop_claim_acquirer(
                    desktop_id,
                    desktop_pid,
                    desktop_start,
                )
            else:
                current = self._current_desktop_claim()
                if (
                    current is not None
                    and current.get("desktop_instance_id") != desktop_id
                ):
                    return {
                        "status": "error",
                        "error": "second_desktop_active",
                        "desktop_claim": current,
                    }
                claim = current or {
                    "runtime_domain_id": self._authority_identity.get(
                        "runtime_domain_id"
                    ),
                    "service_instance_id": self._authority_identity.get(
                        "service_instance_id"
                    ),
                    "lease_generation": self._authority_identity.get(
                        "lease_generation"
                    ),
                    "desktop_instance_id": desktop_id,
                    "desktop_pid": desktop_pid,
                    "desktop_process_start_identity": desktop_start,
                }
        except Exception as exc:
            if exc.__class__.__name__ == "DesktopClaimAlreadyHeld":
                try:
                    current = self._current_desktop_claim()
                except Exception:
                    current = None
                return {
                    "status": "error",
                    "error": "second_desktop_active",
                    "desktop_claim": current,
                }
            return {"status": "error", "error": str(exc)}

        with self._lock:
            self._desktop_claim = dict(claim)
            result_claim = copy.deepcopy(self._desktop_claim)

        return {
            "status": "ok",
            "claimed": True,
            "desktop_claim": result_claim,
        }

```

### CanonicalLiveServer._current_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._current_desktop_claim
SOURCE_LINES=lines 948-963

```python
    def _current_desktop_claim(self) -> dict[str, Any] | None:
        # External claim readers may participate in RuntimeLease/authority
        # callbacks. Never invoke them while holding the server state lock.
        if self._desktop_claim_reader is not None:
            claim = self._desktop_claim_reader()
            normalized = dict(claim) if claim is not None else None
            with self._lock:
                self._desktop_claim = normalized
                return copy.deepcopy(normalized) if normalized is not None else None

        with self._lock:
            return (
                copy.deepcopy(self._desktop_claim)
                if self._desktop_claim is not None
                else None
            )

```

### CanonicalLiveServer._dispatch_release_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._dispatch_release_desktop_claim
SOURCE_LINES=lines 1070-1137

```python
    def _dispatch_release_desktop_claim(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if request.get("client_kind") != "desktop":
            return {
                "status": "error",
                "error": "desktop_claim_requires_desktop_client",
            }

        desktop_id = request.get("desktop_instance_id")
        if not isinstance(desktop_id, str) or not desktop_id.strip():
            return {
                "status": "error",
                "error": "desktop_instance_id_required",
            }
        desktop_id = desktop_id.strip()

        desktop_pid = request.get("desktop_pid")
        desktop_start = request.get("desktop_process_start_identity")
        if (
            isinstance(desktop_pid, bool)
            or not isinstance(desktop_pid, int)
            or desktop_pid <= 0
            or not isinstance(desktop_start, str)
            or not desktop_start.strip()
        ):
            return {
                "status": "error",
                "error": "desktop_process_identity_required",
            }
        desktop_start = desktop_start.strip()

        if not self._claim_identity_matches_request(request):
            return {
                "status": "error",
                "error": "desktop_claim_identity_mismatch",
            }

        try:
            if self._desktop_claim_releaser is not None:
                # External authority callback outside self._lock.
                self._desktop_claim_releaser(
                    desktop_id,
                    desktop_pid,
                    desktop_start,
                )
            else:
                current = self._current_desktop_claim()
                if (
                    current is not None
                    and current.get("desktop_instance_id") != desktop_id
                ):
                    return {
                        "status": "error",
                        "error": "desktop_claim_not_owned",
                    }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

        with self._lock:
            self._desktop_claim = None

        return {
            "status": "ok",
            "released": True,
            "desktop_claim": None,
        }

```

### CanonicalLiveServer._claim_identity_matches_request

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._claim_identity_matches_request
SOURCE_LINES=lines 938-946

```python
    def _claim_identity_matches_request(self, request: Mapping[str, Any]) -> bool:
        for field in (
            "runtime_domain_id",
            "service_instance_id",
            "lease_generation",
        ):
            if request.get(field) != self._authority_identity.get(field):
                return False
        return True

```

### CanonicalLiveServer._dispatch_desktop_claim_status

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._dispatch_desktop_claim_status
SOURCE_LINES=lines 965-973

```python
    def _dispatch_desktop_claim_status(self) -> dict[str, Any]:
        try:
            claim = self._current_desktop_claim()
        except Exception as exc:
            return {
                "status": "error",
                "error": f"desktop_claim_unavailable: {exc}",
            }
        return {"status": "ok", "desktop_claim": claim}

```

### CanonicalLiveServer.serve_forever

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer.serve_forever
SOURCE_LINES=lines 1139-1201

```python
    def serve_forever(self) -> None:
        while not self._stop.is_set():
            accept_started = time.monotonic()
            try:
                connection = self._listener.accept()
            except OSError as exc:
                if self._stop.is_set():
                    break
                _safe_trace_event(
                    "LIVE", "LIVE_IPC_FAILURE", side="server",
                    operation_or_request_type="accept", host=self.endpoint.host,
                    port=self.endpoint.port, exception_class=type(exc).__name__,
                    errno=getattr(exc, "errno", None),
                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                    elapsed_ms=(time.monotonic() - accept_started) * 1000.0,
                )
                raise
            request_type = "recv"
            request_started = time.monotonic()
            try:
                try:
                    request = connection.recv()
                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
                    _safe_trace_event(
                        "LIVE", "LIVE_IPC_FAILURE", side="server",
                        operation_or_request_type="recv", host=self.endpoint.host,
                        port=self.endpoint.port, exception_class=type(exc).__name__,
                        errno=getattr(exc, "errno", None),
                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
                    )
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
                    continue
                if isinstance(request, dict) and isinstance(request.get("operation"), str):
                    request_type = request["operation"]
                try:
                    response = self._dispatch(request)
                except Exception as exc:
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
                    continue
                try:
                    connection.send(response)
                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
                    _safe_trace_event(
                        "LIVE", "LIVE_IPC_FAILURE", side="server",
                        operation_or_request_type=(request_type if request_type != "recv" else "send"),
                        host=self.endpoint.host, port=self.endpoint.port,
                        exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
                    )
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
            finally:
                connection.close()

```

### CanonicalLiveServer.close

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer.close
SOURCE_LINES=lines 1745-1753

```python
    def close(
        self, *, mutation_join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT
    ) -> bool:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        return self._mutation_coordinator.close(join_timeout=mutation_join_timeout)

```

### LiveStateClient.claim_desktop

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=LiveStateClient.claim_desktop
SOURCE_LINES=lines 1828-1842

```python
    def claim_desktop(
        self,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        return self.request(
            "claim_desktop",
            client_kind="desktop",
            desktop_instance_id=desktop_instance_id,
            desktop_pid=desktop_process_identity.pid,
            desktop_process_start_identity=desktop_process_identity.process_start_identity,
            runtime_domain_id=self.endpoint.runtime_domain_id,
            service_instance_id=self.endpoint.service_instance_id,
            lease_generation=self.endpoint.lease_generation,
        )

```

### LiveStateClient.release_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=LiveStateClient.release_desktop_claim
SOURCE_LINES=lines 1844-1858

```python
    def release_desktop_claim(
        self,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        return self.request(
            "release_desktop_claim",
            client_kind="desktop",
            desktop_instance_id=desktop_instance_id,
            desktop_pid=desktop_process_identity.pid,
            desktop_process_start_identity=desktop_process_identity.process_start_identity,
            runtime_domain_id=self.endpoint.runtime_domain_id,
            service_instance_id=self.endpoint.service_instance_id,
            lease_generation=self.endpoint.lease_generation,
        )

```

### CanonicalLiveServer._dispatch

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=CanonicalLiveServer._dispatch
SOURCE_LINES=lines 1516-1743

```python
    def _dispatch(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
            return {"status": "error", "error": "invalid_request"}
        operation = request["operation"]

        # Desktop authority callbacks cross the RuntimeLease/observability
        # boundary and may synchronously emit back into record_authority_event.
        # Dispatch them outside the server state lock.
        if operation == "desktop_claim_status":
            return self._dispatch_desktop_claim_status()
        if operation == "claim_desktop":
            return self._dispatch_claim_desktop(request)
        if operation == "release_desktop_claim":
            return self._dispatch_release_desktop_claim(request)
        if operation == "submit_update_file":
            return self._mutation_coordinator.submit(request)
        if operation == "mutation_status":
            return self._mutation_coordinator.status(request.get("job_id"))
        if operation == "update_file":
            return self._execute_update_file(request)
        if operation == "publish":
            return self._execute_publish(request)

        with self._lock:
            if operation == "canonical_query":
                if self._state is None:
                    return {
                        "status": "error",
                        "error": "live_state_unavailable",
                    }
                if self._canonical_query_handler is None:
                    return {
                        "status": "error",
                        "error": "canonical_query_unavailable",
                    }

                query_kind = request.get("query_kind")
                if (
                    not isinstance(query_kind, str)
                    or not query_kind
                ):
                    return {
                        "status": "error",
                        "error": "invalid_query_kind",
                    }

                payload = request.get("payload", {})
                if not isinstance(payload, Mapping):
                    return {
                        "status": "error",
                        "error": "invalid_query_payload",
                    }

                try:
                    result = self._canonical_query_handler(
                        self._state,
                        query_kind,
                        dict(payload),
                    )
                except Exception as exc:
                    return {
                        "status": "error",
                        "error": "canonical_query_failed",
                        "detail": str(exc)[:500],
                    }

                return {
                    "status": "ok",
                    "revision": self._revision,
                    "result": result,
                }
            if operation == "ping":
                return {
                    "status": "ok",
                    "protocol_version": LIVE_PROTOCOL_VERSION,
                    "revision": self._revision,
                    "available": self._state is not None,
                }
            if operation == "authority_status":
                if not self._authority_identity:
                    return {"status": "error", "error": "authority_identity_unavailable"}
                return {
                    "status": "ok",
                    "protocol_version": LIVE_PROTOCOL_VERSION,
                    "revision": self._revision,
                    "repo_id": self._authority_identity.get("repo_id"),
                    "root_path": self._authority_identity.get("root_path"),
                    "runtime_domain_id": self._authority_identity.get("runtime_domain_id"),
                    "service_instance_id": self._authority_identity.get("service_instance_id"),
                    "lease_generation": self._authority_identity.get("lease_generation"),
                    "service_pid": self._authority_identity.get("service_pid"),
                    "process_start_identity": self._authority_identity.get("process_start_identity"),
                    "endpoint_fingerprint": self.endpoint.fingerprint(),
                }
            if operation == "snapshot":
                return {"status": "ok", "revision": self._revision, "state": self._state}
            if operation in {"status", "record_activity", "mcp_call"}:
                cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
                evt = self._record_event(operation, request, category=cat)
                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
            if operation == "get_events":
                after_revision = request.get("after_revision")
                after_seq = request.get("after_seq")
                category = request.get("category")
                limit = request.get("limit", 20)

                if after_revision is not None and (
                    isinstance(after_revision, bool)
                    or not isinstance(after_revision, int)
                ):
                    return {"status": "error", "error": "invalid_after_revision"}

                if after_seq is not None and (
                    isinstance(after_seq, bool)
                    or not isinstance(after_seq, int)
                ):
                    return {"status": "error", "error": "invalid_after_seq"}

                earliest_retained_seq = self._events[0]["seq"] if self._events else None

                if after_seq is None:
                    activity_continuity = "not_requested"
                    activity_resync_required = False
                elif after_seq == self._activity_seq:
                    activity_continuity = "continuous"
                    activity_resync_required = False
                elif earliest_retained_seq is None:
                    activity_continuity = "gap"
                    activity_resync_required = True
                elif after_seq < earliest_retained_seq - 1:
                    activity_continuity = "gap"
                    activity_resync_required = True
                else:
                    activity_continuity = "continuous"
                    activity_resync_required = False

                canonical_events = [
                    e for e in self._events
                    if e.get("category") == "LIVE_STATE" and e.get("operation") in {"publish", "update_file"}
                ]
                earliest_retained_revision = canonical_events[0]["canonical_revision"] if canonical_events else None
                latest_revision = self._revision
                latest_seq = self._activity_seq

                if after_revision is None:
                    continuity = "not_requested"
                    resync_required = False
                    resync_reason = None
                elif after_revision > latest_revision:
                    continuity = "gap"
                    resync_required = True
                    resync_reason = "revision_discontinuity"
                elif not canonical_events:
                    if after_revision == latest_revision:
                        continuity = "continuous"
                        resync_required = False
                        resync_reason = None
                    else:
                        continuity = "gap"
                        resync_required = True
                        resync_reason = "event_retention_gap"
                else:
                    if earliest_retained_revision is not None and after_revision < earliest_retained_revision - 1:
                        continuity = "gap"
                        resync_required = True
                        resync_reason = "event_retention_gap"
                    else:
                        continuity = "continuous"
                        resync_required = False
                        resync_reason = None

                events = self._events
                if category is not None:
                    events = [e for e in events if e.get("category") == category]
                if after_seq is not None:
                    events = [e for e in events if e.get("seq", 0) > after_seq]
                elif after_revision is not None:
                    events = [
                        e
                        for e in events
                        if (
                            e.get("category") == "LIVE_STATE"
                            and e.get("operation") in {"publish", "update_file"}
                            and isinstance(e.get("canonical_revision"), int)
                            and e["canonical_revision"] > after_revision
                        )
                    ]

                total = len(events)
                selected = events if limit is None else events[:max(0, int(limit))]

                if after_revision is not None and after_seq is None:
                    formatted_selected = []
                    for e in selected:
                        item = {
                            "revision": e["revision"],
                            "operation": e["operation"],
                            "origin": e["origin"],
                            "status": e["status"],
                            "file_path": e.get("file_path"),
                        }
                        for name in ("error", "line_number", "column_number", "blast_radius_state", "affected_modules", "diagnostic_changes", "message"):
                            if e.get(name) is not None:
                                item[name] = copy.deepcopy(e[name])
                        formatted_selected.append(item)
                    selected = formatted_selected

                return {
                    "status": "ok",
                    "activity_epoch": self._activity_epoch,
                    "revision": self._revision,
                    "latest_revision": latest_revision,
                    "latest_seq": latest_seq,
                    "earliest_retained_revision": earliest_retained_revision,
                    "earliest_retained_seq": earliest_retained_seq,
                    "continuity": continuity,
                    "resync_required": resync_required,
                    "resync_reason": resync_reason,
                    "activity_continuity": activity_continuity,
                    "activity_resync_required": activity_resync_required,
                    "events": selected,
                    "total": total,
                    "truncated": len(selected) < total,
                }
            if operation == "shutdown":
                self._stop.set()
                return {"status": "ok", "revision": self._revision}
            return {"status": "error", "error": "unknown_operation"}

```

### main

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=main
SOURCE_LINES=lines 1782-1798

```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--owner-pid", type=int, default=None)
    parser.add_argument("--owner-token", type=str, default=None)
    parser.add_argument("--desktop-instance-id", type=str, default=None)
    parser.add_argument("--desktop-process-start-identity", type=str, default=None)
    parser.add_argument("--authority-start-recorded", action="store_true")
    args = parser.parse_args()
    run_service(
        args.repo,
        owner_pid=args.owner_pid,
        owner_token=args.owner_token,
        desktop_instance_id=args.desktop_instance_id,
        desktop_process_start_identity=args.desktop_process_start_identity,
        authority_start_recorded=args.authority_start_recorded,
    )

```

### RuntimeLeaseManager.__init__

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.__init__
SOURCE_LINES=lines 862-891

```python
    def __init__(
        self,
        domain: RuntimeDomain,
        *,
        process_identity: ProcessIdentity | None = None,
        liveness_verifier: LivenessVerifier | None = None,
        known_production_roots: Iterable[str | Path] | None = None,
        known_test_roots: Iterable[str | Path] | None = None,
        lock_timeout: float = 10.0,
        clock: Callable[[], float] = time.time,
        failure_injector: FailureInjector | None = None,
        authority_event_emitter: Callable[..., object] | None = None,
    ) -> None:
        _validate_domain_input(
            domain,
            known_production_roots=known_production_roots,
            known_test_roots=known_test_roots,
        )
        if lock_timeout <= 0 or not math.isfinite(lock_timeout):
            raise RuntimeLeaseError("lock_timeout must be finite and positive")
        self.domain = domain
        self.process_identity = process_identity or ProcessIdentity.current()
        self.liveness_verifier = liveness_verifier or DefaultLivenessVerifier()
        self.lock_timeout = lock_timeout
        self.clock = clock
        self.failure_injector = failure_injector
        self.authority_event_emitter = authority_event_emitter
        self._lease_lock_depth = 0
        self._deferred_authority_events: list[tuple[str, dict[str, object]]] = []
        self._deferred_authority_lock = threading.Lock()

```

### RuntimeLeaseManager.read_live_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.read_live_lease
SOURCE_LINES=lines 937-939

```python
    def read_live_lease(self) -> RuntimeLease | None:
        with self._lock():
            return self._read_live_lease()

```

### RuntimeLeaseManager.read_generation

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.read_generation
SOURCE_LINES=lines 933-935

```python
    def read_generation(self) -> AuthorityGenerationRecord:
        with self._lock():
            return self._read_generation()

```

### RuntimeLeaseManager.refresh_heartbeat

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.refresh_heartbeat
SOURCE_LINES=lines 1461-1468

```python
    def refresh_heartbeat(self, lease: RuntimeLease, *, now: float | None = None) -> RuntimeLease:
        with self._lock():
            current, _record = self._assert_current_owner(lease)
            refreshed = replace(current, last_heartbeat_at=self._now() if now is None else _timestamp(now, field="now"))
            if refreshed.last_heartbeat_at < refreshed.started_at:
                raise RuntimeLeaseError("heartbeat cannot precede lease start")
            self._write_live_lease(refreshed)
            return refreshed

```

### RuntimeLeaseManager._fence_stale_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._fence_stale_lease
SOURCE_LINES=lines 1279-1305

```python
    def _fence_stale_lease(
        self,
        record: AuthorityGenerationRecord,
        lease: RuntimeLease,
    ) -> AuthorityGenerationRecord:
        if record.last_lease_generation != lease.lease_generation or record.last_service_instance_id != lease.service_instance_id:
            raise ForeignLeaseError("stale lease does not match durable generation record")
        fenced = replace(
            record,
            status="fenced",
            fenced_service_instance_id=lease.service_instance_id,
            fenced_lease_generation=lease.lease_generation,
            updated_at=self._now(),
        )
        self._write_generation(fenced)
        self._inject("after_fence_persist")
        self._remove_desktop_claim_if_owner(lease)
        self._remove_live_lease()
        self._emit_authority(
            "RUNTIME_LEASE_FENCE",
            service_instance_id=lease.service_instance_id,
            lease_generation=lease.lease_generation,
            decision="FENCE_STALE",
            status="FENCED",
            reason="confirmed_stale_authority",
        )
        return fenced

```

### live_lease_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=live_lease_path
SOURCE_LINES=lines 697-698

```python
def live_lease_path(domain: RuntimeDomain) -> Path:
    return domain.cache_root / f"authority_lease.{domain.domain_id}.json"

```

### generation_metadata_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=generation_metadata_path
SOURCE_LINES=lines 693-694

```python
def generation_metadata_path(domain: RuntimeDomain) -> Path:
    return domain.cache_root / f"authority_generation.{domain.domain_id}.json"

```

### desktop_claim_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=desktop_claim_path
SOURCE_LINES=lines 701-702

```python
def desktop_claim_path(domain: RuntimeDomain) -> Path:
    return domain.cache_root / f"desktop_claim.{domain.domain_id}.json"

```

### domain_lock_path

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=domain_lock_path
SOURCE_LINES=lines 705-706

```python
def domain_lock_path(domain: RuntimeDomain) -> Path:
    return domain.lock_root / f"authority.{domain.domain_id}.lock"

```

### RuntimeLeaseManager._write_live_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._write_live_lease
SOURCE_LINES=lines 964-967

```python
    def _write_live_lease(self, lease: RuntimeLease) -> None:
        if not lease.matches_domain(self.domain):
            raise ForeignLeaseError("refusing to write foreign live lease")
        _atomic_write_json(live_lease_path(self.domain), lease.to_dict())

```

### RuntimeLeaseManager._read_live_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._read_live_lease
SOURCE_LINES=lines 950-957

```python
    def _read_live_lease(self) -> RuntimeLease | None:
        payload = _read_json(live_lease_path(self.domain))
        if payload is None:
            return None
        lease = RuntimeLease.from_dict(payload)
        if not lease.matches_domain(self.domain):
            raise ForeignLeaseError("live lease belongs to another domain")
        return lease

```

### RuntimeLeaseManager._write_generation

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._write_generation
SOURCE_LINES=lines 959-962

```python
    def _write_generation(self, record: AuthorityGenerationRecord) -> None:
        if not record.matches_domain(self.domain):
            raise ForeignLeaseError("refusing to write foreign generation metadata")
        _atomic_write_json(generation_metadata_path(self.domain), record.to_dict())

```

### RuntimeLeaseManager._read_generation

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._read_generation
SOURCE_LINES=lines 941-948

```python
    def _read_generation(self) -> AuthorityGenerationRecord:
        payload = _read_json(generation_metadata_path(self.domain))
        if payload is None:
            return AuthorityGenerationRecord.initial(self.domain, now=self._now())
        record = AuthorityGenerationRecord.from_dict(payload)
        if not record.matches_domain(self.domain):
            raise ForeignLeaseError("authority-generation metadata belongs to another domain")
        return record

```

### RuntimeLeaseManager._allocate_next_locked

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._allocate_next_locked
SOURCE_LINES=lines 1323-1361

```python
    def _allocate_next_locked(self, record: AuthorityGenerationRecord) -> RuntimeLease:
        next_generation = record.last_lease_generation + 1
        lease = self._new_lease(next_generation)
        reserved = replace(
            record,
            last_lease_generation=next_generation,
            last_service_instance_id=lease.service_instance_id,
            service_pid=lease.service_pid,
            process_start_identity=lease.process_start_identity,
            endpoint_fingerprint=lease.endpoint_fingerprint,
            status="reserved",
            fenced_service_instance_id=None,
            fenced_lease_generation=None,
            updated_at=self._now(),
        )
        self._write_generation(reserved)
        self._inject("after_generation_reservation")
        self._write_live_lease(lease)
        self._inject("after_live_lease_persist")
        active = replace(reserved, status="active", updated_at=self._now())
        self._write_generation(active)
        self._inject("after_generation_activation")
        self._emit_authority(
            "RUNTIME_LEASE_RESERVATION",
            service_instance_id=lease.service_instance_id,
            lease_generation=lease.lease_generation,
            decision="ALLOCATE",
            status="RESERVED",
            reason="durable_generation_reserved",
        )
        self._emit_authority(
            "RUNTIME_LEASE_ACTIVATION",
            service_instance_id=lease.service_instance_id,
            lease_generation=lease.lease_generation,
            decision="ACTIVATE",
            status="ACTIVE",
            reason="durable_generation_active",
        )
        return lease

```

### RuntimeLeaseManager.claim_desktop

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.claim_desktop
SOURCE_LINES=lines 1042-1197

```python
    def claim_desktop(
        self,
        lease: RuntimeLease,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        desktop_id = _non_empty_text(desktop_instance_id, field="desktop_instance_id")
        if not isinstance(desktop_process_identity, ProcessIdentity):
            raise RuntimeLeaseError("desktop_process_identity must be ProcessIdentity")
        for _attempt in range(3):
            with self._lock():
                current, record = self._assert_current_owner(lease)
                claim = self._read_desktop_claim_unlocked()
                if claim is None:
                    new_claim = {
                        "schema_version": DESKTOP_CLAIM_SCHEMA_VERSION,
                        "repo_id": self.domain.repo_id,
                        "runtime_domain_id": self.domain.domain_id,
                        "service_instance_id": current.service_instance_id,
                        "lease_generation": current.lease_generation,
                        "service_pid": current.service_pid,
                        "process_start_identity": current.process_start_identity,
                        "desktop_instance_id": desktop_id,
                        "desktop_pid": desktop_process_identity.pid,
                        "desktop_process_start_identity": desktop_process_identity.process_start_identity,
                    }
                    _atomic_write_json(desktop_claim_path(self.domain), new_claim)
                    self._emit_authority(
                        "DESKTOP_CLAIM_ACQUIRE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="ACQUIRE",
                        status="ACTIVE",
                        reason="desktop claim created",
                    )
                    return new_claim
                if (
                    claim["service_instance_id"] == current.service_instance_id
                    and claim["lease_generation"] == current.lease_generation
                    and claim["desktop_instance_id"] == desktop_id
                    and claim["desktop_pid"] == desktop_process_identity.pid
                    and claim["desktop_process_start_identity"] == desktop_process_identity.process_start_identity
                ):
                    self._emit_authority(
                        "DESKTOP_CLAIM_ACQUIRE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="IDEMPOTENT",
                        status="ACTIVE",
                        reason="desktop claim already owned by requester",
                    )
                    return claim
                observed_claim = dict(claim)
                observed_authority = (
                    current.service_instance_id,
                    current.lease_generation,
                    current.service_pid,
                    current.process_start_identity,
                    current.endpoint_fingerprint,
                    record.status,
                    record.endpoint_fingerprint,
                )

            try:
                _image, creation_time, alive = _process_identity(observed_claim["desktop_pid"])
            except Exception as exc:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process identity is unknown",
                    error=str(exc),
                )
                raise LeaseLivenessUnknown("desktop claim process identity is unknown") from exc
            if alive and creation_time is not None and str(creation_time) == observed_claim["desktop_process_start_identity"]:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT",
                    status="LIVE",
                    reason="desktop claim process is live",
                )
                raise DesktopClaimAlreadyHeld("repository already active in another Contextor Desktop")
            if alive and creation_time is None:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process start identity is unknown",
                )
                raise LeaseLivenessUnknown("desktop claim process start identity is unknown")
            if alive:
                claim_is_stale = True
            elif alive is False:
                claim_is_stale = True
            else:
                self._emit_authority(
                    "DESKTOP_CLAIM_REJECT",
                    service_instance_id=observed_claim.get("service_instance_id"),
                    lease_generation=observed_claim.get("lease_generation"),
                    process_id=observed_claim.get("desktop_pid"),
                    decision="REJECT_UNKNOWN",
                    status="UNKNOWN",
                    reason="desktop claim process liveness is unknown",
                )
                raise LeaseLivenessUnknown("desktop claim process liveness is unknown")

            with self._lock():
                current, record = self._assert_current_owner(lease)
                reread_claim = self._read_desktop_claim_unlocked()
                reread_authority = (
                    current.service_instance_id,
                    current.lease_generation,
                    current.service_pid,
                    current.process_start_identity,
                    current.endpoint_fingerprint,
                    record.status,
                    record.endpoint_fingerprint,
                )
                if reread_claim != observed_claim or reread_authority != observed_authority:
                    continue
                if claim_is_stale:
                    replacement = dict(observed_claim)
                    replacement.update(
                        desktop_instance_id=desktop_id,
                        desktop_pid=desktop_process_identity.pid,
                        desktop_process_start_identity=desktop_process_identity.process_start_identity,
                    )
                    _atomic_write_json(desktop_claim_path(self.domain), replacement)
                    self._emit_authority(
                        "DESKTOP_CLAIM_REPLACE",
                        service_instance_id=current.service_instance_id,
                        lease_generation=current.lease_generation,
                        process_id=desktop_process_identity.pid,
                        decision="REPLACE_STALE",
                        status="ACTIVE",
                        reason="previous desktop claim is stale or PID identity mismatched",
                    )
                    return replacement
        self._emit_authority(
            "DESKTOP_CLAIM_REJECT",
            decision="REJECT_RACE",
            status="UNKNOWN",
            reason="desktop claim changed during liveness verification",
        )
        raise LeaseLivenessUnknown("desktop claim changed during liveness verification")

```

### RuntimeLeaseManager.release_desktop_claim

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.release_desktop_claim
SOURCE_LINES=lines 1199-1233

```python
    def release_desktop_claim(
        self,
        lease: RuntimeLease,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> None:
        desktop_id = _non_empty_text(desktop_instance_id, field="desktop_instance_id")
        if not isinstance(desktop_process_identity, ProcessIdentity):
            raise RuntimeLeaseError("desktop_process_identity must be ProcessIdentity")
        with self._lock():
            current, _record = self._assert_current_owner(lease)
            claim = self._read_desktop_claim_unlocked()
            if claim is None:
                return
            if not (
                claim["service_instance_id"] == current.service_instance_id
                and claim["lease_generation"] == current.lease_generation
                and claim["desktop_instance_id"] == desktop_id
                and claim["desktop_pid"] == desktop_process_identity.pid
                and claim["desktop_process_start_identity"] == desktop_process_identity.process_start_identity
            ):
                raise LeaseNotOwner("desktop claim is not owned by this Desktop and authority generation")
            try:
                desktop_claim_path(self.domain).unlink()
            except FileNotFoundError:
                pass
            self._emit_authority(
                "DESKTOP_CLAIM_RELEASE",
                service_instance_id=current.service_instance_id,
                lease_generation=current.lease_generation,
                process_id=desktop_process_identity.pid,
                decision="RELEASE",
                status="RELEASED",
                reason="exact desktop claim owner released",
            )

```

### RuntimeLeaseManager._new_lease

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._new_lease
SOURCE_LINES=lines 1250-1269

```python
    def _new_lease(self, generation: int) -> RuntimeLease:
        now = self._now()
        fingerprints = _domain_resource_fingerprints(self.domain)
        return RuntimeLease(
            schema_version=RUNTIME_LEASE_SCHEMA_VERSION,
            repo_id=self.domain.repo_id,
            runtime_domain_id=self.domain.domain_id,
            mode=self.domain.mode,
            repo_root=_canonical_path_text(self.domain.repo_root, field="repo_root"),
            repo_root_fingerprint=dict(fingerprints)["repo_root"],
            service_instance_id=uuid.uuid4().hex,
            lease_generation=generation,
            service_pid=self.process_identity.pid,
            process_start_identity=self.process_identity.process_start_identity,
            endpoint_fingerprint=None,
            started_at=now,
            last_heartbeat_at=now,
            owner_token=uuid.uuid4().hex,
            resource_root_fingerprints=fingerprints,
        )

```

### RuntimeLeaseManager.release

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.release
SOURCE_LINES=lines 1574-1596

```python
    def release(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
        with self._lock():
            current, record = self._assert_current_owner(lease)
            fenced = replace(
                record,
                status="released",
                fenced_service_instance_id=current.service_instance_id,
                fenced_lease_generation=current.lease_generation,
                updated_at=self._now(),
            )
            self._write_generation(fenced)
            self._remove_desktop_claim_if_owner(lease)
            self._inject("before_release_live_remove")
            self._remove_live_lease()
            self._emit_authority(
                "RUNTIME_LEASE_RELEASE",
                service_instance_id=current.service_instance_id,
                lease_generation=current.lease_generation,
                decision="RELEASE",
                status="RELEASED",
                reason="clean authority shutdown",
            )
            return fenced

```

### RuntimeLeaseManager.fence_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager.fence_owner
SOURCE_LINES=lines 1517-1572

```python
    def fence_owner(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
        """Fail-closed an exact owner after bootstrap failure without touching a newer owner."""
        if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
            raise LeaseNotOwner("lease does not belong to this runtime domain")
        with self._lock():
            current = self._read_live_lease()
            record = self._read_generation()
            exact_record = (
                record.last_service_instance_id == lease.service_instance_id
                and record.last_lease_generation == lease.lease_generation
                and record.service_pid == lease.service_pid
                and record.process_start_identity == lease.process_start_identity
            )
            if not exact_record:
                raise LeaseNotOwner("refusing to fence a newer or foreign authority generation")
            if current is not None and (
                not self._same_owner(current, lease)
                or current.service_pid != lease.service_pid
                or current.process_start_identity != lease.process_start_identity
            ):
                raise LeaseNotOwner("refusing to fence a newer or foreign live owner")
            if record.status in {"released", "fenced"}:
                self._remove_desktop_claim_if_owner(lease)
                if current is not None:
                    self._remove_live_lease()
                self._emit_authority(
                    "RUNTIME_LEASE_FENCE",
                    service_instance_id=lease.service_instance_id,
                    lease_generation=lease.lease_generation,
                    decision="FENCE_ALREADY_RESOLVED",
                    status=record.status.upper(),
                    reason="authority generation was already resolved",
                )
                return record
            if record.status not in {"reserved", "active"}:
                raise LeaseNotOwner("authority generation is not fenceable")
            fenced = replace(
                record,
                status="fenced",
                fenced_service_instance_id=lease.service_instance_id,
                fenced_lease_generation=lease.lease_generation,
                updated_at=self._now(),
            )
            self._write_generation(fenced)
            self._remove_desktop_claim_if_owner(lease)
            if current is not None:
                self._remove_live_lease()
            self._emit_authority(
                "RUNTIME_LEASE_FENCE",
                service_instance_id=lease.service_instance_id,
                lease_generation=lease.lease_generation,
                decision="FENCE_OWNER",
                status="FENCED",
                reason="bootstrap failure fenced exact owner",
            )
            return fenced

```

### RuntimeLeaseManager._assert_current_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._assert_current_owner
SOURCE_LINES=lines 1443-1459

```python
    def _assert_current_owner(self, lease: RuntimeLease) -> tuple[RuntimeLease, AuthorityGenerationRecord]:
        if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
            raise LeaseNotOwner("lease does not belong to this runtime domain")
        current = self._read_live_lease()
        record = self._read_generation()
        if current is None or not self._same_owner(current, lease):
            raise LeaseNotOwner("service instance/generation is not the current live owner")
        if (
            record.status != "active"
            or record.last_lease_generation != lease.lease_generation
            or record.last_service_instance_id != lease.service_instance_id
            or record.service_pid != current.service_pid
            or record.process_start_identity != current.process_start_identity
            or record.endpoint_fingerprint != current.endpoint_fingerprint
        ):
            raise LeaseNotOwner("service instance/generation has been durably fenced")
        return current, record

```

### RuntimeLeaseManager._same_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._same_owner
SOURCE_LINES=lines 1271-1277

```python
    @staticmethod
    def _same_owner(left: RuntimeLease, right: RuntimeLease) -> bool:
        return (
            left.runtime_domain_id == right.runtime_domain_id
            and left.service_instance_id == right.service_instance_id
            and left.lease_generation == right.lease_generation
        )

```

### RuntimeLeaseManager._remove_desktop_claim_if_owner

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py
SYMBOL=RuntimeLeaseManager._remove_desktop_claim_if_owner
SOURCE_LINES=lines 1235-1248

```python
    def _remove_desktop_claim_if_owner(self, lease: RuntimeLease) -> None:
        try:
            payload = _read_json(desktop_claim_path(self.domain))
        except RuntimeLeaseError:
            return
        if isinstance(payload, Mapping) and (
            payload.get("runtime_domain_id") == self.domain.domain_id
            and payload.get("service_instance_id") == lease.service_instance_id
            and payload.get("lease_generation") == lease.lease_generation
        ):
            try:
                desktop_claim_path(self.domain).unlink()
            except FileNotFoundError:
                pass

```

### LiveEndpoint

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
SYMBOL=LiveEndpoint
SOURCE_LINES=lines 26-88

```python
@dataclass(frozen=True)
class LiveEndpoint:
    host: str
    port: int
    authkey_hex: str
    pid: int | None = None
    service_pid: int | None = None
    owner_pid: int | None = None
    owner_token: str | None = None
    repo_id: str | None = None
    root_path: str | None = None
    runtime_domain_id: str | None = None
    service_instance_id: str | None = None
    lease_generation: int | None = None
    process_start_identity: str | None = None
    desktop_instance_id: str | None = None
    schema_version: int = LIVE_ENDPOINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.service_pid is None:
            object.__setattr__(self, "service_pid", self.pid)
        elif self.pid is None:
            object.__setattr__(self, "pid", self.service_pid)
        elif self.pid != self.service_pid:
            raise ValueError("LIVE endpoint pid and service_pid disagree")

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    @property
    def authkey(self) -> bytes:
        return bytes.fromhex(self.authkey_hex)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "host": self.host,
            "port": self.port,
            "authkey_hex": self.authkey_hex,
            "pid": self.pid,
            "service_pid": self.service_pid,
            "repo_id": self.repo_id,
            "root_path": self.root_path,
            "runtime_domain_id": self.runtime_domain_id,
            "service_instance_id": self.service_instance_id,
            "lease_generation": self.lease_generation,
            "process_start_identity": self.process_start_identity,
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.identity_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "owner_pid": self.owner_pid,
            "owner_token": self.owner_token,
            "desktop_instance_id": self.desktop_instance_id,
        }

```

### RuntimeDomain

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_domain.py
SYMBOL=RuntimeDomain
SOURCE_LINES=lines 253-485

```python
@dataclass(frozen=True, slots=True)
class RuntimeDomain:
    """Immutable, serializable namespace for one Contextor runtime domain."""

    domain_id: str
    mode: RuntimeMode
    repo_id: str
    repo_root: Path
    cache_root: Path
    logs_root: Path
    lock_root: Path
    ipc_endpoint_root: Path
    test_context_root: Path | None = None
    service_instance_id: str | None = None
    test_run_id: str | None = None

    def __post_init__(self) -> None:
        canonical = {
            "repo_root": _canonical_path(self.repo_root, field="repo_root"),
            "cache_root": _canonical_path(self.cache_root, field="cache_root"),
            "logs_root": _canonical_path(self.logs_root, field="logs_root"),
            "lock_root": _canonical_path(self.lock_root, field="lock_root"),
            "ipc_endpoint_root": _canonical_path(
                self.ipc_endpoint_root,
                field="ipc_endpoint_root",
            ),
            "test_context_root": _canonical_optional_path(
                self.test_context_root,
                field="test_context_root",
            ),
        }
        for name, value in canonical.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "repo_id", str(self.repo_id).strip())
        if self.service_instance_id is not None:
            object.__setattr__(self, "service_instance_id", str(self.service_instance_id).strip())
        if self.test_run_id is not None:
            object.__setattr__(self, "test_run_id", str(self.test_run_id).strip())
        _validate_structural_fields(self)

    @classmethod
    def create(
        cls,
        *,
        repo_id: str,
        repo_root: str | Path,
        mode: RuntimeMode,
        cache_root: str | Path | None = None,
        logs_root: str | Path | None = None,
        lock_root: str | Path | None = None,
        ipc_endpoint_root: str | Path | None = None,
        service_instance_id: str | None = None,
        test_run_id: str | None = None,
        test_context_root: str | Path | None = None,
        known_production_roots: Iterable[str | Path] | None = None,
        known_test_roots: Iterable[str | Path] | None = None,
    ) -> "RuntimeDomain":
        """Construct and validate without creating or opening any resource."""

        if mode not in ("production", "test"):
            raise RuntimeDomainError("mode must be 'production' or 'test'")
        canonical_repo_root = _canonical_path(repo_root, field="repo_root")
        if not str(repo_id).strip():
            raise RuntimeDomainError("repo_id must not be empty")
        context = _canonical_optional_path(test_context_root, field="test_context_root")
        production_roots = _path_list(
            known_production_roots,
            field="known_production_root",
        )
        test_roots = _path_list(known_test_roots, field="known_test_root")

        if mode == "production":
            # These defaults are the existing Contextor path authority.  They
            # only resolve/read identity metadata; they do not create files.
            cache = _canonical_path(
                cache_root if cache_root is not None else repo_cache_dir(canonical_repo_root),
                field="cache_root",
            )
            logs = _canonical_path(
                logs_root if logs_root is not None else runtime_logs_dir(),
                field="logs_root",
            )
        else:
            if cache_root is None or logs_root is None:
                raise RuntimeDomainError(
                    "test mode requires explicit cache_root and logs_root"
                )
            cache = _canonical_path(cache_root, field="cache_root")
            logs = _canonical_path(logs_root, field="logs_root")

        lock = _canonical_path(
            lock_root if lock_root is not None else cache / "runtime",
            field="lock_root",
        )
        endpoint = _canonical_path(
            ipc_endpoint_root if ipc_endpoint_root is not None else cache,
            field="ipc_endpoint_root",
        )
        roots = {
            "cache_root": cache,
            "logs_root": logs,
            "lock_root": lock,
            "ipc_endpoint_root": endpoint,
        }
        _validate_root_relationships(repo_root=canonical_repo_root, roots=roots)
        _validate_resource_context(
            mode=mode,
            roots=roots,
            test_context_root=context,
            known_production_roots=production_roots,
            known_test_roots=test_roots,
        )

        payload = _domain_payload(
            mode=mode,
            repo_id=str(repo_id).strip(),
            repo_root=canonical_repo_root,
            cache_root=cache,
            logs_root=logs,
            lock_root=lock,
            ipc_endpoint_root=endpoint,
            test_context_root=context,
            service_instance_id=(
                None if service_instance_id is None else str(service_instance_id).strip()
            ),
            test_run_id=None if test_run_id is None else str(test_run_id).strip(),
        )
        identity_payload = _identity_payload(
            mode=mode,
            repo_id=str(repo_id).strip(),
            repo_root=canonical_repo_root,
            cache_root=cache,
            logs_root=logs,
            lock_root=lock,
            ipc_endpoint_root=endpoint,
            test_context_root=context,
            test_run_id=None if test_run_id is None else str(test_run_id).strip(),
        )
        return cls(domain_id=_domain_id(identity_payload), **{key: identity_payload[key] for key in (
            "mode",
            "repo_id",
        )}, **{
            "repo_root": canonical_repo_root,
            "cache_root": cache,
            "logs_root": logs,
            "lock_root": lock,
            "ipc_endpoint_root": endpoint,
            "test_context_root": context,
            "service_instance_id": payload["service_instance_id"],
            "test_run_id": payload["test_run_id"],
        })

    @classmethod
    def from_identity(
        cls,
        identity: RepositoryIdentity,
        **kwargs: Any,
    ) -> "RuntimeDomain":
        """Construct from the existing canonical repository identity owner."""

        if not isinstance(identity, RepositoryIdentity):
            raise RuntimeDomainError("identity must be RepositoryIdentity")
        return cls.create(
            repo_id=identity.repo_id,
            repo_root=identity.root_path,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _domain_payload(
            mode=self.mode,
            repo_id=self.repo_id,
            repo_root=self.repo_root,
            cache_root=self.cache_root,
            logs_root=self.logs_root,
            lock_root=self.lock_root,
            ipc_endpoint_root=self.ipc_endpoint_root,
            test_context_root=self.test_context_root,
            service_instance_id=self.service_instance_id,
            test_run_id=self.test_run_id,
        )
        payload["domain_id"] = self.domain_id
        return payload

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RuntimeDomain":
        if not isinstance(payload, Mapping):
            raise RuntimeDomainError("RuntimeDomain payload must be a mapping")
        expected = {
            "schema_version",
            "domain_id",
            "mode",
            "repo_id",
            "repo_root",
            "cache_root",
            "logs_root",
            "lock_root",
            "ipc_endpoint_root",
            "test_context_root",
            "service_instance_id",
            "test_run_id",
        }
        if set(payload) != expected:
            raise RuntimeDomainError("RuntimeDomain payload fields do not match schema")
        if payload["schema_version"] != RUNTIME_DOMAIN_SCHEMA_VERSION:
            raise RuntimeDomainError("unsupported RuntimeDomain schema_version")
        return cls(
            domain_id=str(payload["domain_id"]),
            mode=payload["mode"],
            repo_id=str(payload["repo_id"]),
            repo_root=payload["repo_root"],
            cache_root=payload["cache_root"],
            logs_root=payload["logs_root"],
            lock_root=payload["lock_root"],
            ipc_endpoint_root=payload["ipc_endpoint_root"],
            test_context_root=payload["test_context_root"],
            service_instance_id=payload["service_instance_id"],
            test_run_id=payload["test_run_id"],
        )

    @classmethod
    def deserialize(cls, payload: str | Mapping[str, Any]) -> "RuntimeDomain":
        if isinstance(payload, str):
            try:
                value = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise RuntimeDomainError("invalid RuntimeDomain JSON") from exc
        else:
            value = payload
        return cls.from_dict(value)

```

### endpoint_file

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=endpoint_file
SOURCE_LINES=lines 214-215

```python
def endpoint_file(repo_path: str | Path) -> Path:
    return repo_cache_dir(repo_path) / "live_endpoint.json"

```

### repo_cache_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\paths.py
SYMBOL=repo_cache_dir
SOURCE_LINES=lines 185-198

```python
def repo_cache_dir(root_path: str | Path) -> Path:
    """
    Cache directory dedicated to one analyzed repository identity.

    Registered repositories use their durable ``repo_id``. Before the first
    registration, callers retain the legacy path-derived cache location.
    """

    from contextor.core.repository_identity import read_repository_identity

    identity = read_repository_identity(root_path)
    if identity is not None:
        return app_cache_dir() / "repositories" / identity.repo_id
    return legacy_repo_cache_dir(root_path)

```

### app_cache_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\paths.py
SYMBOL=app_cache_dir
SOURCE_LINES=lines 152-167

```python
def app_cache_dir() -> Path:
    """
    User-level cache root for Contextor.

    Deliberately outside every analyzed repository: Contextor advertises
    read-only analysis and must not create files in inspected projects.

    Override with the CONTEXTOR_CACHE_DIR environment variable.
    """

    return _env_dir("CONTEXTOR_CACHE_DIR") or _platform_dir(
        "LOCALAPPDATA",
        "Contextor/cache",
        "XDG_CACHE_HOME",
        Path(".cache") / "contextor",
    )

```

### legacy_repo_cache_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\paths.py
SYMBOL=legacy_repo_cache_dir
SOURCE_LINES=lines 201-204

```python
def legacy_repo_cache_dir(root_path: str | Path) -> Path:
    """Pre-identity cache location retained only for safe migration."""

    return app_cache_dir() / repo_key(root_path)

```

### runtime_logs_dir

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\paths.py
SYMBOL=runtime_logs_dir
SOURCE_LINES=lines 37-40

```python
def runtime_logs_dir() -> Path:
    """Canonical per-user directory for Contextor runtime diagnostic traces."""

    return state_dir() / "logs"

```



#### Exact Contextor source ranges for LIVE owner-loss watchdog and shutdown finalization

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=run_service signature and Desktop identity parameters (source lines 1295-1302)

```python
def run_service(
    repo_path: str | Path,
    owner_pid: int | None = None,
    owner_token: str | None = None,
    desktop_instance_id: str | None = None,
    desktop_process_start_identity: str | None = None,
    authority_start_recorded: bool = False,
) -> None:
```

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=run_service lease acquisition and Desktop claim (source lines 1378-1393)

```python
        manager = RuntimeLeaseManager(
            domain,
            liveness_verifier=AuthorityLivenessVerifier(domain),
            authority_event_emitter=authority_emitter.emit,
        )
        lease = manager.acquire()
        if desktop_instance_id is not None:
            if owner_pid is None or desktop_process_start_identity is None:
                raise RuntimeLeaseError("Desktop claim process identity is required")
            desktop_claim = manager.claim_desktop(
                lease,
                desktop_instance_id,
                ProcessIdentity(owner_pid, desktop_process_start_identity),
            )
        startup_timing_started = time.monotonic()
        startup_timings_ms: dict[str, float] = {}
```

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=run_service authority identity projection (source lines 1485-1501)

```python
        revision = startup_metadata.revision if startup_metadata else 0
        adapter_holder: dict[str, object] = {}
        authority_identity = {
            "repo_id": identity.repo_id,
            "root_path": _canonical_root(identity.root_path),
            "runtime_domain_id": domain.domain_id,
            "service_instance_id": lease.service_instance_id,
            "lease_generation": lease.lease_generation,
            "service_pid": lease.service_pid,
            "process_start_identity": lease.process_start_identity,
            "owner_pid": owner_pid,
            "owner_token": owner_token,
            "desktop_instance_id": desktop_instance_id,
        }
        step_started = time.monotonic()
        server = CanonicalLiveServer(
            state,
```

SYMBOL=run_service (owner watchdog block, source lines 1649-1684)

```python
        if owner_pid is not None and owner_pid > 0:
            if sys.platform == "win32":
                import ctypes

                SYNCHRONIZE = 0x00100000
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                owner_handle = ctypes.windll.kernel32.OpenProcess(
                    SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    int(owner_pid),
                )
                if not owner_handle:
                    return

                def _owner_watchdog() -> None:
                    try:
                        while not server._stop.wait(0.75):
                            res = ctypes.windll.kernel32.WaitForSingleObject(owner_handle, 0)
                            if res == 0:
                                server.close()
                                break
                    finally:
                        ctypes.windll.kernel32.CloseHandle(owner_handle)
            else:

                def _owner_watchdog() -> None:
                    while not server._stop.wait(0.75):
                        if not _is_pid_alive(owner_pid):
                            server.close()
                            break

            threading.Thread(
                target=_owner_watchdog,
                name=f"contextor-live-watchdog-{owner_pid}",
                daemon=True,
            ).start()
```

ABSOLUTE_PATH=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
SYMBOL=run_service (finalization block, source lines 1703-1779)

```python
    finally:
        if authority_emitter is not None:
            authority_emitter.detach_live_sink()
        mutation_worker_drained = True
        if server is not None:
            mutation_worker_drained = server.close(mutation_join_timeout=30.0)
        if server_thread is not None and server_thread.is_alive():
            server_thread.join(timeout=1.0)
        if lease is not None and mutation_worker_drained:
            if published_endpoint is not None:
                try:
                    manager.reconcile_endpoint_binding(lease, published_endpoint.fingerprint())
                except Exception as exc:
                    if authority_emitter is not None:
                        authority_emitter.emit(
                            "RUNTIME_ENDPOINT_RECONCILE_FAIL",
                            source="runtime",
                            service_instance_id=lease.service_instance_id,
                            lease_generation=lease.lease_generation,
                            status="FAILED",
                            decision="FAIL_CLOSED",
                            reason="endpoint reconciliation failed during shutdown",
                            error=str(exc),
                        )
            try:
                manager.release(lease)
                ownership_resolved = True
            except Exception as exc:
                if authority_emitter is not None:
                    authority_emitter.emit(
                        "RUNTIME_LEASE_RELEASE_FAIL",
                        source="runtime",
                        service_instance_id=lease.service_instance_id,
                        lease_generation=lease.lease_generation,
                        status="FAILED",
                        decision="FENCE_REQUIRED",
                        reason="clean release failed; fencing required",
                        error=str(exc),
                    )
                try:
                    manager.fence_owner(lease)
                    ownership_resolved = True
                except Exception as fence_exc:
                    if authority_emitter is not None:
                        authority_emitter.emit(
                            "RUNTIME_LEASE_FENCE_FAIL",
                            source="runtime",
                            service_instance_id=lease.service_instance_id,
                            lease_generation=lease.lease_generation,
                            status="FAILED",
                            decision="FAIL_CLOSED",
                            reason="authority fence failed",
                            error=str(fence_exc),
                        )
        if authority_emitter is not None and lease is not None:
            try:
                authority_emitter.emit(
                    "RUNTIME_AUTHORITY_SHUTDOWN",
                    source="runtime",
                    service_instance_id=lease.service_instance_id,
                    lease_generation=lease.lease_generation,
                    status="STOPPED" if ownership_resolved else "UNRESOLVED",
                    decision="SHUTDOWN" if ownership_resolved else "FAIL_CLOSED",
                    reason=(
                        "authority service shutdown completed"
                        if ownership_resolved
                        else (
                            "queued mutation worker did not drain; ownership left for fencing"
                            if not mutation_worker_drained
                            else "authority shutdown could not resolve exact ownership"
                        )
                    ),
                )
            except Exception:
                pass
        if published_endpoint is not None and ownership_resolved:
            _remove_endpoint_if_exact(root, published_endpoint)
```

## CURRENT_BACKEND_LIFETIME_MODEL

1. `contextor.__main__.main` routes `backend start/status/stop` to `mcp_backend_cli.main`; the CLI delegates to `start_backend`, `get_backend_status`, or `stop_backend`.
2. `start_backend` holds only `control.lock` for control serialization. It authenticates/reuses a ready instance when possible; otherwise it removes a stale record, spawns a new process, captures its PID/create-time/executable identity and waits for authenticated readiness.
3. New process enters through `contextor.mcp_main.main -> mcp_server.main`; for role `persistent-backend`, server main requires HTTP transport and acquires `PersistentBackendLease`. Lease creates `backend.json` and holds `backend.lock` for process lifetime.
4. Backend run blocks in `mcp.run_http_async`. There is no external host ownership/lease/heartbeat in `PersistentBackendRecord` or in the persistent-role shutdown path.
5. `stop_backend` serializes via `control.lock`, validates PID + creation identity + executable against the record, terminates the exact process registration and waits for exit; server finalization releases lease/record. Stale-record cleanup does not terminate a process if exact process identity does not match.
6. Ready backend reuse is a control-plane property. The one backend lifecycle has no host-specific admission, and bearer auth maps all accepted clients to the same static auth client identity.

## CURRENT_LIVE_OWNER_MODEL

- Desktop process creates `owner_token` and `desktop_instance_id`; GUI supplies its process PID and process-start identity to `connect_or_start`.
- LIVE service lease separately creates a new `service_instance_id`, increments durable `lease_generation`, records service PID/start identity, and creates its own `RuntimeLease.owner_token`. The runtime lease owner tuple is `(runtime_domain_id, service_instance_id, lease_generation)`; the durable generation record progresses through reserved/active/released/fenced.
- LIVE `run_service` places the external owner PID/token/Desktop identity in authority endpoint identity and runs a 0.75-second owner-PID watchdog. Exact source shows Windows process-handle waiting or non-Windows PID liveness polling; on owner loss it calls `server.close()`.
- LIVE shutdown closes server/mutation coordination, joins server thread, calls `RuntimeLeaseManager.release` when drained (otherwise leaves ownership for fencing), falls back to `fence_owner` on release failure, emits final status, and removes endpoint only if ownership is resolved.
- Desktop claim is a separate persisted claim. It carries domain/service/generation and desktop instance/PID/start identity. Current owner releases it on GUI close; a later claimant validates stale process identity before replacement.
- GUI only sends explicit authority shutdown when client is owner, both owner tokens exist and match, and service PID exists. Closing an attached non-owner releases its exact claim but does not shut down the service.
- `refresh_heartbeat` is a public manager helper but no direct consumer/caller was present in Contextor module/call-context projections; complete `run_service` source ranges contain no heartbeat call. Thus no periodic LIVE lease heartbeat loop is evidenced here.

## REUSABLE_OWNER_PRIMITIVES

Istniejące, literalnie obecne prymitywy LIVE (opis inventory, bez propozycji użycia):

- PID wraz z process-start identity do odróżniania PID reuse.
- `ProcessIdentity` oraz `RuntimeLease`; lease ma service instance ID, generation, service PID/start identity, endpoint fingerprint, heartbeat timestamp, owner token i resource fingerprints.
- Monotoniczny `AuthorityGenerationRecord` z last generation/instance, stanem reserved/active/released/fenced i dokładnym fenced owner tuple.
- Domain-scoped OS file lock i atomowe JSON zapisy.
- Dokładne `_assert_current_owner`, compare-by-generation fencing, exact release i fail-closed unknown liveness.
- Osobny Desktop claim i atomowe acquire/release/replacement po sprawdzeniu process-start identity.
- Owner PID watchdog w LIVE `run_service`, oraz dokładny GUI close guard oparty o owner flag + token equality.
- W backendzie: odrębny process instance ID, PID/create-time/executable identity, per-process lifetime file lock, short control lock i stale-record identity check. Nie są to obecnie host-owner lease.

## MISSING_PRIMITIVES

W aktualnym persistent backend lifecycle nie znaleziono:

- EXTERNAL_HOST / host-owner identity w `PersistentBackendRecord`;
- backend owner PID/token/Desktop instance claim;
- backend owner lease/generation, claim/release/revocation;
- backend heartbeat lub okresowego owner-liveness verifiera;
- backend self-termination po utracie EXTERNAL_HOST;
- per-host HTTP client identity poza wspólnym bearer (token maps to `contextor-local`);
- testu kontraktowego potwierdzającego równoczesne sesje różnych hostów.

To są obserwowane braki kontraktu/runtime, nie propozycje implementacji.

## FILES_REQUIRED_FOR_IMPLEMENTATION_DESIGN

Pliki obecnie definiujące odpowiednie ownership/lifecycle i ich bezpośrednie granice:

- `C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_main.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_backend_http_headers.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_backend_autostart.py`
- `C:\Temp\Contextor_Repo\contextor\mcp_backend_cli.py`
- `C:\Temp\Contextor_Repo\contextor\__main__.py`
- `C:\Temp\Contextor_Repo\contextor\core\paths.py`
- `C:\Temp\Contextor_Repo\contextor\ui\gui.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_domain.py`

## TESTS_RELEVANT_TO_OWNER_LEASE

Test symbols found through Contextor catalogs; NONE were executed.

### Backend singleton, reuse, stale record and process termination

- `tests.test_mcp_backend_state::test_same_process_backend_lease_is_singleton`
- `tests.test_mcp_backend_state::test_cross_process_backend_lease_is_singleton_and_helper_is_cleaned_up`
- `tests.test_mcp_backend_state::test_acquire_writes_durable_record_and_release_removes_it`
- `tests.test_mcp_backend_state::test_backend_record_removal_requires_exact_owner`
- `tests.test_mcp_shared_backend_server_mode::test_second_persistent_backend_is_rejected_before_lifecycle_side_effects`
- `tests.test_mcp_shared_backend_server_mode::test_persistent_http_main_uses_shared_registry_without_root_registration`
- `tests.test_mcp_backend_control::test_start_returns_existing_ready_backend_without_spawn`
- `tests.test_mcp_backend_control::test_start_removes_stale_record_before_spawn`
- `tests.test_mcp_backend_control::test_status_live_owner_requires_authenticated_readiness`
- `tests.test_mcp_backend_control::test_status_stale_record_never_probes_http`
- `tests.test_mcp_backend_control::test_stop_stale_record_removes_metadata_without_termination`
- `tests.test_mcp_backend_control::test_stop_without_record_is_idempotent`
- `tests.test_mcp_backend_control::test_failed_start_terminates_only_exact_spawn_identity`
- `tests.test_mcp_backend_control::test_windows_stop_uses_exact_backend_record_for_termination`
- `tests.test_mcp_backend_control::test_windows_stop_refuses_missing_creation_identity`
- `tests.test_mcp_child_process_cleanup::test_windows_registered_process_termination_uses_tree_kill`
- `tests.test_mcp_backend_control::test_control_lock_same_process_is_exclusive`
- `tests.test_mcp_backend_control::test_authenticated_probe_accepts_contextor_identity_and_ping`
- `tests.test_mcp_backend_control::test_authenticated_probe_rejects_wrong_server_identity`
- `tests.test_mcp_backend_secret::test_backend_token_is_stable_and_stored_without_plaintext`
- `tests.test_mcp_backend_secret::test_cross_process_first_create_is_serialized_and_stable`
- `tests.test_mcp_shared_backend_server_mode::test_http_transport_requires_bearer_token`
- `tests.test_mcp_shared_backend_server_mode::test_http_verifier_accepts_only_exact_token`
- `tests.test_mcp_backend_autostart::test_launch_backend_autostart_uses_existing_lifecycle`
- `tests.test_mcp_backend_autostart::test_launch_backend_autostart_failure_is_bounded`
- `tests.test_mcp_backend_cli::test_application_main_routes_backend_start_to_backend_cli`
- `tests.test_mcp_backend_cli::test_backend_cli_start_emits_json_and_returns_zero`
- `tests.test_mcp_backend_cli::test_backend_cli_status_ready_returns_zero`
- `tests.test_mcp_backend_cli::test_backend_cli_stop_returns_zero`
- `tests.test_gui_backend_restart::test_restart_runs_lifecycle_in_progress_task_and_confirms_new_identity`
- `tests.test_gui_backend_restart::test_restart_requires_independently_confirmed_stopped_state`
- `tests.test_gui_backend_restart::test_restart_requires_new_backend_to_be_authenticated_and_ready`
- `tests.test_gui_backend_restart::test_restart_rejects_reused_complete_backend_identity`

### LIVE ownership, identity, stale takeover and shutdown

- `tests.live_state.test_runtime_domain::test_domain_id_is_deterministic_and_normalizes_equivalent_paths`
- `tests.live_state.test_runtime_domain::test_service_instance_id_is_not_part_of_stable_domain_id`
- `tests.live_state.test_runtime_lease::test_process_identity_requires_start_token_and_is_not_pid_only`
- `tests.live_state.test_runtime_lease::test_pid_reuse_with_same_pid_but_different_start_identity_is_stale`
- `tests.live_state.test_runtime_lease::test_heartbeat_is_owner_validated_but_not_liveness_evidence`
- `tests.live_state.test_runtime_lease::test_confirmed_dead_process_and_unavailable_endpoint_allow_stale_takeover`
- `tests.live_state.test_runtime_lease::test_stale_recovery_increments_generation_and_fences_old_service`
- `tests.live_state.test_runtime_lease::test_old_service_cannot_bind_endpoint_or_release_current_generation`
- `tests.live_state.test_runtime_lease::test_clean_release_preserves_high_water_mark_and_next_acquisition_is_two`
- `tests.test_live_authority_bootstrap::test_desktop_claim_replaces_dead_owner_and_rejects_unknown_probe`
- `tests.test_gui_live_startup::test_second_desktop_is_rejected_before_gui_cache_touch`
- `tests.test_live_desktop_integration::test_closing_gui_shuts_down_owned_live_client`
- `tests.test_live_desktop_integration::test_closing_gui_does_not_shut_down_unowned_live_client`
- `tests.test_live_desktop_integration::test_closing_gui_with_mismatched_owner_token_does_not_shut_down_client`
- `tests.test_live_desktop_integration::test_closing_gui_with_missing_owner_token_does_not_shut_down_client`

Evidence limit: the current catalog search did not identify a dedicated test named for automatic LIVE owner-watchdog shutdown after parent death. The 0.75 s watchdog and cleanup path are directly visible in Contextor source. Do not treat a missing matching test name as proof no such test exists elsewhere.

FILES_CHANGED=NONE
DIFFS=NONE
