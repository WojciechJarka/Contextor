TASK: CONTEXTOR_C38P1_ATOMIC_PROFILER_FOUNDATION
STAGE: BLOCKER_RESOLUTION_AND_IMPLEMENTATION
HEAD_BEFORE: 8fbde208c4be32be1d6d32f759e7bda376032a1d
HEAD_AFTER: 8fbde208c4be32be1d6d32f759e7bda376032a1d
GIT_STATUS:
 M contextor/core/analysis/profile_worker.py
 M contextor/mcp/diagnostics.py
 M contextor/mcp/docs/contextor_profile_analysis.json
 M contextor/mcp/docs/index.json
 M contextor/mcp/tools/contextor_profile_analysis.py
 M tests/mcp/tools/test_contextor_profile_analysis.py
 M tests/test_mcp_diagnostics.py
 M tests/test_mcp_documentation.py
 M tests/test_profile_worker.py
 M walkthrough.md
?? contextor/core/profiling/
?? tests/test_atomic_profiler.py
?? tests/test_atomic_profiler_scopes.py

BLOCKER_RESOLUTION: Auditor approved local raw JSON validation in snapshot_metadata.py. Shared contextor/core/live_state/store.py remains unchanged.
LOCAL_RAW_REVISION_VALIDATION: The scope calls read_metadata under its named span; validate_identity reads engine_state.meta.json bytes twice, rejects differing bytes, parses the raw JSON object, requires type(revision) is int and revision > 0, matches the helper's revision, compares raw fields to the helper result, and verifies registered repo identity plus resolved root.
METADATA_CONSISTENCY_LIMITATIONS: Two equal validation reads and helper/raw field parity are a validated observation, not an exclusive generation lock or proof that durable revision matches LIVE.

CONTEXTOR_DISCOVERY_COVERAGE: Previous accepted discovery resolved adapter, worker, diagnostics, query helper, identity, paths, and LIVE modules via Contextor. This continuation fetched complete implementations for fuzzy_choice_candidates, inject_diagnostics_summary, _run_profile_subprocess, read_metadata, read_repository_identity, and connect. Exact lineage and call context identified the adapter -> subprocess -> worker -> legacy runner path. Contextor verified current production source at LIVE revision 568.
PRE_EDIT_FILES_AND_PLAN: The prior stage recorded full absolute target paths and responsibilities. The auditor's only correction was local raw revision validation in snapshot_metadata.py; no additional production file was authorized or edited.
MODULAR_ARCHITECTURE: New contextor/core/profiling package with recorder, immutable registry, runner, and three scope modules. One scope is selected per call.
STATIC_SCOPE_REGISTRY: Canonical order reports.summary, live.ping, snapshot.metadata; fixed presets, safety labels, execution kind, and callable. Unknown names cannot dispatch.
PUBLIC_MCP_SIGNATURE: async def contextor_profile_analysis(repo_path: str, exclude_paths: list[str] | None = None, mode: str = "full", scope: str | None = None, presets: list[str] | None = None, samples: int = 1, warmup: int = 0, result_view: str = "summary") -> str.
ATOMIC_RECORDER_IMPLEMENTATION: Selected spans use perf_counter_ns and record preset, iteration, duration_ns, status. Exception status is recorded and original exception re-raised. Record limit 30.
PRESET_SELECTION_SEMANTICS: Selected presets control timing only. Scope steps execute in fixed order regardless of selection.
DISABLED_PRESET_PROOF: nullcontext returns without timer read; focused test replaces timer with a failing callable and proves enclosed operation executes with zero records.
LEGACY_FULL_COMPATIBILITY: Existing full request remains exactly repo_path plus exclude_paths. Worker dispatches unchanged run_analysis_profile for payloads without mode. Existing FULL result formatting and subprocess lifecycle remain. Focused regression verified payload.
CATALOG_MODE: Builds static registry locally without subprocess, LIVE, report, or snapshot reads.
PROBE_MODE: Adapter validates then sends one explicit request to the existing worker, which validates again and calls run_probe. No FULL analysis is called.
REPORTS_SCOPE: Resolves output_dir()/root.name_summary.json, checks regular file/path containment, reads bytes, JSON-decodes, and returns only bounded historical metadata. Missing and invalid JSON are explicit failures.
LIVE_PING_SCOPE: Calls connect, never connect_or_start, then one ping. Validates status and nonnegative nonbool revision. No publication or ownership claim.
SNAPSHOT_METADATA_SCOPE: Uses registered repository identity, repo_cache_dir, read_metadata, and approved double raw-metadata validation. No load_snapshot, lineage chunk read, or validation-cache write.
SMART_FUZZY_INPUT_GUIDANCE: Invalid finite names use shared fuzzy_choice_candidates; candidates are suggestions only. Wrong-scope preset returns owning_scope. Invalid requests are rejected before spawn.
INVALID_INPUT_NO_SPAWN_PROOF: Focused adapter tests monkeypatch subprocess creation to fail and exercise catalog plus invalid mode/scope/preset/duplicate/count combinations.
SAMPLE_STATISTICS: Separate wall and per-preset count/min/median/max/p95 in milliseconds. p95 is null for count<5 and nearest-rank for count>=5. Failed operations do not become successful samples and missing spans are not zero-filled.
WARMUP_EXCLUSION: Warmup uses an unselected recorder; failures stop measurement. Focused test proves no measured samples run afterward.
OUTPUT_SIZE_LIMIT: Runner measures UTF-8 JSON size against 15 KiB and returns confirmation_required with estimated bytes and summary suggestion on overflow. Summary contains no individual spans; spans returns selected records only.
DIAGNOSTICS_NOISE_GATE: inject_diagnostics_summary returns contextor-atomic-profile/v1 results unchanged for contextor_profile_analysis; legacy FULL path remains.
PROCESS_OWNERSHIP: Existing process registry route is retained.
SUBPROCESS_CLEANUP: Existing cancellation/termination/bounded wait remains unchanged.

TARGETED_TEST_RESULTS: Named focused selection (test_atomic_profiler.py, test_atomic_profiler_scopes.py, test_profile_worker.py, test_profile_runner.py, test_profile_analysis.py, test_mcp_profile_worker_lifecycle.py, test_mcp_documentation.py, test_mcp_diagnostics.py, tests/mcp/tools/test_contextor_profile_analysis.py): 136 passed, 1 third-party AuthlibDeprecationWarning. Final atomic.py edit was separately verified: test_atomic_profiler.py 12 passed. No full repository pytest; no production FULL, snapshot hydration, or LIVE publication.
LIVE_REVISION_BEFORE_AFTER: 542 -> 568, continuous event history, resync_required=false.
WATCHER_EVENTS: desktop_watcher UPDATED production files at revisions 543 (__init__), 544 (atomic), 545 (live_ipc), 546 (reports), 547 (snapshot_metadata), 548 (scopes/__init__), 549 (registry), 550 (runner), 551 (MCP adapter), 552 (worker), 553 (diagnostics), 564 (snapshot_metadata latest edits), 568 (atomic latest edit). Later UNCHANGED events reflected duplicate/coalesced notifications. Python test files also received watcher updates. Documentation JSON is not a canonical Python module and has no corresponding Python watcher revision.
WORKSPACE_SYNC: Contextor get_symbol_implementation preview reported workspace_sync=verified for every changed symbol-bearing production Python file at revision 567; atomic.py rechecked verified at revision 568. Package __init__.py files were confirmed by UPDATED watcher events. Documentation and tests were checked by focused tests; exact source/test/docs contents are represented in FULL_DIFFS.
MCP_BACKEND_RESTART_REQUIRED=YES
MCP_BACKEND_RESTART_PERFORMED=NO
SERVING_RUNTIME_ADOPTION=PENDING
E2_PUBLICATION_TIMEOUT_REMAINS_OPEN=YES
FINAL_VERDICT: C38P1_SOURCE_PASS_PENDING_RUNTIME

FILES_CHANGED:
C:\Temp\Contextor_Repo\contextor\core\profiling\__init__.py
C:\Temp\Contextor_Repo\contextor\core\profiling\atomic.py
C:\Temp\Contextor_Repo\contextor\core\profiling\registry.py
C:\Temp\Contextor_Repo\contextor\core\profiling\runner.py
C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\__init__.py
C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\reports.py
C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\live_ipc.py
C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\snapshot_metadata.py
C:\Temp\Contextor_Repo\contextor\mcp\tools\contextor_profile_analysis.py
C:\Temp\Contextor_Repo\contextor\core\analysis\profile_worker.py
C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py
C:\Temp\Contextor_Repo\contextor\mcp\docs\contextor_profile_analysis.json
C:\Temp\Contextor_Repo\contextor\mcp\docs\index.json
C:\Temp\Contextor_Repo\tests\test_atomic_profiler.py
C:\Temp\Contextor_Repo\tests\test_atomic_profiler_scopes.py
C:\Temp\Contextor_Repo\tests\test_profile_worker.py
C:\Temp\Contextor_Repo\tests\test_mcp_diagnostics.py
C:\Temp\Contextor_Repo\tests\test_mcp_documentation.py
C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_profile_analysis.py

FULL_DIFFS (exact complete per-file diffs; walkthrough.md excluded):

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\__init__.py
diff --git a/contextor/core/profiling/__init__.py b/contextor/core/profiling/__init__.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/__init__.py
@@ -0,0 +1 @@
+"""Bounded atomic profiling of explicitly registered operations."""

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\atomic.py
diff --git a/contextor/core/profiling/atomic.py b/contextor/core/profiling/atomic.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/atomic.py
@@ -0,0 +1,54 @@
+"""In-memory timing spans for one measured operation iteration."""
+
+from contextlib import contextmanager, nullcontext
+from time import perf_counter_ns
+
+
+MAX_RECORDS = 30
+
+
+class AtomicRecorder:
+    def __init__(self, scope: str, selected_presets: frozenset[str], iteration: int):
+        from contextor.core.profiling.registry import get_scope
+
+        spec = get_scope(scope)
+        if spec is None or not selected_presets.issubset(spec.presets):
+            raise ValueError("Unknown scope or preset.")
+        if type(iteration) is not int or iteration < 0:
+            raise ValueError("Invalid iteration.")
+        self.scope = scope
+        self.selected_presets = selected_presets
+        self.iteration = iteration
+        self._records: list[dict[str, object]] = []
+
+    def span(self, preset_name: str):
+        from contextor.core.profiling.registry import get_scope
+
+        if preset_name not in get_scope(self.scope).presets:
+            raise ValueError("Unknown preset.")
+        if preset_name not in self.selected_presets:
+            return nullcontext()
+
+        @contextmanager
+        def measured():
+            if len(self._records) >= MAX_RECORDS:
+                raise RuntimeError("Atomic record limit exceeded.")
+            start = perf_counter_ns()
+            status = "ok"
+            try:
+                yield
+            except BaseException:
+                status = "failed"
+                raise
+            finally:
+                self._records.append({
+                    "preset": preset_name,
+                    "iteration": self.iteration,
+                    "duration_ns": perf_counter_ns() - start,
+                    "status": status,
+                })
+
+        return measured()
+
+    def records(self) -> tuple[dict[str, object], ...]:
+        return tuple(dict(record) for record in self._records)

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\registry.py
diff --git a/contextor/core/profiling/registry.py b/contextor/core/profiling/registry.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/registry.py
@@ -0,0 +1,64 @@
+"""Closed, ordered registry of safe initial atomic operations."""
+
+from dataclasses import dataclass
+from typing import Callable
+from pathlib import Path
+
+from contextor.core.profiling.scopes import reports, live_ipc, snapshot_metadata
+
+SCHEMA = "contextor-atomic-profile/v1"
+
+
+@dataclass(frozen=True)
+class ScopeSpec:
+    name: str
+    description: str
+    presets: tuple[str, ...]
+    safety: str
+    execution_kind: str
+    run_scope: Callable
+
+
+_SCOPES = (
+    ScopeSpec("reports.summary", "Read and JSON-decode the existing summary report.",
+              reports.PRESETS, "READ_WITH_OS_CACHE_EFFECTS", "INDEPENDENT_OPERATION", reports.run_scope),
+    ScopeSpec("live.ping", "Connect to the existing authoritative LIVE service and perform one read-only ping.",
+              live_ipc.PRESETS, "LIVE_READ_WITH_TRANSPORT_TELEMETRY", "INDEPENDENT_OPERATION", live_ipc.run_scope),
+    ScopeSpec("snapshot.metadata", "Read and validate committed snapshot metadata.",
+              snapshot_metadata.PRESETS, "READ_WITH_OS_CACHE_EFFECTS", "INDEPENDENT_OPERATION",
+              snapshot_metadata.run_scope),
+)
+
+
+def get_scope(name: str) -> ScopeSpec | None:
+    return next((scope for scope in _SCOPES if scope.name == name), None)
+
+
+def list_scopes() -> tuple[ScopeSpec, ...]:
+    return _SCOPES
+
+
+def validate_scope_presets(scope: str, presets: list[str]) -> tuple[str, ...]:
+    spec = get_scope(scope)
+    if spec is None:
+        raise ValueError("Unknown scope.")
+    if not isinstance(presets, list) or not presets:
+        raise ValueError("Presets must be a nonempty list.")
+    if any(not isinstance(item, str) or item not in spec.presets for item in presets):
+        raise ValueError("Unknown or wrong-scope preset.")
+    if len(set(presets)) != len(presets):
+        raise ValueError("Duplicate preset.")
+    return tuple(item for item in spec.presets if item in presets)
+
+
+def build_catalog() -> dict[str, object]:
+    return {
+        "schema": SCHEMA,
+        "status": "ok",
+        "mode": "catalog",
+        "scopes": [
+            {"name": item.name, "description": item.description, "presets": list(item.presets),
+             "safety": item.safety, "execution_kind": item.execution_kind}
+            for item in _SCOPES
+        ],
+    }

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\runner.py
diff --git a/contextor/core/profiling/runner.py b/contextor/core/profiling/runner.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/runner.py
@@ -0,0 +1,144 @@
+"""Sequential bounded runner for one registered atomic operation."""
+
+import math
+import statistics
+from pathlib import Path
+from time import perf_counter_ns
+
+from contextor.core.profiling.atomic import AtomicRecorder
+from contextor.core.profiling.registry import SCHEMA, get_scope, validate_scope_presets
+
+MAX_OUTPUT_BYTES = 15 * 1024
+
+
+def validate_probe_request(scope: object, presets: object, samples: object, warmup: object,
+                           result_view: object) -> tuple[str, ...]:
+    if not isinstance(scope, str) or get_scope(scope) is None:
+        raise ValueError("Unknown profiling scope.")
+    selected = validate_scope_presets(scope, presets)
+    if type(samples) is not int or not 1 <= samples <= 10:
+        raise ValueError("samples must be an integer from 1 to 10.")
+    if type(warmup) is not int or not 0 <= warmup <= 3:
+        raise ValueError("warmup must be an integer from 0 to 3.")
+    if result_view not in ("summary", "spans"):
+        raise ValueError("Invalid result_view.")
+    return selected
+
+
+def _stats(values: list[int]) -> dict[str, object]:
+    ms = sorted(value / 1_000_000 for value in values)
+    return {
+        "count": len(ms),
+        "min_ms": min(ms) if ms else None,
+        "median_ms": statistics.median(ms) if ms else None,
+        "max_ms": max(ms) if ms else None,
+        "p95_ms": ms[math.ceil(.95 * len(ms)) - 1] if len(ms) >= 5 else None,
+    }
+
+
+def _safe_failure(exc: Exception) -> dict[str, str]:
+    return {"category": type(exc).__name__[:80], "reason": "scope_operation_failed"}
+
+
+def _consistency(scope: str, revisions: list[int]) -> dict[str, object]:
+    if scope == "reports.summary":
+        return {"status": "historical_unverified"}
+    if scope == "snapshot.metadata":
+        return {"status": "durable_metadata_only"}
+    if not revisions:
+        return {"status": "unverified"}
+    return {"status": "revision_changed" if len(set(revisions)) > 1 else "observed_revisions_equal",
+            "observed_revisions": revisions}
+
+
+def _base(scope: str, selected: tuple[str, ...], samples: int, warmup: int,
+          result_view: str) -> dict[str, object]:
+    return {
+        "schema": SCHEMA, "mode": "probe", "scope": scope,
+        "selected_presets": list(selected), "samples": samples, "warmup": warmup,
+        "result_view": result_view,
+        "measurement": {
+            "timing_unit": "ms", "clock": "perf_counter_ns",
+            "absolute_wall_authoritative": False, "includes_worker_startup": False,
+            "measurement_atomicity": "timing_span_only",
+        },
+    }
+
+
+def run_probe(repo_path: str | Path, scope: str, presets: list[str], samples: int,
+              warmup: int, result_view: str) -> dict[str, object]:
+    selected = validate_probe_request(scope, presets, samples, warmup, result_view)
+    root = Path(repo_path).expanduser().resolve()
+    if not root.is_dir():
+        raise ValueError("Repository root must exist.")
+    spec = get_scope(scope)
+    base = _base(scope, selected, samples, warmup, result_view)
+    for index in range(warmup):
+        try:
+            outcome = spec.run_scope(root, AtomicRecorder(scope, frozenset(), index))
+        except Exception as exc:
+            failure = _safe_failure(exc)
+            return {**base, "status": "warmup_failed", "wall": _stats([]),
+                    "presets": {name: _stats([]) for name in selected},
+                    "consistency": _consistency(scope, []),
+                    "outcomes": {"successful": 0, "failed": 0, "iterations": [],
+                                 "warmup_failure": failure}}
+        if outcome.get("status") != "ok":
+            return {**base, "status": "warmup_failed", "wall": _stats([]),
+                    "presets": {name: _stats([]) for name in selected},
+                    "consistency": _consistency(scope, []),
+                    "outcomes": {"successful": 0, "failed": 0, "iterations": [],
+                                 "warmup_failure": {"category": outcome.get("status"),
+                                                    "reason": outcome.get("reason")}}}
+
+    walls: list[int] = []
+    durations: dict[str, list[int]] = {name: [] for name in selected}
+    span_records: list[dict[str, object]] = []
+    outcomes: list[dict[str, object]] = []
+    revisions: list[int] = []
+    for index in range(samples):
+        recorder = AtomicRecorder(scope, frozenset(selected), index)
+        start = perf_counter_ns()
+        try:
+            outcome = spec.run_scope(root, recorder)
+        except Exception as exc:
+            outcome = {"status": "failed", **_safe_failure(exc)}
+        elapsed = perf_counter_ns() - start
+        status = outcome.get("status", "failed")
+        if status == "ok":
+            walls.append(elapsed)
+            if type(outcome.get("observed_revision")) is int:
+                revisions.append(outcome["observed_revision"])
+        public_fields = ("reason", "category", "bytes_read", "json_root_type", "data_source",
+                         "live_binding_verified", "observed_revision", "operation",
+                         "durable_revision", "snapshot_schema_version", "identity_verified")
+        outcomes.append({"iteration": index, "status": status,
+                         **{key: outcome[key] for key in public_fields if key in outcome}})
+        for record in recorder.records():
+            if record["status"] == "ok" and status == "ok":
+                durations[record["preset"]].append(record["duration_ns"])
+            if result_view == "spans":
+                span_records.append({"preset": record["preset"], "iteration": index,
+                                     "duration_ms": record["duration_ns"] / 1_000_000,
+                                     "status": record["status"]})
+
+    successes = len(walls)
+    consistency = _consistency(scope, revisions)
+    result = {
+        **base,
+        "status": "ok" if successes == samples else "partial" if successes else "failed",
+        "wall": _stats(walls),
+        "presets": {name: _stats(durations[name]) for name in selected},
+        "consistency": consistency,
+        "outcomes": {"successful": successes, "failed": samples - successes, "iterations": outcomes},
+    }
+    if result_view == "spans":
+        result["spans"] = span_records
+    import json
+    size = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
+    if size > MAX_OUTPUT_BYTES:
+        return {"schema": SCHEMA, "status": "confirmation_required", "mode": "probe",
+                "estimated_bytes": size, "size_limit": MAX_OUTPUT_BYTES,
+                "suggested_result_view": "summary", "scope": scope,
+                "selected_presets": list(selected)}
+    return result

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\__init__.py
diff --git a/contextor/core/profiling/scopes/__init__.py b/contextor/core/profiling/scopes/__init__.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/scopes/__init__.py
@@ -0,0 +1 @@
+"""Fixed, read-only atomic profiling operations."""

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\reports.py
diff --git a/contextor/core/profiling/scopes/reports.py b/contextor/core/profiling/scopes/reports.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/scopes/reports.py
@@ -0,0 +1,33 @@
+"""Historical summary-report read probe."""
+
+import json
+from pathlib import Path
+
+from contextor.core.paths import output_dir
+
+PRESETS = ("resolve_path", "read_bytes", "json_decode")
+
+
+def run_scope(root: Path, recorder) -> dict[str, object]:
+    with recorder.span("resolve_path"):
+        base = output_dir().resolve()
+        path = base / f"{root.name}_summary.json"
+        if path.name != f"{root.name}_summary.json" or path.resolve().parent != base or not path.is_file():
+            return {"status": "unavailable", "reason": "summary_report_unavailable"}
+    try:
+        with recorder.span("read_bytes"):
+            content = path.read_bytes()
+    except OSError:
+        return {"status": "unavailable", "reason": "summary_report_unavailable"}
+    try:
+        with recorder.span("json_decode"):
+            parsed = json.loads(content.decode("utf-8"))
+    except (UnicodeError, json.JSONDecodeError):
+        return {"status": "invalid_data", "reason": "invalid_summary_json"}
+    return {
+        "status": "ok",
+        "bytes_read": len(content),
+        "json_root_type": type(parsed).__name__,
+        "data_source": "historical_report",
+        "live_binding_verified": False,
+    }

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\live_ipc.py
diff --git a/contextor/core/profiling/scopes/live_ipc.py b/contextor/core/profiling/scopes/live_ipc.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/scopes/live_ipc.py
@@ -0,0 +1,27 @@
+"""Existing-authority read-only ping probe."""
+
+from pathlib import Path
+
+from contextor.core.live_state import connect
+
+PRESETS = ("connect", "ping")
+
+
+def run_scope(root: Path, recorder) -> dict[str, object]:
+    with recorder.span("connect"):
+        client = connect(root)
+    if client is None:
+        return {"status": "unavailable", "reason": "live_authority_unavailable"}
+    with recorder.span("ping"):
+        response = client.ping()
+    if not isinstance(response, dict) or response.get("status") != "ok":
+        return {"status": "invalid_data", "reason": "invalid_ping_response"}
+    revision = response.get("revision")
+    if type(revision) is not int or revision < 0:
+        return {"status": "invalid_data", "reason": "invalid_ping_revision"}
+    return {
+        "status": "ok",
+        "observed_revision": revision,
+        "operation": "ping",
+        "data_source": "live_authority",
+    }

FILE: C:\Temp\Contextor_Repo\contextor\core\profiling\scopes\snapshot_metadata.py
diff --git a/contextor/core/profiling/scopes/snapshot_metadata.py b/contextor/core/profiling/scopes/snapshot_metadata.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/profiling/scopes/snapshot_metadata.py
@@ -0,0 +1,67 @@
+"""Validated observation of committed metadata without snapshot hydration."""
+
+import json
+from pathlib import Path
+
+from contextor.core.paths import repo_cache_dir
+from contextor.core.repository_identity import read_repository_identity
+from contextor.core.live_state.store import LIVE_STATE_SCHEMA_VERSION, read_metadata
+
+PRESETS = ("resolve_cache", "read_metadata", "validate_identity")
+SCHEMAS = frozenset({"1.0", "1.1", "1.2", "1.3", LIVE_STATE_SCHEMA_VERSION})
+
+
+def run_scope(root: Path, recorder) -> dict[str, object]:
+    with recorder.span("resolve_cache"):
+        identity = read_repository_identity(root)
+        if identity is None:
+            return {"status": "unavailable", "reason": "repository_not_registered"}
+        cache_dir = repo_cache_dir(root)
+    with recorder.span("read_metadata"):
+        try:
+            metadata = read_metadata(cache_dir)
+        except (AttributeError, OSError, TypeError, ValueError):
+            return {"status": "invalid_data", "reason": "metadata_unreadable"}
+    if metadata is None:
+        return {"status": "unavailable", "reason": "metadata_unavailable"}
+    with recorder.span("validate_identity"):
+        path = cache_dir / "engine_state.meta.json"
+        try:
+            first = path.read_bytes()
+            second = path.read_bytes()
+        except OSError:
+            return {"status": "invalid_data", "reason": "metadata_unreadable"}
+        if first != second:
+            return {"status": "changed_during_read", "reason": "metadata_changed"}
+        try:
+            raw = json.loads(first.decode("utf-8"))
+        except (UnicodeError, json.JSONDecodeError):
+            return {"status": "invalid_data", "reason": "metadata_unreadable"}
+        if not isinstance(raw, dict):
+            return {"status": "invalid_data", "reason": "metadata_not_object"}
+        revision = raw.get("revision")
+        if type(revision) is not int or revision <= 0 or revision != metadata.revision:
+            return {"status": "invalid_data", "reason": "invalid_raw_revision"}
+        defaults = {
+            "schema_version": "1.0", "state_id": "", "writer": "legacy",
+            "repo_id": "", "root_path": "", "state_file": "",
+            "file_state_file": "", "lineage_manifest_file": "",
+        }
+        if any(raw.get(key, default) != getattr(metadata, key)
+               for key, default in defaults.items()):
+            return {"status": "invalid_identity", "reason": "metadata_field_mismatch"}
+        if not metadata.state_id or metadata.schema_version not in SCHEMAS:
+            return {"status": "invalid_identity", "reason": "metadata_identity_invalid"}
+        try:
+            matches = metadata.repo_id == identity.repo_id and Path(metadata.root_path).expanduser().resolve() == root.resolve()
+        except (OSError, ValueError, TypeError):
+            matches = False
+        if not matches:
+            return {"status": "invalid_identity", "reason": "metadata_identity_mismatch"}
+    return {
+        "status": "ok",
+        "durable_revision": revision,
+        "snapshot_schema_version": metadata.schema_version,
+        "identity_verified": True,
+        "data_source": "durable_snapshot_metadata",
+    }

FILE: C:\Temp\Contextor_Repo\contextor\mcp\tools\contextor_profile_analysis.py
diff --git a/contextor/mcp/tools/contextor_profile_analysis.py b/contextor/mcp/tools/contextor_profile_analysis.py
index 73f7653..eb5f1c1 100644
--- a/contextor/mcp/tools/contextor_profile_analysis.py
+++ b/contextor/mcp/tools/contextor_profile_analysis.py
@@ -4,6 +4,10 @@ import os
 import sys
 from pathlib import Path
 
+from contextor.core.profiling.registry import SCHEMA, build_catalog, get_scope, list_scopes, validate_scope_presets
+from contextor.core.profiling.runner import validate_probe_request
+from contextor.mcp.query_helpers import fuzzy_choice_candidates
+
 from contextor.mcp_process_registry import (
     register_process,
     remove_record,
@@ -88,6 +92,7 @@ async def _run_profile_subprocess(
     root: Path,
     *,
     exclude_paths: list[str] | None,
+    probe_request: dict[str, object] | None = None,
 ) -> dict[str, object]:
     process = await asyncio.create_subprocess_exec(
         sys.executable,
@@ -115,11 +120,14 @@ async def _run_profile_subprocess(
                 executable=sys.executable,
             )
 
-        request = json.dumps(
+        request_payload = (
             {
                 "repo_path": str(root),
                 "exclude_paths": exclude_paths,
-            },
+            } if probe_request is None else {"repo_path": str(root), **probe_request}
+        )
+        request = json.dumps(
+            request_payload,
             ensure_ascii=False,
             separators=(",", ":"),
         ).encode("utf-8")
@@ -175,7 +183,64 @@ async def _run_profile_subprocess(
 async def contextor_profile_analysis(
     repo_path: str,
     exclude_paths: list[str] | None = None,
+    mode: str = "full",
+    scope: str | None = None,
+    presets: list[str] | None = None,
+    samples: int = 1,
+    warmup: int = 0,
+    result_view: str = "summary",
 ) -> str:
+    def invalid(parameter: str, value: object, reason: str, allowed: list[str] | None = None,
+                owner: str | None = None) -> str:
+        result: dict[str, object] = {
+            "schema": SCHEMA, "status": "invalid_profile_request", "parameter": parameter,
+            "invalid_value": value[:120] if isinstance(value, str) else value if isinstance(value, (int, float, bool, type(None))) else str(type(value).__name__),
+            "reason": reason, "similar_candidates": fuzzy_choice_candidates(value, allowed or []) if isinstance(value, str) else [],
+            "allowed_values": allowed or [], "retry_instruction": "Choose an exact supported value.",
+            "documentation_hint": "get_mcp_documentation",
+        }
+        if owner is not None:
+            result["owning_scope"] = owner
+        return json.dumps(result, ensure_ascii=False)
+
+    if not isinstance(mode, str) or mode not in ("full", "catalog", "probe"):
+        return invalid("mode", mode, "Unsupported profiling mode.", ["full", "catalog", "probe"])
+    if not isinstance(repo_path, str) or not repo_path.strip():
+        return invalid("repo_path", repo_path, "Repository path must be a nonempty string.")
+    if mode == "full":
+        if scope is not None or presets is not None or samples != 1 or type(samples) is not int or warmup != 0 or type(warmup) is not int or result_view != "summary":
+            return invalid("mode", mode, "FULL mode does not accept probe parameters.")
+        if exclude_paths is not None and (not isinstance(exclude_paths, list) or
+                                          any(not isinstance(item, str) or not item.strip() for item in exclude_paths)):
+            return invalid("exclude_paths", exclude_paths, "Invalid exclusions.")
+    else:
+        if exclude_paths is not None:
+            return invalid("exclude_paths", exclude_paths, "Exclusions are valid only for FULL mode.")
+        if mode == "catalog":
+            if scope is not None or presets is not None or samples != 1 or type(samples) is not int or warmup != 0 or type(warmup) is not int or result_view != "summary":
+                return invalid("mode", mode, "Catalog does not accept probe parameters.")
+            return json.dumps(build_catalog(), ensure_ascii=False)
+        if scope is None:
+            return invalid("scope", scope, "A scope is required.", [item.name for item in list_scopes()])
+        if not isinstance(scope, str) or get_scope(scope) is None:
+            return invalid("scope", scope, "Unsupported profiling scope.", [item.name for item in list_scopes()])
+        if not isinstance(presets, list) or not presets:
+            return invalid("presets", presets, "Explicit nonempty preset selection required.", list(get_scope(scope).presets))
+        if any(not isinstance(item, str) for item in presets):
+            return invalid("presets", presets, "Presets must be strings.", list(get_scope(scope).presets))
+        if len(set(presets)) != len(presets):
+            return invalid("presets", presets, "Duplicate preset.", list(get_scope(scope).presets))
+        for preset in presets:
+            if preset not in get_scope(scope).presets:
+                owner = next((item.name for item in list_scopes() if preset in item.presets), None)
+                return invalid("presets", preset, "Preset does not belong to selected scope.", list(get_scope(scope).presets), owner)
+        if type(samples) is not int or not 1 <= samples <= 10:
+            return invalid("samples", samples, "samples must be an integer from 1 to 10.")
+        if type(warmup) is not int or not 0 <= warmup <= 3:
+            return invalid("warmup", warmup, "warmup must be an integer from 0 to 3.")
+        if not isinstance(result_view, str) or result_view not in ("summary", "spans"):
+            return invalid("result_view", result_view, "Unsupported result view.", ["summary", "spans"])
+        validated_presets = list(validate_probe_request(scope, presets, samples, warmup, result_view))
     root = Path(repo_path).expanduser().resolve()
     if not root.is_dir():
         return (
@@ -186,11 +251,14 @@ async def contextor_profile_analysis(
     profile = await _run_profile_subprocess(
         root,
         exclude_paths=exclude_paths,
+        **({"probe_request": {
+            "mode": "probe", "scope": scope, "presets": validated_presets,
+            "samples": samples, "warmup": warmup, "result_view": result_view,
+        }} if mode == "probe" else {}),
     )
-    return json.dumps(
-        profile,
-        indent=2,
-    )
+    if mode == "probe":
+        return json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
+    return json.dumps(profile, indent=2)
 
 
 __all__ = [

FILE: C:\Temp\Contextor_Repo\contextor\core\analysis\profile_worker.py
diff --git a/contextor/core/analysis/profile_worker.py b/contextor/core/analysis/profile_worker.py
index 5b874bf..d2c96c5 100644
--- a/contextor/core/analysis/profile_worker.py
+++ b/contextor/core/analysis/profile_worker.py
@@ -5,10 +5,21 @@ import sys
 from pathlib import Path
 from typing import Any
 from contextor.core.analysis.profile_runner import run_analysis_profile
+from contextor.core.profiling.runner import run_probe, validate_probe_request
 def execute_profile_request(payload: object) -> dict[str, object]:
     if not isinstance(payload, dict): raise ValueError("profile worker request must be a JSON object")
     repo_path = payload.get("repo_path")
     if not isinstance(repo_path, str) or not repo_path.strip(): raise ValueError("repo_path must be a non-empty string")
+    mode = payload.get("mode", "full")
+    if mode == "probe":
+        if set(payload) != {"repo_path", "mode", "scope", "presets", "samples", "warmup", "result_view"}:
+            raise ValueError("Invalid probe worker request fields.")
+        scope = payload["scope"]; presets = payload["presets"]
+        samples = payload["samples"]; warmup = payload["warmup"]; result_view = payload["result_view"]
+        validate_probe_request(scope, presets, samples, warmup, result_view)
+        return run_probe(Path(repo_path), scope, presets, samples, warmup, result_view)
+    if mode != "full" or "mode" in payload:
+        raise ValueError("Invalid legacy FULL worker request.")
     exclude_paths = payload.get("exclude_paths")
     if exclude_paths is not None and (not isinstance(exclude_paths, list) or not all(isinstance(item, str) and item.strip() for item in exclude_paths)): raise ValueError("exclude_paths must be null or an array of non-empty strings")
     return run_analysis_profile(Path(repo_path), exclude_paths=exclude_paths)

FILE: C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index 766e823..489d2ed 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -183,6 +183,8 @@ def inject_diagnostics_summary(
         return result
     if not isinstance(payload, dict):
         return result
+    if tool_name == "contextor_profile_analysis" and payload.get("schema") == "contextor-atomic-profile/v1":
+        return result
     if payload.get("status") in {
         "error",
         "queued",

FILE: C:\Temp\Contextor_Repo\contextor\mcp\docs\contextor_profile_analysis.json
diff --git a/contextor/mcp/docs/contextor_profile_analysis.json b/contextor/mcp/docs/contextor_profile_analysis.json
index 9683b78..cf89051 100644
--- a/contextor/mcp/docs/contextor_profile_analysis.json
+++ b/contextor/mcp/docs/contextor_profile_analysis.json
@@ -1,11 +1,43 @@
 {
   "version": "1.0.0",
   "tool": "contextor_profile_analysis",
-  "purpose": ["Run one repository-wide diagnostic profile through the real production full-analysis path and return a compact, deterministic breakdown of where the analysis spends time and which structured evidence explains known bottlenecks."],
-  "parameters": ["repo_path (string, required): canonical repository root to profile.", "exclude_paths (array of strings or null, optional, default null): additional per-run repository-relative exclusions forwarded unchanged to the production full-analysis path."],
-  "behavior": ["1. The MCP coroutine launches a dedicated Contextor profile worker process so the MCP event loop does not execute the synchronous analysis body and the worker's normal full-analysis ProcessPool is isolated from the MCP server process.\n2. The runner attempts the existing canonical full-analysis writer with timeout=0.0; if another writer already owns the repository, status=busy with reason_code=full_analysis_busy is returned instead of waiting and contaminating the sample.\n3. Evidence is captured in memory from the existing runtime trace path under one scoped profile operation; the tool creates no second trace session and reads no JSONL.\n4. Bottleneck ranking uses only FULL_ANALYSIS_STAGE_END critical-path wall timings. Aggregate worker/file-task sums are reported separately and never participate in that ranking.\n5. The wide stages identity_and_setup, reports, canonical_materialization, persistence, and live_publish emit non-overlapping structured stage-component evidence; the profiler selects the dominant measured component or measured residual, while canonical lineage retains nested lineage attribution."],
-  "freshness": ["The tool executes a real full repository analysis and therefore refreshes the same canonical analysis state and LIVE publication path as the normal production full-analysis owner when the run succeeds.", "The returned profile describes only the analysis executed by this call. It is not a historical profiler report and is not persisted as a separate profiling artifact."],
-  "errors": ["A missing or non-directory repo_path returns an Error string before starting the profile runner.", "status=busy with reason_code=full_analysis_busy means another canonical full-analysis writer already owns the repository; retry later rather than treating the result as a performance sample.", "status=incomplete means required structured profile evidence was missing or duplicated.", "status=invalid_evidence means captured timing/evidence contracts were internally inconsistent.", "Unexpected production analysis failures propagate through the normal central MCP wrapper and are not converted into profiler guesses."],
-  "usage_notes": ["Use this tool to identify which analysis stages dominate and why, not to establish clean-machine absolute benchmark time. The response explicitly marks absolute_wall_authoritative=false because caller/runtime load can inflate wall duration.", "One run is normally sufficient for architectural diagnosis. Repeat only when confirming a specific optimization or investigating unstable evidence.", "Do not add aggregate source_parse_sum_ms, cache_get_sum_ms, or lineage_extract_sum_ms to critical-path stage durations; those values are aggregate file-task diagnostics and may exceed wall time under parallel execution.", "stage_attribution returns component timings, component_sum_ms, residual_ms, coverage_pct, and dominant_component for identity_and_setup, reports, canonical_materialization, persistence, and live_publish.", "residual_ms is the critical-path portion of a stage not covered by named components and must not be heuristically allocated.", "warm_cache_fast_path means every indexed file task was a cache hit with valid cached lineage and no AST source parse call; it does not imply that the whole indexing stage is cheap because cache I/O, process-pool, IPC, scheduling, and aggregation costs may remain."],
-  "examples": ["Call contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\") and inspect bottlenecks first. Evidence-backed reason_code examples include artifact_pipeline_cost, lineage_reuse_gate_cost, live_publish_ipc_cost, repository_identity_cost, snapshot_save_cost, and warm_cache_fast_path."]
+  "purpose": ["Profile the legacy full analysis or measure selected spans in one registered read operation."],
+  "parameters": [
+    "repo_path (string, required): repository root.",
+    "exclude_paths (array of strings or null, default null): legacy FULL exclusions only.",
+    "mode (full|catalog|probe, default full): full preserves the original worker and contextor-profile-analysis/v1 result; catalog returns static capabilities without worker or repository reads; probe executes one selected operation.",
+    "scope (string or null, default null): required for probe; one of reports.summary, live.ping, snapshot.metadata.",
+    "presets (array of strings or null, default null): explicit nonempty selection from the selected scope; controls timing only, not execution.",
+    "samples (integer 1..10, default 1): sequential measured iterations; booleans rejected.",
+    "warmup (integer 0..3, default 0): sequential iterations excluded from statistics; booleans rejected.",
+    "result_view (summary|spans, default summary): aggregated statistics or bounded individual selected spans."
+  ],
+  "behavior": [
+    "The first two positional arguments and legacy FULL worker request remain unchanged. FULL launches the original full-analysis worker and may publish canonical state.",
+    "Catalog is static and bounded. Probe validates before spawning one existing profile-worker process; the worker validates again and runs no full analysis.",
+    "reports.summary reads the existing historical report with OS cache effects; it does not prove current canonical identity.",
+    "live.ping connects only to an existing verified authority and performs a read-only ping; transport telemetry and scheduling effects remain possible.",
+    "snapshot.metadata reads committed metadata, validates raw JSON identity and revision, and never hydrates a snapshot or lineage cache. Matching reads are an observation, not an exclusive generation lock.",
+    "Each scope executes all operation steps regardless of selected presets. Unselected spans produce no timing records. Total wall and individual preset timings are independent.",
+    "Responses use contextor-atomic-profile/v1 for catalog/probe and contextor-profile-analysis/v1 for FULL. Probe p95 is nearest-rank when count >=5 and null otherwise.",
+    "Atomic results are limited to 15 KiB UTF-8. Oversized detail returns confirmation_required with estimated size and a summary-view suggestion.",
+    "Invalid finite choices receive suggestion-only candidates from fuzzy_choice_candidates. get_mcp_documentation expands help explicitly. FastMCP may reject malformed JSON or missing required MCP arguments before dispatch.",
+    "The existing worker process registry and cancellation cleanup remain in use. No arbitrary symbol, function or source path can be executed."
+  ],
+  "freshness": [
+    "reports.summary is historical_unverified; snapshot.metadata is durable_metadata_only; live.ping compares only revisions actually observed in sampled ping responses.",
+    "Equal ping revisions do not prove atomic stability between sampling instants. A durable revision does not prove the current LIVE revision."
+  ],
+  "errors": [
+    "Invalid requests are rejected before worker spawn with compact parameter guidance.",
+    "Unavailable, invalid_data, invalid_identity and changed_during_read outcomes are explicit failures, not successful timing samples.",
+    "Warmup failure stops measurement. Measured failures preserve a bounded failure category without traceback or arbitrary contents."
+  ],
+  "usage_notes": [
+    "Use mode=catalog to inspect the fixed scope and preset registry.",
+    "Use mode=probe with exactly one scope and explicitly selected presets. Repeated samples are sequential and do not include worker startup."
+  ],
+  "examples": [
+    "contextor_profile_analysis(repo_path=\"C:\\\\Temp\\\\Contextor_Repo\", mode=\"probe\", scope=\"live.ping\", presets=[\"connect\", \"ping\"])"
+  ]
 }

FILE: C:\Temp\Contextor_Repo\contextor\mcp\docs\index.json
diff --git a/contextor/mcp/docs/index.json b/contextor/mcp/docs/index.json
index 79b3579..ec32136 100644
--- a/contextor/mcp/docs/index.json
+++ b/contextor/mcp/docs/index.json
@@ -141,7 +141,7 @@
     {
       "tool": "contextor_profile_analysis",
       "filename": "contextor_profile_analysis.json",
-      "short_description": "Run one non-blocking-admission full-analysis diagnostic profile and return critical-path bottlenecks with deterministic structured evidence. Absolute wall time is diagnostic, not benchmark-authoritative."
+      "short_description": "Profile legacy FULL analysis or measure selected timing spans in one registered read operation. Catalog lists fixed scopes; probe uses one isolated worker with bounded results."
     },
     {
       "tool": "get_mcp_documentation",

FILE: C:\Temp\Contextor_Repo\tests\test_atomic_profiler.py
diff --git a/tests/test_atomic_profiler.py b/tests/test_atomic_profiler.py
new file mode 100644
--- /dev/null
+++ b/tests/test_atomic_profiler.py
@@ -0,0 +1,101 @@
+import json
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.profiling.atomic import AtomicRecorder
+from contextor.core.profiling.registry import build_catalog, get_scope
+from contextor.core.profiling.runner import _stats, run_probe, validate_probe_request
+
+
+def test_catalog_static_and_ordered():
+    assert [item["name"] for item in build_catalog()["scopes"]] == [
+        "reports.summary", "live.ping", "snapshot.metadata"]
+    assert get_scope("arbitrary.function") is None
+
+
+def test_disabled_span_executes_without_timing(monkeypatch):
+    import contextor.core.profiling.atomic as atomic
+    monkeypatch.setattr(atomic, "perf_counter_ns", lambda: pytest.fail("timer read"))
+    recorder = AtomicRecorder("reports.summary", frozenset(), 0)
+    called = []
+    with recorder.span("read_bytes"):
+        called.append(1)
+    assert called == [1]
+    assert recorder.records() == ()
+
+
+def test_selected_span_records_success_and_failure():
+    recorder = AtomicRecorder("reports.summary", frozenset({"read_bytes"}), 0)
+    with recorder.span("read_bytes"):
+        pass
+    with pytest.raises(RuntimeError):
+        with recorder.span("read_bytes"):
+            raise RuntimeError("private value")
+    assert [item["status"] for item in recorder.records()] == ["ok", "failed"]
+    assert all(item["duration_ns"] >= 0 for item in recorder.records())
+
+
+@pytest.mark.parametrize("samples,warmup", [(True, 0), (1, False), (0, 0), (11, 0), (1, 4)])
+def test_invalid_counts(samples, warmup):
+    with pytest.raises(ValueError):
+        validate_probe_request("reports.summary", ["read_bytes"], samples, warmup, "summary")
+
+
+def test_statistics_nearest_rank():
+    assert _stats([1_000_000])["p95_ms"] is None
+    assert _stats([n * 1_000_000 for n in range(1, 6)])["p95_ms"] == 5
+
+
+def test_runner_excludes_warmup_and_spans_are_selected(tmp_path, monkeypatch):
+    spec = get_scope("reports.summary")
+    called = []
+    def fake_run(root, recorder):
+        called.append(1)
+        with recorder.span("read_bytes"):
+            pass
+        with recorder.span("json_decode"):
+            pass
+        return {"status": "ok", "data_source": "historical_report"}
+    import contextor.core.profiling.registry as registry
+    monkeypatch.setattr(registry, "_SCOPES", (replace(spec, run_scope=fake_run), *registry.list_scopes()[1:]))
+    summary = run_probe(tmp_path, "reports.summary", ["read_bytes"], 2, 1, "summary")
+    assert len(called) == 3
+    assert summary["wall"]["count"] == 2
+    assert summary["presets"]["read_bytes"]["count"] == 2
+    assert "spans" not in summary
+    spans = run_probe(tmp_path, "reports.summary", ["read_bytes"], 1, 0, "spans")
+    assert {item["preset"] for item in spans["spans"]} == {"read_bytes"}
+
+
+def test_warmup_failure_stops_and_is_not_success(tmp_path, monkeypatch):
+    import contextor.core.profiling.registry as registry
+    spec = get_scope("reports.summary")
+    calls = []
+    def fail(root, recorder):
+        calls.append(1)
+        return {"status": "unavailable", "reason": "report_missing"}
+    monkeypatch.setattr(registry, "_SCOPES", (replace(spec, run_scope=fail), *registry.list_scopes()[1:]))
+    result = run_probe(tmp_path, "reports.summary", ["read_bytes"], 3, 1, "summary")
+    assert result["status"] == "warmup_failed"
+    assert result["wall"]["count"] == 0
+    assert calls == [1]
+
+
+def test_live_revision_change_and_output_bound(tmp_path, monkeypatch):
+    import contextor.core.profiling.registry as registry
+    import contextor.core.profiling.runner as runner
+    specs = registry.list_scopes()
+    revisions = iter((1, 2))
+    def ping(root, recorder):
+        with recorder.span("ping"):
+            pass
+        return {"status": "ok", "observed_revision": next(revisions),
+                "data_source": "live_authority"}
+    monkeypatch.setattr(registry, "_SCOPES", (specs[0], replace(specs[1], run_scope=ping), specs[2]))
+    result = run_probe(tmp_path, "live.ping", ["ping"], 2, 0, "summary")
+    assert result["consistency"]["status"] == "revision_changed"
+    monkeypatch.setattr(runner, "MAX_OUTPUT_BYTES", 100)
+    overflow = run_probe(tmp_path, "reports.summary", ["read_bytes"], 1, 0, "spans")
+    assert overflow["status"] == "confirmation_required"

FILE: C:\Temp\Contextor_Repo\tests\test_atomic_profiler_scopes.py
diff --git a/tests/test_atomic_profiler_scopes.py b/tests/test_atomic_profiler_scopes.py
new file mode 100644
--- /dev/null
+++ b/tests/test_atomic_profiler_scopes.py
@@ -0,0 +1,93 @@
+import json
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.profiling.atomic import AtomicRecorder
+from contextor.core.profiling.scopes import reports, live_ipc, snapshot_metadata
+from contextor.core.live_state.store import LiveStateMetadata
+
+
+def _recorder(scope):
+    return AtomicRecorder(scope, frozenset(), 0)
+
+
+@pytest.mark.parametrize("raw_revision,valid", [
+    (True, False), (False, False), ("1", False), (1.0, False),
+    (None, False), (0, False), (-1, False), (1, True), (2, True),
+])
+def test_raw_revision_validation(tmp_path, monkeypatch, raw_revision, valid):
+    root = tmp_path / "repo"
+    root.mkdir()
+    cache = tmp_path / "cache"
+    cache.mkdir()
+    metadata = {
+        "state_id": "state-1", "revision": raw_revision, "repo_id": "ctx_test",
+        "root_path": str(root), "schema_version": "1.4",
+    }
+    (cache / "engine_state.meta.json").write_text(json.dumps(metadata))
+    monkeypatch.setattr(snapshot_metadata, "read_repository_identity", lambda _: SimpleNamespace(repo_id="ctx_test"))
+    monkeypatch.setattr(snapshot_metadata, "repo_cache_dir", lambda _: cache)
+    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
+        state_id="state-1", revision=int(raw_revision or 0) if raw_revision is not None else 0,
+        repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
+    result = snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))
+    assert (result["status"] == "ok") is valid
+    assert not (cache / "lineage_validation_cache.json").exists()
+    assert sorted(path.name for path in cache.iterdir()) == ["engine_state.meta.json"]
+
+
+def test_metadata_mismatch_and_replacement(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    cache = tmp_path / "cache"
+    cache.mkdir()
+    path = cache / "engine_state.meta.json"
+    raw = {"state_id": "a", "revision": 1, "repo_id": "ctx_test",
+           "root_path": str(root), "schema_version": "1.4"}
+    path.write_text(json.dumps(raw))
+    monkeypatch.setattr(snapshot_metadata, "read_repository_identity", lambda _: SimpleNamespace(repo_id="ctx_test"))
+    monkeypatch.setattr(snapshot_metadata, "repo_cache_dir", lambda _: cache)
+    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
+        state_id="different", revision=1, repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
+    assert snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))["status"] == "invalid_identity"
+    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
+        state_id="a", revision=1, repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
+    original = Path.read_bytes
+    reads = [0]
+    def changing(self):
+        if self == path:
+            reads[0] += 1
+            if reads[0] == 2:
+                return b'{"changed":true}'
+        return original(self)
+    monkeypatch.setattr(Path, "read_bytes", changing)
+    assert snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))["status"] == "changed_during_read"
+
+
+def test_reports_missing_and_invalid(tmp_path, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    out = tmp_path / "output"
+    out.mkdir()
+    monkeypatch.setattr(reports, "output_dir", lambda: out)
+    assert reports.run_scope(root, _recorder("reports.summary"))["status"] == "unavailable"
+    report = out / "repo_summary.json"
+    report.write_text("{invalid")
+    assert reports.run_scope(root, _recorder("reports.summary"))["status"] == "invalid_data"
+    report.write_text('{"secret": "must-not-return"}')
+    result = reports.run_scope(root, _recorder("reports.summary"))
+    assert result["status"] == "ok"
+    assert "secret" not in str(result)
+
+
+def test_live_uses_existing_connect_and_only_ping(tmp_path, monkeypatch):
+    calls = []
+    monkeypatch.setattr(live_ipc, "connect", lambda root: calls.append("connect") or SimpleNamespace(
+        ping=lambda: calls.append("ping") or {"status": "ok", "revision": 2}))
+    result = live_ipc.run_scope(tmp_path, _recorder("live.ping"))
+    assert calls == ["connect", "ping"]
+    assert result["observed_revision"] == 2
+    monkeypatch.setattr(live_ipc, "connect", lambda root: None)
+    assert live_ipc.run_scope(tmp_path, _recorder("live.ping"))["status"] == "unavailable"

FILE: C:\Temp\Contextor_Repo\tests\test_profile_worker.py
diff --git a/tests/test_profile_worker.py b/tests/test_profile_worker.py
index b066363..14ad022 100644
--- a/tests/test_profile_worker.py
+++ b/tests/test_profile_worker.py
@@ -14,3 +14,14 @@ def test_execute_profile_request_delegates_to_profile_runner(tmp_path: Path, mon
 @pytest.mark.parametrize("payload",[None,[],{},{"repo_path":""},{"repo_path":"x","exclude_paths":"x"},{"repo_path":"x","exclude_paths":[""]},{"repo_path":"x","exclude_paths":[1]}])
 def test_execute_profile_request_rejects_invalid_request(payload):
     with pytest.raises(ValueError): profile_worker.execute_profile_request(payload)
+
+def test_probe_worker_validates_and_avoids_full(tmp_path, monkeypatch):
+    monkeypatch.setattr(profile_worker, "run_analysis_profile", lambda *a, **k: pytest.fail("FULL"))
+    observed = {}
+    monkeypatch.setattr(profile_worker, "run_probe", lambda *args: observed.setdefault("args", args) or {})
+    request = {"repo_path": str(tmp_path), "mode": "probe", "scope": "reports.summary",
+               "presets": ["read_bytes"], "samples": 1, "warmup": 0, "result_view": "summary"}
+    profile_worker.execute_profile_request(request)
+    assert observed["args"][1] == "reports.summary"
+    with pytest.raises(ValueError):
+        profile_worker.execute_profile_request({**request, "presets": ["ping"]})

FILE: C:\Temp\Contextor_Repo\tests\test_mcp_diagnostics.py
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 8da374e..1c7de24 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -18,6 +18,13 @@ import contextor.mcp.tools.get_name_collisions as collision_tool
 from contextor.mcp.tools.get_analysis_status import get_analysis_status
 
 
+def test_atomic_profile_skips_diagnostics_injection(tmp_path, monkeypatch):
+    import contextor.mcp.diagnostics as diagnostic_module
+    monkeypatch.setattr(diagnostic_module, "diagnostics_summary", lambda _: pytest.fail("diagnostics read"))
+    response = json.dumps({"schema": "contextor-atomic-profile/v1", "status": "ok"})
+    assert inject_diagnostics_summary(response, tmp_path, "contextor_profile_analysis") == response
+
+
 def _collision(kind="NAME_COLLISION", identical=False, module="pkg.a"):
     return SimpleNamespace(
         kind=kind,

FILE: C:\Temp\Contextor_Repo\tests\test_mcp_documentation.py
diff --git a/tests/test_mcp_documentation.py b/tests/test_mcp_documentation.py
index 8c18f13..546f8db 100644
--- a/tests/test_mcp_documentation.py
+++ b/tests/test_mcp_documentation.py
@@ -278,7 +278,7 @@ def test_contextor_profile_analysis_is_registered_and_documented():
 
     assert tool.description == entry["short_description"]
     assert str(inspect.signature(tool.fn, eval_str=True)) == (
-        "(repo_path: str, exclude_paths: list[str] | None = None) -> str"
+        "(repo_path: str, exclude_paths: list[str] | None = None, mode: str = 'full', scope: str | None = None, presets: list[str] | None = None, samples: int = 1, warmup: int = 0, result_view: str = 'summary') -> str"
     )
     assert index["tools"][-1]["tool"] == "get_mcp_documentation"
 

FILE: C:\Temp\Contextor_Repo\tests\mcp\tools\test_contextor_profile_analysis.py
diff --git a/tests/mcp/tools/test_contextor_profile_analysis.py b/tests/mcp/tools/test_contextor_profile_analysis.py
index 88efaaf..d6bcfa7 100644
--- a/tests/mcp/tools/test_contextor_profile_analysis.py
+++ b/tests/mcp/tools/test_contextor_profile_analysis.py
@@ -64,3 +64,51 @@ def test_profile_worker_non_object_payload_propagates_as_runtime_error(tmp_path:
     monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
     with pytest.raises(RuntimeError, match="^Contextor profile worker returned a non-object payload\\.$"):
         asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path)))
+
+
+def test_catalog_and_invalid_input_never_spawn(tmp_path, monkeypatch):
+    async def forbidden(*args, **kwargs):
+        pytest.fail("worker spawned")
+    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", forbidden)
+    catalog = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), mode="catalog")))
+    assert catalog["mode"] == "catalog"
+    for kwargs in [
+        {"mode": "proeb"}, {"mode": "probe", "scope": "live.png", "presets": ["ping"]},
+        {"mode": "probe", "scope": "live.ping", "presets": ["read_bytes"]},
+        {"mode": "probe", "scope": "live.ping", "presets": ["ping", "ping"]},
+        {"mode": "probe", "scope": "live.ping", "presets": []},
+        {"mode": "probe", "scope": "live.ping", "presets": ["ping"], "samples": True},
+        {"mode": "catalog", "scope": "live.ping"},
+    ]:
+        result = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), **kwargs)))
+        assert result["status"] == "invalid_profile_request"
+    wrong = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(
+        str(tmp_path), mode="probe", scope="live.ping", presets=["read_bytes"])))
+    assert wrong["owning_scope"] == "reports.summary"
+
+
+def test_probe_request_payload(tmp_path, monkeypatch):
+    process = _FakeProfileProcess({"schema": "contextor-atomic-profile/v1", "status": "ok"})
+    async def create(*args, **kwargs):
+        return process
+    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", create)
+    asyncio.run(profile_tool.contextor_profile_analysis(
+        str(tmp_path), mode="probe", scope="live.ping", presets=["ping"]))
+    assert json.loads(process.request) == {
+        "repo_path": str(tmp_path.resolve()), "mode": "probe", "scope": "live.ping",
+        "presets": ["ping"], "samples": 1, "warmup": 0, "result_view": "summary"}
+
+
+def test_fuzzy_guidance_uses_shared_helper_without_execution(tmp_path, monkeypatch):
+    seen = []
+    def shared(value, choices):
+        seen.append((value, choices))
+        return [{"value": "live.ping", "score": 0.9}]
+    monkeypatch.setattr(profile_tool, "fuzzy_choice_candidates", shared)
+    async def forbidden(*args, **kwargs):
+        pytest.fail("worker spawned")
+    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", forbidden)
+    result = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(
+        str(tmp_path), mode="probe", scope="live.png", presets=["ping"])))
+    assert result["similar_candidates"] == [{"value": "live.ping", "score": 0.9}]
+    assert seen[0][0] == "live.png"
