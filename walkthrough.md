# CONTEXTOR P1D3-WARN-5K — PEP 420 namespace contract matrix

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `95e4acb126711b09c25ee9fff5ce4969e5fbbac0`; initial worktree had only the prior `walkthrough.md` report modified. The authorized new test file did not exist. Python is 3.10.9.
- DIRECT_EVIDENCE: Contextor MCP first resolved `package_model.py` from canonical revision 900. Structural DFS cycle count was 16; installed active warnings 16, model-pass 0. No production file was edited.

## PEP420_CONTRACT_MATRIX

| Test | CPython 3.10 observation | Restricted model |
| --- | --- | --- |
| T01 namespace under regular package | Child imports; namespace has origin None and search locations | UNKNOWN |
| T02 top-level namespace | Child imports; namespace has origin None and search locations | UNKNOWN |
| T03 two portions | Both children import; namespace path has two portions | Not queried |
| T04 later regular package | Regular initializer shadows earlier namespace candidate | Not queried |
| T05 dynamic path change | Newly added portion supplies later child import | Not queried |
| T06 meta_path finder | Custom finder blocks child despite local source | Not queried |

## PYTHON_VERSION

- DIRECT_EVIDENCE: `\.venv\Scripts\python.exe --version` returned `Python 3.10.9`. Subprocess tests use that interpreter with `-I -B` and explicitly prepend isolated temporary roots inside each subprocess.

## PER_TEST_RESULT

- DIRECT_EVIDENCE: `python -m py_compile tests/test_cycle_semantics_namespace_pep420_contract.py` passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_namespace_pep420_contract.py` → `6 passed in 2.91s`. Each test's asserted CPython observation passed; T01/T02 also asserted model UNKNOWN.
- DIRECT_EVIDENCE: Tracked `git diff --check` and untracked `git diff --no-index --check -- /dev/null tests/test_cycle_semantics_namespace_pep420_contract.py` produced no whitespace errors. Git gave only an LF-to-CRLF advisory.

## CPYTHON_RUNTIME_OBSERVATIONS

- CONTRACT_PROVED: The six tests capture actual isolated Python 3.10 subprocess behavior for the six specified fixtures. No result is extrapolated to the active Contextor runtime or a globally closed import search path.

## CURRENT_MODEL_UNKNOWN_PARITY

- CONTRACT_PROVED: T01 and T02 verify the restricted model remains UNKNOWN while CPython imports their local namespace children. T03–T06 intentionally do not call the restricted model and establish only the runtime resolution facts named above. No LIVE MODEL_PASS or warning suppression is authorized by this matrix.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: MCP still resolves `package_model.py` at revision 900 with workspace_sync verified, graph/cycles fresh, cycle_semantics stale; structural DFS count remains 16 and installed active warnings remain 16. The new test file is not yet present in the active module registry (`get_module_context` returned `not_found`), so its canonical workspace synchronization is UNKNOWN. This does not affect the local py_compile/pytest results.
- UNKNOWN: Active loaded-code adoption was not checked or claimed. No FULL, update_file or restart was performed.

## FILES_CHANGED

- `tests/test_cycle_semantics_namespace_pep420_contract.py` (new, untracked)

`walkthrough.md` was overwritten as the report. No production file changed.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_namespace_pep420_contract.py b/tests/test_cycle_semantics_namespace_pep420_contract.py
new file mode 100644
index 0000000..3172800
--- /dev/null
+++ b/tests/test_cycle_semantics_namespace_pep420_contract.py
@@ -0,0 +1,187 @@
+"""CPython 3.10 import-resolution contracts for namespace packages.
+
+These tests do not authorize LIVE MODEL_PASS or warning suppression.
+"""
+
+from __future__ import annotations
+
+import ast
+import json
+import subprocess
+import sys
+from pathlib import Path
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _write(root: Path, relative: str, source: str) -> None:
+    path = root / relative
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text(source, encoding="utf-8")
+
+
+def _run(roots: tuple[Path, ...], script: str):
+    prefix = (
+        "import sys, json\n"
+        "roots=json.loads(sys.argv[1])\n"
+        "sys.path[:0]=roots\n"
+    )
+    return subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            prefix + script,
+            json.dumps([str(root) for root in roots]),
+        ],
+        capture_output=True,
+        text=True,
+        timeout=10,
+        check=False,
+    )
+
+
+def _restricted(sources: dict[str, str], entry: str):
+    return evaluate_package_import_order(
+        {
+            name: ast.parse(source)
+            for name, source in sources.items()
+        },
+        entry,
+    )
+
+
+def test_t01_namespace_under_regular_package(tmp_path):
+    root = tmp_path / "root"
+    _write(root, "regular/__init__.py", "value = 1\n")
+    _write(root, "regular/ns/child.py", "value = 7\n")
+
+    result = _run(
+        (root,),
+        (
+            "import regular.ns.child\n"
+            "assert regular.ns.child.value == 7\n"
+            "assert regular.ns.__spec__.origin is None\n"
+            "assert regular.ns.__spec__.submodule_search_locations\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
+
+    model = _restricted(
+        {
+            "regular.__init__": "value = 1",
+            "regular.ns.child": "value = 7",
+        },
+        "regular.ns.child",
+    )
+    assert model.outcome == "UNKNOWN"
+
+
+def test_t02_top_level_namespace(tmp_path):
+    root = tmp_path / "root"
+    _write(root, "nsp/child.py", "value = 11\n")
+
+    result = _run(
+        (root,),
+        (
+            "import nsp.child\n"
+            "assert nsp.child.value == 11\n"
+            "assert nsp.__spec__.origin is None\n"
+            "assert nsp.__spec__.submodule_search_locations\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
+
+    assert _restricted(
+        {"nsp.child": "value = 11"},
+        "nsp.child",
+    ).outcome == "UNKNOWN"
+
+
+def test_t03_namespace_with_two_portions(tmp_path):
+    first = tmp_path / "first"
+    second = tmp_path / "second"
+
+    _write(first, "nsp/left.py", "value = 1\n")
+    _write(second, "nsp/right.py", "value = 2\n")
+
+    result = _run(
+        (first, second),
+        (
+            "import nsp.left, nsp.right\n"
+            "assert nsp.left.value == 1\n"
+            "assert nsp.right.value == 2\n"
+            "assert len(list(nsp.__path__)) == 2\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
+
+
+def test_t04_later_regular_package_shadows_namespace(
+    tmp_path,
+):
+    first = tmp_path / "first"
+    second = tmp_path / "second"
+
+    _write(first, "nsp/namespace_child.py", "value = 1\n")
+    _write(second, "nsp/__init__.py", "value = 99\n")
+
+    result = _run(
+        (first, second),
+        (
+            "import nsp\n"
+            "assert nsp.value == 99\n"
+            "assert nsp.__file__ is not None\n"
+            "assert nsp.__spec__.origin.endswith('__init__.py')\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
+
+
+def test_t05_namespace_path_changes_dynamically(tmp_path):
+    first = tmp_path / "first"
+    second = tmp_path / "second"
+
+    _write(first, "nsp/left.py", "value = 1\n")
+    _write(second, "nsp/right.py", "value = 2\n")
+
+    result = _run(
+        (first,),
+        (
+            "import nsp.left\n"
+            f"sys.path.insert(0, {str(second)!r})\n"
+            "import nsp.right\n"
+            "assert nsp.right.value == 2\n"
+            "assert len(list(nsp.__path__)) == 2\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
+
+
+def test_t06_meta_path_finder_can_override_resolution(
+    tmp_path,
+):
+    root = tmp_path / "root"
+    _write(root, "nsp/child.py", "value = 7\n")
+
+    result = _run(
+        (root,),
+        (
+            "import nsp\n"
+            "class Blocker:\n"
+            "    def find_spec(self, fullname, path=None, target=None):\n"
+            "        if fullname == 'nsp.child':\n"
+            "            raise ModuleNotFoundError('blocked by finder')\n"
+            "sys.meta_path.insert(0, Blocker())\n"
+            "try:\n"
+            "    import nsp.child\n"
+            "except ModuleNotFoundError as exc:\n"
+            "    assert str(exc) == 'blocked by finder'\n"
+            "else:\n"
+            "    raise AssertionError('custom finder was ignored')\n"
+        ),
+    )
+    assert result.returncode == 0, result.stderr
```

## REMAINING_UNKNOWN

- New test file canonical synchronization and exact active runtime loaded-code identity are unverified. No production namespace capability was added. The observations are bounded to the six synthetic Python 3.10 fixtures.

## FINAL_VERDICT

The architect-authored test-only matrix was added exactly and all six focused tests passed. Structural DFS cycles and active warnings remained at 16. STOP after WARN-5K.
