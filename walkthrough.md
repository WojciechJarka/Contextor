# C16-B03-P1D3G18-P2-P5

## HEAD_BEFORE/AFTER

`d0bb50aff53f7a73df4fe9c86ed1e10f67aee8b3` before and after. Initial worktree clean. No commit or push.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`

`walkthrough.md` was overwritten as the required report.

## CPYTHON_IDENTITY

Active repository `.venv\Scripts\python.exe`: CPython 3.15.2. No interpreter switch.

## CONDITIONAL_PEP420_CONTRACT

DIRECT_EVIDENCE: Added the exact namespace path import and appended `ConditionalNamespaceModelAssessment` plus `evaluate_conditional_namespace_import_order` after the existing evaluator. The new function validates a caller-supplied ordered portion inventory against the indexed AST cohort and package layout, rejects explicit synthetic initializer references, then invokes the unchanged restricted evaluator on an ephemeral in-memory mapping with empty namespace initializers. Its positive outcomes are prefixed `CONDITIONAL_` and its authority explicitly disclaims runtime/LIVE proof. No canonical source, hard edge, physical initializer or warning rule was changed. Existing evaluator behavior was not edited.

## TARGETED_TEST_RESULTS

Four specified modules: **172 passed in 23.74s**, exit code 0. `git diff --check` exited 0.

## POSITIVE_AND_NEGATIVE_SCENARIOS

CONTRACT_PROVED by supplied passing assertions: default namespace evaluation remains UNKNOWN. Supplied closed inventory can yield `CONDITIONAL_MODEL_PASS` or `CONDITIONAL_EARLY_BINDING_HAZARD`, with entry-order differences preserved. Two namespace portions are supported conditionally. Missing source, unlisted shadowing initializer, alternate loader, absent namespace parent and explicit synthetic initializer reference fail to UNKNOWN. Eager external import remains `UNKNOWN / RESTRICTED_MODEL_UNKNOWN`. No conditional outcome was promoted to unqualified MODEL_PASS.

## AST_IMMUTABILITY

CONTRACT_PROVED: the supplied determinism test passed and compared complete `ast.dump(..., include_attributes=True)` before and after repeated conditional evaluations. The implementation copies the source mapping and creates only in-memory synthetic AST nodes.

## REAL_SCC_REPLAY

DIRECT_EVIDENCE: Read-only replay on canonical revision 1095. Physical production Python inventory remains 307 files (`contextor` 306 plus root `main.py`). SCC1: 44 members, optional closure 202, 607 external records/scope records, 4 namespace records, gate `OPAQUE_EXECUTION_POSSIBLE`. SCC2: 9 members, optional closure 222, 725 external records/scope records, 4 namespace records, same gate. Both retain consistency `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`; scenario classification INDETERMINATE, coverage NONE, zero entry assessments. The closure and external counts increased relative to the historical 201/221 and 605/723 after the new production import added a reachable module. The conditional evaluator was not used for real SCC assessment. Structural DFS cycles remain 16; no new MODEL_PASS claim.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot metadata and metadata-selected FileState agreed on revision 1095 and state_id `20261106_195021`. All 222 selected source SHA-256 fingerprints in the union matched FileState, zero missing or mismatched. An earlier revision-1093 replay found one changed file and was explicitly discarded as unbound; watcher later advanced canonical revisions without `update_file`.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP for both modified modules reported revision 1095, canonical_state fresh, workspace_sync verified, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0, cycle_semantics stale. No FULL, update_file or restart was performed.

## REMAINING_AUTHORITY_GAPS

The supplied inventory does not authenticate actual runtime finder selection, search path, loaders, source bytes or LIVE installation. Real SCC namespace resolution and external import effects remain unmodeled. Runtime adoption of the new code was not certified; local replay used current repository source. No optional /3 receipt was claimed.

## FULL_DIFFS

Complete actual Git diff follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index c43d893..8722d49 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -11,6 +11,10 @@ from collections.abc import Mapping
 from dataclasses import dataclass, field, replace
 
 from contextor.core.cycle_semantics.package_layout import build_package_layout
+from contextor.core.cycle_semantics.namespace_path_model import (
+    SearchPortion,
+    resolve_namespace_path,
+)
 from contextor.core.cycle_semantics.typing_guard import (
     RecognizedTypingGuard,
     matches_typing_guard,
@@ -1634,3 +1638,253 @@ def evaluate_package_import_order(
         frames[-1] = (module, index + 1)
 
     return result("MODEL_PASS")
+
+
+@dataclass(frozen=True)
+class ConditionalNamespaceModelAssessment:
+    entry_module: str
+    outcome: str
+    reason: str | None
+    model_assessment: PackageImportAssessment | None
+    namespace_parents: tuple[str, ...]
+    authority: str = (
+        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def evaluate_conditional_namespace_import_order(
+    indexed_sources: Mapping[str, ast.AST],
+    entry_module: str,
+    portions: tuple[SearchPortion, ...],
+) -> ConditionalNamespaceModelAssessment:
+    """Evaluate a supplied closed PEP 420 inventory conditionally.
+
+    This assumes standard finder behavior for the supplied ordered
+    inventory. It does not authenticate actual runtime import state,
+    sys.path, sys.modules, custom finders, external portions,
+    source bytes or canonical LIVE freshness.
+
+    Namespace parents are represented by an empty initialization
+    program only within this private conditional evaluation.
+    No synthetic source is written or indexed.
+
+    The result is never eligible for MODEL_PASS warning suppression.
+    """
+
+    def reject(
+        reason: str,
+        parents: tuple[str, ...] = (),
+    ) -> ConditionalNamespaceModelAssessment:
+        return ConditionalNamespaceModelAssessment(
+            entry_module=entry_module,
+            outcome="UNKNOWN",
+            reason=reason,
+            model_assessment=None,
+            namespace_parents=parents,
+        )
+
+    if (
+        not isinstance(indexed_sources, Mapping)
+        or type(entry_module) is not str
+        or not entry_module
+        or type(portions) is not tuple
+        or not portions
+        or any(
+            type(portion) is not SearchPortion
+            or type(portion.files) is not frozenset
+            or any(
+                type(filename) is not str
+                for filename in portion.files
+            )
+            for portion in portions
+        )
+    ):
+        return reject("INVALID_CONDITIONAL_INPUT")
+
+    if (
+        not indexed_sources
+        or len(indexed_sources) > 256
+        or any(
+            type(module_id) is not str
+            or not isinstance(tree, ast.Module)
+            for module_id, tree in indexed_sources.items()
+        )
+    ):
+        return reject("INVALID_CONDITIONAL_SOURCE_COHORT")
+
+    try:
+        layout = build_package_layout(indexed_sources)
+    except (TypeError, ValueError):
+        return reject("INVALID_CONDITIONAL_LAYOUT")
+
+    nodes = {
+        node.name: node
+        for node in layout.nodes
+    }
+
+    namespace_parents = tuple(sorted(
+        node.name
+        for node in layout.nodes
+        if node.kind == "NAMESPACE_CANDIDATE"
+    ))
+
+    if not namespace_parents:
+        return reject("NO_NAMESPACE_PARENT")
+
+    if any(
+        node.kind not in {
+            "REGULAR_PACKAGE",
+            "MODULE_FILE",
+            "NAMESPACE_CANDIDATE",
+        }
+        for node in layout.nodes
+    ):
+        return reject(
+            "AMBIGUOUS_CONDITIONAL_LAYOUT",
+            namespace_parents,
+        )
+
+    expected_files = tuple(sorted(
+        module_id.replace(".", "/") + ".py"
+        for module_id in indexed_sources
+    ))
+
+    inventory_files = tuple(sorted(
+        filename
+        for portion in portions
+        for filename in portion.files
+        if filename.endswith(".py")
+    ))
+
+    if inventory_files != expected_files:
+        return reject(
+            "INVENTORY_SOURCE_DOMAIN_MISMATCH",
+            namespace_parents,
+        )
+
+    for node in layout.nodes:
+        resolution = resolve_namespace_path(
+            portions,
+            node.name,
+            standard_finder_assumed=True,
+        )
+
+        if resolution.status != "CONDITIONAL":
+            return reject(
+                "CONDITIONAL_PATH_UNRESOLVED:" + node.name,
+                namespace_parents,
+            )
+
+        if node.kind == "NAMESPACE_CANDIDATE":
+            if (
+                resolution.kind != "NAMESPACE_PACKAGE"
+                or resolution.source is not None
+                or not resolution.portions
+            ):
+                return reject(
+                    "NAMESPACE_PATH_KIND_MISMATCH:" + node.name,
+                    namespace_parents,
+                )
+            continue
+
+        if (
+            len(node.indexed_module_ids) != 1
+            or resolution.kind != node.kind
+        ):
+            return reject(
+                "CONDITIONAL_SOURCE_KIND_MISMATCH:" + node.name,
+                namespace_parents,
+            )
+
+        expected_path = (
+            node.indexed_module_ids[0].replace(".", "/")
+            + ".py"
+        )
+
+        selected_candidates = {
+            portion.root_id + ":" + expected_path
+            for portion in portions
+            if expected_path in portion.files
+        }
+
+        if resolution.source not in selected_candidates:
+            return reject(
+                "CONDITIONAL_SOURCE_PATH_MISMATCH:" + node.name,
+                namespace_parents,
+            )
+
+    # An implicit namespace has no executable __init__.py.
+    # Do not let a synthetic model-only initializer become
+    # an explicitly importable source module.
+    synthetic_ids = {
+        name + ".__init__"
+        for name in namespace_parents
+    }
+
+    for tree in indexed_sources.values():
+        for statement in ast.walk(tree):
+            if isinstance(statement, ast.Import):
+                if any(
+                    alias.name in synthetic_ids
+                    for alias in statement.names
+                ):
+                    return reject(
+                        "SYNTHETIC_INITIALIZER_REFERENCE",
+                        namespace_parents,
+                    )
+
+            elif isinstance(statement, ast.ImportFrom):
+                if (
+                    statement.level == 0
+                    and statement.module in namespace_parents
+                    and any(
+                        alias.name == "__init__"
+                        for alias in statement.names
+                    )
+                ):
+                    return reject(
+                        "SYNTHETIC_INITIALIZER_REFERENCE",
+                        namespace_parents,
+                    )
+
+    augmented = dict(indexed_sources)
+
+    for parent in namespace_parents:
+        augmented[parent + ".__init__"] = ast.Module(
+            body=[],
+            type_ignores=[],
+        )
+
+    # Reuse the existing import-order simulator.
+    # Its internal observations remain model-relative.
+    # Never change or promote its execution outcomes.
+    model = evaluate_package_import_order(
+        augmented,
+        entry_module,
+    )
+
+    conditional_outcomes = {
+        "MODEL_PASS": "CONDITIONAL_MODEL_PASS",
+        "EARLY_BINDING_HAZARD":
+            "CONDITIONAL_EARLY_BINDING_HAZARD",
+        "MISSING_EXPORT": "CONDITIONAL_MISSING_EXPORT",
+        "MISSING_ATTRIBUTE": "CONDITIONAL_MISSING_ATTRIBUTE",
+    }
+
+    outcome = conditional_outcomes.get(
+        model.outcome,
+        "UNKNOWN",
+    )
+
+    return ConditionalNamespaceModelAssessment(
+        entry_module=entry_module,
+        outcome=outcome,
+        reason=(
+            None
+            if outcome != "UNKNOWN"
+            else "RESTRICTED_MODEL_UNKNOWN"
+        ),
+        model_assessment=model,
+        namespace_parents=namespace_parents,
+    )
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index c7a5eda..f747ab9 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -2,8 +2,14 @@
 
 from __future__ import annotations
 
+import ast
+
 from dataclasses import asdict
 
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_conditional_namespace_import_order,
+    evaluate_package_import_order,
+)
 from contextor.core.cycle_semantics.namespace_path_model import (
     SearchPortion,
     resolve_namespace_path,
@@ -244,3 +250,348 @@ def test_t11_deterministic_and_not_runtime_certified():
         "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
     )
     assert first.status == "CONDITIONAL"
+
+
+def _g18_p2_p5_sources(*, hazard=False):
+    return {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.ns.a": ast.parse(
+            (
+                "import pkg.ns.b\n"
+                "value = 1\n"
+            )
+            if hazard else (
+                "value = 1\n"
+                "import pkg.ns.b\n"
+            )
+        ),
+        "pkg.ns.b": ast.parse(
+            "from pkg.ns.a import value\n"
+        ),
+    }
+
+
+def _g18_p2_p5_portions():
+    return (
+        SearchPortion(
+            "root",
+            frozenset({
+                "pkg/__init__.py",
+                "pkg/ns/a.py",
+                "pkg/ns/b.py",
+            }),
+        ),
+    )
+
+
+def test_g18_p2_p5_default_namespace_remains_unknown():
+    sources = _g18_p2_p5_sources()
+
+    result = evaluate_package_import_order(
+        sources,
+        "pkg.ns.a",
+    )
+
+    assert result.outcome == "UNKNOWN"
+
+
+def test_g18_p2_p5_conditional_safe_order():
+    sources = _g18_p2_p5_sources()
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.a",
+        _g18_p2_p5_portions(),
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == "MODEL_PASS"
+    assert result.namespace_parents == ("pkg.ns",)
+    assert result.authority == (
+        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def test_g18_p2_p5_conditional_early_binding_hazard():
+    sources = _g18_p2_p5_sources(hazard=True)
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.a",
+        _g18_p2_p5_portions(),
+    )
+
+    assert result.outcome == (
+        "CONDITIONAL_EARLY_BINDING_HAZARD"
+    )
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == (
+        "EARLY_BINDING_HAZARD"
+    )
+    assert result.model_assessment.target_module == (
+        "pkg.ns.a"
+    )
+    assert result.model_assessment.symbol == "value"
+
+
+def test_g18_p2_p5_other_entry_can_pass():
+    sources = _g18_p2_p5_sources(hazard=True)
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.b",
+        _g18_p2_p5_portions(),
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+
+
+def test_g18_p2_p5_two_namespace_portions():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "import ns.b\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import value\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "first",
+            frozenset({"ns/a.py"}),
+        ),
+        SearchPortion(
+            "second",
+            frozenset({"ns/b.py"}),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        portions,
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.namespace_parents == ("ns",)
+
+
+def test_g18_p2_p5_unlisted_shadowing_source_unknown():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "import ns.b\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import value\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "namespace",
+            frozenset({
+                "ns/a.py",
+                "ns/b.py",
+            }),
+        ),
+        SearchPortion(
+            "shadow",
+            frozenset({
+                "ns/__init__.py",
+            }),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
+    )
+
+
+def test_g18_p2_p5_alternative_loader_unknown():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "import ns.b\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import value\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/b.py",
+                "ns/a.cp315-win_amd64.pyd",
+            }),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "CONDITIONAL_PATH_UNRESOLVED:ns.a"
+    )
+
+
+def test_g18_p2_p5_missing_source_unknown():
+    sources = _g18_p2_p5_sources()
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "pkg/__init__.py",
+                "pkg/ns/a.py",
+            }),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
+    )
+
+
+def test_g18_p2_p5_no_namespace_parent_unknown():
+    sources = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse("value = 1\n"),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "pkg/__init__.py",
+                "pkg/a.py",
+            }),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "NO_NAMESPACE_PARENT"
+
+
+def test_g18_p2_p5_explicit_synthetic_initializer_rejected():
+    sources = {
+        "ns.a": ast.parse(
+            "import ns.__init__\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({"ns/a.py"}),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "SYNTHETIC_INITIALIZER_REFERENCE"
+    )
+
+
+def test_g18_p2_p5_external_execution_still_unknown():
+    sources = {
+        "ns.a": ast.parse(
+            "import os\n"
+            "import ns.b\n"
+        ),
+        "ns.b": ast.parse(
+            "import ns.a\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/b.py",
+            }),
+        ),
+    )
+
+    result = evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        portions,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+
+
+def test_g18_p2_p5_deterministic_and_ast_immutable():
+    sources = _g18_p2_p5_sources()
+
+    before = {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in sources.items()
+    }
+
+    first = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.a",
+        _g18_p2_p5_portions(),
+    )
+
+    second = evaluate_conditional_namespace_import_order(
+        sources,
+        "pkg.ns.a",
+        _g18_p2_p5_portions(),
+    )
+
+    assert first == second
+    assert first.outcome == "CONDITIONAL_MODEL_PASS"
+
+    assert before == {
+        name: ast.dump(
+            tree,
+            include_attributes=True,
+        )
+        for name, tree in sources.items()
+    }
```

## FINAL_VERDICT

PASS — exact conditional PEP 420 model, 172 targeted tests passed, all 222 current SCC source files FileState-bound, real SCCs remain INDETERMINATE and structural cycles remain 16.
