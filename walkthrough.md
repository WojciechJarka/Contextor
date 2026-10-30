# CONTEXTOR P1D3-WARN-5L — conditional PEP 420 path resolution model

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `f8cd11533dabd50d52f1a0ce0d4b2cecca8c2a0f`; initial worktree clean. Both authorized new files were absent. Python 3.10.9.
- DIRECT_EVIDENCE: Contextor MCP first resolved existing `package_model.py` and WARN-5K contract test at canonical revision 901 with workspace_sync verified, graph/cycles fresh, cycle_semantics stale, structural DFS count 16 and active-warning count 16.

## EXACT_FILE_CREATION

- DIRECT_EVIDENCE: Created only `contextor/core/cycle_semantics/namespace_path_model.py` and `tests/test_cycle_semantics_namespace_path_model.py` from the exact architect-supplied file bodies. No existing production, scenario, consistency, warning or LIVE file was changed.

## CONDITIONAL_RESOLVER_AUTHORITY

- CODE_PATH_PROVED: Resolver output authority is `CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF`. It requires caller-supplied ordered `SearchPortion` inventories and explicit `standard_finder_assumed=True`; otherwise it returns INDETERMINATE with `IMPORT_FINDER_ENVIRONMENT_NOT_PROVED`. This is conditional path inventory reasoning, not authenticated filesystem provenance or runtime safety.

## PATH_SEARCH_PRECEDENCE

- CONTRACT_PROVED: T01/T02 cover nested and top-level namespace paths. T10 covers regular `__init__.py` before same-root module file. The algorithm scans active portions in order and selects a regular initializer or `.py` file before falling back to collected namespace directories. The focused tests pass.

## NAMESPACE_PORTIONS

- CONTRACT_PROVED: T03 verifies two portions are retained in order for a namespace and each child resolves to its corresponding supplied root. It does not prove completeness of actual runtime `sys.path`.

## SHADOWING_AND_DYNAMIC_PATH_TESTS

- CONTRACT_PROVED: T04 verifies a later regular package shadows an earlier namespace candidate in the supplied inventory, and child lookup then fails closed when missing from the regular package. T05 verifies changing the supplied root list changes conditional resolution. These are source-local model tests; WARN-5K separately tests CPython fixtures.

## NEGATIVE_FAIL_CLOSED_CASES

- CONTRACT_PROVED: T06 rejects unproved finder environment; T07 rejects a plain module as package parent; T08 rejects an alternative loader candidate; T09 rejects malformed/duplicate inventory and invalid requested name; T11 verifies deterministic equal results and non-runtime authority.
- CODE_PATH_PROVED: The new resolver returns only `CONDITIONAL` or `INDETERMINATE`; it introduces no `MODEL_PASS` classification or warning suppression path.

## TARGETED_TESTS

- DIRECT_EVIDENCE: `python -m py_compile` on both new Python files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_namespace_pep420_contract.py` → `17 passed in 3.69s` (11 conditional model tests + 6 CPython 3.10 tests).
- DIRECT_EVIDENCE: `git diff --check` and `git diff --no-index --check -- /dev/null` for each new file found no whitespace errors. Git emitted only LF-to-CRLF advisories.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Post-change MCP still reports revision 901, package_model workspace_sync verified, graph/cycles fresh, cycle_semantics stale, structural DFS cycles 16, active warnings 16 and installed model-pass 0. Both new files returned `not_found` in the active module registry at the audit read; their canonical workspace synchronization and registration are UNKNOWN. No manual update_file, FULL or restart was performed.
- UNKNOWN: Active process loaded-code adoption was not checked or claimed. No canonical namespace evidence or LIVE warning integration was added.

## FILES_CHANGED

- `contextor/core/cycle_semantics/namespace_path_model.py` (new, untracked)
- `tests/test_cycle_semantics_namespace_path_model.py` (new, untracked)

`walkthrough.md` was overwritten as the report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/namespace_path_model.py b/contextor/core/cycle_semantics/namespace_path_model.py
new file mode 100644
index 0000000..badae99
--- /dev/null
+++ b/contextor/core/cycle_semantics/namespace_path_model.py
@@ -0,0 +1,206 @@
+"""Conditional PEP 420 path-based resolution for supplied inventories.
+
+This is not filesystem provenance, authenticated runtime search state,
+or authorization to suppress a structural cycle warning.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class SearchPortion:
+    root_id: str
+    files: frozenset[str]
+
+
+@dataclass(frozen=True)
+class PathCandidate:
+    name: str
+    kind: str
+    source: str | None
+    portions: tuple[str, ...]
+
+
+@dataclass(frozen=True)
+class NamespacePathResult:
+    status: str
+    requested_name: str
+    kind: str | None
+    source: str | None
+    portions: tuple[str, ...]
+    steps: tuple[PathCandidate, ...]
+    reason: str | None
+    authority: str = (
+        "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
+    )
+
+
+def resolve_namespace_path(
+    roots: tuple[SearchPortion, ...],
+    requested_name: str,
+    *,
+    standard_finder_assumed: bool = False,
+) -> NamespacePathResult:
+    """Model .py, regular-package and namespace search precedence.
+
+    The supplied file inventory and finder policy are assumptions.
+    Runtime sys.modules, custom finders, alternative loaders,
+    import-time path mutation and external portions are not certified.
+    """
+    steps: list[PathCandidate] = []
+
+    def reject(reason: str) -> NamespacePathResult:
+        return NamespacePathResult(
+            "INDETERMINATE",
+            requested_name,
+            None,
+            None,
+            (),
+            tuple(steps),
+            reason,
+        )
+
+    if not standard_finder_assumed:
+        return reject("IMPORT_FINDER_ENVIRONMENT_NOT_PROVED")
+
+    if (
+        type(roots) is not tuple
+        or not roots
+        or type(requested_name) is not str
+        or not requested_name
+        or any(
+            not part.isidentifier()
+            for part in requested_name.split(".")
+        )
+    ):
+        return reject("INVALID_SEARCH_INPUT")
+
+    seen: set[str] = set()
+    directory_sets: dict[str, frozenset[str]] = {}
+
+    for root in roots:
+        if (
+            type(root) is not SearchPortion
+            or type(root.root_id) is not str
+            or not root.root_id
+            or root.root_id in seen
+            or type(root.files) is not frozenset
+            or any(
+                type(path) is not str
+                or not path
+                or path.startswith("/")
+                or "\\" in path
+                or any(
+                    part in ("", ".", "..")
+                    for part in path.split("/")
+                )
+                or path.endswith("/")
+                for path in root.files
+            )
+        ):
+            return reject("INVALID_SEARCH_INVENTORY")
+
+        seen.add(root.root_id)
+        dirs: set[str] = set()
+
+        for filename in root.files:
+            parts = filename.split("/")
+            for index in range(1, len(parts)):
+                dirs.add("/".join(parts[:index]))
+
+        directory_sets[root.root_id] = frozenset(dirs)
+
+    active: list[tuple[SearchPortion, str]] = [
+        (root, "") for root in roots
+    ]
+    fragments = requested_name.split(".")
+
+    for depth, fragment in enumerate(fragments):
+        name = ".".join(fragments[:depth + 1])
+        namespace_parts: list[tuple[SearchPortion, str]] = []
+        selected: tuple[str, str, SearchPortion, str] | None = None
+
+        for root, parent in active:
+            candidate = (
+                (parent + "/" if parent else "") + fragment
+            )
+
+            if (
+                any(
+                    candidate + extension in root.files
+                    for extension in (".pyc", ".pyd", ".so")
+                )
+                or any(
+                    candidate + "/__init__" + extension in root.files
+                    for extension in (".pyc", ".pyd", ".so")
+                )
+            ):
+                return reject("ALTERNATIVE_LOADER_CANDIDATE")
+
+            if candidate + "/__init__.py" in root.files:
+                selected = (
+                    "REGULAR_PACKAGE",
+                    candidate + "/__init__.py",
+                    root,
+                    candidate,
+                )
+                break
+
+            if candidate + ".py" in root.files:
+                selected = (
+                    "MODULE_FILE",
+                    candidate + ".py",
+                    root,
+                    candidate,
+                )
+                break
+
+            if candidate in directory_sets[root.root_id]:
+                namespace_parts.append((root, candidate))
+
+        if selected is not None:
+            kind, filename, root, directory = selected
+            source = root.root_id + ":" + filename
+            portions: tuple[str, ...] = ()
+
+            active = (
+                [(root, directory)]
+                if kind == "REGULAR_PACKAGE"
+                else []
+            )
+
+        elif namespace_parts:
+            kind = "NAMESPACE_PACKAGE"
+            source = None
+            portions = tuple(
+                root.root_id + ":" + directory
+                for root, directory in namespace_parts
+            )
+            active = namespace_parts
+
+        else:
+            return reject("TARGET_NOT_IN_SUPPLIED_INVENTORY")
+
+        steps.append(
+            PathCandidate(name, kind, source, portions)
+        )
+
+        if (
+            depth < len(fragments) - 1
+            and kind == "MODULE_FILE"
+        ):
+            return reject("MODULE_IS_NOT_A_PACKAGE")
+
+    last = steps[-1]
+
+    return NamespacePathResult(
+        "CONDITIONAL",
+        requested_name,
+        last.kind,
+        last.source,
+        last.portions,
+        tuple(steps),
+        None,
+    )
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
new file mode 100644
index 0000000..74bc76f
--- /dev/null
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -0,0 +1,191 @@
+"""Conditional namespace path-resolution model contracts."""
+
+from __future__ import annotations
+
+from dataclasses import asdict
+
+from contextor.core.cycle_semantics.namespace_path_model import (
+    SearchPortion,
+    resolve_namespace_path,
+)
+
+
+def _p(name, *files):
+    return SearchPortion(name, frozenset(files))
+
+
+def _resolve(roots, name, *, standard_finder_assumed=True):
+    return resolve_namespace_path(
+        tuple(roots),
+        name,
+        standard_finder_assumed=standard_finder_assumed,
+    )
+
+
+def test_t01_namespace_nested_under_regular_package():
+    result = _resolve(
+        [_p(
+            "root",
+            "regular/__init__.py",
+            "regular/ns/child.py",
+        )],
+        "regular.ns.child",
+    )
+
+    assert result.status == "CONDITIONAL"
+    assert tuple(item.kind for item in result.steps) == (
+        "REGULAR_PACKAGE",
+        "NAMESPACE_PACKAGE",
+        "MODULE_FILE",
+    )
+    assert result.source == "root:regular/ns/child.py"
+
+
+def test_t02_top_level_namespace():
+    result = _resolve(
+        [_p("root", "nsp/child.py")],
+        "nsp.child",
+    )
+
+    assert tuple(item.kind for item in result.steps) == (
+        "NAMESPACE_PACKAGE",
+        "MODULE_FILE",
+    )
+
+
+def test_t03_two_namespace_portions():
+    roots = [
+        _p("first", "nsp/left.py"),
+        _p("second", "nsp/right.py"),
+    ]
+
+    result = _resolve(roots, "nsp")
+
+    assert result.kind == "NAMESPACE_PACKAGE"
+    assert result.portions == (
+        "first:nsp",
+        "second:nsp",
+    )
+    assert _resolve(
+        roots, "nsp.left"
+    ).source == "first:nsp/left.py"
+    assert _resolve(
+        roots, "nsp.right"
+    ).source == "second:nsp/right.py"
+
+
+def test_t04_regular_package_shadows_earlier_namespace():
+    roots = [
+        _p("namespace", "nsp/child.py"),
+        _p("regular", "nsp/__init__.py"),
+    ]
+
+    result = _resolve(roots, "nsp")
+
+    assert result.kind == "REGULAR_PACKAGE"
+    assert result.source == "regular:nsp/__init__.py"
+
+    missing = _resolve(roots, "nsp.child")
+    assert missing.status == "INDETERMINATE"
+    assert missing.reason == (
+        "TARGET_NOT_IN_SUPPLIED_INVENTORY"
+    )
+
+
+def test_t05_changed_path_inventory_changes_resolution():
+    first = _p("first", "nsp/left.py")
+    second = _p("second", "nsp/right.py")
+
+    assert _resolve(
+        [first], "nsp.right"
+    ).status == "INDETERMINATE"
+
+    assert _resolve(
+        [second, first], "nsp.right"
+    ).status == "CONDITIONAL"
+
+
+def test_t06_finder_environment_not_proved():
+    result = _resolve(
+        [_p("root", "nsp/child.py")],
+        "nsp.child",
+        standard_finder_assumed=False,
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == (
+        "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
+    )
+    assert result.steps == ()
+
+
+def test_t07_plain_module_cannot_be_package_parent():
+    result = _resolve(
+        [_p("root", "nsp.py", "nsp/child.py")],
+        "nsp.child",
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "MODULE_IS_NOT_A_PACKAGE"
+
+
+def test_t08_alternative_loader_fails_closed():
+    result = _resolve(
+        [_p(
+            "root",
+            "nsp/__init__.py",
+            "nsp/child.pyd",
+        )],
+        "nsp.child",
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == (
+        "ALTERNATIVE_LOADER_CANDIDATE"
+    )
+
+
+def test_t09_invalid_inventory_fails_closed():
+    assert _resolve(
+        [_p("root", "../evil.py")],
+        "pkg",
+    ).status == "INDETERMINATE"
+
+    assert _resolve(
+        [_p("root", "ok.py"), _p("root", "other.py")],
+        "ok",
+    ).status == "INDETERMINATE"
+
+    assert _resolve(
+        [_p("root", "x.py")],
+        "missing..pkg",
+    ).status == "INDETERMINATE"
+
+
+def test_t10_regular_initializer_precedes_module_file():
+    result = _resolve(
+        [_p(
+            "root",
+            "pkg.py",
+            "pkg/__init__.py",
+            "pkg/child.py",
+        )],
+        "pkg.child",
+    )
+
+    assert result.status == "CONDITIONAL"
+    assert result.steps[0].kind == "REGULAR_PACKAGE"
+
+
+def test_t11_deterministic_and_not_runtime_certified():
+    roots = (_p("root", "nsp/child.py"),)
+
+    first = _resolve(roots, "nsp.child")
+    second = _resolve(roots, "nsp.child")
+
+    assert first == second
+    assert asdict(first) == asdict(second)
+    assert first.authority == (
+        "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
+    )
+    assert first.status == "CONDITIONAL"
```

## REMAINING_UNKNOWN

- The supplied inventory is not a proof of actual runtime search path, absence of external portions, absence of custom finders or loaded-code adoption. MCP had not registered either new file at the post-change read.

## FINAL_VERDICT

The exact two new files compile, all 17 focused tests pass, and existing structural cycle and warning counts remain 16. The resolver remains explicitly conditional and disconnected from LIVE warning authority. STOP after WARN-5L.
