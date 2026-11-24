PREFLIGHT

DIRECT_EVIDENCE:
- The request was read from the supplied attachment. Before changes, HEAD was f1b287209a0d2ce668112e0111a30206e6a53189 on main and the working tree was clean.
- MCP preflight LIVE/canonical revision was 1571. The live event stream was continuous with no resync required. Project metadata reported canonical_state=fresh and global workspace_sync=unverified; cycle_semantics was stale.
- File-specific MCP contexts for both requested files at revision 1571 reported canonical_state=fresh, workspace_sync=verified, provenance=live, and syntax_diagnostics=checked_and_none with zero errors.
- Contextor confirmed the flat helpers in tests/test_cycle_semantics_initialization_model.py:14-33. _assess parses each source then calls evaluate_flat_import_order. _actual writes to tmp_path / (name + ".py") directly and does not create tmp_path.
- Contextor confirmed the package helpers in tests/test_cycle_semantics_package_model.py:1375-1421. _model parses each source then calls evaluate_package_import_order. _actual creates each file's parent directory before writing.
- The supplied flat G4 and G5 tests pass tmp_path / label or tmp_path / str(index) to the flat _actual helper. Those child directories do not yet exist. To honor that helper's actual precondition without changing helpers, imports, evaluators, fixtures, or production, the two flat tests create their local case_dir before calling _actual.
- New test locations from MCP source search: flat G4 lines 170-227, flat G5 lines 230-287, package G4 lines 3659-3722, package G5 lines 3725-3788.

INFERENCE:
- The directory creation is setup needed by the existing helper; it does not alter either metamorphic relation or its assertions.

G4_FLAT_RENAMING

DIRECT_EVIDENCE:
- Added test at tests/test_cycle_semantics_initialization_model.py:170-227.
- The original and bijectively renamed flat import cycles both produce EARLY_BINDING_HAZARD, and the test compares target module, symbol, and event tuples after renaming.
- The test then executes both source sets through _actual(return_process=True) and checks nonzero return code plus AttributeError naming the partially initialized module and missing attribute.
- This test passed in the targeted run.

G4_PACKAGE_RENAMING

DIRECT_EVIDENCE:
- Added test at tests/test_cycle_semantics_package_model.py:3659-3722.
- Both model results are EARLY_BINDING_HAZARD; target module and target symbol assertions passed for pkg/value and tree/payload.
- The exact event-trace equality assertion failed before the test's own _actual calls could run.

BLOCKED:
- Failing assertion: tests/test_cycle_semantics_package_model.py:3690, the equality between the renamed original event tuples and the renamed-source event tuples.
- First divergent event is index 2 (zero-based). The left tuple is ('tree.branch', 'IMPORT', 'tree', 'pkg'); the right tuple is ('tree.branch', 'IMPORT', 'tree', 'tree').
- The model's IMPORT event stores the imported module name in event.symbol. The provided mapping applies module_names to event.module/event.target, but applies only symbol_names to event.symbol. Thus pkg in the original IMPORT event remains pkg while the corresponding renamed event contains tree.
- This identifies a mismatch in the supplied trace-normalization assertion. It is not evidence that the two model outcomes, hazard target, or CPython outcomes differ. No assertion was changed after the failure.

G5_FLAT_PERMUTATION

DIRECT_EVIDENCE:
- Added test at tests/test_cycle_semantics_initialization_model.py:230-287.
- Both permutations passed: the model's START_IMPORT targets match each supplied order, and the isolated CPython process confirms [11, 22] and the matching sys.modules insertion order.
- This test passed in the targeted run.

G5_PACKAGE_PERMUTATION

DIRECT_EVIDENCE:
- Added test at tests/test_cycle_semantics_package_model.py:3725-3788.
- Both child-import permutations passed: model START_IMPORT child targets match the supplied order, and CPython confirms values [11, 22] and corresponding sys.modules insertion order.
- This test passed in the targeted run.

CPYTHON_PARITY

DIRECT_EVIDENCE:
- The passing G4 flat test ran both source variants through CPython and confirmed AttributeError for the partially initialized modules a/value and alpha/token.
- The G5 flat and package tests ran isolated CPython subprocesses and checked values plus module insertion order, not only return codes.
- Because the G4 package trace assertion fails before its test-local runtime calls, a separate diagnostic reproduction used the same package helper and identical original/renamed source dictionaries. Both CPython subprocesses returned code 1.
- Original CPython exception: AttributeError: partially initialized module 'pkg' from '...\\original\\pkg\\__init__.py' has no attribute 'value' (most likely due to a circular import).
- Renamed CPython exception: AttributeError: partially initialized module 'tree' from '...\\renamed\\tree\\__init__.py' has no attribute 'payload' (most likely due to a circular import).
- Both runtime exceptions match the corresponding model hazard and renamed target symbol. The first divergence in this test is the model event comparison described above, before its runtime assertions.

DIRECT_EVIDENCE — MODEL OUTPUTS FROM THE DIAGNOSTIC REPRODUCTION:

Original:
- outcome=EARLY_BINDING_HAZARD, target_module=pkg, symbol=value
- events, in order:
  1. (module='\u0000ENTRY', operation=START_IMPORT, target=pkg, symbol=None)
  2. (module=pkg, operation=START_IMPORT, target=pkg.child, symbol=None)
  3. (module=pkg.child, operation=IMPORT, target=pkg, symbol=pkg)
  4. (module=pkg.child, operation=EARLY_BINDING_HAZARD, target=pkg, symbol=value)

Renamed:
- outcome=EARLY_BINDING_HAZARD, target_module=tree, symbol=payload
- events, in order:
  1. (module='\u0000ENTRY', operation=START_IMPORT, target=tree, symbol=None)
  2. (module=tree, operation=START_IMPORT, target=tree.branch, symbol=None)
  3. (module=tree.branch, operation=IMPORT, target=tree, symbol=tree)
  4. (module=tree.branch, operation=EARLY_BINDING_HAZARD, target=tree, symbol=payload)

INFERENCE:
- The module-name bijection applies to event.symbol for this IMPORT event because that field contains the imported module name in these outputs. The supplied assertion maps that field only through the attribute-symbol mapping, causing the observed false test mismatch. This is an inference from the source event dictionaries and the failing tuple.

TARGETED_TESTS

DIRECT_EVIDENCE:
- Command: .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_package_model.py -k "consistent_renaming_preserves_flat_hazard_and_trace or consistent_renaming_preserves_package_hazard_and_trace or independent_flat_import_permutation or independent_package_import_permutation"
- Result: 3 passed, 1 failed, 284 deselected in 5.28s; exit code 1.
- The failing test was test_consistent_renaming_preserves_package_hazard_and_trace at tests/test_cycle_semantics_package_model.py:3690.
- Per the failure instruction, the two full test files were not run. No further tests were run after the failure.
- git diff --check on the two test files reported no whitespace errors; Git emitted a working-copy LF-to-CRLF notice for the initialization test file.

FULL_TARGETED_TRACEBACK:

~~~~text
..F.                                                                     [100%]
================================== FAILURES ===================================
_________ test_consistent_renaming_preserves_package_hazard_and_trace _________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1397/test_consistent_renaming_prese1')

    def test_consistent_renaming_preserves_package_hazard_and_trace(tmp_path):
        original = {
            "pkg.__init__": "import pkg.child\nvalue=1\n",
            "pkg.child": "import pkg\nseen=pkg.value\n",
        }
        renamed = {
            "tree.__init__": "import tree.branch\npayload=1\n",
            "tree.branch": "import tree\nreadback=tree.payload\n",
        }

        first = _model(original, "pkg")
        second = _model(renamed, "tree")

        assert first.outcome == second.outcome == "EARLY_BINDING_HAZARD"

        module_names = {
            "pkg": "tree",
            "pkg.__init__": "tree.__init__",
            "pkg.child": "tree.branch",
        }
        symbol_names = {
            "value": "payload",
            "child": "branch",
            "seen": "readback",
        }

        assert (
            module_names[first.target_module],
            symbol_names[first.symbol],
        ) == (second.target_module, second.symbol)

>       assert [
            (
                module_names.get(event.module, event.module),
                event.operation,
                module_names.get(event.target, event.target),
                symbol_names.get(event.symbol, event.symbol),
            )
            for event in first.events
        ] == [
            (
                event.module,
                event.operation,
                event.target,
                event.symbol,
            )
            for event in second.events
        ]
E       AssertionError: assert [('\x00ENTRY'...', 'payload')] == [('\x00ENTRY'...', 'payload')]
E         
E         At index 2 diff: ('tree.branch', 'IMPORT', 'tree', 'pkg') != ('tree.branch', 'IMPORT', 'tree', 'tree')
E         Use -v to get more diff

tests\test_cycle_semantics_package_model.py:3690: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cycle_semantics_package_model.py::test_consistent_renaming_preserves_package_hazard_and_trace
1 failed, 3 passed, 284 deselected in 5.28s
~~~~

MCP_POST_CHANGE

DIRECT_EVIDENCE:
- Desktop watcher reported update_file / UPDATED for tests/test_cycle_semantics_initialization_model.py at LIVE revision 1572 and tests/test_cycle_semantics_package_model.py at LIVE revision 1573.
- Event continuity was continuous and resync_required=false. Latest LIVE/canonical revision at the audit was 1573.
- File-specific MCP contexts at revision 1573 report canonical_state=fresh, workspace_sync=verified, provenance=live for both changed files. AST/syntax diagnostics were checked_and_none with zero errors.
- Project metadata reports canonical_state=fresh at revision 1573 but global workspace_sync=unverified. cycle_semantics remains stale. These global/family states are not represented as file-level freshness.
- No MCP update_file call was used.

FULL_DIFFS

FILES_CHANGED:
- tests/test_cycle_semantics_initialization_model.py
- tests/test_cycle_semantics_package_model.py

Complete actual git diffs for the changed test files follow. walkthrough.md is the required report and is excluded from FILES_CHANGED under the repository reporting rule.

~~~~diff
diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
index 00d104f..792207d 100644
--- a/tests/test_cycle_semantics_initialization_model.py
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -167,6 +167,126 @@ def test_nested_attribute_first_segment_hazard(tmp_path):
     assert "has no attribute 'value'" in exception_line
 
 
+def test_consistent_renaming_preserves_flat_hazard_and_trace(tmp_path):
+    original = {
+        "a": "import b\nvalue=1\n",
+        "b": "import a\nobserved=a.value\n",
+    }
+    renamed = {
+        "alpha": "import omega\ntoken=1\n",
+        "omega": "import alpha\nreadback=alpha.token\n",
+    }
+
+    first = _assess(original, "a")
+    second = _assess(renamed, "alpha")
+
+    assert first.outcome == second.outcome == "EARLY_BINDING_HAZARD"
+
+    module_names = {"a": "alpha", "b": "omega"}
+    symbol_names = {"value": "token", "observed": "readback"}
+
+    assert (
+        module_names[first.target_module],
+        symbol_names[first.symbol],
+    ) == (second.target_module, second.symbol)
+
+    def renamed_event(event):
+        return (
+            module_names.get(event.module, event.module),
+            event.operation,
+            module_names.get(event.target, event.target),
+            symbol_names.get(event.symbol, event.symbol),
+        )
+
+    assert [renamed_event(event) for event in first.events] == [
+        (
+            event.module,
+            event.operation,
+            event.target,
+            event.symbol,
+        )
+        for event in second.events
+    ]
+
+    for label, sources, entry, module, symbol in (
+        ("original", original, "a", "a", "value"),
+        ("renamed", renamed, "alpha", "alpha", "token"),
+    ):
+        case_dir = tmp_path / label
+        case_dir.mkdir()
+        process = _actual(
+            case_dir,
+            sources,
+            entry,
+            return_process=True,
+        )
+        assert process.returncode != 0
+        exception = process.stderr.strip().splitlines()[-1]
+        assert exception.startswith("AttributeError:")
+        assert f"partially initialized module '{module}'" in exception
+        assert f"has no attribute '{symbol}'" in exception
+
+
+def test_independent_flat_import_permutation(tmp_path):
+    modules = {
+        "unit_left": "value=11\n",
+        "unit_right": "value=22\n",
+    }
+
+    orders = (
+        ("unit_left", "unit_right"),
+        ("unit_right", "unit_left"),
+    )
+
+    for index, order in enumerate(orders):
+        entry = (
+            f"import {order[0]}\n"
+            f"import {order[1]}\n"
+            "left_value=unit_left.value\n"
+            "right_value=unit_right.value\n"
+        )
+
+        sources = {**modules, "entry": entry}
+        result = _assess(sources, "entry")
+
+        assert result.outcome == "MODEL_PASS"
+        assert [
+            event.target
+            for event in result.events
+            if event.operation == "START_IMPORT"
+        ] == list(order)
+
+        case_dir = tmp_path / str(index)
+        case_dir.mkdir()
+        assert _actual(case_dir, sources, "entry")
+
+        runtime = subprocess.run(
+            [
+                sys.executable, "-I", "-B", "-c",
+                (
+                    "import importlib,json,sys;"
+                    "sys.path.insert(0,sys.argv[1]);"
+                    "entry=importlib.import_module('entry');"
+                    "print(json.dumps({"
+                    "'values':[entry.left_value,entry.right_value],"
+                    "'order':[name for name in sys.modules "
+                    "if name in ('unit_left','unit_right')]"
+                    "}))"
+                ),
+                str(case_dir),
+            ],
+            capture_output=True,
+            text=True,
+            timeout=10,
+            check=False,
+        )
+
+        assert runtime.returncode == 0, runtime.stderr
+        observed = json.loads(runtime.stdout)
+        assert observed["values"] == [11, 22]
+        assert observed["order"] == list(order)
+
+
 def test_nested_attribute_known_first_segment_stops_unknown():
     sources = {
         "alpha": "import beta\nx=beta.value.next",
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index d01ccbc..cdb1ad3 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -3654,3 +3654,135 @@ def test_single_attribute_event_contract_after_nested_support(tmp_path):
         ("route", "value"),
     ]
     assert _actual(tmp_path, source, "entry")
+
+
+def test_consistent_renaming_preserves_package_hazard_and_trace(tmp_path):
+    original = {
+        "pkg.__init__": "import pkg.child\nvalue=1\n",
+        "pkg.child": "import pkg\nseen=pkg.value\n",
+    }
+    renamed = {
+        "tree.__init__": "import tree.branch\npayload=1\n",
+        "tree.branch": "import tree\nreadback=tree.payload\n",
+    }
+
+    first = _model(original, "pkg")
+    second = _model(renamed, "tree")
+
+    assert first.outcome == second.outcome == "EARLY_BINDING_HAZARD"
+
+    module_names = {
+        "pkg": "tree",
+        "pkg.__init__": "tree.__init__",
+        "pkg.child": "tree.branch",
+    }
+    symbol_names = {
+        "value": "payload",
+        "child": "branch",
+        "seen": "readback",
+    }
+
+    assert (
+        module_names[first.target_module],
+        symbol_names[first.symbol],
+    ) == (second.target_module, second.symbol)
+
+    assert [
+        (
+            module_names.get(event.module, event.module),
+            event.operation,
+            module_names.get(event.target, event.target),
+            symbol_names.get(event.symbol, event.symbol),
+        )
+        for event in first.events
+    ] == [
+        (
+            event.module,
+            event.operation,
+            event.target,
+            event.symbol,
+        )
+        for event in second.events
+    ]
+
+    for label, sources, entry, module, symbol in (
+        ("original", original, "pkg", "pkg", "value"),
+        ("renamed", renamed, "tree", "tree", "payload"),
+    ):
+        process = _actual(
+            tmp_path / label,
+            sources,
+            entry,
+            return_process=True,
+        )
+        assert process.returncode != 0
+        exception = process.stderr.strip().splitlines()[-1]
+        assert exception.startswith("AttributeError:")
+        assert f"partially initialized module '{module}'" in exception
+        assert f"has no attribute '{symbol}'" in exception
+
+
+def test_independent_package_import_permutation(tmp_path):
+    modules = {
+        "pkg.__init__": "pass",
+        "pkg.left": "value=11",
+        "pkg.right": "value=22",
+    }
+
+    orders = (
+        ("pkg.left", "pkg.right"),
+        ("pkg.right", "pkg.left"),
+    )
+
+    for index, order in enumerate(orders):
+        source = {
+            **modules,
+            "entry": (
+                f"import {order[0]} as first\n"
+                f"import {order[1]} as second\n"
+                "import pkg.left as left\n"
+                "import pkg.right as right\n"
+                "left_value=left.value\n"
+                "right_value=right.value\n"
+            ),
+        }
+
+        result = _model(source, "entry")
+        assert result.outcome == "MODEL_PASS"
+
+        started_children = [
+            event.target
+            for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target in {"pkg.left", "pkg.right"}
+        ]
+        assert started_children == list(order)
+
+        case_dir = tmp_path / str(index)
+        assert _actual(case_dir, source, "entry")
+
+        runtime = subprocess.run(
+            [
+                sys.executable, "-I", "-B", "-c",
+                (
+                    "import importlib,json,sys;"
+                    "sys.path.insert(0,sys.argv[1]);"
+                    "entry=importlib.import_module('entry');"
+                    "print(json.dumps({"
+                    "'values':[entry.left_value,entry.right_value],"
+                    "'order':[name for name in sys.modules "
+                    "if name in ('pkg.left','pkg.right')]"
+                    "}))"
+                ),
+                str(case_dir),
+            ],
+            capture_output=True,
+            text=True,
+            timeout=8,
+            check=False,
+        )
+
+        assert runtime.returncode == 0, runtime.stderr
+        observed = json.loads(runtime.stdout)
+        assert observed["values"] == [11, 22]
+        assert observed["order"] == list(order)
~~~~

FINAL_STATUS

BLOCKED: the targeted G4 package trace assertion failed. The model outcomes and independent CPython hazard outcomes agree; the first discrepancy is the event tuple normalization at the IMPORT event described above. The assertion, helper, fixture, and production code were not changed to force a pass. The requested two-file test run remains unperformed because the focused run failed.

