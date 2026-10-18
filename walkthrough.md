TASK=CONTEXTOR_C38E2Q_R3_FINAL_AUTHORITY_VERIFICATION
MODE=CONTROLLED IMPLEMENTATION CONTINUATION

HEAD_BEFORE=b99a20a27f6210061bdf082e9081fcf1f5657de1
HEAD_AFTER=b99a20a27f6210061bdf082e9081fcf1f5657de1

FILES_CHANGED:
- contextor/mcp/tools/get_analysis_status.py
- tests/mcp/tools/test_analysis_status_concurrency.py
walkthrough.md jest wyłącznie raportem.

ROOT_CAUSE:
CODE_PATH_PROVED: dotychczasowa ścieżka utrwalała terminalny wynik classify_publication_receipt po mutation_status bez drugiego authority_status. Warunek isinstance(job_id, str) oraz bool(lookup_job_id) akceptował pusty/whitespace-only identyfikator w niewłaściwych punktach.

IMPLEMENTATION_DETAILS:
- Po terminalnej klasyfikacji wykonywany jest drugi read-only authority_status. Trwały status terminalny jest zapisany tylko przy status=ok oraz pełnej, niepustej i dokładnie zgodnej tożsamości authority, endpointu i durable expected identity.
- Jawny mismatch po receipt zwraca unverified_authority_changed z revision=None bez utrwalenia terminalnego rozstrzygnięcia. Niedostępna/niewłaściwie ukształtowana authority pozostawia pending_verification.
- Brakujący, pusty i whitespace-only durable job_id kieruje do dotychczasowego lookup. Lookup job_id musi być niepusty po strip. Oryginalne poprawne identyfikatory pozostają niezmienione.

AUTHORITY_RACE_PROOF:
CONTRACT_PROVED przez kontrolowane sekwencje testów R3-T01–T06: authority zgodna przed i po terminalnym receipt zezwala na zapis. Zmiana service_instance_id albo process_start_identity po receipt blokuje terminalny success. Timeout, None, malformed, missing identity i status!=ok pozostawiają pending. To samo fence obejmuje failed i recovery_required. Każdy test odczytuje także trwały rekord.

EMPTY_JOB_ID_PROOF:
CONTRACT_PROVED R3-T07–T09: pusty i whitespace-only durable job_id uruchamiają canonical-key lookup; poprawne lookup job_id prowadzi do terminalnego success. Pusty i whitespace-only wynik lookup nie jest utrwalany ani przekazywany do mutation_status. Walidacja exact requested_state_id/revision oraz canonical idempotency key pozostała aktywna.

LATER_RECOVERY_PROOF:
CONTRACT_PROVED R3-T10: pierwszy odczyt kończy się pending_verification po timeout drugiej authority; trwały expected identity/key pozostaje; drugi odczyt uzyskuje zgodną authority i ten sam terminalny receipt, zapisuje success bez submit/publish i bez lookup dla prawidłowego durable job_id.

RESULTS R3-T01–R3-T10:
R3-T01 PASS; R3-T02 PASS; R3-T03 PASS; R3-T04 PASS; R3-T05 PASS (4 warianty); R3-T06 PASS (6 wariantów); R3-T07 PASS; R3-T08 PASS; R3-T09 PASS (2 warianty); R3-T10 PASS.

TARGETED_TEST_RESULTS:
- .venv/Scripts/python.exe -m pytest tests/mcp/tools/test_analysis_status_concurrency.py -q: 55 passed, 1 unrelated AuthlibDeprecationWarning, 7.22s. Obejmuje istniejące testy R2.
- .venv/Scripts/python.exe -m pytest tests/test_async_publication_receipt.py tests/test_live_mutation_coordinator.py::test_duplicate_idempotency_key_reuses_job_and_executes_once tests/test_live_mutation_coordinator.py::test_unknown_and_invalid_mutation_job_status_fail_closed tests/test_durable_verified_publish.py::test_opt_in_ack_confirms_exact_installed_generation_without_mutation tests/test_durable_verified_publish.py::test_opt_in_ack_rejects_nonmatching_or_unavailable_generation -q: 18 passed, 4.00s.
- git diff --check: bez błędów. Nie uruchamiano pełnego suite.

CANONICAL_INVARIANTS:
Nie wywołano FULL, publish ani update_file. Read-only reconciliation zachowuje canonical idempotency key i expected identity. Nie zmieniono classify_publication_receipt. Contextor pokazuje niezmienione 6 importów modułu produkcyjnego, 5 bezpośrednich konsumentów i brak świeżych błędów składni. Cycle semantics pozostaje stale jako odrębna istniejąca rodzina i nie jest objęta R3.

WATCHER_EVENTS:
DIRECT_EVIDENCE: desktop_watcher update_file revision 605 UPDATED dla get_analysis_status.py; revision 606 UPDATED dla test_analysis_status_concurrency.py; revision 607 UNCHANGED dla pliku testowego. Eventy po cursor 604 mają continuity=continuous, resync_required=false, truncated=false.
LIVE_REVISION_BEFORE_AFTER=604/607
LIVE_VERIFICATION:
Contextor get_file_edit_context dla modułu produkcyjnego: canonical revision 607, canonical_state=fresh, workspace_sync=verified, syntax_diagnostics=checked_and_none; testowego: canonical revision 607, workspace_sync=verified, syntax_diagnostics=checked_and_none. Brak nieoczekiwanej zmiany zależności w zakresie obserwowanych importów/consumerów. Event blast_radius_state=deferred; nie stanowi dowodu pełnego materializowanego blast radius.

MCP_BACKEND_RESTART_REQUIRED=YES — zmieniono kod publicznego narzędzia MCP ładowany przez proces MCP; testy Python importują nowy kod, ale nie dowodzą reloadu działającego procesu. Restartu nie wykonano.
LIVE_SERVICE_RESTART_REQUIRED=NO dla tej zmiany — zmieniono moduł adaptera MCP oraz testy, bez kodu serwera LIVE. Nie wykonano restartu.
RUNTIME_CERTIFICATION=UNKNOWN do manualnego reloadu MCP i sprawdzenia świeżości nowego procesu.

FINAL_VERDICT=PARTIAL — kod i focused gates PASS; runtime MCP nie został przeładowany ani certyfikowany. Brak podstaw do FINAL PASS runtime.

FULL_DIFFS:
diff --git a/contextor/mcp/tools/get_analysis_status.py b/contextor/mcp/tools/get_analysis_status.py
index 2d6d115..42d13de 100644
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -174,7 +174,7 @@ def get_analysis_status(
                     authority = None
         if client is not None and isinstance(authority, dict) and authority.get("status") == "ok":
             mutation_job_id = job.get("live_publish_job_id")
-            if not isinstance(mutation_job_id, str):
+            if not isinstance(mutation_job_id, str) or not mutation_job_id.strip():
                 state_id = job["live_publish_expected_state_id"]
                 revision = job["live_publish_expected_revision"]
                 stored_key = job.get("live_publish_idempotency_key")
@@ -197,7 +197,7 @@ def get_analysis_status(
                         isinstance(lookup, dict)
                         and lookup.get("status") == "ok"
                         and isinstance(lookup.get("job_id"), str)
-                        and bool(lookup.get("job_id"))
+                        and bool(lookup.get("job_id").strip())
                         and lookup.get("requested_state_id") == state_id
                         and type(lookup.get("requested_revision")) is int
                         and lookup.get("requested_revision") == revision
@@ -208,7 +208,7 @@ def get_analysis_status(
                             analysis_jobs._write_analysis_job(root, job)
                         except OSError:
                             pass
-            if isinstance(mutation_job_id, str) and mutation_job_id:
+            if isinstance(mutation_job_id, str) and mutation_job_id.strip():
                 try:
                     receipt = client.mutation_status(mutation_job_id)
                 except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
@@ -223,8 +223,43 @@ def get_analysis_status(
                     idempotency_key=job.get("live_publish_idempotency_key"),
                 )
                 if classified["live_publish_status"] in {"success", "failed", "recovery_required"}:
-                    job = {**job, **classified}
-                    analysis_jobs._write_analysis_job(root, job)
+                    try:
+                        final_authority = client.authority_status()
+                    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                        final_authority = None
+                    final_endpoint_service = client.endpoint.service_instance_id
+                    final_endpoint_process = client.endpoint.process_start_identity
+                    final_service = (
+                        final_authority.get("service_instance_id")
+                        if isinstance(final_authority, dict) and final_authority.get("status") == "ok"
+                        else None
+                    )
+                    final_process = (
+                        final_authority.get("process_start_identity")
+                        if isinstance(final_authority, dict) and final_authority.get("status") == "ok"
+                        else None
+                    )
+                    final_identity_available = (
+                        isinstance(final_service, str) and bool(final_service)
+                        and isinstance(final_process, str) and bool(final_process)
+                        and isinstance(final_endpoint_service, str) and bool(final_endpoint_service)
+                        and isinstance(final_endpoint_process, str) and bool(final_endpoint_process)
+                    )
+                    if final_identity_available and (
+                        final_service != expected_service
+                        or final_process != expected_process
+                        or final_service != final_endpoint_service
+                        or final_process != final_endpoint_process
+                    ):
+                        job = {
+                            **job,
+                            "live_publish_status": "unverified_authority_changed",
+                            "live_publish_revision": None,
+                            "live_publish_warning": "LIVE authority identity changed after receipt verification.",
+                        }
+                    elif final_identity_available:
+                        job = {**job, **classified}
+                        analysis_jobs._write_analysis_job(root, job)
     public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
     if public_job.get("status") == "completed":
         diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
diff --git a/tests/mcp/tools/test_analysis_status_concurrency.py b/tests/mcp/tools/test_analysis_status_concurrency.py
index 4ab3c0e..4f65224 100644
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -94,6 +94,273 @@ def _status_response(root: Path, job: dict) -> dict:
     return json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
 
 
+def _r3_reconcile(
+    tmp_path, monkeypatch, *,
+    authority_sequence, receipt_state="completed", response=None,
+    durable_job_id="mu-exact", lookup_job_id="mu-exact",
+):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    job["live_publish_job_id"] = durable_job_id
+    analysis_jobs._write_analysis_job(tmp_path, job)
+    calls = []
+    replies = iter(authority_sequence)
+    expected_authority = {
+        "status": "ok", "service_instance_id": "service",
+        "process_start_identity": "process", "repo_id": "repo-id",
+    }
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            calls.append("authority")
+            reply = next(replies)
+            if isinstance(reply, BaseException):
+                raise reply
+            return expected_authority if reply == "same" else reply
+
+        def lookup_committed_publish(self, **kwargs):
+            calls.append("lookup")
+            assert kwargs == {
+                "idempotency_key": job["live_publish_idempotency_key"],
+                "state_id": "sid", "revision": 7,
+            }
+            return {
+                "status": "ok", "job_id": lookup_job_id,
+                "requested_state_id": "sid", "requested_revision": 7,
+            }
+
+        def mutation_status(self, mutation_job_id):
+            calls.append("mutation")
+            assert mutation_job_id == "mu-exact"
+            return {
+                "status": "ok", "job_id": mutation_job_id,
+                "requested_state_id": "sid", "requested_revision": 7,
+                "state": receipt_state,
+                "response": response if response is not None else {
+                    "status": "ok", "revision": 7,
+                },
+            }
+
+        def submit_committed_publish(self, **kwargs):
+            raise AssertionError("read-only reconciliation must not publish")
+
+    monkeypatch.setattr(
+        live_state_module, "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
+    )
+    result = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    return job, result, stored, calls
+
+
+def _r3_assert_identity_preserved(job, stored):
+    assert stored["live_publish_idempotency_key"] == job["live_publish_idempotency_key"]
+    assert stored["live_publish_service_instance_id"] == "service"
+    assert stored["live_publish_process_start_identity"] == "process"
+    assert stored["live_publish_expected_state_id"] == "sid"
+    assert stored["live_publish_expected_revision"] == 7
+
+
+def test_r3_t01_matching_final_authority_allows_success(tmp_path, monkeypatch):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", "same"]
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
+    assert result["live_publish_revision"] == stored["live_publish_revision"] == 7
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t02_final_service_replacement_fences_success(tmp_path, monkeypatch):
+    replacement = {
+        "status": "ok", "service_instance_id": "other",
+        "process_start_identity": "process",
+    }
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", replacement]
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert result["live_publish_revision"] is None
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t03_final_process_replacement_fences_success(tmp_path, monkeypatch):
+    replacement = {
+        "status": "ok", "service_instance_id": "service",
+        "process_start_identity": "other",
+    }
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", replacement]
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert result["live_publish_revision"] is None
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t04_final_authority_timeout_stays_pending(tmp_path, monkeypatch):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", TimeoutError("timeout")]
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
+    assert result["live_publish_revision"] is None
+    assert stored["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, stored)
+
+
+@pytest.mark.parametrize("final_authority", [
+    None, "malformed", {"status": "ok", "service_instance_id": "service"},
+    {"status": "unavailable"},
+], ids=["none", "malformed", "missing-identity", "not-ok"])
+def test_r3_t05_unknown_final_authority_stays_pending(
+    tmp_path, monkeypatch, final_authority
+):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", final_authority]
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
+    assert result["live_publish_revision"] is None
+    assert stored["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, stored)
+
+
+@pytest.mark.parametrize("receipt_state,response,expected", [
+    ("failed", None, "failed"),
+    ("completed", {"status": "ok", "revision": 7, "resync_required": True}, "recovery_required"),
+])
+@pytest.mark.parametrize("final_authority,accepted", [
+    ("same", True),
+    ({"status": "ok", "service_instance_id": "other",
+      "process_start_identity": "process"}, False),
+    (None, False),
+])
+def test_r3_t06_other_terminal_states_require_final_authority(
+    tmp_path, monkeypatch, receipt_state, response, expected, final_authority, accepted
+):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", final_authority],
+        receipt_state=receipt_state, response=response,
+    )
+    assert calls == ["authority", "mutation", "authority"]
+    if accepted:
+        assert result["live_publish_status"] == stored["live_publish_status"] == expected
+    else:
+        assert result["live_publish_status"] == (
+            "pending_verification" if final_authority is None
+            else "unverified_authority_changed"
+        )
+        assert stored["live_publish_status"] == "pending_verification"
+        assert stored["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t07_empty_durable_job_id_recovers_by_lookup(tmp_path, monkeypatch):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", "same"], durable_job_id=""
+    )
+    assert calls == ["authority", "lookup", "mutation", "authority"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
+    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == "mu-exact"
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t08_whitespace_durable_job_id_recovers_by_lookup(tmp_path, monkeypatch):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same", "same"], durable_job_id="  "
+    )
+    assert calls == ["authority", "lookup", "mutation", "authority"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
+    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == "mu-exact"
+    _r3_assert_identity_preserved(job, stored)
+
+
+@pytest.mark.parametrize("lookup_job_id", ["", "  "], ids=["empty", "whitespace"])
+def test_r3_t09_invalid_lookup_job_id_is_not_persisted(
+    tmp_path, monkeypatch, lookup_job_id
+):
+    job, result, stored, calls = _r3_reconcile(
+        tmp_path, monkeypatch, authority_sequence=["same"],
+        durable_job_id="", lookup_job_id=lookup_job_id,
+    )
+    assert calls == ["authority", "lookup"]
+    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
+    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == ""
+    _r3_assert_identity_preserved(job, stored)
+
+
+def test_r3_t10_later_read_only_recovery_after_final_timeout(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    job["live_publish_job_id"] = "mu-exact"
+    analysis_jobs._write_analysis_job(tmp_path, job)
+    calls = []
+    replies = iter(["same", TimeoutError("timeout"), "same", "same"])
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            calls.append("authority")
+            reply = next(replies)
+            if isinstance(reply, BaseException):
+                raise reply
+            return {
+                "status": "ok", "service_instance_id": "service",
+                "process_start_identity": "process", "repo_id": "repo-id",
+            }
+
+        def mutation_status(self, mutation_job_id):
+            calls.append("mutation")
+            assert mutation_job_id == "mu-exact"
+            return {
+                "status": "ok", "job_id": mutation_job_id, "state": "completed",
+                "requested_state_id": "sid", "requested_revision": 7,
+                "response": {"status": "ok", "revision": 7},
+            }
+
+        def submit_committed_publish(self, **kwargs):
+            raise AssertionError("status must never publish")
+
+        def lookup_committed_publish(self, **kwargs):
+            raise AssertionError("valid durable job ID needs no lookup")
+
+    monkeypatch.setattr(
+        live_state_module, "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
+    )
+    first = _status_response(tmp_path, job)
+    first_stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert first["live_publish_status"] == first_stored["live_publish_status"] == "pending_verification"
+    assert first["live_publish_revision"] is None
+    _r3_assert_identity_preserved(job, first_stored)
+
+    second = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert calls == ["authority", "mutation", "authority", "authority", "mutation", "authority"]
+    assert second["live_publish_status"] == stored["live_publish_status"] == "success"
+    assert second["live_publish_revision"] == stored["live_publish_revision"] == 7
+    _r3_assert_identity_preserved(job, stored)
+
+
 @pytest.mark.parametrize(
     "authority_result",
     [
