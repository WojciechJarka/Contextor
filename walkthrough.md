# F2L-READY certification gate

STATUS=BLOCKED
READY=NO
INTERFACE_DESCRIPTOR_CLASSIFICATION=B

## GATE_1_RESULT

FAIL — brak bezpośredniego testu porównującego końcowy full state z końcowym incremental/COW state dla wszystkich wymaganych pól. Istniejące invariants dowodzą zgodności pojedynczego materialization call, ale ujawniają lifecycle gap przy zmianie active identities.

`_materialize_full_analysis_lineage` (`contextor/core/api/facade.py:264-378`) materializuje każdy extracted source wobec finalnego registry i sprawdza source_key/fingerprint. `_update_candidate_lineage_slice` (`contextor/core/analysis/incremental/engine.py:166-283`) używa tego samego czystego materializatora, ale `_apply_delta_and_commit` (`engine.py:590-679`) wywołuje go tylko dla `syntax_source_path` albo usuwanego source. Przy `identity_sync_required` registry jest synchronizowane, lecz pozostałe source slices nie są ponownie materializowane.

Wniosek: dla zwykłej zmiany jednego slice istnieje silny proof deterministyczności, COW i manifestów; dla końcowego stanu po dodaniu/usunięciu ownera nie ma parity. Przykład kontraktowy: usunięcie providera usuwa jego slice, ale pozostawiony consumer może zachować `SemanticEndpoint` do nieaktywnego artifact ownera. Full analysis tego consumera zdegradowałby ref do `MaterializedSymbolicRef`, incremental nie.

## GATE_2_RESULT

PASS_WITH_D1_GAP — canonical facts wystarczają do wyprowadzenia freshness/provenance bez source scan, AST parse i re-extraction:

- `RepositoryAnalysisState` ma `lineage_facts_by_source`, `lineage_facts_state` i `lineage_facts_semantic_version` (`contextor/core/analysis/state_manager.py:82-123`).
- `SourceLineageManifest` ma `source_key`, `source_fingerprint`, semantic version, status i anchor/flow/surface counts (`contextor/core/domain/lineage_facts.py:365-382`).
- incremental invalidation, resync i statusy `not_materialized|fresh|stale|deferred|resource_limit` są obsługiwane przez engine (`engine.py:115-164`, `166-283`).
- snapshot hydration normalizuje i waliduje mapping, manifesty, endpointy, flows, surfaces i descriptors bez odbudowy ze źródeł (`contextor/core/live_state/store.py:116-309`, `496-743`).

Lineage jest first-class family w canonical state, ale nie jest jeszcze first-class family we wspólnym envelope `build_state_freshness`: `contextor/mcp/query_helpers.py:264-444` publikuje `module/graph/topology/artifact_consumption/cycles/collisions`, bez `lineage_facts_state`, semantic version ani per-source manifest status/fingerprint/counts. To jest oczekiwany D1 query-layer gap, nie samodzielny blocker canonical implementation. Blockerem pozostaje opisana w GATE_1 niespójność active-owner lifecycle.

## GATE_3_RESULT

FAIL — domain traversal contract jest poprawny, ale incremental lifecycle może zachować semantic endpoint po utracie active ownera, więc fail-closed identity guarantee nie jest utrzymane end-to-end.

## GATE_4_RESULT

PASS, klasyfikacja B. Producer emituje rzeczywiste relacje `ARGUMENT_TO_PARAMETER`, `RETURNS` i `CALL_RESULT`:

- `lineage_extraction_calls.py:58` emituje `ARGUMENT_TO_PARAMETER` z parameter symbolic ref.
- `lineage_extraction_visitors.py:218-269` emituje `RETURNS` do return symbolic ref.
- `lineage_extraction_visitors.py:340-420` emituje `CALL_RESULT` dla exact/imported oraz dynamic/unresolved boundary.

Materializer potrafi zamienić exact parameter/return/state ref w `SemanticEndpoint`, ale tylko gdy istnieje active owner oraz pasujący `SemanticInterfaceDescriptor`/slot (`lineage_materialization.py:157-212`). Pełna facade i incremental engine przekazują obecnie `interface_descriptors={}` (`facade.py:316-323`, `engine.py:229-236`). W realnym canonical path:

- exact `DEFINITION`/`PUBLIC_TARGET` bez slotu może stać się `SemanticEndpoint`, jeśli exact active artifact owner istnieje;
- `PARAMETER`, `RETURN` i `STATE` wymagają slotu obecnego w descriptorze i przy pustym descriptor map pozostają `MaterializedSymbolicRef`;
- `ARGUMENT_TO_PARAMETER` oraz return-side `CALL_RESULT` są więc reprezentowane fail-closed, bez wiarygodnego cross-source slot traversal;
- testy materializatora potwierdzają poprawną konwersję przy dostarczonym descriptorze (`tests/analysis/test_lineage_materialization.py:72-102`, `165-196`).

Brak descriptor coverage ogranicza część traversal, ale nie wzmacnia ścieżki: publiczny query layer może jawnie zakończyć traversal na symbolic boundary. Nie jest to klasyfikacja C.

## CANONICAL_TRAVERSAL_RULES

1. `MaterializedOccurrenceRef` jest source-slice-local; jego `source_key` i `source_fingerprint` muszą odpowiadać manifestowi. Anchor wymaga rzeczywistego occurrence.
2. `MaterializedSymbolicRef` jest slice-bound symbolic boundary, nie occurrence i nie owner. `module_name/symbol_name` nie są samodzielną cross-source identity.
3. `SemanticEndpoint(owner_id, slot)` jest jedynym canonical semantic owner/slot i może być cross-source join point. Slot musi należeć do ownera.
4. Dalsze rozstrzygnięcie symbolic ref wymaga istniejącego exact proof: confirmed confidence, dozwolony `ResolutionKind`, exact active module/artifact mapping oraz — dla parameter/return/state — obecny slot w descriptorze. Brak któregokolwiek warunku kończy ścieżkę symbolic.
5. Flow edges są wyłącznie `MaterializedFlowFact`; surface, anchor i span nie są flow edges. Domain odrzuca cross-source occurrence-to-occurrence flow (`lineage_facts.py:313-334`, `640-717`).
6. Dynamic, unresolved, deferred, resource-limit, resync i nieaktywne identity nie mogą być publikowane jako confirmed semantic path. Obecny wyjątek lifecycle opisany w BLOCKERS narusza tę zasadę przez zachowanie starego endpointu w niezmienionym slice.

## FAIL_CLOSED_PROOF

- Missing active module/artifact owner: facade i incremental engine failują przed materialization, zamiast alokować identity (`facade.py:296-316`, `engine.py:207-228`); test: `tests/test_lineage_state_lifecycle.py:639-678`.
- Source-key mismatch i manifest mismatch: incremental wymaga `extracted.source_key == source_path` oraz zgodności manifest key/fingerprint przed publikacją; test: `tests/test_lineage_state_lifecycle.py:639-678`.
- Fingerprint mismatch/out-of-sync: manifest carries fingerprint; `build_state_freshness` rozróżnia `verified`, `metadata_match`, `out_of_sync`, `unverified` i emituje advisory warning zamiast potwierdzać zgodność (`query_helpers.py:264-444`).
- Unsupported semantic version, invalid family-state/version pair, corrupted endpoint/flow: snapshot normalization i revalidation odrzucają payload (`store.py:116-309`); testy: `tests/test_lineage_state_lifecycle.py:154-294`.
- Parse failure: preparation zwraca error bez extracted lineage; commit usuwa slice i zachowuje `not_materialized`/`None` dla niezmateriałowanego state albo ustawia `stale`/current version dla state materialized (`tests/test_lineage_state_lifecycle.py:543-602`).
- Deferred/resource limit/resync: full path publikuje `deferred`/`resource_limit`, incremental publikuje `stale` przy `resync_required`; testy: `tests/test_full_analysis_lineage_materialization.py:121-144`, `tests/test_lineage_state_lifecycle.py:605-638`.
- Unresolved/dynamic/ambiguous slot: `claims_exact_semantic_target` wymaga confirmed exact evidence; materializer zachowuje symbolic boundary i dynamic metadata (`lineage_facts.py:640-717`, `lineage_materialization.py:157-184`); test: `tests/analysis/test_lineage_materialization.py:105-135`, `224-257`.
- Lifecycle exception: `_revalidate_lineage_endpoint` przyjmuje istniejący `SemanticEndpoint`, ale nie sprawdza jego active registry ownera (`store.py:116-125`). Po identity deletion nie ma re-materialization niezmienionych consumer slices, więc stare endpointy mogą przejść hydration jako pozornie fresh.

## BLOCKERS

Jeden konkretny blocker canonical lifecycle: po active artifact/module deletion lub owner introduction incremental ścieżka synchronizuje registry, lecz materializuje tylko changed/deleted source slice. Unchanged cross-source consumers nie są rewalidowane ani re-materializowane, a family może pozostać `fresh`. Owner: `IncrementalAnalysisEngine._apply_delta_and_commit` i `_update_candidate_lineage_slice` (`contextor/core/analysis/incremental/engine.py:166-283`, `590-679`), przy registry trigger w `contextor/core/analysis/incremental/plan_executor.py:430-505`, `690-707`. Brakujący test: end-state full-vs-incremental parity z untouched consumerem i usuniętym/dodanym exact ownerem; istniejący `test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure` (`tests/test_lineage_state_lifecycle.py:681-768`) sprawdza wyłącznie zmieniony `pkg.py`.

To jest semantic strengthening/stale-owner risk i blokuje READY. Nie rozszerzam naprawy w tym kroku.

## NON_BLOCKING_D1_GAPS

Brak public lineage root, `LineageQueryService`, MCP docs, named/indexed representation, output budgeting i generic large-result store należy do F2L D1+, zgodnie z separation rule. Brak lineage w `build_state_freshness.families` jest D1 freshness-envelope gap, ponieważ canonical state ma już wystarczające facts.

## EVIDENCE_FILES_AND_SYMBOLS

- `contextor/core/domain/lineage_facts.py`: `MaterializedOccurrenceRef`, `MaterializedSymbolicRef`, `SemanticEndpoint`, `MaterializedFlowFact`, `SourceLineageManifest`, `MaterializedLineageSourceFacts`, `claims_exact_semantic_target`.
- `contextor/core/analysis/lineage_materialization.py`: `LineageResolutionContext`, `_symbolic_endpoint`, `_slot_for`, `materialize_lineage_source_facts`.
- `contextor/core/analysis/lineage_extraction.py`, `lineage_extraction_calls.py`, `lineage_extraction_visitors.py`: extraction boundary and emitted relations.
- `contextor/core/api/facade.py`: `_materialize_full_analysis_lineage`.
- `contextor/core/analysis/incremental/engine.py`: `_commit_syntax_candidate`, `_update_candidate_lineage_slice`, `_apply_delta_and_commit`.
- `contextor/core/analysis/incremental/plan_executor.py`: `_prepare_candidate_state`, identity registry execution and outcome.
- `contextor/core/analysis/state_manager.py`: `RepositoryAnalysisState`.
- `contextor/core/live_state/store.py`: lineage normalization, endpoint/flow/slice revalidation, `load_snapshot`.
- `contextor/mcp/query_helpers.py`: `build_state_freshness`.
- `tests/test_full_analysis_lineage_materialization.py`, `tests/test_lineage_state_lifecycle.py`, `tests/analysis/test_lineage_materialization.py`, `tests/domain/test_lineage_facts.py`, `tests/analysis/test_lineage_extraction.py`.

## TEST_EVIDENCE

PRECONDITION_ACCEPTED=full pytest after earlier 8 failures was green; full suite was not rerun.

Existing tests inspected read-only:

- full deterministic materialization, manifest/fingerprint, coverage statuses, real facade path and endpoint/symbolic behavior (`tests/test_full_analysis_lineage_materialization.py:100-264`);
- COW copy, snapshot/hydration normalization, parse invalidation, incremental replace/delete/resource-limit/key/manifest checks (`tests/test_lineage_state_lifecycle.py:129-294`, `295-430`, `485-768`);
- domain cross-source occurrence prohibition and semantic endpoint slot flow (`tests/domain/test_lineage_facts.py:45-125`);
- exact descriptor-supported parameter/return/state materialization and symbolic fallback (`tests/analysis/test_lineage_materialization.py:50-257`);
- extraction of parameter, return and call-result relations plus resource-limit fail-closed (`tests/analysis/test_lineage_extraction.py:1117-1262`).

TESTS_RUN_BY_AGENT=NONE. No production or test files were edited; only the allowed `walkthrough.md` report artifact was written. No focused test was needed to establish the static blocker.

## CONTEXTOR_TOOL_USAGE

Contextor MCP był aktywny od początku; nie było potrzeby deferred-tool discovery ani lazy loading. Użyto: `get_mcp_documentation`, `get_analysis_status`, `get_artifacts_for_module`, `lookup_artifact_by_symbol`, `get_symbol_implementation`, `get_source_range` i `search_source`. Architectural discovery wykonano Contextor-first; lokalne `rg`/git służyły wyłącznie do wąskiej tekstowej i historycznej weryfikacji po discovery, nie jako zamiennik discovery.

## RECOMMENDED_NEXT_STAGE

RECOMMENDED_NEXT_STAGE=separate canonical lineage lifecycle repair for active-owner changes and an explicit full-vs-incremental end-state parity proof; dopiero po tym ponowić F2L-READY i rozpocząć F2L D1.

FILES_CHANGED=NONE
DIFFS=NONE

## GIT_VERIFICATION

`git status` przed raportem wykazał istniejące, niepowiązane zmiany w sześciu production/test files oraz wcześniejszy `walkthrough.md`; nie zostały dotknięte. Po zapisie ponowne `git status`, `git diff --name-only` i `git diff --check` potwierdziły te same sześć istniejących plików oraz wyłącznie `walkthrough.md` jako artefakt tego gate; diff check zakończył się bez błędu poza standardowymi ostrzeżeniami LF/CRLF.

Końcowe potwierdzenie: architectural discovery wykonano Contextor-first, z dokumentacją i canonical symbol/source projections; deferred discovery nie była potrzebna; grep/search służyły wyłącznie tekstowej weryfikacji.
