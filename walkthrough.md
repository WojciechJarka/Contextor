# CPA10K7G2B1_POST_RESTART_RUNTIME_CERTIFICATION

STATUS=BLOCKED
HEAD=befec3d6bdad4b9141c522fc3bf539b774da6708
FILES_CHANGED=C:\Temp\Contextor_Repo\walkthrough.md
RUNNING_MCP_FRESHNESS=VERIFIED
CANONICAL_REVISION=1342
WORKSPACE_SYNC=verified
FIRST_BACKEND_FRESH_IMPORT=YES
FIRST_BACKEND_RUNNER_REACHED=YES
DURABLE_RECORD_ACTIVE=NO
DURABLE_RECORD_PID_MATCH=NO
DURABLE_RECORD_CREATION_IDENTITY_MATCH=NO
TOKEN_PERSISTED=NO
SECOND_BACKEND_REJECTED=NOT_TESTED
SECOND_RUNNER_REACHED=NOT_TESTED
SECOND_CLEANUP_CALLED=NOT_TESTED
REGISTRY_CHANGED_BY_SECOND=NOT_TESTED
OWNER_RECORD_REPLACED_BY_SECOND=NOT_TESTED
FIRST_NORMAL_EXIT=YES (child exit code 0 after parent RETURN signal)
DURABLE_RECORD_REMOVED_AFTER_EXIT=NOT_TESTED
LIFETIME_LOCK_RELEASED=NOT_TESTED
REACQUIRE_AFTER_RELEASE=NOT_TESTED
CERTIFICATION_PROCESS_LEAKS=0
PROCESS_BASELINE_INITIAL=48
PROCESS_OBSERVED_DURING_G2B_DISCOVERY=53
PROCESS_REDUCTION_EXPECTED_THIS_STAGE=NO
FINAL_TARGET=LT_20_UNDER_CONTINUOUS_LOAD
TOKEN_REDACTED=YES
PRODUCTION_TEST_CONFIG_FILES_CHANGED=NO
MCP_SERVER_RESTART_REQUIRED=NO
ACTUAL_DIFF=DIFFS=NONE

## Blocker

Pierwszy świeży child zaimportował lokalne `contextor.mcp_server` przy ustawionym środowisku i osiągnął dozwolony HTTP stub. Podczas jego aktywności harness odczytał i sparsował `backend.json`, ale walidator zwrócił `DURABLE_RECORD_ACTIVE=NO`, `DURABLE_RECORD_PID_MATCH=NO` oraz `DURABLE_RECORD_CREATION_IDENTITY_MATCH=NO`. Child zakończył się kodem 0 po sygnale normalnego powrotu; harness nie zachował surowego rekordu ani wartości porównywanych pól. Dlatego dokładny rozbieżny field/identity nie jest ustalony. Nie ponawiałem ani nie poprawiałem harnessu: kontrakt wymaga zatrzymania certyfikacji po niespełnionym kryterium, bez prób naprawy.

Z powodu tego blockera SECOND, snapshot registry, kontrola niezmienności owner recordu, ponowny odczyt backend.json po exit oraz reacquire nie zostały wykonane. Nie wolno zatem wyciągać wniosku, że singleton rejection, usunięcie rekordu po exit ani zwolnienie locka są runtime-certified.

## Evidence

### DIRECT_EVIDENCE

- Aktywny Contextor MCP rozwiązał wszystkie wymagane symbole z provenance=live, canonical_state=fresh, workspace_sync=verified, canonical_revision=1342: `PersistentBackendLease`, `.acquire`, `.release`, `PersistentBackendRecord`, `read_backend_record`, `remove_backend_record_if_exact` oraz `mcp_server.main`.
- Aktualny canonical file context dla obu modułów źródłowych był fresh/verified; syntax diagnostics checked_and_none, errors=0, warnings=[].
- Fetch kompletnego `mcp_server.main` potwierdził obecność `PersistentBackendLease.acquire()` przed `_cleanup_orphaned_processes()`; w pobranym source kolejność obu anchorów została sprawdzona bezpośrednio.
- Pierwszy certyfikacyjny child używał wskazanego `.venv\Scripts\python.exe`; ścieżki `CONTEXTOR_STATE_DIR` i `CONTEXTOR_MCP_PROCESS_REGISTRY` pochodziły z unikalnego katalogu tymczasowego. Token wygenerowano w pamięci, nie wypisano go, a porównanie stwierdziło brak jego wartości i brak credential-like keys w sparsowanym rekordzie.
- Pierwszy child osiągnął runner stub i zakończył się kodem 0 po sygnale RETURN. Zarejestrowany przez harness wynik cleanupu: CERTIFICATION_PROCESS_LEAKS=0, READER_THREADS_ALIVE=0, CHILD_EXIT_CODES=[0].

### CODE_PATH_PROVED

- Fresh import i runner reach są bezpośrednio potwierdzone markerami procesu. Runtime code gate przechodzi, ale nie przesądza o poprawności durable recordu ani późniejszych kryteriów.
- Dla rekordu walidator sprawdzał schema/version, rolę/transport/host/port, PID, canonical registry path, instance_id, started_at, brak credential fields oraz identity probe procesu. Agregat zwrócił porażkę; poszczególne wartości nie zostały zachowane, więc nie przypisuję przyczyny implementacji ani harnessowi.

### UNKNOWN

- Nieznany jest dokładny field/identity predicate, który spowodował odrzucenie rekordu; brak surowych wartości uniemożliwia rozstrzygnięcie.
- `DURABLE_RECORD_REMOVED_AFTER_EXIT`, `LIFETIME_LOCK_RELEASED`, `REACQUIRE_AFTER_RELEASE` oraz wszystkie kryteria SECOND pozostają NOT_TESTED.
- Harness oznaczył `TEMP_TREE_REMOVED=false` zanim wyszedł z `TemporaryDirectory` scope; to pomiar przed automatycznym cleanupem i nie stanowi dowodu na pozostawiony katalog. Nie używam tego pola do oceny leaków.

## Wykonanie

- Runtime freshness sprawdzono najpierw przez Contextor; dopiero po `RUNNING_MCP_FRESHNESS=VERIFIED` uruchomiono certyfikacyjny child.
- Uruchomiono jeden świeży child z realnym importem `mcp_server` i realną ścieżką `main()`/lease. Jedynym zastąpionym elementem był `mcp_server.mcp.run_http_async`, zgodnie z kontraktem. Lease, acquire/release, zapis/odczyt rekordu, lock, process_identity i lifecycle main nie były mockowane.
- Po niepowodzeniu walidacji rekordu child dostał RETURN i zakończył się kodem 0; runner reader thread zakończył pracę. SECOND i reacquire child nie zostały uruchomione.
- Nie uruchomiono pytest ani persistent backendu użytkownika. Nie zatrzymywano żadnego procesu spoza tej certyfikacji. Nie zmieniono production code, testów ani konfiguracji. HEAD nie zmienił się.
- Harness był inline przez PowerShell do `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -`; nie zapisano helper scriptu ani tokenu do pliku.

## Process metrics

PROCESS_BASELINE_INITIAL=48 i PROCESS_OBSERVED_DURING_G2B_DISCOVERY=53 są wartościami wejściowymi poprzedniego etapu; nie wykonywano tu pomiaru ani porównania. Idle cleanup nie był kryterium. G2B1 nie migruje Codexa ze stdio na shared HTTP, więc PROCESS_REDUCTION_EXPECTED_THIS_STAGE=NO. FINAL_TARGET pozostaje przyszłym celem, nie wynikiem tej certyfikacji.

## Diff

ACTUAL_DIFF=DIFFS=NONE — w tym runtime-certification etapie zmieniono wyłącznie walkthrough.md. Plik jest raportem i nie jest liczony jako production/test/config change.
