# C16-B03-P1D3G18-P2-P8

## HEAD_BEFORE_AFTER

`240be3cf793c6b5fb68d1e243292e4fc04b98c2d` before and after. Initial worktree clean. No commit or push.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`

`walkthrough.md` was overwritten as the report.

## CPYTHON_IDENTITY

Active repository `.venv\Scripts\python.exe`: CPython 3.15.2. No interpreter switch.

## FULL_INVENTORY_VS_REACHABLE_COHORT

DIRECT_EVIDENCE: The new helper runs only after full indexed AST layout validation, full supplied `.py` inventory equality, conditional path checks and synthetic-initializer reference rejection. On canonical revision 1105, all 308 physical production `.py` sources were indexed and FileState-bound. The full source binder returned `SOURCE_BOUND_CONDITIONAL` with digest for `contextor.core.api.facade`. The conservative cohort selected 202 physical ASTs for the restricted evaluator; it excluded unrelated `contextor.__main__` and included `contextor.core.analysis.cache_manager`. The source-bound wrapper remained `UNKNOWN / RESTRICTED_MODEL_UNKNOWN`, with nested model UNKNOWN at `contextor.core.analysis.cache_manager` and zero model events. This is a measured diagnostic result, not safety or runtime import-selection proof.

## CONSERVATIVE_CLOSURE_CONTRACT

DIRECT_EVIDENCE: Added the specified `_conditional_reachable_source_cohort` and substituted its selected mapping only at the original restricted-evaluator invocation. The helper follows all lexical `ast.Import` and `ast.ImportFrom` nodes, including deferred and guarded bodies, adds possible named children and indexed regular parent initializers, and adds model-only empty namespace initializers only where needed. It can over-include physical sources. The original package evaluator, full inventory/path validation, source byte binding, graph, warning policy and authority strings were not edited. No selected source was treated as necessarily executed.

## TARGETED_TEST_RESULTS

Five specified modules: **186 passed in 26.27s**, exit code 0. `git diff --check` exited 0.

## NEGATIVE_SAFETY_TESTS

CONTRACT_PROVED by passing supplied assertions: unsupported direct import, absolute and relative named child, and regular parent initializer remain UNKNOWN; the earlier conditional hazard remains detected; omitted inventory remains `INVENTORY_SOURCE_DOMAIN_MISMATCH`; a source outside the model cohort remains bound and a forged hash for it remains `SOURCE_FINGERPRINT_MISMATCH`. Unreachable unsupported sources can be excluded from the restricted simulation only after full inventory validation. No unqualified MODEL_PASS was returned by the conditional/source-bound interfaces.

## REAL_REPOSITORY_REPLAY

DIRECT_EVIDENCE: Snapshot revision 1105, state_id `20261106_195021`, repo_id `ctx_8efc50d8`; 308 physical/indexed production modules and 626 total indexed modules including tests. Full-production source binding succeeds. SCC1: 44 members, 202 optional selected sources, 607 external records, four namespace records, external gate `OPAQUE_EXECUTION_POSSIBLE`. SCC2: 9 members, 222 sources, 725 external records, four namespace records, same gate. Both actual SCC scenario checks remain `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, coverage NONE, zero entry assessments. Separate source-bound conditional calls for the two cohorts (202 and 222 sources) both bound with digest and returned `UNKNOWN / RESTRICTED_MODEL_UNKNOWN` at `contextor.core.analysis.cache_manager`. No real SCC MODEL_PASS was promoted. Structural DFS cycles remain 16.

## SOURCE_BINDING

DIRECT_EVIDENCE: Metadata-selected FileState and snapshot agreed on revision 1105/state_id `20261106_195021`. Current SHA-256 matched FileState for all 308 production files and all 222 files in the SCC union; zero mismatch. The binder still validates all supplied bytes before the reachable cohort is formed. No analyzed repository source was executed; AST was parsed and model functions were invoked only.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP for all three changed modules returned revision 1105, canonical_state fresh, workspace_sync verified, advisory warning null, syntax errors 0, structural DFS cycles 16, active warnings 16, model_pass_count 0 and cycle_semantics stale. No FULL, update_file or restart occurred.

## REMAINING_UNKNOWN_GATES

The supplied inventory and source binding do not certify actual runtime `sys.path`, `sys.meta_path`, `sys.modules`, loaders or LIVE generation. The restricted model still returns UNKNOWN at `cache_manager` for the real full-production and SCC cohorts. Actual SCC namespace/external execution uncertainty and stale cycle semantics remain. Runtime adoption of modified source was not certified; local replay used current repository source. No warning suppression or /3 receipt was claimed.

## FULL_DIFFS

Complete actual Git diff of all three production/test changes follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index dad4f7c..3fea17e 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1653,6 +1653,149 @@ class ConditionalNamespaceModelAssessment:
     )
 
 
+def _conditional_reachable_source_cohort(
+    indexed_sources: Mapping[str, ast.AST],
+    entry_module: str,
+    namespace_parents: tuple[str, ...],
+) -> dict[str, ast.AST] | None:
+    """Over-approximate physical sources possibly loaded by an entry.
+
+    Examine every lexical import, including imports in deferred
+    or guarded scopes. Include regular parent initializers and
+    optional from-import child modules.
+
+    This may include sources never executed. It must never
+    infer execution safety from an omitted source.
+
+    The caller must validate the FULL source inventory and
+    namespace path layout before invoking this function.
+    """
+
+    physical_by_logical: dict[str, str] = {}
+
+    for indexed_id in indexed_sources:
+        logical = (
+            indexed_id.removesuffix(".__init__")
+            if indexed_id.endswith(".__init__")
+            else indexed_id
+        )
+
+        if logical in physical_by_logical:
+            return None
+
+        physical_by_logical[logical] = indexed_id
+
+    known_namespaces = frozenset(namespace_parents)
+
+    if (
+        entry_module not in physical_by_logical
+        and entry_module not in known_namespaces
+    ):
+        return None
+
+    pending = [entry_module]
+    visited: set[str] = set()
+    selected: dict[str, ast.AST] = {}
+
+    while pending:
+        logical = pending.pop()
+
+        if logical in visited:
+            continue
+
+        visited.add(logical)
+
+        parts = logical.split(".")
+
+        for length in range(1, len(parts)):
+            parent = ".".join(parts[:length])
+
+            if parent in physical_by_logical:
+                pending.append(parent)
+
+        indexed_id = physical_by_logical.get(logical)
+
+        if indexed_id is None:
+            continue
+
+        tree = indexed_sources[indexed_id]
+        selected[indexed_id] = tree
+
+        is_package = indexed_id.endswith(".__init__")
+
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Import):
+                for alias in node.names:
+                    requested = alias.name
+
+                    if (
+                        requested in physical_by_logical
+                        or requested in known_namespaces
+                    ):
+                        pending.append(requested)
+
+            elif isinstance(node, ast.ImportFrom):
+                if node.level == 0:
+                    base = node.module
+                else:
+                    context = (
+                        logical.split(".")
+                        if is_package
+                        else logical.split(".")[:-1]
+                    )
+
+                    climb = node.level - 1
+
+                    if (
+                        not context
+                        or climb >= len(context)
+                    ):
+                        continue
+
+                    components = context[
+                        :len(context) - climb
+                    ]
+
+                    if node.module:
+                        components.extend(
+                            node.module.split(".")
+                        )
+
+                    base = ".".join(components)
+
+                if (
+                    not base
+                    or not all(
+                        part.isidentifier()
+                        for part in base.split(".")
+                    )
+                ):
+                    continue
+
+                if (
+                    base in physical_by_logical
+                    or base in known_namespaces
+                ):
+                    pending.append(base)
+
+                for alias in node.names:
+                    if (
+                        alias.name == "*"
+                        or not alias.name.isidentifier()
+                    ):
+                        continue
+
+                    child = base + "." + alias.name
+
+                    if (
+                        child in physical_by_logical
+                        or child in known_namespaces
+                    ):
+                        pending.append(child)
+
+    return selected
+
+
 def evaluate_conditional_namespace_import_order(
     indexed_sources: Mapping[str, ast.AST],
     entry_module: str,
@@ -1847,14 +1990,45 @@ def evaluate_conditional_namespace_import_order(
                         namespace_parents,
                     )
 
-    augmented = dict(indexed_sources)
+    selected = _conditional_reachable_source_cohort(
+        indexed_sources,
+        entry_module,
+        namespace_parents,
+    )
 
-    for parent in namespace_parents:
-        augmented[parent + ".__init__"] = ast.Module(
-            body=[],
-            type_ignores=[],
+    if selected is None:
+        return reject(
+            "CONDITIONAL_SOURCE_COHORT_UNRESOLVED",
+            namespace_parents,
+        )
+
+    augmented = dict(selected)
+
+    needed_names: set[str] = {entry_module}
+
+    for indexed_id in selected:
+        logical = (
+            indexed_id.removesuffix(".__init__")
+            if indexed_id.endswith(".__init__")
+            else indexed_id
         )
 
+        parts = logical.split(".")
+
+        for length in range(1, len(parts) + 1):
+            needed_names.add(
+                ".".join(parts[:length])
+            )
+
+    for parent in namespace_parents:
+        if parent in needed_names:
+            augmented[parent + ".__init__"] = (
+                ast.Module(
+                    body=[],
+                    type_ignores=[],
+                )
+            )
+
     # Reuse the existing import-order simulator.
     # Its internal observations remain model-relative.
     # Never change or promote its execution outcomes.
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 0326078..c67ff9b 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -371,3 +371,67 @@ def test_p7_source_bound_308_module_cohort():
         "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
+
+
+def test_p8_unreachable_module_still_source_bound():
+    roots, bindings, hashes, snapshots = _case()
+
+    extra = "pkg.ns.unused"
+    path = "pkg/ns/unused.py"
+
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({path}),
+        ),
+    )
+
+    bindings = bindings + (
+        IndexedSourcePath(extra, "root", path),
+    )
+
+    raw = b"raise RuntimeError('unused')\n"
+    digest = hashlib.sha256(raw).hexdigest()
+
+    snapshots[extra] = SourceSnapshot(raw, digest)
+    hashes[extra] = digest
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots),
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.source_evidence_sha256 is not None
+
+
+def test_p8_unreachable_module_bad_hash_still_rejected():
+    roots, bindings, hashes, snapshots = _case()
+
+    extra = "pkg.ns.unused"
+    path = "pkg/ns/unused.py"
+
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({path}),
+        ),
+    )
+
+    bindings = bindings + (
+        IndexedSourcePath(extra, "root", path),
+    )
+
+    raw = b"raise RuntimeError('unused')\n"
+    digest = hashlib.sha256(raw).hexdigest()
+
+    snapshots[extra] = SourceSnapshot(raw, digest)
+    hashes[extra] = "0" * 64
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots),
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+    assert result.source_evidence_sha256 is None
+    assert result.conditional_assessment is None
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index d955939..c7cfdf0 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -629,3 +629,215 @@ def test_g18_p2_p7_conditional_model_accepts_308_sources():
         "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
+
+
+def test_g18_p2_p8_unreachable_unsupported_module():
+    sources = {
+        "ns.a": ast.parse("pass\n"),
+        "ns.unused": ast.parse(
+            "raise RuntimeError('unused')\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/unused.py",
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
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+
+
+def test_g18_p2_p8_direct_imported_unsupported_blocks():
+    sources = {
+        "ns.a": ast.parse("import ns.bad\n"),
+        "ns.bad": ast.parse(
+            "raise RuntimeError('bad')\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/bad.py",
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
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+
+
+def test_g18_p2_p8_from_child_not_omitted():
+    sources = {
+        "ns.a": ast.parse("from ns import bad\n"),
+        "ns.bad": ast.parse(
+            "raise RuntimeError('bad')\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/bad.py",
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
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+
+
+def test_g18_p2_p8_relative_from_child_not_omitted():
+    sources = {
+        "ns.a": ast.parse("from . import bad\n"),
+        "ns.bad": ast.parse(
+            "raise RuntimeError('bad')\n"
+        ),
+    }
+
+    portions = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "ns/a.py",
+                "ns/bad.py",
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
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+
+
+def test_g18_p2_p8_parent_initializer_not_omitted():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "raise RuntimeError('initializer')\n"
+        ),
+        "pkg.ns.a": ast.parse("pass\n"),
+    }
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
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "pkg"
+
+
+def test_g18_p2_p8_unrelated_two_portion_source():
+    sources = {
+        "ns.a": ast.parse("pass\n"),
+        "ns.unused": ast.parse(
+            "raise RuntimeError('unused')\n"
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
+            frozenset({"ns/unused.py"}),
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
+
+
+def test_g18_p2_p8_existing_hazard_still_detected():
+    result = evaluate_conditional_namespace_import_order(
+        _g18_p2_p5_sources(hazard=True),
+        "pkg.ns.a",
+        _g18_p2_p5_portions(),
+    )
+
+    assert result.outcome == (
+        "CONDITIONAL_EARLY_BINDING_HAZARD"
+    )
+    assert result.model_assessment is not None
+    assert result.model_assessment.symbol == "value"
+
+
+def test_g18_p2_p8_no_full_inventory_shortcut():
+    sources = {
+        "ns.a": ast.parse("pass\n"),
+        "ns.unused": ast.parse("pass\n"),
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
+        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
+    )
```

## FINAL_VERDICT

PASS — exact conservative cohort change, 186 targeted tests passed, full 308-source binding preserved, real SCCs remain INDETERMINATE and structural cycles remain 16.
