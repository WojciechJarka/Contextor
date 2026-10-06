STATUS=DISCOVERY_COMPLETE
HEAD=e3a3e99e2139f2b66fe2f6d3631cd57148dffdd5
WORKTREE_STATE=CLEAN_BEFORE_REPORT; no source/test/docs edits; walkthrough.md is the only report output and is excluded from FILES_CHANGED.

# CPA_FILE_UPDATE_REEXPORT_SOURCE_SCAN_DISCOVERY

## Zakres i evidence labels

Discovery-only; nie uruchomiono pytest, `analyze_project`, profilowania ani runtime update. Nie użyto MCP `update_file`; nie wykonano restartu.

- **DIRECT_EVIDENCE**: aktualny literal source z Contextor `get_source_range` / `get_symbol_implementation` oraz literalne `rg` anchor check; HEAD i status z Git.
- **CODE_PATH_PROVED**: połączenie bezpośrednich callerów i implementacji opisanych niżej.
- **INFERENCE**: zachowanie zależne od cyklu życia obiektów/cache, którego nie obserwowano w runtime.
- **UNKNOWN**: brak istniejących liczników do potwierdzenia faktycznej liczby operacji dla pojedynczego update.

## CURRENT_REEXPORT_BUILD_CALL_SITES

Literalne `rg -n "_build_reexport_map\\("` w `contextor/core` znalazło trzy bezpośrednie wywołania:

| Absolute file | Symbol / line | Kiedy i jaki `modules` | AST / I/O |
|---|---|---|---|
| `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:774` | `_apply_delta_and_commit` recompute branch | Gdy `plan.recompute_modules` jest niepuste; przekazuje `candidate.modules`. | Cache miss w `shared.py` iteruje wszystkie `modules.items()` i odczytuje `module.ast_tree` każdego modułu. |
| `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:880` | `_apply_delta_and_commit` `artifact_consumption` patch branch | Gdy `artifact_consumption` jest w `plan.patch_families`; przekazuje to samo `candidate.modules`. | Taka sama ścieżka cache/AST. Jeżeli call-site z linii 774 wykonał się w tym samym update, drugi call ma identyczne dict identity i length, nie ma resetu pomiędzy nimi i trafia w `_REEXPORT_CACHE`. |
| `C:\Temp\Contextor_Repo\contextor\core\reference\engine.py:218` | `_legacy_build_symbol_references` | Legacy helper przyjmuje argument `modules` i bezpośrednio buduje reexport mapę. Jego docstring określa go jako zachowany test/reference helper; literalne wyszukanie nie znalazło call-site tego helpera. Normalna ścieżka `build_symbol_references` zwraca przez `RepositoryReferenceIndex`. | Jeśli helper zostanie wywołany i helper cache miss, działa ta sama iteracja AST. Nie jest to zwykła full-analysis compact-facts ścieżka. |

Evidence: `plan_executor.py:750-795, 870-895`; `engine.py:190-218`; `shared.py:20-105`. Literal direct-call inventory: tylko powyższe trzy w `contextor/core`.

### CURRENT_REEXPORT_CACHE_CONTRACT

**DIRECT_EVIDENCE**

- `contextor/core/reference/shared.py:20-25, 50-56, 135-140`: module-global `_REEXPORT_CACHE`; key to `(id(modules), len(modules))`; hit zwraca mapę; wynik jest przechowywany pod tym kluczem; reset czyści słownik.
- `contextor/core/analysis/incremental/plan_executor.py:600-635`: każde przygotowanie candidate state wykonuje `modules=dict(state.modules)`.
- `CandidateState` i jego fields: `plan_executor.py:38-70`. Candidate dict jest shallow copy state dict, a candidate staje się modułowym stanem po commit.

**CODE_PATH_PROVED / INFERENCE**

1. Candidate dostaje nowy dict na każdy update. Podczas jego utworzenia poprzedni canonical dict nadal istnieje, więc identity różni się od bezpośrednio poprzedniego canonical dict.
2. Cache identity nie jest stabilne pomiędzy sąsiednimi update'ami. Cache przechowuje tylko liczbowe `id` i `len`, nie referencję do dict ani jego zawartość.
3. **POSSIBLE, NOT OBSERVED**: po zwolnieniu starszego dict Python może ponownie użyć jego `id`; jeśli length się zgadza, późniejszy update może trafić do starego wpisu. Nie ma pomiaru, który potwierdza wystąpienie takiego reuse w tej sesji.
4. **POSSIBLE BY KEY CONTRACT**: zmiana zawartości tego samego dict identity przy niezmienionej długości nie unieważnia cache key, więc hit może zwrócić mapę z poprzedniej treści. To opis luki klucza na podstawie source, nie zaobserwowany runtime przypadek.
5. `reset_reexport_cache()` jest wołany przez `reset_caches()` (`reference/engine.py:43-51`). Reset występuje na wejściach full analysis / analysis layer / single-file facade: `api/facade.py:659,1292,1482`. Brak resetu w single-file incremental update path.

## MODULE_AST_TREE_IO_CONTRACT

**DIRECT_EVIDENCE**

- `contextor/core/reference/shared.py:50-70`: przy cache miss `_build_reexport_map` odwiedza każdy moduł i wykonuje `getattr(module, "ast_tree", None)`.
- `contextor/core/domain/module.py:16-42,55-60`: `Module.ast_tree` wywołuje `_get_cached_ast`; getter robi `Path(absolute_path).stat()` przed odczytem `_parse`; `_parse` jest process-local `lru_cache(maxsize=1024)`, którego miss wywołuje `parse_source(absolute_path)`.
- `contextor/core/source.py:45-123`: parser czyta/dekoduje source i wykonuje `ast.parse`.

| Operation | Current behavior |
|---|---|
| `RAM_ONLY` | Hit w `_REEXPORT_CACHE`: zwraca mapę bez wejścia w pętlę modułów. Compact assembler po otrzymaniu wszystkich facts wykonuje assembly w RAM. |
| `FILESYSTEM_STAT` | Reexport-map cache miss: jedna `Module.ast_tree` access na moduł; każda access wykonuje `Path.stat()`, także gdy AST jest ciepły w LRU. |
| `SOURCE_READ` | Nie wynika z samego stat. Następuje, gdy `_parse` dla ścieżki/fingerprint jest LRU miss. |
| `SOURCE_PARSE` | Następuje razem z powyższym LRU miss w `parse_source`; nie przy trafieniu AST LRU. |
| Cold/warm | Cold/evicted LRU może czytać i parsować wiele modułów po jednym helper cache miss. Warm LRU nadal statuje ścieżki wszystkich modułów, ale może ominąć read/parse. |
| Process locality | `_parse` LRU i `_REEXPORT_CACHE` są pamięcią procesu; nie są trwałym cache per-repository. |

Nie zakładam, że `lru_cache(_parse)` usuwa project-wide stat touches: literal source pokazuje stat przed każdym lookupiem LRU.

## FULL_ANALYSIS_COMPACT_REEXPORT_PATH

**CODE_PATH_PROVED**

`index_repository` → `RepositoryIndex.reference_facts_by_module` → `assemble_reference_index_or_fallback` → `RepositoryReferenceIndex.from_compact_facts` → `_assemble_reexport_map`.

Evidence:

- `contextor/core/symbol_engine/indexer.py:938-961`: `RepositoryIndex` zawiera `reference_facts_by_module`.
- `indexer.py:430-505`: worker robi `read_source_snapshot(path)` przed lookupem per-file cache i przekazuje dokładne source bytes do cache walidacji.
- `indexer.py:514-560`: poprawny cached reference envelope może zakończyć worker bez parse.
- `indexer.py:620-690,800-815`: przy brakujących facts worker parsuje snapshot i wywołuje `extract_compact_reference_facts(module_id, tree=tree, imports=imports)`.
- `indexer.py:1735-1757` (oraz równoległa ścieżka pool w `1883-1994`): current-run facts trafiają do `reference_facts_by_module` i zwracanego `RepositoryIndex`.
- `contextor/core/api/facade.py:675-705`: full analysis przekazuje current-run facts do `assemble_reference_index_or_fallback`.
- `contextor/core/reference/index.py:761-778`: przy pełnym module coverage i statusach available/unavailable wybiera `from_compact_facts`; fallback buduje index z `Module.ast_tree`.
- `index.py:305-357,360-413`: compact envelope ma `facts.reexports = {exporter, explicit_all, bindings, star_sources}`; wartości są plain Python dict/list/string/None.
- `index.py:415-466,515-550`: `_assemble_reexport_map` stosuje visibility, star-import fixpoint i cycle-safe alias resolution; `from_compact_facts` woła assembler.
- `contextor/core/analysis/cache_manager.py:120-193`; `indexer.py:731-746,850-870`: per-file cache jest JSON/orjson payloadem związanym z source hash/path; `reference_facts` są zapisywane przy full-index cache write. Cache hit wciąż wymaga świeżego `read_source_snapshot` w indexerze, choć nie musi parsować.

**Czy full analysis umie zbudować mapę wyłącznie z compact facts? YES**, gdy obecne facts obejmują moduły i mają dostępne statusy. Sam assembly po uzyskaniu facts jest RAM-only; full-analysis indexing przedtem odczytuje source plików do walidacji cache.

**Czy compact facts są bezwarunkowo lossless względem aktualnego `_build_reexport_map`? NO — direct source divergence dla wielokrotnego top-level `__all__`.**

- `shared.py:29-44`, `_explicit_all`, zwraca wynik od pierwszego top-level Assign do `__all__`.
- `reference/index.py:315-328`, `_extract_reexport_facts`, kontynuuje pętlę i nadpisuje `explicit_all` przy kolejnych Assign, więc zostawia ostatnie.
- Przy jednym literalnym top-level `__all__` extractor zachowuje wejścia potrzebne assemblerowi dla obsługiwanych statycznych reguł. Dla dwóch przypisań, także gdy pierwsze jest dynamiczne, wejściowe facts mogą dać inny wynik niż aktualny legacy builder. To source-proven semantic difference, nie runtime test.

## EXISTING_REEXPORT_FACT_SOURCES

Legenda dla semantycznej macierzy: **COMPLETE** = ma dane/mechanizm dla semantyki w kodowym modelu; **PARTIAL** = tylko część potrzebnych danych albo rozbieżność; **INSUFFICIENT** = brak danych do odtworzenia.

| Source | Complete? | Persisted? | Updated on single-file change? | Requires source I/O? | Notes |
|---|---|---|---|---|---|
| `RepositoryAnalysisState` | INSUFFICIENT | State snapshot tak; reexport payload nie | Nie zawiera/nie aktualizuje reexport facts | Nie przy samym odczycie state | `state_manager.py:84-115` ma modules, artifacts, usages, usage manifest i lineage; brak per-module reference/reexport facts field. |
| `ModuleUsageFacts` | PARTIAL | Tak, w canonical state/snapshot | Tak, prepared usage może podmienić facts modułu | Nie do odczytu facts; extraction korzysta z już sparsowanego AST | `usage_facts.py:19-42`; zachowuje import/use/alias facts, ale nie `__all__`, star/transitive map ani cycle resolution. |
| `module_usages_manifest` | INSUFFICIENT | Tak, jako state metadata | Nie w incremental CandidateState/update path | Nie | `module_usage_reuse.py:15-27`: module_id/path/sha256/semantic_version; to walidacja reuse, nie export facts. Candidate fields nie zawierają manifestu (`plan_executor.py:38-70`). |
| `artifacts["symbols"]` / `own_symbols` | PARTIAL | Tak, w `state.artifacts` | Tak, dla zmienionego modułu | Nie do odczytu; extraction używa już sparsowanego AST | Dostarcza inventory definicji, nie deklaracje import/export, aliasy reexportu, `__all__` lub star resolution. |
| `Module.imports` / `ImportRef` | PARTIAL | Tak, część canonical `Module` | Tak, zastępowane przez `new_imports` | Nie do odczytu; ekstrakcja korzysta z drzewa w preparation | `imports.py:11-27`, `AdvancedImportVisitor` (`indexer.py:196-258`): module, relative level, imported names, from-import/local flag. `asname` nie jest osobnym polem i pełny top-level export binding z tego nie wynika. |
| `RepositoryIndex.reference_facts_by_module` | PARTIAL (end-to-end; compact semantics powyżej) | Tylko current-run obiekt; trwała kopia jest per-file cache | Nie przez incremental update | Nie w assemblerze; full index wcześniej czyta source snapshoty | Pełna domena compact envelopes zasila full path. |
| Persisted per-file cache `data.reference_facts` | PARTIAL (end-to-end) | Tak, JSON/orjson | Full index może odświeżyć; single-file update nie zapisuje tego cache | Full index czyta source bytes do hash validation; sam assembler nie | Facts są per-file, nie canonical state. Cache jest związany z bieżącym hash/path. |
| `extract_compact_reference_facts` / `_extract_reexport_facts` | PARTIAL | Nie samo w sobie; może trafić do per-file cache | Nie w obecnym preparation path | Bez dodatkowego I/O, jeśli poda się już posiadane `tree` i `imports` | Zawiera source-local reexport envelope. `__all__` wielokrotne rozbiega się z `_explicit_all`; mapa globalna wymaga assemblera. |
| `_assemble_reexport_map(compact_facts)` | COMPLETE dla przekazanego envelope | Nie; pure in-memory derived value | Nie jest wywoływany przez obecne single-file preparation | Nie | Odtwarza transitive/star/cycle rules z dostarczonych facts; nie może skorygować utraconego przez extractor pierwszego/ostatniego `__all__`. |
| `RepositoryReferenceIndex.reexports` | COMPLETE dla wyniku compact path | Current-run object; brak canonical state persistence | Nie w single-file update | Nie po dostarczeniu compact facts | Derived map dla reference index; pełna aktualna compact ścieżka ma opisaną wyżej rozbieżność `__all__`. |
| `_REEXPORT_CACHE` | COMPLETE dla zapisanego map result | Nie; process-local | Wyliczany na helper miss; nie jest per-file fresh facts | Helper miss może stat/read/parse | Wynik globalny, klucz tylko identity/length modules dict. |
| `lineage_facts_by_source` / extracted lineage surfaces | PARTIAL | Tak, canonical snapshot/hydration | Tak, jeśli preparation ma `source_key` | Nie dodatkowo po przekazaniu parsed tree | Potrafi opisać część public/export/reexport surfaces; nie jest globalną star/transitive/cycle-resolved mapą. |
| Other canonical/per-file metadata (`file_state`, parse freshness, collision facts, symbol facts) | INSUFFICIENT | Różnie; canonical state i/lub per-file cache | Część jest aktualizowana | Bez I/O do odczytu | Hash/freshness, collisions lub symbol inventory nie niosą brakującej kompletnej export binding map. |

### Semantic coverage matrix

Zakres kolumn odpowiada kolejno: top-level `from x import y`; alias `as z`; relative imports; `__all__`; star imports; transitive reexports; top-level assignment aliases; private-name filtering; cycle-safe resolution.

| Representation | from import | alias | relative | `__all__` | star | transitive | assignment alias | private filter | cycle-safe |
|---|---|---|---|---|---|---|---|---|---|
| `_build_reexport_map` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| Compact extractor + assembler | COMPLETE | COMPLETE | COMPLETE | PARTIAL | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| `RepositoryAnalysisState` alone | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| `ModuleUsageFacts` | PARTIAL | PARTIAL | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| `module_usages_manifest` | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| `artifacts["symbols"]` | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| `Module.imports` | PARTIAL | INSUFFICIENT | PARTIAL | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| `reference_facts_by_module` / per-file `reference_facts` | COMPLETE | COMPLETE | COMPLETE | PARTIAL | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| Lineage facts/surfaces | PARTIAL | PARTIAL | PARTIAL | PARTIAL | INSUFFICIENT | INSUFFICIENT | PARTIAL | PARTIAL | INSUFFICIENT |
| `RepositoryReferenceIndex.reexports` / `_REEXPORT_CACHE` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |

Source-local compact envelope preserves explicit alias target in `bindings`, normalized relative source, literal `__all__`, star sources, and simple top-level Name assignment bindings. The single `PARTIAL` for compact `__all__` is specifically the first-vs-last repeated-assignment difference, not a generic dynamic Python export claim.

## SINGLE_FILE_PREPARATION_AVAILABLE_INPUTS

**DIRECT_EVIDENCE**: `contextor/core/analysis/incremental/preparation.py:145-301`, symbol `prepare_source_update`.

- Fresh `parsed_tree` comes from one `parse_source_with_fingerprint(path)`.
- Existing code derives `new_imports`, `new_artifacts`, collision facts, optional extracted lineage facts, `new_usage`, and deltas from this tree.
- It does **not** currently call `extract_compact_reference_facts` and the `PreparedSourceUpdate` return has no compact reference/reexport facts.
- Existing helper input contract accepts `module_id, tree=parsed_tree, imports=new_imports`; with both provided, helper does not access `module.ast_tree` or read source again.
- Output is plain dict/list/string/None facts (JSON/orjson-safe by current data shape; pickle compatibility follows from these built-in types, not separately tested). `_extract_reexport_facts` is directly called by the compact helper, so it is the exact same source-local extractor used by full-index current-run facts.
- Exact parity caveat: that extractor is not identical to the existing legacy `_explicit_all` behavior for repeated top-level `__all__` assignments.

## CANONICAL_REEXPORT_FACT_STORAGE

CANONICAL_REEXPORT_FACT_STORAGE=ABSENT

CAN_REBUILD_REEXPORT_MAP_FROM_CURRENT_CANONICAL_STATE_WITHOUT_SOURCE_IO=NO

**DIRECT_EVIDENCE**: canonical `RepositoryAnalysisState` declaration has no per-module reference/reexport facts; the compact facts live in `RepositoryIndex` during current full-analysis execution or in the per-file cache, and `RepositoryReferenceIndex.reexports` is a derived run-local map. Canonical artifacts, imports, usage facts, lineage, and manifests each omit at least required export semantics.

Minimal missing data contract, without schema/design proposal: current, validated per-module source-local reexport facts must be present in canonical state for the entire current module domain. The existing duplicate-`__all__` semantic difference also needs to be treated explicitly before claiming exact parity between the compact and legacy builders.

## SOURCE_SCAN_SCOPE

CAN_CURRENT_SINGLE_FILE_UPDATE_TOUCH_ALL_MODULE_SOURCE_PATHS=YES

CAN_CURRENT_SINGLE_FILE_UPDATE_PARSE_MULTIPLE_UNCHANGED_MODULES=CACHE_DEPENDENT

- Incremental caller can invoke `_build_reexport_map(candidate.modules)` on the recompute and/or artifact-consumption branches.
- On `_REEXPORT_CACHE` miss, the helper visits every candidate module and each `Module.ast_tree` access stats its absolute path. LIVE Contextor `symbol_calls` lineage reports 419 canonical modules at revision 1484; this indicates present module-domain scale, not a measured incremental pass.
- Actual source read and AST parse for unchanged modules depend on `_parse` LRU fingerprint entries: miss/eviction can read+parse multiple modules; warm entries still incur stat but can avoid read/parse.
- A `_REEXPORT_CACHE` hit skips module iteration entirely. Candidate dict identity normally differs from immediately previous state; an old-key id reuse remains possible but unobserved.
- This classification means the single-file route **can** touch every module source path through `stat`; it does not claim unconditional read/parse of all files.

## RAM_ONLY_SCOPE

- `_assemble_reexport_map` is an O(N facts + propagation passes) in-memory traversal once compact facts are already available. This is full-domain RAM work, not a source scan.
- `_REEXPORT_CACHE` hit is a RAM lookup/return.
- Current canonical state does not currently provide all compact reexport facts, so the RAM-only map-build option is not presently available from canonical state alone.
- Full analysis compact path still reads source snapshots before using persisted per-file facts to validate them; this validation read is distinct from later RAM-only reexport assembly.

## EXISTING_MEASUREMENT_CAPABILITY

MEASUREMENT_CAPABILITY=PARTIAL

**DIRECT_EVIDENCE**:

- Full indexer `FULL_ANALYSIS_INDEX_EVIDENCE` includes file-task counts, source parse calls/failures, cache gets/hits/misses, aggregate parse/cache durations (`contextor/core/symbol_engine/indexer.py:1444-1461`).
- Incremental phases emit phase-level timing events. No current hook found for per-update `Module.ast_tree` access count, filesystem stat count, `_build_reexport_map` elapsed time, or `_REEXPORT_CACHE` hit/miss.
- `_parse.cache_info()` exists by virtue of `functools.lru_cache`, but no current incremental trace consumes/emits it; even its aggregate counts would not identify per-module stat calls.
- **UNKNOWN**: actual counts and elapsed time for one current single-file update; actual cross-update `id()` cache reuse.

## MINIMAL_MISSING_EVIDENCE

- For static path/cost claim: none; source evidence proves the conditional whole-module iteration and per-module stat behavior.
- For runtime frequency/cost claim: one update-correlated observation of module AST accesses, stats, parse/read counts, reexport cache hit/miss, and elapsed time is absent from current hooks. No measurement was performed in this discovery.
- For cache id-reuse claim: runtime observation is absent; source proves only that key design permits the case once a numeric identity is reused.

## FILES_CHANGED

FILES_CHANGED=NONE (only the required report file was overwritten).

ACTUAL_DIFF=DIFFS=NONE


