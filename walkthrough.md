# P5-M08-I9-I1 — regression STOP

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `cef29d7d90dbdc43cae58b0ee78fb1eff15844af`; pre-existing change only in `walkthrough.md`; active `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. Contextor LIVE revision 1353, `package_model.py` workspace_sync=verified, cycle_semantics=stale, structural DFS cycle count 16. D1 anchors, single `_DefinitionState` constructor, existing `_snapshot_named_decorators`, both collision guards and I9-T1 baseline were present.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/state.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_class_decorator_staging.py`

`walkthrough.md` is this report.

## CLASS_DECORATOR_ADMISSION

CODE_PATH_PROVED: validator admits only ordinary named decorator syntax under explicit opt-in; attribute and call decorators remain rejected. Conditional frozen dataclass detection uses exact qualified decorator predicate. This admission altered whole-module compilation behavior, producing the regressions below.

## EARLY_DECORATOR_SNAPSHOT

CODE_PATH_PROVED: compiler emits `SNAPSHOT_CLASS_DECORATORS` before `PREPARE_PASSIVE_CLASS` and class-body steps; evaluator stores name/object pairs from `_snapshot_named_decorators` by definition ID without invoking the objects.

## CLASS_COMPILER_SEQUENCE

CODE_PATH_PROVED: staged decorated class emits snapshot, prepare, optional class-local body import, and `DEFINE_DECORATED_PASSIVE_CLASS`; latter returns UNKNOWN. The new staging tests passed within the targeted run. No decorated class name is bound by the new branch.

## METACLASS_AND_MRO_PRESERVATION

No edits to PREPARE_PASSIVE_CLASS, DEFINE_PASSIVE_CLASS, _ClassFact, metaclass selection or C3 merge. Related focused tests passed, but whole-module eager boundary regressed.

## CONDITIONAL_DATACLASS_PRESERVATION

The new test uses the exact fixture and options from `test_frozen_dataclass_direct_conditional_record` and passed. Conditional evidence remains qualified, not ordinary MODEL_PASS runtime proof.

## CHILD_NAME_COLLISION_GUARDS

Both existing definition-name guards include `DEFINE_DECORATED_PASSIVE_CLASS`; no guard was removed.

## UNCHANGED_UNKNOWN_BOUNDARIES

Seven I9-T1 cases passed as UNKNOWN. Attribute/call decorator tests passed. However historical strict/eager boundaries for an unresolved named class decorator changed; see below. Thus this heading cannot claim full preservation.

## TARGETED_TEST_RESULTS

Exact specified suite: `2 failed, 356 passed, 2 warnings in 42.19s`. Two failures in `tests/test_cycle_semantics_package_model.py`:

1. `test_p10_eager_contract_unchanged_and_lazy_opt_in`, line 2839. Source: `pkg.a` defines deferred `later()` importing `pkg.bad`; `pkg.bad` has `@unknown_decorator class Bad: pass`. Expected eager UNKNOWN, actual MODEL_PASS. Exact model event sequence:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"READY","target":null,"symbol":null},{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg.a","symbol":null},{"module":"pkg.a","operation":"DEFINE_FUNCTION","target":null,"symbol":"later"},{"module":"pkg.a","operation":"BIND","target":null,"symbol":"value"},{"module":"pkg.a","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.a","symbol":"a"}]
```
Pytest traceback: `AssertionError: assert 'MODEL_PASS' == 'UNKNOWN'` at line 2839.

2. `test_p11_strict_mode_remains_whole_module_unknown`, line 2912. Source: `pkg.a` binds `value=1`, then has `@unknown_decorator class Bad: pass`. Expected strict UNKNOWN with no events; actual UNKNOWN after partial events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"READY","target":null,"symbol":null},{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg.a","symbol":null},{"module":"pkg.a","operation":"BIND","target":null,"symbol":"value"}]
```
Pytest traceback: `AssertionError: assert (PackageModelEvent...) == ()` at line 2912. Relevant source anchors: validator `package_model.py:244-307`; ClassDef compiler `:809-1009`; eager precompile and execution paths `:1535-1740`; new snapshot `:2384-2418`.

DIRECT_EVIDENCE: these tests do not run CPython subprocess; CPython observed JSON is not applicable. Model outcomes/events above were reproduced with the active interpreter. The likely cause is that compile now accepts syntactically named but unbound decorator references and defers rejection to execution; this is an inference from the changed path, not a certified repair design.

`git diff --check`: exit 0; only LF/CRLF notices.

## MCP_POST_CHANGE_AUDIT

NOT RUN because section 12 allows it only after PASS. No FULL, update_file, restart or semantic refresh. Post-edit canonical freshness is UNKNOWN.

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/cycle_semantics/execution/state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 9b52250..96b9a44 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -98,6 +98,10 @@ class _DefinitionState:
         str, tuple[tuple[_ClassFact, ...], _ClassFact]
     ]
     class_facts_by_identity: dict[str, _ClassFact]
+    class_decorator_snapshots: dict[
+        str,
+        tuple[tuple[str, object], ...],
+    ]
 
 
 def _new_definition_state() -> _DefinitionState:
@@ -107,4 +111,5 @@ def _new_definition_state() -> _DefinitionState:
             fact.identity: fact
             for fact in _BUILTIN_CLASS_FACTS.values()
         },
+        class_decorator_snapshots={},
     )
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index f914265..68261cb 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -246,6 +246,7 @@ def _safe_passive_class_definition(
     *,
     annotation_semantics: str | None = None,
     allow_conditional_frozen_dataclass: bool = False,
+    allow_named_decorators: bool = False,
 ) -> bool:
     """Validate a class whose body has no unknown effects.
 
@@ -301,6 +302,15 @@ def _safe_passive_class_definition(
         or (
             bool(statement.decorator_list)
             and not conditional_dataclass
+            and not (
+                allow_named_decorators
+                and bool(statement.decorator_list)
+                and all(
+                    type(decorator) is ast.Name
+                    and not decorator.id.startswith("__")
+                    for decorator in statement.decorator_list
+                )
+            )
         )
         or getattr(statement, "type_params", ())
     ):
@@ -819,16 +829,26 @@ def _compile(
             )
             conditional_dataclass = (
                 assume_frozen_dataclass
-                and bool(stmt.decorator_list)
+                and annotation_semantics == "DEFERRED"
+                and len(stmt.decorator_list) == 1
+                and _exact_frozen_dataclass_decorator(
+                    stmt.decorator_list[0]
+                )
             )
             if not _safe_passive_class_definition(
                 stmt, annotation_semantics=annotation_semantics,
                 allow_conditional_frozen_dataclass=(
                     conditional_dataclass
                 ),
+                allow_named_decorators=not conditional_dataclass,
             ):
                 return None
 
+            ordinary_named_decorators = (
+                bool(stmt.decorator_list)
+                and not conditional_dataclass
+            )
+
             if not conditional_dataclass:
                 if (
                     type(stmt.lineno) is not int
@@ -841,6 +861,18 @@ def _compile(
                 definition_id = (
                     f"{logical}:{stmt.lineno}:{stmt.col_offset}"
                 )
+                if ordinary_named_decorators:
+                    steps.append(
+                        _Step(
+                            "SNAPSHOT_CLASS_DECORATORS",
+                            binding=stmt.name,
+                            definition_id=definition_id,
+                            decorator_names=tuple(
+                                decorator.id
+                                for decorator in stmt.decorator_list
+                            ),
+                        )
+                    )
                 steps.append(
                     _Step(
                         "PREPARE_PASSIVE_CLASS",
@@ -971,7 +1003,11 @@ def _compile(
             else:
                 steps.append(
                     _Step(
-                        "DEFINE_PASSIVE_CLASS",
+                        (
+                            "DEFINE_DECORATED_PASSIVE_CLASS"
+                            if ordinary_named_decorators
+                            else "DEFINE_PASSIVE_CLASS"
+                        ),
                         binding=stmt.name,
                         source_line=stmt.lineno,
                         source_column=stmt.col_offset,
@@ -1590,6 +1626,7 @@ def evaluate_package_import_order(
                 "DEFINE_STACKED_FUNCTION",
                 "DEFINE_OPAQUE_FUNCTION",
                 "DEFINE_PASSIVE_CLASS",
+                "DEFINE_DECORATED_PASSIVE_CLASS",
                 "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
             }
             and step.binding in children
@@ -1619,6 +1656,9 @@ def evaluate_package_import_order(
     definition_state = _new_definition_state()
     prepared_class_bases = definition_state.prepared_class_bases
     class_facts_by_identity = definition_state.class_facts_by_identity
+    class_decorator_snapshots = (
+        definition_state.class_decorator_snapshots
+    )
 
     bootstrap = "\x00ENTRY"
     execution_cursor = _new_execution_cursor(bootstrap)
@@ -1692,6 +1732,7 @@ def evaluate_package_import_order(
                         "DEFINE_STACKED_FUNCTION",
                         "DEFINE_OPAQUE_FUNCTION",
                         "DEFINE_PASSIVE_CLASS",
+                        "DEFINE_DECORATED_PASSIVE_CLASS",
                         "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
                     }
                     and step.binding in children
@@ -2343,6 +2384,35 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "SNAPSHOT_CLASS_DECORATORS":
+            if (
+                not step.definition_id
+                or not step.binding
+                or not step.decorator_names
+            ):
+                return result("UNKNOWN", module)
+
+            snapshot = _snapshot_named_decorators(
+                step.decorator_names,
+                namespaces[module],
+            )
+
+            if snapshot is None:
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.binding,
+                )
+
+            class_decorator_snapshots[
+                step.definition_id
+            ] = tuple(
+                zip(
+                    snapshot.names,
+                    snapshot.values,
+                )
+            )
+
         elif step.op == "PREPARE_PASSIVE_CLASS":
             if not step.binding or not step.definition_id:
                 return result("UNKNOWN", module, step.binding)
@@ -2426,6 +2496,13 @@ def evaluate_package_import_order(
                 return result("UNKNOWN", module, step.binding)
             prepared_class_bases[step.definition_id] = (base_facts, selected)
 
+        elif step.op == "DEFINE_DECORATED_PASSIVE_CLASS":
+            return result(
+                "UNKNOWN",
+                module,
+                step.binding,
+            )
+
         elif step.op == "DEFINE_PASSIVE_CLASS":
             prepared = prepared_class_bases.pop(
                 step.definition_id or "",
diff --git a/tests/test_cycle_semantics_class_decorator_staging.py b/tests/test_cycle_semantics_class_decorator_staging.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_class_decorator_staging.py
@@ -0,0 +1,145 @@
+"""Compilation staging for named class decorators; execution remains unknown."""
+
+import ast
+
+from contextor.core.cycle_semantics.execution.calls import (
+    _snapshot_named_decorators,
+)
+from contextor.core.cycle_semantics.execution.class_facts import (
+    _BUILTIN_CLASS_FACTS,
+)
+from contextor.core.cycle_semantics.package_model import (
+    _compile,
+    evaluate_package_import_order,
+)
+
+
+def _steps(source, **options):
+    return _compile(ast.parse(source), "pkg", True, **options)
+
+
+def test_single_named_class_decorator_staging():
+    steps = _steps(
+        "def identity(cls):\n    return cls\n"
+        "@identity\nclass C:\n    pass\n"
+    )
+    assert steps is not None
+    class_steps = steps[1:]
+    assert tuple(step.op for step in class_steps) == (
+        "SNAPSHOT_CLASS_DECORATORS",
+        "PREPARE_PASSIVE_CLASS",
+        "DEFINE_DECORATED_PASSIVE_CLASS",
+    )
+    assert class_steps[0].decorator_names == ("identity",)
+    assert len({step.definition_id for step in class_steps}) == 1
+    assert class_steps[0].definition_id is not None
+
+
+def test_decorated_class_body_import_staging():
+    steps = _steps(
+        "def identity(cls):\n    return cls\n"
+        "@identity\nclass C:\n    import pkg.body\n"
+    )
+    assert steps is not None
+    class_steps = steps[1:]
+    assert tuple(step.op for step in class_steps) == (
+        "SNAPSHOT_CLASS_DECORATORS",
+        "PREPARE_PASSIVE_CLASS",
+        "IMPORT",
+        "DEFINE_DECORATED_PASSIVE_CLASS",
+    )
+    assert class_steps[2].target == "pkg.body"
+    assert class_steps[2].class_local is True
+    assert class_steps[0].definition_id == class_steps[-1].definition_id
+
+
+def test_multiple_named_class_decorators_keep_source_order():
+    steps = _steps("@top\n@bottom\nclass C:\n    pass\n")
+    assert steps is not None
+    assert steps[0].op == "SNAPSHOT_CLASS_DECORATORS"
+    assert steps[0].decorator_names == ("top", "bottom")
+
+
+def test_same_name_decorator_stages_but_remains_unknown():
+    source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
+    steps = _steps(source)
+    assert steps is not None
+    assert steps[1].op == "SNAPSHOT_CLASS_DECORATORS"
+    assert steps[1].decorator_names == ("C",)
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)}, "pkg",
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_attribute_class_decorator_stays_unknown():
+    source = "@factory.decorate\nclass C:\n    pass\n"
+    assert _steps(source) is None
+    assert evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)}, "pkg",
+    ).outcome == "UNKNOWN"
+
+
+def test_call_class_decorator_stays_unknown():
+    source = "@factory()\nclass C:\n    pass\n"
+    assert _steps(source) is None
+    assert evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)}, "pkg",
+    ).outcome == "UNKNOWN"
+
+
+def test_qualified_conditional_frozen_dataclass_unchanged():
+    # Same qualified fixture and options as test_frozen_dataclass_direct_conditional_record.
+    source = (
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
+    )
+    steps = _steps(
+        source,
+        annotation_semantics="DEFERRED",
+        assume_frozen_dataclass=True,
+    )
+    assert steps is not None
+    assert any(
+        step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS"
+        for step in steps
+    )
+    assert not any(
+        step.op == "SNAPSHOT_CLASS_DECORATORS" for step in steps
+    )
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert result.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert len(result.assumed_dataclass_decorations) == 1
+    assert result.assumed_dataclass_decorations[0].class_name == "Graph"
+
+
+def test_ordinary_undecorated_class_unchanged():
+    steps = _steps("class C:\n    pass\n")
+    assert steps is not None
+    assert tuple(step.op for step in steps) == (
+        "PREPARE_PASSIVE_CLASS",
+        "DEFINE_PASSIVE_CLASS",
+    )
+
+
+def test_snapshot_preserves_class_fact_reference_without_execution():
+    class_fact = _BUILTIN_CLASS_FACTS["object"]
+    namespace = {"decorator": class_fact}
+    before = namespace.copy()
+    snapshot = _snapshot_named_decorators(
+        ("decorator",), namespace,
+    )
+    assert snapshot is not None
+    assert snapshot.values[0] is class_fact
+    assert namespace == before
```

## FINAL_VERDICT

REGRESSION_FAILURE / BLOCKED_SEMANTIC_INTEGRITY. No FINAL PASS. Per failure contract, no independent fix or test weakening; current staged changes remain uncommitted for auditor review.
