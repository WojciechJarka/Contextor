# CPA10L7C_CROSS_REVISION_LINEAGE_CHUNK_REUSE

STATUS=FINAL_PASS

## PRE-EDIT CONTEXTOR GATE

CONTEXTOR_PRE_EDIT_REVISION=1370
PRE_EDIT_WORKSPACE_SYNC=verified (all four planned files and read-only ipc.py)
PRE_EDIT_SCHEMA=LIVE_STATE_SCHEMA_VERSION=1.3
PRE_EDIT_LINEAGE_MANIFEST_SCHEMA=LINEAGE_MANIFEST_SCHEMA_VERSION=1.0
PRE_EDIT_METADATA_FIELD=lineage_manifest_file: str = ""
PRE_EDIT_SAVE_SNAPSHOT_HAS_PREVIOUS_STATE=NO
PRE_EDIT_SPLIT_WRITER_HAS_PREVIOUS_STATE=NO
PRE_EDIT_RUNTIME_PERSISTER_SIGNATURE=def _repository_persister(root: Path, holder: dict[str, object] | None = None):
PRE_EDIT_RUNTIME_PERSISTER_CONSTRUCTION=persister=_repository_persister(root, adapter_holder),
PRE_EDIT_IPC_PERSISTER_CONTRACT=Callable[[Any, int], Any] | None
PRE_EDIT_IPC_INVOCATION=persister(candidate_state, expected_revision)
PRE_EDIT_IPC_FILE_CHANGED=NO

PLANNED_FILES:
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py

PLANNED_CHANGE_SUMMARY=Add identity-only reuse of unchanged lineage slices' validated current chunk entries for exact schema 1.3 snapshots. Carry the previous-state baseline through the production _repository_persister closure and advance it only after successful persistence. Add the three specified store tests and one persister test. Leave ipc.py and its public two-argument persister contract unchanged.

## IMPLEMENTATION

LIVE_STATE_SCHEMA_VERSION=1.3
UNCHANGED_SLICE_REUSE_BY_IDENTITY=YES
EQUAL_DISTINCT_SLICE_REUSED=NO
CHANGED_SLICE_NEW_CHUNK=YES
UNCHANGED_SLICE_NEW_CHUNK=NO

FAILED_REVISION_DELETES_REUSED_PRIOR_CHUNK=NO
FAILED_PERSIST_ADVANCES_REUSE_BASELINE=NO
SUCCESSFUL_PERSIST_ADVANCES_REUSE_BASELINE=YES

FIRST_SPLIT_REVISION_WITHOUT_REUSABLE_PREDECESSOR_WRITES_ALL_CHUNKS=YES
SCHEMA_12_PREDECESSOR_REUSE=NO
CURRENT_SCHEMA_13_PREDECESSOR_REUSE=YES

CONTENT_HASH_REQUIRED_FOR_REUSE=NO
CONTENT_EQUALITY_USED_FOR_REUSE=NO
REUSE_VALIDATION=Use object identity plus current manifest state/revision/source metadata and a cache-local existing chunk path; no chunk/slice content hash is computed or content equality comparison is used.
NO_DELTA_CHAIN=YES
NO_GC_OR_RETENTION=YES

## IPC INVARIANT

IPC_FILE_CHANGED=NO
IPC_SIGNATURE_CHANGED=NO
PERSISTER_PUBLIC_ARITY=2
PERSISTER_INVOCATION=persister(candidate_state, expected_revision)
IPC_DIFF=NONE

## VALIDATION

PY_COMPILE=PASS
PY_COMPILE_COMMAND=.venv\Scripts\python.exe -m py_compile contextor\core\live_state\store.py contextor\core\live_state\runtime.py tests\test_live_state_store.py tests\test_live_state_ipc.py
FIRST_TEST_GATE=PASS (9 passed)
TARGETED_TESTS=PASS (205 passed; 1 third-party AuthlibDeprecationWarning)
TARGETED_TEST_COMMAND=.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py tests/test_live_state_ipc.py tests/test_live_mutation_coordinator.py tests/test_lineage_state_lifecycle.py tests/test_symbol_call_facts.py
FULL_SUITE_RUN=NO

## CONTEXTOR LIVE VERIFICATION

LIVE_WATCHER_PUBLICATIONS=1371 store.py; 1372 runtime.py; 1373 test_live_state_store.py; 1374 test_live_state_ipc.py (desktop_watcher UPDATED)
CONTEXTOR_POST_EDIT_REVISION=1374
WORKSPACE_SYNC=verified (all four modified files and read-only ipc.py)
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
DIAGNOSTICS_FRESH=YES
CONTEXTOR_PROVENANCE=live
PERSISTER_CALL_CONTEXT=run_service is the direct caller of _repository_persister.
SAVE_SNAPSHOT_BLAST_RADIUS=17 direct static consumer modules; runtime save caller remains the production integration point.
POST_EDIT_IDENTITY_GUARD=previous_slice is source_slice
POST_EDIT_RUNTIME_BASELINE=previous_state is passed to save_snapshot; persisted_state is advanced only after revision validation succeeds.

## RESTART AND PERFORMANCE

PERFORMANCE_CERTIFICATION=NOT_RUN
MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_PERFORMANCE_CERTIFICATION=YES
RESTART_PERFORMED=NO

## CHANGE CONTROL

FILES_CHANGED:
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py

PRODUCTION_CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

GIT_STATUS_AT_REPORT:
```text
 M contextor/core/live_state/runtime.py
 M contextor/core/live_state/store.py
 M tests/test_live_state_ipc.py
 M tests/test_live_state_store.py
 M walkthrough.md
```

## COMPLETE FULL_DIFFS

The following is the complete read-only `git diff --no-ext-diff` for every source/test file listed in FILES_CHANGED.

```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 31a46d2..c613dcf 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1093,20 +1093,44 @@ def _repository_updater(root: Path, holder: dict[str, object] | None = None):
     return update
 
 
-def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+def _repository_persister(
+    root: Path,
+    holder: dict[str, object] | None = None,
+    *,
+    previous_state: object | None = None,
+):
     identity = require_repository_identity(root)
     cache = repo_cache_dir(root)
+    persisted_state = previous_state
 
     def persist(state, exact_revision: int):
+        nonlocal persisted_state
+
         import time
+
         op = _safe_current_trace_operation()
         manager = (holder or {}).get("manager")
+
         if manager is None:
             from contextor.core.analysis.state_manager import FileStateManager
 
-            manager = FileStateManager(str(cache))
-        state_id = (holder or {}).get("state_id", getattr(manager, "state_id", ""))
+            manager = FileStateManager(
+                str(cache)
+            )
+
+        state_id = (
+            holder or {}
+        ).get(
+            "state_id",
+            getattr(
+                manager,
+                "state_id",
+                "",
+            ),
+        )
+
         snapshot_started = time.monotonic()
+
         try:
             meta = save_snapshot(
                 state,
@@ -1116,17 +1140,51 @@ def _repository_persister(root: Path, holder: dict[str, object] | None = None):
                 repo_id=identity.repo_id,
                 root_path=identity.root_path,
                 exact_revision=exact_revision,
-                file_state_payload=manager.build_payload(str(state_id), exact_revision),
+                file_state_payload=manager.build_payload(
+                    str(state_id),
+                    exact_revision,
+                ),
+                previous_state=persisted_state,
             )
+
             if meta.revision != exact_revision:
-                raise ValueError("Exact LIVE persistence revision mismatch.")
-            _safe_trace_event("LIVE", "SNAPSHOT_SAVE_END", op=op, repo=str(root), elapsed_ms=(time.monotonic() - snapshot_started) * 1000.0)
-            _safe_trace_event("LIVE", "FILE_STATE_SAVE_END", op=op, repo=str(root), elapsed_ms=0.0)
+                raise ValueError(
+                    "Exact LIVE persistence revision mismatch."
+                )
+
+            persisted_state = state
+
+            _safe_trace_event(
+                "LIVE",
+                "SNAPSHOT_SAVE_END",
+                op=op,
+                repo=str(root),
+                elapsed_ms=(
+                    time.monotonic()
+                    - snapshot_started
+                )
+                * 1000.0,
+            )
+
+            _safe_trace_event(
+                "LIVE",
+                "FILE_STATE_SAVE_END",
+                op=op,
+                repo=str(root),
+                elapsed_ms=0.0,
+            )
+
         except Exception as exc:
             from contextor.core.live_state.store import SnapshotRevisionConflict
+
             if isinstance(exc, SnapshotRevisionConflict):
-                raise CanonicalPersistenceConflict(exc.current_revision, exc.requested_revision) from exc
+                raise CanonicalPersistenceConflict(
+                    exc.current_revision,
+                    exc.requested_revision,
+                ) from exc
+
             raise
+
         return meta
 
     return persist
@@ -1319,7 +1377,11 @@ def run_service(
             state,
             revision=revision,
             updater=_repository_updater(root, adapter_holder),
-            persister=_repository_persister(root, adapter_holder),
+            persister=_repository_persister(
+                root,
+                adapter_holder,
+                previous_state=state,
+            ),
             canonical_query_handler=(
                 _repository_canonical_query_handler
             ),
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index fd3a7d6..a3ff5a1 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -2,6 +2,7 @@
 
 from __future__ import annotations
 
+import copy
 import json
 import os
 import pickle
@@ -35,7 +36,8 @@ from contextor.core.domain.lineage_facts import (
     SurfaceKind,
 )
 
-LIVE_STATE_SCHEMA_VERSION = "1.2"
+LIVE_STATE_SCHEMA_VERSION = "1.3"
+LINEAGE_MANIFEST_SCHEMA_VERSION = "1.0"
 
 
 class _LegacySymbolCallFact:
@@ -409,6 +411,550 @@ class LiveStateMetadata:
     root_path: str = ""
     state_file: str = ""
     file_state_file: str = ""
+    lineage_manifest_file: str = ""
+
+
+def _supports_split_lineage_generation(state: Any) -> bool:
+    return (
+        state is not None
+        and not isinstance(state, dict)
+        and hasattr(state, "__dict__")
+        and isinstance(
+            getattr(
+                state,
+                "lineage_facts_by_source",
+                None,
+            ),
+            dict,
+        )
+    )
+
+
+def _snapshot_child_path(
+    cache_dir: str | Path,
+    file_name: str,
+    *,
+    label: str,
+) -> Path:
+    if not isinstance(file_name, str) or not file_name:
+        raise pickle.UnpicklingError(
+            f"{label} file name must be non-empty."
+        )
+
+    candidate = Path(file_name)
+
+    if (
+        candidate.is_absolute()
+        or candidate.name != file_name
+    ):
+        raise pickle.UnpicklingError(
+            f"{label} file name must be a cache-local basename."
+        )
+
+    return Path(cache_dir) / candidate
+
+
+def _write_split_lineage_generation(
+    state: Any,
+    manifest_path: Path,
+    *,
+    state_id: str,
+    revision: int,
+    token: str,
+    previous_state: Any = None,
+    reusable_sources: dict[str, Any] | None = None,
+) -> tuple[Any, list[Path]]:
+    sources = getattr(
+        state,
+        "lineage_facts_by_source",
+    )
+
+    if not isinstance(sources, dict):
+        raise ValueError(
+            "lineage_facts_by_source must be a dict."
+        )
+
+    if any(
+        not isinstance(source_key, str)
+        or not source_key
+        for source_key in sources
+    ):
+        raise ValueError(
+            "Lineage source keys must be non-empty strings."
+        )
+
+    previous_sources = (
+        getattr(
+            previous_state,
+            "lineage_facts_by_source",
+            {},
+        )
+        if _supports_split_lineage_generation(
+            previous_state
+        )
+        else {}
+    )
+
+    if not isinstance(
+        previous_sources,
+        dict,
+    ):
+        previous_sources = {}
+
+    if not isinstance(
+        reusable_sources,
+        dict,
+    ):
+        reusable_sources = {}
+
+    created_chunks: list[Path] = []
+    manifest_sources: dict[
+        str,
+        dict[str, str],
+    ] = {}
+
+    try:
+        for index, source_key in enumerate(
+            sorted(sources)
+        ):
+            source_slice = sources[source_key]
+
+            if not isinstance(
+                source_slice,
+                MaterializedLineageSourceFacts,
+            ):
+                raise ValueError(
+                    "Lineage source value has invalid type."
+                )
+
+            if (
+                source_slice.manifest.source_key
+                != source_key
+            ):
+                raise ValueError(
+                    "Lineage mapping key does not match source manifest."
+                )
+
+            previous_slice = previous_sources.get(
+                source_key
+            )
+
+            reusable_entry = reusable_sources.get(
+                source_key
+            )
+
+            if (
+                previous_slice is source_slice
+                and isinstance(
+                    reusable_entry,
+                    dict,
+                )
+            ):
+                reusable_file = reusable_entry.get(
+                    "file"
+                )
+                reusable_fingerprint = reusable_entry.get(
+                    "source_fingerprint"
+                )
+                reusable_semantic_version = reusable_entry.get(
+                    "semantic_version"
+                )
+
+                if (
+                    isinstance(
+                        reusable_file,
+                        str,
+                    )
+                    and reusable_file
+                    and reusable_fingerprint
+                    == source_slice.manifest.source_fingerprint
+                    and reusable_semantic_version
+                    == source_slice.manifest.semantic_version
+                ):
+                    try:
+                        reusable_path = _snapshot_child_path(
+                            manifest_path.parent,
+                            reusable_file,
+                            label="Lineage chunk",
+                        )
+                    except pickle.UnpicklingError:
+                        reusable_path = None
+
+                    if (
+                        reusable_path is not None
+                        and reusable_path.is_file()
+                    ):
+                        manifest_sources[
+                            source_key
+                        ] = {
+                            "file": reusable_file,
+                            "source_fingerprint": (
+                                source_slice.manifest.source_fingerprint
+                            ),
+                            "semantic_version": (
+                                source_slice.manifest.semantic_version
+                            ),
+                        }
+
+                        continue
+
+            chunk_path = (
+                manifest_path.parent
+                / (
+                    f"lineage_source.r{revision}."
+                    f"{token}.{index:05d}.pkl"
+                )
+            )
+
+            created_chunks.append(
+                chunk_path
+            )
+
+            with chunk_path.open(
+                "wb"
+            ) as stream:
+                pickle.dump(
+                    source_slice,
+                    stream,
+                )
+                stream.flush()
+                os.fsync(
+                    stream.fileno()
+                )
+
+            manifest_sources[
+                source_key
+            ] = {
+                "file": chunk_path.name,
+                "source_fingerprint": (
+                    source_slice.manifest.source_fingerprint
+                ),
+                "semantic_version": (
+                    source_slice.manifest.semantic_version
+                ),
+            }
+
+        manifest_payload = {
+            "schema_version": (
+                LINEAGE_MANIFEST_SCHEMA_VERSION
+            ),
+            "state_id": state_id,
+            "revision": revision,
+            "sources": manifest_sources,
+        }
+
+        with manifest_path.open(
+            "w",
+            encoding="utf-8",
+        ) as stream:
+            json.dump(
+                manifest_payload,
+                stream,
+                indent=2,
+                sort_keys=True,
+            )
+            stream.flush()
+            os.fsync(
+                stream.fileno()
+            )
+
+        core_state = copy.copy(
+            state
+        )
+        core_state.lineage_facts_by_source = {}
+
+        return (
+            core_state,
+            created_chunks,
+        )
+
+    except Exception:
+        for generated_path in [
+            *created_chunks,
+            manifest_path,
+        ]:
+            try:
+                generated_path.unlink()
+            except OSError:
+                pass
+
+        raise
+
+
+def _read_split_lineage_manifest(
+    cache_dir: str | Path,
+    metadata: LiveStateMetadata,
+) -> dict[str, Any]:
+    manifest_path = _snapshot_child_path(
+        cache_dir,
+        metadata.lineage_manifest_file,
+        label="Lineage manifest",
+    )
+
+    try:
+        payload = json.loads(
+            manifest_path.read_text(
+                encoding="utf-8"
+            )
+        )
+    except (
+        OSError,
+        json.JSONDecodeError,
+        TypeError,
+        ValueError,
+    ) as exc:
+        raise pickle.UnpicklingError(
+            "Invalid lineage manifest."
+        ) from exc
+
+    if not isinstance(
+        payload,
+        dict,
+    ):
+        raise pickle.UnpicklingError(
+            "Lineage manifest must be a mapping."
+        )
+
+    if (
+        payload.get(
+            "schema_version"
+        )
+        != LINEAGE_MANIFEST_SCHEMA_VERSION
+    ):
+        raise pickle.UnpicklingError(
+            "Unsupported lineage manifest schema."
+        )
+
+    if (
+        payload.get(
+            "state_id"
+        )
+        != metadata.state_id
+    ):
+        raise pickle.UnpicklingError(
+            "Lineage manifest state_id mismatch."
+        )
+
+    if (
+        payload.get(
+            "revision"
+        )
+        != metadata.revision
+    ):
+        raise pickle.UnpicklingError(
+            "Lineage manifest revision mismatch."
+        )
+
+    sources = payload.get(
+        "sources"
+    )
+
+    if not isinstance(
+        sources,
+        dict,
+    ):
+        raise pickle.UnpicklingError(
+            "Lineage manifest sources must be a mapping."
+        )
+
+    return payload
+
+
+def _reusable_lineage_manifest_sources(
+    cache_dir: str | Path,
+    current: LiveStateMetadata | None,
+    previous_state: Any,
+) -> dict[str, Any]:
+    if (
+        current is None
+        or current.schema_version != LIVE_STATE_SCHEMA_VERSION
+        or not current.lineage_manifest_file
+        or not _supports_split_lineage_generation(
+            previous_state
+        )
+    ):
+        return {}
+
+    if (
+        getattr(
+            previous_state,
+            "revision",
+            None,
+        )
+        != current.revision
+    ):
+        return {}
+
+    if (
+        getattr(
+            previous_state,
+            "state_id",
+            None,
+        )
+        != current.state_id
+    ):
+        return {}
+
+    try:
+        payload = _read_split_lineage_manifest(
+            cache_dir,
+            current,
+        )
+    except pickle.UnpicklingError:
+        return {}
+
+    sources = payload.get(
+        "sources"
+    )
+
+    if not isinstance(
+        sources,
+        dict,
+    ):
+        return {}
+
+    return sources
+
+
+def _load_split_lineage_generation(
+    cache_dir: str | Path,
+    metadata: LiveStateMetadata,
+) -> dict[
+    str,
+    MaterializedLineageSourceFacts,
+]:
+    payload = _read_split_lineage_manifest(
+        cache_dir,
+        metadata,
+    )
+
+    raw_sources = payload[
+        "sources"
+    ]
+
+    loaded_sources: dict[
+        str,
+        MaterializedLineageSourceFacts,
+    ] = {}
+
+    for source_key in sorted(
+        raw_sources
+    ):
+        if (
+            not isinstance(
+                source_key,
+                str,
+            )
+            or not source_key
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage manifest source key is invalid."
+            )
+
+        entry = raw_sources[
+            source_key
+        ]
+
+        if not isinstance(
+            entry,
+            dict,
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage manifest source entry must be a mapping."
+            )
+
+        file_name = entry.get(
+            "file"
+        )
+        expected_fingerprint = entry.get(
+            "source_fingerprint"
+        )
+        expected_semantic_version = entry.get(
+            "semantic_version"
+        )
+
+        if (
+            not isinstance(
+                file_name,
+                str,
+            )
+            or not file_name
+            or not isinstance(
+                expected_fingerprint,
+                str,
+            )
+            or not expected_fingerprint
+            or not isinstance(
+                expected_semantic_version,
+                str,
+            )
+            or not expected_semantic_version
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage manifest source entry is incomplete."
+            )
+
+        chunk_path = _snapshot_child_path(
+            cache_dir,
+            file_name,
+            label="Lineage chunk",
+        )
+
+        try:
+            with chunk_path.open(
+                "rb"
+            ) as stream:
+                source_slice = (
+                    _SnapshotUnpickler(
+                        stream
+                    ).load()
+                )
+        except (
+            OSError,
+            pickle.PickleError,
+            EOFError,
+        ) as exc:
+            raise pickle.UnpicklingError(
+                "Invalid lineage source chunk."
+            ) from exc
+
+        if not isinstance(
+            source_slice,
+            MaterializedLineageSourceFacts,
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage source chunk has invalid type."
+            )
+
+        if (
+            source_slice.manifest.source_key
+            != source_key
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage chunk source key mismatch."
+            )
+
+        if (
+            source_slice.manifest.source_fingerprint
+            != expected_fingerprint
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage chunk source fingerprint mismatch."
+            )
+
+        if (
+            source_slice.manifest.semantic_version
+            != expected_semantic_version
+        ):
+            raise pickle.UnpicklingError(
+                "Lineage chunk semantic version mismatch."
+            )
+
+        loaded_sources[
+            source_key
+        ] = source_slice
+
+    return loaded_sources
 
 
 class SnapshotRevisionConflict(ValueError):
@@ -433,7 +979,10 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
     try:
         payload = json.loads(meta_file.read_text(encoding="utf-8"))
         if payload.get("schema_version") not in {
-            "1.0", "1.1", LIVE_STATE_SCHEMA_VERSION
+            "1.0",
+            "1.1",
+            "1.2",
+            LIVE_STATE_SCHEMA_VERSION,
         }:
             return None
         return LiveStateMetadata(
@@ -445,8 +994,14 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
             root_path=str(payload.get("root_path", "")),
             state_file=str(payload.get("state_file", "")),
             file_state_file=str(payload.get("file_state_file", "")),
+            lineage_manifest_file=str(
+                payload.get(
+                    "lineage_manifest_file",
+                    "",
+                )
+            ),
         )
-    except (OSError, ValueError, TypeError):
+    except (OSError, ValueError, KeyError, TypeError):
         return None
 
 
@@ -479,6 +1034,7 @@ def save_snapshot(
     revision_floor: int = 0,
     exact_revision: int | None = None,
     file_state_payload: dict[str, Any] | None = None,
+    previous_state: Any = None,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -490,90 +1046,330 @@ def save_snapshot(
     meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
     generation_state = state_tmp
     generation_file_state: Path | None = None
+    generation_lineage_manifest: Path | None = None
+    generation_lineage_chunks: list[Path] = []
+    reusable_lineage_sources: dict[str, Any] = {}
     committed = False
+
     try:
         current = read_metadata(cache_dir)
         normalized_root = (
-            str(Path(root_path).expanduser().resolve()) if root_path else ""
+            str(Path(root_path).expanduser().resolve())
+            if root_path
+            else ""
         )
-        if current and repo_id and current.repo_id and current.repo_id != repo_id:
-            raise ValueError("Snapshot repository ID does not match existing metadata.")
+
+        if (
+            current
+            and repo_id
+            and current.repo_id
+            and current.repo_id != repo_id
+        ):
+            raise ValueError(
+                "Snapshot repository ID does not match existing metadata."
+            )
+
         if (
             current
             and normalized_root
             and current.root_path
-            and Path(current.root_path).expanduser().resolve() != Path(normalized_root)
+            and Path(current.root_path).expanduser().resolve()
+            != Path(normalized_root)
         ):
-            raise ValueError("Snapshot repository root does not match existing metadata.")
+            raise ValueError(
+                "Snapshot repository root does not match existing metadata."
+            )
+
         if exact_revision is not None:
-            if isinstance(exact_revision, bool) or not isinstance(exact_revision, int) or exact_revision < 0:
-                raise ValueError("exact_revision must be a non-negative integer.")
-            current_revision = current.revision if current is not None else None
-            if current_revision is None and exact_revision != 1:
-                raise SnapshotRevisionConflict(None, exact_revision)
-            if current_revision is not None and exact_revision != current_revision + 1:
-                raise SnapshotRevisionConflict(current_revision, exact_revision)
+            if (
+                isinstance(exact_revision, bool)
+                or not isinstance(exact_revision, int)
+                or exact_revision < 0
+            ):
+                raise ValueError(
+                    "exact_revision must be a non-negative integer."
+                )
+
+            current_revision = (
+                current.revision
+                if current is not None
+                else None
+            )
+
+            if (
+                current_revision is None
+                and exact_revision != 1
+            ):
+                raise SnapshotRevisionConflict(
+                    None,
+                    exact_revision,
+                )
+
+            if (
+                current_revision is not None
+                and exact_revision
+                != current_revision + 1
+            ):
+                raise SnapshotRevisionConflict(
+                    current_revision,
+                    exact_revision,
+                )
+
             next_revision = exact_revision
-            generation_state = state_file.parent / f"engine_state.r{exact_revision}.{token}.pkl"
-            generation_file_state = state_file.parent / f"file_state.r{exact_revision}.{token}.json"
+
+            generation_state = (
+                state_file.parent
+                / (
+                    f"engine_state.r{exact_revision}."
+                    f"{token}.pkl"
+                )
+            )
+
+            generation_file_state = (
+                state_file.parent
+                / (
+                    f"file_state.r{exact_revision}."
+                    f"{token}.json"
+                )
+            )
+
+            if _supports_split_lineage_generation(
+                state
+            ):
+                generation_lineage_manifest = (
+                    state_file.parent
+                    / (
+                        f"lineage_manifest.r{exact_revision}."
+                        f"{token}.json"
+                    )
+                )
+
+                reusable_lineage_sources = (
+                    _reusable_lineage_manifest_sources(
+                        cache_dir,
+                        current,
+                        previous_state,
+                    )
+                )
+
         else:
-            next_revision = max(current.revision if current else 0, revision_floor) + 1
+            next_revision = (
+                max(
+                    current.revision
+                    if current
+                    else 0,
+                    revision_floor,
+                )
+                + 1
+            )
+
         metadata = LiveStateMetadata(
             state_id=state_id,
             revision=next_revision,
             writer=writer,
             repo_id=repo_id,
             root_path=normalized_root,
-            state_file=generation_state.name if exact_revision is not None else "",
-            file_state_file=generation_file_state.name if generation_file_state is not None else "",
+            state_file=(
+                generation_state.name
+                if exact_revision is not None
+                else ""
+            ),
+            file_state_file=(
+                generation_file_state.name
+                if generation_file_state is not None
+                else ""
+            ),
+            lineage_manifest_file=(
+                generation_lineage_manifest.name
+                if generation_lineage_manifest is not None
+                else ""
+            ),
         )
-        if exact_revision is not None and isinstance(state, dict):
+
+        if (
+            exact_revision is not None
+            and isinstance(
+                state,
+                dict,
+            )
+        ):
             state["revision"] = metadata.revision
             state["state_id"] = metadata.state_id
-        elif state is not None and hasattr(state, "__dict__"):
+
+        elif (
+            state is not None
+            and hasattr(
+                state,
+                "__dict__",
+            )
+        ):
             try:
-                setattr(state, "state_id", metadata.state_id)
-                setattr(state, "revision", metadata.revision)
+                setattr(
+                    state,
+                    "state_id",
+                    metadata.state_id,
+                )
+                setattr(
+                    state,
+                    "revision",
+                    metadata.revision,
+                )
             except AttributeError:
                 pass
-        with generation_state.open("wb") as stream:
-            pickle.dump({"metadata": asdict(metadata), "state": state}, stream)
+
+        state_to_persist = state
+
+        if (
+            generation_lineage_manifest
+            is not None
+        ):
+            (
+                state_to_persist,
+                generation_lineage_chunks,
+            ) = _write_split_lineage_generation(
+                state,
+                generation_lineage_manifest,
+                state_id=metadata.state_id,
+                revision=metadata.revision,
+                token=token,
+                previous_state=previous_state,
+                reusable_sources=reusable_lineage_sources,
+            )
+
+        with generation_state.open(
+            "wb"
+        ) as stream:
+            pickle.dump(
+                {
+                    "metadata": asdict(
+                        metadata
+                    ),
+                    "state": state_to_persist,
+                },
+                stream,
+            )
             stream.flush()
-            os.fsync(stream.fileno())
+            os.fsync(
+                stream.fileno()
+            )
+
         if generation_file_state is not None:
-            if not isinstance(file_state_payload, dict) or not isinstance(file_state_payload.get("_meta"), dict):
-                raise ValueError("file_state_payload must contain a _meta mapping.")
-            payload_meta = file_state_payload["_meta"]
-            if payload_meta.get("state_id", "") != state_id:
-                raise ValueError("FileState payload state_id does not match snapshot state_id.")
-            if payload_meta.get("revision") != exact_revision:
-                raise ValueError("FileState payload revision does not match exact_revision.")
-            with generation_file_state.open("w", encoding="utf-8") as stream:
-                json.dump(file_state_payload, stream, indent=2)
+            if (
+                not isinstance(
+                    file_state_payload,
+                    dict,
+                )
+                or not isinstance(
+                    file_state_payload.get(
+                        "_meta"
+                    ),
+                    dict,
+                )
+            ):
+                raise ValueError(
+                    "file_state_payload must contain a _meta mapping."
+                )
+
+            payload_meta = file_state_payload[
+                "_meta"
+            ]
+
+            if (
+                payload_meta.get(
+                    "state_id",
+                    "",
+                )
+                != state_id
+            ):
+                raise ValueError(
+                    "FileState payload state_id does not match snapshot state_id."
+                )
+
+            if (
+                payload_meta.get(
+                    "revision"
+                )
+                != exact_revision
+            ):
+                raise ValueError(
+                    "FileState payload revision does not match exact_revision."
+                )
+
+            with generation_file_state.open(
+                "w",
+                encoding="utf-8",
+            ) as stream:
+                json.dump(
+                    file_state_payload,
+                    stream,
+                    indent=2,
+                )
                 stream.flush()
-                os.fsync(stream.fileno())
-        with meta_tmp.open("w", encoding="utf-8") as stream:
-            json.dump(asdict(metadata), stream, indent=2)
+                os.fsync(
+                    stream.fileno()
+                )
+
+        with meta_tmp.open(
+            "w",
+            encoding="utf-8",
+        ) as stream:
+            json.dump(
+                asdict(
+                    metadata
+                ),
+                stream,
+                indent=2,
+            )
             stream.flush()
-            os.fsync(stream.fileno())
+            os.fsync(
+                stream.fileno()
+            )
+
         if exact_revision is None:
-            os.replace(generation_state, state_file)
-        os.replace(meta_tmp, meta_file)
+            os.replace(
+                generation_state,
+                state_file,
+            )
+
+        os.replace(
+            meta_tmp,
+            meta_file,
+        )
+
         committed = True
+
         return metadata
+
     finally:
-        for temporary in (state_tmp, meta_tmp):
+        for temporary in (
+            state_tmp,
+            meta_tmp,
+        ):
             try:
                 temporary.unlink()
             except OSError:
                 pass
-        if not committed and exact_revision is not None:
-            for temporary in (generation_state, generation_file_state):
-                if temporary is not None:
-                    try:
-                        temporary.unlink()
-                    except OSError:
-                        pass
+
+        if (
+            not committed
+            and exact_revision is not None
+        ):
+            failed_generations = [
+                generation_state,
+                generation_file_state,
+                generation_lineage_manifest,
+                *generation_lineage_chunks,
+            ]
+
+            for temporary in failed_generations:
+                if temporary is None:
+                    continue
+
+                try:
+                    temporary.unlink()
+                except OSError:
+                    pass
+
         try:
             os.close(lock_fd)
         finally:
@@ -624,12 +1420,66 @@ def load_snapshot(
                 root_path=str(embedded.get("root_path", "")),
                 state_file=str(embedded.get("state_file", "")),
                 file_state_file=str(embedded.get("file_state_file", "")),
+                lineage_manifest_file=str(
+                    embedded.get(
+                        "lineage_manifest_file",
+                        "",
+                    )
+                ),
             )
             if embedded_metadata.revision != metadata.revision:
                 return None
+            if (
+                embedded_metadata.lineage_manifest_file
+                != metadata.lineage_manifest_file
+            ):
+                return None
+
+            raw_state = payload[
+                "state"
+            ]
+
+            if metadata.lineage_manifest_file:
+                if (
+                    metadata.schema_version
+                    != LIVE_STATE_SCHEMA_VERSION
+                ):
+                    return None
+
+                if (
+                    raw_state is None
+                    or isinstance(
+                        raw_state,
+                        dict,
+                    )
+                    or not hasattr(
+                        raw_state,
+                        "__dict__",
+                    )
+                ):
+                    return None
+
+                split_lineage = (
+                    _load_split_lineage_generation(
+                        cache_dir,
+                        metadata,
+                    )
+                )
+
+                try:
+                    setattr(
+                        raw_state,
+                        "lineage_facts_by_source",
+                        split_lineage,
+                    )
+                except AttributeError:
+                    return None
+
             state_obj = _normalize_lineage_query_index_state(
                 _normalize_lineage_facts_state(
-                    _normalize_symbol_call_facts(payload["state"])
+                    _normalize_symbol_call_facts(
+                        raw_state
+                    )
                 )
             )
             state_revision = (
@@ -737,6 +1587,9 @@ def load_snapshot(
                     except AttributeError:
                         pass
             return state_obj, metadata
+        if metadata.lineage_manifest_file:
+            return None
+
         payload = _normalize_lineage_query_index_state(
             _normalize_lineage_facts_state(
                 _normalize_symbol_call_facts(payload)
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index b060f96..51fce71 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1079,9 +1079,150 @@ def test_real_repository_adapter_two_successive_updates_are_exact_successors(tmp
         assert read_metadata(cache).revision == expected
         loaded_state, loaded_metadata = load_snapshot(cache, "sid")
         assert loaded_metadata.revision == expected
-        assert loaded_state.revision == expected
-        assert FileStateManager(str(cache)).revision == expected
-        assert server._events[-1]["revision"] == expected
+    assert loaded_state.revision == expected
+    assert FileStateManager(str(cache)).revision == expected
+    assert server._events[-1]["revision"] == expected
+
+
+def test_repository_persister_advances_previous_state_only_after_success(
+    tmp_path,
+    monkeypatch,
+):
+    import contextor.core.live_state.runtime as runtime
+
+    from contextor.core.repository_identity import (
+        ensure_repository_identity,
+    )
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    ensure_repository_identity(
+        repo
+    )
+
+    class StubManager:
+        state_id = "sid"
+
+        def build_payload(
+            self,
+            state_id,
+            revision,
+        ):
+            return {
+                "_meta": {
+                    "state_id": state_id,
+                    "revision": revision,
+                },
+                "files": {},
+            }
+
+    holder = {
+        "manager": StubManager(),
+        "state_id": "sid",
+    }
+
+    initial = SimpleNamespace(
+        marker="initial"
+    )
+
+    first = SimpleNamespace(
+        marker="first"
+    )
+
+    failed = SimpleNamespace(
+        marker="failed"
+    )
+
+    second = SimpleNamespace(
+        marker="second"
+    )
+
+    calls = []
+
+    def fake_save_snapshot(
+        state,
+        _cache,
+        _state_id,
+        **kwargs,
+    ):
+        calls.append(
+            (
+                state,
+                kwargs.get(
+                    "previous_state"
+                ),
+                kwargs.get(
+                    "exact_revision"
+                ),
+            )
+        )
+
+        if state is failed:
+            raise RuntimeError(
+                "synthetic persistence failure"
+            )
+
+        return SimpleNamespace(
+            revision=kwargs[
+                "exact_revision"
+            ]
+        )
+
+    monkeypatch.setattr(
+        runtime,
+        "save_snapshot",
+        fake_save_snapshot,
+    )
+
+    persist = runtime._repository_persister(
+        repo,
+        holder,
+        previous_state=initial,
+    )
+
+    first_meta = persist(
+        first,
+        1,
+    )
+
+    assert first_meta.revision == 1
+
+    with pytest.raises(
+        RuntimeError,
+        match=(
+            "^synthetic persistence failure$"
+        ),
+    ):
+        persist(
+            failed,
+            2,
+        )
+
+    second_meta = persist(
+        second,
+        2,
+    )
+
+    assert second_meta.revision == 2
+
+    assert calls == [
+        (
+            first,
+            initial,
+            1,
+        ),
+        (
+            failed,
+            first,
+            2,
+        ),
+        (
+            second,
+            first,
+            2,
+        ),
+    ]
 
 
 def test_persistence_trace_operation_is_propagated_across_successful_real_update(tmp_path, monkeypatch):
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index d24db10..8aa692a 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -1,6 +1,7 @@
 """Unit and integration boundaries for the shared canonical LIVE snapshot store."""
 
 from concurrent.futures import ThreadPoolExecutor
+from pathlib import Path
 from types import SimpleNamespace
 
 import pytest
@@ -38,6 +39,53 @@ def test_legacy_state_without_manifest_loads_with_empty_manifest(tmp_path):
     assert loaded.module_usages_manifest == {}
 
 
+def _split_lineage_test_state(*source_keys):
+    from contextor.core.analysis.state_manager import (
+        RepositoryAnalysisState,
+    )
+    from contextor.core.domain.lineage_facts import (
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        LineageFamilyStatus,
+        MaterializedLineageSourceFacts,
+        SourceLineageManifest,
+    )
+
+    sources = {}
+
+    for index, source_key in enumerate(
+        source_keys
+    ):
+        sources[source_key] = (
+            MaterializedLineageSourceFacts(
+                manifest=SourceLineageManifest(
+                    source_key=source_key,
+                    source_fingerprint=(
+                        f"source-{index}"
+                    ),
+                    semantic_version=(
+                        LINEAGE_FACTS_SEMANTIC_VERSION
+                    ),
+                    status=(
+                        LineageFamilyStatus.FRESH
+                    ),
+                    anchor_count=0,
+                    flow_count=0,
+                    surface_count=0,
+                )
+            )
+        )
+
+    return RepositoryAnalysisState(
+        lineage_facts_by_source=sources,
+        lineage_facts_state=(
+            LineageFamilyStatus.FRESH.value
+        ),
+        lineage_facts_semantic_version=(
+            LINEAGE_FACTS_SEMANTIC_VERSION
+        ),
+    )
+
+
 def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
     second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")
@@ -131,6 +179,769 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
+def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
+    import json
+    import pickle
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
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    assert metadata.schema_version == "1.3"
+    assert metadata.lineage_manifest_file
+
+    with (
+        tmp_path
+        / metadata.state_file
+    ).open("rb") as stream:
+        core_payload = pickle.load(
+            stream
+        )
+
+    assert (
+        core_payload[
+            "state"
+        ].lineage_facts_by_source
+        == {}
+    )
+
+    manifest = json.loads(
+        (
+            tmp_path
+            / metadata.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        manifest[
+            "schema_version"
+        ]
+        == "1.0"
+    )
+    assert (
+        manifest[
+            "state_id"
+        ]
+        == "sid"
+    )
+    assert (
+        manifest[
+            "revision"
+        ]
+        == 1
+    )
+    assert set(
+        manifest[
+            "sources"
+        ]
+    ) == {
+        "pkg/a.py",
+        "pkg/b.py",
+    }
+
+    for entry in manifest[
+        "sources"
+    ].values():
+        assert (
+            tmp_path
+            / entry[
+                "file"
+            ]
+        ).is_file()
+
+    loaded_state, loaded_metadata = (
+        load_snapshot(
+            tmp_path,
+            "sid",
+        )
+    )
+
+    assert loaded_metadata == metadata
+    assert (
+        loaded_state.lineage_facts_by_source
+        == state.lineage_facts_by_source
+    )
+
+
+def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
+    tmp_path,
+):
+    import json
+    from dataclasses import replace
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    first = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    first_manifest = json.loads(
+        (
+            tmp_path
+            / first.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    candidate = state.clone_for_update()
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
+    second = save_snapshot(
+        candidate,
+        tmp_path,
+        "sid",
+        exact_revision=2,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 2,
+            },
+            "files": {},
+        },
+        previous_state=state,
+    )
+
+    second_manifest = json.loads(
+        (
+            tmp_path
+            / second.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        second_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+        == first_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+    )
+
+    assert (
+        second_manifest[
+            "sources"
+        ][
+            "pkg/b.py"
+        ][
+            "file"
+        ]
+        != first_manifest[
+            "sources"
+        ][
+            "pkg/b.py"
+        ][
+            "file"
+        ]
+    )
+
+    assert len(
+        list(
+            tmp_path.glob(
+                "lineage_source.r2.*.pkl"
+            )
+        )
+    ) == 1
+
+    loaded_state, loaded_metadata = (
+        load_snapshot(
+            tmp_path,
+            "sid",
+        )
+    )
+
+    assert loaded_metadata == second
+
+    assert (
+        loaded_state.lineage_facts_by_source
+        == candidate.lineage_facts_by_source
+    )
+
+
+def test_exact_split_lineage_does_not_reuse_equal_distinct_slice(
+    tmp_path,
+):
+    import json
+    from dataclasses import replace
+
+    state = _split_lineage_test_state(
+        "pkg/a.py"
+    )
+
+    first = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    first_manifest = json.loads(
+        (
+            tmp_path
+            / first.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    candidate = state.clone_for_update()
+
+    previous_slice = (
+        state.lineage_facts_by_source[
+            "pkg/a.py"
+        ]
+    )
+
+    equal_distinct = replace(
+        previous_slice
+    )
+
+    assert (
+        equal_distinct
+        == previous_slice
+    )
+
+    assert (
+        equal_distinct
+        is not previous_slice
+    )
+
+    candidate.lineage_facts_by_source[
+        "pkg/a.py"
+    ] = equal_distinct
+
+    second = save_snapshot(
+        candidate,
+        tmp_path,
+        "sid",
+        exact_revision=2,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 2,
+            },
+            "files": {},
+        },
+        previous_state=state,
+    )
+
+    second_manifest = json.loads(
+        (
+            tmp_path
+            / second.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    assert (
+        second_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+        != first_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+    )
+
+    assert len(
+        list(
+            tmp_path.glob(
+                "lineage_source.r2.*.pkl"
+            )
+        )
+    ) == 1
+
+
+def test_split_lineage_reuse_failure_preserves_previous_chunk(
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
+    first = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    first_manifest = json.loads(
+        (
+            tmp_path
+            / first.lineage_manifest_file
+        ).read_text(
+            encoding="utf-8"
+        )
+    )
+
+    reused_chunk = (
+        tmp_path
+        / first_manifest[
+            "sources"
+        ][
+            "pkg/a.py"
+        ][
+            "file"
+        ]
+    )
+
+    candidate = state.clone_for_update()
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
+    original_replace = store.os.replace
+
+    def fail_metadata_replace(
+        source,
+        target,
+    ):
+        if (
+            Path(
+                target
+            ).name
+            == "engine_state.meta.json"
+        ):
+            raise RuntimeError(
+                "synthetic metadata commit failure"
+            )
+
+        return original_replace(
+            source,
+            target,
+        )
+
+    monkeypatch.setattr(
+        store.os,
+        "replace",
+        fail_metadata_replace,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match=(
+            "^synthetic metadata commit failure$"
+        ),
+    ):
+        save_snapshot(
+            candidate,
+            tmp_path,
+            "sid",
+            exact_revision=2,
+            file_state_payload={
+                "_meta": {
+                    "state_id": "sid",
+                    "revision": 2,
+                },
+                "files": {},
+            },
+            previous_state=state,
+        )
+
+    assert reused_chunk.is_file()
+
+    assert (
+        read_metadata(
+            tmp_path
+        ).revision
+        == 1
+    )
+
+    assert not list(
+        tmp_path.glob(
+            "engine_state.r2.*.pkl"
+        )
+    )
+
+    assert not list(
+        tmp_path.glob(
+            "file_state.r2.*.json"
+        )
+    )
+
+    assert not list(
+        tmp_path.glob(
+            "lineage_manifest.r2.*.json"
+        )
+    )
+
+    assert not list(
+        tmp_path.glob(
+            "lineage_source.r2.*.pkl"
+        )
+    )
+
+
+@pytest.mark.parametrize(
+    "failure",
+    [
+        "missing_chunk",
+        "manifest_revision",
+        "corrupt_chunk",
+    ],
+)
+def test_split_lineage_corruption_fails_closed(
+    tmp_path,
+    failure,
+):
+    import json
+
+    state = _split_lineage_test_state(
+        "pkg/a.py"
+    )
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    manifest_path = (
+        tmp_path
+        / metadata.lineage_manifest_file
+    )
+
+    manifest = json.loads(
+        manifest_path.read_text(
+            encoding="utf-8"
+        )
+    )
+
+    entry = manifest[
+        "sources"
+    ][
+        "pkg/a.py"
+    ]
+
+    chunk_path = (
+        tmp_path
+        / entry[
+            "file"
+        ]
+    )
+
+    if failure == "missing_chunk":
+        chunk_path.unlink()
+
+    elif failure == "manifest_revision":
+        manifest[
+            "revision"
+        ] = 2
+        manifest_path.write_text(
+            json.dumps(
+                manifest,
+                indent=2,
+                sort_keys=True,
+            ),
+            encoding="utf-8",
+        )
+
+    elif failure == "corrupt_chunk":
+        chunk_path.write_bytes(
+            b"not-a-pickle"
+        )
+
+    assert (
+        load_snapshot(
+            tmp_path,
+            "sid",
+        )
+        is None
+    )
+
+
+def test_split_lineage_failed_metadata_commit_cleans_new_generation(
+    tmp_path,
+    monkeypatch,
+):
+    import contextor.core.live_state.store as store
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    baseline = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    candidate = state.clone_for_update()
+
+    original_replace = (
+        store.os.replace
+    )
+
+    def fail_metadata_replace(
+        source,
+        target,
+    ):
+        if (
+            Path(
+                target
+            ).name
+            == "engine_state.meta.json"
+        ):
+            raise RuntimeError(
+                "synthetic metadata commit failure"
+            )
+
+        return original_replace(
+            source,
+            target,
+        )
+
+    monkeypatch.setattr(
+        store.os,
+        "replace",
+        fail_metadata_replace,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match=(
+            "^synthetic metadata commit failure$"
+        ),
+    ):
+        save_snapshot(
+            candidate,
+            tmp_path,
+            "sid",
+            exact_revision=2,
+            file_state_payload={
+                "_meta": {
+                    "state_id": "sid",
+                    "revision": 2,
+                },
+                "files": {},
+            },
+        )
+
+    assert (
+        read_metadata(
+            tmp_path
+        ).revision
+        == baseline.revision
+    )
+
+    assert not list(
+        tmp_path.glob(
+            "engine_state.r2.*.pkl"
+        )
+    )
+    assert not list(
+        tmp_path.glob(
+            "file_state.r2.*.json"
+        )
+    )
+    assert not list(
+        tmp_path.glob(
+            "lineage_manifest.r2.*.json"
+        )
+    )
+    assert not list(
+        tmp_path.glob(
+            "lineage_source.r2.*.pkl"
+        )
+    )
+
+
+def test_schema_12_monolithic_snapshot_remains_loadable(
+    tmp_path,
+):
+    import json
+    import pickle
+
+    from contextor.core.analysis.state_manager import (
+        RepositoryAnalysisState,
+    )
+
+    state = RepositoryAnalysisState()
+    state.state_id = "legacy-sid"
+    state.revision = 1
+
+    state_file = (
+        "engine_state.r1.legacy.pkl"
+    )
+
+    metadata = {
+        "schema_version": "1.2",
+        "state_id": "legacy-sid",
+        "revision": 1,
+        "writer": "legacy",
+        "repo_id": "",
+        "root_path": "",
+        "state_file": state_file,
+        "file_state_file": "",
+    }
+
+    with (
+        tmp_path
+        / state_file
+    ).open("wb") as stream:
+        pickle.dump(
+            {
+                "metadata": metadata,
+                "state": state,
+            },
+            stream,
+        )
+
+    (
+        tmp_path
+        / "engine_state.meta.json"
+    ).write_text(
+        json.dumps(
+            metadata,
+            indent=2,
+        ),
+        encoding="utf-8",
+    )
+
+    loaded_state, loaded_metadata = (
+        load_snapshot(
+            tmp_path,
+            "legacy-sid",
+        )
+    )
+
+    assert (
+        loaded_metadata.schema_version
+        == "1.2"
+    )
+    assert (
+        loaded_metadata.lineage_manifest_file
+        == ""
+    )
+    assert (
+        loaded_state.state_id
+        == "legacy-sid"
+    )
+    assert (
+        loaded_state.revision
+        == 1
+    )
+
+
 def test_build_payload_is_side_effect_free(tmp_path):
     manager = FileStateManager(str(tmp_path))
     manager.state_id = "sid-r1"

```

## COMPLETION

STATUS=FINAL_PASS
LIVE_STATE_SCHEMA_VERSION=1.3
UNCHANGED_SLICE_REUSE_BY_IDENTITY=YES
EQUAL_DISTINCT_SLICE_REUSED=NO
CHANGED_SLICE_NEW_CHUNK=YES
UNCHANGED_SLICE_NEW_CHUNK=NO
FAILED_REVISION_DELETES_REUSED_PRIOR_CHUNK=NO
FAILED_PERSIST_ADVANCES_REUSE_BASELINE=NO
SUCCESSFUL_PERSIST_ADVANCES_REUSE_BASELINE=YES
FIRST_SPLIT_REVISION_WITHOUT_REUSABLE_PREDECESSOR_WRITES_ALL_CHUNKS=YES
SCHEMA_12_PREDECESSOR_REUSE=NO
CURRENT_SCHEMA_13_PREDECESSOR_REUSE=YES
CONTENT_HASH_REQUIRED_FOR_REUSE=NO
CONTENT_EQUALITY_USED_FOR_REUSE=NO
IPC_FILE_CHANGED=NO
IPC_SIGNATURE_CHANGED=NO
PERSISTER_PUBLIC_ARITY=2
PY_COMPILE=PASS
FIRST_TEST_GATE=PASS
TARGETED_TESTS=PASS
FULL_SUITE_RUN=NO
WORKSPACE_SYNC=verified
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
PERFORMANCE_CERTIFICATION=NOT_RUN
MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_PERFORMANCE_CERTIFICATION=YES
PRODUCTION_CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
