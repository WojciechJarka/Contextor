# L32H1_LOCAL_FALLBACK_PERSIST_ALL_RESULTS

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md is the requested report and is excluded from source/test changes.

The three source/test paths were clean before editing. Scoped post-edit status reports exactly those three modified paths. No other production or test file was changed. Commits, HEAD, and SHA were not inspected.

## CURRENT_SOURCE_VERIFICATION

DIRECT_EVIDENCE — Contextor MCP before the source edit:

- Read current MCP documentation and discovered the Contextor source, call-context, lineage, blast-radius, and LIVE-event tools before using them.
- update_file was fetched in full from contextor/mcp/tools/update_file.py, lines 188–295. Contextor marked implementation_is_complete=true, no_partial_symbol_source=true, canonical state fresh, and workspace_sync=verified at revision 194 before source editing.
- The exact defect was present in the local branch: call _persist_live_engine only for UPDATED/DELETED; all other result statuses set live_state_persisted=True without the helper call.
- _persist_live_engine was fetched in full, lines 73–104. It returns false when save_engine_state returns no metadata; after metadata it updates the engine/revision and invokes the manager save path when available, then returns true.
- IncrementalAnalysisEngine.update_file was fetched as a complete Contextor source range, lines 453–736 of a 1,046-line file (284 lines; no preview/truncation). It confirms the early UNCHANGED return before parsing, syntax-failure state publication, parse-and-plan semantic no-op, RECOVERED, and UPDATED/DELETED result paths.
- _commit_syntax_candidate and _update_candidate_lineage_slice were fetched as complete implementations; both were workspace-synchronized at revision 194.
- Call context identifies update_file as the sole direct caller of _persist_live_engine in that module. The wrapper constructs the public response and its live_state_persisted field.
- Blast radius: direct static consumers include contextor.mcp_server and four test modules; downstream module reachability reports 32 modules (one production module, contextor.mcp_main, and 31 test modules). Contextor explicitly scopes this to direct static evidence.

DIRECT_EVIDENCE — after the exact source edit:

Contextor fetched the complete updated update_file, lines 188–294, with implementation_is_complete=true, no_partial_symbol_source=true, canonical_state=fresh, workspace_sync=verified, and revision 204. The local branch now calls:

    res = engine.update_file(str(target_file))
    live_state_persisted = _persist_live_engine(
        root,
        engine,
    )

The LIVE-connected branch remains separate and still sets its flag after a successful LIVE update and engine-cache refresh. _persist_live_engine itself was not changed.

## RED_RESULT

Before the production edit, the corrected focused regression command ran 20 cases: 14 failed, 6 passed.

- The six passing cases were the newly added UPDATED/DELETED matrix cases across both helper outcomes (those statuses were already persisted by the old branch), the LIVE-delegation check, and the existing local UPDATED snapshot-hydration integration.
- The 14 failures were the SYNTAX_ERROR, RECOVERED, both UNCHANGED labels, and structured ERROR statuses for both helper return values; the helper-exception contract; syntax-error snapshot hydration; early-UNCHANGED helper invocation; and structured preparation-error persistence.
- Failures showed skipped helper calls, a fabricated true response flag, or missing snapshot hydration for state mutations. The independent LIVE delegation case was green before and after the patch.

## GREEN_RESULT

After the production edit, the new focused regressions passed: 20 passed, 1 third-party Authlib deprecation warning. The complete requested test command passed: 114 passed, 1 third-party Authlib deprecation warning.

## ALL_STATUS_PERSISTENCE_MATRIX

The parameterized local-fallback test forces every connect(root) call to return None. For each returned status it checks one engine update, exactly one persister call, original status preservation, and the public flag against both helper outcomes.

| Engine result status | Helper True | Helper False | Additional real local evidence |
|---|---:|---:|---|
| UPDATED | flag true | flag false | Updated artifact facts survive snapshot hydration. |
| DELETED | flag true | flag false | Local-wrapper result exercised through the isolated status fixture. |
| SYNTAX_ERROR | flag true | flag false | Retained module/artifacts, syntax error, and stale parse marker survive hydration. |
| RECOVERED | flag true | flag false | Recovery snapshot has checked syntax and no old parse-stale entry. |
| Parsed semantic no-op UNCHANGED | flag true | flag false | A parsed no-op persists syntax, lineage, and FileState tracking through hydration. |
| Early UNCHANGED | flag true | flag false | Real engine returns early; a spy confirms the persister is explicitly called. |
| Structured ERROR | flag true | flag false | The engine error branch mutates parse freshness; the resulting state is persisted and hydrates. |

These status-table booleans are tested with an isolated wrapper fixture and a controlled helper return value. The real local integrations use the repository engine and snapshot hydration where listed.

## TRUE_FALSE_RESPONSE_CONTRACT

CODE_PATH_PROVED: In local fallback, the wrapper assigns the helper's Boolean return directly to live_state_persisted. Both Boolean outcomes are covered for all seven listed statuses. If the helper raises, the existing outer exception handler returns status=ERROR and does not include live_state_persisted.

CONTRACT LIMIT: A true flag means _persist_live_engine returned true. It is not a claim of atomic publication across snapshot and FileStateManager storage, crash safety, read-back verification, or power-loss durability.

## SYNTAX_SNAPSHOT_HYDRATION

DIRECT_EVIDENCE: The real local integration starts with a valid indexed provider.py, introduces a syntax error, and calls the public wrapper with connect(root) -> None. It receives SYNTAX_ERROR and a true helper result. After clearing the runtime engine cache and hydrating from the saved snapshot:

- the previous provider module and artifact payloads remain equal to their pre-error values (LKG);
- module_parse_freshness['provider']['state'] == 'stale';
- syntax_diagnostics_by_path['provider.py']['status'] == 'checked_with_errors'.

## RECOVERY_AND_NOOP_HYDRATION

- A subsequent valid parse with changed source returns RECOVERED; its hydrated snapshot contains checked_and_none syntax diagnostics and no provider parse-stale entry.
- The early no-op path returns UNCHANGED without parsing; the persistence spy records one helper call.
- The parsed semantic no-op is driven by a changed file timestamp after the fixture's initial reconciliation, while source text stays identical. It returns UNCHANGED, persists, and hydrates checked_and_none syntax, the same non-empty provider.py lineage source facts, and a FileStateManager record for which has_changed(path) is false.

## LIVE_BRANCH_COMPATIBILITY

The isolated LIVE test returns a successful remote result and verifies delegation with origin='mcp'. The fake local engine is never invoked and the local persister is configured to fail the test if called. The LIVE response retains its existing true flag. No LIVE process or service was restarted.

## TARGETED_TEST_RESULTS

Before production edit (RED): 20 newly added focused cases; 14 failed and 6 passed, as detailed above.

After production edit (new focused regressions):

    20 passed, 1 warning

Complete requested targeted gate:

    & .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py tests/test_mcp_regressions.py tests/test_incremental_equivalence.py::test_incremental_syntax_error tests/test_incremental_equivalence.py::test_incremental_successful_modify_after_failed_modify

    114 passed, 1 warning in 28.27s

The warning is Authlib's third-party deprecation warning from the installed FastMCP environment.

Compilation of the production file and both changed test files passed with .venv\Scripts\python.exe -m py_compile. git diff --check returned exit code 0 with no whitespace errors. Git printed only line-ending notices that LF will be converted to CRLF the next time it touches these files.

## LIVE_REVISION_BEFORE_AFTER

- Initial Contextor baseline: revision 194, activity epoch 9e9a2a2edcb046bba00df0850244ad36, resync_required=false.
- Immediately before the production edit: revision 195, continuous from 194, resync_required=false.
- After edits and tests: revision 204, same activity epoch, event continuity continuous, resync_required=false.
- The watcher emitted revisions 196–204 for the authorized test/source file edits. Revision 199 identifies the production edit to contextor\mcp\tools\update_file.py; later events are the two authorized test files. No artificial file event was generated.

## SOURCE_SYNC_VERIFICATION

Contextor's post-edit complete source fetch reports revision 204, canonical state fresh, workspace_sync=verified, and every returned family marker fresh. Post-edit call context and blast radius also resolve against revision 204. The source fetch was complete and not truncated.

The modified Python file is under the MCP package path. The complete _is_mcp_runtime_source_path and _mcp_runtime_restart_required implementations confirm that changed MCP package code requires a serving MCP process restart when it differs from its startup fingerprint.

## FULL_DIFFS

Complete actual working-tree diffs for every changed production/test file follow. walkthrough.md is the requested report and is not a source/test diff.

FULL_DIFFS_BEGIN
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index 86f3c46..8bcde7e 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -221,10 +221,9 @@ def update_file(
             live_state_persisted = True
         else:
             res = engine.update_file(str(target_file))
-            live_state_persisted = (
-                _persist_live_engine(root, engine)
-                if res.status in {"UPDATED", "DELETED"}
-                else True
+            live_state_persisted = _persist_live_engine(
+                root,
+                engine,
             )
         new_artifacts = engine.state.artifacts.get(module_path, {})
         semantic_diff = _semantic_artifact_diff(old_artifacts, new_artifacts)
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 20e0ec0..9bf8523 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -1,11 +1,15 @@
 """End-to-end MCP test for incremental state persistence and live context hydration."""
 
 import json
+from copy import deepcopy
+import os
 
 import pytest
 import threading
+from types import SimpleNamespace
 
 from contextor import mcp_server
+from contextor.core.analysis.incremental import engine as incremental_engine_module
 from contextor.mcp import report_helpers
 from contextor.mcp import runtime as mcp_runtime
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
@@ -23,10 +27,63 @@ from contextor.core.reference.shared import (
     validate_reexport_facts_by_module,
 )
 from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
+from contextor.mcp.tools import update_file as update_file_module
 
 pytestmark = pytest.mark.live
 
 
+def _build_local_fallback_engine(tmp_path, monkeypatch, source):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    provider = repo / "provider.py"
+    provider.write_text(source, encoding="utf-8")
+    index = index_repository(str(repo))
+    modules = index.modules
+    reexport_facts_by_module = materialize_reexport_facts_by_module(
+        modules,
+        index.reference_facts_by_module,
+    )
+    artifacts, failures = collect_module_artifacts(modules, str(repo))
+    assert not failures
+    trie = build_trie(modules)
+    package_root = detect_package_root(modules, trie)
+    state = RepositoryAnalysisState(
+        modules=dict(modules),
+        reexport_facts_by_module=reexport_facts_by_module,
+        artifacts=artifacts,
+        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
+        trie=trie,
+        package_root=package_root,
+        artifact_consumption={},
+    )
+    registry = PersistentIdentityRegistry(str(repo))
+    with registry.transaction():
+        registry.sync_with_workspace(
+            set(modules), collect_qualified_artifact_identities(artifacts)
+        )
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    cache_dir = repo_cache_dir(repo)
+    state_manager = FileStateManager(str(cache_dir))
+    state_manager.update_state(str(provider))
+    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(repo))
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo.resolve()): engine})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
+    return repo, provider, engine
+
+
+def _local_update(repo, provider):
+    return json.loads(
+        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(provider))
+    )
+
+
+def _rehydrate_local_engine(repo):
+    mcp_runtime._live_engines.clear()
+    return mcp_runtime.get_or_init_engine(repo.resolve())
+
+
 def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
     first = RepositoryAnalysisState(modules={"old": object()})
     second = RepositoryAnalysisState(modules={"new": object()})
@@ -147,3 +204,139 @@ def test_update_persist_restart_hydrate_keeps_live_reverse_context(tmp_path, mon
         {"module_id": registry.get_module_id("consumer"), "module": "consumer"}
     ]
     assert context["dependency_data_source"] == "live_canonical_graph"
+
+
+def test_local_fallback_updated_facts_survive_snapshot_hydration(tmp_path, monkeypatch):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    original_artifacts = deepcopy(engine.state.artifacts["provider"])
+    provider.write_text(
+        "def run():\n    return 1\n\ndef added():\n    return 2\n",
+        encoding="utf-8",
+    )
+
+    response = _local_update(repo, provider)
+    assert response["status"] == "UPDATED"
+    assert response["live_state_persisted"] is True
+
+    updated_engine = mcp_runtime._live_engines[str(repo.resolve())]
+    assert updated_engine.state.artifacts["provider"] != original_artifacts
+    hydrated = _rehydrate_local_engine(repo)
+    assert hydrated is not None
+    assert hydrated.state.artifacts["provider"] == updated_engine.state.artifacts["provider"]
+
+
+def test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    original_module = deepcopy(engine.state.modules["provider"])
+    original_artifacts = deepcopy(engine.state.artifacts["provider"])
+
+    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
+    syntax_error = _local_update(repo, provider)
+    assert syntax_error["status"] == "SYNTAX_ERROR"
+    assert syntax_error["live_state_persisted"] is True
+
+    syntax_hydrated = _rehydrate_local_engine(repo)
+    assert syntax_hydrated is not None
+    assert syntax_hydrated.state.modules["provider"] == original_module
+    assert syntax_hydrated.state.artifacts["provider"] == original_artifacts
+    assert syntax_hydrated.state.module_parse_freshness["provider"]["state"] == "stale"
+    assert (
+        syntax_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
+        == "checked_with_errors"
+    )
+
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    recovered = _local_update(repo, provider)
+    assert recovered["status"] == "RECOVERED"
+    assert recovered["live_state_persisted"] is True
+
+    recovered_hydrated = _rehydrate_local_engine(repo)
+    assert recovered_hydrated is not None
+    assert "provider" not in recovered_hydrated.state.module_parse_freshness
+    assert (
+        recovered_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
+        == "checked_and_none"
+    )
+
+
+def test_local_fallback_early_and_parsed_unchanged_are_persisted_and_hydrated(
+    tmp_path, monkeypatch
+):
+    repo, provider, _engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    real_persist = update_file_module._persist_live_engine
+    persist_calls = []
+
+    def persist_and_record(root, engine):
+        persist_calls.append((root, engine))
+        return real_persist(root, engine)
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist_and_record)
+
+    early_unchanged = _local_update(repo, provider)
+    assert early_unchanged["status"] == "UNCHANGED"
+    assert early_unchanged["live_state_persisted"] is True
+    assert len(persist_calls) == 1
+
+    stat = provider.stat()
+    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
+    reconciled = _local_update(repo, provider)
+    assert reconciled["status"] in {"UPDATED", "UNCHANGED"}
+    assert reconciled["live_state_persisted"] is True
+    assert len(persist_calls) == 2
+
+    stat = provider.stat()
+    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
+    parsed_unchanged = _local_update(repo, provider)
+    assert parsed_unchanged["status"] == "UNCHANGED", parsed_unchanged
+    assert parsed_unchanged["live_state_persisted"] is True
+    assert len(persist_calls) == 3
+
+    parsed_engine = mcp_runtime._live_engines[str(repo.resolve())]
+    expected_lineage = deepcopy(parsed_engine.state.lineage_facts_by_source)
+    assert "provider.py" in expected_lineage
+    hydrated = _rehydrate_local_engine(repo)
+    assert hydrated is not None
+    assert (
+        hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
+        == "checked_and_none"
+    )
+    assert hydrated.state.lineage_facts_by_source == expected_lineage
+    assert hydrated.state_manager.has_changed(str(provider)) is False
+
+
+def test_local_fallback_structured_preparation_error_persists_published_mutations(
+    tmp_path, monkeypatch
+):
+    repo, provider, _engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    provider.write_text(
+        "def run():\n    return 1\n# trigger preparation\n", encoding="utf-8"
+    )
+    monkeypatch.setattr(
+        incremental_engine_module,
+        "prepare_source_update",
+        lambda **_kwargs: SimpleNamespace(
+            has_error=True,
+            error_status="ERROR",
+            error_message="structured preparation failure",
+            line_number=2,
+            column_number=3,
+        ),
+    )
+
+    response = _local_update(repo, provider)
+    assert response["status"] == "ERROR"
+    assert response["live_state_persisted"] is True
+
+    hydrated = _rehydrate_local_engine(repo)
+    assert hydrated is not None
+    assert hydrated.state.module_parse_freshness["provider"]["state"] == "stale"
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index b4bbe05..010bdeb 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -2737,6 +2737,175 @@ def test_mcp_update_file_shapes_affected_modules_compact_full_and_fields(tmp_pat
     assert filtered["status"] == "UPDATED"
 
 
+@pytest.mark.parametrize(
+    ("result_status", "path_kind"),
+    [
+        pytest.param("UPDATED", "updated", id="updated"),
+        pytest.param("DELETED", "deleted", id="deleted"),
+        pytest.param("SYNTAX_ERROR", "syntax-error", id="syntax-error"),
+        pytest.param("RECOVERED", "recovered", id="recovered"),
+        pytest.param("UNCHANGED", "parsed-semantic-no-op", id="parsed-unchanged"),
+        pytest.param("UNCHANGED", "early-no-op", id="early-unchanged"),
+        pytest.param("ERROR", "structured-error", id="structured-error"),
+    ],
+)
+@pytest.mark.parametrize("persisted", [True, False], ids=["persisted", "not-persisted"])
+def test_mcp_update_file_local_fallback_persists_every_returned_status(
+    tmp_path, monkeypatch, result_status, path_kind, persisted
+):
+    root = tmp_path.resolve()
+    target = root / "provider.py"
+    target.write_text("def run():\n    return 1\n", encoding="utf-8")
+    connect_calls = []
+    update_calls = []
+    persist_calls = []
+
+    result = SimpleNamespace(
+        status=result_status,
+        file_path=str(target),
+        graph_state="fresh",
+        dependencies_state="fresh",
+        blast_radius_state="deferred",
+        local_metrics_state="deferred",
+        global_metrics_state="deferred",
+        artifact_consumption_state="fresh",
+        affected_modules=[],
+        delta=None,
+    )
+
+    class FakeEngine:
+        state = SimpleNamespace(artifacts={"provider": {}})
+
+        def update_file(self, file_path):
+            update_calls.append(file_path)
+            return result
+
+    engine = FakeEngine()
+
+    def connect(_root):
+        connect_calls.append(_root)
+        return None
+
+    def persist(_root, candidate_engine):
+        persist_calls.append((_root, candidate_engine))
+        return persisted
+
+    monkeypatch.setattr("contextor.core.live_state.connect", connect)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
+    monkeypatch.setattr(
+        update_file_module, "_mcp_runtime_restart_required", lambda _path: False
+    )
+
+    response = json.loads(
+        mcp_server.update_file.fn(repo_path=str(root), file_path=str(target))
+    )
+
+    assert bool(path_kind)
+    assert connect_calls
+    assert all(call_root == root for call_root in connect_calls)
+    assert update_calls == [str(target)]
+    assert persist_calls == [(root, engine)]
+    assert response["status"] == result_status
+    assert response["live_state_persisted"] is persisted
+
+
+def test_mcp_update_file_live_branch_delegates_without_local_persistence(
+    tmp_path, monkeypatch
+):
+    root = tmp_path.resolve()
+    target = root / "provider.py"
+    target.write_text("def run():\n    return 1\n", encoding="utf-8")
+    remote_result = SimpleNamespace(
+        status="UPDATED",
+        file_path=str(target),
+        graph_state="fresh",
+        dependencies_state="fresh",
+        blast_radius_state="fresh",
+        local_metrics_state="deferred",
+        global_metrics_state="deferred",
+        artifact_consumption_state="fresh",
+        affected_modules=[],
+        delta=None,
+    )
+    remote_calls = []
+
+    class FakeLiveClient:
+        def update_file(self, file_path, *, origin):
+            remote_calls.append((file_path, origin))
+            return {"status": "ok", "revision": 42, "result": remote_result}
+
+    engine = SimpleNamespace(
+        state=SimpleNamespace(artifacts={"provider": {}}),
+        update_file=lambda *_args: pytest.fail("LIVE path used local engine update"),
+    )
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect", lambda _root: FakeLiveClient()
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(
+        mcp_runtime,
+        "_engine_cache_transaction",
+        lambda _root: nullcontext(str(root)),
+    )
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr(
+        update_file_module,
+        "_persist_live_engine",
+        lambda *_args: pytest.fail("LIVE path called the local persister"),
+    )
+    monkeypatch.setattr(
+        update_file_module, "_mcp_runtime_restart_required", lambda _path: False
+    )
+
+    response = json.loads(
+        mcp_server.update_file.fn(repo_path=str(root), file_path=str(target))
+    )
+
+    assert remote_calls == [(str(target), "mcp")]
+    assert response["status"] == "UPDATED"
+    assert response["live_state_persisted"] is True
+
+
+def test_mcp_update_file_local_persistence_exception_keeps_error_response(
+    tmp_path, monkeypatch
+):
+    root = tmp_path.resolve()
+    target = root / "provider.py"
+    target.write_text("def run():\n    return 1\n", encoding="utf-8")
+    result = SimpleNamespace(
+        status="SYNTAX_ERROR",
+        file_path=str(target),
+        graph_state="stale",
+        dependencies_state="stale",
+        blast_radius_state="deferred",
+        local_metrics_state="deferred",
+        global_metrics_state="deferred",
+        artifact_consumption_state="stale",
+        affected_modules=[],
+        delta=None,
+    )
+    engine = SimpleNamespace(
+        state=SimpleNamespace(artifacts={"provider": {}}),
+        update_file=lambda _path: result,
+    )
+
+    def fail_persist(*_args):
+        raise OSError("snapshot persistence failed")
+
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", fail_persist)
+
+    response = json.loads(
+        mcp_server.update_file.fn(repo_path=str(root), file_path=str(target))
+    )
+
+    assert response["status"] == "ERROR"
+    assert "snapshot persistence failed" in response["error"]
+    assert "live_state_persisted" not in response
+
+
 
 def test_mcp_bootstrap_keeps_an_existing_virtual_environment(monkeypatch):
     monkeypatch.setattr(mcp_server.sys, "prefix", "C:/repo/.venv")
FULL_DIFFS_END

## REMAINING_ATOMICITY_RISKS

OUT OF SCOPE / NOT CERTIFIED: This patch does not roll back canonical RAM state if persistence returns false or raises. It does not prove atomic snapshot plus FileStateManager publication, partial-write crash safety, read-back durability, or recovery from a split disk state. A persister exception still becomes an ERROR response after engine execution may already have mutated RAM.

## RESTART_REQUIRED

YES — MCP server process. The changed update_file.py is MCP package source, and the existing restart gate treats changed package code as requiring restart relative to its startup fingerprint. No MCP, Desktop, or LIVE process was restarted. The tests and Contextor source synchronization do not certify that an already-running MCP process imported the new code.

## FINAL_VERDICT

FOCUSED_PATCH_PASS; TARGETED_TESTS_PASS; MCP_RUNTIME_RELOAD_PENDING. The exact authorized local-fallback change is present, the complete targeted gate passed, Contextor confirms the updated source is synchronized, and watcher revisions are continuous with no resync requirement. Serving-process behavior awaits the required manual MCP restart and a separate runtime certification.



