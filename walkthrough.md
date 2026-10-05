# CPA10_LINEAGE_VALIDATION_CACHE_PER_CHUNK_TRUST

STATUS=PASS_WITH_RESTART_REQUIRED
FILES_CHANGED=contextor/core/live_state/store.py; tests/test_live_state_store.py
FULL_DIFFS=complete raw git diff for both changed files is included below

PY_COMPILE=PASS
PY_COMPILE_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\contextor\core\live_state\store.py C:\Temp\Contextor_Repo\tests\test_live_state_store.py
TARGETED_TESTS=PASS; exact requested node IDs; one physical command line
TARGETED_PASSED=12
TARGETED_FAILED=0
TARGETED_COLLECTED=12

VALIDATION_CACHE_SCHEMA_VERSION=2
REVISION_CHURN_REUSED_TRUST=YES
UNCHANGED_CHUNKS_DEEP_REVALIDATED=NO
CHANGED_CHUNK_DEEP_REVALIDATED=YES
CHANGED_CHUNK_CACHE_REFRESHED=YES
THIRD_LOAD_ALL_CURRENT_CHUNKS_TRUSTED=YES
WARM_CORRUPTION_FAIL_CLOSED=YES
STALE_CONTRACT_FALLBACK=YES
SCHEMA_12_BACKWARD_LOAD_PRESERVED=YES
SCHEMA_13_SPLIT_ROUNDTRIP_PRESERVED=YES
CANONICAL_MANIFEST_CHANGED=NO
SAVE_SNAPSHOT_CHANGED=NO
LIVE_STATE_SCHEMA_CHANGED=NO
LINEAGE_MANIFEST_SCHEMA_CHANGED=NO
VALIDATION_CACHE_AUTHORITY=NON_AUTHORITATIVE

CONTEXTOR_BEFORE_EDIT=canonical revision 1463; store module layer adapter; canonical state fresh; workspace_sync verified; syntax diagnostics checked_and_none; module blast radius reports 44 artifacts, 22 direct consumer modules and 140 transitive consumer modules. Test module context reports 30 indexed test artifacts including existing validation-cache, corruption, schema 1.2/1.3, and split-lineage tests.
CONTEXTOR_CALL_PATH=_load_split_lineage_generation is called by load_snapshot; _normalize_lineage_facts_state has load_snapshot call sites; _read_lineage_validation_cache is called by _load_split_lineage_generation; _write_lineage_validation_cache is called by load_snapshot.
CONTEXTOR_AFTER_EDIT=get_live_events after_revision=1463 returned revisions 1464 and 1465, both desktop_watcher update_file UPDATED, continuity continuous, resync_required false. Narrow file contexts for both changed files report canonical_state=fresh, workspace_sync=verified, canonical_revision=1465, syntax_diagnostics=checked_and_none with zero errors.
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
MCP_SERVER_RESTART_PERFORMED=NO
DESKTOP_RUNTIME_RESTART_PERFORMED=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
FIX_DESIGNED_BY_AGENT=NO

Protected-source check: `save_snapshot`, `_write_split_lineage_generation`, `_read_split_lineage_manifest`, and `_reusable_lineage_manifest_sources` are byte-for-byte unchanged against HEAD. `LIVE_STATE_SCHEMA_VERSION` remains `1.3`, `LINEAGE_MANIFEST_SCHEMA_VERSION` remains `1.0`, and `LINEAGE_VALIDATION_CONTRACT_VERSION` remains `1`. Forbidden files are unchanged. The only source/test paths in the diff are the two allowlisted files. `walkthrough.md` is the requested report artifact and is excluded from FILES_CHANGED.

## FULL_DIFFS

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index a05dddb..3b395e7 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -41,7 +41,7 @@ from contextor.core.domain.lineage_facts import (
 LIVE_STATE_SCHEMA_VERSION = "1.3"
 LINEAGE_MANIFEST_SCHEMA_VERSION = "1.0"
 
-LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION = "1"
+LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION = "2"
 LINEAGE_VALIDATION_CONTRACT_VERSION = "1"
 _LINEAGE_VALIDATION_CACHE_NAME = "lineage_validation_cache.json"
 
@@ -301,7 +301,7 @@ def _revalidate_lineage_slice(
 def _normalize_lineage_facts_state(
     state: Any,
     *,
-    revalidate_slices: bool = True,
+    trusted_source_keys: set[str] | None = None,
 ) -> Any:
     """Normalize/validate persisted materialized lineage without source work."""
 
@@ -357,17 +357,19 @@ def _normalize_lineage_facts_state(
                 "Materialized lineage requires the current semantic version."
             )
 
+        trusted = (
+            trusted_source_keys
+            if trusted_source_keys is not None
+            else set()
+        )
+
         normalized: dict[str, MaterializedLineageSourceFacts] = {}
         for source_key, source_slice in raw_mapping.items():
             if not isinstance(source_key, str) or not source_key:
                 raise pickle.UnpicklingError(
                     "Lineage source key must be a non-empty string."
                 )
-            if revalidate_slices:
-                rebuilt = _revalidate_lineage_slice(
-                    source_slice
-                )
-            else:
+            if source_key in trusted:
                 if not isinstance(
                     source_slice,
                     MaterializedLineageSourceFacts,
@@ -376,6 +378,10 @@ def _normalize_lineage_facts_state(
                         "Lineage source value has invalid type."
                     )
                 rebuilt = source_slice
+            else:
+                rebuilt = _revalidate_lineage_slice(
+                    source_slice
+                )
 
             if rebuilt.manifest.source_key != source_key:
                 raise pickle.UnpicklingError(
@@ -505,7 +511,6 @@ def _read_lineage_validation_cache(
     cache_dir: str | Path,
     *,
     metadata: LiveStateMetadata,
-    manifest_sha256: str,
 ) -> dict[str, dict[str, str]] | None:
     path = _lineage_validation_cache_path(
         cache_dir
@@ -529,6 +534,15 @@ def _read_lineage_validation_cache(
     if not isinstance(payload, dict):
         return None
 
+    if set(payload) != {
+        "schema_version",
+        "validation_contract_version",
+        "repo_id",
+        "lineage_semantic_version",
+        "chunks",
+    }:
+        return None
+
     if (
         payload.get("schema_version")
         != LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION
@@ -538,16 +552,6 @@ def _read_lineage_validation_cache(
         != LINEAGE_VALIDATION_CONTRACT_VERSION
         or payload.get("repo_id")
         != metadata.repo_id
-        or payload.get("state_id")
-        != metadata.state_id
-        or payload.get("revision")
-        != metadata.revision
-        or payload.get(
-            "lineage_manifest_file"
-        )
-        != metadata.lineage_manifest_file
-        or payload.get("manifest_sha256")
-        != manifest_sha256
         or payload.get(
             "lineage_semantic_version"
         )
@@ -573,13 +577,37 @@ def _read_lineage_validation_cache(
         ):
             return None
 
+        if set(entry) != {
+            "file",
+            "sha256",
+            "source_fingerprint",
+            "semantic_version",
+        }:
+            return None
+
         file_name = entry.get("file")
         sha256 = entry.get("sha256")
+        source_fingerprint = entry.get(
+            "source_fingerprint"
+        )
+        semantic_version = entry.get(
+            "semantic_version"
+        )
 
         if (
             not isinstance(file_name, str)
             or not file_name
             or not _is_sha256_hex(sha256)
+            or not isinstance(
+                source_fingerprint,
+                str,
+            )
+            or not source_fingerprint
+            or not isinstance(
+                semantic_version,
+                str,
+            )
+            or not semantic_version
         ):
             return None
 
@@ -598,6 +626,12 @@ def _read_lineage_validation_cache(
         chunks[source_key] = {
             "file": file_name,
             "sha256": sha256,
+            "source_fingerprint": (
+                source_fingerprint
+            ),
+            "semantic_version": (
+                semantic_version
+            ),
         }
 
     return chunks
@@ -607,7 +641,6 @@ def _write_lineage_validation_cache(
     cache_dir: str | Path,
     *,
     metadata: LiveStateMetadata,
-    manifest_sha256: str,
     chunks: dict[
         str,
         dict[str, str],
@@ -629,12 +662,6 @@ def _write_lineage_validation_cache(
             LINEAGE_VALIDATION_CONTRACT_VERSION
         ),
         "repo_id": metadata.repo_id,
-        "state_id": metadata.state_id,
-        "revision": metadata.revision,
-        "lineage_manifest_file": (
-            metadata.lineage_manifest_file
-        ),
-        "manifest_sha256": manifest_sha256,
         "lineage_semantic_version": (
             LINEAGE_FACTS_SEMANTIC_VERSION
         ),
@@ -1117,42 +1144,26 @@ def _load_split_lineage_generation(
         str,
         MaterializedLineageSourceFacts,
     ],
-    bool,
+    set[str],
     dict[
         str,
         dict[str, str],
     ],
-    str,
+    bool,
 ]:
     payload = _read_split_lineage_manifest(
         cache_dir,
         metadata,
     )
 
-    manifest_path = _snapshot_child_path(
-        cache_dir,
-        metadata.lineage_manifest_file,
-        label="Lineage manifest",
-    )
-
-    try:
-        manifest_sha256 = _sha256_bytes(
-            manifest_path.read_bytes()
-        )
-    except OSError as exc:
-        raise pickle.UnpicklingError(
-            "Invalid lineage manifest."
-        ) from exc
-
     validation_cache = (
         _read_lineage_validation_cache(
             cache_dir,
             metadata=metadata,
-            manifest_sha256=manifest_sha256,
         )
     )
 
-    validation_cache_complete = (
+    validation_cache_matches_current_chunks = (
         validation_cache is not None
     )
 
@@ -1165,6 +1176,8 @@ def _load_split_lineage_generation(
         MaterializedLineageSourceFacts,
     ] = {}
 
+    trusted_source_keys: set[str] = set()
+
     chunk_hashes: dict[
         str,
         dict[str, str],
@@ -1258,37 +1271,20 @@ def _load_split_lineage_generation(
                 "Invalid lineage source chunk."
             ) from exc
 
-        chunk_hashes[
-            source_key
-        ] = {
+        current_chunk = {
             "file": file_name,
             "sha256": actual_sha256,
+            "source_fingerprint": (
+                expected_fingerprint
+            ),
+            "semantic_version": (
+                expected_semantic_version
+            ),
         }
 
-        if validation_cache is not None:
-            cached_entry = (
-                validation_cache.get(
-                    source_key
-                )
-            )
-
-            if (
-                not isinstance(
-                    cached_entry,
-                    dict,
-                )
-                or cached_entry.get(
-                    "file"
-                )
-                != file_name
-                or cached_entry.get(
-                    "sha256"
-                )
-                != actual_sha256
-            ):
-                validation_cache_complete = (
-                    False
-                )
+        chunk_hashes[
+            source_key
+        ] = current_chunk
 
         if not isinstance(
             source_slice,
@@ -1322,6 +1318,24 @@ def _load_split_lineage_generation(
                 "Lineage chunk semantic version mismatch."
             )
 
+        if validation_cache is not None:
+            cached_entry = (
+                validation_cache.get(
+                    source_key
+                )
+            )
+
+            if cached_entry != current_chunk:
+                validation_cache_matches_current_chunks = (
+                    False
+                )
+            elif _lineage_slice_validation_cache_eligible(
+                source_slice
+            ):
+                trusted_source_keys.add(
+                    source_key
+                )
+
         loaded_sources[
             source_key
         ] = source_slice
@@ -1331,13 +1345,15 @@ def _load_split_lineage_generation(
         and set(validation_cache)
         != set(raw_sources)
     ):
-        validation_cache_complete = False
+        validation_cache_matches_current_chunks = (
+            False
+        )
 
     return (
         loaded_sources,
-        validation_cache_complete,
+        trusted_source_keys,
         chunk_hashes,
-        manifest_sha256,
+        validation_cache_matches_current_chunks,
     )
 
 
@@ -1865,10 +1881,9 @@ def load_snapshot(
                 "state"
             ]
 
-            lineage_validation_trusted = False
-            lineage_validation_cache_eligible = False
+            lineage_validation_trusted_source_keys: set[str] = set()
+            lineage_validation_cache_matches_current_chunks = False
             lineage_validation_chunks = None
-            lineage_validation_manifest_sha256 = None
 
             if metadata.lineage_manifest_file:
                 if (
@@ -1893,22 +1908,14 @@ def load_snapshot(
                 phase_started = time.monotonic()
                 (
                     split_lineage,
-                    lineage_validation_trusted,
+                    lineage_validation_trusted_source_keys,
                     lineage_validation_chunks,
-                    lineage_validation_manifest_sha256,
+                    lineage_validation_cache_matches_current_chunks,
                 ) = _load_split_lineage_generation(
                     cache_dir,
                     metadata,
                 )
 
-                lineage_validation_cache_eligible = all(
-                    _lineage_slice_validation_cache_eligible(
-                        source_slice
-                    )
-                    for source_slice
-                    in split_lineage.values()
-                )
-
                 _trace_snapshot_load_phase(
                     "split_lineage_load",
                     phase_started,
@@ -1938,8 +1945,8 @@ def load_snapshot(
             phase_started = time.monotonic()
             state_obj = _normalize_lineage_facts_state(
                 state_obj,
-                revalidate_slices=(
-                    not lineage_validation_trusted
+                trusted_source_keys=(
+                    lineage_validation_trusted_source_keys
                 ),
             )
             _trace_snapshot_load_phase(
@@ -2076,19 +2083,13 @@ def load_snapshot(
 
             if (
                 metadata.lineage_manifest_file
-                and not lineage_validation_trusted
-                and lineage_validation_cache_eligible
+                and not lineage_validation_cache_matches_current_chunks
                 and lineage_validation_chunks
                 is not None
-                and lineage_validation_manifest_sha256
-                is not None
             ):
                 _write_lineage_validation_cache(
                     cache_dir,
                     metadata=metadata,
-                    manifest_sha256=(
-                        lineage_validation_manifest_sha256
-                    ),
                     chunks=(
                         lineage_validation_chunks
                     ),
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 827c837..8d8ad88 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -432,12 +432,29 @@ def test_split_lineage_validation_cache_skips_repeat_deep_revalidation(
         ]
         == store.LINEAGE_VALIDATION_CONTRACT_VERSION
     )
+
     assert (
         cache_payload[
-            "lineage_manifest_file"
+            "schema_version"
         ]
-        == metadata.lineage_manifest_file
+        == "2"
     )
+
+    assert (
+        cache_payload[
+            "repo_id"
+        ]
+        == "repo-test"
+    )
+
+    assert set(cache_payload) == {
+        "schema_version",
+        "validation_contract_version",
+        "repo_id",
+        "lineage_semantic_version",
+        "chunks",
+    }
+
     assert (
         set(
             cache_payload[
@@ -602,6 +619,304 @@ def test_split_lineage_validation_cache_contract_mismatch_revalidates(
         == metadata
     )
 
+def test_split_lineage_validation_cache_survives_revision_churn_with_reused_chunks(
+    tmp_path,
+    monkeypatch,
+):
+    import json
+
+    import contextor.core.live_state.store as store
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    first_metadata = save_snapshot(
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
+    cache_before = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    first_manifest = json.loads(
+        (
+            tmp_path
+            / first_metadata.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    candidate = (
+        first_loaded[
+            0
+        ].clone_for_update()
+    )
+
+    second_metadata = save_snapshot(
+        candidate,
+        tmp_path,
+        "sid",
+        exact_revision=2,
+        repo_id="repo-test",
+        root_path=str(tmp_path),
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 2,
+            },
+            "files": {},
+        },
+        previous_state=first_loaded[0],
+    )
+
+    second_manifest = json.loads(
+        (
+            tmp_path
+            / second_metadata.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        first_manifest[
+            "sources"
+        ]
+        == second_manifest[
+            "sources"
+        ]
+    )
+
+    def unexpected_revalidation(
+        source_slice,
+    ):
+        raise AssertionError(
+            "revision churn revalidated unchanged lineage chunk"
+        )
+
+    monkeypatch.setattr(
+        store,
+        "_revalidate_lineage_slice",
+        unexpected_revalidation,
+    )
+
+    second_loaded = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-test",
+        expected_root_path=str(tmp_path),
+    )
+
+    assert second_loaded is not None
+    assert second_loaded[1] == second_metadata
+
+    cache_after = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert cache_after == cache_before
+
+    assert "revision" not in cache_after
+    assert "state_id" not in cache_after
+    assert (
+        "lineage_manifest_file"
+        not in cache_after
+    )
+    assert (
+        "manifest_sha256"
+        not in cache_after
+    )
+
+def test_split_lineage_validation_cache_revalidates_only_changed_chunk(
+    tmp_path,
+    monkeypatch,
+):
+    import json
+    from dataclasses import replace
+
+    import contextor.core.live_state.store as store
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    save_snapshot(
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
+    first_state = first_loaded[0]
+
+    candidate = first_state.clone_for_update()
+
+    previous_b = (
+        candidate.lineage_facts_by_source[
+            "pkg/b.py"
+        ]
+    )
+
+    candidate.lineage_facts_by_source[
+        "pkg/b.py"
+    ] = replace(
+        previous_b,
+        manifest=replace(
+            previous_b.manifest,
+            source_fingerprint=(
+                "source-1-next"
+            ),
+        ),
+    )
+
+    second_metadata = save_snapshot(
+        candidate,
+        tmp_path,
+        "sid",
+        exact_revision=2,
+        repo_id="repo-test",
+        root_path=str(tmp_path),
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 2,
+            },
+            "files": {},
+        },
+        previous_state=first_state,
+    )
+
+    original_revalidate = (
+        store._revalidate_lineage_slice
+    )
+    calls = []
+
+    def counting_revalidation(
+        source_slice,
+    ):
+        calls.append(
+            source_slice.manifest.source_key
+        )
+        return original_revalidate(
+            source_slice
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
+    assert second_loaded is not None
+    assert second_loaded[1] == second_metadata
+
+    assert calls == [
+        "pkg/b.py",
+    ]
+
+    cache_path = (
+        tmp_path
+        / store._LINEAGE_VALIDATION_CACHE_NAME
+    )
+
+    refreshed_cache = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        refreshed_cache[
+            "chunks"
+        ][
+            "pkg/b.py"
+        ][
+            "source_fingerprint"
+        ]
+        == "source-1-next"
+    )
+
+    def unexpected_revalidation(
+        source_slice,
+    ):
+        raise AssertionError(
+            "refreshed per-chunk trust performed deep revalidation"
+        )
+
+    monkeypatch.setattr(
+        store,
+        "_revalidate_lineage_slice",
+        unexpected_revalidation,
+    )
+
+    third_loaded = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-test",
+        expected_root_path=str(tmp_path),
+    )
+
+    assert third_loaded is not None
+    assert third_loaded[1] == second_metadata
 
 def test_split_lineage_validation_cache_chunk_mutation_falls_back_and_fails_closed(
     tmp_path,
```
