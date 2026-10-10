# L32H2D2B_ACYCLIC_COORDINATOR_EXTRACTION

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py (nowy)
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
- Raport: C:\Temp\Contextor_Repo\walkthrough.md

## EXACT_SOURCE_VERIFICATION

DIRECT_EVIDENCE: Contextor `get_source_range(allow_large_output=true)` pobrał cały 700-wierszowy `full_analysis_coordinator.py` w trzech kompletnych zakresach 1–207, 208–409, 410–700. `get_symbol_implementation(mode=fetch)` pobrał kompletne publiczne i prywatne metody facade, revision 242, workspace_sync=verified. Przed ekstrakcją jedynym odniesieniem koordynatora do `ContextorFacade` był lokalny import w `run_full_analysis_exclusive`; acquire/release nie używały facade. Jedyny modułowy właściciel mutable lock state miał `_PROCESS_LOCKS`, `_ADMISSION_LOCKS` i ich guards. Oba publiczne wrappery importowały lease API z koordynatora. Contextor call context i aktualne źródło wskazywały tylko publiczne wrappery jako callerów prywatnych body. Przed edycją worktree source/test był czysty; HEAD `0a2851f9163f4ebb1d27c3c0f36375f4671ce47a`.

## RED_RESULT

Przed produkcyjną edycją 4 nowe przypadki architektoniczne FAIL z `ImportError: cannot import name 'full_analysis_lease'`: brak nowego modułu, brak tożsamości API/locków oraz obustronna próba wykluczenia. Contextor przed zmianą: hard/hard cycle `facade -> full_analysis_coordinator -> facade`, cycles.count=1. Podpisy publiczne i shared lock ownership zanotowano przed edycją.

## EXTRACTION_INVENTORY

Nowy `full_analysis_lease.py` zawiera dokładnie poprzedni niski blok koordynatora, od modułowego docstringu przez `release_full_analysis`; zmieniono wyłącznie ścieżkę w docstringu pliku. Porównanie z `git show HEAD:contextor/core/analysis/full_analysis_coordinator.py` po normalizacji końców linii: `low_level_source_exact_except_module_docstring_path=True`. Są tam `FullAnalysisLease`, `FullAnalysisBusyError`, `ORPHAN_RECOVERY_TIMEOUT_SECONDS`, słowniki/guards blokad, trace field allowlist, metadata i OS lock helpers, process identity, owner validation, admission contextmanager, acquire/release, pełne allowlist writer_kind z `scoped_analysis`. W nowym module występuje po jednej definicji acquire i release; w koordynatorze zero implementacji tych funkcji. Body `run_full_analysis_exclusive` w koordynatorze jest identyczne z HEAD (`runner_source_exact=True`).

## SINGLE_LOCK_OWNER_PROOF

CONTRACT_PROVED: cold-start import i test wykazują `coordinator.acquire_full_analysis is lease.acquire_full_analysis`, analogicznie release, `FullAnalysisLease`, `FullAnalysisBusyError`, `_PROCESS_LOCKS`, `_ADMISSION_LOCKS`; globals implementacji acquire wskazują dokładnie te same słowniki. Dwa niezależne importy `full_analysis_lease` zwracają ten sam moduł. Nie ma drugiego zestawu lock registries. Obustronne próby acquire przez coordinator/lease dla tego samego repo blokują się w procesie. Istniejący Windows OS lock test i międzyprocesowe scoped/full/local testy przechodzą.

## API_AND_EXCEPTION_COMPATIBILITY

Publiczne sygnatury facade po zmianie są identyczne z zapisanymi przed zmianą:

```text
analyze_layer(root_dir: str, layer_dir: str, log=None, progress_callback=None, additional_excludes: list[str] | None = None) -> str
analyze_single_file(file_path: str, repo_root: str, log=None, progress_callback=None, additional_excludes: list[str] | None = None, publication_result: dict[str, typing.Any] | None = None) -> str
```

`FullAnalysisBusyError` i `FullAnalysisLease` zachowują tę samą klasę object identity przez import koordynatora i low-level ownera. Prywatne helpery/stałe używane w testach są jawnie re-eksportowane, bez wildcard, `__getattr__` i proxy.

## COORDINATOR_COMPATIBILITY

Koordynator zawiera jawne bezpośrednie importy low-level API, wszystkich przeniesionych helperów i istniejących stałych. `run_full_analysis_exclusive` zachowuje całe stare body i nadal odwołuje się do swoich modułowych nazw `acquire_full_analysis` / `release_full_analysis`; monkeypatch tego modułu dla high-level runnera nadal działa. `run_full_analysis_exclusive` pozostaje jedyną zależnością koordynatora do facade, gdy domyślnie wywołuje `analyze_project`.

## MONKEYPATCH_MIGRATION

Testy publicznych wrapperów facade w `test_full_analysis_coordination.py` podmieniają teraz `full_analysis_lease.acquire_full_analysis` / `release_full_analysis`, bo wrappery importują te symbole bezpośrednio z ownera. Testy high-level runnera zachowują monkeypatch koordynatora. Testy `ORPHAN_RECOVERY_TIMEOUT_SECONDS` i `_read_lease_metadata` podmieniają teraz właściciela `full_analysis_lease`, ponieważ globals przeniesionych funkcji są tam. Testy MCP/local i LIVE mutation nadal patchują koordynatora, z którego ich odpowiednie calle pobierają symbole. Asercje realnych OS locków nie zostały zastąpione mockami.

## FACADE_WRAPPER_COMPATIBILITY

W obu publicznych wrapperach zmieniono wyłącznie lokalny import z `full_analysis_coordinator` na `full_analysis_lease`. Prywatne body, dekoratory `@staticmethod`, walidacja scope, owner strings, timeout=10.0, reset `publication_result` przed walidacją, registry, raporty i LIVE publish pozostały bez zmian. Contextor po zmianie nadal identyfikuje czterech konsumentów produkcyjnych obu publicznych symboli: CLI, MCP worker, MCP analysis jobs, GUI.

## LIVE_SINGLE_FILE_PUBLICATION

Istniejący test rzeczywistego `CanonicalLiveServer` + `LiveStateClient` przy publicznym single-file wrapperze przeszedł w pierwszej zielonej bramce oraz w 105-testowej bramce. Pubikacja IPC zakończyła się sukcesem przy trzymanym scoped lease; brak synchronicznego reentry/deadlock.

## SAME_PROCESS_EXCLUSION / CROSS_PROCESS_EXCLUSION

Same-process: nowe obustronne testy coordinator↔lease PASS; istniejące non-reentrant i scoped-vs-writer testy PASS. Cross-process: istniejące testy OS file-lock, process-death recovery, scoped-vs-full oraz scoped-vs-local incremental w `test_full_analysis_coordination.py` PASS. Wszystkie writer_kind używają jednej implementacji acquire/release.

## IMPORT_CYCLE_BEFORE_AFTER

Przed: cycles.count=1, hard cycle `facade -> coordinator -> facade`. Po: Contextor module context pokazuje `facade -> full_analysis_lease` hard, `coordinator -> full_analysis_lease` hard, `coordinator -> facade` hard, low-level module bez back-edge do facade/koordynatora. `get_live_events` revision 246 zawiera `RESOLVED` poprzedniej diagnostyki cyklu. Po zmianie cycles.count=0, availability=fresh, brak nowego cyklu. Nie użyto importlib/callback/service locator ani zmiany klasyfikacji grafu.

## NEW_MODULE_LAYER_ISOLATION

Contextor przypisał `full_analysis_lease` do warstwy `runtime`, fan_in=2, fan_out=5, bez hard zależności do facade ani koordynatora. Importy wychodzące obejmują `contextor.core.errors`, `contextor.core.paths`, `contextor.core.repository_identity`, `contextor.core.runtime_trace` i `contextor.mcp_process_registry`; compact view pokazuje pierwsze trzy i total=5. Moduł rozwiązuje się jednoznacznie w canonical state i `get_symbol_implementation`. Nie uruchomiono pełnej analizy ani dedykowanego `analyze_layer`.

## COLD_START_IMPORT_RESULT

Świeży proces `.venv\Scripts\python.exe`: import facade, lease i coordinator PASS; identyczne podpisy publiczne, identity acquire/release/class/error/lock dicts = True. `py_compile` trzech produkcyjnych modułów i testu: PASS.

## TARGETED_TEST_RESULTS

- RED przed produkcją: 4 failed (oczekiwany brak low-level modułu).
- Pierwszy GREEN: 9 passed (architektura, tożsamości, wzajemna blokada, scoped facade, `publication_result`, prawdziwy LIVE publish).
- Główny focused gate: `test_full_analysis_coordination.py`, `test_live_single_file_reuse.py`, `test_mcp_incremental_hydration.py`, `test_profile_runner.py`: 105 passed.
- Dodatkowe focused nodes LIVE mutation, GUI startup/scoped, watcher i public MCP `update_file`: 22 passed.
- Facade progress, layer hydration i repository scope: 12 passed.
- `git diff --check` dla tracked files oraz `git diff --no-index --check` dla nowego modułu: brak błędów whitespace; Git zwrócił jedynie informację o przyszłej konwersji LF/CRLF.

## SOURCE_SYNC_VERIFICATION / LIVE_REVISION_BEFORE_AFTER

Przed: revision 242. Po: revision 248, continuity=continuous, resync_required=false. Desktop watcher obsłużył revisions 243–247 jako UPDATED dla testu, nowego modułu, koordynatora i facade; revision 248 to UNCHANGED po zmianie samego docstringu modułu. `get_module_context` trzech ownerów: workspace_sync=verified przy revision 247, cycles.count=0. `get_symbol_implementation` przeniesionego acquire: complete=true, workspace_sync=verified przy revision 248. Nie wykonano manual update_file, restartu ani full analysis.

## REMAINING_RISKS

Serving MCP/Desktop/LIVE procesy mogą nadal mieć stare importy w pamięci. Contextor workspace sync potwierdza source index, nie reload wykonywanego kodu. Pełny repository suite oraz globalna certyfikacja L32H pozostają poza tą bramką.

## RESTART_REQUIRED

YES dla już uruchomionych procesów importujących facade/koordynator; restartu nie wykonano.

## FINAL_VERDICT

ACYCLIC_EXTRACTION_TARGETED_PASS, ARCHITECTURAL_CYCLE_RESOLVED_IN_CANONICAL_SOURCE. Nie zgłaszam L32H FINAL PASS ani serving-process certification.

## FULL_DIFFS

Poniżej pełne surowe diffy każdego zmienionego pliku source/test. Raport `walkthrough.md` nie jest liczony jako plik source/test.

```diff

diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 292fa9a..76f26d8 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -1,615 +1,43 @@
 """
-contextor/core/analysis/full_analysis_coordinator.py
-
-Single-writer cross-process coordinator for full repository analysis.
-Guarantees that at most one full analysis execution runs per repository identity
-across Desktop GUI, MCP server, and CLI processes using native OS file locking.
+High-level full-analysis runner and compatibility exports for the lease owner.
 """
 
 from __future__ import annotations
 
-from contextlib import contextmanager
-import json
-import os
-import threading
 import time
-import uuid
-from dataclasses import dataclass
 from pathlib import Path
-from typing import Any, Callable, Mapping
+from typing import Any, Callable
 
-from contextor.core.errors import AnalysisCancelled
-from contextor.core.paths import repo_cache_dir, repo_key
-from contextor.core.repository_identity import read_repository_identity
 from contextor.core.runtime_trace import trace_event
-
-
-@dataclass(frozen=True, slots=True)
-class FullAnalysisLease:
-    repo_key: str
-    token: str
-    owner: str
-    lock_path: str
-    repo_id: str
-    lock_fd: int
-    owner_pid: int = 0
-    owner_process_start_identity: int | None = None
-
-
-class FullAnalysisBusyError(RuntimeError):
-    """Raised when the full analysis lease cannot be acquired."""
-    pass
-
-
-# A dead process normally releases its OS lock immediately. This bound is only
-# for the defensive case where a stale lock handle survives process death; it
-# prevents an orphan diagnostic from turning into an unbounded wait.
-ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0
-
-
-_PROCESS_LOCKS: dict[str, threading.Lock] = {}
-_PROCESS_LOCKS_GUARD = threading.Lock()
-_ADMISSION_LOCKS: dict[str, threading.Lock] = {}
-_ADMISSION_LOCKS_GUARD = threading.Lock()
-
-_ADMISSION_TRACE_FIELD_NAMES = (
-    "op",
-    "path",
-    "job_id",
-    "idempotency_key",
-    "queue_order",
-    "accepted_revision",
-    "started_revision",
-    "origin",
+from contextor.core.analysis.full_analysis_lease import (
+    FullAnalysisLease,
+    FullAnalysisBusyError,
+    ORPHAN_RECOVERY_TIMEOUT_SECONDS,
+    _PROCESS_LOCKS,
+    _PROCESS_LOCKS_GUARD,
+    _ADMISSION_LOCKS,
+    _ADMISSION_LOCKS_GUARD,
+    _ADMISSION_TRACE_FIELD_NAMES,
+    _select_admission_trace_fields,
+    _get_process_lock,
+    _get_admission_lock,
+    _acquire_process_lock_until,
+    _canonical_writer_admission,
+    _prepare_lock_fd,
+    _try_lock_fd,
+    _unlock_fd,
+    _read_lease_metadata,
+    _lease_metadata_path,
+    _read_lease_metadata_file,
+    _write_lease_metadata_file,
+    _process_identity,
+    _lease_owner_state,
+    _log_orphan_recovery,
+    _resolve_lock_path,
+    acquire_full_analysis,
+    release_full_analysis,
 )
 
-
-def _select_admission_trace_fields(
-    fields: Mapping[str, Any] | None,
-) -> dict[str, Any]:
-    if fields is None:
-        return {}
-
-    return {
-        name: fields[name]
-        for name in _ADMISSION_TRACE_FIELD_NAMES
-        if name in fields and fields[name] is not None
-    }
-
-
-def _get_process_lock(
-    repo_key_str: str,
-) -> threading.Lock:
-    with _PROCESS_LOCKS_GUARD:
-        lock = _PROCESS_LOCKS.get(repo_key_str)
-        if lock is None:
-            lock = threading.Lock()
-            _PROCESS_LOCKS[repo_key_str] = lock
-        return lock
-
-
-def _get_admission_lock(
-    repo_key_str: str,
-) -> threading.Lock:
-    with _ADMISSION_LOCKS_GUARD:
-        lock = _ADMISSION_LOCKS.get(repo_key_str)
-        if lock is None:
-            lock = threading.Lock()
-            _ADMISSION_LOCKS[repo_key_str] = lock
-        return lock
-
-
-def _acquire_process_lock_until(
-    lock: threading.Lock,
-    *,
-    deadline: float | None,
-    poll_interval: float,
-    is_cancelled: Callable[[], bool] | None,
-    cancel_message: str,
-    timeout_message: str,
-) -> None:
-    while True:
-        if is_cancelled and is_cancelled():
-            raise AnalysisCancelled(cancel_message)
-        if lock.acquire(blocking=False):
-            return
-        if deadline is not None and time.monotonic() >= deadline:
-            raise FullAnalysisBusyError(timeout_message)
-        time.sleep(min(max(poll_interval, 0.01), 0.25))
-
-
-@contextmanager
-def _canonical_writer_admission(
-    *,
-    lock_file: Path,
-    key: str,
-    repo_id: str,
-    owner: str,
-    writer_kind: str,
-    deadline: float | None,
-    poll_interval: float,
-    is_cancelled: Callable[[], bool] | None,
-    admission_trace_fields: Mapping[str, Any] | None,
-):
-    trace_fields = _select_admission_trace_fields(
-        admission_trace_fields
-    )
-    process_lock = _get_admission_lock(key)
-    started = time.monotonic()
-    _acquire_process_lock_until(
-        process_lock,
-        deadline=deadline,
-        poll_interval=poll_interval,
-        is_cancelled=is_cancelled,
-        cancel_message=(
-            "Canonical writer admission cancelled while waiting for local gate."
-        ),
-        timeout_message=(
-            "Timed out waiting for canonical writer admission gate for "
-            f"{repo_id}"
-        ),
-    )
-    fd = -1
-    os_locked = False
-    admission_path = lock_file.with_name("canonical_writer.admission.lock")
-    try:
-        fd = _prepare_lock_fd(admission_path)
-        while True:
-            if is_cancelled and is_cancelled():
-                raise AnalysisCancelled(
-                    "Canonical writer admission cancelled while waiting for "
-                    "repository gate."
-                )
-            if _try_lock_fd(fd):
-                os_locked = True
-                break
-            if deadline is not None and time.monotonic() >= deadline:
-                raise FullAnalysisBusyError(
-                    "Timed out waiting for canonical writer admission gate for "
-                    f"{repo_id}"
-                )
-            time.sleep(min(max(poll_interval, 0.01), 0.25))
-        trace_event(
-            "ANALYSIS",
-            "CANONICAL_WRITER_ADMISSION_ACQUIRED",
-            repo_id=repo_id,
-            owner=owner,
-            writer_kind=writer_kind,
-            wait_ms=(time.monotonic() - started) * 1000.0,
-            **trace_fields,
-        )
-        yield
-    finally:
-        try:
-            if fd >= 0:
-                if os_locked:
-                    _unlock_fd(fd)
-                else:
-                    try:
-                        os.close(fd)
-                    except OSError:
-                        pass
-        finally:
-            try:
-                process_lock.release()
-            except RuntimeError:
-                pass
-            if os_locked:
-                trace_event(
-                    "ANALYSIS",
-                    "CANONICAL_WRITER_ADMISSION_RELEASED",
-                    repo_id=repo_id,
-                    owner=owner,
-                    writer_kind=writer_kind,
-                    **trace_fields,
-                )
-
-
-def _prepare_lock_fd(lock_path: Path) -> int:
-    lock_path.parent.mkdir(
-        parents=True,
-        exist_ok=True,
-    )
-
-    fd = os.open(
-        lock_path,
-        os.O_RDWR | os.O_CREAT,
-        0o600,
-    )
-
-    if os.fstat(fd).st_size == 0:
-        os.write(fd, b"\0")
-        os.fsync(fd)
-
-    os.lseek(fd, 0, os.SEEK_SET)
-    return fd
-
-
-def _try_lock_fd(fd: int) -> bool:
-    os.lseek(fd, 0, os.SEEK_SET)
-
-    if os.name == "nt":
-        import msvcrt
-
-        try:
-            msvcrt.locking(
-                fd,
-                msvcrt.LK_NBLCK,
-                1,
-            )
-            return True
-        except OSError:
-            return False
-
-    import fcntl
-
-    try:
-        fcntl.flock(
-            fd,
-            fcntl.LOCK_EX | fcntl.LOCK_NB,
-        )
-        return True
-    except BlockingIOError:
-        return False
-
-
-def _unlock_fd(fd: int) -> None:
-    try:
-        os.lseek(fd, 0, os.SEEK_SET)
-
-        if os.name == "nt":
-            import msvcrt
-
-            msvcrt.locking(
-                fd,
-                msvcrt.LK_UNLCK,
-                1,
-            )
-        else:
-            import fcntl
-
-            fcntl.flock(
-                fd,
-                fcntl.LOCK_UN,
-            )
-    finally:
-        os.close(fd)
-
-
-def _read_lease_metadata(fd: int) -> dict[str, Any] | None:
-    """Read diagnostic owner metadata without treating it as lock authority."""
-    try:
-        original_offset = os.lseek(fd, 0, os.SEEK_CUR)
-        os.lseek(fd, 0, os.SEEK_SET)
-        payload = os.read(fd, 16 * 1024)
-    except (OSError, UnicodeError):
-        return None
-    finally:
-        try:
-            os.lseek(fd, original_offset, os.SEEK_SET)
-        except (OSError, UnboundLocalError):
-            pass
-
-    if not payload:
-        return None
-    try:
-        metadata = json.loads(payload.decode("utf-8"))
-    except (UnicodeDecodeError, json.JSONDecodeError):
-        return None
-    return metadata if isinstance(metadata, dict) else None
-
-
-def _lease_metadata_path(lock_path: Path) -> Path:
-    return lock_path.with_name("full_analysis.lease.json")
-
-
-def _read_lease_metadata_file(path: Path) -> dict[str, Any] | None:
-    try:
-        payload = path.read_bytes()
-    except OSError:
-        return None
-    if not payload:
-        return None
-    try:
-        metadata = json.loads(payload.decode("utf-8"))
-    except (UnicodeDecodeError, json.JSONDecodeError):
-        return None
-    return metadata if isinstance(metadata, dict) else None
-
-
-def _write_lease_metadata_file(
-    path: Path,
-    metadata: dict[str, Any],
-) -> None:
-    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
-    try:
-        temporary.write_text(
-            json.dumps(metadata),
-            encoding="utf-8",
-        )
-        os.replace(temporary, path)
-    except OSError:
-        try:
-            temporary.unlink(missing_ok=True)
-        except OSError:
-            pass
-
-
-def _process_identity(pid: int) -> tuple[str | None, int | None, bool]:
-    """Use the existing process-ownership identity model for lease diagnostics."""
-    from contextor.mcp_process_registry import process_identity
-
-    return process_identity(pid)
-
-
-def _lease_owner_state(
-    metadata: dict[str, Any] | None,
-) -> tuple[str, str]:
-    """Return ``active``, ``orphaned`` or ``unknown`` for lease metadata."""
-    if not metadata:
-        return "unknown", "owner metadata unavailable"
-
-    try:
-        owner_pid = int(metadata["pid"])
-    except (KeyError, TypeError, ValueError):
-        return "orphaned", "invalid owner pid"
-
-    image, process_start_identity, alive = _process_identity(owner_pid)
-    owner = str(metadata.get("owner") or "unknown")
-    description = f"owner={owner}, pid={owner_pid}"
-    if not alive:
-        return "orphaned", f"{description} is not alive"
-
-    expected_image = str(metadata.get("executable") or "")
-    if not expected_image:
-        return "unknown", f"{description} identity metadata unavailable"
-    if not image:
-        return "unknown", f"{description} executable identity unavailable"
-    if Path(image).name.casefold() != Path(expected_image).name.casefold():
-        return "orphaned", f"{description} has a reused process identity"
-
-    expected_start = metadata.get("process_start_identity")
-    if expected_start is not None:
-        if process_start_identity is None:
-            return "unknown", f"{description} start identity unavailable"
-        try:
-            if int(expected_start) != int(process_start_identity):
-                return "orphaned", f"{description} has a reused process identity"
-        except (TypeError, ValueError):
-            return "orphaned", f"{description} has invalid start identity"
-
-    return "active", description
-
-
-def _log_orphan_recovery(
-    log: Callable[[str], None] | None,
-    repo_id: str,
-    reason: str,
-) -> None:
-    if log:
-        log(
-            f"Recovering orphaned full analysis lease on repository {repo_id} "
-            f"({reason})."
-        )
-
-
-def _resolve_lock_path(repo_path: str | Path) -> tuple[Path, str, str]:
-    """Resolve lock file path, repo_key, and repo_id for a given repository."""
-    resolved_root = Path(repo_path).expanduser().resolve()
-    key = repo_key(resolved_root)
-    identity = read_repository_identity(resolved_root)
-    repo_id = identity.repo_id if identity is not None else key
-
-    cache_dir = repo_cache_dir(resolved_root)
-    runtime_dir = cache_dir / "runtime"
-    runtime_dir.mkdir(parents=True, exist_ok=True)
-    lock_file = runtime_dir / "full_analysis.lock"
-    return lock_file, key, repo_id
-
-
-def acquire_full_analysis(
-    repo_path: str | Path,
-    *,
-    owner: str = "desktop_analysis",
-    writer_kind: str = "full_analysis",
-    timeout: float | None = None,
-    poll_interval: float = 0.25,
-    is_cancelled: Callable[[], bool] | None = None,
-    log: Callable[[str], None] | None = None,
-    admission_trace_fields: Mapping[str, Any] | None = None,
-) -> FullAnalysisLease:
-    """
-    Acquire exclusive single-writer lease for full repository analysis.
-    Blocks if another process or thread holds the lease until released,
-    timed out, or cancelled.
-    """
-    if writer_kind not in {
-        "full_analysis",
-        "live_mutation",
-        "startup_publish",
-        "local_incremental",
-        "scoped_analysis",
-    }:
-        raise ValueError(
-            "writer_kind must be 'full_analysis', 'live_mutation', "
-            "'startup_publish', 'local_incremental', or 'scoped_analysis'"
-        )
-
-    lock_file, key, repo_id = _resolve_lock_path(repo_path)
-    proc_lock = _get_process_lock(key)
-
-    start_time = time.monotonic()
-    deadline = (
-        start_time + timeout
-        if timeout is not None
-        else None
-    )
-
-    with _canonical_writer_admission(
-        lock_file=lock_file,
-        key=key,
-        repo_id=repo_id,
-        owner=str(owner),
-        writer_kind=writer_kind,
-        deadline=deadline,
-        poll_interval=poll_interval,
-        is_cancelled=is_cancelled,
-        admission_trace_fields=admission_trace_fields,
-    ):
-        _acquire_process_lock_until(
-            proc_lock,
-            deadline=deadline,
-            poll_interval=poll_interval,
-            is_cancelled=is_cancelled,
-            cancel_message="Full analysis cancelled while waiting for local lock.",
-            timeout_message=(
-                "Timed out waiting for in-process full analysis lock for "
-                f"{repo_id}"
-            ),
-        )
-        fd = -1
-        logged_waiting = False
-        logged_recovery = False
-        orphan_recovery_deadline: float | None = None
-        unknown_owner_deadline: float | None = None
-        try:
-            fd = _prepare_lock_fd(lock_file)
-
-            while True:
-                if is_cancelled and is_cancelled():
-                    raise AnalysisCancelled(
-                        "Full analysis cancelled while waiting for repository lease."
-                    )
-
-                previous_metadata = _read_lease_metadata(fd)
-                if previous_metadata is None:
-                    previous_metadata = _read_lease_metadata_file(
-                        _lease_metadata_path(lock_file)
-                    )
-                if _try_lock_fd(fd):
-                    previous_owner_state, previous_owner_reason = _lease_owner_state(
-                        previous_metadata
-                    )
-                    if previous_owner_state == "orphaned" and not logged_recovery:
-                        _log_orphan_recovery(
-                            log,
-                            repo_id,
-                            previous_owner_reason,
-                        )
-                        logged_recovery = True
-                    token = uuid.uuid4().hex
-
-                    owner_image, owner_process_start_identity, _ = _process_identity(
-                        os.getpid()
-                    )
-
-                    metadata = {
-                        "pid": os.getpid(),
-                        "token": token,
-                        "owner": str(owner),
-                        "repo_id": str(repo_id),
-                        "timestamp": time.time(),
-                    }
-                    if owner_image:
-                        metadata["executable"] = owner_image
-                    if owner_process_start_identity is not None:
-                        metadata["process_start_identity"] = owner_process_start_identity
-
-                    _write_lease_metadata_file(
-                        _lease_metadata_path(lock_file),
-                        metadata,
-                    )
-
-                    # Metadata is diagnostic only.
-                    # OS lock ownership is authoritative.
-                    os.ftruncate(fd, 0)
-                    os.lseek(fd, 0, os.SEEK_SET)
-                    os.write(
-                        fd,
-                        json.dumps(metadata).encode("utf-8"),
-                    )
-                    os.fsync(fd)
-
-                    # Ensure byte 0 remains inside the locked file after metadata write.
-                    os.lseek(fd, 0, os.SEEK_SET)
-
-                    lease = FullAnalysisLease(
-                        repo_key=key,
-                        token=token,
-                        owner=str(owner),
-                        lock_path=str(lock_file),
-                        repo_id=str(repo_id),
-                        lock_fd=fd,
-                        owner_pid=os.getpid(),
-                        owner_process_start_identity=owner_process_start_identity,
-                    )
-                    fd = -1
-                    return lease
-
-                if not logged_waiting:
-                    if log:
-                        log(f"Waiting for full analysis lease on repository {repo_id}...")
-                        owner_state, owner_reason = _lease_owner_state(previous_metadata)
-                        if owner_state == "active":
-                            log("Full analysis lease has a valid active owner " f"({owner_reason}).")
-                        elif owner_state == "unknown":
-                            log("Full analysis lease owner could not be verified; " f"continuing to wait ({owner_reason}).")
-                    logged_waiting = True
-
-                owner_state, owner_reason = _lease_owner_state(previous_metadata)
-                if owner_state == "orphaned":
-                    unknown_owner_deadline = None
-                    if orphan_recovery_deadline is None:
-                        orphan_recovery_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
-                    if not logged_recovery:
-                        _log_orphan_recovery(log, repo_id, owner_reason)
-                        logged_recovery = True
-                    if time.monotonic() >= orphan_recovery_deadline:
-                        raise FullAnalysisBusyError(f"Timed out recovering orphaned full analysis lease for {repo_id}")
-                elif owner_state == "unknown":
-                    orphan_recovery_deadline = None
-                    if unknown_owner_deadline is None:
-                        unknown_owner_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
-                    if time.monotonic() >= unknown_owner_deadline:
-                        raise FullAnalysisBusyError(f"Timed out waiting because full analysis lease owner could not be verified for {repo_id}")
-                else:
-                    orphan_recovery_deadline = None
-                    unknown_owner_deadline = None
-                if deadline is not None and time.monotonic() >= deadline:
-                    raise FullAnalysisBusyError(f"Repository {repo_id} is currently locked for full analysis")
-                time.sleep(min(max(poll_interval, 0.01), 0.25))
-        except Exception:
-            if fd >= 0:
-                try:
-                    os.close(fd)
-                except OSError:
-                    pass
-            proc_lock.release()
-            raise
-
-
-def release_full_analysis(
-    lease: FullAnalysisLease,
-) -> None:
-    """Release the full analysis lease."""
-    if not isinstance(
-        lease,
-        FullAnalysisLease,
-    ):
-        return
-
-    try:
-        _unlock_fd(lease.lock_fd)
-    finally:
-        proc_lock = _get_process_lock(
-            lease.repo_key
-        )
-        try:
-            proc_lock.release()
-        except RuntimeError:
-            pass
-
-
 def run_full_analysis_exclusive(
     path: str | Path,
     *,
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 7c90062..9ba32ae 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1306,7 +1306,7 @@ class ContextorFacade:
         progress_callback=None,
         additional_excludes: list[str] | None = None,
     ) -> str:
-        from contextor.core.analysis.full_analysis_coordinator import (
+        from contextor.core.analysis.full_analysis_lease import (
             acquire_full_analysis,
             release_full_analysis,
         )
@@ -1539,7 +1539,7 @@ class ContextorFacade:
                 revision=None,
                 warning=None,
             )
-        from contextor.core.analysis.full_analysis_coordinator import (
+        from contextor.core.analysis.full_analysis_lease import (
             acquire_full_analysis,
             release_full_analysis,
         )
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 10cfbdc..08d6ca7 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -12,6 +12,8 @@ Complete test suite certifying the single-writer full-analysis coordinator:
 from __future__ import annotations
 
 import json
+import ast
+import inspect
 import multiprocessing
 import os
 import threading
@@ -40,6 +42,67 @@ from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
 
 
+def test_acyclic_lease_import_contract():
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_lease as lease
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    def imported_modules(module):
+        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
+        return {
+            node.module
+            for node in ast.walk(tree)
+            if isinstance(node, ast.ImportFrom) and node.module
+        }
+
+    assert "contextor.core.analysis.full_analysis_coordinator" not in imported_modules(facade)
+    assert "contextor.core.api.facade" not in imported_modules(lease)
+    assert "contextor.core.analysis.full_analysis_coordinator" not in imported_modules(lease)
+    assert "contextor.core.analysis.full_analysis_lease" in imported_modules(coordinator)
+    assert str(inspect.signature(facade.ContextorFacade.analyze_layer)) == (
+        "(root_dir: str, layer_dir: str, log=None, progress_callback=None, "
+        "additional_excludes: list[str] | None = None) -> str"
+    )
+    assert str(inspect.signature(facade.ContextorFacade.analyze_single_file)) == (
+        "(file_path: str, repo_root: str, log=None, progress_callback=None, "
+        "additional_excludes: list[str] | None = None, "
+        "publication_result: dict[str, typing.Any] | None = None) -> str"
+    )
+
+
+def test_extracted_lease_api_and_process_locks_have_one_owner():
+    from contextor.core.analysis import full_analysis_lease as lease_a
+    from contextor.core.analysis import full_analysis_lease as lease_b
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    assert lease_a is lease_b
+    assert coordinator.acquire_full_analysis is lease_a.acquire_full_analysis
+    assert coordinator.release_full_analysis is lease_a.release_full_analysis
+    assert coordinator.FullAnalysisLease is lease_a.FullAnalysisLease
+    assert coordinator.FullAnalysisBusyError is lease_a.FullAnalysisBusyError
+    assert coordinator._PROCESS_LOCKS is lease_a._PROCESS_LOCKS
+    assert coordinator._ADMISSION_LOCKS is lease_a._ADMISSION_LOCKS
+    assert coordinator.acquire_full_analysis.__globals__["_PROCESS_LOCKS"] is lease_a._PROCESS_LOCKS
+    assert coordinator.acquire_full_analysis.__globals__["_ADMISSION_LOCKS"] is lease_a._ADMISSION_LOCKS
+
+
+@pytest.mark.parametrize("first", ["coordinator", "lease"])
+def test_coordinator_and_extracted_lease_exclude_each_other(tmp_path, first):
+    from contextor.core.analysis import full_analysis_lease as lease
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    first_owner = coordinator if first == "coordinator" else lease
+    second_owner = lease if first == "coordinator" else coordinator
+    held = first_owner.acquire_full_analysis(repo, timeout=1.0)
+    try:
+        with pytest.raises(FullAnalysisBusyError):
+            second_owner.acquire_full_analysis(repo, timeout=0.1, poll_interval=0.01)
+    finally:
+        first_owner.release_full_analysis(held)
+
+
 def _worker_try_writer_kind(repo_path, writer_kind, result_queue):
     try:
         lease = acquire_full_analysis(
@@ -59,7 +122,7 @@ def test_scoped_facade_holds_writer_lease_before_identity_write(
     tmp_path, isolated_dirs, monkeypatch, method, target_kind
 ):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -201,7 +264,7 @@ def test_scoped_facade_invalid_target_does_not_acquire_lease(
     tmp_path, monkeypatch, method, target_kind
 ):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -224,7 +287,7 @@ def test_scoped_facade_invalid_target_does_not_acquire_lease(
 
 def test_scoped_facade_non_python_target_does_not_acquire_lease(tmp_path, monkeypatch):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -243,7 +306,7 @@ def test_invalid_scoped_file_resets_publication_result_before_validation(
     tmp_path, isolated_dirs, monkeypatch
 ):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -269,7 +332,7 @@ def test_denied_scoped_file_resets_publication_result_without_mutation(
     tmp_path, isolated_dirs, monkeypatch
 ):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -303,7 +366,7 @@ def test_scoped_facade_denied_lease_does_not_start_body_or_identity(
     tmp_path, isolated_dirs, monkeypatch, method, target_kind
 ):
     from contextor.core.api import facade
-    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    from contextor.core.analysis import full_analysis_lease as coordinator
 
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -922,7 +985,7 @@ def test_unknown_owner_metadata_has_bounded_failure(
     monkeypatch,
 ):
     """An occupied lock with unreadable metadata cannot create an infinite wait."""
-    from contextor.core.analysis import full_analysis_coordinator as fac
+    from contextor.core.analysis import full_analysis_lease as fac
 
     monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
     repo = tmp_path / "repo_unknown_owner"
@@ -963,7 +1026,7 @@ def test_legacy_owner_metadata_has_bounded_failure(
     monkeypatch,
 ):
     """Legacy metadata without process identity is unknown, not silently live."""
-    from contextor.core.analysis import full_analysis_coordinator as fac
+    from contextor.core.analysis import full_analysis_lease as fac
 
     monkeypatch.setattr(fac, "ORPHAN_RECOVERY_TIMEOUT_SECONDS", 0.2)
     repo = tmp_path / "repo_legacy_owner"
diff --git a/contextor/core/analysis/full_analysis_lease.py b/contextor/core/analysis/full_analysis_lease.py
new file mode 100644
index 0000000..4e416e9
--- /dev/null
+++ b/contextor/core/analysis/full_analysis_lease.py
@@ -0,0 +1,610 @@
+"""
+contextor/core/analysis/full_analysis_lease.py
+
+Single-writer cross-process coordinator for full repository analysis.
+Guarantees that at most one full analysis execution runs per repository identity
+across Desktop GUI, MCP server, and CLI processes using native OS file locking.
+"""
+
+from __future__ import annotations
+
+from contextlib import contextmanager
+import json
+import os
+import threading
+import time
+import uuid
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any, Callable, Mapping
+
+from contextor.core.errors import AnalysisCancelled
+from contextor.core.paths import repo_cache_dir, repo_key
+from contextor.core.repository_identity import read_repository_identity
+from contextor.core.runtime_trace import trace_event
+
+
+@dataclass(frozen=True, slots=True)
+class FullAnalysisLease:
+    repo_key: str
+    token: str
+    owner: str
+    lock_path: str
+    repo_id: str
+    lock_fd: int
+    owner_pid: int = 0
+    owner_process_start_identity: int | None = None
+
+
+class FullAnalysisBusyError(RuntimeError):
+    """Raised when the full analysis lease cannot be acquired."""
+    pass
+
+
+# A dead process normally releases its OS lock immediately. This bound is only
+# for the defensive case where a stale lock handle survives process death; it
+# prevents an orphan diagnostic from turning into an unbounded wait.
+ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0
+
+
+_PROCESS_LOCKS: dict[str, threading.Lock] = {}
+_PROCESS_LOCKS_GUARD = threading.Lock()
+_ADMISSION_LOCKS: dict[str, threading.Lock] = {}
+_ADMISSION_LOCKS_GUARD = threading.Lock()
+
+_ADMISSION_TRACE_FIELD_NAMES = (
+    "op",
+    "path",
+    "job_id",
+    "idempotency_key",
+    "queue_order",
+    "accepted_revision",
+    "started_revision",
+    "origin",
+)
+
+
+def _select_admission_trace_fields(
+    fields: Mapping[str, Any] | None,
+) -> dict[str, Any]:
+    if fields is None:
+        return {}
+
+    return {
+        name: fields[name]
+        for name in _ADMISSION_TRACE_FIELD_NAMES
+        if name in fields and fields[name] is not None
+    }
+
+
+def _get_process_lock(
+    repo_key_str: str,
+) -> threading.Lock:
+    with _PROCESS_LOCKS_GUARD:
+        lock = _PROCESS_LOCKS.get(repo_key_str)
+        if lock is None:
+            lock = threading.Lock()
+            _PROCESS_LOCKS[repo_key_str] = lock
+        return lock
+
+
+def _get_admission_lock(
+    repo_key_str: str,
+) -> threading.Lock:
+    with _ADMISSION_LOCKS_GUARD:
+        lock = _ADMISSION_LOCKS.get(repo_key_str)
+        if lock is None:
+            lock = threading.Lock()
+            _ADMISSION_LOCKS[repo_key_str] = lock
+        return lock
+
+
+def _acquire_process_lock_until(
+    lock: threading.Lock,
+    *,
+    deadline: float | None,
+    poll_interval: float,
+    is_cancelled: Callable[[], bool] | None,
+    cancel_message: str,
+    timeout_message: str,
+) -> None:
+    while True:
+        if is_cancelled and is_cancelled():
+            raise AnalysisCancelled(cancel_message)
+        if lock.acquire(blocking=False):
+            return
+        if deadline is not None and time.monotonic() >= deadline:
+            raise FullAnalysisBusyError(timeout_message)
+        time.sleep(min(max(poll_interval, 0.01), 0.25))
+
+
+@contextmanager
+def _canonical_writer_admission(
+    *,
+    lock_file: Path,
+    key: str,
+    repo_id: str,
+    owner: str,
+    writer_kind: str,
+    deadline: float | None,
+    poll_interval: float,
+    is_cancelled: Callable[[], bool] | None,
+    admission_trace_fields: Mapping[str, Any] | None,
+):
+    trace_fields = _select_admission_trace_fields(
+        admission_trace_fields
+    )
+    process_lock = _get_admission_lock(key)
+    started = time.monotonic()
+    _acquire_process_lock_until(
+        process_lock,
+        deadline=deadline,
+        poll_interval=poll_interval,
+        is_cancelled=is_cancelled,
+        cancel_message=(
+            "Canonical writer admission cancelled while waiting for local gate."
+        ),
+        timeout_message=(
+            "Timed out waiting for canonical writer admission gate for "
+            f"{repo_id}"
+        ),
+    )
+    fd = -1
+    os_locked = False
+    admission_path = lock_file.with_name("canonical_writer.admission.lock")
+    try:
+        fd = _prepare_lock_fd(admission_path)
+        while True:
+            if is_cancelled and is_cancelled():
+                raise AnalysisCancelled(
+                    "Canonical writer admission cancelled while waiting for "
+                    "repository gate."
+                )
+            if _try_lock_fd(fd):
+                os_locked = True
+                break
+            if deadline is not None and time.monotonic() >= deadline:
+                raise FullAnalysisBusyError(
+                    "Timed out waiting for canonical writer admission gate for "
+                    f"{repo_id}"
+                )
+            time.sleep(min(max(poll_interval, 0.01), 0.25))
+        trace_event(
+            "ANALYSIS",
+            "CANONICAL_WRITER_ADMISSION_ACQUIRED",
+            repo_id=repo_id,
+            owner=owner,
+            writer_kind=writer_kind,
+            wait_ms=(time.monotonic() - started) * 1000.0,
+            **trace_fields,
+        )
+        yield
+    finally:
+        try:
+            if fd >= 0:
+                if os_locked:
+                    _unlock_fd(fd)
+                else:
+                    try:
+                        os.close(fd)
+                    except OSError:
+                        pass
+        finally:
+            try:
+                process_lock.release()
+            except RuntimeError:
+                pass
+            if os_locked:
+                trace_event(
+                    "ANALYSIS",
+                    "CANONICAL_WRITER_ADMISSION_RELEASED",
+                    repo_id=repo_id,
+                    owner=owner,
+                    writer_kind=writer_kind,
+                    **trace_fields,
+                )
+
+
+def _prepare_lock_fd(lock_path: Path) -> int:
+    lock_path.parent.mkdir(
+        parents=True,
+        exist_ok=True,
+    )
+
+    fd = os.open(
+        lock_path,
+        os.O_RDWR | os.O_CREAT,
+        0o600,
+    )
+
+    if os.fstat(fd).st_size == 0:
+        os.write(fd, b"\0")
+        os.fsync(fd)
+
+    os.lseek(fd, 0, os.SEEK_SET)
+    return fd
+
+
+def _try_lock_fd(fd: int) -> bool:
+    os.lseek(fd, 0, os.SEEK_SET)
+
+    if os.name == "nt":
+        import msvcrt
+
+        try:
+            msvcrt.locking(
+                fd,
+                msvcrt.LK_NBLCK,
+                1,
+            )
+            return True
+        except OSError:
+            return False
+
+    import fcntl
+
+    try:
+        fcntl.flock(
+            fd,
+            fcntl.LOCK_EX | fcntl.LOCK_NB,
+        )
+        return True
+    except BlockingIOError:
+        return False
+
+
+def _unlock_fd(fd: int) -> None:
+    try:
+        os.lseek(fd, 0, os.SEEK_SET)
+
+        if os.name == "nt":
+            import msvcrt
+
+            msvcrt.locking(
+                fd,
+                msvcrt.LK_UNLCK,
+                1,
+            )
+        else:
+            import fcntl
+
+            fcntl.flock(
+                fd,
+                fcntl.LOCK_UN,
+            )
+    finally:
+        os.close(fd)
+
+
+def _read_lease_metadata(fd: int) -> dict[str, Any] | None:
+    """Read diagnostic owner metadata without treating it as lock authority."""
+    try:
+        original_offset = os.lseek(fd, 0, os.SEEK_CUR)
+        os.lseek(fd, 0, os.SEEK_SET)
+        payload = os.read(fd, 16 * 1024)
+    except (OSError, UnicodeError):
+        return None
+    finally:
+        try:
+            os.lseek(fd, original_offset, os.SEEK_SET)
+        except (OSError, UnboundLocalError):
+            pass
+
+    if not payload:
+        return None
+    try:
+        metadata = json.loads(payload.decode("utf-8"))
+    except (UnicodeDecodeError, json.JSONDecodeError):
+        return None
+    return metadata if isinstance(metadata, dict) else None
+
+
+def _lease_metadata_path(lock_path: Path) -> Path:
+    return lock_path.with_name("full_analysis.lease.json")
+
+
+def _read_lease_metadata_file(path: Path) -> dict[str, Any] | None:
+    try:
+        payload = path.read_bytes()
+    except OSError:
+        return None
+    if not payload:
+        return None
+    try:
+        metadata = json.loads(payload.decode("utf-8"))
+    except (UnicodeDecodeError, json.JSONDecodeError):
+        return None
+    return metadata if isinstance(metadata, dict) else None
+
+
+def _write_lease_metadata_file(
+    path: Path,
+    metadata: dict[str, Any],
+) -> None:
+    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
+    try:
+        temporary.write_text(
+            json.dumps(metadata),
+            encoding="utf-8",
+        )
+        os.replace(temporary, path)
+    except OSError:
+        try:
+            temporary.unlink(missing_ok=True)
+        except OSError:
+            pass
+
+
+def _process_identity(pid: int) -> tuple[str | None, int | None, bool]:
+    """Use the existing process-ownership identity model for lease diagnostics."""
+    from contextor.mcp_process_registry import process_identity
+
+    return process_identity(pid)
+
+
+def _lease_owner_state(
+    metadata: dict[str, Any] | None,
+) -> tuple[str, str]:
+    """Return ``active``, ``orphaned`` or ``unknown`` for lease metadata."""
+    if not metadata:
+        return "unknown", "owner metadata unavailable"
+
+    try:
+        owner_pid = int(metadata["pid"])
+    except (KeyError, TypeError, ValueError):
+        return "orphaned", "invalid owner pid"
+
+    image, process_start_identity, alive = _process_identity(owner_pid)
+    owner = str(metadata.get("owner") or "unknown")
+    description = f"owner={owner}, pid={owner_pid}"
+    if not alive:
+        return "orphaned", f"{description} is not alive"
+
+    expected_image = str(metadata.get("executable") or "")
+    if not expected_image:
+        return "unknown", f"{description} identity metadata unavailable"
+    if not image:
+        return "unknown", f"{description} executable identity unavailable"
+    if Path(image).name.casefold() != Path(expected_image).name.casefold():
+        return "orphaned", f"{description} has a reused process identity"
+
+    expected_start = metadata.get("process_start_identity")
+    if expected_start is not None:
+        if process_start_identity is None:
+            return "unknown", f"{description} start identity unavailable"
+        try:
+            if int(expected_start) != int(process_start_identity):
+                return "orphaned", f"{description} has a reused process identity"
+        except (TypeError, ValueError):
+            return "orphaned", f"{description} has invalid start identity"
+
+    return "active", description
+
+
+def _log_orphan_recovery(
+    log: Callable[[str], None] | None,
+    repo_id: str,
+    reason: str,
+) -> None:
+    if log:
+        log(
+            f"Recovering orphaned full analysis lease on repository {repo_id} "
+            f"({reason})."
+        )
+
+
+def _resolve_lock_path(repo_path: str | Path) -> tuple[Path, str, str]:
+    """Resolve lock file path, repo_key, and repo_id for a given repository."""
+    resolved_root = Path(repo_path).expanduser().resolve()
+    key = repo_key(resolved_root)
+    identity = read_repository_identity(resolved_root)
+    repo_id = identity.repo_id if identity is not None else key
+
+    cache_dir = repo_cache_dir(resolved_root)
+    runtime_dir = cache_dir / "runtime"
+    runtime_dir.mkdir(parents=True, exist_ok=True)
+    lock_file = runtime_dir / "full_analysis.lock"
+    return lock_file, key, repo_id
+
+
+def acquire_full_analysis(
+    repo_path: str | Path,
+    *,
+    owner: str = "desktop_analysis",
+    writer_kind: str = "full_analysis",
+    timeout: float | None = None,
+    poll_interval: float = 0.25,
+    is_cancelled: Callable[[], bool] | None = None,
+    log: Callable[[str], None] | None = None,
+    admission_trace_fields: Mapping[str, Any] | None = None,
+) -> FullAnalysisLease:
+    """
+    Acquire exclusive single-writer lease for full repository analysis.
+    Blocks if another process or thread holds the lease until released,
+    timed out, or cancelled.
+    """
+    if writer_kind not in {
+        "full_analysis",
+        "live_mutation",
+        "startup_publish",
+        "local_incremental",
+        "scoped_analysis",
+    }:
+        raise ValueError(
+            "writer_kind must be 'full_analysis', 'live_mutation', "
+            "'startup_publish', 'local_incremental', or 'scoped_analysis'"
+        )
+
+    lock_file, key, repo_id = _resolve_lock_path(repo_path)
+    proc_lock = _get_process_lock(key)
+
+    start_time = time.monotonic()
+    deadline = (
+        start_time + timeout
+        if timeout is not None
+        else None
+    )
+
+    with _canonical_writer_admission(
+        lock_file=lock_file,
+        key=key,
+        repo_id=repo_id,
+        owner=str(owner),
+        writer_kind=writer_kind,
+        deadline=deadline,
+        poll_interval=poll_interval,
+        is_cancelled=is_cancelled,
+        admission_trace_fields=admission_trace_fields,
+    ):
+        _acquire_process_lock_until(
+            proc_lock,
+            deadline=deadline,
+            poll_interval=poll_interval,
+            is_cancelled=is_cancelled,
+            cancel_message="Full analysis cancelled while waiting for local lock.",
+            timeout_message=(
+                "Timed out waiting for in-process full analysis lock for "
+                f"{repo_id}"
+            ),
+        )
+        fd = -1
+        logged_waiting = False
+        logged_recovery = False
+        orphan_recovery_deadline: float | None = None
+        unknown_owner_deadline: float | None = None
+        try:
+            fd = _prepare_lock_fd(lock_file)
+
+            while True:
+                if is_cancelled and is_cancelled():
+                    raise AnalysisCancelled(
+                        "Full analysis cancelled while waiting for repository lease."
+                    )
+
+                previous_metadata = _read_lease_metadata(fd)
+                if previous_metadata is None:
+                    previous_metadata = _read_lease_metadata_file(
+                        _lease_metadata_path(lock_file)
+                    )
+                if _try_lock_fd(fd):
+                    previous_owner_state, previous_owner_reason = _lease_owner_state(
+                        previous_metadata
+                    )
+                    if previous_owner_state == "orphaned" and not logged_recovery:
+                        _log_orphan_recovery(
+                            log,
+                            repo_id,
+                            previous_owner_reason,
+                        )
+                        logged_recovery = True
+                    token = uuid.uuid4().hex
+
+                    owner_image, owner_process_start_identity, _ = _process_identity(
+                        os.getpid()
+                    )
+
+                    metadata = {
+                        "pid": os.getpid(),
+                        "token": token,
+                        "owner": str(owner),
+                        "repo_id": str(repo_id),
+                        "timestamp": time.time(),
+                    }
+                    if owner_image:
+                        metadata["executable"] = owner_image
+                    if owner_process_start_identity is not None:
+                        metadata["process_start_identity"] = owner_process_start_identity
+
+                    _write_lease_metadata_file(
+                        _lease_metadata_path(lock_file),
+                        metadata,
+                    )
+
+                    # Metadata is diagnostic only.
+                    # OS lock ownership is authoritative.
+                    os.ftruncate(fd, 0)
+                    os.lseek(fd, 0, os.SEEK_SET)
+                    os.write(
+                        fd,
+                        json.dumps(metadata).encode("utf-8"),
+                    )
+                    os.fsync(fd)
+
+                    # Ensure byte 0 remains inside the locked file after metadata write.
+                    os.lseek(fd, 0, os.SEEK_SET)
+
+                    lease = FullAnalysisLease(
+                        repo_key=key,
+                        token=token,
+                        owner=str(owner),
+                        lock_path=str(lock_file),
+                        repo_id=str(repo_id),
+                        lock_fd=fd,
+                        owner_pid=os.getpid(),
+                        owner_process_start_identity=owner_process_start_identity,
+                    )
+                    fd = -1
+                    return lease
+
+                if not logged_waiting:
+                    if log:
+                        log(f"Waiting for full analysis lease on repository {repo_id}...")
+                        owner_state, owner_reason = _lease_owner_state(previous_metadata)
+                        if owner_state == "active":
+                            log("Full analysis lease has a valid active owner " f"({owner_reason}).")
+                        elif owner_state == "unknown":
+                            log("Full analysis lease owner could not be verified; " f"continuing to wait ({owner_reason}).")
+                    logged_waiting = True
+
+                owner_state, owner_reason = _lease_owner_state(previous_metadata)
+                if owner_state == "orphaned":
+                    unknown_owner_deadline = None
+                    if orphan_recovery_deadline is None:
+                        orphan_recovery_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
+                    if not logged_recovery:
+                        _log_orphan_recovery(log, repo_id, owner_reason)
+                        logged_recovery = True
+                    if time.monotonic() >= orphan_recovery_deadline:
+                        raise FullAnalysisBusyError(f"Timed out recovering orphaned full analysis lease for {repo_id}")
+                elif owner_state == "unknown":
+                    orphan_recovery_deadline = None
+                    if unknown_owner_deadline is None:
+                        unknown_owner_deadline = min(deadline if deadline is not None else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS, time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS)
+                    if time.monotonic() >= unknown_owner_deadline:
+                        raise FullAnalysisBusyError(f"Timed out waiting because full analysis lease owner could not be verified for {repo_id}")
+                else:
+                    orphan_recovery_deadline = None
+                    unknown_owner_deadline = None
+                if deadline is not None and time.monotonic() >= deadline:
+                    raise FullAnalysisBusyError(f"Repository {repo_id} is currently locked for full analysis")
+                time.sleep(min(max(poll_interval, 0.01), 0.25))
+        except Exception:
+            if fd >= 0:
+                try:
+                    os.close(fd)
+                except OSError:
+                    pass
+            proc_lock.release()
+            raise
+
+
+def release_full_analysis(
+    lease: FullAnalysisLease,
+) -> None:
+    """Release the full analysis lease."""
+    if not isinstance(
+        lease,
+        FullAnalysisLease,
+    ):
+        return
+
+    try:
+        _unlock_fd(lease.lock_fd)
+    finally:
+        proc_lock = _get_process_lock(
+            lease.repo_key
+        )
+        try:
+            proc_lock.release()
+        except RuntimeError:
+            pass
```
