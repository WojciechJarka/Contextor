# CONTEXTOR_B0G2D7A_MULTI_MUTATION_FULL_PARITY_MATRIX

## FILES_CHANGED
- C:\Temp\Contextor_Repo\tests\test_incremental_multi_mutation_full_parity.py — new file with six tests A–F.
- C:\Temp\Contextor_Repo\walkthrough.md — current report only, excluded from source/test changes.
- No production files or existing tests were modified.

## SOURCE_PRECHECK
- HEAD: e687e1e091b109e91dd5cb59df6f1e60fcb5e90d; precheck git status was clean.
- Contextor MCP first, with current tool documentation and deferred discovery.
- Complete, untruncated Contextor implementations: RefreshPlanner.plan_refresh; _refresh_canonical_layer_information; _state_projection; _full_state. execute_refresh_plan fetched in contiguous ranges covering lines 932–1499. IncrementalAnalysisEngine.update_file and _apply_delta_and_commit retrieved with contiguous source ranges after confirmation_required for large symbol response; _apply_delta_and_commit spans lines 879–1146. workspace_sync=verified, canonical revision 373.
- LIVE before test: revision 373, continuity=continuous, resync_required=false.
- _state_projection verifies every declared RepositoryAnalysisState field. The new test compares through this helper and normalizes only the two report timestamps.

## BASELINE_AND_FIXTURE_VALIDATION
- Real ContextorFacade.analyze_project on isolated tmp_path/repo for case A, then loaded the persisted FULL state and hydrated a real engine.
- FULL validation succeeded. Hydrated state_id and revision matched metadata.
- Initial FileState: 5/5 sources, no missing/extra paths or SHA-256 mismatches.
- Exactly one mutation: created gamma/__init__.py with bytes b"GAMMA_VALUE = 7\n"; then called engine.update_file with its absolute Windows path.
- Status UPDATED matched expected. Incremental state was copied before another FULL. A real fresh FULL on the same source bytes succeeded.
- Baseline had 5 modules; incremental and fresh FULL both have 6, including gamma.__init__.

## STRICT_COMPARATOR_CONTRACT
- Used existing test_desktop_mcp_canonical_parity._state_projection and _first_difference, without modifying the comparator.
- The only normalization is layer_information.summary_data.generated_at and layer_information.summary_data.report_header.generated_at via normalize_report_timestamps=True.
- No ordering or missing-field exclusions. Snapshot revision/state_id are retained in evidence and not treated as equal-generation parity criteria.

## CASE_A_NEW_LAYER
- Real canonical difference: state.layer_information["layer_index"], incremental length 2, fresh FULL length 3.
- Incremental layer_index contains alpha and beta. Fresh FULL contains those two entries plus:
  {"layer": "gamma", "module_count": 1, "status": "HEALTHY", "cycles_count": 0, "hotspot_count": 0, "computation_mode": "filtered"}.
- gamma.__init__ is present in both module sets, so the package/module was recognized; the layer report index remained stale in incremental state.
- Expected and actual status: UPDATED.
- Initial FULL state_id 20261012_145035, revision 1. Fresh FULL state_id 20261012_145037, revision 2. Different generation metadata was not used as a parity criterion.

## CASE_B_MODULE_DELETION
Not run. pytest -x stopped on the first real mismatch in A; B fixture remained untouched.

## CASE_C_CONSUMER_CHANGE
Not run. Stopped after A mismatch as required.

## CASE_D_SYMBOL_ADDITION
Not run. Stopped after A mismatch as required.

## CASE_E_REEXPORT_RETARGET
Not run. Stopped after A mismatch as required.

## CASE_F_SEMANTIC_NOOP
Not run. Stopped after A mismatch as required.

## FIRST_MISMATCH_IF_ANY
First and only compared mutation case was A. Comparator output:
- path: state.layer_information[{'kind': 'primitive', 'type': 'builtins.str', 'value': 'layer_index'}].<length>
- incremental: 2
- fresh FULL: 3
The complete preserved objects confirm that fresh FULL contains a gamma layer entry absent from incremental.

## MISMATCH_CLASSIFICATION
CANONICAL_STATE — confirmed difference between direct production incremental and fresh FULL. This is not a harness/setup failure: both FULL analyses succeeded, update returned expected UPDATED, gamma module is in both results, FileState covers all source files, and the strict comparator found a different canonical field. The remaining five cases were not run.

## PRESERVED_EVIDENCE_PATHS
Evidence is outside the repository:
C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-570\test_case_a_new_architectural_0\b0g2d7a_a_evidence
- initial_full.pickle
- incremental.pickle
- fresh_full.pickle
- summary.json
Pickles contain complete RepositoryAnalysisState objects, FileState mappings, generation metadata, source bytes and repo/cache paths. JSON contains scenario, statuses, exact first difference, module IDs, freshness markers, FileState coverage, source bytes in Base64, SHA-256 and metadata.

## FILESTATE_AND_MANIFEST_PARITY
- Case A incremental FileState coverage: 6/6; missing=[], extra=[], sha256_mismatches=[].
- Fresh FULL FileState coverage: 6/6; missing=[], extra=[], sha256_mismatches=[].
- module_usages_manifest is covered by the strict canonical comparer, but traversal stopped at the earlier layer_index mismatch; independent manifest parity is not claimed.

## GRAPH_AND_REFERENCE_PARITY
The first difference is layer_index. No conclusion is drawn about fields after that first mismatch or the five unexecuted cases. For A, target module is gamma.__init__; both states contain alpha.__init__, alpha.api, beta.__init__, beta.consumer, gamma.__init__, loose.

## LINEAGE_AND_PROVENANCE_PARITY
Lineage/reexport scenarios were not reached. No parity claim is made for later canonical fields after the first difference.

## LAYER_INFORMATION_AND_CACHE_PARITY
Parity failed: fresh FULL layer_index contains gamma and incremental does not. Other layer_information fields and fields after the first mismatch were not certified.

## FRESHNESS_AND_COMPLETENESS_PARITY
In A, all collected family freshness markers are fresh on both sides; module gamma is present on both. FileState SHA coverage is 6/6 on each side. Despite these markers, layer_index differs.

## TARGETED_TEST_RESULTS
- Required command: .venv\Scripts\python.exe -m pytest -q -x -s tests/test_incremental_multi_mutation_full_parity.py
- Result: 1 failed, 1 warning in 8.73s, exit 1; -x stopped at test_case_a_new_architectural_layer_matches_fresh_full.
- Failure: A CANONICAL_STATE, expected UPDATED, actual UPDATED, first difference layer_index length 2 vs 3. Test saved evidence before failing.
- Follow-up transport and atomicity tests were not run because all six cases did not pass.

## ATOMICITY_RECHECK
Not run in this task; follow-up requires all six cases to pass. The preceding B0G2D6A targeted result was 4 failure-atomicity tests passed; this task did not repeat them.

## PY_COMPILE
.venv\Scripts\python.exe -m py_compile tests\test_incremental_multi_mutation_full_parity.py: PASS, exit 0.

## GIT_DIFF_CHECK
- git diff --check: exit 0.
- git diff --no-index --check -- NUL tests/test_incremental_multi_mutation_full_parity.py: no whitespace errors; exit 1 denotes new untracked file. Git warned only about potential LF/CRLF conversion.

## LIVE_REVISION_BEFORE_AFTER
Before 373. After 375. Watcher recorded event 374 UPDATED and 375 UNCHANGED for the new test file. continuity=continuous; resync_required=false.

## WORKSPACE_SYNC_POSTCHECK
Contextor fetched complete implementation of test_case_a_new_architectural_layer_matches_fresh_full; workspace_sync=verified, canonical revision 375.

## RESYNC_REQUIRED
false after test; event continuity continuous.

## RESTART_REQUIRED
No. Only a test file changed. No restart or serving-process certification was performed.

## FINAL_VERDICT
B0G2D7A_NEW_CANONICAL_MISMATCH. The first test shows direct incremental creation of a package leaves layer_information.layer_index shorter than fresh FULL. Evidence is preserved; B–F and follow-up gate were intentionally not run. STOP; await proceduj.

## FULL_DIFFS
Complete actual diff of the new test follows.

<pre>
diff --git a/tests/test_incremental_multi_mutation_full_parity.py b/tests/test_incremental_multi_mutation_full_parity.py
new file mode 100644
index 0000000..0141993
--- /dev/null
+++ b/tests/test_incremental_multi_mutation_full_parity.py
@@ -0,0 +1,419 @@
+"""Direct incremental mutation parity against a fresh FULL analysis."""
+
+from __future__ import annotations
+
+import base64
+import copy
+import hashlib
+import json
+import pickle
+from pathlib import Path
+from typing import Any
+
+import pytest
+
+from contextor.core.analysis.state_manager import (
+    FileStateManager,
+    RepositoryAnalysisState,
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+from test_desktop_mcp_canonical_parity import (
+    _first_difference,
+    _state_projection,
+)
+
+
+_COMMON_FIXTURE = {
+    "alpha/__init__.py": b"",
+    "alpha/api.py": b"def api_function():\n    return 1\n",
+    "beta/__init__.py": b"",
+    "beta/consumer.py": (
+        b"from alpha.api import api_function\n"
+        b"CONSUMER_RESULT = api_function()\n"
+    ),
+    "loose.py": b"LOOSE_VALUE = 0\n",
+}
+
+_REEXPORT_FIXTURE = {
+    "alpha/__init__.py": b"from .api import api_function\n",
+    "alpha/api.py": b"def api_function():\n    return 1\n",
+    "beta/__init__.py": b"",
+    "beta/consumer.py": (
+        b"from alpha import api_function\n"
+        b"CONSUMER_RESULT = api_function()\n"
+    ),
+    "loose.py": b"LOOSE_VALUE = 0\n",
+}
+
+
+def _write_sources(root: Path, sources: dict[str, bytes]) -> None:
+    for relative, content in sources.items():
+        target = root / relative
+        target.parent.mkdir(parents=True, exist_ok=True)
+        target.write_bytes(content)
+
+
+def _source_bytes(root: Path) -> dict[str, bytes]:
+    return {
+        path.relative_to(root).as_posix(): path.read_bytes()
+        for path in sorted(root.rglob("*.py"))
+    }
+
+
+def _source_hashes(sources: dict[str, bytes]) -> dict[str, str]:
+    return {
+        relative: hashlib.sha256(content).hexdigest()
+        for relative, content in sorted(sources.items())
+    }
+
+
+def _run_full_and_load(root: Path):
+    errors, _result = ContextorFacade.analyze_project(str(root))
+    assert not errors, f"FULL validation failed for isolated fixture {root}: {errors!r}"
+
+    cache_dir = repo_cache_dir(root)
+    metadata = read_metadata(cache_dir)
+    assert metadata is not None, f"FULL did not persist snapshot metadata for {root}"
+    state = load_engine_state(
+        str(cache_dir),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert isinstance(state, RepositoryAnalysisState)
+    assert state.state_id == metadata.state_id
+    assert state.revision == metadata.revision
+    manager = FileStateManager(str(cache_dir))
+    return state, manager._state.copy(), metadata
+
+
+def _file_state_coverage(root: Path, file_states: dict[str, Any]) -> dict:
+    source_paths = {
+        str(path.resolve()): path
+        for path in root.rglob("*.py")
+    }
+    tracked_paths = set(file_states)
+    missing = sorted(set(source_paths) - tracked_paths)
+    extra = sorted(tracked_paths - set(source_paths))
+    digest_mismatches = []
+    for absolute_path in sorted(set(source_paths) & tracked_paths):
+        expected = hashlib.sha256(source_paths[absolute_path].read_bytes()).hexdigest()
+        actual = getattr(file_states[absolute_path], "sha256", None)
+        if actual != expected:
+            digest_mismatches.append(
+                {"path": absolute_path, "expected_sha256": expected, "actual_sha256": actual}
+            )
+    return {
+        "expected_source_count": len(source_paths),
+        "tracked_path_count": len(tracked_paths),
+        "missing_paths": missing,
+        "extra_paths": extra,
+        "sha256_mismatches": digest_mismatches,
+    }
+
+
+def _freshness_markers(state: RepositoryAnalysisState) -> dict:
+    values = vars(state)
+    return {
+        key: copy.deepcopy(value)
+        for key, value in values.items()
+        if key.endswith("_state") or key in {"module_parse_freshness", "resync_required"}
+    }
+
+
+def _capture_payload(
+    *,
+    state: RepositoryAnalysisState,
+    file_states: dict[str, Any],
+    metadata: Any,
+    source_bytes: dict[str, bytes],
+    root: Path,
+) -> dict:
+    return {
+        "state": copy.deepcopy(state),
+        "file_states": copy.deepcopy(file_states),
+        "metadata": copy.deepcopy(metadata),
+        "source_bytes": dict(source_bytes),
+        "cache_dir": str(repo_cache_dir(root)),
+        "root": str(root.resolve()),
+    }
+
+
+def _preserve_mismatch(
+    tmp_path: Path,
+    *,
+    scenario_id: str,
+    expected_status: str,
+    actual_status: str | None,
+    update_exception: str | None,
+    target_module_id: str,
+    initial_payload: dict,
+    incremental_payload: dict,
+    full_payload: dict,
+    state_difference: tuple | None,
+    incremental_file_coverage: dict,
+    full_file_coverage: dict,
+    mismatch_kind: str,
+) -> Path:
+    evidence_dir = tmp_path / f"b0g2d7a_{scenario_id.lower()}_evidence"
+    evidence_dir.mkdir(parents=True, exist_ok=True)
+    for name, payload in (
+        ("initial_full.pickle", initial_payload),
+        ("incremental.pickle", incremental_payload),
+        ("fresh_full.pickle", full_payload),
+    ):
+        with (evidence_dir / name).open("wb") as output:
+            pickle.dump(payload, output, protocol=pickle.HIGHEST_PROTOCOL)
+
+    source_bytes = incremental_payload["source_bytes"]
+    summary = {
+        "scenario_id": scenario_id,
+        "mismatch_kind": mismatch_kind,
+        "expected_update_status": expected_status,
+        "actual_update_status": actual_status,
+        "update_exception": update_exception,
+        "target_module_id": target_module_id,
+        "initial_module_ids": sorted(initial_payload["state"].modules),
+        "incremental_module_ids": sorted(incremental_payload["state"].modules),
+        "fresh_full_module_ids": sorted(full_payload["state"].modules),
+        "family_freshness_markers": {
+            "initial": _freshness_markers(initial_payload["state"]),
+            "incremental": _freshness_markers(incremental_payload["state"]),
+            "fresh_full": _freshness_markers(full_payload["state"]),
+        },
+        "incremental_file_state_coverage": incremental_file_coverage,
+        "fresh_full_file_state_coverage": full_file_coverage,
+        "first_structural_difference": state_difference,
+        "source_bytes_base64": {
+            relative: base64.b64encode(content).decode("ascii")
+            for relative, content in sorted(source_bytes.items())
+        },
+        "source_sha256": _source_hashes(source_bytes),
+        "snapshot_metadata": {
+            "initial_full": repr(initial_payload["metadata"]),
+            "fresh_full": repr(full_payload["metadata"]),
+        },
+    }
+    (evidence_dir / "summary.json").write_text(
+        json.dumps(summary, indent=2, sort_keys=True, default=repr) + "\n",
+        encoding="utf-8",
+    )
+    return evidence_dir
+
+
+def _run_mutation_case(
+    tmp_path: Path,
+    *,
+    scenario_id: str,
+    fixture: dict[str, bytes],
+    mutation_path: str,
+    mutation_bytes: bytes | None,
+    expected_status: str,
+) -> None:
+    root = tmp_path / "repo"
+    root.mkdir()
+    _write_sources(root, fixture)
+
+    initial_state, initial_file_states, initial_metadata = _run_full_and_load(root)
+    hydrated = hydrate_repository_engine(root)
+    assert hydrated is not None, f"Could not hydrate FULL baseline for {scenario_id}: {root}"
+    engine = hydrated.engine
+    assert engine.state.state_id == initial_metadata.state_id
+    assert engine.state.revision == initial_metadata.revision
+    assert _state_projection(engine.state) == _state_projection(initial_state)
+
+    initial_file_states = copy.deepcopy(engine.state_manager._state)
+    initial_state = engine.state
+    initial_source_bytes = _source_bytes(root)
+    initial_payload = _capture_payload(
+        state=initial_state,
+        file_states=initial_file_states,
+        metadata=initial_metadata,
+        source_bytes=initial_source_bytes,
+        root=root,
+    )
+    initial_coverage = _file_state_coverage(root, initial_file_states)
+    assert not initial_coverage["missing_paths"]
+    assert not initial_coverage["extra_paths"]
+    assert not initial_coverage["sha256_mismatches"]
+
+    target = root / mutation_path
+    target.parent.mkdir(parents=True, exist_ok=True)
+    if mutation_bytes is None:
+        target.unlink()
+    else:
+        target.write_bytes(mutation_bytes)
+
+    actual_status = None
+    update_exception = None
+    try:
+        result = engine.update_file(str(target.resolve()))
+        actual_status = result.status
+    except Exception as exc:
+        update_exception = f"{type(exc).__module__}.{type(exc).__qualname__}: {exc}"
+
+    incremental_state = copy.deepcopy(engine.state)
+    incremental_file_states = copy.deepcopy(engine.state_manager._state)
+    incremental_source_bytes = _source_bytes(root)
+    incremental_payload = _capture_payload(
+        state=incremental_state,
+        file_states=incremental_file_states,
+        metadata=initial_metadata,
+        source_bytes=incremental_source_bytes,
+        root=root,
+    )
+    incremental_projection = _state_projection(
+        incremental_state,
+        normalize_report_timestamps=True,
+    )
+    incremental_coverage = _file_state_coverage(root, incremental_file_states)
+
+    fresh_state, fresh_file_states, fresh_metadata = _run_full_and_load(root)
+    assert _source_bytes(root) == incremental_source_bytes, (
+        f"fixture source bytes changed during fresh FULL for {scenario_id}"
+    )
+    full_payload = _capture_payload(
+        state=fresh_state,
+        file_states=fresh_file_states,
+        metadata=fresh_metadata,
+        source_bytes=incremental_source_bytes,
+        root=root,
+    )
+    fresh_projection = _state_projection(
+        fresh_state,
+        normalize_report_timestamps=True,
+    )
+    state_difference = _first_difference(incremental_projection, fresh_projection)
+    full_coverage = _file_state_coverage(root, fresh_file_states)
+
+    mismatch_kind = None
+    if update_exception is not None:
+        mismatch_kind = "UPDATE_EXCEPTION"
+    elif actual_status != expected_status:
+        mismatch_kind = "UPDATE_STATUS"
+    elif state_difference is not None:
+        mismatch_kind = "CANONICAL_STATE"
+    elif any(
+        incremental_coverage[key]
+        for key in ("missing_paths", "extra_paths", "sha256_mismatches")
+    ):
+        mismatch_kind = "INCREMENTAL_FILESTATE"
+    elif any(
+        full_coverage[key]
+        for key in ("missing_paths", "extra_paths", "sha256_mismatches")
+    ):
+        mismatch_kind = "FULL_FILESTATE"
+
+    if mismatch_kind is not None:
+        target_module_id = ".".join(Path(mutation_path).with_suffix("").parts)
+        evidence_dir = _preserve_mismatch(
+            tmp_path,
+            scenario_id=scenario_id,
+            expected_status=expected_status,
+            actual_status=actual_status,
+            update_exception=update_exception,
+            target_module_id=target_module_id,
+            initial_payload=initial_payload,
+            incremental_payload=incremental_payload,
+            full_payload=full_payload,
+            state_difference=state_difference,
+            incremental_file_coverage=incremental_coverage,
+            full_file_coverage=full_coverage,
+            mismatch_kind=mismatch_kind,
+        )
+        pytest.fail(
+            f"{scenario_id} {mismatch_kind}: expected_status={expected_status!r}; "
+            f"actual_status={actual_status!r}; update_exception={update_exception!r}; "
+            f"first_difference={state_difference!r}; "
+            f"incremental_file_coverage={incremental_coverage!r}; "
+            f"fresh_full_file_coverage={full_coverage!r}; evidence={evidence_dir}"
+        )
+
+    if scenario_id == "F":
+        source_sha = hashlib.sha256(incremental_source_bytes["loose.py"]).hexdigest()
+        tracked_path = str((root / "loose.py").resolve())
+        assert incremental_file_states[tracked_path].sha256 == source_sha
+        assert incremental_state.module_usages_manifest["loose"]["sha256"] == source_sha
+
+
+def test_case_a_new_architectural_layer_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="A",
+        fixture=_COMMON_FIXTURE,
+        mutation_path="gamma/__init__.py",
+        mutation_bytes=b"GAMMA_VALUE = 7\n",
+        expected_status="UPDATED",
+    )
+
+
+def test_case_b_module_deletion_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="B",
+        fixture=_COMMON_FIXTURE,
+        mutation_path="beta/consumer.py",
+        mutation_bytes=None,
+        expected_status="DELETED",
+    )
+
+
+def test_case_c_consumer_usage_change_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="C",
+        fixture=_COMMON_FIXTURE,
+        mutation_path="beta/consumer.py",
+        mutation_bytes=(
+            b"from alpha.api import api_function\n"
+            b"CONSUMER_RESULT = api_function()\n"
+            b"SECOND_RESULT = api_function()\n"
+        ),
+        expected_status="UPDATED",
+    )
+
+
+def test_case_d_symbol_addition_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="D",
+        fixture=_COMMON_FIXTURE,
+        mutation_path="alpha/api.py",
+        mutation_bytes=(
+            b"def api_function():\n"
+            b"    return 1\n"
+            b"\n"
+            b"def added_function():\n"
+            b"    return 2\n"
+        ),
+        expected_status="UPDATED",
+    )
+
+
+def test_case_e_reexport_retarget_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="E",
+        fixture=_REEXPORT_FIXTURE,
+        mutation_path="alpha/__init__.py",
+        mutation_bytes=b"api_function = 7\n",
+        expected_status="UPDATED",
+    )
+
+
+def test_case_f_semantic_noop_matches_fresh_full(tmp_path):
+    _run_mutation_case(
+        tmp_path,
+        scenario_id="F",
+        fixture=_COMMON_FIXTURE,
+        mutation_path="loose.py",
+        mutation_bytes=(
+            b"LOOSE_VALUE = 0\n"
+            b"# appended nonsemantic comment\n"
+        ),
+        expected_status="UNCHANGED",
+    )
</pre>
