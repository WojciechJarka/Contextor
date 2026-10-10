# L32H2D2B_SCOPED_FACADE_WRITER_COORDINATION

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
- C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py
- Raport: C:\Temp\Contextor_Repo\walkthrough.md

## SOURCE_CONTRACT_VERIFICATION

DIRECT_EVIDENCE: Contextor MCP `get_symbol_implementation(mode=fetch)` pobrał kompletne aktualne implementacje obu publicznych metod facade, `_resolve_repository_target`, `acquire_full_analysis`, `release_full_analysis`, resolvera stanu, hydratora, migracji oraz ścieżki publikacji. Przed patchem wszystkie źródła deklarowały `implementation_is_complete=true` i `workspace_sync=verified`, revision 231. Obie metody publiczne były i pozostały `@staticmethod`. Potwierdzeni konsumenci produkcyjni: `contextor.cli`, `contextor.mcp_worker`, `contextor.mcp.analysis_jobs`, `contextor.ui.gui`; ich wywołania idą przez publiczne metody. CLI wywołuje metody scoped po powrocie z `run_full_analysis_exclusive`; pozostałe scoped calle nie są objęte istniejącym outer lease. Dynamiczna kompletność callerów pozostaje poza zakresem statycznego narzędzia.

## LIVE_PUBLICATION_LOCK_PREFLIGHT

CODE_PATH_PROVED: `LiveStateClient.publish -> CanonicalLiveServer._dispatch -> _execute_publish -> _execute_committed_publish -> locked_committed_snapshot` (gdy zainstalowano reader). Synchroniczna ścieżka nie wywołuje `acquire_full_analysis`; reader bierze tylko blokadę snapshot store. `_repository_mutation_guard` bierze full-analysis lease dla operacji update, lecz dispatch publish omija guard. `resolve_authoritative_repository_state` wywołuje `migrate_legacy_snapshot`, `connect`, odczyt snapshot; `hydrate_repository_engine` wywołuje resolver. Migracja może zapisać snapshot pod już posiadanym scoped lease i nie bierze kolejnego full-analysis lease. Nie stwierdzono nested acquisition ani odwrotnej krawędzi w tych ścieżkach.

## RED_RESULT

5 oczekiwanych niepowodzeń przed produkcyjnym patchem: dwa testy braku lease przed identity write, dwa testy braku wrappera blokowanego przez wcześniejszego writera, jeden test odrzucanego `writer_kind=scoped_analysis`. Komenda: `.venv\Scripts\python.exe -m pytest -q tests/test_full_analysis_coordination.py::test_scoped_facade_holds_writer_lease_before_identity_write tests/test_full_analysis_coordination.py::test_scoped_facade_blocks_behind_existing_writer_before_body tests/test_full_analysis_coordination.py::test_scoped_writer_kind_is_accepted`.

## GREEN_RESULT / SCOPED_ANALYSIS_WRITER_KIND / PUBLIC_FACADE_WRAPPER_CONTRACT

Literalny writer kind `scoped_analysis` dodany wyłącznie w walidatorze. Publiczne statyczne wrappery walidują scope przed lease, biorą lease z ownerem `scoped_layer_analysis` albo `scoped_single_file_analysis`, `timeout=10.0`, wywołują niezmienione ciała pod prywatnymi nazwami i zwalniają lease w `finally`. Contextor po zmianie pobrał pięć kompletnych implementacji, `workspace_sync=verified`, revision 240. `get_symbol_call_context` pokazuje wywołania prywatnych implementacji z publicznych wrapperów; publiczny blast radius nadal pokazuje czterech wymienionych konsumentów produkcyjnych.

## LAYER_REGISTRY_EXCLUSION / SINGLE_FILE_REGISTRY_EXCLUSION

CONTRACT_PROVED: testy instrumentują wejście do inicjalizacji registry i widzą wcześniejsze nabycie lease; wyjątek z tej ścieżki zwalnia lease. Osobne testy wywołują wyjątek przy generowaniu raportu i ponownie nabywają lease. Oryginalne bloki `registry.transaction` oraz algorytmy raportowe nie zostały zmienione.

## LOCAL_MCP_EXCLUSION / FULL_ANALYSIS_EXCLUSION / CROSS_PROCESS_EXCLUSION

CONTRACT_PROVED: międzyprocesowe testy uruchamiają proces `spawn` próbujący nabyć ten sam OS lease z `writer_kind=local_incremental` i `writer_kind=full_analysis` podczas działania publicznej metody scoped; obie próby zwracają busy. Test wątkowy dowodzi, że body scoped zaczyna się dopiero po zwolnieniu poprzedniego writera. Bezpośrednie wywołania facade są objęte ochroną.

## INVALID_TARGET_BEHAVIOR

CONTRACT_PROVED: błędny layer scope, błędny file scope i plik nie-Python zgłaszają dotychczasowe `ValueError` przed próbą nabycia lease. Odmowa lease zatrzymuje body przed inicjalizacją identity/registry. Testy używają repozytoriów tymczasowych; późniejsze uruchomienia mają izolowane cache/state/output/registry.

## LIVE_SINGLE_FILE_PUBLICATION_COMPATIBILITY

CONTRACT_PROVED: nowy test używa prawdziwego `CanonicalLiveServer` i `LiveStateClient` w izolowanym fixture. Publiczna metoda single-file parsuje zmieniony plik i wykonuje prawdziwe IPC publish; przy publikacji lease pozostaje trzymany. Odpowiedź `publication_result.status=success`, revision zwiększona o 1. Istniejące testy reuse, recovery i output przechodzą.

## NESTED_LOCK_AND_DEADLOCK_GATE

PASS dla sprawdzonych ścieżek: prawdziwa publikacja IPC wróciła przed timeoutem 5 s, bez nested full-analysis acquisition. Testy blokady same-process i cross-process przechodzą. Contextor wykrył nowy statyczny cykl importów `facade <-> full_analysis_coordinator` (revision 234); oba importy są lokalne wewnątrz funkcji, a wykonany test nie wykazał runtime import failure. To pozostaje obserwacją statycznej diagnostyki, bez autonomicznego refaktoru.

## OUTPUT_AND_ARTIFACT_COMPATIBILITY

Istniejące testy report/output, artifact reuse, staging, layer hydration i scope przechodzą. Oryginalne ciała obu metod zachowano bez wewnętrznych zmian. Interfejsy publiczne zachowują oryginalne parametry i typ zwrotu.

## TARGETED_TEST_RESULTS

- RED: 5 failed zgodnie z oczekiwaniem.
- GREEN po patchu: 5 passed dla nowych pierwszych regresji.
- Wybrane pięć plików: 57 passed, 1 warning (zewnętrzne ostrzeżenie AuthlibDeprecationWarning).
- Rzeczywiste IPC publish: 1 passed.
- `py_compile` obu ownerów: PASS.
- `git diff --check` czterech zmienionych plików: PASS. Git podał jedynie informację o przyszłej konwersji LF/CRLF.

## SOURCE_SYNC_VERIFICATION / LIVE_REVISION_BEFORE_AFTER

Przed: 231. Po: 240. `get_live_events(after_revision=231)`: continuity=continuous, resync_required=false, 9 zdarzeń 232–240; zmiany produkcyjne 233–234 oraz testowe zostały przejęte przez desktop_watcher. Contextor fetch po zmianie: `workspace_sync=verified` dla obu wrapperów, prywatnych implementacji i koordynatora. To dowodzi odświeżenia źródła w canonical index; nie certyfikuje reloadu kodu w istniejących procesach MCP/Desktop.

## REMAINING_WRITER_BYPASSES

UNKNOWN poza scoped facade: bezpośrednie registry-only writery z poprzedniego handoffu nie są objęte tą zmianą. Nie rozszerzano scope. Statyczne blast radius nie dowodzi pełnej osiągalności dynamicznej.

## RESTART_REQUIRED

YES dla serving MCP/Desktop/LIVE procesów, jeżeli mają wykonywać nowe wersje zaimportowanych modułów; restartu nie wykonano. Testy uruchomiono w nowym procesie Python.

## FINAL_VERDICT

L32H2D2B_TARGETED_PASS. Nie jest to FINAL PASS całego L32H ani certyfikacja już uruchomionych procesów.

## FULL_DIFFS

Poniżej pełny surowy diff wszystkich czterech zmienionych plików produkcyjnych/testowych. Raport `walkthrough.md` nie jest liczony jako source/test diff.

```diff

diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 5b43d1f..292fa9a 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -428,10 +428,11 @@ def acquire_full_analysis(
         "live_mutation",
         "startup_publish",
         "local_incremental",
+        "scoped_analysis",
     }:
         raise ValueError(
             "writer_kind must be 'full_analysis', 'live_mutation', "
-            "'startup_publish', or 'local_incremental'"
+            "'startup_publish', 'local_incremental', or 'scoped_analysis'"
         )
 
     lock_file, key, repo_id = _resolve_lock_path(repo_path)
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 64352e5..d927b65 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1305,6 +1305,42 @@ class ContextorFacade:
         log=None,
         progress_callback=None,
         additional_excludes: list[str] | None = None,
+    ) -> str:
+        from contextor.core.analysis.full_analysis_coordinator import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        root_resolved, _ = _resolve_repository_target(
+            root_dir,
+            layer_dir,
+            target_kind="layer",
+        )
+
+        lease = acquire_full_analysis(
+            root_resolved,
+            owner="scoped_layer_analysis",
+            writer_kind="scoped_analysis",
+            timeout=10.0,
+        )
+        try:
+            return ContextorFacade._analyze_layer_uncoordinated(
+                root_dir,
+                layer_dir,
+                log=log,
+                progress_callback=progress_callback,
+                additional_excludes=additional_excludes,
+            )
+        finally:
+            release_full_analysis(lease)
+
+    @staticmethod
+    def _analyze_layer_uncoordinated(
+        root_dir: str,
+        layer_dir: str,
+        log=None,
+        progress_callback=None,
+        additional_excludes: list[str] | None = None,
     ) -> str:
         """Analyzes a specific layer. Returns output pattern."""
         progress = _StagedProgress(progress_callback, total_stages=10, log=log)
@@ -1496,6 +1532,48 @@ class ContextorFacade:
         progress_callback=None,
         additional_excludes: list[str] | None = None,
         publication_result: dict[str, Any] | None = None,
+    ) -> str:
+        from contextor.core.analysis.full_analysis_coordinator import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        root_resolved, target = _resolve_repository_target(
+            repo_root,
+            file_path,
+            target_kind="file",
+        )
+        if target.suffix.lower() != ".py":
+            raise ValueError(
+                f"Selected file is not a Python file: {target}"
+            )
+
+        lease = acquire_full_analysis(
+            root_resolved,
+            owner="scoped_single_file_analysis",
+            writer_kind="scoped_analysis",
+            timeout=10.0,
+        )
+        try:
+            return ContextorFacade._analyze_single_file_uncoordinated(
+                file_path,
+                repo_root,
+                log=log,
+                progress_callback=progress_callback,
+                additional_excludes=additional_excludes,
+                publication_result=publication_result,
+            )
+        finally:
+            release_full_analysis(lease)
+
+    @staticmethod
+    def _analyze_single_file_uncoordinated(
+        file_path: str,
+        repo_root: str,
+        log=None,
+        progress_callback=None,
+        additional_excludes: list[str] | None = None,
+        publication_result: dict[str, Any] | None = None,
     ) -> str:
         """Analyzes a single file within the context of a project. Returns report output path."""
         if publication_result is not None:
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 5aa1566..75bbd19 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -40,6 +40,288 @@ from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
 
 
+def _worker_try_writer_kind(repo_path, writer_kind, result_queue):
+    try:
+        lease = acquire_full_analysis(
+            repo_path,
+            writer_kind=writer_kind,
+            timeout=0.3,
+            poll_interval=0.05,
+        )
+        release_full_analysis(lease)
+        result_queue.put("acquired")
+    except FullAnalysisBusyError:
+        result_queue.put("busy")
+
+
+@pytest.mark.parametrize("method,target_kind", [("analyze_layer", "layer"), ("analyze_single_file", "file")])
+def test_scoped_facade_holds_writer_lease_before_identity_write(
+    tmp_path, isolated_dirs, monkeypatch, method, target_kind
+):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / ("layer" if target_kind == "layer" else "module.py")
+    if target_kind == "layer":
+        target.mkdir()
+    else:
+        target.write_text("VALUE = 1\n", encoding="utf-8")
+    events = []
+    real_acquire = coordinator.acquire_full_analysis
+    real_release = coordinator.release_full_analysis
+
+    def acquire(*args, **kwargs):
+        lease = real_acquire(*args, **kwargs)
+        events.append(("acquire", kwargs["writer_kind"], kwargs["owner"]))
+        return lease
+
+    def release(lease):
+        events.append(("release", lease.owner))
+        return real_release(lease)
+
+    def fail_identity(_root):
+        events.append(("identity",))
+        raise RuntimeError("identity stop")
+
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(coordinator, "release_full_analysis", release)
+    monkeypatch.setattr(facade, "_initialize_repository_identity", fail_identity)
+    with pytest.raises(RuntimeError, match="identity stop"):
+        if target_kind == "layer":
+            facade.ContextorFacade.analyze_layer(str(repo), str(target))
+        else:
+            facade.ContextorFacade.analyze_single_file(str(target), str(repo))
+    assert events == [
+        ("acquire", "scoped_analysis", "scoped_layer_analysis" if target_kind == "layer" else "scoped_single_file_analysis"),
+        ("identity",),
+        ("release", "scoped_layer_analysis" if target_kind == "layer" else "scoped_single_file_analysis"),
+    ]
+
+
+@pytest.mark.parametrize("method,target_kind", [("analyze_layer", "layer"), ("analyze_single_file", "file")])
+def test_scoped_facade_blocks_behind_existing_writer_before_body(
+    tmp_path, isolated_dirs, monkeypatch, method, target_kind
+):
+    from contextor.core.api import facade
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / ("layer" if target_kind == "layer" else "module.py")
+    if target_kind == "layer":
+        target.mkdir()
+    else:
+        target.write_text("VALUE = 1\n", encoding="utf-8")
+    entered = threading.Event()
+    completed = threading.Event()
+    errors = []
+
+    def body(*_args, **_kwargs):
+        entered.set()
+        return "done"
+
+    monkeypatch.setattr(
+        facade.ContextorFacade,
+        f"_analyze_{'layer' if target_kind == 'layer' else 'single_file'}_uncoordinated",
+        staticmethod(body),
+        raising=False,
+    )
+    held = acquire_full_analysis(repo, owner="prior_writer")
+
+    def invoke():
+        try:
+            if target_kind == "layer":
+                assert facade.ContextorFacade.analyze_layer(str(repo), str(target)) == "done"
+            else:
+                assert facade.ContextorFacade.analyze_single_file(str(target), str(repo)) == "done"
+        except Exception as exc:
+            errors.append(exc)
+        finally:
+            completed.set()
+
+    worker = threading.Thread(target=invoke)
+    worker.start()
+    try:
+        assert not entered.wait(0.3)
+    finally:
+        release_full_analysis(held)
+        worker.join(timeout=5)
+    assert completed.is_set()
+    assert not errors
+    assert entered.is_set()
+
+
+def test_scoped_writer_kind_is_accepted(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    lease = acquire_full_analysis(repo, writer_kind="scoped_analysis", timeout=1.0)
+    release_full_analysis(lease)
+
+
+@pytest.mark.parametrize("writer_kind", ["full_analysis", "local_incremental"])
+def test_scoped_facade_excludes_cross_process_canonical_writer(
+    tmp_path, isolated_dirs, monkeypatch, writer_kind
+):
+    from contextor.core.api import facade
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    layer = repo / "layer"
+    layer.mkdir()
+    context = multiprocessing.get_context("spawn")
+
+    def body(*_args, **_kwargs):
+        results = context.Queue()
+        process = context.Process(
+            target=_worker_try_writer_kind,
+            args=(str(repo), writer_kind, results),
+        )
+        process.start()
+        try:
+            process.join(timeout=5)
+            assert process.exitcode == 0
+            assert results.get(timeout=2) == "busy"
+        finally:
+            if process.is_alive():
+                process.terminate()
+                process.join(timeout=3)
+        return "done"
+
+    monkeypatch.setattr(
+        facade.ContextorFacade,
+        "_analyze_layer_uncoordinated",
+        staticmethod(body),
+    )
+    assert facade.ContextorFacade.analyze_layer(str(repo), str(layer)) == "done"
+
+
+@pytest.mark.parametrize("method,target_kind", [("analyze_layer", "layer"), ("analyze_single_file", "file")])
+def test_scoped_facade_invalid_target_does_not_acquire_lease(
+    tmp_path, monkeypatch, method, target_kind
+):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    outside = tmp_path / "outside"
+    outside.mkdir()
+    target = outside if target_kind == "layer" else outside / "module.py"
+    if target_kind == "file":
+        target.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setattr(
+        coordinator,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("invalid target acquired writer lease"),
+    )
+    with pytest.raises(ValueError, match="outside the repository root"):
+        if target_kind == "layer":
+            facade.ContextorFacade.analyze_layer(str(repo), str(target))
+        else:
+            facade.ContextorFacade.analyze_single_file(str(target), str(repo))
+
+
+def test_scoped_facade_non_python_target_does_not_acquire_lease(tmp_path, monkeypatch):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / "notes.txt"
+    target.write_text("notes\n", encoding="utf-8")
+    monkeypatch.setattr(
+        coordinator,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("non-Python target acquired writer lease"),
+    )
+    with pytest.raises(ValueError, match="not a Python file"):
+        facade.ContextorFacade.analyze_single_file(str(target), str(repo))
+
+
+@pytest.mark.parametrize("method,target_kind", [("analyze_layer", "layer"), ("analyze_single_file", "file")])
+def test_scoped_facade_denied_lease_does_not_start_body_or_identity(
+    tmp_path, isolated_dirs, monkeypatch, method, target_kind
+):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / ("layer" if target_kind == "layer" else "module.py")
+    if target_kind == "layer":
+        target.mkdir()
+    else:
+        target.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setattr(
+        coordinator,
+        "acquire_full_analysis",
+        lambda *_a, **_k: (_ for _ in ()).throw(FullAnalysisBusyError("denied")),
+    )
+    monkeypatch.setattr(
+        facade,
+        "_initialize_repository_identity",
+        lambda *_a: pytest.fail("identity mutated after lease denial"),
+    )
+    with pytest.raises(FullAnalysisBusyError, match="denied"):
+        if target_kind == "layer":
+            facade.ContextorFacade.analyze_layer(str(repo), str(target))
+        else:
+            facade.ContextorFacade.analyze_single_file(str(target), str(repo))
+
+
+@pytest.mark.parametrize("method", ["layer", "single_file"])
+def test_scoped_facade_releases_lease_after_report_failure(
+    sample_repo, isolated_dirs, monkeypatch, method
+):
+    from contextor.core.api import facade
+
+    def fail_report(*_args, **_kwargs):
+        raise RuntimeError("report stop")
+
+    if method == "layer":
+        monkeypatch.setattr(facade, "generate_summary_report", fail_report)
+    else:
+        monkeypatch.setattr(facade, "generate_report", fail_report)
+    with pytest.raises(RuntimeError, match="report stop"):
+        if method == "layer":
+            facade.ContextorFacade.analyze_layer(
+                str(sample_repo), str(sample_repo / "core")
+            )
+        else:
+            facade.ContextorFacade.analyze_single_file(
+                str(sample_repo / "core" / "alpha.py"), str(sample_repo)
+            )
+    lease = acquire_full_analysis(sample_repo, writer_kind="local_incremental", timeout=0.5)
+    release_full_analysis(lease)
+
+
+@pytest.mark.parametrize("method", ["layer", "single_file"])
+def test_scoped_facade_releases_lease_after_success(
+    tmp_path, isolated_dirs, monkeypatch, method
+):
+    from contextor.core.api import facade
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / ("layer" if method == "layer" else "module.py")
+    if method == "layer":
+        target.mkdir()
+    else:
+        target.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setattr(
+        facade.ContextorFacade,
+        f"_analyze_{method}_uncoordinated",
+        staticmethod(lambda *_a, **_k: "done"),
+    )
+    if method == "layer":
+        assert facade.ContextorFacade.analyze_layer(str(repo), str(target)) == "done"
+    else:
+        assert facade.ContextorFacade.analyze_single_file(str(target), str(repo)) == "done"
+    lease = acquire_full_analysis(repo, writer_kind="full_analysis", timeout=0.5)
+    release_full_analysis(lease)
+
+
 def test_coordinator_lease_acquisition_and_release(tmp_path: Path):
     repo_dir = tmp_path / "repo1"
     repo_dir.mkdir()
diff --git a/tests/test_live_single_file_reuse.py b/tests/test_live_single_file_reuse.py
index f9726f1..b609cea 100644
--- a/tests/test_live_single_file_reuse.py
+++ b/tests/test_live_single_file_reuse.py
@@ -2,6 +2,10 @@
 
 from types import SimpleNamespace
 from dataclasses import replace
+from copy import copy
+import threading
+
+from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
 
 from contextor.core.reporting_engine.canonical_artifacts import (
     canonical_artifact_report,
@@ -124,6 +128,64 @@ def test_single_file_reports_accepted_recovery_without_changing_string_return(
     }
 
 
+def test_scoped_single_file_publishes_to_real_live_server_under_writer_lease(
+    sample_repo, isolated_dirs, monkeypatch
+):
+    import contextor.core.api.facade as facade_module
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    target = sample_repo / "core" / "alpha.py"
+    ContextorFacade.analyze_project(str(sample_repo))
+    resolved = facade_module.resolve_authoritative_repository_state(str(sample_repo))
+    assert resolved is not None
+    initial_revision = max(0, int(getattr(resolved.state, "revision", 0)) - 1)
+    initial_state = copy(resolved.state)
+    initial_state.revision = initial_revision
+    server = CanonicalLiveServer(state=initial_state, revision=initial_revision)
+    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
+    server_thread.start()
+    client = LiveStateClient(server.endpoint)
+    original_hydrate = facade_module.hydrate_repository_engine
+    original_publish = client.publish
+    observed = []
+
+    def hydrate_with_server(root):
+        hydrated = original_hydrate(root)
+        return replace(hydrated, client=client)
+
+    def publish_while_held(*args, **kwargs):
+        observed.append("publish")
+        try:
+            coordinator.acquire_full_analysis(
+                sample_repo, timeout=0.0, writer_kind="local_incremental"
+            )
+        except coordinator.FullAnalysisBusyError:
+            observed.append("lease_held")
+        else:
+            pytest.fail("LIVE publication ran outside scoped lease")
+        return original_publish(*args, **kwargs)
+
+    import pytest
+    monkeypatch.setattr(facade_module, "hydrate_repository_engine", hydrate_with_server)
+    monkeypatch.setattr(client, "publish", publish_while_held)
+    target.write_text(
+        target.read_text(encoding="utf-8").replace("MAX_ITEMS = 10", "MAX_ITEMS = 12"),
+        encoding="utf-8",
+    )
+    publication = {}
+    try:
+        output = ContextorFacade.analyze_single_file(
+            str(target), str(sample_repo), publication_result=publication
+        )
+        assert output.endswith("single_core.alpha.json")
+        assert observed == ["publish", "lease_held"]
+        assert publication["status"] == "success", publication
+        assert publication["revision"] == initial_revision + 1
+    finally:
+        client.request("shutdown")
+        server_thread.join(timeout=5)
+
+
 def test_single_file_resync_state_rejects_state_only_path(
     sample_repo, isolated_dirs, monkeypatch
 ):
```
