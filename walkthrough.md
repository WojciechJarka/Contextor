# P1B5 — Lineage cache content change

## STATUS

SUCCESS

Added the requested integration test only. It changes same-length source content from `+ 1` to `+ 2`, proves exactly one refreshed lineage extraction with a changed `source_fingerprint`, then proves the following unchanged warm run reuses cached lineage.

## FOCUSED_TESTS

`& .\.venv\Scripts\python.exe -m pytest -q tests\analysis\test_cache_manager_content_hash.py tests\test_lineage_index_cache.py tests\analysis\test_lineage_cache_codec.py tests\analysis\test_lineage_extraction_equivalence.py`

21 passed in 1.45s.

`git diff --check -- tests/test_lineage_index_cache.py` passed with no whitespace errors.

## FILES_CHANGED

- `tests/test_lineage_index_cache.py`

## COMMIT_SHA

Not created; this is a working-tree implementation only.
