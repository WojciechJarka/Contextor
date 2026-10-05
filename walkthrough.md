# CPA10_LINEAGE_VALIDATION_CACHE_FAST_PATH

STATUS=PARTIAL (literal implementation and focused validation PASS; MCP/Desktop runtime reload pending)
FILES_CHANGED=
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py
FULL_DIFFS=COMPLETE_BELOW
PY_COMPILE=PASS (exit 0)
TARGETED_TESTS=PASS (9 passed in 10.41s; exit 0)
TARGETED_PASSED=9
TARGETED_FAILED=0
VALIDATION_CACHE_CREATED_AFTER_FULL_REVALIDATION=YES (code path and first-load test)
SECOND_LOAD_SKIPPED_DEEP_REVALIDATION=YES (targeted monkeypatch test)
STALE_CONTRACT_FELL_BACK_TO_DEEP_REVALIDATION=YES (targeted counting test)
CORRUPTION_FAIL_CLOSED_PRESERVED=YES (three parametrized cases)
SCHEMA_12_BACKWARD_LOAD_PRESERVED=YES (targeted test)
SCHEMA_13_SPLIT_ROUNDTRIP_PRESERVED=YES (targeted test)
CHUNK_REUSE_PRESERVED=YES (targeted test)
LIVE_STATE_SCHEMA_CHANGED=NO
LINEAGE_MANIFEST_SCHEMA_CHANGED=NO
CANONICAL_MANIFEST_CHANGED=NO
SAVE_SNAPSHOT_CHANGED=NO
VALIDATION_CACHE_AUTHORITY=NON_AUTHORITATIVE
WORKSPACE_SYNC=verified (both changed files, Contextor LIVE revision 1462)
CANONICAL_STATE=fresh (LIVE provenance, revision 1462; runtime imports still require reload)
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
FIX_DESIGNED_BY_AGENT=NO

## Findings and evidence

DIRECT_EVIDENCE: HEAD before patch=a5b2ffa8226b89b516927f59b4f9b22935dd8807. Before editing, Contextor returned canonical_revision=1458, provenance=live, workspace_sync=verified for store.py. Module blast radius: 35 artifacts, 26 unique direct consumers, 177 downstream consumers. load_snapshot is the direct intra-module caller of _load_split_lineage_generation. All specified literal anchors appeared exactly once; the old loader ended in return loaded_sources.

CODE_PATH_PROVED: The requested helper, cache keys, byte hash comparison, eligibility gate and conditional deep revalidation were inserted only in the specified locations. The schema-1.3 branch receives the loader tuple. The legacy monolithic branch remains as it was. The cache writer is reached only after successful normalization/finalization checks and only when the cache is not trusted and eligibility holds. No canonical snapshot or manifest writer changed.

DIRECT_EVIDENCE: The first patch-insertion script truncated multiline replacements at blank lines and temporarily left store.py with a syntax error. Before any requested validation, the source was reconstructed from the verified HEAD and the eleven literal patches were reapplied in memory; AST parse and git diff --check passed. This was a patch application correction, with no designed code change.

CONTRACT_PROVED: The exact requested py_compile passed. The exact requested pytest node-ID line collected nine cases and passed all nine. No tests were rerun.

DIRECT_EVIDENCE: Post-edit get_file_edit_context returned status=available, canonical_state=fresh, provenance=live, workspace_sync=verified, revision=1462 and fresh checked_and_none syntax diagnostics for both changed files. A single get_live_events poll after a real wait returned continuity=continuous, resync_required=false and latest_revision=1462. It recorded desktop_watcher SYNTAX_ERROR at revision 1459 on the temporary file, UPDATED for the test at 1460, RECOVERED for store.py at 1461, and UNCHANGED for the test at 1462. Diagnostic summary reported syntax_errors.count=0. No further poll was needed.

UNKNOWN: Reloaded MCP/Desktop runtime execution of the new code is not certified in this task. No manual restart was performed. The current LIVE source synchronization does not establish that already imported runtime modules were reloaded.

## Actions and validation

Applied only patches 1-11 to the two allowed files. contextor/core/runtime_trace.py and contextor/core/domain/lineage_facts.py were not edited. No update_file, analyze_project, full pytest suite, manual restart or process termination was performed.

PY_COMPILE_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\contextor\core\live_state\store.py C:\Temp\Contextor_Repo\tests\test_live_state_store.py
TARGETED_PYTEST_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py::test_split_lineage_validation_cache_skips_repeat_deep_revalidation tests/test_live_state_store.py::test_split_lineage_validation_cache_contract_mismatch_revalidates tests/test_live_state_store.py::test_split_snapshot_load_emits_non_overlapping_phase_timings tests/test_live_state_store.py::test_exact_schema_13_splits_lineage_and_roundtrips tests/test_live_state_store.py::test_split_lineage_corruption_fails_closed tests/test_live_state_store.py::test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity tests/test_live_state_store.py::test_schema_12_monolithic_snapshot_remains_loadable

## Next step / STOP

STOP. Await proceduj. After manual reload, first verify runtime freshness/schema/version before runtime certification.

## FULL_DIFFS / ACTUAL_DIFF


### contextor/core/live_state/store.py

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index db775d3..a05dddb 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -3,6 +3,8 @@
 from __future__ import annotations
 
 import copy
+import hashlib
+import io
 import json
 import os
 import pickle
@@ -39,6 +41,10 @@ from contextor.core.domain.lineage_facts import (
 LIVE_STATE_SCHEMA_VERSION = "1.3"
 LINEAGE_MANIFEST_SCHEMA_VERSION = "1.0"
 
+LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION = "1"
+LINEAGE_VALIDATION_CONTRACT_VERSION = "1"
+_LINEAGE_VALIDATION_CACHE_NAME = "lineage_validation_cache.json"
+
 
 class _LegacySymbolCallFact:
     """Unpickle-only shape used by a transient pre-tuple snapshot format."""
@@ -292,7 +298,11 @@ def _revalidate_lineage_slice(
     )
 
 
-def _normalize_lineage_facts_state(state: Any) -> Any:
+def _normalize_lineage_facts_state(
+    state: Any,
+    *,
+    revalidate_slices: bool = True,
+) -> Any:
     """Normalize/validate persisted materialized lineage without source work."""
 
     if state is None or isinstance(state, dict) or not hasattr(state, "__dict__"):
@@ -353,7 +363,20 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
                 raise pickle.UnpicklingError(
                     "Lineage source key must be a non-empty string."
                 )
-            rebuilt = _revalidate_lineage_slice(source_slice)
+            if revalidate_slices:
+                rebuilt = _revalidate_lineage_slice(
+                    source_slice
+                )
+            else:
+                if not isinstance(
+                    source_slice,
+                    MaterializedLineageSourceFacts,
+                ):
+                    raise pickle.UnpicklingError(
+                        "Lineage source value has invalid type."
+                    )
+                rebuilt = source_slice
+
             if rebuilt.manifest.source_key != source_key:
                 raise pickle.UnpicklingError(
                     "Lineage mapping key does not match manifest source_key."
@@ -454,6 +477,276 @@ def _snapshot_child_path(
     return Path(cache_dir) / candidate
 
 
+def _sha256_bytes(payload: bytes) -> str:
+    return hashlib.sha256(payload).hexdigest()
+
+
+def _is_sha256_hex(value: object) -> bool:
+    return (
+        isinstance(value, str)
+        and len(value) == 64
+        and all(
+            character in "0123456789abcdef"
+            for character in value
+        )
+    )
+
+
+def _lineage_validation_cache_path(
+    cache_dir: str | Path,
+) -> Path:
+    return (
+        Path(cache_dir)
+        / _LINEAGE_VALIDATION_CACHE_NAME
+    )
+
+
+def _read_lineage_validation_cache(
+    cache_dir: str | Path,
+    *,
+    metadata: LiveStateMetadata,
+    manifest_sha256: str,
+) -> dict[str, dict[str, str]] | None:
+    path = _lineage_validation_cache_path(
+        cache_dir
+    )
+
+    try:
+        payload = json.loads(
+            path.read_text(
+                encoding="utf-8"
+            )
+        )
+    except (
+        FileNotFoundError,
+        OSError,
+        json.JSONDecodeError,
+        TypeError,
+        ValueError,
+    ):
+        return None
+
+    if not isinstance(payload, dict):
+        return None
+
+    if (
+        payload.get("schema_version")
+        != LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION
+        or payload.get(
+            "validation_contract_version"
+        )
+        != LINEAGE_VALIDATION_CONTRACT_VERSION
+        or payload.get("repo_id")
+        != metadata.repo_id
+        or payload.get("state_id")
+        != metadata.state_id
+        or payload.get("revision")
+        != metadata.revision
+        or payload.get(
+            "lineage_manifest_file"
+        )
+        != metadata.lineage_manifest_file
+        or payload.get("manifest_sha256")
+        != manifest_sha256
+        or payload.get(
+            "lineage_semantic_version"
+        )
+        != LINEAGE_FACTS_SEMANTIC_VERSION
+    ):
+        return None
+
+    raw_chunks = payload.get("chunks")
+
+    if not isinstance(raw_chunks, dict):
+        return None
+
+    chunks: dict[
+        str,
+        dict[str, str],
+    ] = {}
+
+    for source_key, entry in raw_chunks.items():
+        if (
+            not isinstance(source_key, str)
+            or not source_key
+            or not isinstance(entry, dict)
+        ):
+            return None
+
+        file_name = entry.get("file")
+        sha256 = entry.get("sha256")
+
+        if (
+            not isinstance(file_name, str)
+            or not file_name
+            or not _is_sha256_hex(sha256)
+        ):
+            return None
+
+        try:
+            _snapshot_child_path(
+                cache_dir,
+                file_name,
+                label=(
+                    "Lineage validation "
+                    "cache chunk"
+                ),
+            )
+        except pickle.UnpicklingError:
+            return None
+
+        chunks[source_key] = {
+            "file": file_name,
+            "sha256": sha256,
+        }
+
+    return chunks
+
+
+def _write_lineage_validation_cache(
+    cache_dir: str | Path,
+    *,
+    metadata: LiveStateMetadata,
+    manifest_sha256: str,
+    chunks: dict[
+        str,
+        dict[str, str],
+    ],
+) -> None:
+    path = _lineage_validation_cache_path(
+        cache_dir
+    )
+    temporary = path.with_name(
+        f".{path.name}.{os.getpid()}."
+        f"{uuid.uuid4().hex}.tmp"
+    )
+
+    payload = {
+        "schema_version": (
+            LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION
+        ),
+        "validation_contract_version": (
+            LINEAGE_VALIDATION_CONTRACT_VERSION
+        ),
+        "repo_id": metadata.repo_id,
+        "state_id": metadata.state_id,
+        "revision": metadata.revision,
+        "lineage_manifest_file": (
+            metadata.lineage_manifest_file
+        ),
+        "manifest_sha256": manifest_sha256,
+        "lineage_semantic_version": (
+            LINEAGE_FACTS_SEMANTIC_VERSION
+        ),
+        "chunks": {
+            source_key: dict(
+                chunks[source_key]
+            )
+            for source_key in sorted(chunks)
+        },
+    }
+
+    try:
+        with temporary.open(
+            "w",
+            encoding="utf-8",
+            newline="\n",
+        ) as stream:
+            json.dump(
+                payload,
+                stream,
+                indent=2,
+                sort_keys=True,
+            )
+            stream.write("\n")
+            stream.flush()
+            os.fsync(stream.fileno())
+
+        os.replace(
+            temporary,
+            path,
+        )
+
+    except OSError:
+        pass
+
+    finally:
+        try:
+            temporary.unlink()
+        except FileNotFoundError:
+            pass
+        except OSError:
+            pass
+
+
+def _lineage_slice_validation_cache_eligible(
+    source_slice: object,
+) -> bool:
+    if not isinstance(
+        source_slice,
+        MaterializedLineageSourceFacts,
+    ):
+        return False
+
+    manifest = source_slice.manifest
+
+    if not isinstance(
+        manifest,
+        SourceLineageManifest,
+    ):
+        return False
+
+    manifest_boolean_fields = (
+        "semantic_anchor_bindings_materialized",
+        "anchor_ownership_materialized",
+        "flow_ownership_materialized",
+        "interface_descriptors_materialized",
+    )
+
+    if any(
+        not hasattr(manifest, field)
+        or not isinstance(
+            getattr(manifest, field),
+            bool,
+        )
+        for field in manifest_boolean_fields
+    ):
+        return False
+
+    if any(
+        not hasattr(source_slice, field)
+        for field in (
+            "anchors",
+            "flows",
+            "surfaces",
+            "interface_descriptors",
+            "semantic_endpoint_origins",
+            "semantic_anchors",
+        )
+    ):
+        return False
+
+    if any(
+        not hasattr(
+            anchor,
+            "owner_local_id",
+        )
+        for anchor in source_slice.anchors
+    ):
+        return False
+
+    if any(
+        not hasattr(
+            flow,
+            "owner_local_id",
+        )
+        for flow in source_slice.flows
+    ):
+        return False
+
+    return True
+
+
 def _write_split_lineage_generation(
     state: Any,
     manifest_path: Path,
@@ -819,15 +1112,50 @@ def _reusable_lineage_manifest_sources(
 def _load_split_lineage_generation(
     cache_dir: str | Path,
     metadata: LiveStateMetadata,
-) -> dict[
+) -> tuple[
+    dict[
+        str,
+        MaterializedLineageSourceFacts,
+    ],
+    bool,
+    dict[
+        str,
+        dict[str, str],
+    ],
     str,
-    MaterializedLineageSourceFacts,
 ]:
     payload = _read_split_lineage_manifest(
         cache_dir,
         metadata,
     )
 
+    manifest_path = _snapshot_child_path(
+        cache_dir,
+        metadata.lineage_manifest_file,
+        label="Lineage manifest",
+    )
+
+    try:
+        manifest_sha256 = _sha256_bytes(
+            manifest_path.read_bytes()
+        )
+    except OSError as exc:
+        raise pickle.UnpicklingError(
+            "Invalid lineage manifest."
+        ) from exc
+
+    validation_cache = (
+        _read_lineage_validation_cache(
+            cache_dir,
+            metadata=metadata,
+            manifest_sha256=manifest_sha256,
+        )
+    )
+
+    validation_cache_complete = (
+        validation_cache is not None
+    )
+
     raw_sources = payload[
         "sources"
     ]
@@ -837,6 +1165,11 @@ def _load_split_lineage_generation(
         MaterializedLineageSourceFacts,
     ] = {}
 
+    chunk_hashes: dict[
+        str,
+        dict[str, str],
+    ] = {}
+
     for source_key in sorted(
         raw_sources
     ):
@@ -901,14 +1234,21 @@ def _load_split_lineage_generation(
         )
 
         try:
-            with chunk_path.open(
-                "rb"
-            ) as stream:
-                source_slice = (
-                    _SnapshotUnpickler(
-                        stream
-                    ).load()
+            chunk_bytes = (
+                chunk_path.read_bytes()
+            )
+            actual_sha256 = (
+                _sha256_bytes(
+                    chunk_bytes
                 )
+            )
+            source_slice = (
+                _SnapshotUnpickler(
+                    io.BytesIO(
+                        chunk_bytes
+                    )
+                ).load()
+            )
         except (
             OSError,
             pickle.PickleError,
@@ -918,6 +1258,38 @@ def _load_split_lineage_generation(
                 "Invalid lineage source chunk."
             ) from exc
 
+        chunk_hashes[
+            source_key
+        ] = {
+            "file": file_name,
+            "sha256": actual_sha256,
+        }
+
+        if validation_cache is not None:
+            cached_entry = (
+                validation_cache.get(
+                    source_key
+                )
+            )
+
+            if (
+                not isinstance(
+                    cached_entry,
+                    dict,
+                )
+                or cached_entry.get(
+                    "file"
+                )
+                != file_name
+                or cached_entry.get(
+                    "sha256"
+                )
+                != actual_sha256
+            ):
+                validation_cache_complete = (
+                    False
+                )
+
         if not isinstance(
             source_slice,
             MaterializedLineageSourceFacts,
@@ -954,7 +1326,19 @@ def _load_split_lineage_generation(
             source_key
         ] = source_slice
 
-    return loaded_sources
+    if (
+        validation_cache is not None
+        and set(validation_cache)
+        != set(raw_sources)
+    ):
+        validation_cache_complete = False
+
+    return (
+        loaded_sources,
+        validation_cache_complete,
+        chunk_hashes,
+        manifest_sha256,
+    )
 
 
 class SnapshotRevisionConflict(ValueError):
@@ -1481,6 +1865,11 @@ def load_snapshot(
                 "state"
             ]
 
+            lineage_validation_trusted = False
+            lineage_validation_cache_eligible = False
+            lineage_validation_chunks = None
+            lineage_validation_manifest_sha256 = None
+
             if metadata.lineage_manifest_file:
                 if (
                     metadata.schema_version
@@ -1502,12 +1891,24 @@ def load_snapshot(
                     return None
 
                 phase_started = time.monotonic()
-                split_lineage = (
-                    _load_split_lineage_generation(
-                        cache_dir,
-                        metadata,
+                (
+                    split_lineage,
+                    lineage_validation_trusted,
+                    lineage_validation_chunks,
+                    lineage_validation_manifest_sha256,
+                ) = _load_split_lineage_generation(
+                    cache_dir,
+                    metadata,
+                )
+
+                lineage_validation_cache_eligible = all(
+                    _lineage_slice_validation_cache_eligible(
+                        source_slice
                     )
+                    for source_slice
+                    in split_lineage.values()
                 )
+
                 _trace_snapshot_load_phase(
                     "split_lineage_load",
                     phase_started,
@@ -1536,7 +1937,10 @@ def load_snapshot(
 
             phase_started = time.monotonic()
             state_obj = _normalize_lineage_facts_state(
-                state_obj
+                state_obj,
+                revalidate_slices=(
+                    not lineage_validation_trusted
+                ),
             )
             _trace_snapshot_load_phase(
                 "normalize_lineage_facts_state",
@@ -1670,6 +2074,26 @@ def load_snapshot(
                     except AttributeError:
                         pass
 
+            if (
+                metadata.lineage_manifest_file
+                and not lineage_validation_trusted
+                and lineage_validation_cache_eligible
+                and lineage_validation_chunks
+                is not None
+                and lineage_validation_manifest_sha256
+                is not None
+            ):
+                _write_lineage_validation_cache(
+                    cache_dir,
+                    metadata=metadata,
+                    manifest_sha256=(
+                        lineage_validation_manifest_sha256
+                    ),
+                    chunks=(
+                        lineage_validation_chunks
+                    ),
+                )
+
             _trace_snapshot_load_phase(
                 "post_normalization_finalize",
                 phase_started,
```

### tests/test_live_state_store.py

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 6400355..dcc5d39 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -369,6 +369,240 @@ def test_split_snapshot_load_emits_non_overlapping_phase_timings(tmp_path):
     )
 
 
+def test_split_lineage_validation_cache_skips_repeat_deep_revalidation(
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
+    assert (
+        cache_payload[
+            "schema_version"
+        ]
+        == store.LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION
+    )
+    assert (
+        cache_payload[
+            "validation_contract_version"
+        ]
+        == store.LINEAGE_VALIDATION_CONTRACT_VERSION
+    )
+    assert (
+        cache_payload[
+            "lineage_manifest_file"
+        ]
+        == metadata.lineage_manifest_file
+    )
+    assert (
+        set(
+            cache_payload[
+                "chunks"
+            ]
+        )
+        == {
+            "pkg/a.py",
+            "pkg/b.py",
+        }
+    )
+
+    def unexpected_revalidation(
+        source_slice,
+    ):
+        raise AssertionError(
+            "trusted lineage chunk was deeply revalidated"
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
+
+    second_state, second_metadata = (
+        second_loaded
+    )
+
+    assert second_metadata == metadata
+    assert (
+        second_state.lineage_facts_by_source
+        == first_loaded[
+            0
+        ].lineage_facts_by_source
+    )
+
+
+def test_split_lineage_validation_cache_contract_mismatch_revalidates(
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
+    cache_payload = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    cache_payload[
+        "validation_contract_version"
+    ] = "stale"
+
+    cache_path.write_text(
+        json.dumps(
+            cache_payload,
+            indent=2,
+            sort_keys=True,
+        ),
+        encoding="utf-8",
+    )
+
+    original = (
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
+        return original(
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
+
+    assert sorted(calls) == [
+        "pkg/a.py",
+        "pkg/b.py",
+    ]
+
+    rewritten = json.loads(
+        cache_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        rewritten[
+            "validation_contract_version"
+        ]
+        == store.LINEAGE_VALIDATION_CONTRACT_VERSION
+    )
+
+    assert (
+        second_loaded[
+            1
+        ]
+        == metadata
+    )
+
+
 def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
     tmp_path,
 ):
```

