TASK: CONTEXTOR_B0G4C1_RESTRICTED_PACKAGE_INITIALIZATION

HEAD_BEFORE
c9858b869f72138e5c2ab986daaa89af2524fa18

HEAD_AFTER
c9858b869f72138e5c2ab986daaa89af2524fa18

GIT_STATUS_BEFORE
clean

GIT_STATUS_AFTER
M walkthrough.md
?? contextor/core/cycle_semantics/package_model.py
?? tests/test_cycle_semantics_package_model.py
walkthrough.md is the required current-task report and is excluded from FILES_CHANGED.

LIVE_REVISION_BEFORE
420
activity_epoch=1beab26da2ff4932852caa7db6ff4242
canonical_state=fresh
graph=fresh
cycles=fresh, reported cycle diagnostics=16
resync_required=false
name_collisions=0, availability=fresh

LIVE_REVISION_AFTER
422
activity_epoch=1beab26da2ff4932852caa7db6ff4242 (unchanged)
canonical_state=fresh
graph=fresh
cycles=fresh, reported cycle diagnostics=16
resync_required=false
name_collisions=0, availability=fresh
package_model workspace_sync=verified at canonical revision 422

LIVE_WATCHER_EVIDENCE
- Revision 421: desktop_watcher UPDATED contextor/core/cycle_semantics/package_model.py; affected module contextor.core.cycle_semantics.package_model.
- Revision 422: desktop_watcher UPDATED tests/test_cycle_semantics_package_model.py; affected module tests.test_cycle_semantics_package_model.
- Event continuity=continuous. No direct update_file, publish, forced resync, or restart request was made.
- The current activity_epoch remained unchanged across the observed edits.

SOURCE_PRECHECK
- Contextor reported contextor.core.cycle_semantics.package_layout at revision 420 with canonical_state=fresh and workspace_sync=verified.
- Existing build_package_layout is defined by package_layout.py. Its one confirmed direct static consumer before this task was tests.test_cycle_semantics_package_layout. Its hard dependency is contextor.core.cycle_semantics.provenance.
- The requested package_model module and test file did not exist before this task. No cycle_semantics/__init__.py or existing production/test module was changed.
- Git HEAD before editing was c9858b869f72138e5c2ab986daaa89af2524fa18; initial Git status was clean.
- Repository Python was 3.10.9.

FILES_CHANGED
- contextor/core/cycle_semantics/package_model.py (new)
- tests/test_cycle_semantics_package_model.py (new)

IMPLEMENTATION_CONTRACT
- Both created files match the supplied implementation and tests exactly; an in-memory comparison with the attachment returned true for both files.
- The production module models only indexed regular packages and module files with complete source closure. It compiles supported import, from-import, constant assignment, single-level module-attribute read, and pass statements into a restricted operation sequence.
- It models parent-before-child initialization, partially initialized modules, module namespaces, and parent child binding after the child reaches READY.
- Unsupported, ambiguous, incomplete, dynamic, namespace, and special-attribute cases return UNKNOWN. Early reads from an INITIALIZING module return EARLY_BINDING_HAZARD. MODEL_PASS is limited to this model and does not mean SAFE.
- The implementation reads no analyzed source files, executes no analyzed code, invokes no subprocess, mutates no AST, and does not touch ProjectGraph, hard_edges, soft_edges, ArchitectureCycle, detect_cycles, canonical state, or publication.
- The 10,000-step budget is decremented in the model loop; exhaustion returns UNKNOWN. The supplied tests do not contain a dedicated budget-exhaustion fixture.

TEST_COMMAND
Baseline:
& .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
& .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

TEST_RESULTS
- Baseline: 133 passed in 5.08s across the nine specified existing files.
- Post-change: 145 passed in 5.45s across the ten specified files (12 new tests and 133 existing).
- Only the specified files were run. No full repository pytest or full Contextor analysis was run.
- No warnings were emitted; no warning suppression option or filter was used.
- The 12 new tests cover initialization order, early binding, reordered imports, child binding, relative and absolute reexports, dotted aliases, fail-closed ambiguity/unsupported cases, determinism, JSON serialization, invalid input, and no AST mutation.

PACKAGE_INITIALIZATION_EVIDENCE
- test_parent_initializer_precedes_submodule asserts pkg reaches READY before pkg.sub and confirms the synthetic fresh-process import succeeds.
- test_package_relative_reexport and test_package_explicit_reexport confirm supported relative and absolute reexports in both the model and synthetic runtime fixtures.
- Contextor after watcher synchronization reports package_model workspace_sync=verified at revision 422. The model has one hard outbound dependency on package_layout and one direct inbound consumer, tests.test_cycle_semantics_package_model.

PARENT_CHILD_BINDING_EVIDENCE
- test_child_attribute_bound_after_ready verifies the child READY event precedes the parent BIND_CHILD event and confirms the synthetic runtime fixture succeeds.
- The implementation sets a module READY only after its operation frame completes, then records the child reference in the parent namespace and emits BIND_CHILD.

EARLY_BINDING_RUNTIME_FIXTURES
- test_package_early_attribute_failure models pkg.sub reading pkg.value while pkg is still INITIALIZING; outcome is EARLY_BINDING_HAZARD and the isolated synthetic import fails.
- test_same_imports_reordered_pass moves the package binding before the child import; both the model and isolated synthetic import pass.
- test_package_early_from_import_hazard models the corresponding partially initialized from-import; the model reports EARLY_BINDING_HAZARD and the isolated synthetic import fails.
- test_dotted_alias_to_child and test_child_attribute_bound_after_ready confirm supported dotted child access after initialization in the isolated synthetic runtime.
- These subprocess checks operate on temporary synthetic modules created by the test helper. They do not execute analyzed repository modules.

UNKNOWN_FAIL_CLOSED_EVIDENCE
- Tests confirm namespace and ambiguous file/package layouts, an unresolved external import, from-package child ambiguity, special __path__ mutation, module __getattr__, child binding shadowing, and star imports return UNKNOWN.
- The model rejects unsupported AST statement forms instead of claiming a successful import.
- The deterministic test compares repeated results, checks JSON serialization, and verifies that the input AST dumps remain unchanged.

COLLISION_COUNT_BEFORE_AFTER
- Before: 0, fresh at revision 420.
- After: 0, fresh at revision 422.

STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
- Before: 16 reported cycle diagnostics, fresh at revision 420.
- After: 16 reported cycle diagnostics, fresh at revision 422.
- Contextor reports the new model's only hard outbound edge to package_layout. The canonical cycle count is unchanged; this is graph evidence and does not certify all Python runtime import behavior.

NO_SAFETY_CERTIFICATION
- PASS: no general runtime safety claim is made. Synthetic subprocess fixtures validate only the supplied restricted cases. MODEL_PASS and EARLY_BINDING_HAZARD remain restricted-model outcomes and do not suppress ArchitectureCycle.

NO_WARNING_SUPPRESSION
- PASS: no warning filters or suppression options were added to source, tests, or the pytest command.

NO_DIRECT_LIVE_PUBLICATION
- PASS: no direct update_file, publish, forced resync, or restart was requested. The desktop_watcher synchronized the two changed files at revisions 421 and 422.

UNRESOLVED_LIMITATIONS
- Namespace packages, import hooks, dynamic imports, calls, decorators, classes, star imports, special runtime attributes, ambiguous from-package child resolution, child-binding shadowing, and incomplete indexed source closure are deliberately unsupported and return UNKNOWN.
- Synthetic runtime agreement covers only the fixtures in the targeted tests; it is not a certification of arbitrary imports, installed packages, or environment-dependent behavior.
- The 10,000-step exhaustion branch is present in source but has no dedicated test fixture in the supplied test file.

EVIDENCE_CLASSES
- DIRECT_EVIDENCE: baseline and post-change pytest results; Git HEAD/status; Contextor watcher events, revisions, activity epoch, freshness, collision count, and cycle count.
- CODE_PATH_PROVED: both files match the supplied contents; Contextor reports package_model's source verified and its hard dependency on package_layout.
- CONTRACT_PROVED: the specified 12 new tests and 133 existing tests pass; synthetic runtime outcomes are checked by the tests.
- INFERENCE: unchanged fresh canonical cycle count and the new module's single hard dependency show no observed cycle increase in the canonical graph.
- UNKNOWN: general runtime import safety and behavior outside the restricted fixtures.

FINAL_VERDICT
B0G4C1_PASS

FULL_DIFFS
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -0,0 +1,516 @@
+"""Restricted package-aware recursive import initialization evidence.
+
+Only regular, indexed Python packages and simple import/constant/attribute AST.
+Never executes analyzed code or certifies general runtime safety.
+"""
+
+from __future__ import annotations
+
+import ast
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.cycle_semantics.package_layout import build_package_layout
+
+
+@dataclass(frozen=True)
+class PackageModelEvent:
+    module: str
+    operation: str
+    target: str | None = None
+    symbol: str | None = None
+
+
+@dataclass(frozen=True)
+class PackageImportAssessment:
+    entry_module: str
+    outcome: str
+    target_module: str | None
+    symbol: str | None
+    events: tuple[PackageModelEvent, ...]
+    evidence_scope: str = "RESTRICTED_REGULAR_PACKAGE_MODEL"
+
+
+@dataclass(frozen=True)
+class _Step:
+    op: str
+    target: str | None = None
+    symbol: str | None = None
+    binding: str | None = None
+
+
+def _compile(
+    tree: ast.Module,
+    logical: str,
+    package: bool,
+) -> tuple[_Step, ...] | None:
+    steps: list[_Step] = []
+
+    for stmt in tree.body:
+        if isinstance(stmt, ast.Import):
+            for alias in stmt.names:
+                if (
+                    not all(part.isidentifier() for part in alias.name.split("."))
+                    or (
+                        alias.asname is not None
+                        and (
+                            not alias.asname.isidentifier()
+                            or alias.asname.startswith("__")
+                        )
+                    )
+                ):
+                    return None
+
+                steps.append(
+                    _Step(
+                        "IMPORT",
+                        alias.name,
+                        binding=alias.asname or alias.name.split(".")[0],
+                    )
+                )
+
+        elif isinstance(stmt, ast.ImportFrom):
+            if stmt.level:
+                context = (
+                    logical.split(".")
+                    if package
+                    else logical.split(".")[:-1]
+                )
+                climb = stmt.level - 1
+
+                if not context or climb >= len(context):
+                    return None
+
+                base = context[:len(context) - climb]
+
+                if stmt.module:
+                    if not all(
+                        part.isidentifier()
+                        for part in stmt.module.split(".")
+                    ):
+                        return None
+                    base.extend(stmt.module.split("."))
+
+                target = ".".join(base)
+            else:
+                target = stmt.module
+
+            if not target or not all(
+                part.isidentifier() for part in target.split(".")
+            ):
+                return None
+
+            for alias in stmt.names:
+                if (
+                    not alias.name.isidentifier()
+                    or alias.name.startswith("__")
+                    or (
+                        alias.asname is not None
+                        and (
+                            not alias.asname.isidentifier()
+                            or alias.asname.startswith("__")
+                        )
+                    )
+                ):
+                    return None
+
+                steps.append(
+                    _Step(
+                        "FROM",
+                        target,
+                        alias.name,
+                        alias.asname or alias.name,
+                    )
+                )
+
+        elif isinstance(stmt, ast.Assign):
+            if (
+                len(stmt.targets) != 1
+                or not isinstance(stmt.targets[0], ast.Name)
+            ):
+                return None
+
+            name = stmt.targets[0].id
+            if name.startswith("__"):
+                return None
+
+            value = stmt.value
+
+            if (
+                isinstance(value, ast.Constant)
+                and type(value.value) in (
+                    type(None),
+                    bool,
+                    int,
+                    float,
+                    complex,
+                    str,
+                    bytes,
+                )
+            ):
+                steps.append(_Step("BIND", binding=name))
+
+            elif (
+                isinstance(value, ast.Attribute)
+                and isinstance(value.value, ast.Name)
+                and not value.attr.startswith("__")
+            ):
+                steps.append(
+                    _Step(
+                        "ATTR",
+                        value.value.id,
+                        value.attr,
+                        name,
+                    )
+                )
+            else:
+                return None
+
+        elif isinstance(stmt, ast.Pass):
+            continue
+
+        else:
+            return None
+
+    return tuple(steps)
+
+
+def evaluate_package_import_order(
+    indexed_sources: Mapping[str, ast.AST],
+    entry_module: str,
+) -> PackageImportAssessment:
+    """Simulate a restricted closed regular-package source set.
+
+    Indexed package __init__ IDs are translated to logical package names.
+    The operation budget prevents unbounded model execution.
+
+    Results cannot certify general Python import safety.
+    """
+    events: list[PackageModelEvent] = []
+
+    def result(
+        outcome: str,
+        target: str | None = None,
+        symbol: str | None = None,
+    ) -> PackageImportAssessment:
+        return PackageImportAssessment(
+            entry_module,
+            outcome,
+            target,
+            symbol,
+            tuple(events),
+        )
+
+    if (
+        not isinstance(indexed_sources, Mapping)
+        or not isinstance(entry_module, str)
+    ):
+        return result("UNKNOWN")
+
+    if any(
+        not isinstance(name, str)
+        or not isinstance(tree, ast.Module)
+        for name, tree in indexed_sources.items()
+    ):
+        return result("UNKNOWN")
+
+    try:
+        layout = build_package_layout(indexed_sources)
+    except (TypeError, ValueError):
+        return result("UNKNOWN")
+
+    nodes = {node.name: node for node in layout.nodes}
+
+    logical_sources: dict[str, ast.Module] = {}
+    packages: set[str] = set()
+
+    for name, node in nodes.items():
+        if node.kind not in {
+            "REGULAR_PACKAGE",
+            "MODULE_FILE",
+        }:
+            return result("UNKNOWN", name)
+
+        indexed_id = node.indexed_module_ids[0]
+
+        if indexed_id not in indexed_sources:
+            return result("UNKNOWN", name)
+
+        logical_sources[name] = indexed_sources[indexed_id]
+
+        if node.kind == "REGULAR_PACKAGE":
+            packages.add(name)
+
+    def valid_chain(target: str) -> bool:
+        if target not in logical_sources:
+            return False
+
+        parts = target.split(".")
+
+        return all(
+            ".".join(parts[:length]) in packages
+            for length in range(1, len(parts))
+        )
+
+    if not valid_chain(entry_module):
+        return result("UNKNOWN", entry_module)
+
+    programs: dict[str, tuple[_Step, ...]] = {}
+
+    for name, tree in logical_sources.items():
+        if not valid_chain(name):
+            return result("UNKNOWN", name)
+
+        program = _compile(tree, name, name in packages)
+
+        if program is None:
+            return result("UNKNOWN", name)
+
+        programs[name] = program
+
+    # A package initializer that overwrites a direct child
+    # binding requires richer import-statement semantics.
+    # This restricted model refuses that case.
+    for package in packages:
+        children = {
+            name.rsplit(".", 1)[1]
+            for name in programs
+            if (
+                "." in name
+                and name.rsplit(".", 1)[0] == package
+            )
+        }
+
+        if any(
+            step.binding in children
+            for step in programs[package]
+            if step.op in {"BIND", "FROM"}
+        ):
+            return result("UNKNOWN", package)
+
+    states = {
+        name: "NEW"
+        for name in programs
+    }
+
+    namespaces: dict[str, dict[str, str | None]] = {
+        name: {}
+        for name in programs
+    }
+
+    bootstrap = "\x00ENTRY"
+    frames: list[tuple[str, int]] = [(bootstrap, 0)]
+
+    def chain(name: str) -> tuple[str, ...]:
+        parts = name.split(".")
+
+        return tuple(
+            ".".join(parts[:index])
+            for index in range(1, len(parts) + 1)
+        )
+
+    def missing_piece(name: str) -> str | None:
+        for piece in chain(name):
+            if piece not in states:
+                return piece
+
+            if states[piece] == "NEW":
+                return piece
+
+        return None
+
+    step_budget = 10000
+
+    while frames:
+        step_budget -= 1
+
+        if step_budget < 0:
+            return result("UNKNOWN")
+
+        module, index = frames[-1]
+
+        steps = (
+            (_Step("IMPORT", entry_module, binding=None),)
+            if module == bootstrap
+            else programs[module]
+        )
+
+        if index >= len(steps):
+            frames.pop()
+
+            if module != bootstrap:
+                states[module] = "READY"
+                events.append(
+                    PackageModelEvent(module, "READY")
+                )
+
+                if "." in module:
+                    parent, child = module.rsplit(".", 1)
+                    namespaces[parent][child] = module
+
+                    events.append(
+                        PackageModelEvent(
+                            parent,
+                            "BIND_CHILD",
+                            module,
+                            child,
+                        )
+                    )
+
+            continue
+
+        step = steps[index]
+
+        if step.op in {"IMPORT", "FROM"}:
+            target = step.target
+
+            if not target or target not in programs:
+                return result("UNKNOWN", target)
+
+            next_piece = missing_piece(target)
+
+            if next_piece:
+                if next_piece not in programs:
+                    return result("UNKNOWN", next_piece)
+
+                states[next_piece] = "INITIALIZING"
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        "START_IMPORT",
+                        next_piece,
+                    )
+                )
+
+                frames.append((next_piece, 0))
+                continue
+
+            if step.op == "IMPORT":
+                if module != bootstrap:
+                    if (
+                        step.binding != target.split(".")[0]
+                        and "." in target
+                    ):
+                        parent, child = target.rsplit(".", 1)
+
+                        if namespaces[parent].get(child) != target:
+                            return result("UNKNOWN", target, child)
+
+                    binding_target = (
+                        target
+                        if step.binding != target.split(".")[0]
+                        else target.split(".")[0]
+                    )
+
+                    namespaces[module][step.binding] = binding_target
+
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            "IMPORT",
+                            target,
+                            step.binding,
+                        )
+                    )
+
+            else:
+                member = step.symbol
+
+                # from-package child resolution is ambiguous.
+                # C1 does not attempt to resolve that ambiguity.
+                if (
+                    target in packages
+                    and target + "." + member in programs
+                ):
+                    return result("UNKNOWN", target, member)
+
+                if member not in namespaces[target]:
+                    outcome = (
+                        "EARLY_BINDING_HAZARD"
+                        if states[target] == "INITIALIZING"
+                        else "MISSING_EXPORT"
+                    )
+
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            outcome,
+                            target,
+                            member,
+                        )
+                    )
+
+                    return result(outcome, target, member)
+
+                namespaces[module][step.binding] = namespaces[target][member]
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        "FROM",
+                        target,
+                        member,
+                    )
+                )
+
+        elif step.op == "BIND":
+            namespaces[module][step.binding] = None
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "BIND",
+                    symbol=step.binding,
+                )
+            )
+
+        elif step.op == "ATTR":
+            reference = namespaces[module].get(step.target)
+
+            if reference not in namespaces:
+                return result(
+                    "UNKNOWN",
+                    step.target,
+                    step.symbol,
+                )
+
+            if step.symbol not in namespaces[reference]:
+                outcome = (
+                    "EARLY_BINDING_HAZARD"
+                    if states[reference] == "INITIALIZING"
+                    else "MISSING_ATTRIBUTE"
+                )
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        outcome,
+                        reference,
+                        step.symbol,
+                    )
+                )
+
+                return result(
+                    outcome,
+                    reference,
+                    step.symbol,
+                )
+
+            namespaces[module][step.binding] = namespaces[reference][step.symbol]
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "ATTR",
+                    reference,
+                    step.symbol,
+                )
+            )
+
+        else:
+            return result("UNKNOWN")
+
+        frames[-1] = (module, index + 1)
+
+    return result("MODEL_PASS")

diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_package_model.py
@@ -0,0 +1,289 @@
+import ast
+import json
+import subprocess
+import sys
+from dataclasses import asdict
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _model(source, entry):
+    return evaluate_package_import_order(
+        {
+            key: ast.parse(code)
+            for key, code in source.items()
+        },
+        entry,
+    )
+
+
+def _actual(tmp_path, source, entry):
+    for module_id, code in source.items():
+        parts = module_id.split(".")
+
+        if parts[-1] == "__init__":
+            path = tmp_path.joinpath(
+                *parts[:-1],
+                "__init__.py",
+            )
+        else:
+            path = tmp_path.joinpath(
+                *parts[:-1],
+                parts[-1] + ".py",
+            )
+
+        path.parent.mkdir(
+            parents=True,
+            exist_ok=True,
+        )
+        path.write_text(
+            code + "\n",
+            encoding="utf-8",
+        )
+
+    process = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            (
+                "import importlib,sys;"
+                "sys.path.insert(0,sys.argv[1]);"
+                "importlib.import_module(sys.argv[2])"
+            ),
+            str(tmp_path),
+            entry,
+        ],
+        capture_output=True,
+        text=True,
+        timeout=8,
+        check=False,
+    )
+
+    return process.returncode == 0
+
+
+def test_parent_initializer_precedes_submodule(tmp_path):
+    source = {
+        "pkg.__init__": "value=7",
+        "pkg.sub": "from pkg import value",
+    }
+
+    result = _model(source, "pkg.sub")
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert [
+        (event.module, event.operation)
+        for event in result.events
+        if event.operation == "READY"
+    ] == [
+        ("pkg", "READY"),
+        ("pkg.sub", "READY"),
+    ]
+
+    assert _actual(tmp_path, source, "pkg.sub")
+
+
+def test_package_early_attribute_failure(tmp_path):
+    source = {
+        "pkg.__init__": "import pkg.sub\nvalue=2",
+        "pkg.sub": "import pkg\nx=pkg.value",
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "value"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_same_imports_reordered_pass(tmp_path):
+    source = {
+        "pkg.__init__": "value=2\nimport pkg.sub",
+        "pkg.sub": "import pkg\nx=pkg.value",
+    }
+
+    assert _model(source, "pkg").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_child_attribute_bound_after_ready(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub": "value=7",
+        "entry": "import pkg.sub\nx=pkg.sub",
+    }
+
+    result = _model(source, "entry")
+
+    assert result.outcome == "MODEL_PASS"
+
+    operations = [
+        (event.module, event.operation, event.target)
+        for event in result.events
+    ]
+
+    assert operations.index(
+        ("pkg.sub", "READY", None)
+    ) < operations.index(
+        ("pkg", "BIND_CHILD", "pkg.sub")
+    )
+
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_package_relative_reexport(tmp_path):
+    source = {
+        "pkg.__init__": "from .sub import value",
+        "pkg.sub": "value=7",
+    }
+
+    assert _model(source, "pkg").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_package_explicit_reexport(tmp_path):
+    source = {
+        "pkg.__init__": "from pkg.sub import value",
+        "pkg.sub": "value=7",
+    }
+
+    assert _model(source, "pkg").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_package_early_from_import_hazard(tmp_path):
+    source = {
+        "pkg.__init__": "from pkg.sub import value",
+        "pkg.sub": "from pkg import value",
+    }
+
+    assert (
+        _model(source, "pkg").outcome
+        == "EARLY_BINDING_HAZARD"
+    )
+
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_dotted_alias_to_child(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub": "value=7",
+        "entry": "import pkg.sub as s\nx=s.value",
+    }
+
+    assert _model(source, "entry").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_from_package_child_remains_unknown():
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.child": "value=7",
+        "entry": "from pkg import child",
+    }
+
+    assert _model(source, "entry").outcome == "UNKNOWN"
+
+
+def test_namespace_ambiguous_external_unknown():
+    assert _model(
+        {"pkg.sub": "value=7"},
+        "pkg.sub",
+    ).outcome == "UNKNOWN"
+
+    assert _model(
+        {
+            "pkg": "pass",
+            "pkg.__init__": "pass",
+        },
+        "pkg",
+    ).outcome == "UNKNOWN"
+
+    assert _model(
+        {"pkg.__init__": "import os"},
+        "pkg",
+    ).outcome == "UNKNOWN"
+
+
+def test_unsupported_hooks_mutations_unknown():
+    assert _model(
+        {"pkg.__init__": "__path__=[]"},
+        "pkg",
+    ).outcome == "UNKNOWN"
+
+    assert _model(
+        {
+            "pkg.__init__":
+                "def __getattr__(name):\n    pass"
+        },
+        "pkg",
+    ).outcome == "UNKNOWN"
+
+    assert _model(
+        {
+            "pkg.__init__": "sub=1\nimport pkg.sub",
+            "pkg.sub": "pass",
+        },
+        "pkg",
+    ).outcome == "UNKNOWN"
+
+    assert _model(
+        {
+            "pkg.__init__": "pass",
+            "pkg.sub": "pass",
+            "entry": "from pkg import *",
+        },
+        "entry",
+    ).outcome == "UNKNOWN"
+
+
+def test_determinism_invalid_no_ast_mutation():
+    sources = {
+        "pkg.__init__": ast.parse("import pkg.sub"),
+        "pkg.sub": ast.parse("import pkg"),
+    }
+
+    before = {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in sources.items()
+    }
+
+    first = evaluate_package_import_order(
+        sources,
+        "pkg",
+    )
+
+    second = evaluate_package_import_order(
+        sources,
+        "pkg",
+    )
+
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+
+    assert {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in sources.items()
+    } == before
+
+    json.dumps(asdict(first))
+
+    assert (
+        evaluate_package_import_order(None, "pkg").outcome
+        == "UNKNOWN"
+    )
+
+    assert (
+        evaluate_package_import_order(
+            {"pkg.__init__": None},
+            "pkg",
+        ).outcome
+        == "UNKNOWN"
+    )

