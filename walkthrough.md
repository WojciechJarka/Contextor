# P5-M08-I8-I1 — named decorator identity snapshot

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first reported canonical LIVE revision 1335, `package_model.py` source fresh and `workspace_sync=verified`, cycle semantics stale. Initial HEAD `db1dd71b7bc3c0edcd8d21816ad84b380ad39e6d`; initial `git status --short` clean. Backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. New test target did not exist.
- DIRECT_EVIDENCE: `_RestrictedFunction` remains `@dataclass(frozen=True, eq=False)` at `execution/calls.py:8-12`; `_execute_restricted_call` resolves current module binding at `:27-52`. I7 parameter binding guard exists at `package_model.py:1072-1091`; single-name decorator branch at `:2028-2083`; multiple decorators remain rejected by validator at `:160-180`. I8-T1 and R1 tests are present.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/calls.py`
- `tests/test_cycle_semantics_decorator_snapshots.py` (new)
- `walkthrough.md` (this report)

## SNAPSHOT_REPRESENTATION

- DIRECT_EVIDENCE: `_DecoratorSnapshot` is frozen and identity-comparing (`eq=False`), with immutable tuples of names and values (`execution/calls.py:15-18`). `_snapshot_named_decorators` resolves each name from the provided namespace in source order and returns a tuple-backed snapshot (`:21-47`). It returns `None` for an empty stack, invalid name or absent binding.

## OBJECT_IDENTITY_CONTRACT

- CODE_PATH_PROVED: The helper appends the exact object from `namespace[name]`; it does not copy, invoke or mutate the value (`execution/calls.py:29-47`). Direct tests show identity retained after rebinding and unchanged namespace after construction (`tests/test_cycle_semantics_decorator_snapshots.py:27-45,92-106`). This is a helper contract, not stacked-decorator execution support.

## DUPLICATE_DECORATOR_CONTRACT

- DIRECT_EVIDENCE: Repeated name entries produce repeated references to the same object (`tests/test_cycle_semantics_decorator_snapshots.py:48-60`). The helper does not deduplicate (`execution/calls.py:29-42`).

## NONCALLABLE_AND_MISSING_NAME_CONTRACTS

- DIRECT_EVIDENCE: A name bound to `None` yields a snapshot containing `None`; a missing name yields no snapshot (`tests/test_cycle_semantics_decorator_snapshots.py:63-81`). Callable eligibility is not checked in the helper (`execution/calls.py:21-47`). Invalid identifiers and an empty tuple are rejected (`tests/test_cycle_semantics_decorator_snapshots.py:84-89`).

## UNCHANGED_EXECUTION_BOUNDARIES

- CODE_PATH_PROVED: `_execute_restricted_call` below the inserted helper is unchanged, and `package_model.py`, `_compile`, `_Step`, `_FunctionFrame` and decorator execution branches have no task diff. The stacked-decorator regression remains UNKNOWN (`tests/test_cycle_semantics_stacked_decorator_identity.py:178-186`). No new MODEL_PASS case is admitted by this helper alone.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested seven-file focused subset completed **66 passed**, exit 0, 16.80 s. `git diff --check` exited 0; Git printed a line-ending notice only. No full suite or SCC02 was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: `execution.calls` was fresh and `workspace_sync=verified` at LIVE revision 1336; new test was fresh and verified at revision **1337**. Syntax errors 0, structural DFS back-edge cycle count 16. `execution.calls` still has only one hard outbound dependency, `execution.steps`; new test depends on `execution.calls`. `cycle_semantics=stale`; source freshness is not loaded-code adoption or a fresh semantic verdict.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/calls.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index e9c5728..840c919 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -12,6 +12,38 @@ class _RestrictedFunction:
     parameters: tuple[str, ...] = ()


+@dataclass(frozen=True, eq=False)
+class _DecoratorSnapshot:
+    names: tuple[str, ...]
+    values: tuple[object, ...]
+
+
+def _snapshot_named_decorators(
+    names: tuple[str, ...],
+    namespace: dict[str, object | None],
+) -> _DecoratorSnapshot | None:
+    if not names:
+        return None
+
+    values: list[object] = []
+
+    for name in names:
+        if (
+            not name
+            or not name.isidentifier()
+            or name.startswith("__")
+            or name not in namespace
+        ):
+            return None
+
+        values.append(namespace[name])
+
+    return _DecoratorSnapshot(
+        names=names,
+        values=tuple(values),
+    )
+
+
 def _new_restricted_function(
     defining_module: str,
     body: tuple[_Step, ...],
```

### tests/test_cycle_semantics_decorator_snapshots.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_snapshots.py b/tests/test_cycle_semantics_decorator_snapshots.py
new file mode 100644
index 0000000..c3a3aa9
--- /dev/null
+++ b/tests/test_cycle_semantics_decorator_snapshots.py
@@ -0,0 +1,106 @@
+from contextor.core.cycle_semantics.execution.calls import (
+    _DecoratorSnapshot,
+    _new_restricted_function,
+    _snapshot_named_decorators,
+)
+
+
+def test_snapshot_preserves_source_order_and_identity():
+    upper = _new_restricted_function("pkg", ())
+    lower = _new_restricted_function("pkg", ())
+
+    namespace = {
+        "upper": upper,
+        "lower": lower,
+    }
+
+    snapshot = _snapshot_named_decorators(
+        ("upper", "lower"),
+        namespace,
+    )
+
+    assert isinstance(snapshot, _DecoratorSnapshot)
+    assert snapshot.names == ("upper", "lower")
+    assert snapshot.values[0] is upper
+    assert snapshot.values[1] is lower
+
+
+def test_rebinding_after_snapshot_preserves_objects():
+    upper = _new_restricted_function("pkg", ())
+    lower = _new_restricted_function("pkg", ())
+    namespace = {"upper": upper, "lower": lower}
+
+    snapshot = _snapshot_named_decorators(
+        ("upper", "lower"),
+        namespace,
+    )
+
+    namespace["upper"] = None
+    namespace["lower"] = None
+
+    assert snapshot.values[0] is upper
+    assert snapshot.values[1] is lower
+
+
+def test_repeated_name_preserves_duplicate_identity():
+    decorator = _new_restricted_function("pkg", ())
+    namespace = {"deco": decorator}
+
+    snapshot = _snapshot_named_decorators(
+        ("deco", "deco"),
+        namespace,
+    )
+
+    assert snapshot.names == ("deco", "deco")
+    assert snapshot.values[0] is decorator
+    assert snapshot.values[1] is decorator
+
+
+def test_none_binding_is_snapshot_value():
+    snapshot = _snapshot_named_decorators(
+        ("deco",),
+        {"deco": None},
+    )
+
+    assert snapshot is not None
+    assert snapshot.values == (None,)
+
+
+def test_missing_name_rejects_entire_snapshot():
+    decorator = _new_restricted_function("pkg", ())
+
+    assert _snapshot_named_decorators(
+        ("upper", "missing"),
+        {"upper": decorator},
+    ) is None
+
+
+def test_invalid_names_and_empty_stack_rejected():
+    decorator = _new_restricted_function("pkg", ())
+    namespace = {"deco": decorator}
+
+    for names in (
+        (),
+        ("",),
+        ("__hidden",),
+        ("not-valid",),
+    ):
+        assert _snapshot_named_decorators(
+            names,
+            namespace,
+        ) is None
+
+
+def test_snapshot_does_not_modify_namespace():
+    decorator = _new_restricted_function("pkg", ())
+    namespace = {"deco": decorator}
+    before = dict(namespace)
+
+    snapshot = _snapshot_named_decorators(
+        ("deco",),
+        namespace,
+    )
+
+    assert snapshot is not None
+    assert namespace == before
+    assert namespace["deco"] is decorator
```

## FINAL_VERDICT

CONTRACT_PROVED for the snapshot helper's bounded ordering and identity behavior. Focused regressions passed, while stacked execution and current UNKNOWN boundaries remain unchanged. STOP after this stage.
