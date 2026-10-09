# L33/L34 snapshot manifest integrity discovery

MODE: READ-ONLY ARCHITECTURAL AUDIT. No implementation, tests, FULL analysis, restart or update_file.

## CURRENT_HEAD

`1a1efaee06aa927385821617dc72b889f436cf80` (`git rev-parse HEAD`). Initial `git status --short` was empty. Contextor MCP discovery included deferred-tool inventory, tool documentation, symbol lookup, implementation/source ranges, and lineage. Canonical owner: `contextor.core.live_state.store`; inspected Contextor records: canonical revision 114, `workspace_sync=verified`. Git working-tree source/test files supplied literal anchors; `git diff --name-only -- contextor tests` was empty.

## CANONICAL_SOURCE_DOMAIN_CONTRACT

- CONTRACT_PROVED: `RepositoryAnalysisState.modules` and `lineage_facts_by_source` are canonical state fields (`contextor/core/analysis/state_manager.py:83-102`). The full producer derives eligible keys as `Path(str(module.path)).as_posix()` over `modules.values()`, and marks the family `deferred` when an eligible key is absent (`contextor/core/api/facade.py:291-300,430-439`). Incremental refresh derives the same domain from `candidate.modules` and marks missing keys `deferred` or preserves `stale` (`contextor/core/analysis/incremental/engine.py:234-238,381-414`). These checks do not run in `load_snapshot`.
- DIRECT_EVIDENCE: `not_materialized` requires an empty lineage mapping and no semantic version; materialized family states require the current version (`contextor/core/live_state/store.py:347-395`). Thus an unmaterialized optional lineage family is distinct from an omitted source in a `fresh` materialized family.
- DIRECT_EVIDENCE: A valid intentionally empty source has a manifest entry/chunk and zero anchor/flow/surface counts (`contextor/core/domain/lineage_facts.py:428-465,483-499`; `tests/test_live_state_store.py:45-89`). An omitted source has no key. Malformed manifest or chunk is a separate corruption case.

## SAVE_LOAD_GENERATION_BOUNDARY

- CODE_PATH_PROVED: `save_snapshot` creates revision/token engine, file-state and lineage-manifest names (`contextor/core/live_state/store.py:1620-1654`). `LiveStateMetadata` carries schema, state_id, revision, writer, repo_id, root_path, and all three file references (`:469-479,1667-1688`). Split mode requires a dict lineage map (`:482-495`). Only present mapping keys are serialized into source chunks and manifest `sources`; the core pickle copy gets an empty lineage map (`:813-839,873-892,981-1025`). The pickle embeds metadata (`:1721-1755`). Save validates file-state `_meta.state_id/revision` (`:1757-1797`); `engine_state.meta.json` is committed last by `os.replace` (`:1813-1842`), with failed exact-generation cleanup (`:1854-1872`).
- CODE_PATH_PROVED: `load_snapshot` reads outer metadata, optionally checks caller-expected state/repository/root, then follows outer `state_file` (`:1926-1963`). Split load follows outer manifest reference, validates its schema/state_id/revision and each *listed* chunk (`:1040-1116,1175-1393,2004-2049`). The loaded map replaces the deliberately empty core map before normalization (`:2042-2067`), then the state/metadata pair is returned (`:2224-2229`).
- CODE_PATH_PROVED: Disk hydration delegates to `load_snapshot` and requires nonempty modules and a dependency graph, but does not check lineage domain (`contextor/core/analysis/state_manager.py:485-504`; `contextor/core/live_state/hydration.py:59-82`). LIVE startup calls the loader with expected repo/root, then constructs the server (`contextor/core/live_state/runtime.py:1431-1441,1528-1540`). Committed LIVE publication checks loaded state_id/revision against outer metadata and candidate, then installs the state (`contextor/core/live_state/ipc.py:1353-1404,1439-1451`).

## MANIFEST_COMPLETENESS_EVIDENCE

- DIRECT_EVIDENCE: The manifest holds schema_version, state_id, revision, sources, but no required-source count/domain (`contextor/core/live_state/store.py:993-1000`). Save iterates `sorted(sources)` without comparing to `state.modules` (`:823-839,873-892`).
- CODE_PATH_PROVED: Load requires `sources` to be a dict and iterates only its keys (`:1104-1116,1206-1245`). It checks each listed entry/chunk file, fingerprint, semantic version and key (`:1248-1355`). The validation cache compares its keys to manifest keys, not module paths (`:1379-1385`). Normalization validates only present source slices and preserves family state (`:357-430`). Index normalization builds from present sources and sets `lineage_query_index_state="fresh"` for a materialized family when index building succeeds (`:441-466`).
- INFERENCE from complete code path: Removing a valid entry from `manifest.sources` leaves a structurally valid manifest; the omitted chunk is never read. A validation-cache mismatch may revalidate/rewrite the remaining entries, but does not establish module-domain completeness. Persisted `lineage_facts_state="fresh"` and derived index `"fresh"` can remain after partial hydration.

## METADATA_BINDING_MATRIX

| Field | Save | Load comparison before assignment | Finding |
|---|---|---|---|
| repo_id / canonical root_path | Outer and embedded (`store.py:1667-1688,1740-1751`) | Caller expectations checked against outer only (`:1949-1957`); embedded parsed with empty defaults (`:1972-1987`) | Missing/mismatched embedded values accepted. |
| state_id | Outer, embedded, core, manifest, file-state _meta | Manifest vs outer (`:1084-1092`); *present* core vs outer (`:2109-2116`); embedded not compared and then assigned to core (`:2117-2123`) | Embedded omission defaults to empty string. Loader can return outer sid with state id empty; committed publish separately rejects (`ipc.py:1380-1391`). |
| revision | Same generation layers | Embedded vs outer (`store.py:1988-1989`), manifest vs outer (`:1094-1102`), present core vs outer (`:2105-2116`) | Embedded mismatch rejected; missing embedded revision defaults to 0 and fails for positive revisions. Missing core revision can be filled after check. |
| schema_version | Outer, embedded; manifest has own schema | Outer supported-set check (`:1416-1424`), split requires current outer schema (`:2004-2009`), manifest checks own schema (`:1074-1082`); no embedded comparison (`:1972-1994`) | Embedded omission/mismatch accepted. |
| engine state_file | Outer and embedded generation name | Outer selects pickle (`:1958-1963`); no embedded comparison (`:1972-1994`) | Embedded omission/mismatch accepted. |
| file_state_file / file-state generation | Outer and embedded; file JSON _meta | Save checks JSON id/revision (`:1757-1797`). `load_snapshot` does not read file JSON or compare embedded reference. Separate `FileStateManager._load` follows outer reference and checks JSON identity (`contextor/core/analysis/state_manager.py:293-375`) | Embedded reference mismatch accepted by snapshot loader. |
| lineage_manifest_file | Outer and embedded; manifest id/revision/schema | Embedded ref must equal outer (`store.py:1990-1994`); referenced manifest fields checked (`:1074-1102`) | Wrong/missing embedded split reference rejected. |
| writer | Outer and embedded | Parsed, not compared (`:1972-1994`) | Mismatch accepted; informational field. |

CODE_PATH_PROVED: The hypothesized mechanism “embedded metadata overwritten with trusted outer values before validation” is **not** what the code does. Embedded fields receive defaults; only embedded revision and manifest reference are compared. Present core state_id/revision are checked against outer, then core values are assigned from embedded values (`store.py:1972-1994,2105-2123`). This can mask missing core revision and inject an unverified embedded state_id. Embedded repo/root/schema/file names are not checked later by `load_snapshot`.

## EXISTING_NEGATIVE_TEST_COVERAGE

- DIRECT_EVIDENCE: Complete split roundtrip asserts both manifest source keys and equality of loaded and saved maps, but its fixture has no active modules domain (`tests/test_live_state_store.py:45-89,337-435`). Lifecycle roundtrip checks endpoint types and index freshness (`tests/test_lineage_state_lifecycle.py:172-207`). Neither tests omitted-but-valid source detection.
- DIRECT_EVIDENCE: Split corruption parameterization covers missing *listed chunk*, manifest revision mismatch and corrupt listed chunk, all asserting `load_snapshot is None` (`tests/test_live_state_store.py:1725-1808`). It never removes a source entry. Invalid family/version pairs and mapping/manifest source-key mismatch are covered (`tests/test_lineage_state_lifecycle.py:319-355`). Empty valid slices occur in the split fixture/roundtrip, without a check against active module paths.
- DIRECT_EVIDENCE: The embedded metadata roundtrip test asserts only successful revision equality (`tests/test_live_state_store.py:330-334`). Repository identity/root negatives pass expectations that disagree with **outer** metadata (`:2074-2094`). No inspected assertion tampers with embedded repo_id/root/schema/state_id/state_file/file_state_file or removes an embedded identity field. Manifest revision mismatch has a negative test (`:1784-1808`); embedded revision mismatch and wrong embedded manifest reference are rejected by code (`store.py:1988-1994`) but have no corresponding negative assertion in inspected snapshot tests.
- DIRECT_EVIDENCE: Interrupted metadata commit test asserts old revision remains and new generation files are absent (`tests/test_live_state_store.py:1811-1913`). Missing/invalid file-state generation and absent _meta have separate tests (`:2003-2048`). Legacy not-materialized lineage is asserted empty after hydration (`tests/test_lineage_state_lifecycle.py:430-505`). Search of test definitions found no omitted-manifest-source or embedded/outer metadata tamper assertion. This is a coverage observation, not a claim about every possible indirect test.

## MINIMAL_FAILURE_CASES

1. **L33, CODE_PATH_PROVED; unexecuted:** Take a valid schema-1.4 exact-revision snapshot with active module paths `a.py`, `b.py`, valid slices for both (each may have zero facts), and family state/version `fresh`/current. Remove only `"b.py"` from committed manifest `sources`; leave outer metadata, core pickle, remaining entry/chunk and manifest id/revision intact. Load iterates `a.py` only, assigns the reduced map, preserves family `fresh`, builds index state `fresh`, and returns a state with active `b.py` but no `b.py` lineage slice (`store.py:1104-1116,1222-1245,1375-1393,2042-2067,382-430,441-466,2224-2229`). A valid empty `b.py` slice would retain a manifest entry and differs from this case.
2. **L34, CODE_PATH_PROVED; unexecuted:** Save a valid split generation with outer `repo_id=R`, `root_path=P`, `state_id=sid`, `revision=1`. Change only the pickle's embedded repo_id to `R2` (or remove it); retain embedded revision, state_id and manifest reference, outer metadata and core state. `load_snapshot(..., expected_repo_id=R, expected_root_path=P)` compares expectations to outer, checks only embedded revision/manifest reference, and returns the snapshot (`store.py:1949-1957,1970-1994,2224-2229`). Committed-publish id/revision checks do not inspect embedded repo_id (`ipc.py:1362-1404`). No claim that normal save produces this mismatch.
3. **L34 distinction, CODE_PATH_PROVED; unexecuted:** Remove only embedded state_id. It defaults to empty string; the preassignment core `state_id=sid` passes outer comparison, then is replaced with empty string and returned alongside outer metadata `sid` (`store.py:1972-1994,2109-2123`). Committed publication rejects this particular returned state (`ipc.py:1380-1391`).

## L33_VERDICT

**PROVED_GAP.** Loader validates listed sources but never checks coverage of the active-module source domain. It can accept an omitted valid source while retaining `fresh` lineage family and index classifications. Code-path proof; counterexample not executed.

## L34_VERDICT

**PROVED_GAP.** Embedded revision and manifest reference are bound to outer metadata; embedded repository identity, root, state_id, schema, engine and file-state references are not fully bound. Embedded repo_id/root mismatch is accepted under matching outer caller expectations. Missing embedded state_id also yields a return-time inconsistency. Code-path proof; counterexamples not executed.

## REQUIRED_SOURCE_RANGES

`contextor/core/live_state/store.py:337-466,469-495,813-1037,1040-1116,1175-1393,1411-1442,1620-1688,1721-1874,1926-2123,2210-2229`; `contextor/core/analysis/state_manager.py:83-105,293-375,485-504`; `contextor/core/api/facade.py:291-300,430-439`; `contextor/core/analysis/incremental/engine.py:234-238,381-414`; `contextor/core/domain/lineage_facts.py:75-80,428-465,483-499`; `contextor/core/live_state/hydration.py:59-112`; `contextor/core/live_state/runtime.py:1431-1441,1528-1540`; `contextor/core/live_state/ipc.py:1353-1451`; `tests/test_live_state_store.py:45-89,330-435,1725-1913,2003-2048,2068-2094`; `tests/test_lineage_state_lifecycle.py:172-207,319-355,430-505`.

## ACTIONS / RESULT / NEXT STEP

Actions: Contextor-first discovery/lineage, Git HEAD and source-anchor verification, relevant test assertions read. Result: read-only code-path audit complete; no tests run. Next step: await `proceduj`.

FILES_CHANGED=NONE

ACTUAL_DIFF=NONE

DIFFS=NONE

