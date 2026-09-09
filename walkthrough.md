FILES_CHANGED=
contextor/core/analysis/lineage_extraction.py
tests/analysis/test_lineage_extraction.py

TESTS_RUN=
.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q

TEST_RESULTS=
11 passed in 0.75s
22 passed in 2.61s

IMPLEMENTATION_NOTES=
Current patch is incomplete against the requested Stage 1C contract and is not suitable for acceptance: imports, control-flow frame merging, runtime-bound locals, and the complete required focused-test matrix are not implemented. No full-diff report is emitted because the requested implementation is not complete.

ACTUAL_DIFF=
NONE: incomplete implementation; do not treat this worktree as Stage 1C acceptance.
