# CONTEXTOR C16-B03-P1D3-P15-R7 — conditional frozen dataclass initialization

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first. Both target module contexts at LIVE canonical revision 1135: `canonical_state=fresh`, `workspace_sync=verified`, graph/cycles fresh, cycle_semantics stale, 2 cyclic SCCs, 16 structural DFS paths. HEAD `388f116fba682466b5dba82bd74b42850f21f66e`; only pre-existing `walkthrough.md` modification before this task. Repository CPython 3.15.2.
- CODE_PATH_PROVED: inspected existing constructors/consumers and exact current anchors for `PackageImportAssessment`, `ConditionalNamespaceModelAssessment`, `SourceBoundConditionalNamespaceAssessment`, `_Step`, `_compile`, `_compile_reachable_prefix`, `_safe_passive_class_definition`, including all recursive compile calls, both package child shadowing checks, result construction and conditional wrapper forwarding. Material anchors matched the specified contract.

## EXACT_DECORATOR_RECOGNITION

- Added the specified `_exact_frozen_dataclass_decorator`: only a single call to name `dataclass` with no positional arguments and exactly `frozen=True` (literal bool) is admitted. Other decorators, option values, multiple keywords and bare `@dataclass` remain unsupported.
- Added the specified restricted field annotation checker for built-in names, string literals, tuples and bounded subscripts. Attribute annotations, call expressions and arbitrary annotation forms fail closed. This checker is applied only under the explicit conditional dataclass policy and deferred annotation semantics.

## RESTRICTED_CLASS_BODY_CONTRACT

- `_safe_passive_class_definition` accepts a keyword-only default-off conditional flag. When active and the exact decorator matches under `annotation_semantics="DEFERRED"`, it rejects direct class-body import, assignment, field initializer, unsupported annotation and special-name methods. Existing base, class-keyword/metaclass, type-parameter, method-decorator/default and unsupported-statement checks remain in force. Ordinary calls retain the prior decorator rejection.
- Source `@dataclass(frozen=True)` with `hard_edges: dict[str, set[str]]`, `soft_edges: dict[str, set[str]]` and an uncalled method with string return annotation is covered. It is a restricted model assumption, not execution of `dataclasses`.

## COMPILER_AND_EXECUTION_CHANGES

- `_Step` now carries `annotation_builtin_names`; `_compile` and `_compile_reachable_prefix` receive the default-off `assume_frozen_dataclass` flag, propagated through selected If bodies, class import fragments, function import fragments and both reachable-prefix compilation paths.
- A validated decorated class emits `DEFINE_CONDITIONAL_FROZEN_DATACLASS` with decorator AST line/column and sorted built-in annotation names; a regular class still emits `DEFINE_PASSIVE_CLASS`. Both package child-name shadowing checks recognize the new step.
- The package evaluator accepts private `_assume_frozen_dataclass_decoration` only as an exact bool and only together with lazy compilation and the R5 passive external policy. It records assumptions separately, with evidence scope `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`. Default and R5-only scopes remain unchanged.

## DYNAMIC_DECORATOR_BINDING_PROOF

- Before the conditional class step, the model requires the local `dataclass` binding to equal the R5 opaque sentinel `\x00ASSUMED_EXTERNAL:dataclasses:dataclass`; it also rejects any local binding of built-in names used in field annotations. A rebound decorator or shadowed `dict` returns UNKNOWN without a fabricated class binding or decoration record.
- On success it records `AssumedFrozenDataclassDecoration(module, class_name, "dataclasses.dataclass(frozen=True)", decorator line/column)`, then binds the existing passive-class sentinel and emits, in order, `ASSUMED_FROZEN_DATACLASS_DECORATION` followed by `DEFINE_PASSIVE_CLASS`. No decorator, analyzed class, generated method or external module is invoked.

## CONDITIONAL_POLICY_BOUNDARIES

- Both conditional namespace wrappers expose default-off `assume_frozen_dataclass_decoration`; reject nonbool with `INVALID_DATACLASS_DECORATOR_ASSUMPTION`; and reject true without passive external policy with `DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY`. Both carry `class_decorator_policy=STOP_AT_UNMODELED` by default or `ASSUME_PASSIVE_FROZEN_DATACLASS` when requested, including rejection outputs. Existing authority strings, source hashes, finder assumption, interpreter version gate and outcome mapping remain unchanged.
- Neither conditional MODEL_PASS nor conditional hazard is a canonical LIVE or runtime safety claim. No ordinary scenario model, warning suppression, persistence or MCP API was changed.

## REGRESSION_T01_T15

- T01 default decorator policy with R5 external opt-in: UNKNOWN, external dataclasses assumption, no decoration record, STOP policy — PASS.
- T02 exact frozen decorator with both policies: CONDITIONAL_MODEL_PASS / inner MODEL_PASS, distinct scope, one external and one decoration record at line 2 column 1, assumption event precedes passive-class event — PASS.
- T03 internal early binding before decoration: CONDITIONAL_EARLY_BINDING_HAZARD at `pkg.ns.a.Graph`; dataclasses external assumption present, no decoration record — PASS.
- T04 class bound before reentrant child import: CONDITIONAL_MODEL_PASS, recorded decoration, child FROM Graph succeeds — PASS.
- T05 wrong decorator and T06 four nonexact options: UNKNOWN, no decoration assumption — PASS.
- T07 dynamic field initializer: UNKNOWN, no decoration — PASS.
- T08 direct class import, class call, metaclass and base: UNKNOWN, no decoration — PASS.
- T09 rebound `dataclass` and T10 shadowed built-in `dict`: UNKNOWN, no decoration — PASS.
- T11 uncalled function containing decorated class: conditional pass without decoration event/record — PASS.
- T12 changed byte snapshot with unchanged indexed fingerprint: `SOURCE_FINGERPRINT_MISMATCH` before model — PASS.
- T13 nonbool flag: `INVALID_DATACLASS_DECORATOR_ASSUMPTION` — PASS.
- T14 missing external policy: `DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY` — PASS.
- T15 repeated accepted case: identical frozen results, event sequences, assumption records and JSON serialization; input snapshots unchanged — PASS.

## DIRECT_PACKAGE_MODEL_REGRESSIONS

- Default decorated class remains UNKNOWN without a decoration record. Private dataclass policy without R5 external assumption returns UNKNOWN. Exact opt-in with deferred annotation semantics records one decoration under the distinct conditional scope. Rebound decorator returns UNKNOWN without `DEFINE_PASSIVE_CLASS`. Existing regular MODEL_PASS and EARLY_BINDING_HAZARD tests in the targeted modules remain passing.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: exactly the four requested modules under repository CPython 3.15.2 with `PYTHONDONTWRITEBYTECODE=1`, `-B -m pytest -q -rs`: **238 passed in 18.07s**, 0 failed. A trailing space in one newly added test line was removed after that run; no behavior changed. `git diff --check` after that whitespace edit returned exit 0 for source/test files. No full suite.

## DEFAULT_MODEL_PARITY

- CONTRACT_PROVED by focused tests and default-off parameters: normal decorated definitions remain UNKNOWN, ordinary package model and earlier R5 passive-external-only behavior retain their outcomes and evidence scopes. No arbitrary decorator is accepted, no external whitelist or canonical MODEL_PASS promotion was added.

## EXISTING_EVENT_PARITY

- CODE_PATH_PROVED: regular class step and its existing event remain unchanged; the two new events are emitted only for the explicit validated conditional step. Existing event-order tests in the targeted suite passed, including internal early-binding behavior. No exhaustive byte-by-byte comparison of every historical trace was performed.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: watcher incorporated edited source. Current canonical revision **1144**, `canonical_state=fresh`, graph/cycles fresh, cycle_semantics **stale**, `resync_required=false`, zero syntax errors; structural SCC sizes 44/9 and 16 DFS paths unchanged. The two target production module contexts were `workspace_sync=verified` at revision 1142 during post-change synchronization; subsequent canonical/FileState revision is 1144 with exact disk/hash parity for all edited files. No unrelated production modifications.
- No FULL, update_file, Desktop/backend/LIVE restart, package installation, manual Git mutation or warning suppression.

## SOURCE_FILESTATE_PARITY

- DIRECT_EVIDENCE: canonical metadata and referenced FileState both revision **1144**, state_id `20261108_172727`, repo_id `ctx_8efc50d8`. Disk SHA-256 equals FileState for all four edited files: `package_model.py` `521c558f6b350dafcb7a3f3ba573fa94aa82b1357c66401b456fe74aea94a511`; `namespace_bound_model.py` `e0f54001d9ffaed6a597ae598c5c894fb7b19a6ab98d0020ad2788d5476643e6`; package-model test `f64200c69b99bbe5328643893b96af4dc8e148fb0d5f2b39c4621757717eb64a`; namespace-bound test `ca5918739356919d6a7a747e2decdbe8889a77cb602f9505de5b5fb096c584af`.

## CANONICAL_FRESHNESS_LIMITATION

The canonical cycle_semantics family remains stale after SOURCE_CHANGED. FileState parity and passing tests do not establish adoption of the new code by the persistent LIVE interpreter, nor do they justify a current canonical semantic classification or warning suppression. No FULL/restart was authorized.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/namespace_bound_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (report only; excluded from its own diff)

## FULL_DIFFS

Complete actual Git diffs of the four changed source/test files follow; `walkthrough.md` excluded.

```diff
diff --git a/contextor/core/cycle_semantics/namespace_bound_model.py b/contextor/core/cycle_semantics/namespace_bound_model.py
index ca00036..d7a88cd 100644
--- a/contextor/core/cycle_semantics/namespace_bound_model.py
+++ b/contextor/core/cycle_semantics/namespace_bound_model.py
@@ -46,6 +46,7 @@ class SourceBoundConditionalNamespaceAssessment:
         "NOT_RUNTIME_OR_LIVE_PROOF"
     )
     external_import_policy: str = "STOP_AT_UNMODELED"
+    class_decorator_policy: str = "STOP_AT_UNMODELED"
 
 
 def evaluate_source_bound_conditional_namespace_import_order(
@@ -58,6 +59,7 @@ def evaluate_source_bound_conditional_namespace_import_order(
     standard_finder_assumed: bool = False,
     target_python_version: tuple[int, int] | None = None,
     assume_passive_external_imports: bool = False,
+    assume_frozen_dataclass_decoration: bool = False,
 ) -> SourceBoundConditionalNamespaceAssessment:
     """Parse indexed byte snapshots and conditionally evaluate PEP 420.
 
@@ -74,6 +76,11 @@ def evaluate_source_bound_conditional_namespace_import_order(
         if assume_passive_external_imports is True
         else "STOP_AT_UNMODELED"
     )
+    class_decorator_policy = (
+        "ASSUME_PASSIVE_FROZEN_DATACLASS"
+        if assume_frozen_dataclass_decoration is True
+        else "STOP_AT_UNMODELED"
+    )
 
     def reject(
         reason: str,
@@ -86,8 +93,17 @@ def evaluate_source_bound_conditional_namespace_import_order(
             source_evidence_sha256=digest,
             conditional_assessment=None,
             external_import_policy=external_import_policy,
+            class_decorator_policy=class_decorator_policy,
         )
 
+    if type(assume_frozen_dataclass_decoration) is not bool:
+        return reject("INVALID_DATACLASS_DECORATOR_ASSUMPTION")
+    if (
+        assume_frozen_dataclass_decoration
+        and not assume_passive_external_imports
+    ):
+        return reject("DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY")
+
     if type(assume_passive_external_imports) is not bool:
         return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")
 
@@ -206,6 +222,9 @@ def evaluate_source_bound_conditional_namespace_import_order(
         assume_passive_external_imports=(
             assume_passive_external_imports
         ),
+        assume_frozen_dataclass_decoration=(
+            assume_frozen_dataclass_decoration
+        ),
     )
 
     # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
@@ -218,4 +237,5 @@ def evaluate_source_bound_conditional_namespace_import_order(
         source_evidence_sha256=digest,
         conditional_assessment=conditional,
         external_import_policy=external_import_policy,
+        class_decorator_policy=class_decorator_policy,
     )
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 1f483ca..a690976 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -41,6 +41,15 @@ class ReachedUnmodeledImport:
     column: int | None
 
 
+@dataclass(frozen=True)
+class AssumedFrozenDataclassDecoration:
+    module: str
+    class_name: str
+    decorator: str
+    line: int
+    column: int
+
+
 @dataclass(frozen=True)
 class PackageImportAssessment:
     entry_module: str
@@ -55,6 +64,9 @@ class PackageImportAssessment:
     assumed_external_imports: (
         tuple[ReachedUnmodeledImport, ...]
     ) = ()
+    assumed_dataclass_decorations: (
+        tuple[AssumedFrozenDataclassDecoration, ...]
+    ) = ()
 
 
 @dataclass(frozen=True)
@@ -69,6 +81,7 @@ class _Step:
     class_local: bool = False
     source_line: int | None = None
     source_column: int | None = None
+    annotation_builtin_names: tuple[str, ...] = ()
 
 
 @dataclass
@@ -161,10 +174,64 @@ def _safe_passive_function_definition(
     return True
 
 
+def _exact_frozen_dataclass_decorator(
+    decorator: ast.AST,
+) -> bool:
+    return (
+        isinstance(decorator, ast.Call)
+        and isinstance(decorator.func, ast.Name)
+        and decorator.func.id == "dataclass"
+        and not decorator.args
+        and len(decorator.keywords) == 1
+        and decorator.keywords[0].arg == "frozen"
+        and isinstance(
+            decorator.keywords[0].value,
+            ast.Constant,
+        )
+        and decorator.keywords[0].value.value is True
+        and type(
+            decorator.keywords[0].value.value
+        ) is bool
+    )
+
+
+def _restricted_dataclass_field_annotation(
+    node: ast.AST,
+) -> bool:
+    if isinstance(node, ast.Name):
+        return node.id in {
+            "str", "int", "bool", "float",
+            "bytes", "dict", "list",
+            "set", "tuple",
+        }
+
+    if isinstance(node, ast.Constant):
+        return type(node.value) is str
+
+    if isinstance(node, ast.Tuple):
+        return all(
+            _restricted_dataclass_field_annotation(item)
+            for item in node.elts
+        )
+
+    if isinstance(node, ast.Subscript):
+        return (
+            _restricted_dataclass_field_annotation(
+                node.value
+            )
+            and _restricted_dataclass_field_annotation(
+                node.slice
+            )
+        )
+
+    return False
+
+
 def _safe_passive_class_definition(
     statement: ast.ClassDef,
     *,
     annotation_semantics: str | None = None,
+    allow_conditional_frozen_dataclass: bool = False,
 ) -> bool:
     """Validate a class whose body has no unknown effects.
 
@@ -175,16 +242,51 @@ def _safe_passive_class_definition(
     Direct class-body imports execute before class-name
     binding. Method bodies remain deferred.
     """
+    conditional_dataclass = (
+        allow_conditional_frozen_dataclass
+        and annotation_semantics == "DEFERRED"
+        and len(statement.decorator_list) == 1
+        and _exact_frozen_dataclass_decorator(
+            statement.decorator_list[0]
+        )
+    )
     if (
         not statement.name.isidentifier()
         or statement.name.startswith("__")
         or statement.bases
         or statement.keywords
-        or statement.decorator_list
+        or (
+            bool(statement.decorator_list)
+            and not conditional_dataclass
+        )
         or getattr(statement, "type_params", ())
     ):
         return False
 
+    if conditional_dataclass:
+        for body_statement in statement.body:
+            if isinstance(
+                body_statement,
+                (ast.Import, ast.ImportFrom, ast.Assign),
+            ):
+                return False
+
+            if isinstance(body_statement, ast.AnnAssign):
+                if (
+                    body_statement.value is not None
+                    or not _restricted_dataclass_field_annotation(
+                        body_statement.annotation
+                    )
+                ):
+                    return False
+
+            if isinstance(
+                body_statement,
+                (ast.FunctionDef, ast.AsyncFunctionDef),
+            ):
+                if body_statement.name.startswith("__"):
+                    return False
+
     for index, body_statement in enumerate(
         statement.body
     ):
@@ -458,6 +560,7 @@ def _compile(
     _depth: int = 0,
     typing_guard: RecognizedTypingGuard | None = None,
     annotation_semantics: str | None = None,
+    assume_frozen_dataclass: bool = False,
 ) -> tuple[_Step, ...] | None:
     steps: list[_Step] = []
 
@@ -671,6 +774,7 @@ def _compile(
                 package,
                 _depth=_depth + 1,
                 annotation_semantics=annotation_semantics,
+                assume_frozen_dataclass=assume_frozen_dataclass,
             )
 
             if selected_steps is None:
@@ -750,8 +854,15 @@ def _compile(
                 steps.append(_Step("BIND", binding=stmt.target.id))
 
         elif isinstance(stmt, ast.ClassDef):
+            conditional_dataclass = (
+                assume_frozen_dataclass
+                and bool(stmt.decorator_list)
+            )
             if not _safe_passive_class_definition(
                 stmt, annotation_semantics=annotation_semantics,
+                allow_conditional_frozen_dataclass=(
+                    conditional_dataclass
+                ),
             ):
                 return None
 
@@ -786,6 +897,7 @@ def _compile(
                     logical,
                     package,
                     _depth=_depth + 1,
+                    assume_frozen_dataclass=assume_frozen_dataclass,
                 )
                 if (
                     compiled is None
@@ -805,12 +917,29 @@ def _compile(
                     for item in compiled
                 )
 
-            steps.append(
-                _Step(
-                    "DEFINE_PASSIVE_CLASS",
-                    binding=stmt.name,
+            if conditional_dataclass:
+                steps.append(
+                    _Step(
+                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
+                        binding=stmt.name,
+                        source_line=stmt.decorator_list[0].lineno,
+                        source_column=stmt.decorator_list[0].col_offset,
+                        annotation_builtin_names=tuple(sorted({
+                            node.id
+                            for field in stmt.body
+                            if isinstance(field, ast.AnnAssign)
+                            for node in ast.walk(field.annotation)
+                            if isinstance(node, ast.Name)
+                        })),
+                    )
+                )
+            else:
+                steps.append(
+                    _Step(
+                        "DEFINE_PASSIVE_CLASS",
+                        binding=stmt.name,
+                    )
                 )
-            )
 
         elif isinstance(stmt, ast.FunctionDef):
             if not _safe_passive_function_definition(
@@ -853,6 +982,7 @@ def _compile(
                         fragment,
                         logical,
                         package,
+                        assume_frozen_dataclass=assume_frozen_dataclass,
                     )
 
                     if (
@@ -942,6 +1072,7 @@ def _compile_reachable_prefix(
     *,
     typing_guard: RecognizedTypingGuard | None,
     annotation_semantics: str | None,
+    assume_frozen_dataclass: bool = False,
 ) -> tuple[_Step, ...] | None:
     """Preserve modeled effects before the first unsupported statement.
 
@@ -961,6 +1092,7 @@ def _compile_reachable_prefix(
         package,
         typing_guard=typing_guard,
         annotation_semantics=annotation_semantics,
+        assume_frozen_dataclass=assume_frozen_dataclass,
     )
 
     if complete is not None:
@@ -981,6 +1113,7 @@ def _compile_reachable_prefix(
             package,
             typing_guard=typing_guard,
             annotation_semantics=annotation_semantics,
+            assume_frozen_dataclass=assume_frozen_dataclass,
         )
 
     # The existing restricted compiler processes top-level
@@ -1020,6 +1153,7 @@ def evaluate_package_import_order(
     annotation_semantics: str | None = None,
     _compile_on_first_import: bool = False,
     _assume_passive_external_imports: bool = False,
+    _assume_frozen_dataclass_decoration: bool = False,
 ) -> PackageImportAssessment:
     """Simulate a restricted closed regular-package source set.
 
@@ -1030,6 +1164,9 @@ def evaluate_package_import_order(
     """
     events: list[PackageModelEvent] = []
     assumed_external_imports: list[ReachedUnmodeledImport] = []
+    assumed_dataclass_decorations: list[
+        AssumedFrozenDataclassDecoration
+    ] = []
 
     def result(
         outcome: str,
@@ -1047,7 +1184,10 @@ def evaluate_package_import_order(
             symbol,
             tuple(events),
             evidence_scope=(
-                "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
+                "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+                "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+                if _assume_frozen_dataclass_decoration is True
+                else "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
                 "ASSUMPTION_NOT_RUNTIME_PROOF"
                 if _assume_passive_external_imports is True
                 else "RESTRICTED_REGULAR_PACKAGE_MODEL"
@@ -1056,6 +1196,9 @@ def evaluate_package_import_order(
             assumed_external_imports=tuple(
                 assumed_external_imports
             ),
+            assumed_dataclass_decorations=tuple(
+                assumed_dataclass_decorations
+            ),
         )
 
     if (
@@ -1066,6 +1209,14 @@ def evaluate_package_import_order(
         }
         or type(_compile_on_first_import) is not bool
         or type(_assume_passive_external_imports) is not bool
+        or type(_assume_frozen_dataclass_decoration) is not bool
+        or (
+            _assume_frozen_dataclass_decoration
+            and (
+                not _compile_on_first_import
+                or not _assume_passive_external_imports
+            )
+        )
         or (
             _assume_passive_external_imports
             and not _compile_on_first_import
@@ -1281,6 +1432,7 @@ def evaluate_package_import_order(
                 "DEFINE_FUNCTION",
                 "DEFINE_OPAQUE_FUNCTION",
                 "DEFINE_PASSIVE_CLASS",
+                "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
             }
             and step.binding in children
             for step in programs[package]
@@ -1383,6 +1535,9 @@ def evaluate_package_import_order(
                     if has_future_annotations
                     else annotation_semantics
                 ),
+                assume_frozen_dataclass=(
+                    _assume_frozen_dataclass_decoration
+                ),
             )
 
             if program is None:
@@ -1403,6 +1558,7 @@ def evaluate_package_import_order(
                         "DEFINE_FUNCTION",
                         "DEFINE_OPAQUE_FUNCTION",
                         "DEFINE_PASSIVE_CLASS",
+                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
                     }
                     and step.binding in children
                     for step in program
@@ -1779,6 +1935,47 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS":
+            if (
+                namespaces[module].get("dataclass")
+                != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
+                or any(
+                    name in namespaces[module]
+                    for name in step.annotation_builtin_names
+                )
+            ):
+                return result("UNKNOWN", module, step.binding)
+
+            assumed_dataclass_decorations.append(
+                AssumedFrozenDataclassDecoration(
+                    module=module,
+                    class_name=step.binding,
+                    decorator="dataclasses.dataclass(frozen=True)",
+                    line=step.source_line,
+                    column=step.source_column,
+                )
+            )
+            namespaces[module][step.binding] = (
+                "\x00PASSIVE_CLASS:"
+                + module
+                + ":"
+                + step.binding
+            )
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "ASSUMED_FROZEN_DATACLASS_DECORATION",
+                    symbol=step.binding,
+                )
+            )
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_PASSIVE_CLASS",
+                    symbol=step.binding,
+                )
+            )
+
         elif step.op == "DEFINE_PASSIVE_CLASS":
             namespaces[module][step.binding] = (
                 "\x00PASSIVE_CLASS:"
@@ -1934,6 +2131,7 @@ class ConditionalNamespaceModelAssessment:
     )
     target_python_version: tuple[int, int] | None = None
     external_import_policy: str = "STOP_AT_UNMODELED"
+    class_decorator_policy: str = "STOP_AT_UNMODELED"
 
 
 def _conditional_annotation_mode_for_target(
@@ -2134,6 +2332,7 @@ def evaluate_conditional_namespace_import_order(
     *,
     target_python_version: tuple[int, int] | None = None,
     assume_passive_external_imports: bool = False,
+    assume_frozen_dataclass_decoration: bool = False,
 ) -> ConditionalNamespaceModelAssessment:
     """Evaluate a supplied closed PEP 420 inventory conditionally.
 
@@ -2159,6 +2358,11 @@ def evaluate_conditional_namespace_import_order(
         if assume_passive_external_imports is True
         else "STOP_AT_UNMODELED"
     )
+    class_decorator_policy = (
+        "ASSUME_PASSIVE_FROZEN_DATACLASS"
+        if assume_frozen_dataclass_decoration is True
+        else "STOP_AT_UNMODELED"
+    )
 
     def reject(
         reason: str,
@@ -2176,8 +2380,17 @@ def evaluate_conditional_namespace_import_order(
                 else None
             ),
             external_import_policy=external_import_policy,
+            class_decorator_policy=class_decorator_policy,
         )
 
+    if type(assume_frozen_dataclass_decoration) is not bool:
+        return reject("INVALID_DATACLASS_DECORATOR_ASSUMPTION")
+    if (
+        assume_frozen_dataclass_decoration
+        and not assume_passive_external_imports
+    ):
+        return reject("DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY")
+
     if type(assume_passive_external_imports) is not bool:
         return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")
 
@@ -2397,6 +2610,9 @@ def evaluate_conditional_namespace_import_order(
         _assume_passive_external_imports=(
             assume_passive_external_imports
         ),
+        _assume_frozen_dataclass_decoration=(
+            assume_frozen_dataclass_decoration
+        ),
     )
 
     conditional_outcomes = {
@@ -2424,4 +2640,5 @@ def evaluate_conditional_namespace_import_order(
         namespace_parents=namespace_parents,
         target_python_version=target_python_version,
         external_import_policy=external_import_policy,
+        class_decorator_policy=class_decorator_policy,
     )
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index b98311a..a8b5de5 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -6,6 +6,8 @@ import hashlib
 import json
 from dataclasses import asdict
 
+import pytest
+
 from contextor.core.source import SourceSnapshot
 from contextor.core.cycle_semantics.namespace_bound_model import (
     evaluate_source_bound_conditional_namespace_import_order,
@@ -114,6 +116,257 @@ def _external_result(source, *, assume=False, child=None):
     )
 
 
+_FROZEN_CLASS = (
+    "@dataclass(frozen=True)\n"
+    "class Graph:\n"
+    "    hard_edges: dict[str, set[str]]\n"
+    "    soft_edges: dict[str, set[str]]\n"
+    "    def without_module(self, name: str) -> \"Graph\":\n"
+    "        return self\n"
+)
+
+
+def _dataclass_result(source, *, decorate=False, external=True, child=None):
+    return evaluate_source_bound_conditional_namespace_import_order(
+        *_external_case(source, child=child),
+        "pkg.ns.a",
+        standard_finder_assumed=True,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=external,
+        assume_frozen_dataclass_decoration=decorate,
+    )
+
+
+def test_frozen_dataclass_t01_default_unknown():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n" + _FROZEN_CLASS
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "UNKNOWN"
+    assert tuple(x.target for x in model.assumed_external_imports) == (
+        "dataclasses",
+    )
+    assert model.assumed_dataclass_decorations == ()
+    assert result.class_decorator_policy == "STOP_AT_UNMODELED"
+
+
+def test_frozen_dataclass_t02_exact_conditional_pass():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n" + _FROZEN_CLASS,
+        decorate=True,
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert model.outcome == "MODEL_PASS"
+    assert model.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert len(model.assumed_external_imports) == 1
+    assert model.assumed_external_imports[0].target == "dataclasses"
+    assert len(model.assumed_dataclass_decorations) == 1
+    row = model.assumed_dataclass_decorations[0]
+    assert (row.module, row.class_name, row.decorator) == (
+        "pkg.ns.a", "Graph", "dataclasses.dataclass(frozen=True)"
+    )
+    assert (row.line, row.column) == (2, 1)
+    assert result.class_decorator_policy == "ASSUME_PASSIVE_FROZEN_DATACLASS"
+    operations = [event.operation for event in model.events]
+    assert operations.index("ASSUMED_FROZEN_DATACLASS_DECORATION") < (
+        operations.index("DEFINE_PASSIVE_CLASS")
+    )
+
+
+def test_frozen_dataclass_t03_internal_hazard_retained():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "import pkg.ns.b\n"
+        "@dataclass(frozen=True)\n"
+        "class Graph:\n"
+        "    value: int\n",
+        decorate=True,
+        child="from pkg.ns.a import Graph\n",
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "CONDITIONAL_EARLY_BINDING_HAZARD"
+    assert model.outcome == "EARLY_BINDING_HAZARD"
+    assert (model.target_module, model.symbol) == ("pkg.ns.a", "Graph")
+    assert len(model.assumed_external_imports) == 1
+    assert model.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_t04_class_bound_before_import():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class Graph:\n"
+        "    value: int\n"
+        "import pkg.ns.b\n",
+        decorate=True,
+        child="from pkg.ns.a import Graph\n",
+    )
+    model = result.conditional_assessment.model_assessment
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert len(model.assumed_dataclass_decorations) == 1
+    assert any(
+        event.operation == "FROM" and event.symbol == "Graph"
+        for event in model.events
+    )
+
+
+@pytest.mark.parametrize(
+    "decorator",
+    ["other(frozen=True)", "dataclass(frozen=False)",
+     "dataclass(frozen=flag)", "dataclass",
+     "dataclass(slots=True, frozen=True)"],
+)
+def test_frozen_dataclass_t05_t06_nonexact_unknown(decorator):
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        f"@{decorator}\nclass Graph:\n    value: int\n",
+        decorate=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert (
+        result.conditional_assessment.model_assessment
+        .assumed_dataclass_decorations
+    ) == ()
+
+
+def test_frozen_dataclass_t07_dynamic_field_unknown():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class Graph:\n"
+        "    value: int = field(default_factory=make)\n",
+        decorate=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()
+
+
+@pytest.mark.parametrize(
+    "class_text",
+    [
+        "class Graph:\n    import os\n",
+        "class Graph:\n    run()\n",
+        "class Graph(metaclass=Meta):\n    value: int\n",
+        "class Graph(Base):\n    value: int\n",
+    ],
+)
+def test_frozen_dataclass_t08_class_effects_unknown(class_text):
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n" + class_text,
+        decorate=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_t09_rebound_decorator_unknown():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "dataclass = 1\n"
+        "@dataclass(frozen=True)\n"
+        "class Graph:\n    value: int\n",
+        decorate=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_t10_builtin_shadow_unknown():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "dict = 1\n"
+        "@dataclass(frozen=True)\n"
+        "class Graph:\n    value: dict[str, int]\n",
+        decorate=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_t11_unreached_definition():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "def later():\n"
+        "    @dataclass(frozen=True)\n"
+        "    class Graph:\n"
+        "        value: int\n",
+        decorate=True,
+    )
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_t12_fingerprint_mismatch():
+    roots, bindings, hashes, snapshots = _external_case(
+        "from dataclasses import dataclass\n" + _FROZEN_CLASS
+    )
+    snapshots["pkg.ns.a"] = _snapshot("changed = True\n")
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        roots, bindings, hashes, snapshots, "pkg.ns.a",
+        standard_finder_assumed=True,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+        assume_frozen_dataclass_decoration=True,
+    )
+    assert (result.outcome, result.reason) == (
+        "UNKNOWN", "SOURCE_FINGERPRINT_MISMATCH"
+    )
+    assert result.conditional_assessment is None
+
+
+def test_frozen_dataclass_t13_invalid_policy():
+    result = evaluate_source_bound_conditional_namespace_import_order(
+        *_external_case("pass\n"), "pkg.ns.a",
+        assume_passive_external_imports=True,
+        assume_frozen_dataclass_decoration="yes",
+    )
+    assert (result.outcome, result.reason) == (
+        "UNKNOWN", "INVALID_DATACLASS_DECORATOR_ASSUMPTION"
+    )
+
+
+def test_frozen_dataclass_t14_requires_external_policy():
+    result = _dataclass_result("pass\n", decorate=True, external=False)
+    assert (result.outcome, result.reason) == (
+        "UNKNOWN", "DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY"
+    )
+
+
+def test_frozen_dataclass_t15_deterministic():
+    args = _external_case(
+        "from dataclasses import dataclass\n" + _FROZEN_CLASS
+    )
+    before = dict(args[3])
+    first = evaluate_source_bound_conditional_namespace_import_order(
+        *args, "pkg.ns.a", standard_finder_assumed=True,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+        assume_frozen_dataclass_decoration=True,
+    )
+    second = evaluate_source_bound_conditional_namespace_import_order(
+        *args, "pkg.ns.a", standard_finder_assumed=True,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+        assume_frozen_dataclass_decoration=True,
+    )
+    assert first == second
+    assert first.conditional_assessment.model_assessment.events == (
+        second.conditional_assessment.model_assessment.events
+    )
+    assert first.conditional_assessment.model_assessment.assumed_dataclass_decorations == (
+        second.conditional_assessment.model_assessment.assumed_dataclass_decorations
+    )
+    assert json.dumps(asdict(first), sort_keys=True) == json.dumps(
+        asdict(second), sort_keys=True
+    )
+    assert args[3] == before
+
+
 def test_external_policy_t01_default_still_unknown():
     result = _external_result("import os\nvalue=1\nimport pkg.ns.b\n")
     model = result.conditional_assessment.model_assessment
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index e222bbb..a8cc90d 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -21,6 +21,73 @@ def _model(source, entry):
     )
 
 
+def test_frozen_dataclass_default_model_unknown():
+    result = _model(
+        {"pkg.__init__": (
+            "from dataclasses import dataclass\n"
+            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
+        )},
+        "pkg",
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_private_policy_requires_external():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(
+            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
+        )},
+        "pkg",
+        _compile_on_first_import=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+
+
+def test_frozen_dataclass_direct_conditional_record():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(
+            "from dataclasses import dataclass\n"
+            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
+        )},
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
+def test_frozen_dataclass_rebound_name_does_not_bind_class():
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(
+            "from dataclasses import dataclass\n"
+            "dataclass = 1\n"
+            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
+        )},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "Graph"
+        for event in result.events
+    )
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```

## FINAL_VERDICT

PASS — restricted conditional frozen-dataclass contract implemented with default-off policy, explicit assumptions and fail-closed guards; 238 targeted tests passed, source/FileState parity and structural MCP audit succeeded. Canonical cycle_semantics remains stale and persistent LIVE adoption is unverified.
