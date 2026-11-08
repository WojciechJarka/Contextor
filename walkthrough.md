# C16-B03-P1D3G18-P2-P10 — compile restricted programs on first modeled import

## HEAD_BEFORE_AFTER

- Before and after: `15147701b1ad401900a4eed1d9cd6dd7ded6353d`. Worktree clean before P10. No commit, push or reset.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`
- `walkthrough.md` (report; excluded from its own diff)

## PRECOMPILATION_ROOT_CAUSE

- CONTRACT_PROVED: prior `evaluate_package_import_order` compiled every selected source with restricted `_compile` before its bootstrap import frame. An unsupported source included in the conservative cohort could therefore return UNKNOWN with zero modeled events even when its import was never reached. The full CPython `compile(..., dont_inherit=True)` validity pass is a separate earlier stage.

## P10_PRIVATE_OPT_IN_CONTRACT

- Added keyword-only `_compile_on_first_import: bool = False` to `evaluate_package_import_order`. Exact bool validation rejects None, integers and strings; combining the opt-in with a non-null `_session` returns UNKNOWN.
- Existing eager behavior remains the default. Only `evaluate_conditional_namespace_import_order` passes `_compile_on_first_import=True`. The conditional/source-bound authority strings, source cohort and outcome mapping were not changed.

## FULL_CPYTHON_VALIDATION_PRESERVED

- CODE_PATH_PROVED: layout validation, full CPython validity compilation of every selected AST, logical mapping and `valid_chain` still precede the pending-program path. The new negative test confirms that an unreachable AST containing an invalid `break` fails closed before any modeled event.

## ON_FIRST_IMPORT_COMPILATION_CONTRACT

- All logical names receive a pending empty placeholder. The execution loop compiles an entered pending module before reading its steps; it replaces the placeholder and removes the pending marker only after successful compilation and package checks. A failed reached `_compile` returns UNKNOWN with that module. The original step budget, import frame flow, function-body insertion, compiler and annotation modes remain unchanged.
- The full `programs` key set is retained for optional from-child candidates and package-child checks. No analyzed source code is executed by the model.

## PACKAGE_SHADOWING_PARITY

- Eager package-shadowing loop body remains unchanged. In opt-in mode, the same checks run on the program of each actually entered package before its steps execute, using all logical `programs` keys to find direct children. Targeted negative tests for package child shadowing and parent initializer refusal pass.

## TARGETED_TEST_RESULTS

- Exact six-module P10 command using repository CPython 3.15.2: **313 passed in 33.19s**, zero failures. No full pytest.
- `git diff --check` restricted to the three changed source/test files: exit 0, no whitespace errors. Git printed only a Windows line-ending conversion notice.

## NEGATIVE_SAFETY_TESTS

- Passing P10 tests cover unsupported reached decorated class, from-import child, required regular parent initializer, false branch remaining unvisited, CPython-invalid unreachable source, package child shadowing, early-binding hazard, reached external import, invalid private flag and private-mode/session incompatibility. Existing six-module regression assertions also passed without alteration.

## FULL_SOURCE_BOUND_REPLAY

- DIRECT_EVIDENCE: one metadata-selected FileState generation, revision **1111**, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`. All **308** physical production source bytes matched FileState SHA-256, mismatch count 0. Conservative facade cohort: **202** ASTs. Both calls produced source-binding digest `43193b26845af8ed95aa5e74df8ef5f8596c0ab13f70b61c91f35ed74ea137a0`.
- Explicit `target_python_version=(3,15)`: UNKNOWN / RESTRICTED_MODEL_UNKNOWN, first UNKNOWN target `contextor.core.domain.graph`, **9** events, first START_IMPORT target `contextor`. No START_IMPORT for `contextor.core.analysis.full_analysis_lease`; that module was selected but not reached by modeled import execution.
- Default `target_python_version=None`: UNKNOWN / RESTRICTED_MODEL_UNKNOWN, first UNKNOWN target `contextor.core.graph.graph`, **7** events, first START_IMPORT target `contextor`. No modeled START_IMPORT for `full_analysis_lease`.
- Both retain outer authority `SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF` and inner authority `CONDITIONAL_ORDERED_INVENTORY_AND_AST_NOT_RUNTIME_OR_LIVE_PROOF`. Conditional replay cannot certify actual application import behavior or runtime safety.

## SCC1_SCC2_GATES

- DIRECT_EVIDENCE at revision **1112**, same state_id: current canonical snapshot and read-only source-closure reconstruction. SCC1: 44 members, 202 sources, zero FileState SHA-256 mismatches. SCC2: 9 members, 222 sources, zero mismatches.
- Both graph-consistency assessments remain INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED with four namespace candidates and OPAQUE_EXECUTION_POSSIBLE external gate. SCC1 has 608 opaque external candidates; SCC2 has 726. No MODEL_PASS promotion, warning suppression or /3 receipt was performed.

## MCP_POST_CHANGE_AUDIT

- Contextor MCP contexts for `package_model` and both changed test modules: canonical revision **1112**, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, LIVE provenance; graph/cycles fresh, cycle_semantics stale; syntax errors 0, structural DFS cycles **16**, active warnings **16**, model_pass_count **0**.
- Metadata at revision 1112: state_id `20261106_195021`, repo_id `ctx_8efc50d8`. Changed-file on-disk SHA-256 equals metadata-selected FileState: `package_model.py` `85d084002ec3d2ef382979efc51077720b4d6653fc50c8c10ac93a353d21f097`; `test_cycle_semantics_package_model.py` `65d5b150b5ddfc7467f74b82daed05e93708680be683743f44eb39a8db78908a`; `test_cycle_semantics_namespace_path_model.py` `4db66f51123783e22b2c86cd27c11827837c51142bc67d7acf27cb571182c27e`.

## RESTART_DECISION

- No Desktop/backend restart. Fresh-process replay loaded the modified code directly. Adoption by the active Desktop/backend process is **UNVERIFIED** until a later controlled restart and identity audit. No production FULL or update_file.

## REMAINING_UNKNOWN

- Actual application finder, interpreter state, `sys.path`, `sys.meta_path`, `sys.modules`, external import effects and live-process code adoption remain unknown. The canonical cycle-semantics family remains stale. UNKNOWN is not proof of safety.

## FULL_DIFFS

Complete actual diffs for all three changed production/test files follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index eb5cb5a..363dca0 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -917,6 +917,7 @@ def evaluate_package_import_order(
     *,
     _session: _PackageSourceSession | None = None,
     annotation_semantics: str | None = None,
+    _compile_on_first_import: bool = False,
 ) -> PackageImportAssessment:
     """Simulate a restricted closed regular-package source set.
 
@@ -946,6 +947,11 @@ def evaluate_package_import_order(
         or annotation_semantics not in {
             None, "STOCK_EAGER", "STRINGIFIED", "DEFERRED",
         }
+        or type(_compile_on_first_import) is not bool
+        or (
+            _compile_on_first_import
+            and _session is not None
+        )
     ):
         return result("UNKNOWN")
 
@@ -1080,6 +1086,7 @@ def evaluate_package_import_order(
         return result("UNKNOWN", entry_module)
 
     programs: dict[str, list[_Step]] = {}
+    pending_programs: set[str] = set()
 
     for name, tree in logical_sources.items():
         if not valid_chain(name):
@@ -1094,6 +1101,10 @@ def evaluate_package_import_order(
         )
         if annotation_semantics == "STRINGIFIED" and not has_future_annotations:
             return result("UNKNOWN", name)
+        if _compile_on_first_import:
+            programs[name] = []
+            pending_programs.add(name)
+            continue
         typing_guard = recognize_typing_guard(
             indexed_sources[indexed_id],
             frozenset(indexed_sources),
@@ -1132,7 +1143,9 @@ def evaluate_package_import_order(
     # A package may prebind a same-named attribute before a later
     # from-import; the attribute takes priority. Keep more complex
     # package-owned import/rebinding sequences indeterminate.
-    for package in packages:
+    for package in (
+        packages if not _compile_on_first_import else ()
+    ):
         children = {
             name.rsplit(".", 1)[1]
             for name in programs
@@ -1215,6 +1228,86 @@ def evaluate_package_import_order(
 
         module, index = frames[-1]
 
+        if module in pending_programs:
+            tree = logical_sources[module]
+            indexed_id = nodes[module].indexed_module_ids[0]
+
+            has_future_annotations = any(
+                isinstance(statement, ast.ImportFrom)
+                and statement.module == "__future__"
+                and any(
+                    alias.name == "annotations"
+                    for alias in statement.names
+                )
+                for statement in tree.body
+            )
+
+            typing_guard = recognize_typing_guard(
+                indexed_sources[indexed_id],
+                frozenset(indexed_sources),
+            )
+
+            program = _compile(
+                tree,
+                module,
+                module in packages,
+                typing_guard=typing_guard,
+                annotation_semantics=(
+                    "STRINGIFIED"
+                    if has_future_annotations
+                    else annotation_semantics
+                ),
+            )
+
+            if program is None:
+                return result("UNKNOWN", module)
+
+            if module in packages:
+                children = {
+                    name.rsplit(".", 1)[1]
+                    for name in programs
+                    if (
+                        "." in name
+                        and name.rsplit(".", 1)[0] == module
+                    )
+                }
+
+                if any(
+                    step.op in {
+                        "DEFINE_FUNCTION",
+                        "DEFINE_OPAQUE_FUNCTION",
+                        "DEFINE_PASSIVE_CLASS",
+                    }
+                    and step.binding in children
+                    for step in program
+                ):
+                    return result("UNKNOWN", module)
+
+                writes_child = any(
+                    step.binding in children
+                    and (
+                        step.op in {"BIND", "ALIAS"}
+                        or (
+                            step.op == "FROM"
+                            and step.target != module
+                        )
+                    )
+                    for step in program
+                )
+
+                if writes_child and any(
+                    step.op in {
+                        "IMPORT",
+                        "FROM",
+                        "CALL_FUNCTION",
+                    }
+                    for step in program
+                ):
+                    return result("UNKNOWN", module)
+
+            programs[module] = list(program)
+            pending_programs.remove(module)
+
         steps = (
             (_Step("IMPORT", entry_module, binding=None),)
             if module == bootstrap
@@ -2102,6 +2195,7 @@ def evaluate_conditional_namespace_import_order(
         augmented,
         entry_module,
         annotation_semantics=annotation_mode,
+        _compile_on_first_import=True,
     )
 
     conditional_outcomes = {
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index 8c2efc8..0403be6 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -420,6 +420,230 @@ def test_g18_p2_p5_unlisted_shadowing_source_unknown():
     )
 
 
+def _p10_assess(sources, entry="ns.a"):
+    paths = frozenset(
+        module.replace(".", "/") + ".py"
+        for module in sources
+    )
+
+    return evaluate_conditional_namespace_import_order(
+        sources,
+        entry,
+        (SearchPortion("root", paths),),
+        target_python_version=(3, 15),
+    )
+
+
+def test_p10_deferred_unreached_decorator_does_not_block():
+    sources = {
+        "ns.a": ast.parse(
+            "def later():\n"
+            "    import ns.unused\n"
+            "value = 1\n"
+        ),
+        "ns.unused": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+    first = _p10_assess(sources)
+    second = _p10_assess(sources)
+
+    assert first == second
+    assert first.outcome == "CONDITIONAL_MODEL_PASS"
+    assert first.model_assessment is not None
+
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "ns.unused"
+        for event in first.model_assessment.events
+    )
+
+    assert before == {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+
+def test_p10_reached_decorated_class_still_unknown():
+    sources = {
+        "ns.a": ast.parse("import ns.bad"),
+        "ns.bad": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+
+    assert any(
+        event.operation == "START_IMPORT"
+        and event.target == "ns.bad"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p10_from_child_reached_decorator_still_unknown():
+    sources = {
+        "ns.a": ast.parse("from ns import bad"),
+        "ns.bad": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+
+
+def test_p10_regular_parent_initializer_not_skipped():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "pkg.ns.a": ast.parse("pass"),
+    }
+
+    result = _p10_assess(
+        sources,
+        entry="pkg.ns.a",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "pkg"
+
+
+def test_p10_unselected_false_branch_remains_unvisited():
+    sources = {
+        "ns.a": ast.parse(
+            "if False:\n"
+            "    import ns.bad\n"
+            "value = 1\n"
+        ),
+        "ns.bad": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+
+
+def test_p10_compile_invalid_unreached_source_fails_closed():
+    sources = {
+        "ns.a": ast.parse(
+            "def later():\n"
+            "    import ns.bad\n"
+        ),
+        "ns.bad": ast.parse(
+            "def broken():\n"
+            "    break\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.bad"
+    assert result.model_assessment.events == ()
+
+
+def test_p10_lazy_package_child_shadow_remains_unknown():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "def child():\n"
+            "    pass\n"
+        ),
+        "pkg.ns.a": ast.parse(
+            "def later():\n"
+            "    import pkg.child\n"
+        ),
+        "pkg.child": ast.parse("pass"),
+    }
+
+    result = _p10_assess(
+        sources,
+        entry="pkg.ns.a",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "pkg"
+
+
+def test_p10_early_binding_hazard_is_not_hidden():
+    sources = {
+        "ns.a": ast.parse(
+            "from ns.b import ready\n"
+            "ready = 1\n"
+            "def later():\n"
+            "    import ns.unused\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import ready\n"
+        ),
+        "ns.unused": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == (
+        "CONDITIONAL_EARLY_BINDING_HAZARD"
+    )
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == (
+        "EARLY_BINDING_HAZARD"
+    )
+    assert any(
+        event.operation == "EARLY_BINDING_HAZARD"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p10_reached_external_import_still_unknown():
+    sources = {
+        "ns.a": ast.parse(
+            "import missing_external_xyz\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == (
+        "missing_external_xyz"
+    )
+
+
 def _p9_annotation_sources(code):
     return {"ns.a": ast.parse(code)}
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index da99426..a91541e 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1430,3 +1430,77 @@ def test_p1d3_d1_deterministic_events_and_ast_unchanged():
     assert first.events == second.events
     assert first.outcome == "EARLY_BINDING_HAZARD"
     assert {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()} == before
+
+
+def test_p10_eager_contract_unchanged_and_lazy_opt_in():
+    source = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse(
+            "def later():\n"
+            "    import pkg.bad\n"
+            "value = 1\n"
+        ),
+        "pkg.bad": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    eager = evaluate_package_import_order(
+        source,
+        "pkg.a",
+        annotation_semantics="DEFERRED",
+    )
+    lazy = evaluate_package_import_order(
+        source,
+        "pkg.a",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+
+    assert eager.outcome == "UNKNOWN"
+    assert eager.target_module == "pkg.bad"
+    assert eager.events == ()
+
+    assert lazy.outcome == "MODEL_PASS"
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.bad"
+        for event in lazy.events
+    )
+
+
+def test_p10_private_mode_invalid_flag_fails_closed():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse("pass"),
+    }
+
+    for invalid in (None, 1, "True"):
+        result = evaluate_package_import_order(
+            sources,
+            "pkg.a",
+            _compile_on_first_import=invalid,
+        )
+        assert result.outcome == "UNKNOWN"
+
+
+def test_p10_private_mode_rejects_session_combination():
+    from contextor.core.cycle_semantics.package_model import (
+        _PackageSourceSession,
+    )
+
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse("pass"),
+    }
+
+    result = evaluate_package_import_order(
+        sources,
+        "pkg.a",
+        _session=_PackageSourceSession(),
+        _compile_on_first_import=True,
+    )
+
+    assert result.outcome == "UNKNOWN"
```

## FINAL_VERDICT

PASS. Exact P10 implementation and test scope completed; 313 targeted tests passed; both source-bound replays remain UNKNOWN; 16 structural cycles and 16 active warnings remain; no active-process code adoption is claimed.
