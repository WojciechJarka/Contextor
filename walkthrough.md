# SP-LIVE-R3 — PID REUSE RECOVERY FIX

## PREFLIGHT

- Zaakceptowany preflight SP-LIVE-R3: HEAD `97d5e824b638c0152fac6d7ef48b551ad9ba74ba`; przed edycją jedyną zmianą w worktree było wcześniejsze `walkthrough.md`. Oba pliki docelowe były czyste, a literalne anchory zgadzały się z preflightem.
- Contextor MCP preflight: `repo_id=ctx_8efc50d8`, revision 1431, canonical state fresh, provenance `snapshot`, global `workspace_sync=unverified`, `resync_required=false`. Konteksty obu plików wskazywały revision 1431, per-file `workspace_sync=verified` przed zmianą, syntax `checked_and_none`.
- Po zmianie testy wykonano przez `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` — CPython 3.15.2.

## EXACT_IMPLEMENTATION

- `contextor/core/live_state/runtime.py`: w `AuthorityLivenessVerifier.verify()`, bezpośrednio po `endpoint_is_dead = endpoint_alive is False`, wstawiono dokładnie zatwierdzony warunek `endpoint_pid_reused` i wynik `LivenessResult.stale`. Pozostałe gałęzie verifiera są bez zmian.
- `tests/live_state/test_runtime_lease.py`: dokładny helper i trzy definicje testowe przekazane w SP-R3 dopisano na końcu, po istniejącym teście w linii 480. Istniejące testy/asercje pozostawiono bez zmian.
- `contextor/core/live_state/runtime_lease.py` nie zmieniano. `issues.md`, `audyt.txt` i Spiral Prophet nie zmieniano.
- Rzeczywisty diff Git zawiera tylko wskazany blok produkcyjny i dodany blok testowy. Git wyświetlił ostrzeżenie o roboczych LF normalizowanych do CRLF; diff treści nie pokazuje innych zmian.

## PID_REUSE_MECHANISM

- Nowy warunek wymaga jednocześnie: metadanych endpointu dopasowanych do lease; `ConnectionRefusedError`; pierwszego probe żywego PID z dostępnym CreationTime różnym od lease; drugiego probe żywego PID endpointu z dostępnym CreationTime różnym od zapisanej tożsamości endpointu.
- `LiveStateClient.request()` wywołuje `multiprocessing.connection.Client` i po trace re-raise zachowuje typ błędu (`contextor/core/live_state/ipc.py:2937-2969`); `authority_status()` deleguje do request (`:2977-2978`). To pozwala warunkowi odróżnić odmowę połączenia od timeout/reset i innych błędów.
- Wynik ustawia `STALE` z `process_alive=True`, `process_identity_matches=False`, endpoint niedostępny i `endpoint_evidence_verified=True`. Istniejący kontrakt `confirmed_stale` w `runtime_lease.py:266-271` uznaje to za potwierdzony stale bez zmiany API lease.
- Nie dodano identyfikatora repozytorium, ścieżki ani wyjątku specyficznego dla Contextora do logiki warunku.

## FAIL_CLOSED_NEGATIVE_CASES

Nowy test parametryzowany pokrywa osiem przypadków: nowa tożsamość PID + refused/dopasowany endpoint daje STALE; zgodna tożsamość, brak któregokolwiek CreationTime, druga tożsamość zgodna z endpointem, timeout, reset oraz niedopasowany endpoint dają UNKNOWN. Osobny test utrzymuje istniejący kontrakt martwego PID i refused endpoint jako STALE/confirmed.

To są syntetyczne wejścia verifiera. Testy nie wykonują rzeczywistego połączenia do LIVE ani nie ingerują w trwałe lease. Test fencingowy używa `_domain(tmp_path)` i `_manager` z istniejącego pliku; weryfikuje realny acquire/fence na izolowanym stanie testowym.

## LEASE_FENCING_REGRESSION

- `RuntimeLeaseManager.acquire()` przechodzi do fencing wyłącznie, gdy `evidence.confirmed_stale` (`contextor/core/live_state/runtime_lease.py:1427-1441`). `_fence_stale_lease` sprawdza zgodność generation i service instance, zapisuje fenced record, usuwa claim/lease i emituje event (`:1279-1305`).
- `test_sp_live_r3_reused_pid_fences_old_generation` otrzymuje stale z nowego verifier-helpera, przekazuje ten wynik do `ScriptedVerifier` i sprawdza wywołanie verifiera dla starej lease, generation +1 oraz nowy service instance. Potwierdza ścieżkę fencing bez uruchamiania rzeczywistego LIVE.

## TARGETED_TESTS

Uruchomiono wyłącznie wskazany plik testowy i testy pasujące do:

```text
sp_live_r3
stale_recovery_increments_generation_and_fences_old_service
pid_reuse_with_same_pid_but_different_start_identity_is_stale
ambiguous_timeout_or_busy_liveness_rejects_takeover
confirmed_dead_process_and_unavailable_endpoint_allow_stale_takeover
default_liveness_does_not_fabricate_endpoint_stale_evidence
```

Wynik: **18 passed, 20 deselected in 1.88s** na CPython 3.15.2. Nie uruchomiono pełnego pytest.

## MCP_POST_CHANGE_AUDIT

- Odczytowy `get_project_architecture(fields=[])`: revision nadal 1431; `provenance=snapshot`, canonical state fresh, global `workspace_sync=unverified`, `resync_required=false`. Zbiorcze syntax errors: 0 (availability fresh); cycles: 16 (availability fresh); cycle semantics: 2 cyclic SCC, 53 cyclic modules, status fresh — wszystkie te wartości pochodzą ze snapshotu revision 1431.
- `get_file_edit_context` obu plików po zmianie: `workspace_sync=out_of_sync`, revision 1431, provenance snapshot; advisory mówi, że pliki na dysku zmieniły się po utworzeniu canonical revision. Syntax projection nadal pokazuje `checked_and_none`, ale jej revision/snapshot nie uwzględnia tych zmian i nie jest post-change LIVE syntax proof.
- MCP `get_source_range` dla `runtime.py:457-491` zwrócił nowy blok w aktualnym widoku źródła; potwierdza to literalny anchor/tekst, nie adopcję przez załadowany proces. Nie wywołano `update_file`, FULL ani restartu. Runtime loaded-code adoption pozostaje **NOT_CONFIRMED**; przeładowanie procesu będzie wymagane, aby dowieść adopcji kodu runtime.
- Graf, cykle i resync z revision 1431 są raportowane jako stan snapshotu; `resync_required=false` nie znosi per-file `out_of_sync` i nie oznacza LIVE-ready.

## FINAL_VERDICT

**R3_PASS** — literalny patch trafił w zatwierdzony anchor, testy nowych i wskazanych istniejących przypadków przeszły, a niezależna kontrola kodu potwierdza ograniczenie nowej klasyfikacji do potwierdzonej różnicy start identity i odmowy połączenia. PASS dotyczy implementacji oraz ukierunkowanego zestawu testów, nie wdrożenia do procesu LIVE. `LIVE_ADOPTION=NOT_CONFIRMED`; MCP post-change pozostaje snapshot revision 1431 z targetami `out_of_sync`.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py`
- `C:\Temp\Contextor_Repo\tests\live_state\test_runtime_lease.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` — raport wymagany zadaniem.

## FULL_DIFFS

Poniżej pełny rzeczywisty diff Git plików produkcyjnego i testowego. Diff walkthrough pominięty jako diff samego raportu.

```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 64a4ff6..0276375 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -461,6 +461,33 @@ class AuthorityLivenessVerifier:
                 endpoint_alive = None
                 endpoint_creation = None
             endpoint_is_dead = endpoint_alive is False
+            endpoint_pid_reused = (
+                endpoint_matches
+                and isinstance(exc, ConnectionRefusedError)
+                and alive is True
+                and creation_time is not None
+                and not process_matches
+                and endpoint_alive is True
+                and endpoint_creation is not None
+                and str(endpoint_creation)
+                != endpoint.process_start_identity
+            )
+            if endpoint_pid_reused:
+                return finish(
+                    LivenessResult.stale(
+                        process_alive=True,
+                        process_identity_matches=False,
+                        endpoint_available=False,
+                        endpoint_matches=True,
+                        reason=(
+                            "recorded authority PID identity was "
+                            "replaced and endpoint refused connection"
+                        ),
+                        endpoint_evidence_verified=True,
+                    ),
+                    endpoint,
+                    exc,
+                )
             if not endpoint_matches and process_stale and endpoint_is_dead:
                 return finish(LivenessResult.stale(
                     process_alive=bool(alive),
diff --git a/tests/live_state/test_runtime_lease.py b/tests/live_state/test_runtime_lease.py
index 97bcb47..8e27f0c 100644
--- a/tests/live_state/test_runtime_lease.py
+++ b/tests/live_state/test_runtime_lease.py
@@ -478,3 +478,180 @@ def test_runtime_lease_serialization_round_trip_and_test_root_isolation(tmp_path
 def test_process_identity_requires_start_token_and_is_not_pid_only():
     with pytest.raises(RuntimeLeaseError):
         ProcessIdentity(os.getpid(), "")
+
+
+def _sp_live_r3_verify_case(
+    monkeypatch,
+    *,
+    before,
+    after,
+    before_alive=True,
+    after_alive=True,
+    error_type=ConnectionRefusedError,
+    domain_matches=True,
+    lease=None,
+):
+    from types import SimpleNamespace
+    from contextor.core.live_state import runtime
+
+    if lease is None:
+        lease = SimpleNamespace(
+            service_pid=45123,
+            service_instance_id="synthetic-instance",
+            lease_generation=7,
+            process_start_identity="100",
+        )
+
+    endpoint = SimpleNamespace(
+        pid=lease.service_pid,
+        service_instance_id=lease.service_instance_id,
+        lease_generation=lease.lease_generation,
+        process_start_identity=lease.process_start_identity,
+        fingerprint=lambda: "synthetic-fingerprint",
+    )
+
+    observations = iter([
+        (before, before_alive),
+        (after, after_alive),
+    ])
+    observed_pids = []
+
+    def process_identity(pid):
+        observed_pids.append(pid)
+        creation, alive = next(observations)
+        return "synthetic-process", creation, alive
+
+    class RefusingClient:
+        def __init__(self, _endpoint):
+            pass
+
+        def authority_status(self):
+            raise error_type("synthetic transport failure")
+
+    monkeypatch.setattr(
+        runtime, "_process_identity", process_identity
+    )
+    monkeypatch.setattr(
+        runtime, "_read_endpoint",
+        lambda _root, strict=True: endpoint,
+    )
+    monkeypatch.setattr(
+        runtime, "_endpoint_matches_domain",
+        lambda _endpoint, _domain: domain_matches,
+    )
+    monkeypatch.setattr(
+        runtime, "LiveStateClient", RefusingClient,
+    )
+    monkeypatch.setattr(
+        runtime, "_safe_trace_event",
+        lambda *_args, **_kwargs: None,
+    )
+
+    result = runtime.AuthorityLivenessVerifier(
+        SimpleNamespace(repo_root="synthetic-root")
+    ).verify(lease)
+
+    assert observed_pids == [
+        lease.service_pid, lease.service_pid
+    ]
+    return result
+
+
+@pytest.mark.parametrize(
+    "before,after,error_type,matches,expected",
+    [
+        (
+            "200", "200", ConnectionRefusedError,
+            True, LivenessStatus.STALE,
+        ),
+        (
+            "100", "100", ConnectionRefusedError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            None, "200", ConnectionRefusedError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            "200", None, ConnectionRefusedError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            "200", "100", ConnectionRefusedError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            "200", "200", TimeoutError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            "200", "200", ConnectionResetError,
+            True, LivenessStatus.UNKNOWN,
+        ),
+        (
+            "200", "200", ConnectionRefusedError,
+            False, LivenessStatus.UNKNOWN,
+        ),
+    ],
+)
+def test_sp_live_r3_pid_identity_and_transport_gate(
+    monkeypatch, before, after,
+    error_type, matches, expected,
+):
+    result = _sp_live_r3_verify_case(
+        monkeypatch,
+        before=before,
+        after=after,
+        error_type=error_type,
+        domain_matches=matches,
+    )
+    assert result.status is expected
+    assert result.confirmed_stale is (
+        expected is LivenessStatus.STALE
+    )
+
+
+def test_sp_live_r3_dead_pid_existing_contract(
+    monkeypatch,
+):
+    result = _sp_live_r3_verify_case(
+        monkeypatch,
+        before=None,
+        after=None,
+        before_alive=False,
+        after_alive=False,
+    )
+    assert result.status is LivenessStatus.STALE
+    assert result.confirmed_stale is True
+
+
+def test_sp_live_r3_reused_pid_fences_old_generation(
+    tmp_path, monkeypatch,
+):
+    domain = _domain(tmp_path)
+    old_manager = _manager(domain)
+    old_lease = old_manager.acquire()
+
+    result = _sp_live_r3_verify_case(
+        monkeypatch,
+        before="different-process-start",
+        after="different-process-start",
+        lease=old_lease,
+    )
+
+    assert result.status is LivenessStatus.STALE
+    assert result.confirmed_stale is True
+
+    verifier = ScriptedVerifier(result)
+    new_manager = _manager(domain, verifier=verifier)
+    new_lease = new_manager.acquire()
+
+    assert verifier.calls == [old_lease]
+    assert (
+        new_lease.lease_generation
+        == old_lease.lease_generation + 1
+    )
+    assert (
+        new_lease.service_instance_id
+        != old_lease.service_instance_id
+    )
```
