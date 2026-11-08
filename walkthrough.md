# CONTEXTOR C16-B03-P1D3-P15-R4 — reached unmodeled import

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP module contexts before editing: `contextor.core.cycle_semantics.package_model` and `contextor.core.cycle_semantics.namespace_bound_model` both canonical revision 1128, `canonical_state=fresh`, `workspace_sync=verified`, provenance LIVE. Architecture at revision 1128: graph/cycles/cycle_semantics fresh, 2 cyclic SCCs, 16 DFS paths. Git HEAD `8261654e6f2ca09375dffe65243fea53dd093eb0`; only pre-existing `walkthrough.md` modification. Repository interpreter CPython 3.15.2.
- CODE_PATH_PROVED: exact anchors existed in `package_model.py`: frozen `PackageImportAssessment`, `_Step`, `_compile` IMPORT/FROM/PREPARE_FROM_MEMBER constructors, local `result()`, and `if not target or target not in programs: return result("UNKNOWN", target)`. Focused `rg` showed direct assessment construction only in this result helper; `scenarios.py`, `evidence.py`, namespace conditional model consume the type; `PackageModelEvent` construction is in the model and event consumers. No material anchor drift.

## EXACT_MODEL_CONTRACT_ADDITION

- Added frozen `ReachedUnmodeledImport(importer, operation, target, symbol, line, column)` immediately before `PackageImportAssessment`; appended nullable `reached_unmodeled_import` after existing `evidence_scope`. Existing positional fields retain order and default behavior.
- Appended nullable `source_line`/`source_column` to `_Step`. The record means only that an actually reached import target is outside the restricted indexed program domain. It does not assert absence from Python's installed environment.

## EXACT_IMPORT_STEP_SOURCE_BINDING

- `_compile` now copies the original import AST statement's `lineno` and `col_offset` onto generated IMPORT, PREPARE_FROM_MEMBER and FROM steps. The called local-function body path compiles the original body statement in an in-memory fragment, so its original coordinates propagate to its reached step. Alias resolution, execution order, binding flags and AST remain unchanged.

## UNKNOWN_BRANCH_BEFORE_AFTER

- Before: `if not target or target not in programs: return result("UNKNOWN", target)`.
- After: this same branch constructs `ReachedUnmodeledImport` only when `target` is truthy and the executing module is not the synthetic bootstrap, then returns the same `UNKNOWN` and target with the record. The local `result()` has one keyword-only nullable argument and passes it into `PackageImportAssessment`. No event is appended, no other UNKNOWN branch changed, and no target is skipped or whitelisted.

## REGRESSION_T01_T06

- T01 direct `import os`: UNKNOWN/os; blocker `pkg`, IMPORT, os, null symbol, line 1 column 0; deterministic `dataclasses.asdict`/`json.dumps` equality and exact serialized blocker fields.
- T02 `from dataclasses import dataclass`: UNKNOWN; blocker FROM/dataclasses/dataclass, line 1 column 0.
- T03 called local function: UNKNOWN; blocker IMPORT/os at original line 2 column 4; CALL_FUNCTION event present.
- T04 uncalled local function: MODEL_PASS, no reached blocker.
- T05 earlier unsupported call: UNKNOWN, no fabricated blocker for later `import os`.
- T06 fully indexed relative import: MODEL_PASS, no blocker.

## CONDITIONAL_NAMESPACE_REGRESSION

Existing `test_p6_eager_external_import_unknown` retained original UNKNOWN, RESTRICTED_MODEL_UNKNOWN and non-null source-bound digest assertions. Added exact nested-model assertions: UNKNOWN with `pkg.ns.a` IMPORT/os, null symbol, line 1 column 0. Source binding and namespace resolution implementations were not edited; conditional authority was not promoted.

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: requested four modules only — `tests/test_cycle_semantics_package_model.py`, `tests/test_cycle_semantics_namespace_bound_model.py`, `tests/test_cycle_semantics_namespace_path_model.py`, `tests/test_cycle_semantics_scenarios.py` — run with repository CPython 3.15.2, `-B -m pytest -q -rs`, `PYTHONDONTWRITEBYTECODE=1`: **196 passed in 18.00s**, zero failures. `git diff --check` exit 0. No full suite.

## MODEL_OUTCOME_PARITY

- CONTRACT_PROVED by focused regressions: new reached external cases remain UNKNOWN; uncalled and fully indexed cases remain MODEL_PASS; unsupported prefix stays UNKNOWN without a false reached record. Existing namespace, path-model and scenario tests also passed. No external code execution or external-module whitelist was added to the model. Existing intentionally isolated tests within requested modules retain their own behavior.
- CODE_PATH_PROVED: the only production behavior change is an extra nullable field returned from one already-UNKNOWN branch. `PackageImportAssessment` old outcome, target and symbol arguments are unchanged. AST nodes are read to obtain coordinates, not mutated. No warning suppression or conditional assessment promotion code changed.

## EVENT_SEQUENCE_PARITY

- CODE_PATH_PROVED: the changed branch still returns before emitting a `PackageModelEvent`; no event constructors or append order were changed. `_Step` source fields are metadata only. Existing event-sequence tests in the four requested modules passed. A byte-for-byte capture of every prior event sequence was not separately performed; the code-path and focused test evidence support parity within the tested contracts.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: after watcher processing, target `package_model` module context: LIVE revision **1131**, `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning; graph and cycles fresh; cycle_semantics **stale**. Architecture: 627 modules, `resync_required=false`, 0 syntax errors, 2 cyclic SCCs, 16 structural DFS paths, runtime execution `UNKNOWN_NOT_EVALUATED`.
- DIRECT_EVIDENCE: metadata and referenced FileState both revision 1131, state_id `20261108_172727`, repo_id `ctx_8efc50d8`. On-disk SHA-256 equals FileState for all three edited files: production `d4e29fbc6ace6fc610a1c21c4bf15249fa4ec89028433056411700e6bae2d031`; package-model test `7b90cbf0dbc78fb42f21e3a2f00442f90cbe085a31498f5a909532585907adfd`; namespace-bound test `700774095a055990940482561810f593d5f5241b70faeada029a6713b50bbdfa`.
- DIRECT_EVIDENCE: source/test diff contains only the three allowlisted files; no unrelated production modification. No `update_file` was called.

## CANONICAL_FRESHNESS_LIMITATION

- The canonical `cycle_semantics` family became `stale` after `SOURCE_CHANGED`; no FULL was run to refresh it. Current on-disk tests and source are synchronized to FileState, but this does **not** prove the persistent LIVE Python process adopted the edited `package_model.py`. Any installed-runtime behavior claim remains unverified.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (report only; excluded from its own diff)

## FULL_DIFFS

Complete actual Git diffs of every changed production/test file follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 4ccaa26..58b98ca 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -31,6 +31,16 @@ class PackageModelEvent:
     symbol: str | None = None
 
 
+@dataclass(frozen=True)
+class ReachedUnmodeledImport:
+    importer: str
+    operation: str
+    target: str
+    symbol: str | None
+    line: int | None
+    column: int | None
+
+
 @dataclass(frozen=True)
 class PackageImportAssessment:
     entry_module: str
@@ -39,6 +49,9 @@ class PackageImportAssessment:
     symbol: str | None
     events: tuple[PackageModelEvent, ...]
     evidence_scope: str = "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    reached_unmodeled_import: (
+        ReachedUnmodeledImport | None
+    ) = None
 
 
 @dataclass(frozen=True)
@@ -51,6 +64,8 @@ class _Step:
     function_body: tuple[_Step, ...] = ()
     function_local: bool = False
     class_local: bool = False
+    source_line: int | None = None
+    source_column: int | None = None
 
 
 @dataclass
@@ -500,6 +515,8 @@ def _compile(
                         alias.name,
                         binding=alias.asname or alias.name.split(".")[0],
                         explicit_alias=alias.asname is not None,
+                        source_line=stmt.lineno,
+                        source_column=stmt.col_offset,
                     )
                 )
 
@@ -562,6 +579,8 @@ def _compile(
                             "PREPARE_FROM_MEMBER",
                             target,
                             alias.name,
+                            source_line=stmt.lineno,
+                            source_column=stmt.col_offset,
                         )
                     )
 
@@ -585,6 +604,8 @@ def _compile(
                         target,
                         alias.name,
                         alias.asname or alias.name,
+                        source_line=stmt.lineno,
+                        source_column=stmt.col_offset,
                     )
                 )
 
@@ -1009,6 +1030,10 @@ def evaluate_package_import_order(
         outcome: str,
         target: str | None = None,
         symbol: str | None = None,
+        *,
+        reached_unmodeled_import: (
+            ReachedUnmodeledImport | None
+        ) = None,
     ) -> PackageImportAssessment:
         return PackageImportAssessment(
             entry_module,
@@ -1016,6 +1041,7 @@ def evaluate_package_import_order(
             target,
             symbol,
             tuple(events),
+            reached_unmodeled_import=reached_unmodeled_import,
         )
 
     if (
@@ -1442,7 +1468,23 @@ def evaluate_package_import_order(
             target = step.target
 
             if not target or target not in programs:
-                return result("UNKNOWN", target)
+                blocker = (
+                    ReachedUnmodeledImport(
+                        importer=module,
+                        operation=step.op,
+                        target=target,
+                        symbol=step.symbol,
+                        line=step.source_line,
+                        column=step.source_column,
+                    )
+                    if target and module != bootstrap
+                    else None
+                )
+                return result(
+                    "UNKNOWN",
+                    target,
+                    reached_unmodeled_import=blocker,
+                )
 
             next_piece = missing_piece(target)
 
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 05fa83b..58f0fc1 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -333,6 +333,25 @@ def test_p6_eager_external_import_unknown():
     assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
     assert result.source_evidence_sha256 is not None
 
+    assert result.conditional_assessment is not None
+
+    model = (
+        result.conditional_assessment.model_assessment
+    )
+
+    assert model is not None
+    assert model.outcome == "UNKNOWN"
+    assert model.reached_unmodeled_import is not None
+
+    blocker = model.reached_unmodeled_import
+
+    assert blocker.importer == "pkg.ns.a"
+    assert blocker.operation == "IMPORT"
+    assert blocker.target == "os"
+    assert blocker.symbol is None
+    assert blocker.line == 1
+    assert blocker.column == 0
+
 
 def test_p6_two_portions_source_bound():
     roots = (
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 5556799..c83ecb4 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -21,6 +21,116 @@ def _model(source, entry):
     )
 
 
+def test_reached_unmodeled_import_direct_import():
+    result = _model({"pkg.__init__": "import os\nvalue=1\n"}, "pkg")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.target_module == "os"
+    blocker = result.reached_unmodeled_import
+    assert blocker is not None
+    assert blocker.importer == "pkg"
+    assert blocker.operation == "IMPORT"
+    assert blocker.target == "os"
+    assert blocker.symbol is None
+    assert blocker.line == 1
+    assert blocker.column == 0
+
+    encoded = json.dumps(asdict(result), sort_keys=True)
+    assert json.loads(encoded)["reached_unmodeled_import"] == {
+        "column": 0,
+        "importer": "pkg",
+        "line": 1,
+        "operation": "IMPORT",
+        "symbol": None,
+        "target": "os",
+    }
+    assert encoded == json.dumps(asdict(result), sort_keys=True)
+
+
+def test_reached_unmodeled_import_from_import():
+    result = _model(
+        {"pkg.__init__": "from dataclasses import dataclass\n"},
+        "pkg",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    blocker = result.reached_unmodeled_import
+    assert blocker is not None
+    assert blocker.operation == "FROM"
+    assert blocker.target == "dataclasses"
+    assert blocker.symbol == "dataclass"
+    assert blocker.line == 1
+    assert blocker.column == 0
+
+
+def test_reached_unmodeled_import_called_function_body():
+    result = _model(
+        {
+            "pkg.__init__": (
+                "def activate():\n"
+                "    import os\n"
+                "activate()\n"
+            ),
+        },
+        "pkg",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    blocker = result.reached_unmodeled_import
+    assert blocker is not None
+    assert blocker.importer == "pkg"
+    assert blocker.operation == "IMPORT"
+    assert blocker.target == "os"
+    assert blocker.line == 2
+    assert blocker.column == 4
+    assert "CALL_FUNCTION" in (event.operation for event in result.events)
+
+
+def test_uncalled_function_import_has_no_reached_blocker():
+    result = _model(
+        {
+            "pkg.__init__": (
+                "def activate():\n"
+                "    import os\n"
+                "value=1\n"
+            ),
+        },
+        "pkg",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.reached_unmodeled_import is None
+
+
+def test_earlier_unsupported_statement_has_no_reached_blocker():
+    result = _model(
+        {
+            "pkg.__init__": (
+                "value=1\n"
+                "unsupported_call()\n"
+                "import os\n"
+            ),
+        },
+        "pkg",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reached_unmodeled_import is None
+
+
+def test_indexed_import_has_no_reached_blocker():
+    result = _model(
+        {
+            "pkg.__init__": "from .child import value\n",
+            "pkg.child": "value=7\n",
+        },
+        "pkg",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.reached_unmodeled_import is None
+
+
 def _actual(tmp_path, source, entry):
     for module_id, code in source.items():
         parts = module_id.split(".")
```

## FINAL_VERDICT

PASS — literal change implemented; 196 targeted tests pass, exact blocker identities and coordinates verified, existing outcomes/events preserved within focused contracts, and MCP post-change source/FileState audit succeeded. Canonical cycle_semantics is stale and persistent runtime adoption remains unverified.
