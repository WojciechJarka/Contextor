# PREFLIGHT

**DIRECT_EVIDENCE**

- HEAD before and after the task: 053dae50a5eb9b7d1b9c361c71b993f4fffb0ee4.
- The preflight worktree was clean. The post-task worktree contains only the authorized test file plus this report.
- Active interpreter: C:\Temp\Contextor_Repo\.venv\Scripts\python.exe, CPython 3.15.2. The reference runner uses that interpreter with -I and -B.
- Contextor MCP preflight at canonical LIVE revision 1370: canonical state fresh and workspace_sync verified for package_model.py, execution/calls.py, execution/state.py, execution/imports.py, and the T1 test module. The cycle_semantics family was stale and advisory_warning was null.
- The T1 test file was present. It contained five A-E parametrized reference cases and four additional test functions, for nine collected cases before this task. Their original fixture sources and expectations remain unchanged.
- Source discovery used Contextor MCP get_source_range, get_module_context, get_symbol_call_context, and get_symbol_lineage. The call-context tool is explicitly intra-module and returned zero edges for the queried helpers; that does not establish absence of inter-module callers. The fetched lineage includes unresolved CALL_RESULT edges, so literal source is the evidence for call and return behavior below.

# FILES_CHANGED

- tests/test_cycle_semantics_cross_module_decorator_baseline.py — authorized test-only additions and CPython observation fields. No production source, other tests, or documentation source was changed.
- walkthrough.md — task report, excluded from the source/test FILES_CHANGED list.

# SUPPORTED_BODY_BASELINES

**DIRECT_EVIDENCE — CPython 3.15.2**

- A2: import succeeds; the decorator is called once; final f is the same function object passed to identity; f() returns None.
- B2: import succeeds; pkg.effect is imported by the decorator; final f is the same function object passed to apply_decorator; f() returns None.
- C2: import succeeds through the imported alias; final f is the same function object passed to identity; f() returns None.
- D2: import succeeds; replace is called once; final f is None.
- The original A-E reference cases and their final expectations are unchanged.

**DIRECT_EVIDENCE — model**

All A2-D2 results are UNKNOWN in RESTRICTED_REGULAR_PACKAGE_MODEL. Each reaches the indexed FROM in pkg.app and has no CALL_FUNCTION event. No A2-D2 model event targets pkg.effect. For B2 this confirms that the CPython decorator body’s import is not fabricated as a model effect.

Complete event sequences, written as (module, operation, target, symbol):

- A2: (ENTRY, START_IMPORT, pkg, None); (pkg, READY, None, None); (ENTRY, START_IMPORT, pkg.app, None); (pkg.app, START_IMPORT, pkg.decorators, None); (pkg.decorators, DEFINE_FUNCTION, None, identity); (pkg.decorators, READY, None, None); (pkg, BIND_CHILD, pkg.decorators, decorators); (pkg.app, FROM, pkg.decorators, identity).
- B2: same package/import prefix; pkg.decorators emits DEFINE_FUNCTION for apply_decorator; final event is (pkg.app, FROM, pkg.decorators, apply_decorator). No pkg.effect event is emitted.
- C2: same package/import prefix as A2; final event is (pkg.app, FROM, pkg.decorators, identity). The app binding is alias, while the FROM event symbol is the exported name identity.
- D2: same package/import prefix; pkg.decorators emits DEFINE_OPAQUE_FUNCTION for replace; final event is (pkg.app, FROM, pkg.decorators, replace).

**CODE_PATH_PROVED**

- The app function f has a pass-only body in every A2-D2 fixture, so the original A-E return-1 compilation failure is not present in these new application fixtures.
- D2 has a separate current-model limitation: explicit return None is an ast.Return whose value is ast.Constant(None). The restricted function compiler accepts a bare return (value is None), but not this explicit constant expression; it emits DEFINE_OPAQUE_FUNCTION for replace. Thus D2’s UNKNOWN result is observed after FROM but does not independently isolate the _RestrictedFunction defining-module guard. This is reported as a model observation; the specified fixture and expectations were preserved.

# INDEXED_FROM_IMPORT_IDENTITY

**DIRECT_EVIDENCE**

- Existing test test_indexed_from_import_availability_does_not_admit_cross_module_call directly asserts that _execute_from_binding stores the exact imported object in the importing namespace and that the alias is the same _RestrictedFunction instance.
- In execution/imports.py:206-258, _execute_from_binding reads namespaces[target][member] and, for non-local imports, stores that same object under namespaces[module][step.binding]. The existing test also confirms that the object retains defining_module=pkg.decorators.
- The A2-C2 CPython observations preserve the original decorated function identity where the decorator returns its input. D2 correctly has no such final-binding identity because CPython returns None.

# CPYTHON_RELATIVE_IMPORT_CONTEXT

**DIRECT_EVIDENCE**

- E2 imports relative_decorator from the pkg.decorators package. That function runs from pkg.app and executes from . import effect.
- CPython reports the decorator function globals’ __package__ as pkg.decorators, loads pkg.decorators.effect, does not load pkg.effect, and leaves f bound to the string 'defining-package-effect'. The competing pkg.effect fixture contains 'caller-package-effect'.
- This distinguishes the defining package context from pkg.app’s package context. CPython import succeeds and the decorator runs once.

**CODE_PATH_PROVED**

- package_model.py:555-625 calculates a relative ImportFrom target from the logical module/package passed to _compile.
- package_model.py:1035-1165 compiles permitted function-body import statements by recursively calling _compile with the function’s logical module and package.
- The import operation is still executed when the function frame reaches its compiled step. Therefore target selection is compile-time for this restricted representation, while import execution is call-time.
- E2’s current model outcome is UNKNOWN after FROM; the imported decorator is represented as DEFINE_OPAQUE_FUNCTION and there is no CALL_FUNCTION or relative-effect import event.

# CPYTHON_GLOBAL_NAMESPACE_CONTEXT

**DIRECT_EVIDENCE**

- F2 defines marker='decorators-global' in pkg.decorators and marker='app-global' in pkg.app.
- CPython calls read_marker and binds f to 'decorators-global'. The defining module’s global is read.
- The current model result is UNKNOWN after FROM. It emits BIND for each module’s marker and DEFINE_OPAQUE_FUNCTION for read_marker; it does not call that decorator.

# CURRENT_FUNCTION_FRAME_SEMANTICS

**DIRECT_EVIDENCE — source anchors**

- contextor/core/cycle_semantics/execution/calls.py:8-12: _RestrictedFunction stores defining_module, body, and parameters.
- contextor/core/cycle_semantics/execution/calls.py:59-83: _execute_restricted_call looks up the target in namespaces[module], requires a _RestrictedFunction whose defining_module equals module, checks argument count, and binds parameters into local_bindings.
- contextor/core/cycle_semantics/execution/calls.py:86-101: _execute_restricted_object_call applies the same defining-module equality and one-parameter check, binds the argument, and returns the stored body.
- contextor/core/cycle_semantics/execution/state.py:31-45: _FunctionFrame has module, index, steps, local_bindings, result_binding, decorator_final_binding, and remaining_decorators. It has no separate defining-module or caller-module field.
- contextor/core/cycle_semantics/execution/state.py:56-77: _frame_position reads the function frame’s module; _advance_frame preserves it and carries the same locals and continuation fields.
- package_model.py:1680-1700: the evaluator gets module and index from _frame_position and selects the active function frame’s stored steps.

**CODE_PATH_PROVED**

- In package_model.py:2217-2257, DEFINE_DECORATED_FUNCTION calls _execute_restricted_call with the currently evaluating module. If accepted, it pushes _FunctionFrame with that same module. The stacked decorator branch at package_model.py:2146-2215 similarly passes the current module into _execute_restricted_object_call and the new frame.
- Consequently, the frame module is the evaluator’s active importing/applying module. The restricted callable separately records defining_module, but the current gate requires those identities to be equal. They are not represented as two execution environments in _FunctionFrame.
- Function-body compilation at package_model.py:1035-1165 admits only pass, bare return, return of the sole parameter, and supported imports. General global-expression returns such as F2 are opaque in this model.
- For function-local imports, execution/imports.py:50-90 and :206-258 suppress module-namespace writes when function_local is true. The evaluator advances the frame and emits the import event; these helpers do not place imported values into _FunctionFrame.local_bindings. The supported function-body language does not otherwise provide general local/global lookup.

# CALLER_VS_DEFINING_MODULE

**CODE_PATH_PROVED**

- The current cross-module call is rejected before a function frame is pushed because _execute_restricted_call and _execute_restricted_object_call require defining_module == module.
- If only that equality check were removed, the existing call sites would still pass pkg.app as module and create a frame whose module is pkg.app. The evaluator derives the active module from that field, and import/call namespace operations use namespaces[module]. This would retain caller/applying-module environment behavior for frame execution.
- Relative import target strings already compiled from the defining logical module would remain in the steps, but runtime event attribution and namespace operations would still use the caller module. This is a source-path conclusion about the hypothetical guard-only change; the prohibited cross-module execution path was not executed.
- CPython E2 and F2 independently show the language behavior: a function’s relative-import package and global namespace come from its defining module.

# FUNCTION_RETURN_TRANSPORT

**CODE_PATH_PROVED**

- package_model.py:2640-2705 implements RETURN_FUNCTION. A named returned value is read from active_frame.local_bindings; a bare return yields None. The function frame is popped before continuation.
- When decorators remain, the returned value is passed as the next decorator’s argument and a new frame is pushed with the stored final binding and remaining decorators. After the last decorator, namespaces[module][decorator_final_binding] receives the returned value.
- package_model.py:1772-1845 handles natural frame completion. It passes None to the next decorator when a decorator body completes without explicit return, and otherwise binds None after the final decorator. Ordinary result_binding completion also receives None.
- These transfers are within the frame module currently in use. There is no executed cross-module return transport in this model because the foreign callable fails the defining-module equality gate first.
- Contextor lineage returned two unresolved CALL_RESULT edges for calls in calls.py and an unresolved frame-constructor CALL_RESULT edge for state.py. Those lineage edges are not treated as proof of return transport; the evaluator source above is the direct evidence.

# RECURSION_AND_BUDGET_GUARDS

**DIRECT_EVIDENCE**

- execution/state.py:80-92 initializes _ExecutionCursor with a 10000 step_budget. The cursor has frames and step_budget but no recursion-depth field.
- package_model.py:1680-1689 decrements the budget on every evaluator loop iteration and returns UNKNOWN below zero. Natural function-frame completion compensates by incrementing one at package_model.py:1793-1845.
- package_model.py:2707-2755 pushes a function frame for an accepted CALL_FUNCTION. No separate call-depth guard appears in this path.
- package_model.py:1035-1165 restricts function bodies to imports, pass, and simple return forms; nested call statements make a restricted callable unavailable. Therefore recursive decorator bodies are not executed by this restricted function subset.

# MODEL_OBSERVATIONS

**DIRECT_EVIDENCE**

- A2, B2, C2, D2, E2, and F2 all return UNKNOWN.
- Each of the six model traces contains a completed pkg.app FROM from pkg.decorators and no CALL_FUNCTION for the imported decorator.
- A2-C2 emit DEFINE_FUNCTION for the exported decorator. D2, E2, and F2 emit DEFINE_OPAQUE_FUNCTION for replace, relative_decorator, and read_marker respectively.
- Only the CPython B2 execution loads pkg.effect. The model emits no pkg.effect event in A2-D2.
- E2’s CPython run loads pkg.decorators.effect only. F2’s CPython result reads the pkg.decorators global. No MODEL_PASS is required or asserted for E2/F2.

# TARGETED_TEST_RESULTS

**DIRECT_EVIDENCE**

- Command: .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_package_model.py -rs
- Result: 238 passed in 24.13s; exit code 0.
- The first repository-wide diff check flagged the copied unified diff's blank context lines in walkthrough.md. The report now carries the complete zero-context unified diff instead; a direct comparison against git diff --unified=0 confirmed the block is complete and exact.
- git diff --check: exit code 0, no whitespace errors. Git printed its LF-to-CRLF working-copy advisory for the changed test file.
- No full pytest, SCC02, FULL, update_file, backend restart, semantic refresh, Git index change, commit, or push was run.

# MCP_POST_TASK_AUDIT

**DIRECT_EVIDENCE**

- Canonical LIVE revision advanced from 1370 at preflight to 1371 after the test edit.
- At revision 1371, get_module_context reported canonical_state=fresh and workspace_sync=verified for package_model.py, execution/calls.py, execution/state.py, execution/imports.py, and the changed test module. cycle_semantics remained stale, as it was at preflight; advisory_warning was null.
- get_source_range diagnostics summary: syntax errors 0 (fresh); structural DFS cycle count 16 (fresh). Contextor defines this cycle count as DFS back-edge paths deduplicated by rotation, not all simple cycles. The cycle family is stale; the separate source-diagnostics count is fresh.
- Lineage queries were served from LIVE revision 1371 with fresh lineage facts; their workspace_sync is unverified by design because that query path does not read/hash source files. The get_module_context source-sync results above provide the file synchronization evidence.

# FULL_DIFFS

Complete actual unified diff in zero-context form; all added and removed lines are included:

```diff
diff --git a/tests/test_cycle_semantics_cross_module_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
index 68b95ea..e0ba3ff 100644
--- a/tests/test_cycle_semantics_cross_module_decorator_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
@@ -40 +40 @@ def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
-    if name in {"pkg.decorators", "pkg.effect"}:
+    if name in {"pkg.decorators", "pkg.effect", "pkg.decorators.effect"}:
@@ -65,0 +66,4 @@ decorators = sys.modules.get("pkg.decorators")
+decorator = (
+    getattr(decorators, export_name, None)
+    if decorators is not None else None
+)
@@ -88,0 +93 @@ print(json.dumps({
+    "binding_repr": repr(value) if binding_present else None,
@@ -103,0 +109,9 @@ print(json.dumps({
+    "decorator_package": (
+        getattr(decorator, "__globals__", {}).get("__package__")
+        if decorator is not None else None
+    ),
+    "loaded_effect_modules": [
+        name
+        for name in ("pkg.decorators.effect", "pkg.effect")
+        if name in sys.modules
+    ],
@@ -179,0 +194,87 @@ def _case_sources(case):
+    elif case == "A2":
+        sources.update({
+            "pkg.decorators": (
+                "def identity(fn):\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "@identity\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        })
+    elif case == "B2":
+        sources.update({
+            "pkg.decorators": (
+                "def apply_decorator(fn):\n"
+                "    import pkg.effect\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import apply_decorator\n"
+                "@apply_decorator\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+            "pkg.effect": "pass\n",
+        })
+    elif case == "C2":
+        sources.update({
+            "pkg.decorators": (
+                "def identity(fn):\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import identity as alias\n"
+                "@alias\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        })
+    elif case == "D2":
+        sources.update({
+            "pkg.decorators": (
+                "def replace(fn):\n"
+                "    return None\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import replace\n"
+                "@replace\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        })
+    elif case == "E2":
+        sources.update({
+            "pkg.decorators.__init__": (
+                "def relative_decorator(fn):\n"
+                "    from . import effect\n"
+                "    return effect.ORIGIN\n"
+            ),
+            "pkg.decorators.effect": (
+                "ORIGIN = 'defining-package-effect'\n"
+            ),
+            "pkg.effect": "ORIGIN = 'caller-package-effect'\n",
+            "pkg.app": (
+                "from pkg.decorators import relative_decorator\n"
+                "@relative_decorator\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        })
+    elif case == "F2":
+        sources.update({
+            "pkg.decorators": (
+                "marker = 'decorators-global'\n"
+                "def read_marker(fn):\n"
+                "    return marker\n"
+            ),
+            "pkg.app": (
+                "marker = 'app-global'\n"
+                "from pkg.decorators import read_marker\n"
+                "@read_marker\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        })
@@ -306,0 +408,126 @@ def test_indexed_cross_module_decorator_reference_and_model_boundary(
+@pytest.mark.parametrize(
+    "case,export_name,decorator_binding_name,imported_symbol,expected_imports,expected_type,expected_callable,expected_result,expected_same_input",
+    [
+        pytest.param(
+            "A2", "identity", "identity", "identity",
+            ("pkg.decorators",), "builtins.function", True, None, True,
+            id="A2-supported-imported-identity",
+        ),
+        pytest.param(
+            "B2", "apply_decorator", "apply_decorator", "apply_decorator",
+            ("pkg.decorators", "pkg.effect"),
+            "builtins.function", True, None, True,
+            id="B2-supported-imported-effectful-decorator",
+        ),
+        pytest.param(
+            "C2", "identity", "alias", "identity",
+            ("pkg.decorators",), "builtins.function", True, None, True,
+            id="C2-supported-imported-alias",
+        ),
+        pytest.param(
+            "D2", "replace", "replace", "replace",
+            ("pkg.decorators",), "builtins.NoneType", False, None, False,
+            id="D2-supported-imported-returns-none",
+        ),
+    ],
+)
+def test_supported_body_imported_decorators_remain_unknown(
+    tmp_path,
+    case,
+    export_name,
+    decorator_binding_name,
+    imported_symbol,
+    expected_imports,
+    expected_type,
+    expected_callable,
+    expected_result,
+    expected_same_input,
+):
+    sources = _case_sources(case)
+    observed = _reference(
+        tmp_path,
+        sources,
+        export_name,
+        "f",
+        "function",
+        decorator_binding_name,
+    )
+
+    assert observed["error"] is None
+    assert tuple(observed["imports"]) == expected_imports
+    assert observed["binding_present"] is True
+    assert observed["binding_type"] == expected_type
+    assert observed["binding_callable"] is expected_callable
+    assert observed["body_result"] == expected_result
+    assert observed["decorator_calls_at_definition"] == 1
+    assert observed["decorator_seen_present"] is True
+    assert observed["binding_is_decorator_input"] is expected_same_input
+    assert observed["binding_is_imported_export"] is True
+
+    modeled = evaluate_package_import_order(
+        {name: ast.parse(source) for name, source in sources.items()},
+        "pkg.app",
+    )
+    assert modeled.outcome == "UNKNOWN"
+    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == imported_symbol
+        for event in modeled.events
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        for event in modeled.events
+    )
+    assert not any(
+        event.target == "pkg.effect"
+        for event in modeled.events
+    )
+
+
+def test_cpython_relative_decorator_import_uses_defining_package_context(
+    tmp_path,
+):
+    sources = _case_sources("E2")
+    observed = _reference(
+        tmp_path,
+        sources,
+        "relative_decorator",
+        "f",
+        "function",
+        "relative_decorator",
+    )
+
+    assert observed["error"] is None
+    assert observed["binding_present"] is True
+    assert observed["binding_type"] == "builtins.str"
+    assert observed["binding_repr"] == repr("defining-package-effect")
+    assert observed["decorator_package"] == "pkg.decorators"
+    assert observed["loaded_effect_modules"] == ["pkg.decorators.effect"]
+    assert observed["decorator_calls_at_definition"] == 1
+    assert observed["binding_is_imported_export"] is True
+
+
+def test_cpython_imported_decorator_reads_its_defining_module_global(
+    tmp_path,
+):
+    sources = _case_sources("F2")
+    observed = _reference(
+        tmp_path,
+        sources,
+        "read_marker",
+        "f",
+        "function",
+        "read_marker",
+    )
+
+    assert observed["error"] is None
+    assert observed["binding_present"] is True
+    assert observed["binding_type"] == "builtins.str"
+    assert observed["binding_repr"] == repr("decorators-global")
+    assert observed["decorator_calls_at_definition"] == 1
+    assert observed["binding_is_imported_export"] is True
+
+
```

# FINAL_VERDICT

PASS — P5-M08-I10-T2 test addition, targeted regression run, CPython reference checks, and read-only source discovery completed. This verdict does not claim cross-module decorator execution is implemented or supported by the model. The D2 opaque-helper observation is called out above; its CPython behavior, indexed FROM completion, UNKNOWN outcome, and absence of a modeled call match the requested test contract.
