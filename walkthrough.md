# L32G_B2_COW_FALSE_FRESH_FOCUSED_DISCOVERY
MODE: STRICT READ-ONLY DISCOVERY
Zakres: tylko aktualny task; bez edycji source/test, bez pytest, bez Git, bez restartów.

## COW_STATE_MATRIX

Canonical owner pola RepositoryAnalysisState.module_parse_freshness: C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:95. Adnotacja to Dict[str, Dict[str, Any]], ale Python assignment/unpickle nie egzekwuje tego typu.

| Wejście do _prepare_candidate_state | Rezultat konstruktora | module_current_truth przed/po | Ocena |
|---|---|---|---|
| Brak atrybutu | getattr(..., {}) daje {}; kandydat dostaje nowy pusty dict | Brak wpisu oznacza available=True, state=fresh, provenance=current | LEGACY CONTRACT; fresh jest umową dla braku wpisu |
| Poprawne {} | pusty, płytko skopiowany dict | brak wpisu => fresh | PROVED_SAFE dla poprawnego pustego stanu |
| Poprawny dict z wpisami fresh/stale | nowy zewnętrzny dict; wpisy są współdzielone płytko | zachowane wpisy nadal fresh/stale | PROVED_SAFE, o ile wpis nie jest kasowany przez target-local clear |
| Falsey błędna mapa, np. None, False, 0, "", [], pusty tuple/set | or {} zastępuje wartość przez {}, potem dict ją kopiuje | przed COW cała nie-dict mapa jest unavailable; po publikacji brakujące moduły stają się fresh | PROVED_FALSE_FRESH przy wykonaniu i publikacji COW |
| Truthy nie-dict, którego dict(value) nie umie zbudować, np. ["bad"], 17, typowy string "bad" | dict(...) rzuca wyjątek przed ukończeniem kandydata | stan źródłowy nie przechodzi przez COW publication | PROVED_FAIL_CLOSED dla tych kształtów |
| Truthy nie-dict, który jest iterowalny jako pary key/value, np. [("kept", {"state":"stale"})] | dict(value) tworzy zwykły dict; brak walidacji jego domeny/wpisów | brakujące klucze po konwersji raportowane jako fresh | CONDITIONAL_CODE_PATH; typ jest niepoprawny kontraktowo, ale konstruktor go akceptuje |
| Poprawny dict z błędnym wpisem dla innego modułu | wpis przechodzi przez kopię bez walidacji | ten moduł pozostaje unavailable/untrusted | PROVED_SAFE względem błędnego wpisu niebędącego targetem |
| Poprawny dict z błędnym wpisem dla targetu; source poprawnie sparsowany | clear usuwa targetowy wpis, nawet jeśli wpis nie miał state=stale | po usunięciu brak wpisu => fresh; źródło targetu zostało sparsowane w tej ścieżce | PROVED_SAFE jako target-local recovery po udanym parse; status nie musi być RECOVERED |
| Poprawny dict z błędnym wpisem dla targetu; target parse kończy się błędem | mark nadpisuje targetowy wpis na state=stale | module_current_truth zwraca available=False, state=stale, provenance=last_known_good | MARKER REPLACED; nie fresh, ale poprzedni untrusted wpis zostaje sklasyfikowany jako stale/LKG |

Dokładna normalizująca linia to C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:694:
```python
module_parse_freshness=dict(getattr(state, "module_parse_freshness", {}) or {}),
```
Nie sprawdza typu mapy przed or, nie waliduje kluczy ani wpisów, i kopiuje jedynie kontener zewnętrzny.

## FALSE_FRESH_PUBLICATION_PATHS

Wspólna podstawa: C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:227 zwraca fresh dla brakującego atrybutu lub brakującego modułu. Nie sprawdza resync_required. Po skasowaniu/konwersji malformed mapy jego missing-key branch ma więc skutek odczytywalny jako available=True,state=fresh.

| Ścieżka | Warunek i przepływ | Wynik | Klasyfikacja |
|---|---|---|---|
| Syntax failure dla modułu A przy falsey malformed whole-map | update_file -> error branch -> _commit_syntax_candidate -> COW zamienia mapę na {} -> mark_module_parse_failure(A) -> publikuje kandydat | A jest stale/LKG; niepowiązane moduły, których metadata utracono przez whole-map malformation, stają się fresh przez brak wpisu. Wynik update to SYNTAX_ERROR; LIVE uważa ten status za completed i persystuje kandydata | PROVED_FALSE_FRESH code path |
| Target-local semantic no-op | plik parsowany przez prepare_source_update; plan.is_empty -> _commit_syntax_candidate -> COW -> clear target -> publikuje; potem aktualizuje FileStateManager | falsey whole-map znika, a niepowiązane moduły stają się fresh; target przechodzi po parse do fresh przez brak wpisu. Zwracane UNCHANGED albo RECOVERED | PROVED_FALSE_FRESH code path |
| Zmiana semantyczna / zwykłe UPDATED | po poprawnym parse execute_refresh_plan tworzy COW candidate; _apply_delta_and_commit publikuje jego mapę i czyści target | falsey whole-map znika; niepowiązane brakujące wpisy stają się fresh. LIVE zapisuje candidate snapshot i potem commituje go do RAM | PROVED_FALSE_FRESH code path |
| Delete path | przed source parse wykryta nieobecność pliku -> plan delete -> execute_refresh_plan COW -> clear target w commit | falsey whole-map znika; niepowiązane moduły stają się fresh. Target jest usuwany z modułów/faktów. Brak target markera zwraca fresh w helperze, ale faktycznie targetu już nie ma; query resolution po delete nie został runtime-sprawdzony | PROVED_FALSE_FRESH dla pozostałych modułów; UNKNOWN co do query po usuniętym target |
| Truthy coercible whole-map podczas parse error lub delete | te dwie ścieżki dochodzą do COW przed udanym-parse precheckiem; dict(raw) może zaakceptować pair iterable | nieznany whole-map zostaje zamieniony w dict; missing modules stają się fresh | CONDITIONAL_CODE_PATH |
| Truthy coercible whole-map podczas zwykłego udanego source parse | przed COW update_file wykonuje freshness.get(module_path) na oryginalnej mapie | typ bez metody .get kończy się wyjątkiem przed candidate publication; mapping-like obiekt z .get może przejść dalej | PROVED_FAIL_CLOSED dla typowego list; CONDITIONAL_CODE_PATH dla obiektów z .get |
| Malformed individual entry poza targetem | płytka kopia zachowuje wpis | ten moduł nadal unavailable; nie jest usunięty przez clear innego targetu | PROVED_SAFE |
| Malformed individual entry targetu przy syntax failure | mark bezwarunkowo zastępuje entry przez stale payload | target unavailable/stale, nie current/fresh | PROVED_SAFE względem false-fresh; provenance zmienia się z untrusted na LKG |
| Malformed individual entry targetu po poprawnym parse | clear usuwa wpis, bez sprawdzenia czy stan był stale; źródło targetu sparsowane przed clear | target może następnie być current/fresh; tylko targetowo i po bieżącym parse | PROVED_SAFE w granicach source parse |

Katalog bezpośrednich module_current_truth consumers potwierdzony dokładnym tekstowym wyszukaniem: C:\Temp\Contextor_Repo\contextor\core\canonical_state_query\runtime.py, C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py, C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py, C:\Temp\Contextor_Repo\contextor\mcp\tools\contextor_fact_lineage.py, C:\Temp\Contextor_Repo\contextor\mcp\tools\get_symbol_call_context.py, C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py, C:\Temp\Contextor_Repo\contextor\mcp\tools\get_module_blast_radius.py, C:\Temp\Contextor_Repo\contextor\core\reference\module_usage_reuse.py, C:\Temp\Contextor_Repo\contextor\core\single_file\builders\layer0_builders.py i layer2_builders.py. Missing marker semantics są współdzielone; nie analizowano wszystkich tych odpowiedzi end-to-end dla konkretnego modułu. To consumer list, nie dowód bieżącego runtime leak.

## UNCHANGED_FAST_PATH

C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:470-487 warunek to jednocześnie not self.state_manager.has_changed(file_path) i obecność modułu w state.modules. Gałąź wraca przed get_current_file_state, prepare_source_update, module_parse_freshness.get, _prepare_candidate_state, mark/clear i candidate publication.

Wynik ma status=UNCHANGED; graph_state jest fresh, gdy dependency graph istnieje, a dependencies_state=fresh. Nie zwraca module parse freshness envelope i nie parsuje bieżącego pliku. Dla malformed target markera:
- PROVED_SAFE: marker pozostaje nietknięty; module_current_truth dalej zwraca unavailable dla błędnego wpisu.
- CONDITIONALLY FRESH-LOOKING: update response oznacza graph/dependencies jako fresh, ale to inne rodziny freshness niż parse targetu.
- Desktop watcher traktuje UNCHANGED jako ukończony update i aktualizuje snapshot ścieżki; nie naprawia ani nie bada parse freshness.

Ten fast path różni się od semantic no-op poniżej: semantic no-op najpierw parsuje source, a potem wchodzi do _commit_syntax_candidate, który może normalizować i publikować metadata.

## MARK_CLEAR_CALLERS

Jedyni produkcyjni callerzy potwierdzeni przez Contextor search_source i scoped source search:

- mark_module_parse_failure: jeden call w IncrementalAnalysisEngine._commit_syntax_candidate, przy mark_parse_error is not None (C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:184-190). Żaden inny production caller nie został znaleziony.
- clear_module_parse_failure: dwa call sites w C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:192 i C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:954. Pierwszy w _commit_syntax_candidate; drugi w _apply_delta_and_commit canonical publication.
- _prepare_candidate_state: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:139 z _commit_syntax_candidate, oraz C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:789 z execute_refresh_plan. Contextor call-context dla executor zwraca jeden caller w module-local graph; literal search potwierdza cross-module caller C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:139.
- Candidate publication sites: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:195 i 960 assignment self.state.module_parse_freshness = candidate.module_parse_freshness.

Semantyka helperów:
- mark_module_parse_failure tworzy nowy pusty dict, jeżeli podany state ma non-dict mapę, po czym zapisuje target jako stale. Aktualny produkcyjny caller przekazuje candidate zwrócony przez _prepare_candidate_state, więc standardowa ścieżka malformed whole-map normalizuje wcześniej.
- clear_module_parse_failure zwraca True tylko dla dict entry o state=="stale", ale pop(module_name, None) wykonuje niezależnie od wyniku. Usuwa więc także malformed target entry. Normalny successful parse/no-op wywołuje clear dopiero po sparsowaniu targetu. Delete path wywołuje clear bez parse, ale usuwa target module i jego artefakty z candidate.

## LIVE_ERROR_AND_ATOMICITY_CONTRACT

**Wyjątek z COW prep (uncoercible truthy map):**
1. _commit_syntax_candidate wykonuje _prepare_candidate_state jako pierwszą operację, zanim przypisze zmiany do self.state; wyjątek przerywa przed jej publikacją.
2. execute_refresh_plan przygotowuje candidate przed plan phases/registry transaction; wyjątek nie dochodzi do _apply_delta_and_commit publication.
3. _repository_updater łapie wyjątek, odtwarza identity registry checkpoint i ponownie rzuca.
4. LIVE _execute_update_file uruchamia updater na _clone_state_for_update(previous_state); przy wyjątku nie woła persistera i nie zamienia self._state. Bezpośredni canonical RAM state/revision pozostają poprzednie.
5. Mutation coordinator zamienia wyjątek na canonical_mutation_execution_failed, state=failed. Desktop watcher nie klasyfikuje failed job jako completed, emituje WATCH_UPDATE_FAIL i requeue ścieżkę.
6. Brak kodu w tej ścieżce, który automatycznie ustawia resync_required albo uruchamia full analysis. Error sam w sobie nie wymusza full analysis.

**Udana ścieżka falsey-normalization:**
- Nie ma wyjątku. Update result może być SYNTAX_ERROR, UNCHANGED, RECOVERED, UPDATED lub DELETED, zależnie od branch.
- LIVE _execute_update_file persystuje każdy successful updater result przed RAM commit. Snapshot serialization pickle'uje cały obiekt state; nie normalizuje module_parse_freshness. Potem candidate zostaje ustawiony jako canonical state.
- Persistence failure nie wykonuje RAM commit. Dla wyjątku z current_revision response ma resync_required=True; dla zwykłego OSError response nie ustawia resync. Registry checkpoint ma rollback.
- Jeśli po udanym persisterze końcowy revision/state identity check zawiedzie, metoda zwraca canonical_revision_changed_during_update po snapshot write i przed RAM commit. Kod pokazuje ordering; runtime osiągalność i wpływ executor serialization są UNKNOWN. Nie jest to skutek błędu _prepare_candidate_state.

**Local MCP fallback:**
- contextor/mcp/tools/update_file.py wywołuje lokalny engine, jeśli connect(root) nie zwraca LIVE client.
- W tej gałęzi snapshot persist wywoływany jest tylko dla statusów UPDATED i DELETED; SYNTAX_ERROR, UNCHANGED i RECOVERED nie persistują, choć zmiany engine.state mogą już być w pamięci.
- Kod ustawia live_state_persisted=True dla tych niepersistowanych statusów przez gałąź else True. To jest response flag niezgodny z faktem wywołania persistera; nie dowodzi trwałej snapshot publikacji.
- Dla wyjątku z update_file MCP handler zwraca {"status":"ERROR", ...}. W LIVE route błąd remote również staje się RuntimeError i trafia do tego handlera.

## REQUIRED_PATCH_POINTS

Poniższe są dokładnymi locus obecnego zachowania do rozstrzygnięcia przez audytora; nie stanowią projektu ani instrukcji implementacji:

1. C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:681-755 — _prepare_candidate_state, zwłaszcza line 694.
2. C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:126-206 — _commit_syntax_candidate, COW i publikacja po syntax result.
3. C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:453-734 — update_file: fast path 470-487, syntax-error path, direct .get 608-612, semantic no-op path, update result.
4. C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:760-1018 — _apply_delta_and_commit: COW executor, clear i canonical field publication, global resync retention, file-state acknowledgement.
5. C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:227-303 — current-truth/mutation helper contracts.
6. C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1108-1260 — updater/persister wrapper and registry checkpoint.
7. C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1856-2129 plus dispatch at 2131-2374 — queued and sync update, persistence and atomic publication.
8. C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:592-665 — completed-vs-failed/requeue semantics.
9. C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1507-1874, 1926-2371 — exact raw-state persistence/hydration path.
10. C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:188-295 — public update projection and local persistence decision.

## TARGETED_TEST_OWNERS

Nie uruchomiono testów — zakaz użytkownika.

Istniejący targeted coverage:
- C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py:141 — test_module_current_truth_rejects_malformed_whole_map_without_mutation (None, False, 0, [], "", "bad", 17, ["bad"]); helper-only.
- Ten plik: test_module_current_truth_rejects_malformed_entry_without_mutation dla błędnych typów i state values; helper-only.
- Ten plik: test_module_current_truth_keeps_valid_and_legacy_absence_contract; absent attribute/map, other module, explicit fresh i stale.
- Ten plik: test_syntax_error_marks_authoritative_last_known_good_and_recovery; valid stale/error/recovery lifecycle.
- Ten plik: test_parse_freshness_survives_snapshot_hydration_and_recovers; valid stale snapshot roundtrip + legal recovery.
- Ten plik: test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted; invalid per-module state oraz truthy ["bad"] roundtrip; brak update po hydration.
- Ten plik: test_reading_malformed_parse_freshness_does_not_claim_recovery; malformed target, source update, assert status is not RECOVERED; nie asseruje końcowej mapy/truth dla targetu lub unrelated module.
- C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py:202 — test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic; prawidłowa syntax stale/recovery. Linia 284 test_live_persistence_failure_does_not_publish_half_updated_syntax_fact; poprawny marker shape.
- C:\Temp\Contextor_Repo\tests\test_live_state_C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:807 — test_repository_structural_clone_isolates_top_level_updater_failure; linia 890 ...success_keeps_previous_top_level_state_untouched; structural clone invariants, nie bad map coercion.
- C:\Temp\Contextor_Repo\tests\test_refresh_plan_execution.py:270 — test_case_g_noop_unchanged; semantic/no-op engine coverage bez malformed freshness.
- C:\Temp\Contextor_Repo\tests\test_freshness_preservation.py:67 — test_freshness_scenario_b_noop; no-op freshness preservation bez malformed parse map.

Brakujące regression scenarios:
1. Falsey malformed whole-map + syntax failure: assert target stale, unrelated previously unavailable module does not become current.
2. Falsey malformed whole-map + target-local parsed semantic no-op; odróżnić od early mtime UNCHANGED.
3. Falsey malformed whole-map + unrelated successful UPDATED i delete branches.
4. Truthy dict-coercible non-dict pair sequence; odróżnić od invalid ["bad"] które rzuca. Sprawdzić wszystkie missing modules po publikacji.
5. Uncoercible truthy map przez LIVE updater exception: canonical state identity/revision/snapshot unchanged, no persistence, mutation failed, watcher requeue; osobno jawnie sprawdzić czy resync/full-analysis jest wymagany.
6. Malformed target entry po udanym source parse: końcowy target truth i RECOVERED vs UNCHANGED/UPDATED.
7. Malformed target entry po syntax error: zachowanie zastąpienia untrusted wpisu na stale i publiczny rezultat.
8. Malformed non-target entry po unrelated successful update pozostaje unavailable.
9. Early UNCHANGED z malformed target markerem: parser nie jest wywołany, metadata bez zmian, zapisać graph/dependency result fields.
10. Snapshot-hydrated falsey map i dict-coercible truthy map, następnie incremental update; aktualny test zatrzymuje się po roundtrip.
11. Candidate-init exception atomicity przez local MCP, LIVE IPC i Desktop status; obecne testy dotyczą ogólnego clone failure/persistence failure, nie tego wyjątku.
12. live_state_persisted dla local fallback statuses gdy in-memory syntax/no-op metadata change nie trafia do snapshot.

## CONTEXTOR_EVIDENCE

- Deferred Contextor MCP capability discovery wykonane przed workspace text verification. Użyte narzędzia: get_symbol_implementation, get_source_range, get_symbol_call_context, get_symbol_lineage, get_artifact_blast_radius, search_source, get_live_events. contextor_fact_lineage capability sprawdzono; obsługuje swój ograniczony canonical fact-family set i nie zastępował symbol/source evidence.
- Full-symbol fetches dla primary symbols i clone method raportują implementation_is_complete=true, no_partial_symbol_source=true, workspace_sync=verified, canonical_state=fresh, provenance=live, canonical_revision=176.
- get_symbol_call_context dla _prepare_candidate_state ma scope intra_module; potwierdza execute_refresh_plan line789. Cross-module C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:139 potwierdzony osobno przez dokładny Contextor source search i targetowane lokalne rg.
- get_artifact_blast_radius dla marker mutation helpers wskazuje bezpośredniego produkcyjnego konsumenta contextor.core.analysis.incremental.engine; reachability downstream podano jako 141 modules (41 prod, 100 tests). To statyczny blast radius, nie dowód runtime exposure.
- get_live_events(repo_path, after_revision=176, limit=20): revision/latest_revision=176, continuity=continuous, brak nowszych events, resync_required=false; diagnostics families fresh. Nie wprowadzano ani nie obserwowano malformed per-module state.
- Public LIVE family module=fresh nie certyfikuje poprawności per-module parse markers. Runtime malformed marker reachability pozostaje niezaobserwowane.

## SOURCE_TRUNCATION_STATUS

- Wszystkie poniższe code blocks są kompletnymi implementacjami z Contextora; żaden preview nie został użyty jako pełne źródło.
- _prepare_candidate_state, update_file, execute_refresh_plan, _commit_syntax_candidate, _apply_delta_and_commit, module_current_truth, mark/clear, LIVE _execute_update_file, coordinator _run/submit, watcher poll i MCP update pochodzą z full AST-bounded fetch lub pełnego exact source range.
- save_snapshot fetch jawnie zgłosił complete=true.
- load_snapshot AST fetch najpierw zwrócił confirmation_required; nie użyto go jako źródła. Następny exact range 1926-2371 zwrócił wszystkie 446 linii (source_total_lines=2409) w jednym nie-preview wyniku.
- Jedno pierwsze złe file path dla module_truth_unavailable zwróciło parameter_contract_error i zostało odrzucone; skorygowany absolutny source path zwrócił pełną implementację.
- Broad search output był ograniczony i użyty wyłącznie jako locator. Pełne implementacje poniżej pochodzą z source range/full fetch.

## FULL_SOURCE_EVIDENCE

### C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:131-168 — LIVE structural clone

```python
def _clone_state_for_update(state: Any) -> Any:
    if state is None:
        raise ValueError("canonical state unavailable")

    clone_method = getattr(state, "clone_for_update", None)
    if callable(clone_method):
        candidate = clone_method()
    else:
        candidate = copy.deepcopy(state)

    if candidate is state:
        raise ValueError("canonical state clone returned original object")

    return candidate

```


### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:681-755 — full _prepare_candidate_state

```python
def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
    """Initializes Copy-on-Write candidate state from current canonical state."""
    return CandidateState(
        modules=dict(state.modules),
        reexport_facts_by_module=dict(
            getattr(
                state,
                "reexport_facts_by_module",
                {},
            )
            or {}
        ),
        artifacts=dict(state.artifacts),
        module_parse_freshness=dict(getattr(state, "module_parse_freshness", {}) or {}),
        syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
        syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
        module_usages=dict(getattr(state, "module_usages", {}) or {}),
        lineage_facts_by_source=dict(
            getattr(state, "lineage_facts_by_source", {}) or {}
        ),
        lineage_facts_state=(
            getattr(state, "lineage_facts_state", "not_materialized")
            or "not_materialized"
        ),
        lineage_facts_semantic_version=getattr(
            state,
            "lineage_facts_semantic_version",
            None,
        ),
        lineage_owner_source_index=dict(
            getattr(state, "lineage_owner_source_index", {}) or {}
        ),
        lineage_source_owner_index=dict(
            getattr(state, "lineage_source_owner_index", {}) or {}
        ),
        lineage_query_index_state=getattr(
            state,
            "lineage_query_index_state",
            "not_materialized",
        ),
        lineage_semantic_anchor_bindings_complete=bool(
            getattr(state, "lineage_semantic_anchor_bindings_complete", False)
        ),
        artifact_consumption=dict(state.artifact_consumption or {}),
        dependency_graph=state.dependency_graph,
        trie=state.trie,
        package_root=state.package_root,
        metrics=state.metrics,
        topology_analytics=dict(getattr(state, "topology_analytics", {}) or {}),
        dependency_matrix=dict(
            getattr(state, "dependency_matrix", {}) or {}
        ),
        dependency_matrix_state=getattr(
            state,
            "dependency_matrix_state",
            "deferred",
        ),
        shared_usage_clusters=list(
            getattr(state, "shared_usage_clusters", []) or []
        ),
        shared_usage_clusters_state=getattr(
            state,
            "shared_usage_clusters_state",
            "deferred",
        ),
        cached_analytics=dict(getattr(state, "cached_analytics", {}) or {}),
        topology_metrics_state=getattr(state, "topology_metrics_state", "deferred"),
        cached_analytics_state=getattr(state, "cached_analytics_state", "deferred"),
        cycles=list(getattr(state, "cycles", []) or []),
        cycles_state=getattr(state, "cycles_state", "deferred"),
        collision_facts=dict(getattr(state, "collision_facts", {}) or {}),
        collisions=list(getattr(state, "collisions", []) or []),
        collisions_state=getattr(state, "collisions_state", "deferred"),
        artifact_consumption_state=getattr(state, "artifact_consumption_state", "deferred"),
    )
```


### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:758-1273 — full execute_refresh_plan

```python
def execute_refresh_plan(
    state: RepositoryAnalysisState,
    delta: FileDelta,
    usage_delta: Any,
    plan: RefreshPlan,
    new_imports: Optional[List[Any]],
    new_artifacts: Optional[Dict[str, Any]],
    new_usage: Optional[ModuleUsageFacts],
    root_path: Path,
    file_path: str,
    new_collision_facts: Optional[List[Dict[str, Any]]] = None,
    new_reexport_facts: Optional[Dict[str, Any]] = None,
) -> PlanExecutionOutcome:
    """
    Executes the phases of a RefreshPlan (REPARSE, RECOMPUTE, PATCH, GRAPH)
    on an isolated Copy-on-Write candidate state without performing disk I/O or state mutation.
    """
    path = Path(file_path)
    mod_id = Path(delta.module_path).stem if delta.module_path.endswith(".py") else delta.module_path
    old_graph = state.dependency_graph

    if not validate_reexport_facts_by_module(
        state.reexport_facts_by_module,
        state.modules,
    ):
        raise RuntimeError(
            "Canonical re-export facts baseline is incomplete; "
            "fresh full analysis is required."
        )

    # 1. PREPARE candidate state
    candidate = _prepare_candidate_state(state)
    matrix_inputs_changed = bool(
        {
            "definitions",
            "artifact_consumption",
            "dependency_graph",
        }
        & set(plan.patch_families)
    )
    cluster_inputs_changed = bool(
        {
            "definitions",
            "artifact_consumption",
        }
        & set(plan.patch_families)
    )
    if getattr(state, "resync_required", False):
        candidate.artifact_consumption_state = "stale"

    # Pre-populate candidate modules, artifacts, and usages before RECOMPUTE
    if delta.is_deleted:
        candidate.modules.pop(mod_id, None)
        candidate.modules.pop(delta.module_path, None)
        candidate.reexport_facts_by_module.pop(
            mod_id,
            None,
        )
        candidate.reexport_facts_by_module.pop(
            delta.module_path,
            None,
        )
        candidate.artifacts.pop(mod_id, None)
        candidate.artifacts.pop(delta.module_path, None)
        candidate.module_usages.pop(delta.module_path, None)
        # Purge deleted targets
        for art_key in list(candidate.artifact_consumption.keys()):
            if (
                art_key == mod_id
                or art_key == delta.module_path
                or art_key.startswith(mod_id + ".")
                or art_key.startswith(delta.module_path + ".")
                or art_key.startswith(mod_id + "::")
                or art_key.startswith(delta.module_path + "::")
            ):
                candidate.artifact_consumption.pop(art_key, None)
    else:
        if "modules" in plan.patch_families:
            candidate.modules[delta.module_path] = Module(
                module_id=delta.module_path,
                path=str(path.relative_to(root_path)),
                absolute_path=str(path.resolve()),
                imports=new_imports or [],
            )
        if "definitions" in plan.patch_families and new_artifacts is not None:
            candidate.artifacts[delta.module_path] = new_artifacts
        if "module_usages" in plan.patch_families and new_usage is not None:
            candidate.module_usages[delta.module_path] = new_usage

        # Ensure canonical targets for delta.module_path exist in candidate.artifact_consumption
        mod_art = candidate.artifacts.get(delta.module_path, {})
        if isinstance(mod_art, dict):
            current_targets = canonical_artifact_consumption_targets({delta.module_path: mod_art})
            for t_key in current_targets:
                if t_key not in candidate.artifact_consumption:
                    candidate.artifact_consumption[t_key] = {"consumers": [], "channels": {}}
            for art_key in list(candidate.artifact_consumption.keys()):
                if (
                    art_key.startswith(f"{delta.module_path}::")
                    or art_key.startswith(f"{mod_id}::")
                ) and art_key not in current_targets:
                    candidate.artifact_consumption.pop(art_key, None)

    if not delta.is_deleted and "reexport_facts" in plan.patch_families:
        if new_reexport_facts is None:
            raise ValueError(
                f"Planned reexport_facts patch for '{delta.module_path}' "
                "requires non-None new_reexport_facts."
            )
        candidate.reexport_facts_by_module[
            delta.module_path
        ] = new_reexport_facts

    if not validate_reexport_facts_by_module(
        candidate.reexport_facts_by_module,
        candidate.modules,
    ):
        raise RuntimeError(
            "Candidate re-export facts do not cover the candidate module domain."
        )

    expected_targets = canonical_artifact_consumption_targets(
        candidate.artifacts
    )
    dotted_target_index = _build_dotted_target_index(
        expected_targets
    )
    consumer_target_index = _build_consumer_target_index(
        candidate.artifact_consumption
    )

    # 2. REPARSE - record planned reparse modules (trace-only, no secondary source I/O)
    executed_reparse: List[str] = []
    for reparse_mod in plan.reparse_modules:
        executed_reparse.append(reparse_mod)

    reexports = None
    module_export_surfaces = None
    if (
        plan.recompute_modules
        or "artifact_consumption" in plan.patch_families
    ):
        reexports = _assemble_reexport_map(
            candidate.reexport_facts_by_module
        )
        module_export_surfaces = _assemble_module_export_surfaces(
            candidate.reexport_facts_by_module
        )

    # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
    executed_recompute: List[str] = []
    if plan.recompute_modules:
        from contextor.core.analysis.refresh_planner import (
            _find_dependent_consumers,
        )

        recompute_queue = deque(plan.recompute_modules)
        scheduled_recompute = set(plan.recompute_modules)
        processed_recompute: Set[str] = set()

        while recompute_queue:
            consumer_path = recompute_queue.popleft()

            if consumer_path in processed_recompute:
                continue

            processed_recompute.add(consumer_path)

            consumer_facts = candidate.module_usages.get(
                consumer_path
            )
            if not consumer_facts:
                continue

            previous_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            candidate.artifact_consumption = _rebuild_consumer_slice(
                consumer=consumer_path,
                consumer_facts=consumer_facts,
                candidate_consumption=candidate.artifact_consumption,
                candidate_artifacts=candidate.artifacts,
                reexports=reexports,
                reexport_facts_by_module=candidate.reexport_facts_by_module,
                module_export_surfaces=module_export_surfaces,
                expected_targets=expected_targets,
                dotted_target_index=dotted_target_index,
                consumer_target_index=consumer_target_index,
            )

            executed_recompute.append(
                consumer_path
            )

            current_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            if current_slice == previous_slice:
                continue

            downstream_consumers = _find_dependent_consumers(
                consumer_path,
                candidate.module_usages,
            )

            for downstream_consumer in sorted(
                downstream_consumers
            ):
                if downstream_consumer == delta.module_path:
                    continue

                if downstream_consumer in processed_recompute:
                    continue

                if downstream_consumer in scheduled_recompute:
                    continue

                scheduled_recompute.add(
                    downstream_consumer
                )
                recompute_queue.append(
                    downstream_consumer
                )

    # 4. PATCH - apply fact families listed in plan.patch_families
    executed_patch_families: List[str] = []
    identity_sync_required = False

    for family in plan.patch_families:
        if family == "modules":
            executed_patch_families.append("modules")

        elif family == "definitions":
            executed_patch_families.append("definitions")

        elif family == "module_usages":
            executed_patch_families.append("module_usages")

        elif family == "reexport_facts":
            executed_patch_families.append("reexport_facts")

        elif family == "dependency_graph":
            if delta.is_deleted or delta.is_new:
                new_trie = build_trie(candidate.modules.keys())
                new_package_root = detect_package_root(candidate.modules, new_trie)
                new_graph = build_graph(candidate.modules, trie=new_trie, package_root=new_package_root)
                candidate.trie = new_trie
                candidate.package_root = new_package_root
                candidate.dependency_graph = new_graph
            else:
                new_trie = candidate.trie
                new_package_root = candidate.package_root
                curr_graph = candidate.dependency_graph
                if curr_graph:
                    hard, soft = resolve_module_edges(delta.module_path, candidate.modules[delta.module_path], new_trie, new_package_root)
                    candidate.dependency_graph = curr_graph.with_module_edges(delta.module_path, hard, soft)
            executed_patch_families.append("dependency_graph")

        elif family == "artifact_consumption":
            if delta.is_deleted:
                # Remove delta.module_path from all remaining targets
                for t_key, entry in list(candidate.artifact_consumption.items()):
                    if delta.module_path in entry.get("consumers", []) or delta.module_path in entry.get("channels", {}):
                        copied_entry = _get_copy_of_entry(entry)
                        if delta.module_path in copied_entry["consumers"]:
                            copied_entry["consumers"].remove(delta.module_path)
                        copied_entry["channels"].pop(delta.module_path, None)
                        candidate.artifact_consumption[t_key] = copied_entry
            elif new_usage:
                candidate.artifact_consumption = _rebuild_consumer_slice(
                    consumer=delta.module_path,
                    consumer_facts=new_usage,
                    candidate_consumption=candidate.artifact_consumption,
                    candidate_artifacts=candidate.artifacts,
                    reexports=reexports,
                    reexport_facts_by_module=candidate.reexport_facts_by_module,
                    module_export_surfaces=module_export_surfaces,
                    expected_targets=expected_targets,
                    dotted_target_index=dotted_target_index,
                    consumer_target_index=consumer_target_index,
                )
            if (
                getattr(state, "resync_required", False)
                or plan.refresh_completeness == "requires_resync"
            ):
                candidate.artifact_consumption_state = "stale"
            elif validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts):
                candidate.artifact_consumption_state = "fresh"
            else:
                candidate.artifact_consumption_state = "stale"

            executed_patch_families.append("artifact_consumption")

        elif family == "identity_registry":
            identity_sync_required = True
            executed_patch_families.append("identity_registry")

        elif family == "cached_analytics":
            from contextor.core.reporting_engine.graph_analytics import compute_cached_analytics
            hard_edges = getattr(candidate.dependency_graph, "hard_edges", {}) if candidate.dependency_graph else {}
            candidate.cached_analytics = compute_cached_analytics(
                modules=candidate.modules,
                artifacts=candidate.artifacts,
                artifact_consumption=candidate.artifact_consumption,
                hard_edges=hard_edges,
            )
            executed_patch_families.append("cached_analytics")

        elif family == "collision_facts":
            if delta.is_deleted:
                candidate.collision_facts.pop(delta.module_path, None)
            else:
                if new_collision_facts is None:
                    raise ValueError(
                        f"Planned collision_facts patch for '{delta.module_path}' requires non-None new_collision_facts."
                    )
                candidate.collision_facts[delta.module_path] = new_collision_facts
            executed_patch_families.append("collision_facts")

        elif family == "collisions":
            from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
            from contextor.core.validator.collisions import (
                compute_collisions_from_facts,
                resolve_collision_candidate_codes,
            )

            if candidate.collisions_state == "stale":
                pass
            elif _validate_collision_facts_dict(candidate.collision_facts, candidate.modules):
                try:
                    resolved_facts = resolve_collision_candidate_codes(
                        candidate.collision_facts,
                        candidate.modules,
                    )
                    candidate.collision_facts = resolved_facts
                    computed = compute_collisions_from_facts(candidate.collision_facts)
                    candidate.collisions = computed
                    candidate.collisions_state = "fresh"
                except Exception:
                    candidate.collisions_state = "deferred"
            else:
                candidate.collisions_state = "deferred"
            executed_patch_families.append("collisions")

        else:
            raise ValueError(f"Unsupported patch family: {family}")

    # 5. GRAPH - execute graph-only computations
    executed_graph_recomputations: List[str] = []
    affected_set: Set[str] = set()
    blast_radius_complete = False

    for graph_item in plan.graph_recomputations:
        if graph_item == "reverse_blast_radius":
            if delta.is_deleted:
                blast_radius_complete = old_graph is not None
            elif delta.is_new:
                blast_radius_complete = candidate.dependency_graph is not None
            else:
                blast_radius_complete = old_graph is not None and candidate.dependency_graph is not None

            affected_set = (
                calculate_affected_set(
                    delta.module_path,
                    old_graph=old_graph,
                    new_graph=candidate.dependency_graph,
                )
                if blast_radius_complete
                else set()
            )
            executed_graph_recomputations.append("reverse_blast_radius")

        elif graph_item == "macro_metrics":
            if candidate.dependency_graph is not None:
                from contextor.core.graph.metrics import compute_graph_metrics
                candidate.metrics = compute_graph_metrics(
                    candidate.dependency_graph.hard_edges,
                    candidate.dependency_graph.soft_edges,
                )
            executed_graph_recomputations.append("macro_metrics")

        elif graph_item == "advanced_graph_metrics":
            if candidate.dependency_graph is not None:
                from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
                candidate.topology_analytics = compute_topology_analytics(
                    candidate.dependency_graph.hard_edges,
                    candidate.dependency_graph.soft_edges,
                    candidate.metrics,
                )
            executed_graph_recomputations.append("advanced_graph_metrics")

        elif graph_item == "cycles":
            if candidate.dependency_graph is not None:
                from contextor.core.graph.cycles import detect_cycles
                hard_edges = getattr(candidate.dependency_graph, "hard_edges", {}) or {}
                candidate.cycles = detect_cycles(hard_edges)
            executed_graph_recomputations.append("cycles")

        else:
            raise ValueError(f"Unsupported graph recomputation: {graph_item}")

    # 6. FRESHNESS ASSIGNMENT
    if plan.refresh_completeness == "requires_resync" or getattr(state, "resync_required", False):
        candidate.topology_metrics_state = "stale"
        candidate.cached_analytics_state = "stale"
        candidate.cycles_state = "stale"
        candidate.collisions_state = "stale"
        candidate.artifact_consumption_state = "stale"
    else:
        if "advanced_graph_metrics" in plan.graph_recomputations:
            candidate.topology_metrics_state = "fresh"
        if "cached_analytics" in plan.patch_families:
            candidate.cached_analytics_state = "fresh"
        if "cycles" in plan.graph_recomputations:
            candidate.cycles_state = "fresh"

    derived_artifact_projection = None
    derived_artifact_projection_failed = False
    if (
        (matrix_inputs_changed or cluster_inputs_changed)
        and plan.refresh_completeness != "requires_resync"
        and not getattr(state, "resync_required", False)
    ):
        from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
        if artifact_consumption_is_fresh(candidate):
            from contextor.core.reporting_engine.graph_analytics import build_artifact_data_projection
            try:
                derived_artifact_projection = build_artifact_data_projection(
                    artifacts=candidate.artifacts,
                    artifact_consumption=candidate.artifact_consumption,
                )
            except Exception:
                derived_artifact_projection_failed = True

    if plan.refresh_completeness == "requires_resync" or getattr(
        state, "resync_required", False
    ):
        candidate.dependency_matrix_state = "stale"
    elif matrix_inputs_changed:
        from contextor.core.analysis.state_manager import (
            dependency_matrix_inputs_are_fresh,
        )

        if not dependency_matrix_inputs_are_fresh(candidate) or derived_artifact_projection_failed:
            candidate.dependency_matrix_state = "stale"
        else:
            from contextor.core.reporting_engine.graph_analytics import (
                build_module_dependency_matrix,
            )

            try:
                hard_edges = (
                    getattr(candidate.dependency_graph, "hard_edges", {}) or {}
                    if candidate.dependency_graph is not None
                    else {}
                )
                dependency_matrix = build_module_dependency_matrix(
                    artifact_data=derived_artifact_projection,
                    hard_edges=hard_edges,
                )
            except Exception:
                candidate.dependency_matrix_state = "stale"
            else:
                candidate.dependency_matrix = dependency_matrix
                candidate.dependency_matrix_state = "fresh"

    if plan.refresh_completeness == "requires_resync" or getattr(
        state, "resync_required", False
    ):
        candidate.shared_usage_clusters_state = "stale"
    elif cluster_inputs_changed:
        from contextor.core.analysis.state_manager import (
            artifact_consumption_is_fresh,
        )

        if not artifact_consumption_is_fresh(candidate) or derived_artifact_projection_failed:
            candidate.shared_usage_clusters_state = "stale"
        else:
            from contextor.core.reporting_engine.graph_analytics import (
                build_jaccard_clusters,
            )

            try:
                clusters = build_jaccard_clusters(artifact_data=derived_artifact_projection)
            except Exception:
                candidate.shared_usage_clusters_state = "stale"
            else:
                candidate.shared_usage_clusters = clusters
                candidate.shared_usage_clusters_state = "fresh"

    # 7. PREPARE registry payload if required
    all_modules = set(candidate.modules.keys())
    current_artifacts = collect_qualified_artifact_identities(candidate.artifacts) if identity_sync_required else {}

    execution_trace = {
        "reparse_modules": tuple(executed_reparse),
        "recompute_modules": tuple(executed_recompute),
        "patch_families": tuple(executed_patch_families),
        "graph_recomputations": tuple(executed_graph_recomputations),
    }

    return PlanExecutionOutcome(
        candidate_state=candidate,
        affected_modules=affected_set,
        blast_radius_complete=blast_radius_complete,
        execution_trace=execution_trace,
        identity_sync_required=identity_sync_required,
        all_modules=all_modules,
        current_artifacts=current_artifacts,
    )
```


### C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:227-303 — truth, stale mark, clear

```python
def module_current_truth(state: RepositoryAnalysisState, module_name: str) -> Dict[str, Any]:
    """Return authoritative per-module parse freshness and provenance."""
    missing = object()
    freshness = getattr(state, "module_parse_freshness", missing)

    if freshness is missing:
        freshness = {}

    entry = (
        freshness.get(module_name, missing)
        if isinstance(freshness, dict)
        else None
    )

    if entry is missing:
        return {"available": True, "state": "fresh", "provenance": "current"}

    if (
        not isinstance(entry, dict)
        or type(entry.get("state")) is not str
        or entry["state"] not in {"fresh", "stale"}
    ):
        return {
            "available": False,
            "state": "unavailable",
            "provenance": "untrusted",
            "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
        }

    if entry["state"] == "fresh":
        return {"available": True, "state": "fresh", "provenance": "current"}

    return {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            key: entry.get(key)
            for key in ("error", "line_number", "column_number")
            if entry.get(key) is not None
        },
    }


def mark_module_parse_failure(
    state: RepositoryAnalysisState,
    module_name: str,
    *,
    error: str | None,
    line_number: int | None,
    column_number: int | None,
) -> None:
    """Mark retained module facts as last-known-good after a parse failure."""
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        freshness = {}
        state.module_parse_freshness = freshness
    freshness[module_name] = {
        "state": "stale",
        "error": error,
        "line_number": line_number,
        "column_number": column_number,
    }


def clear_module_parse_failure(
    state: RepositoryAnalysisState, module_name: str
) -> bool:
    """Clear parse failure and report whether this is a recovery transition."""
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        return False
    entry = freshness.get(module_name)
    recovered = isinstance(entry, dict) and entry.get("state") == "stale"
    freshness.pop(module_name, None)
    return recovered
```


### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:126-206 — full _commit_syntax_candidate

```python
    def _commit_syntax_candidate(
        self,
        *,
        source_path: str,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        mark_parse_error: tuple[str | None, int | None, int | None] | None = None,
        clear_parse_module: str | None = None,
        degrade_syntax_family: bool = False,
        extracted_lineage_facts: Any | None = None,
        invalidate_lineage: bool = False,
    ) -> None:
        """Commit syntax, parse-freshness, and lineage changes through one COW candidate."""
        candidate = _prepare_candidate_state(self.state)
        if invalidate_lineage:
            from contextor.core.domain.lineage_facts import (
                LINEAGE_FACTS_SEMANTIC_VERSION,
                LineageFamilyStatus,
            )
            from contextor.core.lineage_query.index import (
                build_lineage_query_indexes,
            )

            candidate.lineage_facts_by_source.pop(source_path, None)
            if candidate.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value:
                candidate.lineage_facts_state = LineageFamilyStatus.NOT_MATERIALIZED.value
                candidate.lineage_facts_semantic_version = None
            else:
                candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
                candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
            (
                candidate.lineage_owner_source_index,
                candidate.lineage_source_owner_index,
                candidate.lineage_semantic_anchor_bindings_complete,
            ) = build_lineage_query_indexes(candidate.lineage_facts_by_source)
            candidate.lineage_query_index_state = (
                "not_materialized"
                if candidate.lineage_facts_state
                == LineageFamilyStatus.NOT_MATERIALIZED.value
                else "fresh"
            )
            if candidate.lineage_query_index_state != "fresh":
                candidate.lineage_semantic_anchor_bindings_complete = False
        elif extracted_lineage_facts is not None:
            with self.registry.read_transaction():
                self._update_candidate_lineage_slice(
                    candidate,
                    source_path=source_path,
                    extracted_lineage_facts=extracted_lineage_facts,
                )
        if remove_syntax_fact:
            candidate.syntax_diagnostics_by_path.pop(source_path, None)
        elif syntax_fact is not None:
            candidate.syntax_diagnostics_by_path[source_path] = syntax_fact
        if degrade_syntax_family and candidate.syntax_diagnostics_state == "fresh":
            candidate.syntax_diagnostics_state = "deferred"
        if mark_parse_error is not None:
            error, line_number, column_number = mark_parse_error
            mark_module_parse_failure(
                candidate,
                clear_parse_module or "",
                error=error,
                line_number=line_number,
                column_number=column_number,
            )
        elif clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )
        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
        self.state.lineage_query_index_state = candidate.lineage_query_index_state
        self.state.lineage_semantic_anchor_bindings_complete = (
            candidate.lineage_semantic_anchor_bindings_complete
        )
```


### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:453-734 — full IncrementalAnalysisEngine.update_file

```python
    def update_file(self, file_path: str) -> IncrementalUpdateResult:
        """
        Updates the canonical state incrementally for a single changed file.
        Returns the update status and the freshness of the architectural model.
        """
        with self._lock:
            if getattr(self.state, "resync_required", False):
                # Every exit path, including a semantic no-op, must expose the
                # already-lost incremental continuity as fail-closed.
                self.state.artifact_consumption_state = "stale"
            path = Path(file_path)
            rel_path = path.relative_to(self.root_path)
            module_path = ".".join(rel_path.with_suffix("").parts)
            source_path = canonical_python_source_path(rel_path.as_posix())
            if source_path is None:
                raise ValueError(f"Incremental source path is not canonical Python: {file_path}")

            if (
                not self.state_manager.has_changed(file_path)
                and module_path in self.state.modules
            ):
                return IncrementalUpdateResult(
                    status="UNCHANGED",
                    file_path=file_path,
                    graph_state="fresh" if self.state.dependency_graph is not None else "stale",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                )

            # 1. Handle Deletion
            current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
            if not current_state:
                old_module = self.state.modules.get(module_path)
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
                delta, usage_delta, collision_facts_changed = prepare_deleted_module_update(
                    module_path,
                    old_module=old_module,
                    old_artifacts=old_artifacts,
                    old_usage=old_usage,
                    old_collision_facts=old_collision_facts,
                )

                from contextor.core.analysis.refresh_planner import RefreshPlanner
                plan = RefreshPlanner.plan_refresh(
                    delta,
                    usage_delta=usage_delta,
                    module_usages=self.state.module_usages,
                    collision_facts_changed=collision_facts_changed,
                )
                _trace_incremental_phase(
                    "INCREMENTAL_APPLY_START",
                    result=(
                        f"artifacts_added={len(delta.artifacts_added)};"
                        f"artifacts_removed={len(delta.artifacts_removed)};"
                        f"artifacts_changed={len(delta.artifacts_changed)};"
                        f"patch_families={','.join(plan.patch_families)}"
                    ),
                )
                affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                    file_path, delta, usage_delta, plan, [], {}, ModuleUsageFacts(),
                    new_collision_facts=None,
                    new_reexport_facts=None,
                    syntax_source_path=source_path,
                    remove_syntax_fact=True,
                    clear_parse_module=module_path,
                )
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                affected_modules = sorted(affected_set) if blast_radius_complete else []
                return IncrementalUpdateResult(
                    status="DELETED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state=blast_radius_state,
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state="fresh",
                    cached_analytics_state="fresh",
                    cycles_state="fresh",
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                    affected_modules=affected_modules,
                    shadow_plan=plan,
                    execution_trace=execution_trace,
                )

            # 2. Prepare Source Update
            module_id = self.registry.get_module_id(module_path)
            is_new = (module_id is None) or (module_path not in self.state.modules)
            old_module = self.state.modules.get(module_path)
            old_artifacts = self.state.artifacts.get(module_path, {})
            old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
            old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
            old_reexport_facts = (
                self.state.reexport_facts_by_module.get(
                    module_path
                )
            )

            prep = prepare_source_update(
                file_path=file_path,
                module_path=module_path,
                is_new=is_new,
                old_module=old_module,
                old_artifacts=old_artifacts,
                old_usage=old_usage,
                persistent_id=module_id,
                old_collision_facts=old_collision_facts,
                source_key=source_path,
                old_reexport_facts=old_reexport_facts,
            )

            if prep.has_error:
                syntax_fact = (
                    {
                        "status": "checked_with_errors",
                        "errors": [{
                            "message": prep.error_message,
                            "line_number": prep.line_number,
                            "column_number": prep.column_number,
                        }],
                    }
                    if prep.error_status == "SYNTAX_ERROR"
                    else None
                )
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=syntax_fact,
                    mark_parse_error=(
                        prep.error_message,
                        prep.line_number,
                        prep.column_number,
                    ),
                    clear_parse_module=module_path,
                    degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
                    invalidate_lineage=True,
                )
                return IncrementalUpdateResult(
                    status=prep.error_status,
                    file_path=file_path,
                    error=prep.error_message,
                    line_number=prep.line_number,
                    column_number=prep.column_number,
                )

            freshness = getattr(self.state, "module_parse_freshness", {}) or {}
            recovered_from_parse_failure = (
                isinstance(freshness.get(module_path), dict)
                and freshness[module_path].get("state") == "stale"
            )
            checked_and_none = {"status": "checked_and_none", "errors": []}

            delta = prep.delta
            usage_delta = prep.usage_delta
            new_imports = prep.new_imports
            new_artifacts = prep.new_artifacts
            new_usage = prep.new_usage
            new_collision_facts = prep.new_collision_facts
            new_reexport_facts = prep.new_reexport_facts

            from contextor.core.analysis.refresh_planner import RefreshPlanner
            plan = RefreshPlanner.plan_refresh(
                delta,
                usage_delta=usage_delta,
                module_usages=self.state.module_usages,
                collision_facts_changed=prep.collision_facts_changed,
            )

            # Check if true no-op
            if plan.is_empty and not is_new and not delta.is_deleted:
                # Parsing proved the tracked source is semantically unchanged.
                # Acknowledge its current fingerprint so restart reconciliation
                # does not repeatedly queue the same canonical module.
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=checked_and_none,
                    clear_parse_module=module_path,
                    extracted_lineage_facts=prep.extracted_lineage_facts,
                )
                self.state_manager.update_state(file_path)
                return IncrementalUpdateResult(
                    status="RECOVERED" if recovered_from_parse_failure else "UNCHANGED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                    affected_modules=[],
                    shadow_plan=plan,
                    execution_trace={
                        "reparse_modules": (),
                        "recompute_modules": (),
                        "patch_families": (),
                        "graph_recomputations": (),
                    },
                )

            # 3. Apply and Commit driven by RefreshPlan
            _trace_incremental_phase(
                "INCREMENTAL_APPLY_START",
                result=(
                    f"artifacts_added={len(delta.artifacts_added)};"
                    f"artifacts_removed={len(delta.artifacts_removed)};"
                    f"artifacts_changed={len(delta.artifacts_changed)};"
                    f"patch_families={','.join(plan.patch_families)}"
                ),
            )
            affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage,
                new_collision_facts=new_collision_facts,
                new_reexport_facts=new_reexport_facts,
                extracted_lineage_facts=prep.extracted_lineage_facts,
                syntax_source_path=source_path,
                syntax_fact=checked_and_none,
                clear_parse_module=module_path,
            )

            if plan.refresh_completeness == "requires_resync":
                graph_state = "stale"
                dependencies_state = "stale"
                blast_radius_state = "deferred"
                topology_metrics_state = "stale"
                cached_analytics_state = "stale"
                cycles_state = "stale"
                collisions_state = "stale"
                artifact_consumption_state = "stale"
            else:
                graph_state = "fresh" if ("dependency_graph" in plan.patch_families or self.state.dependency_graph is not None) else "stale"
                dependencies_state = "fresh"
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                if "advanced_graph_metrics" in plan.graph_recomputations:
                    topology_metrics_state = "fresh"
                else:
                    topology_metrics_state = getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred")
                if "cached_analytics" in plan.patch_families:
                    cached_analytics_state = "fresh"
                else:
                    cached_analytics_state = getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred")
                if "cycles" in plan.graph_recomputations:
                    cycles_state = "fresh"
                else:
                    cycles_state = getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred")
                collisions_state = getattr(self.state, "collisions_state", "deferred")
                artifact_consumption_state = "fresh" if artifact_consumption_is_fresh(self.state) else "stale"

            affected_modules = sorted(affected_set) if blast_radius_complete else []

            return IncrementalUpdateResult(
                status="RECOVERED" if recovered_from_parse_failure else "UPDATED",
                file_path=file_path,
                delta=delta,
                graph_state=graph_state,
                dependencies_state=dependencies_state,
                blast_radius_state=blast_radius_state,
                local_metrics_state="deferred",
                global_metrics_state="deferred",
                topology_metrics_state=topology_metrics_state,
                cached_analytics_state=cached_analytics_state,
                cycles_state=cycles_state,
                collisions_state=collisions_state,
                artifact_consumption_state=artifact_consumption_state,
                affected_modules=affected_modules,
                shadow_plan=plan,
                execution_trace=execution_trace,
            )
```


### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:760-1018 — full _apply_delta_and_commit

```python
    def _apply_delta_and_commit(
        self,
        file_path: str,
        delta: FileDelta,
        usage_delta: Any,
        plan: Any,
        new_imports: list,
        mod_artifacts: dict,
        new_usage: Any,
        new_collision_facts: Optional[List[Dict[str, Any]]] = None,
        new_reexport_facts: Optional[Dict[str, Any]] = None,
        extracted_lineage_facts: Any | None = None,
        syntax_source_path: str | None = None,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        clear_parse_module: str | None = None,
    ) -> tuple[Set[str], bool, dict]:
        """
        Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
        """
        resync_required = bool(getattr(self.state, "resync_required", False))
        execute_started = time.monotonic()
        _trace_incremental_phase(
            "INCREMENTAL_EXECUTE_PLAN_START",
        )
        try:
            outcome = execute_refresh_plan(
                state=self.state,
                delta=delta,
                usage_delta=usage_delta,
                plan=plan,
                new_imports=new_imports,
                new_artifacts=mod_artifacts,
                new_usage=new_usage,
                root_path=self.root_path,
                file_path=file_path,
                new_collision_facts=new_collision_facts,
                new_reexport_facts=new_reexport_facts,
            )
        except Exception as exc:
            _trace_incremental_phase(
                "INCREMENTAL_EXECUTE_PLAN_FAIL",
                started=execute_started,
                error=str(exc),
            )
            raise
        _trace_incremental_phase(
            "INCREMENTAL_EXECUTE_PLAN_END",
            started=execute_started,
            result=(
                f"identity_sync_required="
                f"{outcome.identity_sync_required};"
                f"patch_families="
                f"{','.join(outcome.execution_trace.get('patch_families', ()))};"
                f"recompute_count="
                f"{len(outcome.execution_trace.get('recompute_modules', ()))};"
                f"graph_count="
                f"{len(outcome.execution_trace.get('graph_recomputations', ()))}"
            ),
        )

        candidate = outcome.candidate_state

        # Persistent identity sync and lineage materialization share one registry view.
        if outcome.identity_sync_required:
            try:
                with self.registry.transaction():
                    registry_started = time.monotonic()
                    _trace_incremental_phase(
                        "INCREMENTAL_REGISTRY_SYNC_START",
                        count=len(outcome.current_artifacts),
                    )
                    try:
                        self.registry.sync_with_workspace(
                            outcome.all_modules,
                            outcome.current_artifacts,
                        )
                    except Exception as exc:
                        _trace_incremental_phase(
                            "INCREMENTAL_REGISTRY_SYNC_FAIL",
                            started=registry_started,
                            error=str(exc),
                        )
                        raise
                    missing_after_sync = sorted(
                        outcome.current_artifacts
                        - set(
                            self.registry._state[
                                "artifact_registry"
                            ]["path_to_id"]
                        )
                    )
                    _trace_incremental_phase(
                        "INCREMENTAL_REGISTRY_SYNC_END",
                        started=registry_started,
                        count=len(missing_after_sync),
                        result=(
                            "missing_after_sync="
                            + ",".join(
                                missing_after_sync[:5]
                            )
                        ),
                    )

                    lineage_started = time.monotonic()
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_START",
                        result="rematerialize_all=true",
                    )
                    try:
                        self._update_candidate_lineage_slice(
                            candidate,
                            source_path=(
                                syntax_source_path or ""
                            ),
                            extracted_lineage_facts=(
                                extracted_lineage_facts
                            ),
                            delete=bool(
                                getattr(
                                    delta,
                                    "is_deleted",
                                    False,
                                )
                            ),
                            rematerialize_all=True,
                        )
                    except Exception as exc:
                        _trace_incremental_phase(
                            "INCREMENTAL_LINEAGE_FAIL",
                            started=lineage_started,
                            error=str(exc),
                        )
                        raise
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_END",
                        started=lineage_started,
                        result="rematerialize_all=true",
                    )
            except Exception:
                # A failed write transaction leaves no persisted commit; reload its
                # in-memory view before exposing the registry again.
                with self.registry.read_transaction():
                    pass
                raise
        elif extracted_lineage_facts is not None or bool(
            getattr(delta, "is_deleted", False)
        ):
            _trace_incremental_phase(
                "INCREMENTAL_REGISTRY_SYNC_SKIP",
                result="identity_sync_required=false",
            )
            with self.registry.read_transaction():
                lineage_started = time.monotonic()
                _trace_incremental_phase(
                    "INCREMENTAL_LINEAGE_START",
                    result="rematerialize_all=false",
                )
                try:
                    self._update_candidate_lineage_slice(
                        candidate,
                        source_path=(
                            syntax_source_path or ""
                        ),
                        extracted_lineage_facts=(
                            extracted_lineage_facts
                        ),
                        delete=bool(
                            getattr(
                                delta,
                                "is_deleted",
                                False,
                            )
                        ),
                    )
                except Exception as exc:
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_FAIL",
                        started=lineage_started,
                        error=str(exc),
                    )
                    raise
                _trace_incremental_phase(
                    "INCREMENTAL_LINEAGE_END",
                    started=lineage_started,
                    result="rematerialize_all=false",
                )

        # Canonical State Publication
        if remove_syntax_fact and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path.pop(syntax_source_path, None)
        elif syntax_fact is not None and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path[syntax_source_path] = syntax_fact
        if clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.modules = candidate.modules
        self.state.reexport_facts_by_module = (
            candidate.reexport_facts_by_module
        )
        self.state.artifacts = candidate.artifacts
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.dependency_graph = candidate.dependency_graph
        self.state.metrics = candidate.metrics
        self.state.topology_analytics = candidate.topology_analytics
        self.state.cached_analytics = candidate.cached_analytics
        self.state.dependency_matrix = candidate.dependency_matrix
        self.state.dependency_matrix_state = candidate.dependency_matrix_state
        self.state.shared_usage_clusters = candidate.shared_usage_clusters
        self.state.shared_usage_clusters_state = candidate.shared_usage_clusters_state
        self.state.topology_metrics_state = candidate.topology_metrics_state
        self.state.cached_analytics_state = candidate.cached_analytics_state
        self.state.cycles = candidate.cycles
        self.state.cycles_state = candidate.cycles_state
        self.state.collision_facts = candidate.collision_facts
        self.state.collisions = candidate.collisions
        self.state.collisions_state = candidate.collisions_state
        self.state.artifact_consumption = candidate.artifact_consumption
        if (
            candidate.artifact_consumption_state != "stale"
            and not resync_required
            and validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts)
        ):
            self.state.artifact_consumption_state = "fresh"
        else:
            self.state.artifact_consumption_state = "stale"
        if resync_required:
            # A lost incremental continuity is authoritative until a full
            # rebuild replaces this state; an incremental candidate cannot
            # certify it fresh again.
            self.state.resync_required = True
        self.state.module_usages = candidate.module_usages
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )
        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
        self.state.lineage_query_index_state = candidate.lineage_query_index_state
        self.state.lineage_semantic_anchor_bindings_complete = (
            candidate.lineage_semantic_anchor_bindings_complete
        )
        self.state.trie = candidate.trie
        self.state.package_root = candidate.package_root

        # FileStateManager acknowledgement
        file_state_started = time.monotonic()
        _trace_incremental_phase(
            "INCREMENTAL_FILE_STATE_START",
        )
        self.state_manager.update_state(file_path)
        _trace_incremental_phase(
            "INCREMENTAL_FILE_STATE_END",
            started=file_state_started,
        )

        return outcome.affected_modules, outcome.blast_radius_complete, outcome.execution_trace
```


### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1108-1152 — full _repository_updater

```python
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
```


### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1153-1260 — full _repository_persister

```python
def _repository_persister(
    root: Path,
    holder: dict[str, object] | None = None,
    *,
    previous_state: object | None = None,
):
    identity = require_repository_identity(root)
    cache = repo_cache_dir(root)
    persisted_state = previous_state

    def persist(state, exact_revision: int):
        nonlocal persisted_state

        import time

        op = _safe_current_trace_operation()
        manager = (holder or {}).get("manager")

        if manager is None:
            from contextor.core.analysis.state_manager import FileStateManager

            manager = FileStateManager(
                str(cache)
            )

        state_id = (
            holder or {}
        ).get(
            "state_id",
            getattr(
                manager,
                "state_id",
                "",
            ),
        )

        snapshot_started = time.monotonic()

        try:
            meta = save_snapshot(
                state,
                cache,
                str(state_id),
                writer="live-service",
                repo_id=identity.repo_id,
                root_path=identity.root_path,
                exact_revision=exact_revision,
                file_state_payload=manager.build_payload(
                    str(state_id),
                    exact_revision,
                ),
                previous_state=persisted_state,
            )
        except Exception as exc:
            try:
                _restore_registry_checkpoint(holder)
            except Exception as rollback_exc:
                failure = RuntimeError(
                    "Canonical snapshot persistence failed and registry rollback failed."
                )
                failure.current_revision = exact_revision - 1
                raise failure from rollback_exc
            finally:
                _clear_registry_checkpoint(holder)

            from contextor.core.live_state.store import SnapshotRevisionConflict

            if isinstance(exc, SnapshotRevisionConflict):
                raise CanonicalPersistenceConflict(
                    exc.current_revision,
                    exc.requested_revision,
                ) from exc

            raise

        try:
            if meta.revision != exact_revision:
                raise ValueError(
                    "Exact LIVE persistence revision mismatch."
                )
        finally:
            _clear_registry_checkpoint(holder)

        persisted_state = state

        _safe_trace_event(
            "LIVE",
            "SNAPSHOT_SAVE_END",
            op=op,
            repo=str(root),
            elapsed_ms=(
                time.monotonic()
                - snapshot_started
            )
            * 1000.0,
        )

        _safe_trace_event(
            "LIVE",
            "FILE_STATE_SAVE_END",
            op=op,
            repo=str(root),
            elapsed_ms=0.0,
        )

        return meta

    return persist

```


### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1856-1864 — full queued updater wrapper

```python
    def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
        trace_op = _safe_trace_op(request, "u")
        if trace_op is not None:
            request = {**request, "trace_op": trace_op}

        if self._mutation_guard is None:
            return self._execute_update_file(request, allow_recovery_fence=True)
        with self._mutation_guard(request, self._stop):
            return self._execute_update_file(request, allow_recovery_fence=True)
```


### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1866-2129 — full CanonicalLiveServer._execute_update_file

```python
    def _execute_update_file(
        self, request: dict[str, Any], *, allow_recovery_fence: bool = False
    ) -> dict[str, Any]:
        if (
            not allow_recovery_fence
            and self._mutation_coordinator.recovery_verification_active()
        ):
            return {
                "status": "error",
                "error": "recovery_verification_in_progress",
                "accepted": False,
            }
        with self._mutation_execution_lock:
            if (
                not allow_recovery_fence
                and self._mutation_coordinator.recovery_verification_active()
            ):
                return {
                    "status": "error",
                    "error": "recovery_verification_in_progress",
                    "accepted": False,
                }
            with self._lock:
                if self._state is None or self._updater is None:
                    return {
                        "status": "error",
                        "error": "live_state_unavailable",
                    }
                previous_state = self._state
                previous_revision = self._revision
                expected_revision = previous_revision + 1
                updater = self._updater
                persister = self._persister

            file_path = str(request.get("file_path", ""))
            trace_op = _safe_trace_op(request, "u")
            if trace_op is not None:
                request = {**request, "trace_op": trace_op}
            _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)

            try:
                candidate_state = _clone_state_for_update(previous_state)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
                return {
                    "status": "error",
                    "error": "canonical_state_clone_failed",
                    "revision": previous_revision,
                    "expected_revision": expected_revision,
                    "detail": str(exc),
                }
            _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)

            # IMPORTANT: updater operates ONLY on candidate_state.
            # It must never receive previous_state/self._state directly.
            _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
            updater_started = time.monotonic()
            try:
                with _trace_operation_context(trace_op):
                    result = updater(candidate_state, file_path)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
                raise
            _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))

            try:
                state_rev = _extract_state_revision(candidate_state)
            except ValueError:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "invalid_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if state_rev is None:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": None,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev == previous_revision:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev < previous_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "non_monotonic_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev > expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            # Final parity proof before commit.
            if _extract_state_revision(candidate_state) != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "canonical_revision_binding_failed",
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if persister is not None:
                _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
                try:
                    with _trace_operation_context(trace_op):
                        persister(candidate_state, expected_revision)
                except Exception as exc:
                    from .store import SnapshotRevisionConflict

                    status = (
                        "canonical_persistence_revision_conflict"
                        if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
                        else "canonical_persistence_failed"
                    )
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
                    response = {
                        "status": "error",
                        "error": status,
                        "revision": previous_revision,
                        "expected_revision": expected_revision,
                    }
                    persisted_revision = getattr(exc, "current_revision", None)
                    if persisted_revision is not None:
                        response["persisted_revision"] = persisted_revision
                        response["resync_required"] = True
                    return response
                _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)

            with self._lock:
                if self._revision != previous_revision or self._state is not previous_state:
                    _safe_trace_event(
                        "LIVE",
                        "UPDATE_FAIL",
                        op=trace_op,
                        path=file_path,
                        rev=self._revision,
                        status="canonical_revision_changed_during_update",
                        expected_revision=expected_revision,
                    )
                    return {
                        "status": "error",
                        "error": "canonical_revision_changed_during_update",
                        "revision": self._revision,
                        "expected_revision": expected_revision,
                    }

                # ATOMIC COMMIT BOUNDARY.
                # Nothing above this line may replace/mutate active canonical ownership.
                self._state = candidate_state
                self._revision = expected_revision
                _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)

                try:
                    diagnostic_delta = _build_diagnostic_delta(
                        previous_state, self._state
                    )
                except Exception:
                    diagnostic_delta = []
                diagnostic_payload = _bounded_diagnostic_payload(diagnostic_delta)
                event_request = dict(request)
                # Request payload is untrusted metadata: only the committed-state
                # comparison may publish diagnostic evidence.
                event_request.pop("diagnostic_changes", None)
                if diagnostic_payload is not None:
                    event_request["diagnostic_changes"] = diagnostic_payload

                evt = self._record_event(
                    "update_file",
                    event_request,
                    result,
                    category="LIVE_STATE",
                )
                committed_revision = self._revision
                committed_seq = evt["seq"]

            _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=committed_revision, seq=committed_seq, status=getattr(result, "status", None))
            origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
            trace_common = {
                "repo": self._authority_identity.get("root_path"),
                "repo_id": self._authority_identity.get("repo_id"),
                "origin": origin,
                "diagnostic_total": len(diagnostic_delta),
                "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
            }
            for change in diagnostic_delta:
                event_name = _diagnostic_trace_event_name(change)
                if event_name is None:
                    continue
                trace_fields = {
                    **trace_common,
                    "diagnostic_kind": change["diagnostic_kind"],
                    "diagnostic_key": change["diagnostic_key"],
                }
                if "source_path" in change:
                    trace_fields["path"] = change["source_path"]
                if change["diagnostic_kind"] == "syntax":
                    trace_fields.update(
                        error=change["message"],
                        line_number=change["line_number"],
                        column_number=change["column_number"],
                    )
                elif change["diagnostic_kind"] == "collision":
                    for field in (
                        "collision_kind",
                        "collision_artifact_type",
                        "collision_symbol",
                        "collision_is_identical",
                        "collision_nodes",
                    ):
                        trace_fields[field] = change[field]
                else:
                    trace_fields["cycle_nodes"] = change["cycle_nodes"]
                _safe_trace_event(
                    "LIVE", event_name, op=trace_op, rev=committed_revision, **trace_fields
                )

            return {
                "status": "ok",
                "activity_epoch": self._activity_epoch,
                "revision": committed_revision,
                "result": result,
                "seq": committed_seq,
            }
```


### ipc.py — full CanonicalMutationCoordinator._run

```python
    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and not self._stop:
                    self._condition.wait()
                if self._stop and not self._queue:
                    return
                job_id = self._queue.popleft()
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                if job.state == "cancelled":
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                    continue
                job.state = "running"
                job.started_revision = int(self._revision_reader())
                execution_request = dict(job.request)
                execution_request.update(
                    {
                        "job_id": job.job_id,
                        "queue_order": job.queue_order,
                        "accepted_revision": job.accepted_revision,
                        "started_revision": job.started_revision,
                    }
                )

            try:
                response = self._executor(execution_request)
            except Exception as exc:
                response = {
                    "status": "error",
                    "error": "canonical_mutation_execution_failed",
                    "detail": str(exc),
                }
                with self._condition:
                    job.state = "failed"
                    job.response = response
                    job.error = str(exc)
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                continue

            with self._condition:
                if isinstance(response, dict) and response.get("status") == "ok":
                    job.state = "completed"
                    job.response = response
                else:
                    job.state = "failed"
                    if isinstance(response, dict):
                        job.response = response
                        error = response.get("error")
                        job.error = str(error) if error is not None else "canonical_mutation_invalid_response"
                    else:
                        job.response = {
                            "status": "error",
                            "error": "canonical_mutation_invalid_response",
                        }
                        job.error = "canonical_mutation_invalid_response"
                final_revision = job.response.get("revision") if job.response else None
                if isinstance(final_revision, int) and not isinstance(final_revision, bool):
                    job.final_revision = final_revision
                self._prune_terminal_locked()
                self._condition.notify_all()

```


### ipc.py — full CanonicalMutationCoordinator.submit

```python
    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            request_dict = dict(request)
        except (TypeError, ValueError):
            request_dict = {}
        file_path = request_dict.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            return {"status": "error", "error": "invalid_file_path"}
        idempotency_key = request_dict.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            return {"status": "error", "error": "invalid_idempotency_key"}

        with self._condition:
            if self._recovery_verification_fenced:
                return {
                    "status": "error",
                    "error": "recovery_verification_in_progress",
                    "accepted": False,
                }
            existing_job_id = self._idempotency_jobs.get(idempotency_key)
            if existing_job_id is not None:
                existing_job = self._jobs.get(existing_job_id)
                if existing_job is not None:
                    return {
                        "status": "accepted",
                        "accepted": True,
                        "job_id": existing_job.job_id,
                        "queue_order": existing_job.queue_order,
                        "accepted_revision": existing_job.accepted_revision,
                        "state": existing_job.state,
                    }
                del self._idempotency_jobs[idempotency_key]
            if not self._accepting:
                return {
                    "status": "error",
                    "error": "canonical_mutation_queue_closed",
                }

            self._queue_order += 1
            job_id = "mu-" + uuid.uuid4().hex
            accepted_revision = int(self._revision_reader())
            job = _MutationJob(
                job_id=job_id,
                queue_order=self._queue_order,
                request=request_dict,
                accepted_revision=accepted_revision,
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = job
            self._idempotency_jobs[idempotency_key] = job_id
            self._queue.append(job_id)
            self._ensure_started_locked()
            self._condition.notify_all()
            return {
                "status": "accepted",
                "accepted": True,
                "job_id": job_id,
                "queue_order": job.queue_order,
                "accepted_revision": accepted_revision,
                "state": job.state,
            }

```


### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:2131-2374 — full dispatch method

```python
    def _dispatch(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
            return {"status": "error", "error": "invalid_request"}
        operation = request["operation"]
        if operation == "_recovery_lifecycle_wake":
            if request.get("token") != self._service_wakeup_token:
                return {"status": "error", "error": "invalid_lifecycle_wake"}
            deadline = self._recovery_certificate_deadline
            if deadline is not None and not self._stop.is_set():
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    self._stop.wait(remaining)
            self._expire_recovery_certificate()
            return {"status": "ok"}

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
        if operation == "verify_recovery":
            return self._execute_recovery_verification(request)
        if operation == "complete_recovery_verification":
            return self._finish_recovery_verification(request, cancelled=False)
        if operation == "cancel_recovery_verification":
            return self._finish_recovery_verification(request, cancelled=True)
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


### C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:592-665 — full DesktopLiveWatcher._poll_inflight_updates

```python
    def _poll_inflight_updates(self) -> list[str]:
        completed: list[str] = []
        for job_id, job in list(self._inflight_updates.items()):
            try:
                status = self.client.mutation_status(job_id)
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                recovered = self._recover_client(exc)
                if recovered is None:
                    continue
                try:
                    status = self.client.mutation_status(job_id)
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    continue
            state = status.get("state") if isinstance(status, dict) else None
            if state in {"queued", "running"}:
                continue
            self._inflight_updates.pop(job_id, None)
            if state == "completed":
                response = status.get("response")
                result = response.get("result") if isinstance(response, dict) else None
                result_status = getattr(result, "status", None)
                if isinstance(response, dict) and response.get("status") == "ok" and result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}:
                    def trust_completed_path() -> bool:
                        if job.observed_state is None:
                            self._snapshot.pop(job.path, None)
                        else:
                            self._snapshot[job.path] = job.observed_state
                        return True

                    if self._admit_recovery_action(trust_completed_path) is RECOVERY_DEFERRED:
                        self._enqueue_path(job.path, wake=False)
                    completed.append(job.path)
                    from contextor.core.runtime_trace import trace_event
                    try:
                        relative = Path(job.path).resolve().relative_to(self.root).as_posix()
                    except ValueError:
                        relative = job.path
                    trace_event("LIVE", "WATCH_UPDATE_END", op=job.trace_op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0)
                    if result_status == "SYNTAX_ERROR":
                        line = getattr(result, "line_number", None)
                        column = getattr(result, "column_number", None)
                        position = f" line {line}, column {column}" if line and column else ""
                        self._emit(f"LIVE syntax error: {Path(job.path).name}{position}: {getattr(result, 'error', 'syntax error')}")
                    elif result_status == "RECOVERED":
                        self._emit(f"LIVE syntax recovery: {Path(job.path).name}")
                    else:
                        self._emit(f"LIVE update successful: {Path(job.path).name}")
                    continue
            if isinstance(status, dict) and status.get("error") in {"unknown_mutation_job", "invalid_mutation_job_id"}:
                self._ambiguous_updates.add(job.path)
                self._pending_intents.setdefault(
                    job.path,
                    _PendingMutationIntent(
                        idempotency_key=job.idempotency_key,
                        path=job.path,
                        trace_op=job.trace_op,
                        observed_state=job.observed_state,
                        started_at=job.started_at,
                        observed_sha256=job.observed_sha256,
                    ),
                )
            from contextor.core.runtime_trace import trace_event
            try:
                relative = Path(job.path).resolve().relative_to(self.root).as_posix()
            except ValueError:
                relative = job.path
            trace_event(
                "LIVE", "WATCH_UPDATE_FAIL", op=job.trace_op, repo=str(self.root),
                path=relative, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0,
                err=(status.get("error", "malformed mutation status") if isinstance(status, dict) else "malformed mutation status"),
            )
            self._requeue_paths([job.path])
            self._emit(f"LIVE update failed; deferring watcher update: {Path(job.path).name}")
        return completed

```


### C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:188-295 — full public MCP update handler

```python
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
            with mcp_runtime._engine_cache_transaction(root) as root_key:
                mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
                engine = mcp_runtime.get_or_init_engine(root)
            live_state_persisted = True
        else:
            res = engine.update_file(str(target_file))
            live_state_persisted = (
                _persist_live_engine(root, engine)
                if res.status in {"UPDATED", "DELETED"}
                else True
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
        return json.dumps({"status": "ERROR", "file_path": str(target_file), "error": str(e)}, indent=2)

```


### C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py:111-120 — unavailable response helper

```python
def module_truth_unavailable(state, module_name: str) -> dict | None:
    truth = module_current_truth(state, module_name)
    if truth["available"]:
        return None
    return {
        "status": "stale" if truth.get("state") == "stale" else "unavailable",
        "available": False,
        "module": module_name,
        **{key: value for key, value in truth.items() if key != "available"},
    }
```


### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1507-1874 — full save_snapshot

```python
def save_snapshot(
    state: Any,
    cache_dir: str | Path,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
    revision_floor: int = 0,
    exact_revision: int | None = None,
    file_state_payload: dict[str, Any] | None = None,
    previous_state: Any = None,
) -> LiveStateMetadata:
    """Atomically publish a complete snapshot and monotonically increasing revision."""

    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )
    from contextor.core.reference.shared import (
        validate_reexport_facts_by_module,
    )

    if isinstance(state, RepositoryAnalysisState) and not validate_reexport_facts_by_module(
        getattr(
            state,
            "reexport_facts_by_module",
            None,
        ),
        state.modules,
    ):
        raise ValueError(
            "Cannot persist RepositoryAnalysisState with incomplete "
            "canonical re-export facts."
        )

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
        current = read_metadata(cache_dir)
        normalized_root = (
            str(Path(root_path).expanduser().resolve())
            if root_path
            else ""
        )

        if (
            current
            and repo_id
            and current.repo_id
            and current.repo_id != repo_id
        ):
            raise ValueError(
                "Snapshot repository ID does not match existing metadata."
            )

        if (
            current
            and normalized_root
            and current.root_path
            and Path(current.root_path).expanduser().resolve()
            != Path(normalized_root)
        ):
            raise ValueError(
                "Snapshot repository root does not match existing metadata."
            )

        if exact_revision is not None:
            if (
                isinstance(exact_revision, bool)
                or not isinstance(exact_revision, int)
                or exact_revision < 0
            ):
                raise ValueError(
                    "exact_revision must be a non-negative integer."
                )

            current_revision = (
                current.revision
                if current is not None
                else None
            )

            if (
                current_revision is None
                and exact_revision != 1
            ):
                raise SnapshotRevisionConflict(
                    None,
                    exact_revision,
                )

            if (
                current_revision is not None
                and exact_revision
                != current_revision + 1
            ):
                raise SnapshotRevisionConflict(
                    current_revision,
                    exact_revision,
                )

            next_revision = exact_revision

            generation_state = (
                state_file.parent
                / (
                    f"engine_state.r{exact_revision}."
                    f"{token}.pkl"
                )
            )

            generation_file_state = (
                state_file.parent
                / (
                    f"file_state.r{exact_revision}."
                    f"{token}.json"
                )
            )

            if _supports_split_lineage_generation(
                state
            ):
                generation_lineage_manifest = (
                    state_file.parent
                    / (
                        f"lineage_manifest.r{exact_revision}."
                        f"{token}.json"
                    )
                )

                reusable_lineage_sources = (
                    _reusable_lineage_manifest_sources(
                        cache_dir,
                        current,
                        previous_state,
                    )
                )

        else:
            next_revision = (
                max(
                    current.revision
                    if current
                    else 0,
                    revision_floor,
                )
                + 1
            )

        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=next_revision,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
            state_file=(
                generation_state.name
                if exact_revision is not None
                else ""
            ),
            file_state_file=(
                generation_file_state.name
                if generation_file_state is not None
                else ""
            ),
            lineage_manifest_file=(
                generation_lineage_manifest.name
                if generation_lineage_manifest is not None
                else ""
            ),
        )

        if (
            exact_revision is not None
            and isinstance(
                state,
                dict,
            )
        ):
            state["revision"] = metadata.revision
            state["state_id"] = metadata.state_id

        elif (
            state is not None
            and hasattr(
                state,
                "__dict__",
            )
        ):
            try:
                setattr(
                    state,
                    "state_id",
                    metadata.state_id,
                )
                setattr(
                    state,
                    "revision",
                    metadata.revision,
                )
            except AttributeError:
                pass

        state_to_persist = state

        if (
            generation_lineage_manifest
            is not None
        ):
            (
                state_to_persist,
                generation_lineage_chunks,
            ) = _write_split_lineage_generation(
                state,
                generation_lineage_manifest,
                state_id=metadata.state_id,
                revision=metadata.revision,
                token=token,
                previous_state=previous_state,
                reusable_sources=reusable_lineage_sources,
            )

        with generation_state.open(
            "wb"
        ) as stream:
            pickle.dump(
                {
                    "metadata": asdict(
                        metadata
                    ),
                    "state": state_to_persist,
                },
                stream,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if generation_file_state is not None:
            if (
                not isinstance(
                    file_state_payload,
                    dict,
                )
                or not isinstance(
                    file_state_payload.get(
                        "_meta"
                    ),
                    dict,
                )
            ):
                raise ValueError(
                    "file_state_payload must contain a _meta mapping."
                )

            payload_meta = file_state_payload[
                "_meta"
            ]

            if (
                payload_meta.get(
                    "state_id",
                    "",
                )
                != state_id
            ):
                raise ValueError(
                    "FileState payload state_id does not match snapshot state_id."
                )

            if (
                payload_meta.get(
                    "revision"
                )
                != exact_revision
            ):
                raise ValueError(
                    "FileState payload revision does not match exact_revision."
                )

            with generation_file_state.open(
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    file_state_payload,
                    stream,
                    indent=2,
                )
                stream.flush()
                os.fsync(
                    stream.fileno()
                )

        with meta_tmp.open(
            "w",
            encoding="utf-8",
        ) as stream:
            json.dump(
                asdict(
                    metadata
                ),
                stream,
                indent=2,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if exact_revision is None:
            os.replace(
                generation_state,
                state_file,
            )

        os.replace(
            meta_tmp,
            meta_file,
        )

        committed = True

        return metadata

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

        _release_lock(lock_fd)

```


### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1926-2371 — full load_snapshot

```python
def load_snapshot(
    cache_dir: str | Path,
    expected_state_id: str = "",
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)

    phase_started = time.monotonic()
    metadata = read_metadata(cache_dir)
    _trace_snapshot_load_phase(
        "metadata_read",
        phase_started,
        repo_id=expected_repo_id,
    )
    normalized_root = (
        str(Path(expected_root_path).expanduser().resolve())
        if expected_root_path
        else ""
    )
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    if expected_repo_id and metadata.repo_id != expected_repo_id:
        return None
    if normalized_root and (
        not metadata.root_path
        or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
    ):
        return None
    if metadata.state_file:
        state_file = state_file.parent / metadata.state_file
    try:
        phase_started = time.monotonic()
        with state_file.open("rb") as stream:
            payload = _SnapshotUnpickler(stream).load()
        _trace_snapshot_load_phase(
            "core_pickle_unpickle",
            phase_started,
            repo_id=expected_repo_id,
        )

        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            if not isinstance(embedded, dict):
                return None

            if metadata.schema_version == LIVE_STATE_SCHEMA_VERSION:
                expected_embedded = asdict(metadata)
                if set(embedded) != set(expected_embedded):
                    return None
                if any(
                    type(embedded[key]) is not type(expected_value)
                    or embedded[key] != expected_value
                    for key, expected_value in expected_embedded.items()
                ):
                    return None

            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
                state_file=str(embedded.get("state_file", "")),
                file_state_file=str(embedded.get("file_state_file", "")),
                lineage_manifest_file=str(
                    embedded.get(
                        "lineage_manifest_file",
                        "",
                    )
                ),
            )
            if embedded_metadata.revision != metadata.revision:
                return None
            if (
                embedded_metadata.lineage_manifest_file
                != metadata.lineage_manifest_file
            ):
                return None

            raw_state = payload[
                "state"
            ]

            lineage_validation_trusted_source_keys: set[str] = set()
            lineage_validation_cache_matches_current_chunks = False
            lineage_validation_chunks = None

            if metadata.lineage_manifest_file:
                if (
                    metadata.schema_version
                    != LIVE_STATE_SCHEMA_VERSION
                ):
                    return None

                if (
                    raw_state is None
                    or isinstance(
                        raw_state,
                        dict,
                    )
                    or not hasattr(
                        raw_state,
                        "__dict__",
                    )
                ):
                    return None

                phase_started = time.monotonic()
                (
                    split_lineage,
                    lineage_validation_trusted_source_keys,
                    lineage_validation_chunks,
                    lineage_validation_cache_matches_current_chunks,
                ) = _load_split_lineage_generation(
                    cache_dir,
                    metadata,
                )

                raw_modules = getattr(raw_state, "modules", None)
                if not isinstance(raw_modules, dict):
                    return None

                try:
                    expected_source_keys = {
                        Path(str(module.path)).as_posix()
                        for module in raw_modules.values()
                    }
                except (AttributeError, TypeError, ValueError):
                    return None

                actual_source_keys = set(split_lineage)

                if not actual_source_keys.issubset(expected_source_keys):
                    return None

                if (
                    getattr(raw_state, "lineage_facts_state", None)
                    == LineageFamilyStatus.FRESH.value
                    and actual_source_keys != expected_source_keys
                ):
                    return None

                _trace_snapshot_load_phase(
                    "split_lineage_load",
                    phase_started,
                    repo_id=expected_repo_id,
                    count=len(split_lineage),
                )

                try:
                    setattr(
                        raw_state,
                        "lineage_facts_by_source",
                        split_lineage,
                    )
                except AttributeError:
                    return None

            phase_started = time.monotonic()
            state_obj = _normalize_symbol_call_facts(
                raw_state
            )
            _trace_snapshot_load_phase(
                "normalize_symbol_call_facts",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_obj = _normalize_lineage_facts_state(
                state_obj,
                trusted_source_keys=(
                    lineage_validation_trusted_source_keys
                ),
            )
            _trace_snapshot_load_phase(
                "normalize_lineage_facts_state",
                phase_started,
                repo_id=expected_repo_id,
                count=len(
                    getattr(
                        state_obj,
                        "lineage_facts_by_source",
                        {},
                    )
                    or {}
                ),
            )

            phase_started = time.monotonic()
            state_obj = (
                _normalize_lineage_query_index_state(
                    state_obj
                )
            )
            _trace_snapshot_load_phase(
                "normalize_lineage_query_index_state",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_obj = _normalize_reexport_facts_state(
                state_obj
            )
            _trace_snapshot_load_phase(
                "normalize_reexport_facts_state",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_revision = (
                state_obj.get("revision") if isinstance(state_obj, dict)
                else getattr(state_obj, "revision", None)
            )
            state_id_value = (
                state_obj.get("state_id") if isinstance(state_obj, dict)
                else getattr(state_obj, "state_id", None)
            )
            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
                return None
            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
                return None
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                try:
                    setattr(state_obj, "state_id", embedded_metadata.state_id)
                    setattr(state_obj, "revision", embedded_metadata.revision)
                    setattr(state_obj, "provenance", "snapshot")
                except AttributeError:
                    pass
                if not hasattr(state_obj, "module_usages"):
                    try:
                        setattr(state_obj, "module_usages", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_by_path"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_by_path", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_state"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_state", "not_materialized")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "module_usages_manifest"):
                    try:
                        setattr(state_obj, "module_usages_manifest", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_analytics"):
                    try:
                        setattr(state_obj, "topology_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_metrics_state"):
                    try:
                        setattr(state_obj, "topology_metrics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics"):
                    try:
                        setattr(state_obj, "cached_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics_state"):
                    try:
                        setattr(state_obj, "cached_analytics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles"):
                    try:
                        setattr(state_obj, "cycles", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles_state"):
                    try:
                        setattr(state_obj, "cycles_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collision_facts"):
                    try:
                        setattr(state_obj, "collision_facts", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions"):
                    try:
                        setattr(state_obj, "collisions", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions_state"):
                    try:
                        setattr(state_obj, "collisions_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix"):
                    try:
                        setattr(state_obj, "dependency_matrix", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix_state"):
                    try:
                        setattr(state_obj, "dependency_matrix_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters"):
                    try:
                        setattr(state_obj, "shared_usage_clusters", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters_state"):
                    try:
                        setattr(state_obj, "shared_usage_clusters_state", "deferred")
                    except AttributeError:
                        pass

            if (
                metadata.lineage_manifest_file
                and not lineage_validation_cache_matches_current_chunks
                and lineage_validation_chunks
                is not None
            ):
                _write_lineage_validation_cache(
                    cache_dir,
                    metadata=metadata,
                    chunks=(
                        lineage_validation_chunks
                    ),
                )

            _trace_snapshot_load_phase(
                "post_normalization_finalize",
                phase_started,
                repo_id=expected_repo_id,
            )
            return state_obj, metadata
        if metadata.lineage_manifest_file:
            return None

        payload = _normalize_lineage_query_index_state(
            _normalize_lineage_facts_state(
                _normalize_symbol_call_facts(payload)
            )
        )
        payload = _normalize_reexport_facts_state(
            payload
        )
        if payload is not None and hasattr(payload, "__dict__"):
            if not hasattr(payload, "module_usages"):
                try:
                    setattr(payload, "module_usages", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_by_path"):
                try:
                    setattr(payload, "syntax_diagnostics_by_path", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_state"):
                try:
                    setattr(payload, "syntax_diagnostics_state", "not_materialized")
                except AttributeError:
                    pass
            if not hasattr(payload, "module_usages_manifest"):
                try:
                    setattr(payload, "module_usages_manifest", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_analytics"):
                try:
                    setattr(payload, "topology_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_metrics_state"):
                try:
                    setattr(payload, "topology_metrics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics"):
                try:
                    setattr(payload, "cached_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics_state"):
                try:
                    setattr(payload, "cached_analytics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles"):
                try:
                    setattr(payload, "cycles", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles_state"):
                try:
                    setattr(payload, "cycles_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "collision_facts"):
                try:
                    setattr(payload, "collision_facts", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions"):
                try:
                    setattr(payload, "collisions", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions_state"):
                try:
                    setattr(payload, "collisions_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix"):
                try:
                    setattr(payload, "dependency_matrix", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix_state"):
                try:
                    setattr(payload, "dependency_matrix_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters"):
                try:
                    setattr(payload, "shared_usage_clusters", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters_state"):
                try:
                    setattr(payload, "shared_usage_clusters_state", "deferred")
                except AttributeError:
                    pass
        return payload, metadata




    except (OSError, pickle.PickleError, EOFError):
        return None
```



## UNRESOLVED_UNCERTAINTIES

- Nie wykonano update, aby wprowadzić malformed state; bieżące LIVE events nie dowodzą, że taki marker jest w active canonical object. Wnioski false-fresh są warunkowe na wejściu malformed metadata do wskazanych branchy.
- Nie odczytano raw module_parse_freshness z aktywnego state; sprawdzono kod/source i family-level LIVE freshness.
- Akceptacja truthy pair-iterable invalid types nie była wykonywana (brak testów/probes zgodnie z restrykcją). Semantyka konstruktora i kolejność callów dowodzą tylko conditional code path.
- Dla usuniętych modułów module_current_truth sam raportuje brak metadata jako current, ale publiczny query resolver może najpierw odrzucić brak modułu/artefaktu; ścieżki nie uruchamiano.
- Wskazani publiczni konsumenci zostali zlokalizowani, nie wszystkie odpowiedzi end-to-end sprawdzone dla konkretnego targetu. Ich własne bramki mogą dodatkowo sprawdzać global resync/canonical family state.
- W normal source-success branch raw truthy non-dict jest odczytywany przez .get przed COW. Typowy list pair nie ma .get i kończy się błędem; custom mapping-like object może je mieć. Runtime reachability unknown.
- RepositoryAnalysisState ma domyślny dict, ale unpickled legacy instances mogą nie mieć field w __dict__; load_snapshot nie odnosi się do tej nazwy pola, a helper definiuje missing attribute jako fresh. Nie sprawdzano, czy taki legacy snapshot istnieje w aktywnym cache.
- Nie wykonano Git/HEAD/status/diff command, ponieważ polecono zignorować Git i HEAD; nie ma twierdzenia o innych pre-existing worktree changes.
- Nie uruchomiono testów, analysis jobs, service restartów, Desktop actions ani update_file.

## FILES_CHANGED

- Jedyny zapis w tym tasku: C:\Temp\Contextor_Repo\walkthrough.md.
- Żadne production source ani testy nie zostały zmienione.

## ACTUAL_DIFF

DIFFS=NONE dla source/test files. Nie wykonano git diff zgodnie z instrukcją. walkthrough.md jest jedynym żądanym zapisem.

## READY_FOR_LITERAL_PATCH

Discovery evidence jest gotowe dla audytora do zaprojektowania literalnego patcha. Główna potwierdzona ścieżka false-fresh to collapse falsey malformed whole-map w _prepare_candidate_state, publikowane z syntax failure, parsed semantic no-op, ordinary update i delete candidates; missing entries spełniają legacy fresh contract. Truthy coercible mapy i bieżące runtime occurrence pozostają conditional/unknown. Nie zaprojektowano ani nie zastosowano patcha.
