# C16-B03-P1D3G18-P2-P9 — interpreter-bound deferred annotation semantics

## HEAD_BEFORE_AFTER

- Before and after: `3abd30b0c216c654d78147b7eada80900731bff5`. No commit or push.
- Before: only prior `walkthrough.md` modification. After: four task source/test files and this report modified.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/namespace_bound_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (report, excluded from its own FULL_DIFFS)

## CPYTHON_IDENTITY

- DIRECT_EVIDENCE: repository `.venv\Scripts\python.exe -B -V` is Python 3.15.2. No interpreter switch.

## D9_ROOT_CAUSE

- CONTRACT_PROVED: absent explicit target, the restricted model passes `annotation_semantics=None`. `cache_manager.py:33-38` has a class with annotated `__init__`; `_safe_passive_function_definition` rejects parameter annotations under that mode, so `_compile` refuses the class. The P9 opt-in changes only the conditional evaluator's chosen annotation mode.

## PEP649_VERSION_ASSUMPTION_CONTRACT

- Implementation: the requested helper accepts only exact tuples for CPython 3.10-3.15 matching the executing interpreter. It returns DEFERRED for 3.14+, STOCK_EAGER for older supported versions, and explicit errors for invalid, unsupported or mismatched versions. None retains the old behavior.
- The selected version is a caller-declared, host-validated conditional model assumption. It is not evidence of an analyzed application's interpreter or its actual imports, finder state or LIVE adoption.

## DEFAULT_VS_EXPLICIT_315_MODEL

- DIRECT_EVIDENCE: with the current 308-source FileState-bound inventory, default call returns UNKNOWN / RESTRICTED_MODEL_UNKNOWN at `contextor.core.analysis.cache_manager`, zero model events. Explicit (3,15) returns UNKNOWN / RESTRICTED_MODEL_UNKNOWN at `contextor.core.analysis.full_analysis_lease`, zero model events.
- DIRECT_EVIDENCE: `cache_manager` `_compile` is False with default semantics and True with DEFERRED. Next model target `full_analysis_lease.py:27-28` has `@dataclass(frozen=True, slots=True)` before `class FullAnalysisLease`; its decorated class is rejected by the existing passive-class guard. This is a model limitation, not a demonstrated runtime failure.

## TARGETED_TEST_RESULTS

- Exact six-module command from task, CPython 3.15.2: **301 passed in 31.07s**, zero failures. No full suite.
- `git diff --check`: exit 0. Git emitted only line-ending conversion notices.

## NEGATIVE_SAFETY_TESTS

- Passing P9 cases cover default UNKNOWN, mismatched and malformed interpreter versions, dynamic default UNKNOWN, annotation introspection UNKNOWN, external import UNKNOWN, source fingerprint mismatch and source-bound bad interpreter. Existing negative assertions in the six targeted modules passed.

## FULL_SOURCE_BOUND_REPLAY

- DIRECT_EVIDENCE: metadata-selected FileState was revision 1107/state_id `20261106_195021` during facade replay; 308 production source bytes matched its SHA-256 values, zero mismatches. No Git restoration was required. Selected model cohort: 202 ASTs. Bound digest for both calls: `6ca1f598aef59e2760bcadb4fac2ba2dbf4bbb180f63de5ab46625cd161b815d`.
- Default and explicit outcomes are above. Both preserve outer authority `SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF` and inner authority `CONDITIONAL_ORDERED_INVENTORY_AND_AST_NOT_RUNTIME_OR_LIVE_PROOF`.
- Canonical revision advanced under the active watcher during this task. Each replay verified all input bytes against the metadata-selected FileState of its own observed revision. The SCC2 replay later used revision 1109 with a fresh all-source hash check. No mixed-generation inputs were accepted.

## REAL_SCC_GATES

- DIRECT_EVIDENCE: SCC1/facade entry remains UNKNOWN at `full_analysis_lease` under explicit 3.15. SCC2 entry `contextor.ui.gui`, with 308 FileState-matching production sources at revision 1109, remains UNKNOWN / RESTRICTED_MODEL_UNKNOWN at `full_analysis_lease`, zero model events.
- MCP: 16 structural DFS cycles, 16 active warnings, model_pass_count=0, cycle_semantics=stale. No MODEL_PASS promotion, /3 receipt or warning suppression.

## MCP_POST_CHANGE_AUDIT

- Contextor MCP module contexts for both production modules and both changed test modules: canonical revision 1109, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, module/graph/cycles fresh, cycle_semantics stale, syntax_errors=0, structural DFS cycles=16, active_warning_count=16, model_pass_count=0. Provenance LIVE. Read-only metadata at revision 1109 confirms state_id `20261106_195021`, repo_id `ctx_8efc50d8` and root `C:\Temp\Contextor_Repo`. MCP reports source freshness of the changed files; it does not establish that an already-running process loaded the changed Python code.
- Current disk SHA-256: `package_model.py` `709bbae668a5a2f9a11dbabf491e14ca28f9c5f854fa8e37dc4154b430c17b4d`; `namespace_bound_model.py` `5952eec55fe7eecfb3047826aff38e76531707d4b89af4dd53adc6c1796bcf27`.

## RESTART_DECISION

- No restart was performed. The opt-in evaluator is not exposed directly by MCP, and fresh-process replay loaded the changed code. Adoption by the already-running Desktop/backend/LIVE process remains unverified. Later integration requires separate process identity, interpreter, GUI ownership and LIVE authority verification after controlled restart.

## REMAINING_UNKNOWN

- Actual analyzed application interpreter, `sys.path`, `sys.meta_path`, `sys.modules`, external execution effects, and active-process code adoption remain unknown. The canonical cycle-semantics family remains stale. No production FULL or update_file was performed.

## FULL_DIFFS

Complete actual diffs of the four production/test files follow. The report's own diff is excluded.

```diff
diff --git a/contextor/core/cycle_semantics/namespace_bound_model.py b/contextor/core/cycle_semantics/namespace_bound_model.py
index 20a4882..59d3b46 100644
--- a/contextor/core/cycle_semantics/namespace_bound_model.py
+++ b/contextor/core/cycle_semantics/namespace_bound_model.py
@@ -27,6 +27,7 @@ from .namespace_source_binding import (
 )
 from .package_model import (
     ConditionalNamespaceModelAssessment,
+    _conditional_annotation_mode_for_target,
     evaluate_conditional_namespace_import_order,
 )
 
@@ -54,6 +55,7 @@ def evaluate_source_bound_conditional_namespace_import_order(
     entry_module: str,
     *,
     standard_finder_assumed: bool = False,
+    target_python_version: tuple[int, int] | None = None,
 ) -> SourceBoundConditionalNamespaceAssessment:
     """Parse indexed byte snapshots and conditionally evaluate PEP 420.
 
@@ -88,6 +90,15 @@ def evaluate_source_bound_conditional_namespace_import_order(
     ):
         return reject("INVALID_ENTRY_OR_FINDER_POLICY")
 
+    _, version_error = (
+        _conditional_annotation_mode_for_target(
+            target_python_version
+        )
+    )
+
+    if version_error is not None:
+        return reject(version_error)
+
     bound = bind_indexed_namespace_resolution(
         roots,
         bindings,
@@ -179,6 +190,7 @@ def evaluate_source_bound_conditional_namespace_import_order(
         parsed_sources,
         entry_module,
         roots,
+        target_python_version=target_python_version,
     )
 
     # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 3fea17e..eb5cb5a 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -7,6 +7,7 @@ Never executes analyzed code or certifies general runtime safety.
 from __future__ import annotations
 
 import ast
+import sys
 from collections.abc import Mapping
 from dataclasses import dataclass, field, replace
 
@@ -1651,6 +1652,55 @@ class ConditionalNamespaceModelAssessment:
         "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
+    target_python_version: tuple[int, int] | None = None
+
+
+def _conditional_annotation_mode_for_target(
+    target_python_version: tuple[int, int] | None,
+) -> tuple[str | None, str | None]:
+    """Select documented CPython annotation semantics.
+
+    The explicit target version must match the interpreter
+    executing this restricted model. This does not prove the
+    interpreter used by an analyzed application.
+    """
+
+    if target_python_version is None:
+        return None, None
+
+    if (
+        type(target_python_version) is not tuple
+        or len(target_python_version) != 2
+        or any(
+            type(part) is not int
+            for part in target_python_version
+        )
+    ):
+        return None, "INVALID_TARGET_PYTHON_VERSION"
+
+    if target_python_version not in {
+        (3, 10),
+        (3, 11),
+        (3, 12),
+        (3, 13),
+        (3, 14),
+        (3, 15),
+    }:
+        return None, "UNSUPPORTED_TARGET_PYTHON_VERSION"
+
+    if (
+        sys.implementation.name != "cpython"
+        or target_python_version != (
+            sys.version_info.major,
+            sys.version_info.minor,
+        )
+    ):
+        return None, "TARGET_INTERPRETER_UNVERIFIED"
+
+    if target_python_version >= (3, 14):
+        return "DEFERRED", None
+
+    return "STOCK_EAGER", None
 
 
 def _conditional_reachable_source_cohort(
@@ -1800,6 +1850,8 @@ def evaluate_conditional_namespace_import_order(
     indexed_sources: Mapping[str, ast.AST],
     entry_module: str,
     portions: tuple[SearchPortion, ...],
+    *,
+    target_python_version: tuple[int, int] | None = None,
 ) -> ConditionalNamespaceModelAssessment:
     """Evaluate a supplied closed PEP 420 inventory conditionally.
 
@@ -1815,6 +1867,12 @@ def evaluate_conditional_namespace_import_order(
     The result is never eligible for MODEL_PASS warning suppression.
     """
 
+    annotation_mode, version_error = (
+        _conditional_annotation_mode_for_target(
+            target_python_version
+        )
+    )
+
     def reject(
         reason: str,
         parents: tuple[str, ...] = (),
@@ -1825,8 +1883,16 @@ def evaluate_conditional_namespace_import_order(
             reason=reason,
             model_assessment=None,
             namespace_parents=parents,
+            target_python_version=(
+                target_python_version
+                if version_error is None
+                else None
+            ),
         )
 
+    if version_error is not None:
+        return reject(version_error)
+
     if (
         not isinstance(indexed_sources, Mapping)
         or type(entry_module) is not str
@@ -2035,6 +2101,7 @@ def evaluate_conditional_namespace_import_order(
     model = evaluate_package_import_order(
         augmented,
         entry_module,
+        annotation_semantics=annotation_mode,
     )
 
     conditional_outcomes = {
@@ -2060,4 +2127,5 @@ def evaluate_conditional_namespace_import_order(
         ),
         model_assessment=model,
         namespace_parents=namespace_parents,
+        target_python_version=target_python_version,
     )
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index c67ff9b..05fa83b 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -146,6 +146,90 @@ def test_p6_finder_assumption_is_required():
     assert result.conditional_assessment is None
 
 
+def _p9_source_bound_annotated_case():
+    roots, bindings, hashes, snapshots = _case()
+
+    snapshots["pkg.ns.a"] = _snapshot(
+        "class Holder:\n"
+        "    def method(self, x: Later) -> Later:\n"
+        "        pass\n"
+        "value = 1\n"
+        "import pkg.ns.b\n"
+    )
+
+    hashes["pkg.ns.a"] = (
+        snapshots["pkg.ns.a"].source_fingerprint
+    )
+
+    return roots, bindings, hashes, snapshots
+
+
+def test_p9_source_bound_default_stays_unknown():
+    result = _evaluate(
+        _p9_source_bound_annotated_case(),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+
+
+def test_p9_source_bound_deferred_cpython315():
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        *_p9_source_bound_annotated_case(),
+        "pkg.ns.a",
+        standard_finder_assumed=True,
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.source_evidence_sha256 is not None
+    assert result.conditional_assessment is not None
+    assert (
+        result.conditional_assessment.target_python_version
+        == (3, 15)
+    )
+    assert result.authority == (
+        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def test_p9_source_bound_deferred_still_checks_hash():
+    roots, bindings, hashes, snapshots = (
+        _p9_source_bound_annotated_case()
+    )
+
+    hashes["pkg.ns.a"] = "0" * 64
+
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        roots,
+        bindings,
+        hashes,
+        snapshots,
+        "pkg.ns.a",
+        standard_finder_assumed=True,
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+    assert result.source_evidence_sha256 is None
+
+
+def test_p9_source_bound_bad_interpreter_rejected():
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        *_p9_source_bound_annotated_case(),
+        "pkg.ns.a",
+        standard_finder_assumed=True,
+        target_python_version=(3, 14),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "TARGET_INTERPRETER_UNVERIFIED"
+    assert result.source_evidence_sha256 is None
+
+
 def test_p6_changed_bytes_fail_closed():
     roots, bindings, hashes, snapshots = _case()
     snapshots["pkg.ns.a"] = _snapshot(
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index c7cfdf0..8c2efc8 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -420,6 +420,157 @@ def test_g18_p2_p5_unlisted_shadowing_source_unknown():
     )
 
 
+def _p9_annotation_sources(code):
+    return {"ns.a": ast.parse(code)}
+
+
+def _p9_annotation_portions():
+    return (
+        SearchPortion(
+            "root",
+            frozenset({"ns/a.py"}),
+        ),
+    )
+
+
+def test_p9_default_annotation_version_stays_unknown():
+    sources = _p9_annotation_sources(
+        "class Holder:\n"
+        "    def method(self, value: Later) -> Later:\n"
+        "        pass\n"
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+    assert result.target_python_version is None
+
+
+def test_p9_cpython315_deferred_method_annotations():
+    sources = _p9_annotation_sources(
+        "class Holder:\n"
+        "    def method(self, value: side_effect())"
+        " -> Later:\n"
+        "        pass\n"
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.target_python_version == (3, 15)
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == "MODEL_PASS"
+    assert result.authority == (
+        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def test_p9_target_interpreter_mismatch_fails_closed():
+    sources = _p9_annotation_sources("pass\n")
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+        target_python_version=(3, 14),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "TARGET_INTERPRETER_UNVERIFIED"
+    assert result.model_assessment is None
+
+
+def test_p9_invalid_target_version_fails_closed():
+    sources = _p9_annotation_sources("pass\n")
+
+    for version in ((True, 15), "3.15", (3,), (3, 16)):
+        result = evaluate_conditional_namespace_import_order(
+            sources,
+            "ns.a",
+            _p9_annotation_portions(),
+            target_python_version=version,
+        )
+
+        assert result.outcome == "UNKNOWN"
+        assert result.model_assessment is None
+        assert result.reason in {
+            "INVALID_TARGET_PYTHON_VERSION",
+            "UNSUPPORTED_TARGET_PYTHON_VERSION",
+        }
+
+
+def test_p9_dynamic_default_remains_unknown():
+    sources = _p9_annotation_sources(
+        "class Holder:\n"
+        "    def method(self, value: Later"
+        " = side_effect()):\n"
+        "        pass\n"
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+
+
+def test_p9_annotation_introspection_remains_unknown():
+    sources = _p9_annotation_sources(
+        "def method(value: side_effect()):\n"
+        "    pass\n"
+        "print(method.__annotations__)\n"
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+
+
+def test_p9_external_import_still_unknown():
+    sources = _p9_annotation_sources(
+        "import missing_external_xyz\n"
+        "class Holder:\n"
+        "    def method(self, x: Later):\n"
+        "        pass\n"
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        _p9_annotation_portions(),
+        target_python_version=(3, 15),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == (
+        "missing_external_xyz"
+    )
+
+
 def test_g18_p2_p5_alternative_loader_unknown():
     sources = {
         "ns.a": ast.parse(
```

## FINAL_VERDICT

PASS. Exact four-file implementation and test scope completed; all 301 targeted tests pass; both real SCC model replays remain UNKNOWN; 16 structural cycles and 16 active warnings remain; no runtime adoption is claimed.
