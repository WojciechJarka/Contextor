# P1B4 — CacheManager content-hash freshness

## STATUS

SUCCESS

`CacheManager._compute_hash()` no longer memoizes file hashes for the lifetime of one manager. Every `get()` and `set()` therefore hashes current file bytes, while the cache format, paths, atomic write, signatures, and indexer stay unchanged.

## FOCUSED_TESTS

`& .\.venv\Scripts\python.exe -m pytest -q tests\analysis\test_cache_manager_content_hash.py tests\test_lineage_index_cache.py tests\analysis\test_lineage_cache_codec.py tests\analysis\test_lineage_extraction_equivalence.py`

20 passed in 3.57s.

`git diff --check -- contextor/core/analysis/cache_manager.py tests/analysis/test_cache_manager_content_hash.py` passed with no whitespace errors.

## CONTEXTOR_VERIFY

- `get_file_edit_context` resolves `contextor/core/analysis/cache_manager.py` as canonical module `contextor.core.analysis.cache_manager` (module `221/1`), with `contextor.core.symbol_engine.indexer` among direct consumers.
- `search_source` confirms unchanged `_cache_manager(root_str)` -> `cache.get(path)` and both existing `cache.set(path, ...)` paths in the indexer.
- No alternative cache path or indexer change was introduced.

## FILES_CHANGED

- `contextor/core/analysis/cache_manager.py`
- `tests/analysis/test_cache_manager_content_hash.py`

## COMMIT_SHA

Not created; this is a working-tree implementation only.
