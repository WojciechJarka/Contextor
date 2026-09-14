# P0_LINEAGE_ORACLE_REFRESH

## STATUS

SUCCESS

Zaktualizowano wyłącznie zapisane oracle hashes w `tests/analysis/test_lineage_extraction_equivalence.py` do audytowanej semantyki `ExtractedFlowFact.owner_local_id`. Nie zmieniono kodu produkcyjnego, logiki testów, corpusu ani serializacji.

## FOCUSED_PYTEST

`..venv\Scripts\python.exe -m pytest -q tests\analysis\test_lineage_extraction_equivalence.py`

`3 passed in 0.50s`

## VALIDATION

`git diff --check -- tests/analysis/test_lineage_extraction_equivalence.py`

Passed (no diff-check findings).

## FILES_CHANGED

- `tests/analysis/test_lineage_extraction_equivalence.py`

## FULL_DIFFS

```diff
diff --git a/tests/analysis/test_lineage_extraction_equivalence.py b/tests/analysis/test_lineage_extraction_equivalence.py
index 541a7ba..9d74ac6 100644
--- a/tests/analysis/test_lineage_extraction_equivalence.py
+++ b/tests/analysis/test_lineage_extraction_equivalence.py
@@ -128,21 +128,21 @@ _CORPUS = {
 
 
 EXPECTED_HASHES = {
-    "async_yield": "57fe7c8ab6b6468031df1a70efa1d66320485207edf99912959977059166dab7",
-    "comprehension_runtime_walrus": "35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9",
-    "if_for_frame_merge": "f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a",
-    "imports_alias_wildcard": "7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8",
-    "relative_import": "44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95",
+    "async_yield": "e6c709d1a5ef347b04ed888dd9fa055dbc5a24c33eb14ea1a489b60a15c7d731",
+    "comprehension_runtime_walrus": "efbd682411093e174775282b2ce9d7012106d09c5180d73f5fbdd54ec45a2a6e",
+    "if_for_frame_merge": "b12603da08418eef897fe090bc05a7783fd877ed6c2bfb5a1bfdcd20c7cdc305",
+    "imports_alias_wildcard": "ad52d65bb4140b3e8ea6f21781c68e749f240358b5683e8648199972db597682",
+    "relative_import": "10ee12f15c6cfc5ecb82511e18081534eb68b9e647ae0ec3d71f3611e510fb2e",
     "resource_limit": "40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb",
-    "signature_defaults_local_call": "97a3964dd7208f83b8200c12e7732e685ffde29f79ca7a1c001c69b2989a0122",
-    "try_except_finally_match": "ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f",
+    "signature_defaults_local_call": "514593c03cb9b3dda00b0e2289a15781b7a7b2e131a89cb6e2f3e2fb2ad09d3c",
+    "try_except_finally_match": "a1384557b901a8f8634f06da6e36c4df91007699f69b24a71d59c1b81da00299",
 }
 
 
 LEGACY_ANCHOR_FLOW_HASHES = {
     **EXPECTED_HASHES,
-    "async_yield": "110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9",
-    "signature_defaults_local_call": "4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b",
+    "async_yield": "49eaf024dbbea341d333f1e705037be68c0fce45c6acaed23ad93a850d381016",
+    "signature_defaults_local_call": "c7ff95a059aeeb7c5a3dc978f6a982fda491029286e0eeb8abe937fea4a2dfb5",
 }
 
```
