# CONTEXTOR P1D3-WARN-5L-R1 — ABI-tagged alternative loaders

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `42fa8f361bd2e12a45c995688117c360a2425777`; initial worktree clean. Contextor MCP resolved both target files at canonical revision 903. The two supplied SEARCH blocks each occurred exactly once.

## SEARCH_REPLACE

- DIRECT_EVIDENCE: Applied exactly the specified production and test substitutions. No other source/test file changed.

## ALTERNATIVE_LOADER_SEMANTICS

- CODE_PATH_PROVED: The resolver now conservatively rejects a supplied filename with `candidate + '.'` or `candidate + '/__init__.'` prefix and `.pyc`, `.pyd` or `.so` suffix. This includes ABI-tagged extension names. It returns `INDETERMINATE / ALTERNATIVE_LOADER_CANDIDATE`, without selecting or certifying a loader.
- CONTRACT_PROVED: The new tests cover tagged Windows/Linux extension names, bytecode, an alternative in an earlier namespace portion, and an unrelated `.txt` file that leaves ordinary conditional resolution intact.

## NEGATIVE_TESTS

- CONTRACT_PROVED: Five tagged/bare variants and an earlier-portion alternative fail closed. The unrelated file remains `CONDITIONAL` with source `root:pkg/child.py`.

## TARGETED_TESTS

- DIRECT_EVIDENCE: `python -m py_compile` on both changed files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_namespace_pep420_contract.py` → `20 passed in 3.70s`.
- DIRECT_EVIDENCE: `git diff --check` passed with no whitespace errors. Git emitted only LF-to-CRLF advisories.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: At canonical revision 903, MCP reports both edited files workspace_sync out_of_sync. Graph/cycles fresh, cycle_semantics stale, structural DFS count 16, active-warning count 16, installed model-pass count 0. No manual update_file, FULL or restart was performed.
- UNKNOWN: Watcher synchronization may occur later. Current source sync is not proof of loaded-code adoption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/namespace_path_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`

`walkthrough.md` was overwritten as the authorized report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/namespace_path_model.py b/contextor/core/cycle_semantics/namespace_path_model.py
index badae99..62b50ce 100644
--- a/contextor/core/cycle_semantics/namespace_path_model.py
+++ b/contextor/core/cycle_semantics/namespace_path_model.py
@@ -127,15 +127,18 @@ def resolve_namespace_path(
                 (parent + "/" if parent else "") + fragment
             )
 
-            if (
-                any(
-                    candidate + extension in root.files
-                    for extension in (".pyc", ".pyd", ".so")
-                )
-                or any(
-                    candidate + "/__init__" + extension in root.files
-                    for extension in (".pyc", ".pyd", ".so")
-                )
+            # Tagged extension modules such as module.cp310-win_amd64.pyd
+            # and module.cpython-310-x86_64-linux-gnu.so are not
+            # recognized by testing only the bare ".pyd"/".so" suffix.
+            # Reject conservatively; this is not a loader selection proof.
+            alternative_prefixes = (
+                candidate + ".",
+                candidate + "/__init__.",
+            )
+            if any(
+                filename.startswith(alternative_prefixes)
+                and filename.endswith((".pyc", ".pyd", ".so"))
+                for filename in root.files
             ):
                 return reject("ALTERNATIVE_LOADER_CANDIDATE")
 
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index 74bc76f..c7a5eda 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -145,6 +145,61 @@ def test_t08_alternative_loader_fails_closed():
     )
 
 
+def test_t08b_tagged_alternative_loaders_fail_closed():
+    variants = (
+        "pkg/child.cp310-win_amd64.pyd",
+        "pkg/child.cpython-310-x86_64-linux-gnu.so",
+        "pkg/child.pyc",
+        "pkg/__init__.cp310-win_amd64.pyd",
+        "pkg/__init__.cpython-310-x86_64-linux-gnu.so",
+    )
+
+    for filename in variants:
+        result = _resolve(
+            [_p(
+                "root",
+                "pkg/__init__.py",
+                "pkg/child.py",
+                filename,
+            )],
+            "pkg.child",
+        )
+
+        assert result.status == "INDETERMINATE"
+        assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"
+
+
+def test_t08c_alternative_in_earlier_namespace_portion():
+    roots = (
+        _p(
+            "first",
+            "nsp/left.py",
+            "nsp/child.cp310-win_amd64.pyd",
+        ),
+        _p("second", "nsp/child.py"),
+    )
+
+    result = _resolve(roots, "nsp.child")
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"
+
+
+def test_t08d_unrelated_file_does_not_block_source():
+    result = _resolve(
+        [_p(
+            "root",
+            "pkg/__init__.py",
+            "pkg/child.py",
+            "pkg/child.notes.txt",
+        )],
+        "pkg.child",
+    )
+
+    assert result.status == "CONDITIONAL"
+    assert result.source == "root:pkg/child.py"
+
+
 def test_t09_invalid_inventory_fails_closed():
     assert _resolve(
         [_p("root", "../evil.py")],
```

## REMAINING_UNKNOWN

- Runtime finder policy, actual source search inventory and active loaded-code identity remain unproved. Canonical cycle_semantics is stale after code edits.

## FINAL_VERDICT

The exact two substitutions and focused tests passed. Resolver authority remains conditional/indeterminate; no MODEL_PASS or warning integration was added. Structural cycles and active warnings remain 16. STOP after WARN-5L-R1.
