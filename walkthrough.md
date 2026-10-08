# L37_L38_A2_STORE_LOCK_COMPATIBILITY_EVIDENCE

## CURRENT_HEAD

- Repository: \`C:\Temp\Contextor_Repo\`
- Git HEAD: \`d20338dd9a8a777e4498919530a628baea302fe3\`
- Git/source verification: \`git diff --quiet\` returned success and \`git status --short\` was empty before writing this report.
- Contextor MCP source evidence was fresh at LIVE revision 1 with \`workspace_sync=verified\` for the target store and relevant test modules.
- No tests were run.

## EXACT_LOCK_IMPLEMENTATION

Source: \`C:\Temp\Contextor_Repo\contextor\core\live_state\store.py\`

### \`_paths\`, lines 1405-1407

\`\`\`python
def _paths(cache_dir: str | Path) -> tuple[Path, Path, Path]:
    root = Path(cache_dir)
    return root / "engine_state.pkl", root / "engine_state.meta.json", root / "engine_state.lock"
\`\`\`

### \`_acquire_lock\`, lines 1444-1459

\`\`\`python
def _acquire_lock(lock_file: Path, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            try:
                if time.time() - lock_file.stat().st_mtime > 30:
                    lock_file.unlink()
                    continue

            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for LIVE state lock: {lock_file}")
            time.sleep(0.02)
\`\`\`

The exception boundaries are as shown: acquisition catches \`FileExistsError\` and \`PermissionError\`; the stale check/unlink catches only \`FileNotFoundError\`; a stale-path unlink \`OSError\` other than that is not caught here. Timeout is raised after checking staleness and before the next 20 ms sleep.

### \`save_snapshot\` acquisition and entry into its protected try, lines 1497-1510

\`\`\`python
    state_file, meta_file, lock_file = _paths(cache_dir)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(lock_file)
    token = uuid.uuid4().hex
    state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
    meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
    generation_state = state_tmp
    generation_file_state: Path | None = None
    generation_lineage_manifest: Path | None = None
    generation_lineage_chunks: list[Path] = []
    reusable_lineage_sources: dict[str, Any] = {}
    committed = False

    try:
\`\`\`

Thus the lock is acquired before the \`try\` begins. The lines between acquisition and \`try\` are retained here because they are part of the exact exception/control-flow boundary.

### \`save_snapshot\` complete finally cleanup, lines 1799-1835

\`\`\`python
    finally:
        for temporary in (
            state_tmp,
            meta_tmp,
        ):
            try:
                temporary.unlink()
            except OSError:
                pass

        if (
            not committed
            and exact_revision is not None
        ):
            failed_generations = [
                generation_state,
                generation_file_state,
                generation_lineage_manifest,
                *generation_lineage_chunks,
            ]

            for temporary in failed_generations:
                if temporary is None:
                    continue

                try:
                    temporary.unlink()
                except OSError:
                    pass

        try:
            os.close(lock_fd)
        finally:
            try:
                lock_file.unlink()
            except OSError:
                pass
\`\`\`

The path unlink is attempted after closing the descriptor and is attempted on both commit success and failure. Any \`OSError\` from lock-path unlink is suppressed. There is no explicit \`lock_file.exists()\` postcondition in this implementation.

## ALL_LOCK_CALLERS

### Direct \`_acquire_lock\` callers

Contextor \`get_symbol_call_context\` returned one direct caller edge in its documented intra-module scope: \`contextor.core.live_state.store::save_snapshot -> contextor.core.live_state.store::_acquire_lock\`, line 1499.

Git/source verification used \`rg -n --glob '*.py' '_acquire_lock\\('\` over \`contextor\` and \`tests\`. It found exactly:

- \`C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1444\` — definition.
- \`C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1499\` — the sole call.
- No test directly calls \`_acquire_lock\`.

Therefore \`save_snapshot\` is the only source-text direct consumer found. This inventory is about direct references; it does not claim that every dynamic monkeypatch or runtime-generated call is represented by Contextor's intra-module call facts.

### Higher-level calls to \`save_snapshot\` (not additional direct lock callers)

Git/source search of production Python files found the definition and these call sites:

- \`C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:470\` — \`save_engine_state\` returns \`save_snapshot(...)\`.
- \`C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1186-1199\`.
- \`C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1465-1474\`.
- \`C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:2297-2305\` — legacy-cache migration calls \`save_snapshot\`.

These are routes into the one \`save_snapshot\` direct lock-acquisition point; they do not add another \`_acquire_lock\` call site.

### Descriptor use

In \`store.py\`, \`lock_fd\` appears at line 1499 as the integer returned by \`_acquire_lock\` and at line 1830 as the argument to \`os.close(lock_fd)\`. It is not passed to \`msvcrt.locking\`, \`fcntl.flock\`, \`os.write\`, or any other lock operation. The cleanup deletes \`lock_file\` by pathname, not by descriptor.

## LOCK_TEST_CONTRACTS

Search scope and classification:

- Repository-wide literal \`engine_state.lock\` search returned only the path constructor at \`store.py:1407\` and the name check at \`tests/test_live_state_store.py:127\`.
- Search for \`_acquire_lock(\` in production and tests returned only the definition and the \`save_snapshot\` call above.
- No test source occurrence of \`st_mtime\` or \`os.utime\` referred to the snapshot lock. Timestamp tests found by source search concern source-file freshness, watcher state, or MCP job files.
- There is no focused test for \`_acquire_lock\` stale reclamation or its \`TimeoutError\`.
- Snapshot behavior tests that exercise the lock indirectly through \`save_snapshot\` are distinguished below from tests that inspect the lock pathname.

### Direct target lock reference and snapshot persistence tests

Source: \`C:\Temp\Contextor_Repo\tests\test_live_state_store.py\`

\`test_snapshot_roundtrip_increments_revision_and_records_writer\`, lines 89-98, makes two sequential saves, loads the result, and checks state/revisions/writer/metadata. It does not inspect the lock file:

\`\`\`python
def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
    first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
    second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")

    state, metadata = load_snapshot(tmp_path, "state-a")

    assert state == {"value": 2}
    assert (first.revision, second.revision, metadata.revision) == (1, 2, 2)
    assert metadata.writer == "mcp"
    assert read_metadata(tmp_path) == metadata
\`\`\`

\`test_default_snapshot_publishes_final_pickle_via_temp_replace\`, lines 101-110, inspects the final pickle replacement source/destination, not the lock file:

\`\`\`python
def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    replacements = []
    original_replace = store.os.replace
    monkeypatch.setattr(store.os, "replace", lambda source, target: (replacements.append((source, target)), original_replace(source, target))[1])
    save_snapshot({"value": 1}, tmp_path, "state-a")
    assert replacements[0][1].name == "engine_state.pkl"
    assert replacements[0][0].name != "engine_state.pkl"
    assert replacements[0][0].name.endswith(".tmp")
\`\`\`

The only explicit \`engine_state.lock\` test-source reference is in \`test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock\`, lines 113-136. It allows the lock unlink to call the original implementation, injects failure for other unlink cleanup, asserts the metadata revision remains at baseline after metadata replacement fails, restores monkeypatches, then verifies another save succeeds:

\`\`\`python
def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
    original_replace = store.os.replace
    original_unlink = type(tmp_path).unlink

    def failing_replace(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("authoritative persistence failure")
        return original_replace(source, target)

    monkeypatch.setattr(store.os, "replace", failing_replace)
    def failing_unlink(self, *args, **kwargs):
        if self.name == "engine_state.lock":
            return original_unlink(self, *args, **kwargs)
        raise OSError("cleanup failure")
    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
    assert read_metadata(tmp_path).revision == baseline.revision
    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
    monkeypatch.setattr(store.os, "replace", original_replace)
    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1
\`\`\`

This test does not assert \`not (tmp_path / "engine_state.lock").exists()\`; it allows the target lock unlink and verifies subsequent acquisition succeeds after restoring normal cleanup.

\`test_concurrent_writers_publish_complete_monotonic_snapshots\`, lines 1968-1978, is thread concurrency in one process, not multiprocess locking:

\`\`\`python
def test_concurrent_writers_publish_complete_monotonic_snapshots(tmp_path):
    def publish(value):
        return save_snapshot({"value": value}, tmp_path, "same", writer=str(value)).revision

    with ThreadPoolExecutor(max_workers=4) as pool:
        revisions = sorted(pool.map(publish, range(8)))

    state, metadata = load_snapshot(tmp_path, "same")
    assert revisions == list(range(1, 9))
    assert metadata.revision == 8
    assert state["value"] in range(8)
\`\`\`

### Snapshot generation cleanup tests (not lock-path assertions)

\`C:\Temp\Contextor_Repo\tests\test_live_state_store.py::test_split_lineage_failed_metadata_commit_cleans_new_generation\`, lines 1656-1758, forces metadata replacement to raise, checks baseline revision remains and the revision-2 generation files are removed. It does not inspect \`engine_state.lock\`.

\`\`\`python
def test_split_lineage_failed_metadata_commit_cleans_new_generation(
    tmp_path,
    monkeypatch,
):
    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    baseline = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    candidate = state.clone_for_update()

    original_replace = (
        store.os.replace
    )

    def fail_metadata_replace(
        source,
        target,
    ):
        if (
            Path(
                target
            ).name
            == "engine_state.meta.json"
        ):
            raise RuntimeError(
                "synthetic metadata commit failure"
            )

        return original_replace(
            source,
            target,
        )

    monkeypatch.setattr(
        store.os,
        "replace",
        fail_metadata_replace,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "^synthetic metadata commit failure$"
        ),
    ):
        save_snapshot(
            candidate,
            tmp_path,
            "sid",
            exact_revision=2,
            file_state_payload={
                "_meta": {
                    "state_id": "sid",
                    "revision": 2,
                },
                "files": {},
            },
        )

    assert (
        read_metadata(
            tmp_path
        ).revision
        == baseline.revision
    )

    assert not list(
        tmp_path.glob(
            "engine_state.r2.*.pkl"
        )
    )
    assert not list(
        tmp_path.glob(
            "file_state.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_manifest.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_source.r2.*.pkl"
        )
    )
\`\`\`

\`C:\Temp\Contextor_Repo\tests\test_live_state_store.py::test_split_lineage_reuse_failure_preserves_previous_chunk\`, lines 1420-1567, is the related metadata-commit failure case when an old lineage chunk is reused. Its assertions retain that previous chunk and the revision-1 metadata while removing revision-2 generated files. It does not inspect \`engine_state.lock\`. Complete implementation is in the current source range 1420-1567.

### Other lock lifecycle tests (different lock paths/protocols)

\`C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py::test_cross_process_os_lock_and_process_death_recovery\`, lines 399-473, tests the full-analysis coordinator's OS lock, not \`engine_state.lock\`. The complete function is:

\`\`\`python
def test_cross_process_os_lock_and_process_death_recovery(tmp_path: Path, isolated_dirs):
    """
    Requirement 11: Cross-process exclusion and OS-held file lock auto-recovery on process termination.
    Proves:
    - Process A blocks Process B on same repo.
    - Process A terminated without release -> Process B automatically acquires without lock file unlinking.
    - Process C on different repo acquires concurrently.
    """
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    ctx = multiprocessing.get_context("spawn")
    ready_a = ctx.Event()
    results_a = ctx.Queue()
    results_b1 = ctx.Queue()
    results_b2 = ctx.Queue()
    results_c = ctx.Queue()

    # 1. Process A acquires repo1
    p_a = ctx.Process(
        target=_worker_os_lock_hold,
        args=(str(repo1), "proc_a", ready_a, results_a, 15.0),
    )
    p_a.start()

    try:
        assert ready_a.wait(timeout=15.0), "Process A produced no acquisition diagnostic"
        res_a = results_a.get(timeout=2.0)
        assert res_a["status"] == "acquired", f"Process A failed to acquire repo1: {res_a}"

        # 2. Process B attempts repo1 while A is alive -> busy
        p_b1 = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo1), "proc_b1", 0.5, results_b1),
        )
        p_b1.start()
        p_b1.join(timeout=3.0)

        res_b1 = results_b1.get(timeout=2.0)
        assert res_b1["status"] == "busy", f"Process B1 was not blocked: {res_b1}"

        # 3. Process C attempts repo2 (different repo) concurrently -> succeeds immediately
        p_c = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo2), "proc_c", 1.0, results_c),
        )
        p_c.start()
        p_c.join(timeout=3.0)

        res_c = results_c.get(timeout=2.0)
        assert res_c["status"] == "ok", f"Process C on different repo failed: {res_c}"

        # 4. Terminate Process A WITHOUT clean release (simulates sudden process death/crash)
        p_a.terminate()
        p_a.join(timeout=3.0)

        # 5. Process B attempts repo1 now -> OS automatically unlocked, acquires without unlinking lock file!
        p_b2 = ctx.Process(
            target=_worker_try_acquire,
            args=(str(repo1), "proc_b2", 2.0, results_b2),
        )
        p_b2.start()
        p_b2.join(timeout=3.0)

        res_b2 = results_b2.get(timeout=2.0)
        assert res_b2["status"] == "ok", f"Process B2 failed to acquire after process death: {res_b2}"

        # Ensure lock file was NOT deleted (file existence is not ownership)
        lock_file, _, _ = _resolve_lock_path(repo1)
        assert lock_file.exists()
    finally:
        if p_a.is_alive():
            p_a.terminate()
\`\`\`

The test's \`_resolve_lock_path(repo1)\` names \`runtime/full_analysis.lock\` at \`C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:406\`. The actual OS admission lock is a separate sibling \`canonical_writer.admission.lock\` (coordinator line 154). The test's persistent-file assertion is not a requirement for \`engine_state.lock\`.

Other adjacent coordinator tests are also on \`acquire_full_analysis\`, not the snapshot store:

- \`test_in_process_non_reentrant_lock_exclusion\`, lines 878-890: holds one full-analysis lease; same-thread nested acquisition with timeout 0.2 raises \`FullAnalysisBusyError\`; releases in \`finally\`.
- \`test_admission_timeout_does_not_leak_locks\`, lines 1015-1060: spawn-process holder, waiting full-analysis thread, live-mutation acquisition with timeout 0.05 raises \`FullAnalysisBusyError\`; terminates holder, lets waiting thread acquire/release, then reacquires and releases.
- \`test_admission_cancellation_does_not_leak_locks\`, lines 1063-1108: spawn-process holder, waiting full-analysis thread, cancellation predicate raises \`AnalysisCancelled\`; cleanup terminates holder, releases waiter, and then reacquires/releases.
- \`test_live_state_consistency::test_concurrent_update\`, lines 364-387, exercises two same-process \`engine.update_file\` threads and contains a Windows \`msvcrt.locking\` comment; it does not call \`save_snapshot\` or inspect \`engine_state.lock\`.

## PLATFORM_CONTRACT

### Declared configuration

\`C:\Temp\Contextor_Repo\pyproject.toml\`:

- \`requires-python = ">=3.10"\` (line 6).
- Ruff target is \`py310\` (line 31).
- No \`classifiers\`, \`platforms\`, or supported-OS matrix is declared in this file.
- \`C:\Temp\Contextor_Repo\requirements.txt:7\` says Python 3.10 or newer.

\`C:\Temp\Contextor_Repo\README.md\` documents the Windows launcher at lines 461-465 and identifies Python 3.10+ at lines 498-520. The inspected project metadata and README do not publish an exhaustive supported-operating-system list. Therefore:
- Windows is explicitly documented.
- POSIX locking branches exist in source.
- Official support for a particular POSIX OS (including macOS) is not specified by the inspected project metadata.

### Current target store protocol

\`store.py\` uses \`os.open(... O_CREAT | O_EXCL | O_WRONLY)\`, filesystem mtime and pathname deletion. It contains no \`msvcrt.locking\` or \`fcntl.flock\` call. Its descriptor is not OS-locked. The file named \`engine_state.lock\` is used as an age-reclaimed existence sentinel.

### Existing project-local OS-lock implementations

Complete call-site inventory from Git source search; each pair is in project code and uses distinct lock paths/owners rather than \`engine_state.lock\`:

| Absolute file | Symbol / role | Windows call lines | POSIX call lines |
|---|---|---:|---:|
| \`C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py\` | \`_try_lock_fd\` / \`_unlock_fd\` | 235-239, 263-267 | 247-251, 271-274 |
| \`C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py\` | \`_DomainFileLock._acquire_os_lock\` / \`_close\` | 796-800, 814-818 | 801-805, 819-822 |
| \`C:\Temp\Contextor_Repo\contextor\core\reporting_engine\persistent_registry.py\` | \`PersistentIdentityRegistry._lock\` / \`_unlock\` | 48-55, 66-73 | 56-62, 74-80 |
| \`C:\Temp\Contextor_Repo\contextor\core\runtime_trace.py\` | \`_AuthorityFileLock\` | 676-679, 696-699 | 680-683, 700-703 |
| \`C:\Temp\Contextor_Repo\contextor\core\runtime_trace.py\` | \`_TraceAppendFileLock\` | 725-732, 754-761 | 733-740, 762-768 |
| \`C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py\` | \`_BackendControlLock\` | 430-434, 480-484 | 439-443, 489-492 |
| \`C:\Temp\Contextor_Repo\contextor\mcp_backend_secret.py\` | \`_BackendSecretLock\` | 728-732, 778-782 | 737-741, 787-790 |
| \`C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py\` | \`_BackendLifetimeLock\` | 765-769, 815-819 | 774-778, 824-827 |

The target-adjacent coordinator excerpt shows its branch, exception handling and release path:

Source: \`C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:228-276\`

\`\`\`python
def _try_lock_fd(fd: int) -> bool:
    os.lseek(fd, 0, os.SEEK_SET)

    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(
                fd,
                msvcrt.LK_NBLCK,
                1,
            )
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(
            fd,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
        return True
    except BlockingIOError:
        return False


def _unlock_fd(fd: int) -> None:
    try:
        os.lseek(fd, 0, os.SEEK_SET)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                fd,
                msvcrt.LK_UNLCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
    finally:
        os.close(fd)
\`\`\`

This coordinator's \`_prepare_lock_fd\` opens/creates the stable file and ensures a one-byte region exists (lines 208-225). \`_canonical_writer_admission\` obtains a process-local lock, opens sibling \`canonical_writer.admission.lock\`, polls \`_try_lock_fd\` until acquired/cancelled/timed out, yields, then unlocks/closes in nested \`finally\` blocks (lines 122-205). This is a distinct coordinator path.

Other wrapper locations are exact in the inventory table. \`rg\` found no production/test use of third-party names \`FileLock\`, \`portalocker\`, or \`fasteners\`; those dependencies also do not appear in \`pyproject.toml\` or \`requirements.txt\`. The listed lock wrappers are separate local classes/helpers, not a common abstraction called by \`store.py\`.

## REENTRANCY_EVIDENCE

- \`_acquire_lock\` has one call expression in production source: \`save_snapshot\` line 1499.
- \`save_snapshot\` contains no recursive call to itself. The in-module migration wrapper at \`store.py:2297\` calls \`save_snapshot\` once after loading the legacy snapshot.
- The direct lock caller inventory found no callee or second acquisition of the same \`engine_state.lock\` inside \`save_snapshot\`'s persistence routine. The nested helpers in that routine do not call \`_acquire_lock\` according to the complete source-text inventory.
- The local lock is not a reentrant OS lock: it is an \`O_EXCL\` file-creation loop. This statement describes the current implementation; it does not infer behavior for calls in separate processes that use different cache directories.
- The other full-analysis coordinator's same-thread non-reentrancy regression is \`test_in_process_non_reentrant_lock_exclusion\` at \`tests/test_full_analysis_coordination.py:878-890\`; it exercises a different lock/path and is not evidence about snapshot-lock recursion.

## COMPATIBILITY_CONSTRAINTS

- \`engine_state.lock\` currently is expected by implementation to be removed on ordinary completion because \`save_snapshot\` calls \`lock_file.unlink()\` after \`os.close(lock_fd)\`. This is an attempted cleanup, not an unconditional guarantee: \`OSError\` from unlink is caught and ignored.
- No inspected test or documentation states a standalone public postcondition that the file must disappear after success. The normal roundtrip test indirectly requires subsequent save acquisition to work. The cleanup regression explicitly allows unlink of \`engine_state.lock\` and verifies a later save succeeds; it does not assert path absence.
- The full-analysis process-death regression explicitly preserves a different lock file (\`full_analysis.lock\`) and asserts it still exists after process A is terminated; its tested OS lock is released by process death, not by deleting that file.
- The snapshot store and OS-lock helpers do not share a lock owner, path, API, descriptor contract or cleanup routine in current source.
- The project Python floor is 3.10. OS support is not specified as an exhaustive packaging matrix; Windows is documented, and several source modules branch between Windows \`msvcrt\` and POSIX \`fcntl\`.
- No test was run for this read-only discovery.

## FILES_CHANGED=NONE

No production file, test, configuration or documentation file was changed.

## ACTUAL_DIFF=NONE

