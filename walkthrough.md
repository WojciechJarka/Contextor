# CONTEXTOR_B0G2B_DESKTOP_MCP_PARITY_HARNESS_DISCOVERY

## FILES_CHANGED

- C:\Temp\Contextor_Repo\walkthrough.md — jedyny plik raportowy nadpisany w tym zadaniu.
- Brak zmian w production, tests i source docs.

## ACTUAL_DIFF

DIFFS=NONE dla source/test/docs. walkthrough.md jest wyłącznie raportem.

## SOURCE_IDENTITY

- Repo: C:\Temp\Contextor_Repo
- CURRENT_HEAD=f9868a364e4ea6884d383c9ac106b0e9e35be51b
- Pre-report git status, staged diff i unstaged diff były puste.
- Contextor responses dla bieżących implementacji: canonical_state=fresh, workspace_sync=verified, canonical_revision=349, provenance=live.
- get_live_events przed i po retrieval: revision/latest_revision=349, continuity=continuous, resync_required=false, events=[]; activity_epoch=a97e66962cfb4bcbb9cb0104d3f0c1af. latest_seq 372→452 jest aktywnością dziennika, bez canonical revision/event.
- Użyto Contextor implementation, source-range, lineage/call-context i blast-radius narzędzi. Static consumers są dowodem potwierdzonych statycznych wywołań, nie braku dynamicznych.
- Bez testów, analizy projektu, publish, zmian source ani restartu.

## DESKTOP_ENTRYPOINT_AND_TASK_SEAM

DIRECT_EVIDENCE — pełny ContextorGUI.analyze, gui.py:1265–1504: metoda pobiera repo path, best-effort latest_seq z LIVE, definiuje task wywołujący produkcyjne run_full_analysis_exclusive(owner="desktop_analysis"), i podaje task do run_with_progress.

~~~python
def task(log=None, progress_callback=None):
    errors, analysis_result = run_full_analysis_exclusive(
        path,
        owner="desktop_analysis",
        log=log,
        progress_callback=progress_callback,
        is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
    )
    return errors, analysis_result

self._full_analysis_done = run_with_progress(
    self.root, self.progress_bar, task,
    on_success=on_success, on_error=on_error,
    buttons=self._busy_buttons(), log_box=self.log_box,
    cpu_indicator=self.cpu_indicator, stop_button=self.stop_btn,
    operation_name="Repository analysis",
)
~~~

run_with_progress (progress_widget.py:132–315) wykonuje task w worker thread, dopasowuje log/progress_callback przez inspect.signature, ustawia result=task(**kwargs), a UI callback planuje przez root.after. Testowy scheduler może przechwycić real task i wywołać bez uruchamiania tego thread/Tk callbacków. Nie wywołując on_success, nie uruchamia drugiego Desktop watcher/recovery callbacka.

Istniejący tests\test_gui_live_startup.py::_make_analysis_controller (661–680) tworzy ContextorGUI.__new__, MockTkRoot, fake vars/progress, recovery maps, watcher MagicMock i _busy_buttons. Istniejący test full-analysis w tym pliku podstawia run_full_analysis_exclusive; sprawdza UI/recovery, nie realną semantykę.

GUI layer/single źródła zostały pobrane kompletnie: ContextorGUI.analyze_layer (gui.py:2012–2073) task woła ContextorFacade.analyze_layer; ContextorGUI.analyze_single (2075–2145) task woła ContextorFacade.analyze_single_file z publication_result. Obie ścieżki schedule’uje run_with_progress.

## MCP_ENTRYPOINT_AND_JOB_SEAM

DIRECT_EVIDENCE — publiczny tool analyze_project (mcp/tools/analyze_project.py:7–18):

~~~python
async def analyze_project(repo_path: str, exclude_paths: list[str] | None = None) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    return json.dumps(
        analysis_jobs._start_analysis_job(
            "project", root, exclude_paths=exclude_paths
        ),
        indent=2,
    )
~~~

_start_analysis_job (analysis_jobs.py:439–475) serializuje queued job, zapisuje job, tworzy daemon Thread uruchamiający asyncio.run(_execute_analysis_job(...)), reużywa aktywny job dla tego repo i zwraca job_id. _run_analysis_worker (224–300) działa przez asyncio.to_thread pod _analysis_lock, ustawia tymczasowo cache/registry env i dla project woła ten sam run_full_analysis_exclusive z owner="mcp_analysis"; dla layer/single woła ContextorFacade.analyze_layer/analyze_single_file.

Pełny _execute_analysis_job (303–436) odczytuje publish status/revision. Po success reloaduje MCP engine cache i sprawdza canonical revision; dla publish status innego niż success czyści cache. Job może mimo tego mieć status completed z komunikatem o publish status. Completed nie jest samodzielnym potwierdzeniem publish.

get_analysis_status(repo_path, job_id=...) czyta konkretny job; bez jawnego ID może zwrócić ambiguous_job. Aktualny test tests\test_mcp_regressions.py::test_analysis_endpoint_returns_reusable_job_and_pollable_completion (944–992) wywołuje realny publiczny mcp_server.analyze_project.fn, sprawdza job ID/status, a następnie Thread.join(timeout=5). Podstawia jednak _run_analysis_worker i engine, więc nie uruchamia rzeczywistej analizy.

Granica: .fn wywołuje prawdziwy FastMCP handler, ale pomija aktywną sesję/transport MCP.

## COMPLETE_CANONICAL_CAPTURE_CONTRACT

ContextorFacade.analyze_project (istotne zakresy facade.py:558–1314) wspólnie wywołuje _analysis_filters/index_repository, korzysta z graph hard_edges, soft_edges, metrics, buduje pełny RepositoryAnalysisState, zapisuje snapshot, publikuje opcjonalnie i zwraca errors/analysis_result. analysis_result zwracany przez fasadę nie jest kompletnym canonical RepositoryAnalysisState.

RepositoryAnalysisState (state_manager.py:83–168) obejmuje: modules, artifacts, reexports, dependency graph, artifact consumption/state, layer info, metrics, FileState, parse freshness, syntax diagnostics/state, module usages/manifest, lineage facts/state/version/indexes/query-state/completeness, topology/cache analytics/states, cycles/state, collision facts/collisions/state, dependency matrix/state, shared clusters/state, trie/package root. Dynamiczne revision/state_id/provenance/resync_required też istnieją; clone_for_update robi top-level shallow COW.

Snapshot write: analyze_project wylicza current metadata revision + 1, buduje FileState payload i wywołuje:

~~~python
meta = save_engine_state(
    state, cache_dir, datestamp,
    writer=writer,
    repo_id=registry.repo_id,
    root_path=path,
    exact_revision=target_revision,
    file_state_payload=file_state_payload,
)
~~~

writer to mcp dla owner zawierającego mcp, w przeciwnym razie desktop. state_id to datestamp YYYYMMDD_HHMMSS. save_snapshot (store.py:1507–1918) przypisuje state_id/revision, waliduje repo identity/root, zapisuje versioned pickle, osobny versioned FileState JSON i metadata wskaźnika. Dla exact_revision wymaga kolejnego revision. Snapshot, FileState i metadata są flush/fsync; metadata jest zatwierdzana przez os.replace.

FileStateManager.build_payload zapisuje _meta.state_id/revision oraz mapę plików; FileState ma mtime_ns/size/sha256. _load uznaje FileState za trusted tylko gdy metadata wskazuje zgodną generację.

Read capture: read_metadata odczytuje metadata; load_engine_state przekazuje state_id oraz expected_repo_id/root do load_snapshot. Pełny loader store.py:1970–2415 pobrano w siedmiu ciągłych zakresach bez truncation. Odrzuca mismatch state ID/repo ID/root, sprawdza current-schema embedded metadata, revision i split-lineage source domain, ustawia state_id/revision/provenance="snapshot" i normalizuje stare pola.

LiveStateClient.snapshot zwraca pełny LIVE state przez request("snapshot"). Disk metadata + load_engine_state zwraca pełny persisted/hydrated state z identity checks. Pierwszy wynik trzeba skopiować przed drugim runem: COW jest płytki na top-level, a obecny _build_full_static_state zwraca engine.state bez deepcopy.

READ SIDE EFFECTS: resolve_authoritative_repository_state wywołuje migrate_legacy_snapshot przed LIVE/disk read. Nie jest pasywnym disk readerem. load_snapshot może zapisać lineage validation cache w split-lineage path. Capture należy ograniczyć do isolated fixture.

## CANONICAL_FAMILY_COMPARISON_CONTRACT

Istniejący _assert_full_parity w tests\test_completeness_freshness_parity_proof.py:55–115 porównuje:

Pełna literalna implementacja comparatora znajduje się w VERIFIED_COMPLETE_LITERAL_SOURCE_ADDENDUM poniżej.

Graph i metrics są sprawdzane tylko, gdy oracle field nie jest None. Helper nie porównuje pełnych Module objects/imports/IDs/paths, wszystkich references, lineage, freshness/ambiguity/completeness markers, file-state, cycles/SCC, topology/cached analytics, dependency matrix, clusters, state_id/revision/provenance/resync_required.

Normalization evidence:

- Job IDs/timestamps, LIVE activity sequence i transport envelopes leżą poza RepositoryAnalysisState.
- Revision legalnie rośnie na kolejnym save; spójność metadata/state/FileState pozostaje wymagana.
- mtime_ns jest timestampem; size/SHA-256/path coverage nie są timestampami.
- state_id pochodzi z datestamp i wiąże FileState generation; nie jest job/transport ID. Brak kontraktu na jego cross-run pominięcie.
- Snapshot metadata writer różni się desktop/mcp; nie ma kontraktu, że różnica jest dozwolona.
- provenance jest częścią żądanego canonical source provenance; brak normalizatora.
- Brak istniejącej allowlisty wyłączeń dla semantycznych state fields. Nie pomijać pól tylko dlatego, że aktualnie różnią się.

## EXISTING_PARITY_TEST_HELPERS

- tests\test_completeness_freshness_parity_proof.py::_build_full_static_state: real ContextorFacade.analyze_project + hydrate_repository_engine; facade oracle, bez deepcopy.
- test_full_canonical_parity_import_and_graph (856–886), test_incremental_signature_change_matches_full_oracle (889–921), test_package_init_star_visibility_changes_match_full_oracle (2592–2680): direct engine kontra fresh facade full oracle.
- tests\test_full_analysis_coordination.py: lease coordination/timeout, bez full-state GUI/MCP equality.
- tests\test_live_desktop_integration.py: GUI publish/watcher; znaleziony test full path podstawia fake analyzer.
- tests\test_gui_live_startup.py: headless GUI helper, ale istniejący semantic path testuje przez mock.
- tests\test_mcp_regressions.py: fake worker job test i fake remote MCP update client.
- tests\test_live_state_ipc.py: watcher test z fake updater; real adapter test direct-dispatchuje server.
- Żaden nie łączy publicznych Desktop i MCP entrypointów w jeden full-state comparison.

## HEADLESS_GUI_TEST_FEASIBILITY

CODE_PATH_PROVED: ContextorGUI.analyze ma real task oddzielny od run_with_progress. _make_analysis_controller tworzy headless controller. Podstawienie wyłącznie scheduler seam pozwala uruchomić real task bez Tk/event loop/thread scheduler oraz bez on_success watcher.

CONDITIONAL: metoda przed task robi read-only connect/get_events; connect nie uruchamia LIVE. Nie wykonano tej ścieżki runtime.

## ASYNC_MCP_JOB_TEST_FEASIBILITY

Publiczny tool .fn tworzy durable job; explicit job_id jest deterministyczny; worker jest threadem z bounded join test seam. Nie istnieje gotowy real-worker wait helper. .fn omija protokół MCP transport.

## LIVE_AND_CACHE_ISOLATION

tests\conftest.py::isolated_dirs ustawia cache/state/output/registry pod tmp_path; sample_repo tworzy tmp_path/repo. MCP worker chwilowo używa _mcp_cache_root(root), facade repo_cache_dir i repository identity. Dla identycznej konfiguracji Desktop używa braku additional_excludes, MCP musi mieć exclude_paths=None; inne excludes zmieniają wynik.

connect(root) nie startuje LIVE. Istniejący live_server fixture uruchamia in-process server z fake state/updater. Real updater/persister test istnieje osobno, lecz direct-dispatchuje server. Nie ma fixture łączącego real updater, endpoint/repo identity oraz oba publiczne update transporty.

Pełne Desktop i MCP analizy muszą przebiegać sekwencyjnie: wspólny repository lease, MCP dodatkowo _analysis_lock i job deduplication.

## DESKTOP_WATCHER_UPDATE_SEAM

DesktopLiveWatcher.__init__ nie startuje thread/observer. _enqueue_path(path, wake=False) i synchroniczne poll_once tworzą seam bez startowania watchera. poll_once przechodzi przez checks LIVE, a następnie submit_update_file(origin="desktop_watcher", trace_op, idempotency_key); _poll_inflight_updates odpytuje mutation_status i rozpoznaje completed statuses UPDATED/DELETED/UNCHANGED/RECOVERED/SYNTAX_ERROR.

Literal admission, watcher.py:908–963:

~~~python
response = self._admit_recovery_action(
    lambda: self.client.submit_update_file(
        path,
        origin="desktop_watcher",
        trace_op=pending_intent.trace_op,
        idempotency_key=pending_intent.idempotency_key,
    )
)
job_id = response.get("job_id") if isinstance(response, dict) else None
if (
    not isinstance(response, dict)
    or response.get("status") != "accepted"
    or response.get("accepted") is not True
    or not isinstance(job_id, str)
    or not job_id
):
    deferred.append(path)
    continue
self._pending_intents.pop(path, None)
self._inflight_updates[job_id] = _WatcherMutationJob(...)
~~~

tests\test_live_state_ipc.py::_poll_until_reconciled bounded-polluje poll_once(timeout=10). Obecny watcher test ma fake updater; potwierdza transport, nie canonical semantic parity.

## MCP_UPDATE_SEAM

Publiczny contextor\mcp\tools\update_file.py::update_file najpierw pobiera engine. Z aktywnym LIVE wywołuje synchroniczny live_client.update_file(target_file, origin="mcp"), potem odświeża cache. Bez LIVE przechodzi do odrębnej local candidate/persistence ścieżki. Porównywać można wspólny LIVE branch.

Desktop async submit i MCP sync update prowadzą do CanonicalLiveServer._execute_update_file. Server klonuje state, uruchamia updater na kandydacie, waliduje revision, persystuje, a następnie atomowo publikuje state. _repository_updater konstruuje IncrementalAnalysisEngine i wywołuje update_file.

IncrementalAnalysisEngine.update_file(self, file_path: str) -> IncrementalUpdateResult (pełny engine.py:453–734) ma early UNCHANGED przed parse, oddzielny parsed no-op UNCHANGED/RECOVERED oraz parse/commit paths DELETED, SYNTAX_ERROR, UPDATED/RECOVERED.

test_mcp_update_file_live_branch_delegates_without_local_persistence używa FakeLiveClient i preloaded result. test_real_repository_adapter_two_successive_updates_are_exact_successors używa real updater/persister, ale omija public transports przez direct server dispatch. Żaden nie dowodzi public-route parity.

## FULL_VS_INCREMENTAL_ORACLE

Obecny direct engine.update_file kontra _build_full_static_state oracle nie wywołuje watcher/MCP transportów. Przy LIVE incremental oba transporty dochodzą do _execute_update_file/_repository_updater; bez LIVE MCP ma inną local persistence ścieżkę.

Nie istnieje gotowy reset/clone seam dla dwóch równoważnych initial LIVE states. Dwa oddzielne tmp roots zmieniają absolute_path i repository identity; helper nie określa root-remapping contractu. To jest brak istniejącej fixture, nie dowód niemożliwości produkcyjnych wywołań.

## EXACT_SOURCE_FRAGMENTS

Aktualny Contextor source retrieval bez truncation:

- C:\Temp\Contextor_Repo\contextor\ui\gui.py: analyze 1265–1504, analyze_layer 2012–2073, analyze_single 2075–2145.
- C:\Temp\Contextor_Repo\contextor\ui\progress_widget.py: run_with_progress 132–315.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py: run_full_analysis_exclusive 41–128.
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py: analyze_project signature/materialization/persistence/outcome 558–1314; _analysis_filters 192–233; layer/single owners 1314–1901.
- C:\Temp\Contextor_Repo\contextor\mcp\tools\analyze_project.py, analyze_layer.py, analyze_single_file.py; analysis_jobs.py 224–475; tools\get_analysis_status.py 14–147.
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py: RepositoryAnalysisState 83–168, save/load engine state 489–536, FileStateManager.
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py: save_snapshot 1507–1918, read_metadata 1411–1442, load_snapshot 1970–2415.
- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py: snapshot/update client methods and _execute_update_file 1874–2148.
- C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py: __init__ 111–158, _enqueue_path 441–451, _poll_inflight_updates 592–665, poll_once; full body retrieved in adjacent ranges 667–973 across discovery continuation.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py: _repository_updater 1108–1150.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py: full update_file 453–734.
- Relevant test helpers/tests were fetched completely from files listed under EXISTING_PARITY_TEST_HELPERS.

Jedno początkowe błędne file_path dla DesktopLiveWatcher zwróciło contract error. Contextor podał kanoniczną ścieżkę core\live_state\watcher.py; błędne preview nie jest źródłem kodu.

## MINIMAL_FUTURE_TEST_FILE_SCOPE

Obecnie zaobserwowane fixture/seam owners:

- C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py — canonical comparator/full oracle/direct incremental.
- C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py — headless GUI controller.
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py — public .fn async job/status i MCP update adapter.
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py — watcher polling, LIVE fixture, real adapter direct-dispatch.
- C:\Temp\Contextor_Repo\tests\conftest.py — tmp repo i env isolation.

Lista identyfikuje istniejących właścicieli seamów, nie zalecany edit set. Nie wskazano koniecznych production edits.

## BLOCKERS

- Brak obecnego real GUI-task kontra real MCP-job full-state parity test.
- Brak wspólnego real-updater fixture dla watcher i public MCP update: obecne testy używają fake updater/client albo omijają publiczne adaptery.
- Nieustalony kontrakt identity/root remapping dla osobnych tmp roots.
- Nieustalona allowlista normalizacji state_id, writer, provenance i absolute paths.
- Są to braki gotowego test fixture/contractu; nie dowodzą semantycznej rozbieżności ani niemożliwości entrypointów. Wspólny full-analysis owner jest potwierdzony.

## LIVE_REVISION_BEFORE_AFTER

Przed: 349. Po: 349. Canonical events po 349: 0; continuity=continuous; resync_required=false. Żadna mutacja/analiza nie została wykonana.

## WORKSPACE_SYNC_POSTCHECK

Pobrane source/teste miały workspace_sync=verified na revision 349. HEAD bez zmiany, pre-report worktree clean. walkthrough.md nie jest Python source analizowany przez Contextor.

## RESYNC_REQUIRED

false; LIVE latest_revision=349, continuity=continuous.

## RESTART_REQUIRED

NO. Kod produkcyjny nie został zmieniony; restartu nie wykonywano.

## FINAL_VERDICT

B0G2B_PARITY_HARNESS_READY

Źródłowe call chains, wspólny full owner, canonical capture contract i istniejące test seamy ustalono. To gotowość materiału do projektu audytora, nie certyfikacja aktualnego GUI/MCP parity; gate testowy jeszcze nie istnieje.

### Literal complete shared full owner — full_analysis_coordinator.py:41–128

~~~python
def run_full_analysis_exclusive(
    path: str | Path,
    *,
    owner: str = "desktop_analysis",
    analysis_fn: Callable[..., Any] | None = None,
    log: Callable[[str], None] | None = None,
    progress_callback: Any = None,
    additional_excludes: list[str] | None = None,
    timeout: float | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute full repository analysis while holding an exclusive repository lease.
    Guarantees single-writer execution across Desktop, MCP, and CLI.
    """
    repo = str(Path(path).resolve())
    full_started = time.monotonic()
    lease_wait_started = full_started
    lease = acquire_full_analysis(
        path,
        owner=owner,
        writer_kind="full_analysis",
        timeout=timeout,
        is_cancelled=is_cancelled,
        log=log,
    )
    try:
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_LEASE_ACQUIRED",
            owner=owner,
            repo=repo,
            wait_ms=(time.monotonic() - lease_wait_started) * 1000.0,
            timing_semantics="critical_path_lease_wait",
        )
        if analysis_fn is not None:
            analysis_started = time.monotonic()
            analysis_result = analysis_fn(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        else:
            from contextor.core.api.facade import ContextorFacade

            analysis_started = time.monotonic()
            analysis_result = ContextorFacade.analyze_project(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        analysis_ms = (time.monotonic() - analysis_started) * 1000.0
        total_before_release_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_BODY_END",
            owner=owner,
            repo=repo,
            analysis_ms=analysis_ms,
            total_before_release_ms=total_before_release_ms,
            elapsed_ms=analysis_ms,
            timing_semantics="critical_path_analysis_body",
            result=(
                f"analysis_ms={analysis_ms:.3f};"
                f"total_before_release_ms={total_before_release_ms:.3f}"
            ),
        )
        return analysis_result
    finally:
        release_full_analysis(lease)
        total_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_END",
            owner=owner,
            repo=repo,
            total_ms=total_ms,
            elapsed_ms=total_ms,
            timing_semantics="critical_path_total",
            result=f"total_ms={total_ms:.3f}",
        )
~~~

### Literal MCP job scheduling and worker call path

~~~python
def _start_analysis_job(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
) -> dict:
    repo_key = str(root)
    with _analysis_job_lock:
        active_id = _analysis_jobs_by_repo.get(repo_key)
        active_task = _analysis_tasks.get(active_id) if active_id else None
        if active_id and active_task is not None and active_task.is_alive():
            existing = _read_analysis_job(root, active_id)
            if existing is not None:
                return _public_job(existing, reused=True)
        job_id = uuid4().hex
        job = {
            "job_id": job_id, "operation": operation, "repo_path": repo_key,
            "target": str(target) if target is not None else None,
            "exclude_paths": list(exclude_paths or []), "status": "queued",
            "created_at": _utc_now(), "started_at": None, "completed_at": None,
            "message": "Analysis accepted.", "error": None,
            "live_publish_status": (
                "pending" if operation == "project" else "not_applicable"
            ),
            "live_publish_revision": None, "live_publish_warning": None,
            "owner_pid": os.getpid(),
        }
        _write_analysis_job(root, job)

        def run_job() -> None:
            asyncio.run(_execute_analysis_job(root, job, target, exclude_paths))

        task = threading.Thread(
            target=run_job, name=f"contextor-analysis-{job_id}", daemon=True
        )
        _analysis_jobs_by_repo[repo_key] = job_id
        _analysis_tasks[job_id] = task
        task.start()
        return _public_job(job)
~~~

~~~python
async def _run_analysis_worker(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
    log=None,
) -> dict:
    effective_log = log or _stderr_log

    def run() -> dict:
        with _analysis_lock:
            previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
            previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
            os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
            if previous_registry is None:
                os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = str(registry_dir(root))
            try:
                if operation == "project":
                    _, result = run_full_analysis_exclusive(
                        str(root),
                        owner="mcp_analysis",
                        log=effective_log,
                        progress_callback=_analysis_progress_callback,
                        additional_excludes=exclude_paths,
                        is_cancelled=_analysis_shutdown_requested,
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                    skipped_files = (getattr(result, "summary_data", {}) or {}).get(
                        "skipped_files", []
                    )
                    if not isinstance(skipped_files, list):
                        skipped_files = []
                    return {
                        "skipped_python_files": skipped_files,
                        "live_publish_status": getattr(
                            result, "live_publish_status", "not_attempted"
                        ),
                        "live_publish_revision": getattr(
                            result, "live_publish_revision", None
                        ),
                        "live_publish_warning": getattr(
                            result, "live_publish_warning", None
                        ),
                    }
                if operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root), str(target), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target), str(root), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
                return {}
            finally:
                if previous_cache is None:
                    os.environ.pop("CONTEXTOR_CACHE_DIR", None)
                else:
                    os.environ["CONTEXTOR_CACHE_DIR"] = previous_cache
                if previous_registry is None:
                    os.environ.pop("CONTEXTOR_MCP_PROCESS_REGISTRY", None)
                else:
                    os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = previous_registry

    return await asyncio.to_thread(run)
~~~

### Literal public scoped facade wrappers

~~~python
@staticmethod
def analyze_layer(
    root_dir: str,
    layer_dir: str,
    log=None,
    progress_callback=None,
    additional_excludes: list[str] | None = None,
) -> str:
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )

    root_resolved, _ = _resolve_repository_target(
        root_dir, layer_dir, target_kind="layer"
    )
    lease = acquire_full_analysis(
        root_resolved,
        owner="scoped_layer_analysis",
        writer_kind="scoped_analysis",
        timeout=10.0,
    )
    try:
        return ContextorFacade._analyze_layer_uncoordinated(
            root_dir,
            layer_dir,
            log=log,
            progress_callback=progress_callback,
            additional_excludes=additional_excludes,
        )
    finally:
        release_full_analysis(lease)
~~~

~~~python
@staticmethod
def analyze_single_file(
    file_path: str,
    repo_root: str,
    log=None,
    progress_callback=None,
    additional_excludes: list[str] | None = None,
    publication_result: dict[str, Any] | None = None,
) -> str:
    if publication_result is not None:
        publication_result.update(status="not_attempted", revision=None, warning=None)
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )
    root_resolved, target = _resolve_repository_target(
        repo_root, file_path, target_kind="file"
    )
    if target.suffix.lower() != ".py":
        raise ValueError(f"Selected file is not a Python file: {target}")
    lease = acquire_full_analysis(
        root_resolved,
        owner="scoped_single_file_analysis",
        writer_kind="scoped_analysis",
        timeout=10.0,
    )
    try:
        return ContextorFacade._analyze_single_file_uncoordinated(
            file_path,
            repo_root,
            log=log,
            progress_callback=progress_callback,
            additional_excludes=additional_excludes,
            publication_result=publication_result,
        )
    finally:
        release_full_analysis(lease)
~~~

### Literal existing canonical comparison helper

~~~python
def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state: RepositoryAnalysisState):
    """Asserts full canonical parity across all plan-controlled families with exact channel sets."""
    # 1. Modules
    assert set(incremental_state.modules.keys()) == set(oracle_state.modules.keys())

    # 2. Definitions / Artifacts
    assert set(incremental_state.artifacts.keys()) == set(oracle_state.artifacts.keys())
    for mod_key, inc_art in incremental_state.artifacts.items():
        ora_art = oracle_state.artifacts[mod_key]
        assert inc_art.get("symbols") == ora_art.get("symbols")
        assert inc_art.get("own_symbols") == ora_art.get("own_symbols")

    # 3. ModuleUsageFacts
    assert set(incremental_state.module_usages.keys()) == set(oracle_state.module_usages.keys())
    for mod_name, inc_facts in incremental_state.module_usages.items():
        ora_facts = oracle_state.module_usages[mod_name]
        assert inc_facts.direct_calls == ora_facts.direct_calls
        assert inc_facts.qualified_refs == ora_facts.qualified_refs
        assert inc_facts.imports == ora_facts.imports
        assert inc_facts.aliases == ora_facts.aliases

    # 4. Canonical re-export facts
    assert (
        incremental_state.reexport_facts_by_module
        == oracle_state.reexport_facts_by_module
    )

    # 5. Artifact Consumption
    assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
    for target, ora_entry in oracle_state.artifact_consumption.items():
        inc_entry = incremental_state.artifact_consumption.get(target, {})
        assert sorted(
            inc_entry.get("consumers", [])
        ) == sorted(
            ora_entry.get("consumers", [])
        )
        inc_channels = inc_entry.get("channels", {})
        ora_channels = ora_entry.get("channels", {})
        assert set(inc_channels.keys()) == set(ora_channels.keys())
        for consumer in ora_channels.keys():
            assert set(inc_channels[consumer]) == set(ora_channels[consumer])

    # 6. Dependency Graph
    if oracle_state.dependency_graph is not None:
        assert incremental_state.dependency_graph is not None
        assert incremental_state.dependency_graph.hard_edges == oracle_state.dependency_graph.hard_edges
        assert incremental_state.dependency_graph.soft_edges == oracle_state.dependency_graph.soft_edges

    # 7. Macro Graph Metrics
    if oracle_state.metrics is not None:
        assert incremental_state.metrics is not None
        assert incremental_state.metrics == oracle_state.metrics
~~~

~~~python
def _build_full_static_state(repo_dir: Path) -> RepositoryAnalysisState:
    """Canonical Oracle: builds fresh full static RepositoryAnalysisState via real production ContextorFacade."""
    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors, errors
    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    return hydrated.engine.state
~~~

### Literal current incremental LIVE updater

~~~python
def _repository_updater(root: Path, holder: dict[str, object] | None = None):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)

    def update(state, file_path: str):
        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
        from contextor.core.analysis.state_manager import FileStateManager
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

        manager = FileStateManager(str(cache))
        registry = PersistentIdentityRegistry(str(root))
        registry_checkpoint = registry.create_checkpoint()
        engine = IncrementalAnalysisEngine(state, registry, manager, str(root))
        try:
            delta = engine.update_file(file_path)
        except Exception:
            try:
                registry.restore_checkpoint(registry_checkpoint)
            finally:
                _clear_registry_checkpoint(holder)
            raise
        if holder is not None:
            holder["manager"] = manager
            holder["state_id"] = getattr(manager, "state_id", "")
        return delta

    return update
~~~


## VERIFIED_COMPLETE_LITERAL_SOURCE_ADDENDUM

### run_full_analysis_exclusive — contextor/core/analysis/full_analysis_coordinator.py

~~~python
def run_full_analysis_exclusive(
    path: str | Path,
    *,
    owner: str = "desktop_analysis",
    analysis_fn: Callable[..., Any] | None = None,
    log: Callable[[str], None] | None = None,
    progress_callback: Any = None,
    additional_excludes: list[str] | None = None,
    timeout: float | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute full repository analysis while holding an exclusive repository lease.
    Guarantees single-writer execution across Desktop, MCP, and CLI.
    """
    repo = str(Path(path).resolve())
    full_started = time.monotonic()
    lease_wait_started = full_started
    lease = acquire_full_analysis(
        path,
        owner=owner,
        writer_kind="full_analysis",
        timeout=timeout,
        is_cancelled=is_cancelled,
        log=log,
    )
    try:
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_LEASE_ACQUIRED",
            owner=owner,
            repo=repo,
            wait_ms=(time.monotonic() - lease_wait_started) * 1000.0,
            timing_semantics="critical_path_lease_wait",
        )
        if analysis_fn is not None:
            analysis_started = time.monotonic()
            analysis_result = analysis_fn(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        else:
            from contextor.core.api.facade import ContextorFacade

            analysis_started = time.monotonic()
            analysis_result = ContextorFacade.analyze_project(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        analysis_ms = (time.monotonic() - analysis_started) * 1000.0
        total_before_release_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_BODY_END",
            owner=owner,
            repo=repo,
            analysis_ms=analysis_ms,
            total_before_release_ms=total_before_release_ms,
            elapsed_ms=analysis_ms,
            timing_semantics="critical_path_analysis_body",
            result=(
                f"analysis_ms={analysis_ms:.3f};"
                f"total_before_release_ms={total_before_release_ms:.3f}"
            ),
        )
        return analysis_result
    finally:
        release_full_analysis(lease)
        total_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_END",
            owner=owner,
            repo=repo,
            total_ms=total_ms,
            elapsed_ms=total_ms,
            timing_semantics="critical_path_total",
            result=f"total_ms={total_ms:.3f}",
        )

~~~

### ContextorFacade.analyze_layer — contextor/core/api/facade.py

~~~python
    @staticmethod
    def analyze_layer(
        root_dir: str,
        layer_dir: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
    ) -> str:
        from contextor.core.analysis.full_analysis_lease import (
            acquire_full_analysis,
            release_full_analysis,
        )

        root_resolved, _ = _resolve_repository_target(
            root_dir,
            layer_dir,
            target_kind="layer",
        )

        lease = acquire_full_analysis(
            root_resolved,
            owner="scoped_layer_analysis",
            writer_kind="scoped_analysis",
            timeout=10.0,
        )
        try:
            return ContextorFacade._analyze_layer_uncoordinated(
                root_dir,
                layer_dir,
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
            )
        finally:
            release_full_analysis(lease)

~~~

### ContextorFacade.analyze_single_file — contextor/core/api/facade.py

~~~python
    @staticmethod
    def analyze_single_file(
        file_path: str,
        repo_root: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
        publication_result: dict[str, Any] | None = None,
    ) -> str:
        if publication_result is not None:
            publication_result.update(
                status="not_attempted",
                revision=None,
                warning=None,
            )
        from contextor.core.analysis.full_analysis_lease import (
            acquire_full_analysis,
            release_full_analysis,
        )

        root_resolved, target = _resolve_repository_target(
            repo_root,
            file_path,
            target_kind="file",
        )
        if target.suffix.lower() != ".py":
            raise ValueError(
                f"Selected file is not a Python file: {target}"
            )

        lease = acquire_full_analysis(
            root_resolved,
            owner="scoped_single_file_analysis",
            writer_kind="scoped_analysis",
            timeout=10.0,
        )
        try:
            return ContextorFacade._analyze_single_file_uncoordinated(
                file_path,
                repo_root,
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                publication_result=publication_result,
            )
        finally:
            release_full_analysis(lease)

~~~

### _start_analysis_job — contextor/mcp/analysis_jobs.py

~~~python
def _start_analysis_job(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
) -> dict:
    repo_key = str(root)
    with _analysis_job_lock:
        active_id = _analysis_jobs_by_repo.get(repo_key)
        active_task = _analysis_tasks.get(active_id) if active_id else None
        if active_id and active_task is not None and active_task.is_alive():
            existing = _read_analysis_job(root, active_id)
            if existing is not None:
                return _public_job(existing, reused=True)
        job_id = uuid4().hex
        job = {
            "job_id": job_id, "operation": operation, "repo_path": repo_key,
            "target": str(target) if target is not None else None,
            "exclude_paths": list(exclude_paths or []), "status": "queued",
            "created_at": _utc_now(), "started_at": None, "completed_at": None,
            "message": "Analysis accepted.", "error": None,
            "live_publish_status": (
                "pending" if operation == "project" else "not_applicable"
            ),
            "live_publish_revision": None, "live_publish_warning": None,
            "owner_pid": os.getpid(),
        }
        _write_analysis_job(root, job)
        def run_job() -> None:
            asyncio.run(_execute_analysis_job(root, job, target, exclude_paths))
        task = threading.Thread(
            target=run_job, name=f"contextor-analysis-{job_id}", daemon=True
        )
        _analysis_jobs_by_repo[repo_key] = job_id
        _analysis_tasks[job_id] = task
        task.start()
        return _public_job(job)

~~~

### _run_analysis_worker — contextor/mcp/analysis_jobs.py

~~~python
async def _run_analysis_worker(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
    log=None,
) -> dict:
    effective_log = log or _stderr_log

    def run() -> dict:
        with _analysis_lock:
            previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
            previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
            os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
            if previous_registry is None:
                os.environ[
                    "CONTEXTOR_MCP_PROCESS_REGISTRY"
                ] = str(registry_dir(root))
            try:
                if operation == "project":
                    _, result = run_full_analysis_exclusive(
                        str(root),
                        owner="mcp_analysis",
                        log=effective_log,
                        progress_callback=_analysis_progress_callback,
                        additional_excludes=exclude_paths,
                        is_cancelled=_analysis_shutdown_requested,
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                    skipped_files = (getattr(result, "summary_data", {}) or {}).get(
                        "skipped_files", []
                    )
                    if not isinstance(skipped_files, list):
                        skipped_files = []
                    return {
                        "skipped_python_files": skipped_files,
                        "live_publish_status": getattr(
                            result,
                            "live_publish_status",
                            "not_attempted",
                        ),
                        "live_publish_revision": getattr(
                            result,
                            "live_publish_revision",
                            None,
                        ),
                        "live_publish_warning": getattr(
                            result,
                            "live_publish_warning",
                            None,
                        ),
                    }
                if operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root), str(target), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target), str(root), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
                return {}
            finally:
                if previous_cache is None:
                    os.environ.pop("CONTEXTOR_CACHE_DIR", None)
                else:
                    os.environ["CONTEXTOR_CACHE_DIR"] = previous_cache
                if previous_registry is None:
                    os.environ.pop("CONTEXTOR_MCP_PROCESS_REGISTRY", None)
                else:
                    os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = previous_registry

    return await asyncio.to_thread(run)

~~~

### _assert_full_parity — tests/test_completeness_freshness_parity_proof.py

~~~python
def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state: RepositoryAnalysisState):
    """Asserts full canonical parity across all plan-controlled families with exact channel sets."""
    # 1. Modules
    assert set(incremental_state.modules.keys()) == set(oracle_state.modules.keys())

    # 2. Definitions / Artifacts
    assert set(incremental_state.artifacts.keys()) == set(oracle_state.artifacts.keys())
    for mod_key, inc_art in incremental_state.artifacts.items():
        ora_art = oracle_state.artifacts[mod_key]
        assert inc_art.get("symbols") == ora_art.get("symbols")
        assert inc_art.get("own_symbols") == ora_art.get("own_symbols")

    # 3. ModuleUsageFacts
    assert set(incremental_state.module_usages.keys()) == set(oracle_state.module_usages.keys())
    for mod_name, inc_facts in incremental_state.module_usages.items():
        ora_facts = oracle_state.module_usages[mod_name]
        assert inc_facts.direct_calls == ora_facts.direct_calls
        assert inc_facts.qualified_refs == ora_facts.qualified_refs
        assert inc_facts.imports == ora_facts.imports
        assert inc_facts.aliases == ora_facts.aliases

    # 4. Canonical re-export facts
    assert (
        incremental_state.reexport_facts_by_module
        == oracle_state.reexport_facts_by_module
    )

    # 5. Artifact Consumption (exact target set, exact consumers, and exact channel sets)
    assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
    for target, ora_entry in oracle_state.artifact_consumption.items():
        inc_entry = incremental_state.artifact_consumption.get(target, {})
        assert sorted(
            inc_entry.get("consumers", [])
        ) == sorted(
            ora_entry.get("consumers", [])
        ), (
            f"Target '{target}' consumers mismatch: "
            f"incremental={inc_entry.get('consumers', [])!r}, "
            f"full={ora_entry.get('consumers', [])!r}"
        )
        inc_channels = inc_entry.get("channels", {})
        ora_channels = ora_entry.get("channels", {})
        assert set(inc_channels.keys()) == set(ora_channels.keys()), (
            f"Target '{target}' channel consumers mismatch: inc={inc_channels} vs ora={ora_channels}"
        )
        for consumer in ora_channels.keys():
            assert set(inc_channels[consumer]) == set(ora_channels[consumer]), (
                f"Target '{target}', Consumer '{consumer}' channel mismatch: "
                f"incremental={inc_channels.get(consumer)} vs full={ora_channels.get(consumer)}"
            )

    # 6. Dependency Graph
    if oracle_state.dependency_graph is not None:
        assert incremental_state.dependency_graph is not None
        assert incremental_state.dependency_graph.hard_edges == oracle_state.dependency_graph.hard_edges
        assert incremental_state.dependency_graph.soft_edges == oracle_state.dependency_graph.soft_edges

    # 7. Macro Graph Metrics
    if oracle_state.metrics is not None:
        assert incremental_state.metrics is not None
        assert incremental_state.metrics == oracle_state.metrics

~~~

### _build_full_static_state — tests/test_completeness_freshness_parity_proof.py

~~~python
def _build_full_static_state(repo_dir: Path) -> RepositoryAnalysisState:
    """Canonical Oracle: builds fresh full static RepositoryAnalysisState via real production ContextorFacade."""
    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors, errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None

    return hydrated.engine.state

~~~

### _repository_updater — contextor/core/live_state/runtime.py

~~~python
def _repository_updater(root: Path, holder: dict[str, object] | None = None):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)

    def update(state, file_path: str):
        import time
        op = _safe_current_trace_operation()
        started = time.monotonic()
        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
        from contextor.core.analysis.state_manager import FileStateManager
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

        manager = FileStateManager(str(cache))
        registry = PersistentIdentityRegistry(str(root))
        registry_checkpoint = registry.create_checkpoint()

        if holder is not None:
            holder["registry"] = registry
            holder["registry_checkpoint"] = registry_checkpoint

        engine = IncrementalAnalysisEngine(
            state,
            registry,
            manager,
            str(root),
        )
        _safe_trace_event("LIVE", "ENGINE_READY", op=op, repo=str(root), elapsed_ms=(time.monotonic() - started) * 1000.0)
        incremental_started = time.monotonic()
        try:
            delta = engine.update_file(file_path)
        except Exception:
            try:
                registry.restore_checkpoint(registry_checkpoint)
            finally:
                _clear_registry_checkpoint(holder)
            raise
        _safe_trace_event("LIVE", "INCREMENTAL_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - incremental_started) * 1000.0, status=getattr(delta, "status", None))
        if holder is not None:
            holder["manager"] = manager
            holder["state_id"] = getattr(manager, "state_id", "")
        return delta

    return update

~~~

### update_file — contextor/mcp/tools/update_file.py

~~~python
def update_file(
    repo_path: str,
    file_path: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()

    engine = mcp_runtime.get_or_init_engine(root)

    if not engine:
        return json.dumps({"status": "NO_SESSION", "file_path": str(target_file), "error": "Run analyze_project first to initialize the session."}, indent=2)

    try:
        rel_path = target_file.relative_to(root)
        module_path = ".".join(rel_path.with_suffix("").parts)
        old_artifacts = engine.state.artifacts.get(module_path, {})
        from contextor.core.live_state import connect

        live_client = connect(root)
        if live_client:
            remote = live_client.update_file(str(target_file), origin="mcp")
            if remote.get("status") != "ok":
                raise RuntimeError(remote.get("error", "Shared LIVE update failed."))
            res = remote["result"]
            cold_migration = False
            with mcp_runtime._engine_cache_transaction(root) as root_key:
                mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
                engine = mcp_runtime.get_or_init_engine(
                    root, _defer_migration=True
                )
                cold_migration = engine is mcp_runtime._MIGRATION_NEEDED
                if cold_migration:
                    mcp_runtime._live_engine_revisions.pop(root_key, None)
            if cold_migration:
                mcp_runtime.get_or_init_engine(root)
                with mcp_runtime._engine_cache_transaction(root) as root_key:
                    engine = mcp_runtime._live_engines.get(root_key)
                    refreshed_revision = mcp_runtime._live_engine_revisions.get(root_key)
                    if (
                        engine is None
                        or refreshed_revision != int(remote["revision"])
                        or getattr(engine.state, "revision", None) != refreshed_revision
                    ):
                        raise RuntimeError(
                            "Canonical LIVE state could not be hydrated at the committed revision."
                        )
            live_state_persisted = True
        else:
            res, engine, old_artifacts, live_state_persisted = (
                _execute_local_candidate_update(
                    root,
                    target_file,
                    engine,
                )
            )
        new_artifacts = engine.state.artifacts.get(module_path, {})
        semantic_diff = _semantic_artifact_diff(old_artifacts, new_artifacts)
        affected_items, affected_total, affected_truncated = query_helpers.bounded_items(
            getattr(res, "affected_modules", []) or [], max_items
        )
        _ev_limit = 3 if max_items is None else min(3, max_items)
        if compact:
            affected_ev = affected_items[:_ev_limit]
            affected_view = {
                "total": affected_total,
                "truncated": affected_total > len(affected_ev),
                "evidence": affected_ev,
            }
        else:
            affected_view = {
                "total": affected_total,
                "truncated": affected_truncated,
                "items": affected_items,
            }
        result = {
            "status": res.status,
            "file_path": res.file_path,
            "graph_state": res.graph_state,
            "dependencies_state": res.dependencies_state,
            "blast_radius_state": res.blast_radius_state,
            "local_metrics_state": res.local_metrics_state,
            "global_metrics_state": res.global_metrics_state,
            "artifact_consumption_state": res.artifact_consumption_state,
            "affected_modules": affected_view,
            "live_state_persisted": live_state_persisted,
            "semantic_diff": _semantic_diff_view(semantic_diff, max_items, compact),
        }
        runtime_restart_required = _mcp_runtime_restart_required(target_file)
        result["runtime_restart_required"] = runtime_restart_required
        if runtime_restart_required:
            result["runtime_state"] = "stale_until_mcp_server_restart"
            result["runtime_warning"] = (
                "Canonical state now describes the MCP server code on disk, but "
                "the running MCP process still executes the previously loaded code. "
                "Restart the MCP server and verify the changed tool live."
            )
        if res.delta:
            result["delta"] = {
                "module_path": res.delta.module_path,
                "is_new": res.delta.is_new,
                "is_deleted": res.delta.is_deleted,
                "imports_added": res.delta.imports_added,
                "imports_removed": res.delta.imports_removed,
                "artifacts_added": res.delta.artifacts_added,
                "artifacts_removed": res.delta.artifacts_removed,
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for update_file",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    },
                    indent=2,
                )
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = {"status": "ERROR", "file_path": str(target_file), "error": str(e)}
        if isinstance(e, _LocalCandidatePersistenceRejected):
            error_result["live_state_persisted"] = False
        return json.dumps(error_result, indent=2)

~~~




## VERIFIED_LITERAL_TEST_AND_CONFIGURATION_SOURCE

### test_analysis_endpoint_returns_reusable_job_and_pollable_completion — tests/test_mcp_regressions.py

~~~python
def test_analysis_endpoint_returns_reusable_job_and_pollable_completion(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    release = threading.Event()

    async def fake_worker(*_args, **_kwargs):
        await asyncio.to_thread(release.wait)
        return {
            "live_publish_status": "success",
            "live_publish_revision": 1,
            "live_publish_warning": None,
        }

    engine_state = SimpleNamespace(fresh=True, revision=1)
    engine = SimpleNamespace(state=engine_state)
    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    async def scenario():
        first = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        second = json.loads(await mcp_server.analyze_project.fn(str(repo)))

        assert first["status"] == "queued"
        assert second["job_id"] == first["job_id"]
        assert second["reused"] is True
        running = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), first["job_id"])
        )
        assert running["status"] in {"queued", "running"}

        task = analysis_jobs._analysis_tasks[first["job_id"]]
        release.set()
        task.join(timeout=5)
        assert not task.is_alive()
        completed = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), first["job_id"])
        )
        assert completed["status"] == "completed"
        assert completed["error"] is None
        assert completed["live_publish_status"] == "success"
        assert completed["live_publish_revision"] == 1
        assert completed["live_publish_warning"] is None
        assert mcp_runtime._live_engine_revisions[str(repo)] == 1

    asyncio.run(scenario())

~~~

### test_mcp_update_file_live_branch_delegates_without_local_persistence — tests/test_mcp_regressions.py

~~~python
def test_mcp_update_file_live_branch_delegates_without_local_persistence(
    tmp_path, monkeypatch
):
    root = tmp_path.resolve()
    target = root / "provider.py"
    target.write_text("def run():\n    return 1\n", encoding="utf-8")
    remote_result = SimpleNamespace(
        status="UPDATED",
        file_path=str(target),
        graph_state="fresh",
        dependencies_state="fresh",
        blast_radius_state="fresh",
        local_metrics_state="deferred",
        global_metrics_state="deferred",
        artifact_consumption_state="fresh",
        affected_modules=[],
        delta=None,
    )
    remote_calls = []

    class FakeLiveClient:
        def update_file(self, file_path, *, origin):
            remote_calls.append((file_path, origin))
            return {"status": "ok", "revision": 42, "result": remote_result}

    engine = SimpleNamespace(
        state=SimpleNamespace(artifacts={"provider": {}}),
        update_file=lambda *_args: pytest.fail("LIVE path used local engine update"),
    )
    monkeypatch.setattr(
        "contextor.core.live_state.connect", lambda _root: FakeLiveClient()
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, **_kwargs: engine)
    monkeypatch.setattr(
        mcp_runtime,
        "_engine_cache_transaction",
        lambda _root: nullcontext(str(root)),
    )
    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
    monkeypatch.setattr(
        update_file_module,
        "_persist_live_engine",
        lambda *_args: pytest.fail("LIVE path called the local persister"),
    )
    monkeypatch.setattr(
        "contextor.core.analysis.full_analysis_coordinator.acquire_full_analysis",
        lambda *_args, **_kwargs: pytest.fail("LIVE path acquired local writer lease"),
    )
    monkeypatch.setattr(
        update_file_module, "_mcp_runtime_restart_required", lambda _path: False
    )

    response = json.loads(
        mcp_server.update_file.fn(repo_path=str(root), file_path=str(target))
    )

    assert remote_calls == [(str(target), "mcp")]
    assert response["status"] == "UPDATED"
    assert response["live_state_persisted"] is True

~~~

### test_desktop_watcher_reports_create_edit_and_delete_without_manual_update — tests/test_live_state_ipc.py

~~~python
def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tmp_path):
    updates = []
    statuses = []
    identity = PersistentIdentityRegistry(str(tmp_path))
    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
    manager.save(identity.repo_id, revision=0)

    def update(state, file_path):
        updates.append(file_path)
        state.updates += 1
        manager.update_state(file_path)
        manager.save(identity.repo_id, revision=state.revision + 1)
        return SimpleNamespace(status="UPDATED", file_path=file_path)

    server_state = SimpleNamespace(updates=0, revision=0, state_id=identity.repo_id, modules={})
    server = CanonicalLiveServer(server_state, revision=0, updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(
        tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
    )
    target = tmp_path / "sample.py"
    try:
        target.write_text("value = 1\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]

        target.write_text("value = 22\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]

        target.unlink()
        watcher._enqueue_path(str(target))
        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]
        snapshot = LiveStateClient(server.endpoint).snapshot()
        assert snapshot["revision"] == 3
        assert snapshot["state"].updates == 3
        assert updates == [str(target)] * 3
        assert statuses == [
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
        ]
    finally:
        server.close()
        thread.join(timeout=2)

~~~

### test_real_repository_adapter_two_successive_updates_are_exact_successors — tests/test_live_state_ipc.py

~~~python
def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp_path, monkeypatch):
    from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
    from contextor.core.live_state.runtime import _repository_persister, _repository_updater
    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import ensure_repository_identity

    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ensure_repository_identity(repo)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    cache = repo_cache_dir(repo)
    state = RepositoryAnalysisState(modules={})
    state.revision = 1
    identity = ensure_repository_identity(repo)[0]
    metadata = save_snapshot(
        state,
        cache,
        "sid",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
    )
    manager = FileStateManager(str(cache))
    manager.save("sid", revision=metadata.revision)
    holder = {}
    server = CanonicalLiveServer(
        state,
        revision=metadata.revision,
        updater=_repository_updater(repo, holder),
        persister=_repository_persister(repo, holder),
    )

    for expected in (2, 3):
        response = server._dispatch({"operation": "update_file", "file_path": str(source)})
        assert response["revision"] == expected
        assert server._revision == expected
        assert server._state.revision == expected
        assert read_metadata(cache).revision == expected
        loaded_state, loaded_metadata = load_snapshot(cache, "sid")
        assert loaded_metadata.revision == expected
        assert loaded_state.revision == expected
        assert FileStateManager(str(cache)).revision == expected
        assert server._events[-1]["revision"] == expected

~~~

### _poll_until_reconciled — tests/test_live_state_ipc.py

~~~python
def _poll_until_reconciled(watcher, expected, timeout=10.0):
    deadline = time.monotonic() + timeout
    observed = []
    while time.monotonic() < deadline:
        observed.extend(watcher.poll_once())
        if observed == expected:
            return observed
        time.sleep(0.01)
    return observed

~~~

### live_server — tests/test_live_state_ipc.py

~~~python
@pytest.fixture
def live_server():
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, LiveStateClient(server.endpoint)
    server.close()
    thread.join(timeout=2)
    assert not thread.is_alive()

~~~

### isolated_dirs — tests/conftest.py

~~~python
@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    """
    Redirects cache, state and output away from real user directories.
    """

    for variable, name in (
        ("CONTEXTOR_CACHE_DIR", "cache"),
        ("CONTEXTOR_STATE_DIR", "state"),
        ("CONTEXTOR_OUTPUT_DIR", "output"),
        ("CONTEXTOR_REGISTRY_DIR", "registries"),
    ):
        monkeypatch.setenv(variable, str(tmp_path / name))

    return tmp_path

~~~

### sample_repo — tests/conftest.py

~~~python
@pytest.fixture
def sample_repo(tmp_path):
    """
    Small repository exercising imports, a cycle and a name collision.
    """

    root = tmp_path / "repo"

    files = {
        "core/__init__.py": "",
        "core/alpha.py": (
            "from core.beta import helper\n"
            "\n"
            "MAX_ITEMS = 10\n"
            "\n"
            "\n"
            "class Engine:\n"
            "    def start(self):\n"
            "        return helper()\n"
        ),
        "core/beta.py": ("from core.alpha import Engine\n\n\ndef helper():\n    return 1\n"),
        "core/gamma.py": (
            "MAX_ITEMS = 99\n"
            "\n"
            "\n"
            "def helper():\n"
            "    return 'a completely different implementation'\n"
        ),
        "ui/__init__.py": "",
        "ui/app.py": (
            "from core.alpha import Engine\n\n\ndef run():\n    return Engine().start()\n"
        ),
    }

    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return root

~~~

### _analysis_filters — contextor/core/api/facade.py

~~~python
def _analysis_filters(
    repo_path: str, additional_excludes: list[str] | None = None
) -> tuple[list[str], set]:
    """Combine saved GUI excludes with safe, per-analysis path exclusions.

    ``additional_excludes`` is intentionally ephemeral: MCP and other API
    callers can narrow one analysis without modifying the repository-specific
    exclude state managed by the GUI. Entries identify a repository-relative
    Python file or directory prefix. Absolute entries are accepted only when
    they resolve inside the repository.
    """

    saved_excludes, extra_dirs = _load_excludes_for_repo(repo_path)
    if not additional_excludes:
        return list(saved_excludes), extra_dirs
    if len(additional_excludes) > 500:
        raise ValueError("At most 500 per-analysis exclude paths are allowed.")

    root = Path(repo_path).expanduser().resolve()
    combined = list(saved_excludes)
    known = {str(item).replace("\\", "/").strip("/") for item in combined}

    for item in additional_excludes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Exclude paths must be non-empty strings.")
        candidate = Path(item).expanduser()
        if candidate.is_absolute():
            try:
                candidate = candidate.resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError(
                    f"Exclude path is outside the repository: {item}"
                ) from exc

        normalized = candidate.as_posix().removeprefix("./").strip("/")
        if not normalized or ".." in Path(normalized).parts:
            raise ValueError(f"Invalid repository-relative exclude path: {item}")
        if normalized not in known:
            combined.append(normalized)
            known.add(normalized)

    return combined, extra_dirs

~~~


