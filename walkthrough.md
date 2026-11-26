# P17-F1-I1 — izolacja AuthenticationError w LIVE IPC

FILES_CHANGED=2: contextor/core/live_state/ipc.py; tests/test_live_state_ipc.py
ACTUAL_DIFF=patrz FULL_DIFFS poniżej

walkthrough.md jest raportem i nie jest liczony jako production/test changed file. Nie wykonano commit, push, staging ani restartu. Nie połączono się z produkcyjnym LIVE i nie odczytano authkey.

## PREFLIGHT

- **DIRECT_EVIDENCE — HEAD/Git:** HEAD 23d4dcf4546d15fa81e18dfbed65af7184c6a132, branch main. Przed patchem git status miał wyłącznie wcześniej zmieniony walkthrough.md; oba pliki zlecone do edycji miały pusty diff.
- **DIRECT_EVIDENCE — Contextor, revision przed zmianą:** canonical_revision=1579, canonical_state=fresh, provenance=live, resync_required=false.
- **DIRECT_EVIDENCE — ipc.py przed zmianą:** target/module contextor.core.live_state.ipc, workspace_sync=verified, syntax_diagnostics.status=checked_and_none, availability=fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — test przed zmianą:** target/module tests.test_live_state_ipc, workspace_sync=verified, syntax_diagnostics.status=checked_and_none, availability=fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — literalne kotwice:** ipc.py:15-16 zawierało parę dataclass/Client, Listener; _serve_requests accept block był w :1323-1326 z except OSError bezpośrednio po Listener.accept; test OSError kończył się w tests/test_live_state_ipc.py:488, a test stopped accept zaczynał się w :490. Wszystkie kotwice pasowały; SOURCE_DRIFT nie wystąpił.
- **DIRECT_EVIDENCE — watcher baseline:** get_live_events(after_revision=1579) przed edycją zwrócił latest_revision=1579, events=[], continuity=continuous, resync_required=false.
- **DIRECT_EVIDENCE:** zachowano zakres dokładnie dwóch source/test plików; nie wykonano połączeń do produkcyjnego portu.

## CONFIRMED_ROOT_CAUSE

- **DIRECT_EVIDENCE; CONTRACT_PROVED:** w CPython 3.15.2 AuthenticationError jest multiprocessing.context.AuthenticationError, pochodzi z ProcessError/Exception i nie jest OSError. Lokalna introspekcja zwróciła issubclass(AuthenticationError, OSError)=False.
- **DIRECT_EVIDENCE; CODE_PATH_PROVED:** Listener.accept wykonuje HMAC challenge przez deliver_challenge; mismatch w _verify_challenge podnosi AuthenticationError, deliver_challenge wysyła failure i re-raise. Wyjątek wychodzi bezpośrednio z Listener.accept.
- **DIRECT_EVIDENCE; CODE_PATH_PROVED:** przed zmianą _serve_requests obejmował Listener.accept tylko except OSError. Obsługa Exception dla dispatch znajduje się później, więc nie obejmowała handshake. serve_forever wykonywał finally i propagował ten wyjątek do produkcyjnego _serve_service, który zapisywał failure i oznaczał service thread jako terminated; po join run_service wchodził w fail-closed cleanup.
- **INFERENCE:** jedna niepoprawna lokalna próba handshake mogła zakończyć usługę LIVE przez fatalną ścieżkę obsługi wątku. Potwierdzono kodem i kontraktem CPythona; nie testowano produkcyjnego portu.

## EXACT_IMPLEMENTATION

- **DIRECT_EVIDENCE:** dodano import multiprocessing.AuthenticationError pomiędzy dataclasses i multiprocessing.connection.
- **DIRECT_EVIDENCE:** _serve_requests łapie konkretnie AuthenticationError bez logowania jako OSError i kontynuuje pętlę. Istniejący except OSError i jego treść pozostają bez zmian.
- **DIRECT_EVIDENCE:** nie zmieniono recv, dispatch, finally/connection.close, serve_forever ani żadnej operacji IPC.
- **DIRECT_EVIDENCE:** nowy test jest dokładnie w kotwicy po test_server_accept_failure_emits_once_and_reraises i przed test_server_stopped_accept_path_emits_no_incident. Korzysta wyłącznie z fixture live_server, flipuje jeden bit key w pamięci, sprawdza AuthenticationError, następnie ping i stan stop. Żadna wartość klucza nie jest wypisywana.

## NEGATIVE_AUTHENTICATION_TEST

**DIRECT_EVIDENCE — dodany test, tests/test_live_state_ipc.py:490-506 po zmianie:**

    def test_server_rejects_invalid_authkey_without_stopping_listener(live_server):
        server, client = live_server
        valid_key = server.endpoint.authkey
        invalid_key = bytes([valid_key[0] ^ 1]) + valid_key[1:]

        with pytest.raises(multiprocessing.AuthenticationError):
            mpc.Client(
                server.endpoint.address,
                family="AF_INET",
                authkey=invalid_key,
            )

        assert not server._stop.is_set()
        assert client.request("ping")["status"] == "ok"
        assert not server._stop.is_set()

- **DIRECT_EVIDENCE:** test używa lokalnego ephemeral listenera fixture; nie używa endpointu produkcyjnego. Klient z błędnym key otrzymuje AuthenticationError, a poprawny fixture client wykonuje ping po odmowie.

## OSERROR_REGRESSION

- **DIRECT_EVIDENCE:** except OSError as exc oraz cały dotychczasowy tracing/re-raise pozostają bez zmian; diff dodaje tylko except AuthenticationError przed OSError.
- **DIRECT_EVIDENCE:** tests/test_live_state_ipc.py:test_server_accept_failure_emits_once_and_reraises nadal istnieje bez zmian w :466-488. test_server_stopped_accept_path_emits_no_incident również nie został zmieniony.
- **DIRECT_EVIDENCE:** oba testy przeszły w celowanej selekcji oraz w pełnym pliku testowym.

## TARGETED_TESTS

1. **DIRECT_EVIDENCE — celowany zestaw:** wykonano:
   
       .venv/Scripts/python.exe -m pytest -q tests/test_live_state_ipc.py -k "rejects_invalid_authkey_without_stopping_listener or accept_failure_emits_once_and_reraises or stopped_accept_path_emits_no_incident" -vv

   Wynik: 3 passed, 97 deselected, 2.46s.
2. **DIRECT_EVIDENCE — cały wskazany plik:** wykonano:
   
       .venv/Scripts/python.exe -m pytest -q tests/test_live_state_ipc.py

   Pierwsze wywołanie zwróciło częściowy output do 72% bez końcowego statusu shell; powtórzono ten sam zlecony command, aby odebrać exit status. Wynik końcowy: 100 passed, 2 warnings, 42.11s.
3. **DIRECT_EVIDENCE:** dwa ostrzeżenia to AuthlibDeprecationWarning z zależności przy teście test_endpoint_before_authority_replay_exposes_valid_pending_live_feed (authlib.jose oraz httpx assertion client). Nie dotyczyły zmienionego kodu. Nie uruchomiono FULL suite ani innych testów.

## MCP_POST_CHANGE

- **DIRECT_EVIDENCE — ipc.py:** Contextor canonical_revision=1581, canonical_state=fresh, workspace_sync=verified, provenance=live; syntax_diagnostics=checked_and_none, errors=[], total=0.
- **DIRECT_EVIDENCE — test file:** Contextor canonical_revision=1581, canonical_state=fresh, workspace_sync=verified, provenance=live; syntax_diagnostics=checked_and_none, errors=[], total=0.
- **DIRECT_EVIDENCE — watcher event 1:** po bazowej revision 1579, revision 1580, operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=contextor/core/live_state/ipc.py, blast_radius_state=fresh.
- **DIRECT_EVIDENCE — watcher event 2:** revision 1581, operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=tests/test_live_state_ipc.py, blast_radius_state=deferred.
- **DIRECT_EVIDENCE — continuity:** oba zapytania get_live_events miały continuity=continuous i resync_required=false; revision wzrosła kolejno 1579→1580→1581. Pierwszy feed z limitem 20 wymagał confirmation_required ze względu na rozmiar widoku warningów; powtórzono odczyt z limit=1, bez zmiany stanu.
- **DIRECT_EVIDENCE:** nie wywołano MCP update_file; zmiany zostały przyjęte przez desktop_watcher. Nie wykonano restartu.
- **DIRECT_EVIDENCE:** rodzina cycle_semantics jest oznaczona stale po revision 1581; canonical_state modułów pozostaje fresh, a target syntax diagnostics są materialized/fresh. Nie używam tej niezwiązanej rodziny jako dowodu semantyki patcha.
- **DIRECT_EVIDENCE:** ponowny diff zawiera wyłącznie import AuthenticationError, jego except/continue oraz wskazany test. OSError block jest zachowany, a dispatcher i pozostałe operation names nie mają hunks w diff.

## FULL_DIFFS

Każdy diff poniżej jest pełnym bieżącym unified diff dla wskazanego source/test pliku.

### contextor/core/live_state/ipc.py

    diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
    index 710a016..2185db1 100644
    --- a/contextor/core/live_state/ipc.py
    +++ b/contextor/core/live_state/ipc.py
    @@ -13,6 +13,7 @@ import threading
     import time
     import uuid
     from dataclasses import dataclass
    +from multiprocessing import AuthenticationError
     from multiprocessing.connection import Client, Listener
     from pathlib import Path
     from types import SimpleNamespace
    @@ -1323,6 +1324,8 @@ class CanonicalLiveServer:
                 accept_started = time.monotonic()
                 try:
                     connection = self._listener.accept()
    +            except AuthenticationError:
    +                continue
                 except OSError as exc:
                     if self._stop.is_set():
                         break

### tests/test_live_state_ipc.py

    diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
    index 7f4b660..cbb73a8 100644
    --- a/tests/test_live_state_ipc.py
    +++ b/tests/test_live_state_ipc.py
    @@ -487,6 +487,23 @@ def test_server_accept_failure_emits_once_and_reraises(monkeypatch):
         assert events[0]["operation_or_request_type"] == "accept"
     
     
    +def test_server_rejects_invalid_authkey_without_stopping_listener(live_server):
    +    server, client = live_server
    +    valid_key = server.endpoint.authkey
    +    invalid_key = bytes([valid_key[0] ^ 1]) + valid_key[1:]
    +
    +    with pytest.raises(multiprocessing.AuthenticationError):
    +        mpc.Client(
    +            server.endpoint.address,
    +            family="AF_INET",
    +            authkey=invalid_key,
    +        )
    +
    +    assert not server._stop.is_set()
    +    assert client.request("ping")["status"] == "ok"
    +    assert not server._stop.is_set()
    +
    +
     def test_server_stopped_accept_path_emits_no_incident(monkeypatch):
         events = []
         server = CanonicalLiveServer(SimpleNamespace(files=[]))

## FINAL_STATUS

- **DIRECT_EVIDENCE:** implementacja i test regresyjny są zgodne z dokładnymi hunks zlecenia; celowane testy i tests/test_live_state_ipc.py przechodzą; oba pliki mają fresh canonical state, verified workspace_sync i świeże, puste syntax diagnostics.
- **DIRECT_EVIDENCE:** zmieniono source/test wyłącznie w dwóch wskazanych plikach. walkthrough.md nadpisano raportem. Brak commit/push/staging/FULL/restartu.
- **UNKNOWN:** nie twierdzę, że już uruchomiony proces LIVE załadował zmieniony kod; restart był wykluczony, a testy używały wyłącznie izolowanego fixture.
- **FINAL_STATUS=PASS — zakres source/test i watcher verification.**

