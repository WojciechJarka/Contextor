FILES_CHANGED=
contextor/core/source.py
contextor/core/analysis/lineage_extraction.py
contextor/core/symbol_engine/indexer.py
contextor/core/analysis/incremental/preparation.py
contextor/core/analysis/incremental/engine.py
tests/analysis/test_lineage_extraction.py

TESTS_RUN=
.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
.venv\Scripts\python.exe -m pytest tests/test_no_double_parse.py tests/test_index_fusion.py -q

TEST_RESULTS=
`tests/analysis/test_lineage_extraction.py`: 10 passed in 0.74s.

Directly affected legacy tests: 7 passed, 4 failed. No production or test file outside the allowed scope was changed to mask these failures.

FAILURES=
`tests/test_no_double_parse.py::test_prepare_source_update_reads_and_parses_target_once` observes `Path.read_text`, while the required `parse_source_with_fingerprint` uses one raw-byte snapshot through `Path.read_bytes` to guarantee that AST and SHA-256 derive from identical bytes. Its historical assertion `len(read_calls) == 1` therefore reports zero.

`tests/test_index_fusion.py::{test_source_change_invalidates_symbol_facts_then_warm_hit_is_parse_free,test_legacy_cache_is_migrated_once_then_warm_hit_is_parse_free,test_symbol_facts_schema_mismatch_recomputes}` monkeypatch `indexer.parse_source` and assert historical cache-dependent parse counts. Stage 1B requires `_process_single_file` to call `parse_source_with_fingerprint` for every current source snapshot, including cache hits, because CacheManager intentionally does not store the transient lineage slice. These assertions consequently observe zero calls to the old wrapper. Changing those tests is outside the explicitly allowed files; changing the implementation to preserve their old cache/parse semantics would violate the required Stage 1B contract.

CONTEXTOR_BOUNDED_OWNERSHIP=
After the focused test was green, `get_symbol_implementation` confirmed the bounded owners: `parse_source` (`source.py:86-88`), `_process_single_file` (`indexer.py:306-544`), and `prepare_source_update` (`preparation.py:135-291`). The served canonical generation predates this working-tree patch, so Contextor correctly returned `stale_source` instead of source content; no resync/full analysis was run.

AUDIT_INVARIANTS=
PASS: `lineage_extraction.py` imports no `PersistentIdentityRegistry`, `RepositoryAnalysisState`, or `SemanticEndpoint`; output is `ExtractedLineageSourceFacts` with `flows=()` and `surfaces=()`; raw SHA-256 is full lowercase 64 hex from the parsed snapshot; resource-limit output is empty/non-partial; global/nonlocal multi-name local IDs use deterministic ordinals; `engine.py` change is only `source_key=source_path`; CacheManager payload has no lineage slice; no lineage domain semantic-version change.

BLOCKER=
The required implementation is in the requested scope and passes its focused certification, but it cannot receive a final green result while the explicitly out-of-scope legacy tests retain incompatible source-read and cache/parse-count assumptions. Direction is needed either to authorize updating those directly affected legacy tests to the new 1B contract, or to revise the 1B source-snapshot/cache requirement.

ACTUAL_DIFF=
NOT_EMITTED: final acceptance is blocked by the scope conflict above. A complete raw unified diff must be emitted only with the final accepted result; emitting it now would present the change as completed despite the required direct-test failures.
