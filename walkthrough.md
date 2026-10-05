# CPA10_LINEAGE_VALIDATION_CACHE_WARM_CORRUPTION_REGRESSION

STATUS=PASS
FILES_CHANGED=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
FULL_DIFFS=COMPLETE_BELOW
PY_COMPILE=PASS (exit 0)
TARGETED_TESTS=PASS (6 passed in 1.90s; exit 0)
TARGETED_PASSED=6
TARGETED_FAILED=0
WARM_CACHE_CREATED=YES
CHUNK_HASH_CHANGED=YES
TRUST_INVALIDATED=YES
DEEP_REVALIDATION_CALLED=YES
SEMANTICALLY_INVALID_VALID_PICKLE_REJECTED=YES
FAILED_LOAD_DID_NOT_RECERTIFY_CHUNK=YES
PRODUCTION_FILES_CHANGED=NO
FIX_DESIGNED_BY_AGENT=NO
WORKSPACE_SYNC=verified (tests/test_live_state_store.py, LIVE revision 1463)
CANONICAL_STATE=fresh (LIVE provenance, revision 1463)

## Evidence

DIRECT_EVIDENCE: Before the edit, Contextor reported revision 1462, provenance=live and workspace_sync=verified for the target test and store.py. Contextor identified _normalize_lineage_facts_state as the direct intra-module caller of _revalidate_lineage_slice. The store module blast-radius view reported 44 artifacts, 26 direct consumers and 177 downstream consumers. HEAD was f6ed9d321c51b6bbb765a033263c12cba5d758c8 and the worktree was clean.

CODE_PATH_PROVED: Exactly the supplied test was inserted immediately after test_split_lineage_validation_cache_contract_mismatch_revalidates. It creates the cache with an initial valid load, changes a chunk after cache creation into a still-valid pickle with invalid flow_count, proves the chunk hash differs, counts a deep revalidation call, requires load_snapshot to return None and checks the old cache hash remains unchanged.

CONTRACT_PROVED: Requested py_compile passed. The one requested pytest command collected six cases and passed all six. No production code or other tests were changed or run. git diff --check passed.

DIRECT_EVIDENCE: Post-edit Contextor get_file_edit_context returned status=available, canonical_state=fresh, provenance=live, workspace_sync=verified and revision=1463 for the test file, with fresh checked_and_none syntax diagnostics. get_live_events(after_revision=1462) returned a desktop_watcher UPDATED event for that file at revision 1463, continuity=continuous and resync_required=false.

## Actions and validation

PY_COMPILE_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\tests\test_live_state_store.py
TARGETED_PYTEST_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py::test_split_lineage_validation_cache_chunk_mutation_falls_back_and_fails_closed tests/test_live_state_store.py::test_split_lineage_validation_cache_skips_repeat_deep_revalidation tests/test_live_state_store.py::test_split_lineage_validation_cache_contract_mismatch_revalidates tests/test_live_state_store.py::test_split_lineage_corruption_fails_closed

UPDATE_FILE_CALLED=NO
ANALYZE_PROJECT_RUN_COUNT=0
FULL_SUITE_RUN=NO
RESTART_PERFORMED=NO

## STOP

Await proceduj.

## FULL_DIFFS / ACTUAL_DIFF


### tests/test_live_state_store.py

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index dcc5d39..827c837 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -603,6 +603,171 @@ def test_split_lineage_validation_cache_contract_mismatch_revalidates(
     )
 
 
+def test_split_lineage_validation_cache_chunk_mutation_falls_back_and_fails_closed(
+    tmp_path,
+    monkeypatch,
+):
+    import json
+    import pickle
+
+    import contextor.core.live_state.store as store
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        repo_id="repo-test",
+        root_path=str(tmp_path),
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    first_loaded = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-test",
+        expected_root_path=str(tmp_path),
+    )
+
+    assert first_loaded is not None
+
+    cache_path = (
+        tmp_path
+        / store._LINEAGE_VALIDATION_CACHE_NAME
+    )
+
+    assert cache_path.is_file()
+
+    cache_payload = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    lineage_manifest = json.loads(
+        (
+            tmp_path
+            / metadata.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    chunk_file = (
+        lineage_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+    )
+
+    chunk_path = (
+        tmp_path
+        / chunk_file
+    )
+
+    cached_sha256 = (
+        cache_payload[
+            "chunks"
+        ][
+            "pkg/a.py"
+        ][
+            "sha256"
+        ]
+    )
+
+    source_slice = (
+        first_loaded[
+            0
+        ].lineage_facts_by_source[
+            "pkg/a.py"
+        ]
+    )
+
+    object.__setattr__(
+        source_slice.manifest,
+        "flow_count",
+        source_slice.manifest.flow_count + 1,
+    )
+
+    chunk_path.write_bytes(
+        pickle.dumps(
+            source_slice
+        )
+    )
+
+    assert (
+        store._sha256_bytes(
+            chunk_path.read_bytes()
+        )
+        != cached_sha256
+    )
+
+    original_revalidate = (
+        store._revalidate_lineage_slice
+    )
+    calls = []
+
+    def counting_revalidation(
+        candidate,
+    ):
+        calls.append(
+            candidate.manifest.source_key
+        )
+        return original_revalidate(
+            candidate
+        )
+
+    monkeypatch.setattr(
+        store,
+        "_revalidate_lineage_slice",
+        counting_revalidation,
+    )
+
+    second_loaded = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-test",
+        expected_root_path=str(tmp_path),
+    )
+
+    assert second_loaded is None
+
+    assert calls == [
+        "pkg/a.py",
+    ]
+
+    unchanged_cache = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        unchanged_cache[
+            "chunks"
+        ][
+            "pkg/a.py"
+        ][
+            "sha256"
+        ]
+        == cached_sha256
+    )
+
+
 def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
     tmp_path,
 ):
```
