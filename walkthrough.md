# P17-F2-I1 — ochrona LIVE IPC authkey przez Windows DPAPI CurrentUser

## PREFLIGHT

- DIRECT_EVIDENCE — ponowny preflight przez Contextor MCP przed edycją: contextor.core.live_state.runtime i tests.test_live_authority_bootstrap miały canonical_revision=1581, canonical_state=fresh, workspace_sync=verified, provenance=live. Zakresy źródła zgłaszały syntax_errors=0.
- DIRECT_EVIDENCE — HEAD przed edycją: 6d77d43ebda9f67fbdb711f27bc4eecdea014c18. Git status: ## main...origin/main, M walkthrough.md; żaden z dwóch docelowych plików nie miał lokalnych zmian.
- DIRECT_EVIDENCE — wszystkie kotwice z promptu zgadzały się: runtime.py import argparse w linii 5; import repo_cache_dir w linii 22; payload/try w _write_endpoint_atomic w liniach 897-898; LiveEndpoint i authkey_hex w _read_endpoint w liniach 265-269; test publikacji endpointu kończy się w linii 187, a następna funkcja zaczyna się w linii 190.
- DIRECT_EVIDENCE — helpery DPAPI odpowiadały P17-F2-D2: BackendSecretError jest klasą wyjątku RuntimeError w mcp_backend_secret.py:39-40; _protect_windows i _unprotect_windows istnieją z sygnaturą bytes -> bytes w mcp_backend_secret.py:255-363.
- DIRECT_EVIDENCE — przed zmianą sprawdzony import chain: mcp_backend_secret → mcp_backend_state → core.paths i mcp_process_registry; repository_identity zależy od repository_storage. runtime już importuje core.paths i mcp_process_registry. Package initializers nie wprowadzają ścieżki z tych helperów z powrotem do runtime.
- INFERENCE — planowany import runtime → mcp_backend_secret nie tworzył cyklu w sprawdzonym grafie ani importach źródłowych. Późniejszy import runtime i testy Windows potwierdziły wykonanie tej ścieżki w CPython.
- DIRECT_EVIDENCE — brak SOURCE_DRIFT; patch zastosowano wyłącznie w contextor/core/live_state/runtime.py i tests/test_live_authority_bootstrap.py. Nie zmieniano ipc.py, mcp_backend_secret.py ani paths.py.
- DIRECT_EVIDENCE — nie wykonano FULL, commit, push, staging, restartu ani połączenia z produkcyjnym LIVE.

## EXACT_IMPLEMENTATION

DIRECT_EVIDENCE — do runtime.py dodano importy base64 i binascii po argparse oraz BackendSecretError, _protect_windows, _unprotect_windows po imporcie repo_cache_dir (linie 5-29).

DIRECT_EVIDENCE — _write_endpoint_atomic (runtime.py:927-949) tworzy świeży payload z endpoint.to_dict(); wyłącznie na Windows zastępuje pole authkey_hex prefiksem dpapi: i base64 z DPAPI ciphertext. Istniejące temporary file, flush/fsync, os.replace i cleanup pozostały niezmienione.

DIRECT_EVIDENCE — _read_endpoint (runtime.py:231-330) na Windows wymaga wartości str z prefiksem dpapi:, dekoduje base64 z validate=True, odszyfrowuje DPAPI bytes i dopiero potem tworzy LiveEndpoint z plaintextowym hex w pamięci. Nie ma ścieżki fallback do plaintext endpointu na Windows. Pozostała walidacja endpoint.authkey i pierwotny except zostały zachowane.

DIRECT_EVIDENCE — poza Windows zapis nadal serializuje pole authkey_hex bez transformacji, a odczyt przekazuje istniejącą wartość do LiveEndpoint. Nie dodano formatu dyskowego dla innych systemów.

DIRECT_EVIDENCE — tests/test_live_authority_bootstrap.py:191-262 zawiera dokładnie dwie żądane funkcje Windows-only; wstawiono je po teście publikacji endpointu i przed testem attach/second Desktop.

## DPAPI_DISK_CONTRACT

- DIRECT_EVIDENCE — źródłowy obiekt LiveEndpoint nie jest modyfikowany przez writer: endpoint.to_dict() zwraca nowy słownik; transformacja przypisuje wyłącznie payload["authkey_hex"]. DPAPI otrzymuje endpoint.authkey, a nie tekstowe pole bezpośrednio.
- DIRECT_EVIDENCE — fingerprint zdefiniowany w niezmienionym ipc.py nadal liczy SHA-256 nad JSON LiveEndpoint.identity_payload(), zawierającym oryginalne authkey_hex. Nie zmieniono ipc.py ani kodu lease; produkcyjna weryfikacja endpoint/lease w runtime.py pozostała poza diffem.
- CODE_PATH_PROVED — parser odszyfrowuje pole przed konstrukcją LiveEndpoint. Zatem w pamięci klient i usługa nadal otrzymują ten sam authkey_hex i tę samą bajtową właściwość authkey; prefiks dpapi: istnieje tylko w słowniku serializowanym na dysk.
- DIRECT_EVIDENCE — test test_live_endpoint_authkey_is_protected_on_disk sprawdza prefiks dpapi:, brak syntetycznego tekstu testowego authkey w JSON i równość odczytanego endpointu z wejściowym obiektem.
- DIRECT_EVIDENCE — test test_bootstrap_publishes_exact_lease_endpoint_identity, uruchomiony w pełnym pliku testowym na Windows, nadal sprawdza zgodność fingerprint endpointu z lease i generation record.
- DIRECT_EVIDENCE — nie loguje się authkey ani ciphertext; nie dodano osobnego plaintext pliku.

## PLAINTEXT_REJECTION

- DIRECT_EVIDENCE — na Windows brak pola tekstowego z prefiksem dpapi: powoduje EndpointSchemaError z komunikatem LIVE endpoint authkey is not DPAPI-protected. W strict mode wyjątek jest propagowany; w zwykłym trybie istniejący except zamienia go na None.
- DIRECT_EVIDENCE — wadliwe base64, DPAPI BackendSecretError, ValueError lub OSError są opakowywane jako EndpointSchemaError z komunikatem LIVE endpoint DPAPI authkey is invalid.
- DIRECT_EVIDENCE — test test_live_endpoint_rejects_plaintext_authkey_on_windows zapisuje testowy endpoint bez szyfrowania i sprawdza odmowę w strict mode oraz None w zwykłym trybie.
- DIRECT_EVIDENCE — oba nowe testy wykonały się na platform win32 / CPython 3.15.2; nie zostały pominięte.

## TARGETED_TESTS

- DIRECT_EVIDENCE — interpreter: Python 3.15.2, platform win32; pytest 9.1.1.
- DIRECT_EVIDENCE — polecenie celowane:
  .venv/Scripts/python.exe -m pytest -q tests/test_live_authority_bootstrap.py -k "live_endpoint_authkey_is_protected_on_disk or live_endpoint_rejects_plaintext_authkey_on_windows" -vv
  Wynik: 2 passed, 17 deselected.
- DIRECT_EVIDENCE — pełny wskazany plik:
  .venv/Scripts/python.exe -m pytest -q tests/test_live_authority_bootstrap.py
  Wynik odebranego końcowego uruchomienia: 19 passed in 55.99s.
- DIRECT_EVIDENCE — pierwsze uruchomienie całego pliku przekroczyło 30-sekundowe oczekiwanie narzędzia i zwróciło wyłącznie częściowy postęp; po zakończeniu procesu ponowiono dokładnie to polecenie, aby uzyskać wynik końcowy. Rozstrzygający, odebrany wynik powtórzenia to 19 passed.
- DIRECT_EVIDENCE — nie uruchamiano FULL ani testów na produkcyjnym endpointcie. Testy korzystają z tmp_path i testowych endpointów.

## MCP_POST_CHANGE

- DIRECT_EVIDENCE — Contextor MCP dla obu plików zwrócił canonical_revision=1584, canonical_state=fresh, workspace_sync=verified, provenance=live. Syntax diagnostics dla runtime.py i tests/test_live_authority_bootstrap.py: syntax_errors.count=0, availability=fresh.
- DIRECT_EVIDENCE — watcher po revision 1581:
  - revision 1582: update_file, origin=desktop_watcher, status=UPDATED, runtime.py;
  - revision 1583: update_file, origin=desktop_watcher, status=UNCHANGED, runtime.py;
  - revision 1584: update_file, origin=desktop_watcher, status=UPDATED, tests/test_live_authority_bootstrap.py.
  Odczyt z kursorem 1581/1582/1583 zgłosił continuity=continuous i resync_required=false; latest_revision=1584.
- DIRECT_EVIDENCE — pierwszy odczyt wydarzeń z limitem 5 przekroczył limit odpowiedzi narzędzia i zwrócił confirmation_required; powtórzenia z limit=1 dostarczyły powyższe trzy rewizje oraz metadane ciągłości.
- DIRECT_EVIDENCE — lokalny git diff zawiera zmiany wyłącznie w runtime.py i tests/test_live_authority_bootstrap.py poza wymaganym raportem walkthrough.md. Nie zmieniono ipc.py, runtime_lease.py ani dispatcherów. W runtime.py zmieniono tylko importy oraz disk write/read endpointu; kod lease i run_service nie został edytowany.
- DIRECT_EVIDENCE — aktualny Contextor source range zawiera nowy import i obie funkcje testowe; obie nowe testy oraz test istniejącej zgodności lease/fingerprint przeszły na Windows.
- UNKNOWN — po zmianie projekcja zależności get_module_context dla runtime nadal wymienia 17 modułów i nie pokazuje mcp_backend_secret, mimo że zsynchronizowany source range zawiera bezpośredni import. Testy CPython importują runtime bez błędu, ale przyczyna braku nowej krawędzi w projekcji dependency pozostaje nierozstrzygnięta.

## FULL_DIFFS

FILES_CHANGED:
- contextor/core/live_state/runtime.py
- tests/test_live_authority_bootstrap.py

walkthrough.md jest raportem wymaganym przez workflow i nie jest liczony jako production/test file. Poniżej kompletne rzeczywiste diffy obu plików:

~~~diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 0276375..be41bbf 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -3,6 +3,8 @@
 from __future__ import annotations
 
 import argparse
+import base64
+import binascii
 import contextlib
 import json
 import os
@@ -20,6 +22,11 @@ from contextor.core.lineage_query.live_query import (
     query_live_symbol_lineage,
 )
 from contextor.core.paths import repo_cache_dir
+from contextor.mcp_backend_secret import (
+    BackendSecretError,
+    _protect_windows,
+    _unprotect_windows,
+)
 from contextor.core.repository_identity import (
     read_repository_identity,
     require_repository_identity,
@@ -262,10 +269,37 @@ def _read_endpoint(repo_path: str | Path, *, strict: bool = False) -> LiveEndpoi
             raise EndpointSchemaError("LIVE endpoint identity fields must be non-empty")
         if not str(payload["service_instance_id"]).strip() or not str(payload["process_start_identity"]).strip():
             raise EndpointSchemaError("LIVE endpoint service identity fields must be non-empty")
+        authkey_hex = payload["authkey_hex"]
+        if os.name == "nt":
+            if (
+                not isinstance(authkey_hex, str)
+                or not authkey_hex.startswith("dpapi:")
+            ):
+                raise EndpointSchemaError(
+                    "LIVE endpoint authkey is not DPAPI-protected"
+                )
+            try:
+                protected = base64.b64decode(
+                    authkey_hex[len("dpapi:"):],
+                    validate=True,
+                )
+                authkey_hex = _unprotect_windows(
+                    protected
+                ).hex()
+            except (
+                BackendSecretError,
+                ValueError,
+                binascii.Error,
+                OSError,
+            ) as exc:
+                raise EndpointSchemaError(
+                    "LIVE endpoint DPAPI authkey is invalid"
+                ) from exc
+
         endpoint = LiveEndpoint(
             str(payload["host"]),
             port,
-            str(payload["authkey_hex"]),
+            str(authkey_hex),
             pid=pid,
             service_pid=service_pid,
             owner_pid=owner_pid,
@@ -895,6 +929,13 @@ def _write_endpoint_atomic(endpoint: LiveEndpoint, root: Path) -> None:
     target.parent.mkdir(parents=True, exist_ok=True)
     temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
     payload = endpoint.to_dict()
+    if os.name == "nt":
+        payload["authkey_hex"] = (
+            "dpapi:"
+            + base64.b64encode(
+                _protect_windows(endpoint.authkey)
+            ).decode("ascii")
+        )
     try:
         with temporary.open("w", encoding="utf-8", newline="\n") as stream:
             json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
diff --git a/tests/test_live_authority_bootstrap.py b/tests/test_live_authority_bootstrap.py
index 767a505..887bffc 100644
--- a/tests/test_live_authority_bootstrap.py
+++ b/tests/test_live_authority_bootstrap.py
@@ -187,6 +187,81 @@ def test_bootstrap_publishes_exact_lease_endpoint_identity(tmp_path: Path, monke
         _stop(client)
 
 
+@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI only")
+def test_live_endpoint_authkey_is_protected_on_disk(tmp_path, monkeypatch):
+    from contextor.core.live_state.ipc import LiveEndpoint
+    from contextor.core.live_state.runtime import (
+        _read_endpoint,
+        _write_endpoint_atomic,
+        endpoint_file,
+    )
+
+    repo = _repo(tmp_path, monkeypatch)
+    endpoint = LiveEndpoint(
+        host="127.0.0.1",
+        port=12345,
+        authkey_hex="a1" * 32,
+        pid=123,
+        service_pid=123,
+        repo_id="ctx_test",
+        root_path=str(repo),
+        runtime_domain_id="test-domain",
+        service_instance_id="test-service",
+        lease_generation=1,
+        process_start_identity="test-process",
+    )
+
+    _write_endpoint_atomic(endpoint, repo)
+    raw = endpoint_file(repo).read_text(encoding="utf-8")
+    stored = json.loads(raw)
+
+    assert stored["authkey_hex"].startswith("dpapi:")
+    assert endpoint.authkey_hex not in raw
+    assert _read_endpoint(repo, strict=True) == endpoint
+
+
+@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI only")
+def test_live_endpoint_rejects_plaintext_authkey_on_windows(
+    tmp_path, monkeypatch
+):
+    from contextor.core.live_state.ipc import LiveEndpoint
+    from contextor.core.live_state.runtime import (
+        EndpointSchemaError,
+        _read_endpoint,
+        endpoint_file,
+    )
+
+    repo = _repo(tmp_path, monkeypatch)
+    endpoint = LiveEndpoint(
+        host="127.0.0.1",
+        port=12345,
+        authkey_hex="a1" * 32,
+        pid=123,
+        service_pid=123,
+        repo_id="ctx_test",
+        root_path=str(repo),
+        runtime_domain_id="test-domain",
+        service_instance_id="test-service",
+        lease_generation=1,
+        process_start_identity="test-process",
+    )
+
+    target = endpoint_file(repo)
+    target.parent.mkdir(parents=True, exist_ok=True)
+    target.write_text(
+        json.dumps(endpoint.to_dict()),
+        encoding="utf-8",
+    )
+
+    with pytest.raises(
+        EndpointSchemaError,
+        match="not DPAPI-protected",
+    ):
+        _read_endpoint(repo, strict=True)
+
+    assert _read_endpoint(repo) is None
+
+
 def test_verified_existing_authority_attaches_and_second_desktop_is_rejected(
     tmp_path: Path, monkeypatch: pytest.MonkeyPatch
 ):
~~~

## RUNTIME_ADOPTION_STATUS

- DIRECT_EVIDENCE — źródło i testy są widoczne w Contextor revision 1584, workspace_sync=verified; watcher dostarczył aktualizacje obu plików.
- UNKNOWN — nie restartowano działającego backendu ani LIVE zgodnie z poleceniem. Świeżość workspace/Contextor nie dowodzi, że istniejący proces usługi załadował zmieniony runtime.py. Produkcyjna adopcja kodu pozostaje niepotwierdzona.

## FINAL_STATUS

- DIRECT_EVIDENCE — implementacja zgodna z podanym kontraktem i dokładnym zakresem dwóch plików.
- DIRECT_EVIDENCE — testy celowane: 2 passed; tests/test_live_authority_bootstrap.py: 19 passed.
- DIRECT_EVIDENCE — Contextor post-change revision 1584, canonical_state=fresh, workspace_sync=verified, syntax_errors=0; watcher continuity continuous bez resync.
- UNKNOWN — runtime adoption niezweryfikowane bez restartu; projekcja zależności runtime nie wykazała nowego importu mcp_backend_secret, mimo świeżego zsynchronizowanego źródła i poprawnego importu potwierdzonego testami.
- DIRECT_EVIDENCE — git status po zmianach: M contextor/core/live_state/runtime.py; M tests/test_live_authority_bootstrap.py; M walkthrough.md. Nie zmieniono innych plików.
- FINAL_STATUS=IMPLEMENTATION_AND_TESTS_PASS; LIVE_RUNTIME_ADOPTION=UNKNOWN; DEPENDENCY_PROJECTION_EDGE=UNKNOWN.
