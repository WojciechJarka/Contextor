## CPA10I_REFERENCE_FUSION_TEST_CONTRACT_MIGRATION

STATUS=PASS
HEAD_BEFORE=38f9607aad5d283922a33572dcc94ec314cb1873
HEAD_AFTER=38f9607aad5d283922a33572dcc94ec314cb1873
FILES_CHANGED=tests/test_reference_fusion_integration.py

CONTEXTOR_FIRST_VERIFICATION=PASS. Deferred Contextor tools were found and used. LIVE revision 1209, canonical_state=fresh, workspace_sync=verified: parse_source_snapshot resolved to contextor/core/source.py:85-108; _process_single_file resolved by preview to contextor/core/symbol_engine/indexer.py:313-665 with complete implementation available (implementation payload 15.8 KB, confirmation required for full fetch); index_repository resolved to contextor/core/symbol_engine/indexer.py:723-972. Contextor confirms parse seam signature parse_source_snapshot(snapshot, path), complete current-schema warm return before AST parse, and miss/incomplete parse ownership in _process_single_file.

PRE_EDIT_LITERAL_VERIFICATION=PASS. The target reference-fusion test already contained the migrated parse_source_snapshot seam and zero-parse warm assertion; the two stale len(calls) == 1 assertions remained and matched exactly.

TEST_1_REQUESTED=& ..venv\Scripts\python.exe -m pytest tests/test_reference_fusion_integration.py -q
TEST_1_REQUESTED_RESULT=NOT_EXECUTED_BY_PYTEST: PowerShell rejected the literal path because ..venv\Scripts\python.exe does not exist.
TEST_1_EFFECTIVE=& .\.venv\Scripts\python.exe -m pytest tests/test_reference_fusion_integration.py -q
TEST_1=PASS (9 passed in 5.31s)
TEST_2_EFFECTIVE=& .\.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_collision_facts_fusion.py tests/test_reference_fusion_integration.py tests/test_test_context_fusion.py -q
TEST_2=PASS (226 passed in 14.43s; 0 failed)
PRODUCTION_DIFF_EXTENDED=NO
PROFILE_RUN=NOT_RUN
MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_RUNTIME_RESTART_REQUIRED=YES_BEFORE_LATER_DESKTOP_CERTIFICATION
PROFILE_WORKER_RESTART_REQUIRED=NO
GIT_DIFF_CHECK=PASS (only CRLF conversion warnings)

ACTUAL_DIFF=
diff --git a/tests/test_reference_fusion_integration.py b/tests/test_reference_fusion_integration.py
index 6aad63c..a3553cc 100644
--- a/tests/test_reference_fusion_integration.py
+++ b/tests/test_reference_fusion_integration.py
@@ -98,7 +98,7 @@ def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
     )
     migrated = indexer.index_repository(str(root))
-    assert len(calls) == 1
+    assert calls == [source]
     assert migrated.reference_facts_by_module["module"]["status"] == "available"
     data = _payload(root, source)
@@ -107,7 +107,7 @@ def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
     _reset_worker_cache(root)
     calls.clear()
     remigrated = indexer.index_repository(str(root))
-    assert len(calls) == 1
+    assert calls == [source]
     assert remigrated.reference_facts_by_module["module"]["schema_version"] == 1
     _reset_worker_cache(root)
