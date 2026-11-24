PREFLIGHT

DIRECT_EVIDENCE:
- Attachment P16-I2 specified G1 in tests/test_cycle_semantics_namespace_pep420_contract.py and G3 in tests/test_cycle_semantics_package_model.py. AGENTS.md requires the report to be overwritten in walkthrough.md.
- Before editing: HEAD 432e0fd8f71e3fe096b932b8715b9b81242b3102, branch main, working tree clean. MCP canonical revision 1569. Both target files had file-level canonical_state=fresh and workspace_sync=verified at that revision; cycle_semantics family was stale.
- Exact anchors were present: test_t03_namespace_with_two_portions in the namespace test file and test_nested_attribute_alias_and_overwrite in the package model test file. Existing _write and _run helpers were available for G1; _model and _actual were available for G3.
- Repository interpreter used by the requested commands was Python 3.15.2.

INFERENCE:
- The G1 and G3 insertion anchors matched the requested preflight, so the change proceeded without adapting the requested contracts.

G1_EXACT_CONTRACT

DIRECT_EVIDENCE:
- Added test: tests/test_cycle_semantics_namespace_pep420_contract.py:127-184, immediately after test_t03_namespace_with_two_portions.
- Added imports at lines 7-10: SearchPortion and resolve_namespace_path from contextor.core.cycle_semantics.namespace_path_model.
- For the same namespace child in two search roots, the test runs both root orders. For each order, it asserts the resolver's conditional module-file resolution and selected source, then launches CPython through the existing _run helper and checks the loaded child's value, __file__ origin, and full nsp.__path__ portion order.
- _run starts a distinct process via sys.executable -I -B -c, prepends the supplied roots to sys.path, captures output, and returns the CompletedProcess. The test parses the actual JSON output.

CONTRACT_PROVED:
- CPython's selected module and namespace search path follow the supplied search-root order for this collision case: first/second yields FIRST from the first root; second/first yields SECOND from the second root.
- Each CPython execution checks the value, exact origin path, and portions. The resolver assertions are model assertions and do not independently establish CPython behavior.

UNKNOWN:
- This sample does not establish behavior for custom import finders, concurrent filesystem changes, or nonstandard path hooks.

G3_EXACT_CONTRACT

DIRECT_EVIDENCE:
- Added test: tests/test_cycle_semantics_package_model.py:3553-3646, immediately after test_nested_attribute_alias_and_overwrite.
- Positive source imports pkg.sub as subject, shadows subject with integer 3, imports pkg.sub again, then reads subject.value. The model must return MODEL_PASS and record one entry -> pkg.sub ATTR(value) event.
- The independent CPython process must complete and emit value 7, a module-valued subject, and subject identity equal to sys.modules['pkg.sub'].
- The paired negative source omits the re-import after shadowing. The model is expected to return UNKNOWN without an ATTR(value) event; CPython is invoked through _actual(return_process=True) and must fail with AttributeError stating that int has no attribute value.

CONTRACT_PROVED:
- The test compares actual CPython object identity and final value in the restored case and checks the concrete exception in the lost-binding case. A passing model result alone is not treated as the runtime oracle.

INFERENCE:
- The negative model expectation UNKNOWN is a conservative-model contract; CPython's AttributeError establishes the runtime consequence but cannot by itself prove that UNKNOWN is the only valid evaluator classification.

CPYTHON_PARITY

DIRECT_EVIDENCE:
- Both added contracts execute real source in subprocesses using the repository interpreter. G1 uses the existing _run helper with isolated mode (-I) and bytecode disabled (-B). G3 launches sys.executable directly with -I -B and reads JSON object facts; the negative branch checks the exception text.
- The G1 process assertions cover selected value, module origin, and namespace portion order. G3 checks final value, module type, sys.modules identity, and the negative exception class/message. Thus the assertions would reject the opposite child selection, a stale/non-module binding, an incorrect final value, or a different runtime failure.
- Exact observed values are the values asserted by the passing tests: FIRST/SECOND according to root order for G1; 7, True, True for G3 positive; AttributeError for G3 negative.

UNKNOWN:
- The test runner reports pass/fail rather than persisting raw subprocess stdout/stderr in the report. Assertions and successful process return codes are the direct test evidence for the stated outcomes.

TARGETED_TESTS

DIRECT_EVIDENCE:
- .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_namespace_pep420_contract.py -k "namespace_same_child_order_matches_cpython" — 1 passed, 6 deselected in 2.06s; exit code 0.
- .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k "reimport_restores_shadowed_module_identity" — 1 passed, 249 deselected in 1.87s; exit code 0.
- .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_namespace_pep420_contract.py tests/test_cycle_semantics_package_model.py — 257 passed in 18.12s; exit code 0.
- git diff --check on the changed test files passed. The final git diff --check, including this report, is recorded after report creation below.

MCP_POST_CHANGE

DIRECT_EVIDENCE:
- Desktop watcher reported update_file / UPDATED for tests/test_cycle_semantics_namespace_pep420_contract.py at LIVE revision 1570 and tests/test_cycle_semantics_package_model.py at LIVE revision 1571. Latest LIVE revision at the post-change audit: 1571.
- File-specific MCP contexts at canonical revision 1571 report canonical_state=fresh, workspace_sync=verified, provenance=live for both changed files. Their syntax_diagnostics are checked_and_none with zero errors.
- MCP get_source_range returned the changed source from both files: G1 lines 127-184 and G3 lines 3553-3646. These source ranges matched the local source.
- Project architecture metadata reports canonical_state=fresh at revision 1570 but global workspace_sync=unverified, with an advisory that FileState fingerprint ownership could not be proven for the answered canonical generation. It reports cycle_semantics=stale. File-specific verified sync is limited to the two named files; it does not clear global or cycle-semantics staleness.
- No MCP update_file call was used.

INFERENCE:
- The watcher events and file contexts establish adoption/freshness of these two test files in LIVE. They do not establish freshness of the cycle-semantics analysis family.

FULL_DIFFS

FILES_CHANGED:
- tests/test_cycle_semantics_namespace_pep420_contract.py
- tests/test_cycle_semantics_package_model.py

The following are the complete actual git diffs for both changed test files. walkthrough.md is the required report and is excluded from FILES_CHANGED under the repository reporting rule.

~~~~diff
diff --git a/tests/test_cycle_semantics_namespace_pep420_contract.py b/tests/test_cycle_semantics_namespace_pep420_contract.py
index 3172800..7f7efa2 100644
--- a/tests/test_cycle_semantics_namespace_pep420_contract.py
+++ b/tests/test_cycle_semantics_namespace_pep420_contract.py
@@ -14,6 +14,10 @@ from pathlib import Path
 from contextor.core.cycle_semantics.package_model import (
     evaluate_package_import_order,
 )
+from contextor.core.cycle_semantics.namespace_path_model import (
+    SearchPortion,
+    resolve_namespace_path,
+)
 
 
 def _write(root: Path, relative: str, source: str) -> None:
@@ -120,6 +124,66 @@ def test_t03_namespace_with_two_portions(tmp_path):
     assert result.returncode == 0, result.stderr
 
 
+def test_namespace_same_child_order_matches_cpython(tmp_path):
+    first = tmp_path / "first"
+    second = tmp_path / "second"
+
+    _write(first, "nsp/child.py", "value = 'FIRST'\n")
+    _write(second, "nsp/child.py", "value = 'SECOND'\n")
+
+    for ordered_roots, expected_value in (
+        ((first, second), "FIRST"),
+        ((second, first), "SECOND"),
+    ):
+        portions = tuple(
+            SearchPortion(
+                str(root),
+                frozenset({"nsp/child.py"}),
+            )
+            for root in ordered_roots
+        )
+
+        resolution = resolve_namespace_path(
+            portions,
+            "nsp.child",
+            standard_finder_assumed=True,
+        )
+
+        assert resolution.status == "CONDITIONAL"
+        assert resolution.kind == "MODULE_FILE"
+        assert resolution.source == (
+            f"{ordered_roots[0]}:nsp/child.py"
+        )
+        assert resolution.authority == (
+            "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
+        )
+
+        runtime = _run(
+            ordered_roots,
+            (
+                "import nsp, nsp.child\n"
+                "print(json.dumps({"
+                "'value': nsp.child.value,"
+                "'origin': nsp.child.__file__,"
+                "'portions': list(nsp.__path__)"
+                "}))\n"
+            ),
+        )
+
+        assert runtime.returncode == 0, runtime.stderr
+
+        observed = json.loads(runtime.stdout)
+
+        assert observed["value"] == expected_value
+        assert Path(observed["origin"]) == (
+            ordered_roots[0] / "nsp" / "child.py"
+        )
+        assert observed["portions"] == [
+            str(root / "nsp")
+            for root in ordered_roots
+        ]
+
+
 def test_t04_later_regular_package_shadows_namespace(
     tmp_path,
 ):
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index ee42539..d01ccbc 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -3550,6 +3550,102 @@ def test_nested_attribute_alias_and_overwrite(tmp_path):
     assert not _actual(tmp_path, overwritten, "entry")
 
 
+def test_reimport_restores_shadowed_module_identity(tmp_path):
+    base = {
+        "pkg.__init__": "pass",
+        "pkg.sub": "value=7",
+    }
+
+    restored = {
+        **base,
+        "entry": (
+            "import pkg.sub as subject\n"
+            "subject=3\n"
+            "import pkg.sub as subject\n"
+            "observed=subject.value\n"
+        ),
+    }
+
+    lost = {
+        **base,
+        "entry": (
+            "import pkg.sub as subject\n"
+            "subject=3\n"
+            "observed=subject.value\n"
+        ),
+    }
+
+    restored_result = _model(restored, "entry")
+    lost_result = _model(lost, "entry")
+
+    assert restored_result.outcome == "MODEL_PASS"
+    assert lost_result.outcome == "UNKNOWN"
+
+    assert (
+        len([
+            event
+            for event in restored_result.events
+            if event.module == "entry"
+            and event.operation == "ATTR"
+            and event.target == "pkg.sub"
+            and event.symbol == "value"
+        ])
+        == 1
+    )
+
+    assert not any(
+        event.module == "entry"
+        and event.operation == "ATTR"
+        and event.symbol == "value"
+        for event in lost_result.events
+    )
+
+    restored_dir = tmp_path / "restored"
+    lost_dir = tmp_path / "lost"
+
+    assert _actual(restored_dir, restored, "entry")
+
+    runtime = subprocess.run(
+        [
+            sys.executable, "-I", "-B", "-c",
+            (
+                "import importlib,json,sys,types;"
+                "sys.path.insert(0,sys.argv[1]);"
+                "entry=importlib.import_module('entry');"
+                "print(json.dumps({"
+                "'value':entry.observed,"
+                "'module':isinstance(entry.subject,types.ModuleType),"
+                "'identity':entry.subject is sys.modules['pkg.sub']"
+                "}))"
+            ),
+            str(restored_dir),
+        ],
+        capture_output=True,
+        text=True,
+        timeout=8,
+        check=False,
+    )
+
+    assert runtime.returncode == 0, runtime.stderr
+    assert json.loads(runtime.stdout) == {
+        "value": 7,
+        "module": True,
+        "identity": True,
+    }
+
+    failed = _actual(
+        lost_dir,
+        lost,
+        "entry",
+        return_process=True,
+    )
+
+    assert failed.returncode != 0
+    exception_line = failed.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "'int' object has no attribute 'value'" in exception_line
+
+
 def test_single_attribute_event_contract_after_nested_support(tmp_path):
     source = {"route.__init__": "value=7", "entry": "import route\nx=route.value"}
     result = _model(source, "entry")
~~~~

FINAL_STATUS

- Requested G1 and G3 regression contracts were added at the exact anchors.
- Both focused tests and the requested two-file test run passed.
- No production file, other test file, commit, push, staging operation, FULL run, or restart was performed.
- FINAL_STATUS: PASS for the requested test changes; project-wide cycle_semantics freshness remains UNKNOWN/stale in MCP and is not represented as verified.



