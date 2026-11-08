# CONTEXTOR C16-B03-P1D3-P15-R5 — conditional external import assumption

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first. Both target module contexts at canonical revision 1131: `canonical_state=fresh`, `workspace_sync=verified`, provenance LIVE; graph/cycles fresh and cycle_semantics stale from R4. Architecture had 2 cyclic SCCs, 16 DFS paths, 0 syntax errors, `resync_required=false`. HEAD `46a256477fdd7ce06332c0f70b763175b9cdc5da`; initially clean worktree. Repository interpreter CPython 3.15.2.
- CODE_PATH_PROVED: exact R4 anchors existed in `package_model.py` (`ReachedUnmodeledImport`, `PackageImportAssessment`, local `result`, `programs`/`states`/`namespaces`, IMPORT/FROM/PREPARE_FROM_MEMBER missing-program branch, conditional wrapper) and `namespace_bound_model.py` (assessment and source-bound wrapper). Direct consumers of `PackageImportAssessment` in scenarios/evidence and conditional wrapper were checked. No material anchor drift.

## EXACT_PRODUCTION_DIFFS

Complete actual production diffs appear in FULL_DIFFS. `package_model.py` adds an explicit private hypothesis, records each assumed external import separately from the R4 stopping blocker, and marks the restricted result with a conditional evidence scope. `namespace_bound_model.py` forwards a validated public conditional flag while preserving byte/fingerprint/finder checks. No normal FULL, persistence, warning or MCP implementation changed.

## EXTERNAL_ASSUMPTION_CONTRACT

- The opt-in assumes external import success, requested member existence, no reentry into indexed project modules or namespace mutation, and the independently supplied standard-finder conditional inventory. These are assumptions, not observed runtime effects.
- `_assume_passive_external_imports` is private, exact-bool, default false, and accepted only with `_compile_on_first_import=True`. Conditional wrappers expose exact-bool `assume_passive_external_imports=False` and label outcomes `STOP_AT_UNMODELED` or `ASSUME_PASSIVE_EXTERNAL_SUCCESS`. Their existing authority strings remain unchanged.
- Eligible reached target must be nonempty, absent from `programs`, from an unindexed top-level root, and outside bootstrap. An eligible step appends `ReachedUnmodeledImport` to `assumed_external_imports`, emits `ASSUMED_EXTERNAL_IMPORT`, binds only opaque `\x00ASSUMED_EXTERNAL:` local sentinels for IMPORT/FROM outside function/class local scope, advances one frame, and continues. PREPARE_FROM_MEMBER records but does not bind. It never creates a program/state or executes importlib/external code.
- The existing `reached_unmodeled_import` remains the record of a target that **stops** simulation. Assumed records describe only imports crossed under the explicit hypothesis. Normal evidence scope remains `RESTRICTED_REGULAR_PACKAGE_MODEL`; opt-in is `CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_ASSUMPTION_NOT_RUNTIME_PROOF`, which does not satisfy the regular-model verifier contract.

## DEFAULT_VS_OPT_IN_OUTCOMES

- Default `pkg.ns.a: import os; value=1; import pkg.ns.b` remains `UNKNOWN/RESTRICTED_MODEL_UNKNOWN`, model target os, R4 stopping blocker present, assumed list empty, policy `STOP_AT_UNMODELED`.
- Explicit opt-in with conditional standard finder gives `CONDITIONAL_MODEL_PASS`, inner MODEL_PASS with conditional evidence scope, one source-bound IMPORT/os assumption at line 1 column 0, no R4 stopping blocker, and an `ASSUMED_EXTERNAL_IMPORT` event. This is a hypothetical restricted-model result, not runtime or canonical LIVE authority.
- Direct normal `evaluate_package_import_order` remains UNKNOWN at os and preserves its normal evidence scope/events; private opt-in without lazy compilation is rejected UNKNOWN.

## CONDITIONAL_HAZARD_NEGATIVES

- With `import os` before `import pkg.ns.b` before binding `value`, default stops UNKNOWN at os; opt-in reports only `CONDITIONAL_EARLY_BINDING_HAZARD` (inner EARLY_BINDING_HAZARD at `pkg.ns.a.value`) and records the os assumption. The hazard is conditional, not a confirmed runtime diagnosis.
- An unindexed target under indexed `pkg` is not assumed external. A later `os.path` value expression remains UNKNOWN after recording the os assumption. An earlier unsupported call stops before importing `pkg.ns.b`. No whitelist or external function execution was added.

## UNKNOWN_AND_SOURCE_BINDING_SAFETY

- Source-bound wrapper rejects non-boolean policy with `UNKNOWN/INVALID_EXTERNAL_IMPORT_ASSUMPTION`. Changed bytes with unchanged indexed fingerprint still reject with `SOURCE_FINGERPRINT_MISMATCH` before any model promotion. The ordinary missing-program branch remains for absent internal roots and all non-eligible cases.
- The sentinel is local opaque model state only; later unsupported access remains UNKNOWN by existing restricted steps. No external modules were imported by the implementation. Existing intentionally isolated tests retain their own behavior.

## REGRESSION_T01_T10

- T01 default external UNKNOWN with R4 blocker, empty assumptions and STOP policy: PASS.
- T02 opt-in safe order, conditional scope/policy, source line/column, one assumption/event: PASS.
- T03 opt-in conditional early hazard, default UNKNOWN at os: PASS.
- T04 missing indexed-root target not skipped: PASS.
- T05 opaque external use stays UNKNOWN: PASS.
- T06 unsupported effect stops before later indexed import: PASS.
- T07 external FROM/dataclasses/dataclass assumption with coordinates: PASS.
- T08 invalid non-boolean source-bound policy fails closed: PASS.
- T09 changed source bytes retain fingerprint rejection: PASS.
- T10 equal frozen results/events/assumption records and deterministic JSON via `asdict`; snapshots unchanged: PASS.

## DIRECT_PACKAGE_MODEL_TESTS

Added focused tests for normal UNKNOWN at os; refusal of private opt-in without `_compile_on_first_import=True`; conditional scope; no assumption for ordinary MODEL_PASS; indexed import remains modeled; called local-function import retains original line 2/column 4 under opt-in; uncalled function body produces no assumed record. All pass. Prior assertions were not rewritten.

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: repository CPython 3.15.2, `PYTHONDONTWRITEBYTECODE=1`, `-B -m pytest -q -rs` on exactly the four requested modules (`test_cycle_semantics_package_model.py`, `test_cycle_semantics_namespace_bound_model.py`, `test_cycle_semantics_namespace_path_model.py`, `test_cycle_semantics_scenarios.py`): **213 passed in 18.18s**, 0 failed. `git diff --check` on source/tests before report returned exit 0. No full suite.

## EVENT_AND_OUTCOME_PARITY

- CODE_PATH_PROVED: default flag leaves the R4 missing-target branch and existing event path unchanged. Opt-in adds only explicit assumption events at eligible reached external steps. Existing namespace/path/scenario event and outcome tests all passed; no normal MODEL_PASS promotion or warning-suppression edit.
- The private opt-in result uses a distinct evidence scope so the existing regular-model verifier cannot treat it as a regular closed-model claim. Deterministic serialization and unchanged source snapshot tests pass.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: watcher brought both edited production modules to LIVE canonical revision **1133**, each `workspace_sync=verified`, `canonical_state=fresh`, no advisory warning. Architecture: graph/cycles fresh, cycle_semantics stale, 627 modules, 2 cyclic SCCs with 44/9 members, 16 DFS paths, zero syntax errors, `resync_required=false`, runtime execution `UNKNOWN_NOT_EVALUATED`. No unrelated production file was modified.
- No `update_file`, FULL, backend/Desktop restart, package installation, Git mutation or warning suppression was performed.

## SOURCE_HASH_PARITY

- DIRECT_EVIDENCE: metadata and referenced FileState both revision 1133, state_id `20261108_172727`, repo_id `ctx_8efc50d8`. Production source disk/FileState SHA-256 parity: `package_model.py` `d6996f11bfde93d10313bba0dc9233d93434f4092fcc46ae40f2a305c13f2c86`; `namespace_bound_model.py` `a96c317fda3d90043c0a404f79646e527ad221336c324ec4aedd655c69ed6007`.
- DIRECT_EVIDENCE: test files pass when run from disk but their FileState entries still contain prior hashes at this audit: package test current `ab1968559021830174344314a3d969dec13e6398b31b30c9ab650caa61237e96` versus stored `7b90cbf0dbc78fb42f21e3a2f00442f90cbe085a31498f5a909532585907adfd`; namespace test current `50f7e293b8c65217e9eeae960a9b792ec1c9fd6587ab537a4cfec29d3991a6a6` versus stored `700774095a055990940482561810f593d5f5241b70faeada029a6713b50bbdfa`. This is explicitly **not** claimed as test-source canonical parity; watcher did not acknowledge those files during the bounded audit. No forced update was made.

## CANONICAL_FRESHNESS_LIMITATION

The canonical cycle_semantics family remains stale after source changes. Current on-disk tests and production byte parity do not prove adoption by the persistent LIVE interpreter; no FULL or restart was authorized. Conditional outcomes are not current canonical runtime claims.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/namespace_bound_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (report only; excluded from its own diff)

## FULL_DIFFS

Complete actual Git diffs for the four changed source/test files follow; `walkthrough.md` excluded.

```diff
diff --git a/contextor/core/cycle_semantics/namespace_bound_model.py b/contextor/core/cycle_semantics/namespace_bound_model.py
index 59d3b46..ca00036 100644
--- a/contextor/core/cycle_semantics/namespace_bound_model.py
+++ b/contextor/core/cycle_semantics/namespace_bound_model.py
@@ -45,6 +45,7 @@ class SourceBoundConditionalNamespaceAssessment:
         "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
+    external_import_policy: str = "STOP_AT_UNMODELED"
 
 
 def evaluate_source_bound_conditional_namespace_import_order(
@@ -56,6 +57,7 @@ def evaluate_source_bound_conditional_namespace_import_order(
     *,
     standard_finder_assumed: bool = False,
     target_python_version: tuple[int, int] | None = None,
+    assume_passive_external_imports: bool = False,
 ) -> SourceBoundConditionalNamespaceAssessment:
     """Parse indexed byte snapshots and conditionally evaluate PEP 420.
 
@@ -67,6 +69,12 @@ def evaluate_source_bound_conditional_namespace_import_order(
     LIVE generation or permission to suppress a cycle warning.
     """
 
+    external_import_policy = (
+        "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
+        if assume_passive_external_imports is True
+        else "STOP_AT_UNMODELED"
+    )
+
     def reject(
         reason: str,
         digest: str | None = None,
@@ -77,8 +85,12 @@ def evaluate_source_bound_conditional_namespace_import_order(
             reason=reason,
             source_evidence_sha256=digest,
             conditional_assessment=None,
+            external_import_policy=external_import_policy,
         )
 
+    if type(assume_passive_external_imports) is not bool:
+        return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")
+
     if (
         type(entry_module) is not str
         or not entry_module
@@ -191,6 +203,9 @@ def evaluate_source_bound_conditional_namespace_import_order(
         entry_module,
         roots,
         target_python_version=target_python_version,
+        assume_passive_external_imports=(
+            assume_passive_external_imports
+        ),
     )
 
     # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
@@ -202,4 +217,5 @@ def evaluate_source_bound_conditional_namespace_import_order(
         reason=conditional.reason,
         source_evidence_sha256=digest,
         conditional_assessment=conditional,
+        external_import_policy=external_import_policy,
     )
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 58b98ca..1f483ca 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -52,6 +52,9 @@ class PackageImportAssessment:
     reached_unmodeled_import: (
         ReachedUnmodeledImport | None
     ) = None
+    assumed_external_imports: (
+        tuple[ReachedUnmodeledImport, ...]
+    ) = ()
 
 
 @dataclass(frozen=True)
@@ -1016,6 +1019,7 @@ def evaluate_package_import_order(
     _session: _PackageSourceSession | None = None,
     annotation_semantics: str | None = None,
     _compile_on_first_import: bool = False,
+    _assume_passive_external_imports: bool = False,
 ) -> PackageImportAssessment:
     """Simulate a restricted closed regular-package source set.
 
@@ -1025,6 +1029,7 @@ def evaluate_package_import_order(
     Results cannot certify general Python import safety.
     """
     events: list[PackageModelEvent] = []
+    assumed_external_imports: list[ReachedUnmodeledImport] = []
 
     def result(
         outcome: str,
@@ -1041,7 +1046,16 @@ def evaluate_package_import_order(
             target,
             symbol,
             tuple(events),
+            evidence_scope=(
+                "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
+                "ASSUMPTION_NOT_RUNTIME_PROOF"
+                if _assume_passive_external_imports is True
+                else "RESTRICTED_REGULAR_PACKAGE_MODEL"
+            ),
             reached_unmodeled_import=reached_unmodeled_import,
+            assumed_external_imports=tuple(
+                assumed_external_imports
+            ),
         )
 
     if (
@@ -1051,6 +1065,11 @@ def evaluate_package_import_order(
             None, "STOCK_EAGER", "STRINGIFIED", "DEFERRED",
         }
         or type(_compile_on_first_import) is not bool
+        or type(_assume_passive_external_imports) is not bool
+        or (
+            _assume_passive_external_imports
+            and not _compile_on_first_import
+        )
         or (
             _compile_on_first_import
             and _session is not None
@@ -1322,6 +1341,10 @@ def evaluate_package_import_order(
         return None
 
     step_budget = 10000
+    indexed_roots = frozenset(
+        name.split(".", 1)[0]
+        for name in programs
+    )
 
     while frames:
         step_budget -= 1
@@ -1468,6 +1491,48 @@ def evaluate_package_import_order(
             target = step.target
 
             if not target or target not in programs:
+                if (
+                    _assume_passive_external_imports
+                    and target
+                    and target not in programs
+                    and module != bootstrap
+                    and target.split(".", 1)[0]
+                    not in indexed_roots
+                ):
+                    assumed_external_imports.append(
+                        ReachedUnmodeledImport(
+                            importer=module,
+                            operation=step.op,
+                            target=target,
+                            symbol=step.symbol,
+                            line=step.source_line,
+                            column=step.source_column,
+                        )
+                    )
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            "ASSUMED_EXTERNAL_IMPORT",
+                            target,
+                            step.symbol,
+                        )
+                    )
+                    if (
+                        step.op in {"IMPORT", "FROM"}
+                        and not step.function_local
+                        and not step.class_local
+                    ):
+                        namespaces[module][step.binding] = (
+                            "\x00ASSUMED_EXTERNAL:"
+                            + target
+                            + (
+                                ":" + step.symbol
+                                if step.op == "FROM"
+                                else ""
+                            )
+                        )
+                    frames[-1] = (module, index + 1)
+                    continue
                 blocker = (
                     ReachedUnmodeledImport(
                         importer=module,
@@ -1868,6 +1933,7 @@ class ConditionalNamespaceModelAssessment:
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
     target_python_version: tuple[int, int] | None = None
+    external_import_policy: str = "STOP_AT_UNMODELED"
 
 
 def _conditional_annotation_mode_for_target(
@@ -2067,6 +2133,7 @@ def evaluate_conditional_namespace_import_order(
     portions: tuple[SearchPortion, ...],
     *,
     target_python_version: tuple[int, int] | None = None,
+    assume_passive_external_imports: bool = False,
 ) -> ConditionalNamespaceModelAssessment:
     """Evaluate a supplied closed PEP 420 inventory conditionally.
 
@@ -2087,6 +2154,11 @@ def evaluate_conditional_namespace_import_order(
             target_python_version
         )
     )
+    external_import_policy = (
+        "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
+        if assume_passive_external_imports is True
+        else "STOP_AT_UNMODELED"
+    )
 
     def reject(
         reason: str,
@@ -2103,8 +2175,12 @@ def evaluate_conditional_namespace_import_order(
                 if version_error is None
                 else None
             ),
+            external_import_policy=external_import_policy,
         )
 
+    if type(assume_passive_external_imports) is not bool:
+        return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")
+
     if version_error is not None:
         return reject(version_error)
 
@@ -2318,6 +2394,9 @@ def evaluate_conditional_namespace_import_order(
         entry_module,
         annotation_semantics=annotation_mode,
         _compile_on_first_import=True,
+        _assume_passive_external_imports=(
+            assume_passive_external_imports
+        ),
     )
 
     conditional_outcomes = {
@@ -2344,4 +2423,5 @@ def evaluate_conditional_namespace_import_order(
         model_assessment=model,
         namespace_parents=namespace_parents,
         target_python_version=target_python_version,
+        external_import_policy=external_import_policy,
     )
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 58f0fc1..b98311a 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -3,6 +3,8 @@
 from __future__ import annotations
 
 import hashlib
+import json
+from dataclasses import asdict
 
 from contextor.core.source import SourceSnapshot
 from contextor.core.cycle_semantics.namespace_bound_model import (
@@ -93,6 +95,181 @@ def _evaluate(
     )
 
 
+def _external_case(source, *, child=None):
+    roots, bindings, hashes, snapshots = _case()
+    snapshots["pkg.ns.a"] = _snapshot(source)
+    hashes["pkg.ns.a"] = snapshots["pkg.ns.a"].source_fingerprint
+    if child is not None:
+        snapshots["pkg.ns.b"] = _snapshot(child)
+        hashes["pkg.ns.b"] = snapshots["pkg.ns.b"].source_fingerprint
+    return roots, bindings, hashes, snapshots
+
+
+def _external_result(source, *, assume=False, child=None):
+    return evaluate_source_bound_conditional_namespace_import_order(
+        *_external_case(source, child=child),
+        "pkg.ns.a",
+        standard_finder_assumed=True,
+        assume_passive_external_imports=assume,
+    )
+
+
+def test_external_policy_t01_default_still_unknown():
+    result = _external_result("import os\nvalue=1\nimport pkg.ns.b\n")
+    model = result.conditional_assessment.model_assessment
+    assert (result.outcome, result.reason) == (
+        "UNKNOWN", "RESTRICTED_MODEL_UNKNOWN"
+    )
+    assert result.external_import_policy == "STOP_AT_UNMODELED"
+    assert result.conditional_assessment.external_import_policy == "STOP_AT_UNMODELED"
+    assert model.outcome == "UNKNOWN"
+    assert model.reached_unmodeled_import.target == "os"
+    assert model.assumed_external_imports == ()
+
+
+def test_external_policy_t02_opt_in_safe_order():
+    result = _external_result(
+        "import os\nvalue=1\nimport pkg.ns.b\n", assume=True
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.external_import_policy == "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
+    assert result.conditional_assessment.external_import_policy == "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
+    assert model.outcome == "MODEL_PASS"
+    assert model.evidence_scope == (
+        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
+        "ASSUMPTION_NOT_RUNTIME_PROOF"
+    )
+    assert model.reached_unmodeled_import is None
+    assert len(model.assumed_external_imports) == 1
+    blocker = model.assumed_external_imports[0]
+    assert (
+        blocker.importer, blocker.operation, blocker.target,
+        blocker.symbol, blocker.line, blocker.column,
+    ) == ("pkg.ns.a", "IMPORT", "os", None, 1, 0)
+    assert "ASSUMED_EXTERNAL_IMPORT" in (
+        event.operation for event in model.events
+    )
+
+
+def test_external_policy_t03_early_hazard_remains_conditional():
+    source = "import os\nimport pkg.ns.b\nvalue=1\n"
+    default = _external_result(source)
+    result = _external_result(source, assume=True)
+    model = result.conditional_assessment.model_assessment
+    assert default.outcome == "UNKNOWN"
+    assert default.conditional_assessment.model_assessment.target_module == "os"
+    assert result.outcome == "CONDITIONAL_EARLY_BINDING_HAZARD"
+    assert model.outcome == "EARLY_BINDING_HAZARD"
+    assert model.target_module == "pkg.ns.a"
+    assert model.symbol == "value"
+    assert len(model.assumed_external_imports) == 1
+    assert model.assumed_external_imports[0].target == "os"
+
+
+def test_external_policy_t04_internal_missing_not_skipped():
+    result = _external_result(
+        "import pkg.ns.missing\nvalue=1\n", assume=True
+    )
+    assert result.outcome == "UNKNOWN"
+    if result.conditional_assessment is not None:
+        model = result.conditional_assessment.model_assessment
+        assert model.outcome == "UNKNOWN"
+        assert model.target_module == "pkg.ns.missing"
+        assert model.assumed_external_imports == ()
+
+
+def test_external_policy_t05_opaque_use_unknown():
+    result = _external_result(
+        "import os\nvalue = os.path\nimport pkg.ns.b\n",
+        assume=True,
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "UNKNOWN"
+    assert tuple(x.target for x in model.assumed_external_imports) == ("os",)
+
+
+def test_external_policy_t06_earlier_unsupported_effect_stops():
+    result = _external_result(
+        "import os\nunknown_function()\nimport pkg.ns.b\n",
+        assume=True,
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "UNKNOWN"
+    assert tuple(x.target for x in model.assumed_external_imports) == ("os",)
+    assert not any(
+        event.target == "pkg.ns.b" and event.operation == "START_IMPORT"
+        for event in model.events
+    )
+
+
+def test_external_policy_t07_from_import():
+    result = _external_result(
+        "from dataclasses import dataclass\nvalue=1\nimport pkg.ns.b\n",
+        assume=True,
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert model.outcome == "MODEL_PASS"
+    assert len(model.assumed_external_imports) == 1
+    blocker = model.assumed_external_imports[0]
+    assert (
+        blocker.operation, blocker.target, blocker.symbol,
+        blocker.line, blocker.column,
+    ) == ("FROM", "dataclasses", "dataclass", 1, 0)
+
+
+def test_external_policy_t08_invalid_policy():
+    args = _external_case("import os\nvalue=1\nimport pkg.ns.b\n")
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        *args, "pkg.ns.a", standard_finder_assumed=True,
+        assume_passive_external_imports="yes",
+    )
+    assert (result.outcome, result.reason) == (
+        "UNKNOWN", "INVALID_EXTERNAL_IMPORT_ASSUMPTION"
+    )
+    assert result.external_import_policy == "STOP_AT_UNMODELED"
+
+
+def test_external_policy_t09_fingerprint_retained():
+    roots, bindings, hashes, snapshots = _external_case(
+        "import os\nvalue=1\nimport pkg.ns.b\n"
+    )
+    snapshots["pkg.ns.a"] = _snapshot("import os\nvalue=2\nimport pkg.ns.b\n")
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        roots, bindings, hashes, snapshots, "pkg.ns.a",
+        standard_finder_assumed=True,
+        assume_passive_external_imports=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+    assert result.conditional_assessment is None
+
+
+def test_external_policy_t10_deterministic_and_unmutated():
+    args = _external_case("import os\nvalue=1\nimport pkg.ns.b\n")
+    before = dict(args[3])
+    first = evaluate_source_bound_conditional_namespace_import_order(
+        *args, "pkg.ns.a", standard_finder_assumed=True,
+        assume_passive_external_imports=True,
+    )
+    second = evaluate_source_bound_conditional_namespace_import_order(
+        *args, "pkg.ns.a", standard_finder_assumed=True,
+        assume_passive_external_imports=True,
+    )
+    assert first == second
+    assert first.conditional_assessment.model_assessment.events == (
+        second.conditional_assessment.model_assessment.events
+    )
+    assert first.conditional_assessment.model_assessment.assumed_external_imports == (
+        second.conditional_assessment.model_assessment.assumed_external_imports
+    )
+    assert json.dumps(asdict(first), sort_keys=True) == json.dumps(
+        asdict(second), sort_keys=True
+    )
+    assert args[3] == before
+
+
 def test_p6_source_bound_conditional_pass():
     result = _evaluate(_case())
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index c83ecb4..e222bbb 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -21,6 +21,96 @@ def _model(source, entry):
     )
 
 
+def test_external_assumption_normal_model_still_unknown():
+    result = _model({"pkg.__init__": "import os\n"}, "pkg")
+    assert result.outcome == "UNKNOWN"
+    assert result.target_module == "os"
+    assert result.assumed_external_imports == ()
+    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert not any(
+        event.operation == "ASSUMED_EXTERNAL_IMPORT"
+        for event in result.events
+    )
+
+
+def test_external_assumption_refused_without_lazy_compilation():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse("import os\n")}, "pkg",
+        _assume_passive_external_imports=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_external_imports == ()
+
+
+def test_external_assumption_direct_conditional_scope():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse("import os\nvalue=1\n")},
+        "pkg",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert result.evidence_scope == (
+        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
+        "ASSUMPTION_NOT_RUNTIME_PROOF"
+    )
+    assert tuple(x.target for x in result.assumed_external_imports) == ("os",)
+    assert result.reached_unmodeled_import is None
+
+
+def test_external_assumption_normal_pass_has_no_record():
+    result = _model({"pkg.__init__": "value=1\n"}, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert result.assumed_external_imports == ()
+
+
+def test_external_assumption_does_not_skip_indexed_import():
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse("from .child import value\n"),
+            "pkg.child": ast.parse("value=7\n"),
+        },
+        "pkg",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert result.assumed_external_imports == ()
+    assert any(event.target == "pkg.child" for event in result.events)
+
+
+def test_external_assumption_called_local_import_keeps_location():
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(
+                "def activate():\n    import os\nactivate()\n"
+            )
+        },
+        "pkg",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_external_imports) == 1
+    row = result.assumed_external_imports[0]
+    assert (row.importer, row.operation, row.target) == (
+        "pkg", "IMPORT", "os"
+    )
+    assert (row.line, row.column) == (2, 4)
+    assert "CALL_FUNCTION" in (event.operation for event in result.events)
+
+
+def test_external_assumption_uncalled_function_has_no_record():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse("def activate():\n    import os\nvalue=1\n")},
+        "pkg",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert result.assumed_external_imports == ()
+
+
 def test_reached_unmodeled_import_direct_import():
     result = _model({"pkg.__init__": "import os\nvalue=1\n"}, "pkg")
 
```

## FINAL_VERDICT

PASS — literal conditional opt-in is complete; all 213 targeted tests pass, default behavior and internal fail-closed boundary remain intact, production targets match current FileState, and graph/cycle audit succeeded. Test FileState entries were not yet updated by the watcher; canonical cycle_semantics remains stale and LIVE interpreter adoption is unverified.
