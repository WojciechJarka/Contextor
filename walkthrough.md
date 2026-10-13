# CONTEXTOR_B0G2D7C4_PACKAGE_REFERENCE_DETAIL_PARITY

FINAL_VERDICT=B0G2D7C4_REGRESSION_BLOCKED
STOP_REASON=The first focused test run stopped at a test-fixture setup error under pytest -x. No matrix or follow-up test was run.

## FILES_CHANGED
FILES_CHANGED=
- contextor/core/reference/engine.py
- tests/test_package_reference_detail_parity.py

walkthrough.md is the requested report artifact and is excluded from FILES_CHANGED. No other source, test, or documentation file was modified.

## SOURCE_PRECHECK
DIRECT_EVIDENCE:
- HEAD before edit: c7483ac6cbd689c5e1066d8c2efb8c5048b4bd4d.
- Working tree was clean before edit.
- Contextor MCP returned current complete implementations at canonical revision 387 with workspace_sync=verified for _usage_fact_contains_target, build_symbol_references_from_canonical, RepositoryReferenceIndex.from_compact_facts, _canonicalize_package_reference_target, and _refresh_canonical_artifact_consumers.
- The exact import, matcher signature, and five confirmed-channel call-site anchors were present in reference/engine.py. The called_ambiguous call is separate and was left unchanged.
- Contextor artifact_consumption fact lineage identified the canonical RepositoryAnalysisState.artifact_consumption owner, FULL producer, incremental consumer-slice rebuild, persistence, hydration, and public projections.
- Contextor module blast radius at revision 387: reference.engine 20 direct / 219 downstream consumer modules; reference.index 9 / 231; reference.shared 37 / 213; incremental.plan_executor 12 / 222. This tool reported workspace_sync=unverified; the exact engine file edit context reported verified.
- LIVE before edit: revision 387, continuity=continuous, resync_required=false.

CODE_PATH_PROVED:
- FULL RepositoryReferenceIndex.from_compact_facts applies _resolve_reexport and then _canonicalize_package_reference_target to resolved call targets.
- _canonicalize_package_reference_target gives a real indexed module the longest-prefix precedence, otherwise maps external package references through the package initializer.
- Incremental _refresh_canonical_artifact_consumers calls build_symbol_references_from_canonical with current_modules=set(candidate.modules).
- Before the edit, _usage_fact_contains_target compared the raw source-local target with alpha.__init__.api_function and returned false. The existing FULL normalizer maps alpha.api_function to alpha.__init__.api_function for the current module set, after which the same matcher returns true.
- With a real alpha.api_function module added to the module set, the normalizer preserves alpha.api_function unchanged.

CONTRACT_PROVED: The preserved E evidence and the inspected source support the specified normalization difference. No SOURCE_CONTRACT_MISMATCH was found.

## CASE_E_PRESERVED_EVIDENCE
READ_ONLY_SOURCE=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-580\test_case_e_reexport_retarget_0\b0g2d7a_e_evidence
Read incremental.pickle, fresh_full.pickle, and summary.json without modifying them. Both states contain modules alpha.__init__, alpha.api, beta.__init__, beta.consumer, and loose. Both have materialized beta.consumer reference evidence and the same alias. The prior first canonical difference is alpha.__init__ / consumers / api_function / usage / direct_calls_detail length: incremental 0, fresh FULL 1.

## RAW_REFERENCE_EVIDENCE
Both preserved E states have beta.consumer.reference_evidence:
- ('alpha.api_function', 'api_imports', '', 1)
- ('alpha.api_function', 'direct_calls', '', 2)
Both have beta.consumer.aliases=(('api_function', 'alpha.api_function'),).
reference_evidence_materialized=true in both.

## CONFIRMED_CONSUMPTION_CHANNELS
Both preserved E states have artifact_consumption['alpha.__init__::api_function']={'consumers': ['beta.consumer'], 'channels': {'beta.consumer': ['api_imports', 'direct_calls']}}.
Both consumer records contain direct_calls=['beta.consumer'], api_imports=['beta.consumer'], and consumer_count total=1/direct_calls=1/api_imports=1. The incremental direct_calls_detail is []; fresh FULL has [{'module': 'beta.consumer', 'line': 2, 'context': None}]. No other usage field differed in the inspected record.

## FULL_PACKAGE_CANONICALIZATION_CONTRACT
For current_modules={alpha.__init__, alpha.api, beta.consumer}, the existing helper returns alpha.__init__.api_function for alpha.api_function. The raw matcher returned false; matching after this existing normalization returned true. With a real alpha.api_function module identity present, the helper returns alpha.api_function unchanged.

## EXACT_MATCHER_PATCH
Added the exact approved _canonicalize_package_reference_target import. Added keyword-only current_modules: set[str] | None = None. For a package-initializer definer with supplied current_modules, the matcher now canonicalizes fact_target and each alias target before its unchanged canonical_identity comparison. No source read, parse, or new resolver was added.

## DETAIL_PROJECTION_CALL_SITES
Added current_modules=candidate_modules to the five approved matcher calls: direct_calls, callback_calls, event_bindings, qualified_refs, inheritance. The called_ambiguous call, channel gates, reference_evidence storage, normalization, and detail ordering were unchanged.

## REAL_SUBMODULE_PRECEDENCE
SOURCE CONTRACT AND READ-ONLY HELPER CHECK PASS: alpha.api_function stays alpha.api_function when it is an indexed module, so the matcher does not attribute that target to alpha.__init__::api_function. The new targeted test for this condition was not reached because pytest stopped earlier.

## REEXPORT_RETARGET_REGRESSION
NOT REACHED. The module-scoped isolated fixture completed its initial real FULL and hydration but failed while reading a presumed pre-retarget consumer record, before changing alpha/__init__.py or calling engine.update_file. The new test therefore did not compare incremental and fresh FULL records.

## COW_AND_FAIL_CLOSED
NOT RUN because focused pytest stopped at fixture setup.

## NO_SOURCE_REPARSE
The changed matcher and canonical projection path only use supplied in-memory values by source inspection. The new no-I/O regression was not run because focused pytest stopped at fixture setup.

## FOCUSED_TEST_RESULTS
COMMAND=.venv\Scripts\python.exe -m pytest -q -x -s tests/test_package_reference_detail_parity.py
RESULT=1 passed, 1 error in 6.12s; exit code 1; stopped under -x.
PASSED=test_package_initializer_match_uses_current_module_domain
FIRST_ERROR=ERROR at setup of test_real_import_alias_is_canonicalized
TRACEBACK_LOCATION=tests/test_package_reference_detail_parity.py:81 in retargeted_states
TRACEBACK_EXPRESSION=original_state.artifacts["alpha.__init__"]["consumers"]["api_function"]
EXCEPTION=KeyError: 'api_function'
DIRECT_EVIDENCE: The initial pre-retarget FULL state had no api_function key in that initializer consumer mapping. This is a test fixture assumption; it is not a new canonical parity comparison or a production exception. No test/code repair was attempted after the first failure.

## SIX_MUTATION_MATRIX_RESULTS
NOT RUN: focused gate failed first. The unchanged six-mutation matrix was not modified.

## CASE_A_TO_F_STATUS
CURRENT_TASK_MATRIX_A=NOT RUN
CURRENT_TASK_MATRIX_B=NOT RUN
CURRENT_TASK_MATRIX_C=NOT RUN
CURRENT_TASK_MATRIX_D=NOT RUN
CURRENT_TASK_MATRIX_E=NOT RUN
CURRENT_TASK_MATRIX_F=NOT RUN
Historical B0G2D7C3 matrix evidence remains A-D PASS, E CANONICAL_STATE mismatch, F NOT RUN; it was not reclassified by this task.

## FIRST_MISMATCH_IF_ANY
NO NEW PARITY MISMATCH MEASURED. The first current-task failure is the focused fixture KeyError above.

## PRESERVED_EVIDENCE
- Prior E evidence directory and its initial_full.pickle, incremental.pickle, fresh_full.pickle, and summary.json remain in place.
- Current focused fixture root and cache remain at C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-581\package_reference_detail0. Their existence was checked read-only.
- Pytest traceback and the exact failing expression are recorded above. No snapshot was rewritten or deleted after the failure.

## FOUR_WAY_PARITY_IF_EXECUTED
NOT EXECUTED.

## ATOMICITY_RECHECK_IF_EXECUTED
NOT EXECUTED.

## OTHER_TARGETED_REGRESSIONS
NOT EXECUTED. The focused gate failed before the six-mutation matrix and conditional Desktop/MCP, atomicity, layer, collision, FileState, canonical-reference, and channel-parity regressions.

## PY_COMPILE
PASS, exit code 0:
.venv\Scripts\python.exe -m py_compile contextor/core/reference/engine.py tests/test_package_reference_detail_parity.py

## GIT_DIFF_CHECK
PASS: git diff --check exit code 0 for the tracked production file.
PASS: explicit trailing whitespace check found no affected lines among all 258 lines of the new untracked test file.
Git emitted an LF-to-CRLF working-copy advisory only.

## LIVE_REVISION_BEFORE_AFTER
BEFORE=387
AFTER=390
REVISION_388=desktop_watcher UPDATED contextor/core/reference/engine.py
REVISION_389=desktop_watcher UPDATED tests/test_package_reference_detail_parity.py
REVISION_390=desktop_watcher UNCHANGED tests/test_package_reference_detail_parity.py
CONTINUITY=continuous

The revision 389 event also added one NAME_COLLISION diagnostic for top-level SOURCES between tests.test_full_file_state_domain_reconciliation and tests.test_package_reference_detail_parity. This observed diagnostic was not modified after the first focused failure.

## WORKSPACE_SYNC_POSTCHECK
workspace_sync=verified, canonical_state=fresh, canonical_revision=390 for edited engine.py and the new test file. Contextor syntax diagnostics were checked and none for both.

## RESYNC_REQUIRED
false at LIVE revision 390.

## RESTART_REQUIRED
YES before operational serving-process certification after the production source edit. No MCP, LIVE, or Desktop restart was performed by the agent. LIVE indexing does not prove serving-process reload.

## SAFETY_AND_STOP
FULL_CONTEXTOR_REPO_ANALYSIS=NO
FLASK_BENCHMARK=NO
MANUAL_UPDATE_FILE=NO
SERVICE_RESTART=NO
COMMIT_RESET_CHECKOUT=NO
FULL_PYTEST_SUITE=NO
INDEPENDENT_REDESIGN_AFTER_FAILURE=NO
Await command proceduj.

## FULL_DIFFS
ACTUAL_DIFF=Full git-style diffs for both FILES_CHANGED follow.

~~~~diff
diff --git a/contextor/core/reference/engine.py b/contextor/core/reference/engine.py
index 0d9b1e3..6ff95c1 100644
--- a/contextor/core/reference/engine.py
+++ b/contextor/core/reference/engine.py
@@ -24,6 +24,7 @@ from .shared import (
     MAX_USAGE_DETAILS,
     _REEXPORT_CACHE,
     _build_reexport_map,
+    _canonicalize_package_reference_target,
     _empty_reference,
     _export_module_name,
     _normalize_references,
@@ -795,8 +796,31 @@ def _usage_fact_contains_target(
     definer_module: str,
     symbol: str,
     aliases: tuple[tuple[str, str], ...] = (),
+    *,
+    current_modules: set[str] | None = None,
 ) -> bool:
     """Check whether an outbound usage fact target matches the requested definer::symbol."""
+    if (
+        current_modules is not None
+        and definer_module.endswith(".__init__")
+    ):
+        fact_target = (
+            _canonicalize_package_reference_target(
+                fact_target,
+                current_modules,
+            )
+        )
+        aliases = tuple(
+            (
+                local_alias,
+                _canonicalize_package_reference_target(
+                    target,
+                    current_modules,
+                ),
+            )
+            for local_alias, target in aliases
+        )
+
     canonical_identity = f"{definer_module}.{symbol}"
 
     if fact_target == canonical_identity or fact_target == symbol:
@@ -903,7 +927,8 @@ def build_symbol_references_from_canonical(
                     result[symbol]["called_by"].append(consumer)
                     for item in reference_evidence:
                         if item[1] == "direct_calls" and _usage_fact_contains_target(
-                            item[0], definer_module, symbol, aliases
+                            item[0], definer_module, symbol, aliases,
+                            current_modules=candidate_modules,
                         ):
                             result[symbol]["called_by_detail"].append(
                                 {
@@ -917,7 +942,8 @@ def build_symbol_references_from_canonical(
                     result[symbol]["callback_called"].append(consumer)
                     for item in reference_evidence:
                         if item[1] == "callback_calls" and _usage_fact_contains_target(
-                            item[0], definer_module, symbol, aliases
+                            item[0], definer_module, symbol, aliases,
+                            current_modules=candidate_modules,
                         ):
                             result[symbol]["callback_called_detail"].append(
                                 {
@@ -931,7 +957,8 @@ def build_symbol_references_from_canonical(
                     result[symbol]["event_bound_by"].append(consumer)
                     for item in reference_evidence:
                         if item[1] == "event_bindings" and _usage_fact_contains_target(
-                            item[0], definer_module, symbol, aliases
+                            item[0], definer_module, symbol, aliases,
+                            current_modules=candidate_modules,
                         ):
                             result[symbol]["event_bound_by_detail"].append(
                                 {
@@ -945,7 +972,8 @@ def build_symbol_references_from_canonical(
                     result[symbol]["qualified_refs"].append(consumer)
                     for item in reference_evidence:
                         if item[1] == "qualified_refs" and _usage_fact_contains_target(
-                            item[0], definer_module, symbol, aliases
+                            item[0], definer_module, symbol, aliases,
+                            current_modules=candidate_modules,
                         ):
                             result[symbol]["qualified_refs_detail"].append(
                                 {
@@ -959,7 +987,8 @@ def build_symbol_references_from_canonical(
                     result[symbol]["inherited_by"].append(consumer)
                     for item in reference_evidence:
                         if item[1] == "inheritance" and _usage_fact_contains_target(
-                            item[0], definer_module, symbol, aliases
+                            item[0], definer_module, symbol, aliases,
+                            current_modules=candidate_modules,
                         ):
                             result[symbol]["inherited_by_detail"].append(
                                 {
diff --git a/tests/test_package_reference_detail_parity.py b/tests/test_package_reference_detail_parity.py
new file mode 100644
index 0000000..84deea7
--- /dev/null
+++ b/tests/test_package_reference_detail_parity.py
@@ -0,0 +1,258 @@
+"""Package initializer usage details follow the canonical FULL reference target."""
+
+from __future__ import annotations
+
+import ast
+import builtins
+import copy
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+    load_engine_state,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+from contextor.core.reference import engine as reference_engine
+from contextor.core.reference.engine import (
+    CanonicalReferenceEvidenceUnavailable,
+    _usage_fact_contains_target,
+    build_symbol_references_from_canonical,
+)
+from contextor.core.reference.shared import _canonicalize_package_reference_target
+
+
+SOURCES = {
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
+def _run_full(root: Path) -> RepositoryAnalysisState:
+    errors, _ = ContextorFacade.analyze_project(str(root))
+    assert not errors, f"FULL analysis failed for isolated fixture {root}: {errors!r}"
+    cache = repo_cache_dir(root)
+    metadata = read_metadata(cache)
+    assert metadata is not None
+    state = load_engine_state(
+        str(cache),
+        metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert isinstance(state, RepositoryAnalysisState)
+    assert state.state_id == metadata.state_id
+    assert state.revision == metadata.revision
+    return state
+
+
+@pytest.fixture(scope="module")
+def retargeted_states(tmp_path_factory):
+    parent = tmp_path_factory.mktemp("package_reference_detail")
+    root = parent / "repo"
+    root.mkdir()
+    for relative, content in SOURCES.items():
+        path = root / relative
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_bytes(content)
+
+    with pytest.MonkeyPatch.context() as patch:
+        patch.setenv("CONTEXTOR_CACHE_DIR", str(parent / "cache"))
+        baseline_state = _run_full(root)
+        hydrated = hydrate_repository_engine(root)
+        assert hydrated is not None
+        engine = hydrated.engine
+        assert engine.state.state_id == baseline_state.state_id
+        original_state = engine.state
+        original_consumers = copy.deepcopy(
+            original_state.artifacts["alpha.__init__"]["consumers"]
+        )
+        original_record = original_state.artifacts["alpha.__init__"]["consumers"]["api_function"]
+
+        target = root / "alpha" / "__init__.py"
+        target.write_bytes(b"api_function = 7\n")
+        result = engine.update_file(str(target.resolve()))
+        assert result.status == "UPDATED"
+        incremental_state = engine.state
+        full_state = _run_full(root)
+
+    return {
+        "original": original_state,
+        "original_consumers": original_consumers,
+        "original_record": original_record,
+        "incremental": incremental_state,
+        "full": full_state,
+        "update_status": result.status,
+    }
+
+
+def test_package_initializer_match_uses_current_module_domain():
+    modules = {"alpha.__init__", "alpha.api", "beta.consumer"}
+    assert not _usage_fact_contains_target(
+        "alpha.api_function", "alpha.__init__", "api_function"
+    )
+    assert _usage_fact_contains_target(
+        "alpha.api_function",
+        "alpha.__init__",
+        "api_function",
+        current_modules=modules,
+    )
+
+
+def test_real_import_alias_is_canonicalized(retargeted_states, monkeypatch):
+    state = retargeted_states["incremental"]
+    facts = state.module_usages["beta.consumer"]
+    assert facts.reference_evidence_materialized
+    assert ("api_function", "alpha.api_function") in facts.aliases
+    direct_call = next(
+        item for item in facts.reference_evidence if item[1] == "direct_calls"
+    )
+    assert direct_call == ("alpha.api_function", "direct_calls", "", 2)
+
+    observed = []
+    canonicalize = reference_engine._canonicalize_package_reference_target
+
+    def record_canonicalization(target, modules):
+        observed.append(target)
+        return canonicalize(target, modules)
+
+    with monkeypatch.context() as patch:
+        patch.setattr(
+            reference_engine,
+            "_canonicalize_package_reference_target",
+            record_canonicalization,
+        )
+        assert _usage_fact_contains_target(
+            direct_call[0],
+            "alpha.__init__",
+            "api_function",
+            facts.aliases,
+            current_modules=set(state.modules),
+        )
+
+    assert observed == ["alpha.api_function", "alpha.api_function"]
+    assert _canonicalize_package_reference_target(
+        dict(facts.aliases)["api_function"], set(state.modules)
+    ) == "alpha.__init__.api_function"
+
+
+def test_real_submodule_identity_takes_longest_prefix_precedence():
+    modules = {
+        "alpha.__init__",
+        "alpha.api",
+        "alpha.api_function",
+        "beta.consumer",
+    }
+    assert _canonicalize_package_reference_target(
+        "alpha.api_function", modules
+    ) == "alpha.api_function"
+    assert not _usage_fact_contains_target(
+        "alpha.api_function",
+        "alpha.__init__",
+        "api_function",
+        current_modules=modules,
+    )
+
+
+def test_reexport_retarget_matches_full_consumer_detail(retargeted_states):
+    incremental = retargeted_states["incremental"]
+    full = retargeted_states["full"]
+    target = "alpha.__init__::api_function"
+    for state in (incremental, full):
+        assert state.artifact_consumption[target] == {
+            "consumers": ["beta.consumer"],
+            "channels": {"beta.consumer": ["api_imports", "direct_calls"]},
+        }
+
+    incremental_record = incremental.artifacts["alpha.__init__"]["consumers"]["api_function"]
+    full_record = full.artifacts["alpha.__init__"]["consumers"]["api_function"]
+    assert incremental_record == full_record
+    assert incremental_record["consumers"] == ["beta.consumer"]
+    assert incremental_record["usage"]["direct_calls"] == ["beta.consumer"]
+    assert incremental_record["usage"]["direct_calls_detail"] == [
+        {"module": "beta.consumer", "line": 2, "context": None}
+    ]
+    assert incremental_record["consumer_count"] == {
+        "total": 1,
+        "direct_calls": 1,
+        "callbacks": 0,
+        "events": 0,
+        "qualified_refs": 0,
+        "api_imports": 1,
+        "inheritance": 0,
+    }
+
+
+def test_cow_and_missing_reference_evidence_fail_closed(retargeted_states):
+    original = retargeted_states["original"]
+    incremental = retargeted_states["incremental"]
+    old_record = retargeted_states["original_record"]
+    assert original is not incremental
+    assert original.artifacts["alpha.__init__"]["consumers"] == (
+        retargeted_states["original_consumers"]
+    )
+    assert original.artifacts["alpha.__init__"]["consumers"]["api_function"] is old_record
+    assert incremental.artifacts["alpha.__init__"]["consumers"]["api_function"] is not old_record
+
+    modules = set(incremental.modules)
+    usages = dict(incremental.module_usages)
+    usages.pop("beta.consumer")
+    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
+        build_symbol_references_from_canonical(
+            definer_module="alpha.__init__",
+            symbols=["api_function"],
+            artifact_consumption=incremental.artifact_consumption,
+            module_usages=usages,
+            current_modules=modules,
+        )
+
+    usages = dict(incremental.module_usages)
+    usages["beta.consumer"] = replace(
+        usages["beta.consumer"], reference_evidence_materialized=False
+    )
+    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
+        build_symbol_references_from_canonical(
+            definer_module="alpha.__init__",
+            symbols=["api_function"],
+            artifact_consumption=incremental.artifact_consumption,
+            module_usages=usages,
+            current_modules=modules,
+        )
+
+
+def test_canonical_detail_projection_reads_only_materialized_ram_facts(
+    retargeted_states, monkeypatch
+):
+    state = retargeted_states["incremental"]
+
+    def unexpected_io(*_args, **_kwargs):
+        pytest.fail("canonical RAM projection performed source I/O or parsing")
+
+    with monkeypatch.context() as patch:
+        patch.setattr(builtins, "open", unexpected_io)
+        patch.setattr(Path, "read_text", unexpected_io)
+        patch.setattr(Path, "read_bytes", unexpected_io)
+        patch.setattr(ast, "parse", unexpected_io)
+        patch.setattr(reference_engine, "read_source", unexpected_io)
+        references = build_symbol_references_from_canonical(
+            definer_module="alpha.__init__",
+            symbols=["api_function"],
+            artifact_consumption=state.artifact_consumption,
+            module_usages=state.module_usages,
+            current_modules=set(state.modules),
+        )
+
+    assert references["api_function"]["called_by_detail"] == [
+        {"module": "beta.consumer", "line": 2, "context": None}
+    ]
~~~~
