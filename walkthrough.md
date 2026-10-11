# L03_FRESH_PROCESS_LKG_PARSE_DIAGNOSTIC_REGRESSION

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` (report only, excluded from source/test diff accounting)

## FULL_DIFFS

```diff
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index 95e7d4f..51e7b70 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -99,6 +99,146 @@ def _engine_for_file(tmp_path):
     )
 
 
+def _l03_fresh_process_hydration_worker(
+    repo_path: str,
+    cache_path: str,
+    stale_state_id: str,
+    stale_revision: int,
+) -> None:
+    from pathlib import Path
+
+    from contextor.core.analysis.incremental_engine import (
+        IncrementalAnalysisEngine,
+    )
+    from contextor.core.analysis.state_manager import (
+        FileStateManager,
+        module_current_truth,
+        save_engine_state,
+    )
+    from contextor.core.live_state.store import load_snapshot
+    from contextor.core.reporting_engine.persistent_registry import (
+        PersistentIdentityRegistry,
+    )
+
+    root = Path(repo_path)
+    source = root / "provider.py"
+
+    loaded = load_snapshot(cache_path, stale_state_id)
+    assert loaded is not None
+
+    state, metadata = loaded
+
+    assert metadata.state_id == stale_state_id
+    assert metadata.revision == stale_revision
+    assert state.state_id == stale_state_id
+    assert state.revision == stale_revision
+    assert state.provenance == "snapshot"
+
+    # All three domains must coexist in ONE hydrated generation.
+    assert "helper" in state.artifacts["provider"]["own_symbols"]
+
+    assert module_current_truth(state, "provider") == {
+        "available": False,
+        "state": "stale",
+        "provenance": "last_known_good",
+        "reason": (
+            "Current source could not be parsed; "
+            "canonical facts are last-known-good."
+        ),
+        "parse_failure": {
+            "error": "'(' was never closed",
+            "line_number": 1,
+            "column_number": 11,
+        },
+    }
+
+    assert state.syntax_diagnostics_by_path["provider.py"] == {
+        "status": "checked_with_errors",
+        "errors": [
+            {
+                "message": "'(' was never closed",
+                "line_number": 1,
+                "column_number": 11,
+            }
+        ],
+    }
+
+    # Construct the engine independently in the spawned process.
+    engine = IncrementalAnalysisEngine(
+        state,
+        PersistentIdentityRegistry(str(root)),
+        FileStateManager(str(root / ".state")),
+        str(root),
+    )
+
+    # Replace invalid source with valid source containing a
+    # different canonical symbol to prove actual artifact recovery.
+    source.write_text(
+        "def replacement(value: int) -> int:\n"
+        "    return value + 2\n",
+        encoding="utf-8",
+    )
+
+    recovered = engine.update_file(str(source))
+
+    assert recovered.status == "RECOVERED"
+
+    assert module_current_truth(state, "provider") == {
+        "available": True,
+        "state": "fresh",
+        "provenance": "current",
+    }
+
+    assert "replacement" in state.artifacts["provider"]["own_symbols"]
+    assert "helper" not in state.artifacts["provider"]["own_symbols"]
+
+    assert state.syntax_diagnostics_by_path["provider.py"] == {
+        "status": "checked_and_none",
+        "errors": [],
+    }
+
+    # Persist and independently reload the recovered generation.
+    recovered_state_id = "l03-recovered"
+    recovered_metadata = save_engine_state(
+        state,
+        cache_path,
+        recovered_state_id,
+        writer="l03-regression",
+    )
+
+    assert recovered_metadata is not None
+    assert recovered_metadata.revision == stale_revision + 1
+    assert recovered_metadata.state_id == recovered_state_id
+
+    recovered_snapshot = load_snapshot(
+        cache_path,
+        recovered_state_id,
+    )
+    assert recovered_snapshot is not None
+
+    final_state, final_metadata = recovered_snapshot
+
+    assert final_metadata.revision == stale_revision + 1
+    assert final_metadata.state_id == recovered_state_id
+    assert final_state.revision == final_metadata.revision
+    assert final_state.state_id == final_metadata.state_id
+    assert final_state.provenance == "snapshot"
+
+    assert module_current_truth(final_state, "provider") == {
+        "available": True,
+        "state": "fresh",
+        "provenance": "current",
+    }
+
+    assert "replacement" in final_state.artifacts["provider"]["own_symbols"]
+    assert "helper" not in final_state.artifacts["provider"]["own_symbols"]
+
+    assert final_state.syntax_diagnostics_by_path["provider.py"] == {
+        "status": "checked_and_none",
+        "errors": [],
+    }
+
+
 def _stale_mcp_state(tmp_path):
     module = SimpleNamespace(
         module_id="1/1",
@@ -472,6 +612,89 @@ def test_parse_freshness_survives_snapshot_hydration_and_recovers(tmp_path):
     assert module_current_truth(loaded, "provider")["provenance"] == "current"
 
 
+def test_l03_fresh_process_lkg_parse_diagnostic_and_recovery(tmp_path):
+    import multiprocessing
+
+    from contextor.core.analysis.state_manager import save_engine_state
+    from contextor.core.live_state.store import load_snapshot
+
+    source, engine = _engine_for_file(tmp_path)
+
+    # Establish canonical last-known-good symbols.
+    assert "helper" in engine.state.artifacts["provider"]["own_symbols"]
+
+    # Create a parse failure without replacing LKG artifacts.
+    source.write_text("def helper(\n", encoding="utf-8")
+
+    failed = engine.update_file(str(source))
+
+    assert failed.status == "SYNTAX_ERROR"
+    assert failed.error == "'(' was never closed"
+    assert failed.line_number == 1
+    assert failed.column_number == 11
+
+    assert "helper" in engine.state.artifacts["provider"]["own_symbols"]
+
+    cache = tmp_path / "l03-cache"
+    stale_state_id = "l03-stale"
+
+    stale_metadata = save_engine_state(
+        engine.state,
+        str(cache),
+        stale_state_id,
+        writer="l03-regression",
+    )
+
+    assert stale_metadata is not None
+    assert stale_metadata.state_id == stale_state_id
+
+    # A genuinely new Python interpreter must read the persisted
+    # generation. It must not receive the parent engine or state.
+    ctx = multiprocessing.get_context("spawn")
+
+    worker = ctx.Process(
+        target=_l03_fresh_process_hydration_worker,
+        args=(
+            str(tmp_path),
+            str(cache),
+            stale_state_id,
+            stale_metadata.revision,
+        ),
+    )
+
+    try:
+        worker.start()
+        worker.join(timeout=45)
+
+        assert worker.exitcode == 0, (
+            "Fresh-process L03 hydration/recovery worker failed "
+            f"or timed out: exitcode={worker.exitcode}"
+        )
+    finally:
+        if worker.pid is not None and worker.is_alive():
+            worker.terminate()
+            worker.join(timeout=5)
+
+    # Verify the recovered generation from the parent process too.
+    recovered = load_snapshot(str(cache), "l03-recovered")
+
+    assert recovered is not None
+    recovered_state, recovered_metadata = recovered
+
+    assert recovered_metadata.revision == stale_metadata.revision + 1
+    assert recovered_state.revision == recovered_metadata.revision
+    assert recovered_state.state_id == recovered_metadata.state_id
+
+    assert (
+        recovered_state.syntax_diagnostics_by_path["provider.py"]["status"]
+        == "checked_and_none"
+    )
+
+    assert "replacement" in (
+        recovered_state.artifacts["provider"]["own_symbols"]
+    )
+
+
 @pytest.mark.parametrize(
     "raw_map",
     [{"provider": {"state": "unknown"}}, ["bad"]],
```

## EXACT_TARGETED_TEST_RESULTS

1. New named regression: `tests/test_live_e2e_corrections.py::test_l03_fresh_process_lkg_parse_diagnostic_and_recovery` — **1 passed, 1 warning in 23.80s**. Process exit code 0.
2. Related named regressions: `test_parse_freshness_survives_snapshot_hydration_and_recovers`, `test_syntax_error_marks_authoritative_last_known_good_and_recovery`, `test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration`, `test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction`, `test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic` — **5 passed, 1 warning in 8.11s**.
3. `git diff --check -- tests/test_live_e2e_corrections.py` — exit code 0; no whitespace errors. Git emitted only an LF→CRLF advisory.
4. Warning in pytest: installed FastMCP/Authlib `AuthlibDeprecationWarning`. No test failures.

## CHILD_PROCESS_EXIT_CODE

0, asserted by the parent test after `worker.join(timeout=45)`. The worker is a module-level picklable function started with `multiprocessing.get_context("spawn")`.

## FRESH_PROCESS_PROOF

DIRECT_EVIDENCE: The parent passes only repository/cache paths, stale state ID, and stale revision as arguments, not its engine/state. The spawned child calls `load_snapshot(cache_path, stale_state_id)`, checks persisted metadata and state identity, then constructs its own registry, FileStateManager and IncrementalAnalysisEngine. On Windows `spawn` creates a new interpreter. The child asserts the LKG artifact, stale parse marker and exact syntax fact in the same loaded generation before correcting the source.

## LKG_ARTIFACT_ASSERTIONS

Parent baseline and post-error both retain `helper`. Child loaded stale generation retains `helper`. After a verified valid parse the child and its recovered snapshot contain `replacement` and omit `helper`. The parent independently reloads the recovered snapshot and sees `replacement`.

## PARSE_FRESHNESS_ASSERTIONS

The child asserts `module_current_truth(state, "provider")` exactly equals unavailable/stale/last_known_good with the parse-failure detail. After successful recovery it asserts the exact available/fresh/current dictionary in RAM and in the recovered snapshot. Thus retained LKG is not represented as current source truth.

## EXACT_DIAGNOSTIC_ASSERTIONS

Before recovery, the child checks `syntax_diagnostics_by_path["provider.py"]` equals `checked_with_errors` with one error: `'(' was never closed`, line 1, column 11. After recovery it checks `checked_and_none` and an empty errors list, both in RAM and independently reloaded snapshot. Parent confirms recovered `checked_and_none`.

## RECOVERY_ASSERTIONS

The spawned child writes corrected source defining a different canonical symbol, invokes `engine.update_file`, and asserts `RECOVERED`, fresh parse truth, new artifact, old artifact removal and cleared syntax diagnostic. No production code was changed to obtain this result.

## REVISION_STATE_ID_PARITY

The child checks stale metadata/state ID and revision equality after disk load. It asserts recovered snapshot metadata revision equals stale revision + 1 and state_id `l03-recovered`; loaded state revision/state_id match metadata. The parent independently verifies recovered revision/state_id parity.

## PRODUCTION_CODE_UNCHANGED

YES. Git status after the patch showed only `tests/test_live_e2e_corrections.py` modified before report write. No source, fixture or docs edits. No manual MCP `update_file`, full analysis, process restart or commit.

## WORKSPACE_SYNC

Before edit, Contextor MCP returned `workspace_sync=verified`, `canonical_state=fresh`, revision 327 for `_engine_for_file`, the insertion-boundary tests and production symbols. After edit, Contextor fetched the complete new test and worker with `implementation_is_complete=true`, `workspace_sync=verified`, `canonical_state=fresh`, revision 328. The test file context also reported verified.

## LIVE_REVISION_BEFORE_AFTER

Before: 327. After: 328. `get_live_events(after_revision=327)` showed exactly one canonical event for the edited test file, origin `desktop_watcher`, status `UPDATED`, revision 328. This is the expected watcher propagation, not a manual `update_file` call.

## RESYNC_REQUIRED

false in the post-edit Contextor LIVE event response. Source retrieval and file edit context are fresh/verified.

## RESTART_REQUIRED

NO. The change is test-only; no serving production implementation was edited.

## FINAL_VERDICT

**L03_FINAL_PASS** — all requested integrated fresh-process assertions and directly related named regressions passed. This certifies the tested fixture and code path; it does not claim a full-suite rerun.

