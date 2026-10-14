# CONTEXTOR_B0G4B4_RESTRICTED_IMPORT_INITIALIZATION_MODEL

## HEAD_BEFORE

d8422ab2ccc90b1d9d6ae62fcfc9744069b7dadc. Git status clean. B0G4B0 provenance, B0G4B1 execution_context, B0G4B2 guards and B0G4B3 binding_order existed. B0G4B2F `_project_guard_evidence` rename present. Both B0G4B4 target paths absent.

## HEAD_AFTER

d8422ab2ccc90b1d9d6ae62fcfc9744069b7dadc. No commit. Git status shows only the two new task files as untracked.

## LIVE_REVISION_BEFORE

410; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; collisions=0 fresh; cycles=16 fresh. Global workspace_sync=unverified. Contextor identified binding_order as an isolated cycle_semantics module with only its own test as direct consumer and zero downstream consumers.

## LIVE_REVISION_AFTER

412; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; all reported families fresh; no parse-stale modules; collisions=0; cycles=16. Desktop watcher revision 411 UPDATED initialization_model.py and revision 412 UPDATED test_cycle_semantics_initialization_model.py, both blast_radius_state=fresh. New production module workspace_sync=verified by full get_file_edit_context at revision 412; global project overlay remains unverified.

## FILES_CHANGED

- contextor/core/cycle_semantics/initialization_model.py (new)
- tests/test_cycle_semantics_initialization_model.py (new)

No existing file, including package __init__.py, was edited. walkthrough.md is this report and is excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT

CONTRACT_PROVED: Both new files exactly match the auditor-supplied content with one final newline. The production module compiles only the explicitly supported flat-module AST statements into immutable ModelStep tuples, then iteratively models NEW/INITIALIZING/READY module states, bound names, aliases, recursive import caching, and source-order steps. Unsupported AST, unknown module, invalid input and external dependencies yield UNKNOWN. Distinct outcomes include MODEL_PASS, EARLY_BINDING_HAZARD, MISSING_EXPORT and MISSING_ATTRIBUTE, with immutable event tuples and evidence_scope=RESTRICTED_FLAT_MODULE_MODEL.
CODE_PATH_PROVED: Production code consumes AST objects supplied by the caller. It does not execute analyzed code, read source files, launch subprocesses, mutate AST, change graph/canonical state, or publish diagnostics. Contextor reports only tests.test_cycle_semantics_initialization_model as a direct consumer, with zero downstream consumers. No FULL/incremental, MCP, Desktop, LIVE or snapshot integration was added.

## TEST_COMMAND

Pre-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`
Post-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS

Repository Python 3.10.9. Pre-edit exit 0: 51 passed in 1.40s. Post-edit exit 0: 77 passed in 3.29s (26 new cases plus 51 existing). No other tests, full suite or full analysis run. Contextor syntax diagnostics for the new production module are fresh and empty at revision 412.

## RUNTIME_FIXTURE_EVIDENCE

DIRECT_EVIDENCE: The new tests write only synthetic source strings to pytest `tmp_path` and invoke a fresh Python process using `sys.executable -I -B -c`, inserting only that temporary directory for importlib.import_module. Tests compare both entry orders for plain cycles, early attribute binding, moved binding, and `from` import hazards. The model itself receives already parsed ASTs; only the test helper `_actual` uses subprocess/runtime import of fixture modules. These fixture results support the restricted examples, not general runtime certification.

## MODEL_SCOPE_AND_UNKNOWN_LIMITATIONS

CONTRACT_PROVED: Supported subset is flat module imports, from-import names, aliases, simple constant assignments, simple module.attribute reads and pass. Unsupported syntax and dependencies explicitly yield UNKNOWN. Packages/__init__, dynamic imports, decorators, classes, arbitrary calls and general Python execution are outside the model. MODEL_PASS applies to a single entry order and recognized subset; EARLY_BINDING_HAZARD is model evidence and not a universal runtime-failure proof. No general safety or reachability claim is made.

## COLLISION_COUNT_BEFORE_AFTER

0 -> 0 from fresh canonical get_name_collisions at revisions 410 and 412. No new Contextor name collision.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER

16 -> 16 from fresh canonical diagnostics. Structural graph code and cycle detection were not changed; watcher indexing of two new modules may add ordinary dependency edges, so a byte-identical whole-repository graph is not claimed.

## NO_SAFETY_CERTIFICATION

CODE_PATH_PROVED: The model emits MODEL_PASS only within RESTRICTED_FLAT_MODULE_MODEL and does not emit SAFE or universal runtime certification. Both import entry orders are evaluated separately in tests.

## NO_WARNING_SUPPRESSION

CODE_PATH_PROVED: No ArchitectureCycle or warning-publication code was edited or called. Fresh structural cycle count remains 16; no suppression rule was introduced.

## NO_DIRECT_LIVE_PUBLICATION

CODE_PATH_PROVED: The module is imported directly only by its new test and is not exported in __init__.py or integrated with service/public projections. Desktop watcher indexing is external observation. No direct update_file call, restart or commit.

## FINAL_VERDICT

B0G4B4_PASS — exact two-file restricted model, 77 focused tests passed, watcher indexed both files, fresh canonical state, zero name collisions and unchanged structural cycle count. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/initialization_model.py

diff --git a/contextor/core/cycle_semantics/initialization_model.py b/contextor/core/cycle_semantics/initialization_model.py
new file mode 100644
index 0000000..abdbca2
--- /dev/null
+++ b/contextor/core/cycle_semantics/initialization_model.py
@@ -0,0 +1,197 @@
+"""A deliberately restricted model of Python 3.10 flat-module import recursion.
+
+Results are evidence about this explicitly supported subset, never a general
+runtime proof or permission to suppress structural cycle warnings.
+"""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass
+from typing import Mapping
+
+
+@dataclass(frozen=True)
+class ModelStep:
+    operation: str
+    target: str | None = None
+    symbol: str | None = None
+    binding: str | None = None
+
+
+@dataclass(frozen=True)
+class ModelEvent:
+    module: str
+    operation: str
+    target: str | None = None
+    symbol: str | None = None
+
+
+@dataclass(frozen=True)
+class ImportOrderAssessment:
+    entry_module: str
+    outcome: str
+    target_module: str | None
+    symbol: str | None
+    events: tuple[ModelEvent, ...]
+    evidence_scope: str = "RESTRICTED_FLAT_MODULE_MODEL"
+
+
+def _valid_name(name: str) -> bool:
+    return bool(name) and name.isidentifier() and not name.startswith("__")
+
+
+def _compile(tree: ast.Module) -> tuple[ModelStep, ...] | None:
+    steps: list[ModelStep] = []
+    for statement in tree.body:
+        if isinstance(statement, ast.Import):
+            for alias in statement.names:
+                if not _valid_name(alias.name) or (
+                    alias.asname is not None and not _valid_name(alias.asname)
+                ):
+                    return None
+                steps.append(ModelStep(
+                    "IMPORT_MODULE", alias.name,
+                    binding=alias.asname or alias.name,
+                ))
+        elif isinstance(statement, ast.ImportFrom):
+            if statement.level != 0 or not _valid_name(statement.module or ""):
+                return None
+            for alias in statement.names:
+                if not _valid_name(alias.name) or (
+                    alias.asname is not None and not _valid_name(alias.asname)
+                ):
+                    return None
+                steps.append(ModelStep(
+                    "IMPORT_NAME", statement.module, alias.name,
+                    alias.asname or alias.name,
+                ))
+        elif isinstance(statement, ast.Assign):
+            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
+                return None
+            name = statement.targets[0].id
+            if not _valid_name(name):
+                return None
+            value = statement.value
+            if isinstance(value, ast.Constant) and type(value.value) in {
+                type(None), bool, int, float, complex, str, bytes,
+            }:
+                steps.append(ModelStep("BIND_CONSTANT", binding=name))
+            elif (
+                isinstance(value, ast.Attribute)
+                and isinstance(value.value, ast.Name)
+                and _valid_name(value.value.id)
+                and _valid_name(value.attr)
+            ):
+                steps.append(ModelStep(
+                    "READ_ATTRIBUTE", value.value.id, value.attr, name,
+                ))
+            else:
+                return None
+        elif isinstance(statement, ast.Pass):
+            continue
+        else:
+            return None
+    return tuple(steps)
+
+
+def evaluate_flat_import_order(
+    modules: Mapping[str, ast.AST],
+    entry_module: str,
+) -> ImportOrderAssessment:
+    """Evaluate one import order without evaluating any user-provided Python.
+
+    MODEL_PASS covers only recognized flat modules, operations, and one order.
+    Any unsupported AST is UNKNOWN, not a proof of failure or safety.
+    """
+    def result(
+        outcome: str,
+        target: str | None = None,
+        symbol: str | None = None,
+    ) -> ImportOrderAssessment:
+        return ImportOrderAssessment(
+            entry_module, outcome, target, symbol, tuple(events)
+        )
+
+    events: list[ModelEvent] = []
+    if not isinstance(modules, Mapping) or not _valid_name(entry_module):
+        return result("UNKNOWN")
+    if entry_module not in modules:
+        return result("UNKNOWN", entry_module)
+
+    programs: dict[str, tuple[ModelStep, ...]] = {}
+    for module, tree in modules.items():
+        if not isinstance(module, str) or not _valid_name(module):
+            return result("UNKNOWN")
+        if not isinstance(tree, ast.Module):
+            return result("UNKNOWN", module)
+        compiled = _compile(tree)
+        if compiled is None:
+            return result("UNKNOWN", module)
+        programs[module] = compiled
+
+    states = {name: "NEW" for name in programs}
+    bindings: dict[str, set[str]] = {name: set() for name in programs}
+    aliases: dict[str, dict[str, str]] = {name: {} for name in programs}
+    frames: list[tuple[str, int]] = [(entry_module, 0)]
+    states[entry_module] = "INITIALIZING"
+
+    while frames:
+        module, index = frames[-1]
+        program = programs[module]
+        if index >= len(program):
+            states[module] = "READY"
+            frames.pop()
+            events.append(ModelEvent(module, "READY"))
+            continue
+
+        step = program[index]
+        if step.operation in {"IMPORT_MODULE", "IMPORT_NAME"}:
+            target = step.target
+            if target not in programs:
+                return result("UNKNOWN", target)
+            if states[target] == "NEW":
+                states[target] = "INITIALIZING"
+                events.append(ModelEvent(module, "START_IMPORT", target))
+                frames.append((target, 0))
+                continue
+            if step.operation == "IMPORT_MODULE":
+                bindings[module].add(step.binding)
+                aliases[module][step.binding] = target
+            else:
+                if step.symbol not in bindings[target]:
+                    outcome = (
+                        "EARLY_BINDING_HAZARD"
+                        if states[target] == "INITIALIZING"
+                        else "MISSING_EXPORT"
+                    )
+                    events.append(ModelEvent(module, outcome, target, step.symbol))
+                    return result(outcome, target, step.symbol)
+                bindings[module].add(step.binding)
+                aliases[module].pop(step.binding, None)
+            events.append(ModelEvent(module, step.operation, target, step.symbol))
+        elif step.operation == "BIND_CONSTANT":
+            bindings[module].add(step.binding)
+            aliases[module].pop(step.binding, None)
+            events.append(ModelEvent(module, "BIND_CONSTANT", symbol=step.binding))
+        elif step.operation == "READ_ATTRIBUTE":
+            target = aliases[module].get(step.target)
+            if target is None:
+                return result("UNKNOWN", step.target, step.symbol)
+            if step.symbol not in bindings[target]:
+                outcome = (
+                    "EARLY_BINDING_HAZARD"
+                    if states[target] == "INITIALIZING"
+                    else "MISSING_ATTRIBUTE"
+                )
+                events.append(ModelEvent(module, outcome, target, step.symbol))
+                return result(outcome, target, step.symbol)
+            bindings[module].add(step.binding)
+            aliases[module].pop(step.binding, None)
+            events.append(ModelEvent(module, "READ_ATTRIBUTE", target, step.symbol))
+        else:
+            return result("UNKNOWN")
+
+        frames[-1] = (module, index + 1)
+
+    return result("MODEL_PASS")

### FULL_DIFF: tests/test_cycle_semantics_initialization_model.py

diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
new file mode 100644
index 0000000..2af1589
--- /dev/null
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -0,0 +1,143 @@
+import ast
+import json
+import subprocess
+import sys
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.initialization_model import (
+    evaluate_flat_import_order,
+)
+
+
+def _assess(sources, entry):
+    return evaluate_flat_import_order(
+        {name: ast.parse(code) for name, code in sources.items()}, entry
+    )
+
+
+def _actual(tmp_path, sources, entry):
+    for name, code in sources.items():
+        (tmp_path / (name + ".py")).write_text(code, encoding="utf-8")
+    result = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", (
+            "import importlib,sys; "
+            "sys.path.insert(0,sys.argv[1]); "
+            "importlib.import_module(sys.argv[2])"
+        ), str(tmp_path), entry],
+        capture_output=True, text=True, timeout=10, check=False,
+    )
+    return result.returncode == 0
+
+
+def test_plain_cycle_both_orders(tmp_path):
+    sources = {"a": "import b\nvalue = 1\n", "b": "import a\nother = 2\n"}
+    for entry in ("a", "b"):
+        assert _assess(sources, entry).outcome == "MODEL_PASS"
+        assert _actual(tmp_path, sources, entry)
+
+
+def test_missing_attribute_first_order_hazard(tmp_path):
+    sources = {"a": "import b\nvalue = 1\n", "b": "import a\nobserved = a.value\n"}
+    assert _assess(sources, "a").outcome == "EARLY_BINDING_HAZARD"
+    assert _assess(sources, "b").outcome == "MODEL_PASS"
+    assert not _actual(tmp_path, sources, "a")
+    assert _actual(tmp_path, sources, "b")
+
+
+def test_move_binding_before_import_changes_outcome_not_edges(tmp_path):
+    sources = {"a": "value = 1\nimport b\n", "b": "import a\nobserved = a.value\n"}
+    for entry in ("a", "b"):
+        assert _assess(sources, entry).outcome == "MODEL_PASS"
+        assert _actual(tmp_path, sources, entry)
+
+
+def test_from_import_hazard(tmp_path):
+    sources = {"a": "import b\nvalue = 1\n", "b": "from a import value\n"}
+    assert _assess(sources, "a").outcome == "EARLY_BINDING_HAZARD"
+    assert _assess(sources, "b").outcome == "MODEL_PASS"
+    assert not _actual(tmp_path, sources, "a")
+    assert _actual(tmp_path, sources, "b")
+
+
+def test_from_import_completed_missing_export():
+    r = _assess({"a": "from b import missing\n", "b": "pass\n"}, "a")
+    assert r.outcome == "MISSING_EXPORT"
+    assert r.target_module == "b"
+    assert r.symbol == "missing"
+
+
+def test_missing_attribute_completed_module():
+    r = _assess({"a": "import b\nx = b.missing\n", "b": "pass\n"}, "a")
+    assert r.outcome == "MISSING_ATTRIBUTE"
+
+
+def test_self_import_is_not_automatically_failure():
+    assert _assess({"a": "import a\nx = 1\n"}, "a").outcome == "MODEL_PASS"
+
+
+def test_repeated_import_and_alias():
+    sources = {"a": "import b as alias\nimport b\nx = alias.value\n", "b": "value=3\n"}
+    assert _assess(sources, "a").outcome == "MODEL_PASS"
+
+
+def test_from_import_alias_binding():
+    assert _assess({"a": "from b import value as x\n", "b": "value = 3\n"}, "a").outcome == "MODEL_PASS"
+
+
+@pytest.mark.parametrize("source", [
+    "if True:\n    import b\n",
+    "def f():\n    import b\n",
+    "import importlib\nimportlib.import_module('b')\n",
+    "import pkg.b\n",
+    "from . import b\n",
+    "from b import *\n",
+    "x = f()\n",
+    "class X: pass\n",
+    "import b\nx = getattr(b,'value')\n",
+    "x, y = (1,2)\n",
+    "raise RuntimeError('must never execute')\n",
+    "import b\ndel b\n",
+    "import b\nawait b\n",
+])
+def test_unsupported_fail_closed(source):
+    assert _assess({"a": source, "b": "value=2\n"}, "a").outcome == "UNKNOWN"
+
+
+def test_external_dependency_unknown():
+    assert _assess({"a": "import os\n"}, "a").outcome == "UNKNOWN"
+
+
+def test_invalid_inputs_unknown():
+    assert evaluate_flat_import_order(None, "a").outcome == "UNKNOWN"
+    assert evaluate_flat_import_order({"a": None}, "a").outcome == "UNKNOWN"
+    assert evaluate_flat_import_order({"a": ast.parse("pass\n")}, "missing").outcome == "UNKNOWN"
+
+
+def test_no_ast_mutation_determinism_serializable():
+    modules = {
+        "a": ast.parse("import b\nx=1"),
+        "b": ast.parse("import a\ny=2"),
+    }
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in modules.items()
+    }
+    one = evaluate_flat_import_order(modules, "a")
+    two = evaluate_flat_import_order(modules, "a")
+    assert one == two
+    assert {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in modules.items()
+    } == before
+    json.dumps(asdict(one))
+
+
+def test_iterative_1200_module_chain():
+    modules = {
+        f"m{i}": ast.parse(f"import m{i+1}\n")
+        for i in range(1200)
+    }
+    modules["m1200"] = ast.parse("x=1\n")
+    assert evaluate_flat_import_order(modules, "m0").outcome == "MODEL_PASS"
