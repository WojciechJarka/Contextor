# K09 — implementation

## FILES_CHANGED

tests/test_cycle_semantics_passive_classes.py

## K09_CASE_RESULTS
- K09-A: pkg.a EARLY_BINDING_HAZARD / CPython ImportError; pkg.b MODEL_PASS / CPython success.
- K09-B: pkg.a EARLY_BINDING_HAZARD / CPython ImportError; pkg.b MODEL_PASS / CPython success.
- K09-C: corrected independent pkg.c target; pkg.a EARLY_BINDING_HAZARD / CPython ImportError; pkg.b MISSING_EXPORT / CPython ImportError.
- K09-D: pkg.a EARLY_BINDING_HAZARD / CPython ImportError; pkg.b MISSING_EXPORT / CPython ImportError.
- K09-E: MISSING_EXPORT / CPython ImportError.
- K09-F: MODEL_PASS / CPython success.
- K09-G: all three unsupported forms UNKNOWN.
- K09-H: deterministic result and unchanged AST.

## MODEL_VS_CPYTHON
- DIRECT_EVIDENCE: each K09-A–F assertion ran the existing `_actual` helper, which starts isolated CPython subprocesses, and all assertions passed.
- CODE_PATH_PROVED: class-local imports and bindings are recorded separately from module exports; deferred method body import was not started.
- CONTRACT_PROVED: bounded requested synthetic cases only, via focused tests and CPython subprocess outcomes.
- INFERENCE: none used to claim broader Python import safety.
- UNKNOWN: broader class metaclass, descriptor, and dynamic behavior outside bounded model.

## TARGETED_TEST_RESULTS
- Backend process identity (PID 14072) command line and executable identified C:\Temp\Contextor_Repo\.venv\Scripts\python.exe.
- `-m pytest -q tests/test_cycle_semantics_passive_classes.py`: 101 passed in 17.60s.
- First `git diff --check` found blank lines at EOF in the target and report. Both were corrected. Final `git diff --check` exited 0.

## MCP_POST_CHANGE_AUDIT
- Pre-edit canonical revision 1258; watcher UPDATED event 1259 and UNCHANGED event 1260, continuous journal.
- Canonical revision 1260; target workspace_sync=verified.
- Syntax errors: 0 fresh. Structural DFS cycle paths: 16 fresh. Active warnings: 16 fresh.
- cycle_semantics=stale; runtime execution status UNKNOWN_NOT_EVALUATED.
- Current canonical state_id: unavailable from queried public overlays. Historical expected state_id 20261108_172727 belongs to publication revision 1128 and is not asserted for revision 1260.
- Current graph fingerprint: unavailable from queried public overlays; graph family fresh is not substituted for fingerprint.

## FULL_DIFFS
```diff
diff --git a/tests/test_cycle_semantics_passive_classes.py b/tests/test_cycle_semantics_passive_classes.py
index c59c20e..3d5dfda 100644
--- a/tests/test_cycle_semantics_passive_classes.py
+++ b/tests/test_cycle_semantics_passive_classes.py
@@ -1054,3 +1054,274 @@ def test_p3_d3_import_after_class_binding(tmp_path):
         "assert m.Seen is m.C;assert type(m.C) is m.Meta",
     )
     assert actual.returncode == 0, actual.stderr
+
+
+@pytest.mark.parametrize(
+    "entry,expected",
+    [
+        ("pkg.a", "EARLY_BINDING_HAZARD"),
+        ("pkg.b", "MODEL_PASS"),
+    ],
+)
+def test_k09_a_class_name_bound_after_body(tmp_path, entry, expected):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class C:\n    import pkg.b",
+        "pkg.b": "from pkg.a import C",
+    }
+
+    result = _model(sources, entry)
+    actual = _actual(tmp_path, sources, entry)
+
+    assert result.outcome == expected
+
+    if expected == "EARLY_BINDING_HAZARD":
+        assert (result.target_module, result.symbol) == ("pkg.a", "C")
+        assert actual.returncode != 0
+        assert "ImportError" in actual.stderr
+        assert not any(
+            e.operation == "DEFINE_PASSIVE_CLASS"
+            and e.module == "pkg.a"
+            and e.symbol == "C"
+            for e in result.events
+        )
+    else:
+        assert actual.returncode == 0, actual.stderr
+        operations = [
+            e.operation for e in result.events
+            if e.module == "pkg.a"
+        ]
+        assert operations.index("CLASS_LOCAL_IMPORT") < (
+            operations.index("DEFINE_PASSIVE_CLASS")
+        )
+
+
+@pytest.mark.parametrize(
+    "entry,expected",
+    [
+        ("pkg.a", "EARLY_BINDING_HAZARD"),
+        ("pkg.b", "MODEL_PASS"),
+    ],
+)
+def test_k09_b_module_binding_after_class(tmp_path, entry, expected):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    import pkg.b\n"
+            "value = 1"
+        ),
+        "pkg.b": "from pkg.a import value",
+    }
+
+    result = _model(sources, entry)
+    actual = _actual(tmp_path, sources, entry)
+
+    assert result.outcome == expected
+
+    if expected == "EARLY_BINDING_HAZARD":
+        assert (result.target_module, result.symbol) == (
+            "pkg.a", "value"
+        )
+        assert actual.returncode != 0
+        assert "ImportError" in actual.stderr
+    else:
+        assert actual.returncode == 0, actual.stderr
+        assert any(
+            e.operation == "CLASS_LOCAL_IMPORT"
+            and e.target == "pkg.b"
+            for e in result.events
+        )
+
+
+@pytest.mark.parametrize(
+    "entry,expected",
+    [
+        ("pkg.a", "EARLY_BINDING_HAZARD"),
+        ("pkg.b", "MISSING_EXPORT"),
+    ],
+)
+def test_k09_c_class_local_alias_does_not_escape(
+    tmp_path, entry, expected
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    import pkg.c as inside\n"
+            "    import pkg.b"
+        ),
+        "pkg.b": "from pkg.a import inside",
+        "pkg.c": "pass",
+    }
+
+    result = _model(sources, entry)
+    actual = _actual(tmp_path, sources, entry)
+
+    assert result.outcome == expected
+    assert (result.target_module, result.symbol) == (
+        "pkg.a", "inside"
+    )
+    assert actual.returncode != 0
+    assert "ImportError" in actual.stderr
+
+    assert not any(
+        e.module == "pkg.a"
+        and e.operation in {"BIND", "ALIAS"}
+        and e.symbol == "inside"
+        for e in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "entry,expected",
+    [
+        ("pkg.a", "EARLY_BINDING_HAZARD"),
+        ("pkg.b", "MISSING_EXPORT"),
+    ],
+)
+def test_k09_d_class_local_assignment_does_not_escape(
+    tmp_path, entry, expected
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    local = 1\n"
+            "    import pkg.b"
+        ),
+        "pkg.b": "from pkg.a import local",
+    }
+
+    result = _model(sources, entry)
+    actual = _actual(tmp_path, sources, entry)
+
+    assert result.outcome == expected
+    assert (result.target_module, result.symbol) == (
+        "pkg.a", "local"
+    )
+    assert actual.returncode != 0
+    assert "ImportError" in actual.stderr
+
+    assert any(
+        e.module == "pkg.a"
+        and e.operation == "CLASS_LOCAL_BIND"
+        and e.symbol == "local"
+        for e in result.events
+    )
+    assert not any(
+        e.module == "pkg.a"
+        and e.operation == "BIND"
+        and e.symbol == "local"
+        for e in result.events
+    )
+
+
+def test_k09_e_class_local_from_is_not_module_export(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class C:\n    from pkg.b import token",
+        "pkg.b": "token = 1",
+        "pkg.c": "from pkg.a import token",
+    }
+
+    result = _model(sources, "pkg.c")
+    actual = _actual(tmp_path, sources, "pkg.c")
+
+    assert result.outcome == "MISSING_EXPORT"
+    assert (result.target_module, result.symbol) == (
+        "pkg.a", "token"
+    )
+    assert actual.returncode != 0
+    assert "ImportError" in actual.stderr
+
+    events = result.events
+    class_from = next(
+        i for i, e in enumerate(events)
+        if e.module == "pkg.a"
+        and e.operation == "CLASS_LOCAL_FROM"
+        and e.target == "pkg.b"
+        and e.symbol == "token"
+    )
+    missing = next(
+        i for i, e in enumerate(events)
+        if e.operation == "MISSING_EXPORT"
+        and e.target == "pkg.a"
+        and e.symbol == "token"
+    )
+    assert class_from < missing
+
+
+def test_k09_f_method_body_import_is_deferred(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            "    def later(self):\n"
+            "        import pkg.b\n"
+            "value = 1"
+        ),
+        "pkg.b": "from pkg.a import value",
+    }
+
+    result = _model(sources, "pkg.a")
+    actual = _actual(tmp_path, sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+    assert actual.returncode == 0, actual.stderr
+
+    assert not any(
+        e.operation == "START_IMPORT"
+        and e.target == "pkg.b"
+        for e in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "body",
+    [
+        'class C:\n    exec("import pkg.b")',
+        "class C(factory()):\n    import pkg.b",
+        "@decorator\nclass C:\n    import pkg.b",
+    ],
+)
+def test_k09_g_unmodeled_class_effects_fail_closed(body):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": body,
+        "pkg.b": "pass",
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.outcome != "MODEL_PASS"
+
+
+def test_k09_h_deterministic_without_ast_mutation():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse(
+            "class C:\n"
+            "    import pkg.b"
+        ),
+        "pkg.b": ast.parse("from pkg.a import C"),
+    }
+
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+    first = evaluate_package_import_order(sources, "pkg.a")
+    second = evaluate_package_import_order(sources, "pkg.a")
+
+    assert first == second
+    assert first.events == second.events
+    assert first.outcome == "EARLY_BINDING_HAZARD"
+
+    after = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+    assert after == before
```

## FINAL_VERDICT
Focused K09 tests passed. MCP source freshness verified at revision 1260. FINAL_PASS withheld because current state_id and graph fingerprint were not obtained and cycle_semantics remains stale.
