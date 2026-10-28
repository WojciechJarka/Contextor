# CONTEXTOR P1D3-D2B-1 — TYPE_CHECKING IMPORT-TIME ACTIVATION MODEL

## 1. EXECUTIVE VERDICT

**GO (scoped D2B-1 acceptance).** The four supported forms passed their synthetic graph/model/CPython checks; the 18-case unsupported matrix failed closed; original-worker P0/P1B, manifest v2, forged-event replay, and isolated official FULL receipt assertions passed. The exact focused suite completed with 271 passed, 0 failed, 0 skipped. This is not a claim about arbitrary Python runtime state or active LIVE code adoption.

Evidence: DIRECT_EVIDENCE — focused pytest output; CODE_PATH_PROVED — changed source diff; CONTRACT_PROVED — assertions in the named regression tests.

## 2. INITIAL/FINAL HEAD AND WORKTREE

- Initial HEAD: `5c8badd975a73956742dfde0f4244183954d3c01`.
- Final HEAD: `5c8badd975a73956742dfde0f4244183954d3c01` (unchanged; no Git mutation).
- At task start the source/test worktree was clean. Final worktree contains the three authorized modified files, the authorized new module, and this report.
- No commit, checkout, reset, clean, push, active service restart, active LIVE mutation, or active-repository FULL was performed.

Evidence: DIRECT_EVIDENCE — `git rev-parse HEAD` and `git status --short`.

## 3. EXACT PRODUCTION CHANGES

- `contextor/core/cycle_semantics/typing_guard.py`: pure AST recognizer; exact NAME and ATTRIBUTE marker/condition forms; rejects shadowing, reassignment, duplicate/nested/non-top-level guards, unsupported indexed `typing`, and unsupported import bindings. No filesystem, indexer, graph, `sys.modules`, or Python `typing` imports.
- `contextor/core/cycle_semantics/package_graph_consistency.py`: skips only the recognizer-returned marker AST node by object identity when deriving expected internal edges. The guarded import occurrences remain subject to existing graph resolution and final equality.
- `contextor/core/cycle_semantics/package_model.py`: optional final `_compile(..., typing_guard=None)` argument; records a marker event; selects the `else` suite for an exact top-level positive guard under the restricted standard-library convention; emits a private NUL-prefixed binding sentinel without importing `typing` into modeled indexed module state.

Evidence: CODE_PATH_PROVED — full source diffs below; DIRECT_EVIDENCE — tests preserve the lexical hard graph and model activation behavior.

## 4. SHARED AST RECOGNIZER

`matches_typing_guard(condition, form)` and `recognize_typing_guard(tree, indexed_ids)` are implemented in the new pure module. Recognition requires an actual `ast.Module`, a `frozenset` indexed identity collection without `typing` or `typing.__init__`, exactly one supported direct marker import, an allowed pre-marker prefix (initial literal docstring and/or `pass` only), and one or more direct top-level matching guards after the marker. The binding audit rejects protected-name writes, deletes, imports, definitions, argument/declaration/exception/pattern bindings and ATTRIBUTE-form writes to `typing.TYPE_CHECKING`. Nested matching guards and non-exact expressions are rejected.

Evidence: CODE_PATH_PROVED — `typing_guard.py`; CONTRACT_PROVED — negative matrix and supported-form tests.

## 5. NAME GUARD

`from typing import TYPE_CHECKING` followed by `if TYPE_CHECKING:` is recognized only when the local indexed identity set does not shadow `typing`. Compilation emits `TYPING_MARKER_IMPORT`; the positive `pkg.b` body is inactive in the restricted model. The canonical hard edge and lexical import occurrence remain present. The synthetic CPython observations agreed for fresh entries `pkg.a` and `pkg.b`.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_name_guard_inactive`; CODE_PATH_PROVED — `_compile` and recognizer paths.

## 6. ATTRIBUTE GUARD

`import typing` followed by `if typing.TYPE_CHECKING:` follows the same restricted convention. Aliased `typing`, rebinding/shadowing, and a local indexed `typing` module/package fail recognition. The model represents the marker import with its local private sentinel and does not load an indexed `typing` module.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_attribute_guard_inactive` and negative N05/N11/N13/N14; CODE_PATH_PROVED — shared recognizer and package model.

## 7. ELSE EXECUTION

For either supported positive guard, D2B-1 compiles the `else` suite, preserving source order. `D2B_ELSE_HAZARD` imports `pkg.b` before binding `pkg.a.value`, and the isolated CPython run reports the expected partially initialized module error; the model reports the early-binding hazard. `D2B_ELSE_SAFE` binds `value` before the `else` import and passes in both model and CPython. The lexical control-site branch for these import occurrences is `ELSE`.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_else_activates_import` and `test_p1d3_d2b_else_reordered_safe`; INFERENCE — the model’s scope is restricted to the specified ordinary `typing.TYPE_CHECKING is False` convention.

## 8. GRAPH AND SCC IDENTITY

All four fixtures produce the exact canonical graph:

- `pkg.__init__`: no hard targets
- `pkg.a`: hard target `pkg.b`
- `pkg.b`: hard target `pkg.a`

The SCC remains `{pkg.a, pkg.b}`. Every positive case is `REGULAR_PACKAGE` with `COMPLETE_FRESH_MEMBER_ENTRIES` coverage. ELSE hazard classifies as `MODEL_INTERNAL_EARLY_BINDING_HAZARD`; the other three classify as `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`.

Evidence: DIRECT_EVIDENCE — four positive fixture assertions; CONTRACT_PROVED — Facade-equivalent helper used by `_d2a_source_evidence`.

## 9. HARD/SOFT EDGE PRESERVATION

The D2B-1 tests assert both original `pkg.a`/`pkg.b` hard dependencies remain, the import reference is not `type_only`, and the lexical cyclic import site remains `LEXICAL_CANDIDATES` with its IF control frame (BODY for inactive-body forms and ELSE for else forms). No soft-edge migration or indexer/provenance edit was made.

Evidence: DIRECT_EVIDENCE — integration assertions and final changed-file list; CODE_PATH_PROVED — only package graph consistency and restricted package model changed.

## 10. NEGATIVE MATRIX

N01–N18 all passed as negative cases: missing marker; marker assignment before/after; aliased marker/module; `not`; `is False`; equality comparison; nested function/class marker; `typing.TYPE_CHECKING` reassignment; marker shadow import; local `typing.py`; local `typing/__init__.py`; effectful import before marker; conditional marker; duplicate marker; nested guard. The recognizer returns `None`; no all-pass positive model classification is accepted; if reindex preparation is ready, the test requires no positive manifest digest.

Evidence: DIRECT_EVIDENCE — 18 parametrized case results in the passing focused suite.

## 11. LOCAL TYPING SHADOWING

N13 and N14 add a synthetic indexed `typing.py` and `typing/__init__.py` respectively; both cause recognition to fail closed. No external module identity is inferred from source syntax.

Evidence: DIRECT_EVIDENCE — negative test cases; CODE_PATH_PROVED — exact indexed identity guard in `recognize_typing_guard`.

## 12. CPYTHON DIFFERENTIAL

The supported tests run each `(root, entry)` observation through the existing synthetic import helper in a subprocess, so each observation receives a fresh interpreter. Results agreed for both safe inactive guards, the active ELSE hazard, and the reordered safe ELSE. Only the temporary synthetic repositories were executed.

Evidence: DIRECT_EVIDENCE — passing test assertions; CODE_PATH_PROVED — `tests/cycle_semantics_lab/__init__.py` `run_synthetic_import` subprocess helper. This does not establish behavior under arbitrary import hooks or external mutation of `typing.TYPE_CHECKING`.

## 13. P0 GENUINE EVIDENCE

For each supported fixture, original-worker captured source fingerprints and evidence pass `assess_index_bound_scc_models` as `DECLARED_INPUTS_CONSISTENT`.

Evidence: DIRECT_EVIDENCE — positive test assertions using `_d2a_source_evidence` and captured worker result.

## 14. P1B GENUINE REPLAY

For each supported fixture, captured original-worker source bytes pass `assess_scc_source_bytes` as `BYTE_AST_CONSISTENT_NON_ATOMIC`.

Evidence: DIRECT_EVIDENCE — positive test assertions.

## 15. P1B FORGED EVENT

The test changes one real `TYPING_MARKER_IMPORT` event to `FORGED_TYPING_MARKER_IMPORT`, recomputes the caller-controlled component token, and retains the genuine captured source/fingerprints. P0 remains `DECLARED_INPUTS_CONSISTENT`; P1B returns `MODEL_REPLAY_MISMATCH`.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_forged_marker_event_rejected` passed. The verifier itself was not changed.

## 16. MANIFEST V2

The original-worker preview prepares as `PREPARED_UNPUBLISHED_NON_ATOMIC`, with `cycle-source-manifest/2`, `REGULAR_PACKAGE`, `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`, ordered source signatures for `pkg.__init__`, `pkg.a`, and `pkg.b`, and a nonempty model evidence SHA256.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_original_worker_prepares_v2` passed.

## 17. OFFICIAL ISOLATED FULL

The existing official FULL harness was exercised only against the temporary synthetic D2B_NAME_SAFE root. Its assertions for real index/graph, original-worker source capture, positive preparation preview, receipt publication, and successful isolated publish all passed. No active Contextor FULL or active LIVE/Desktop/MCP mutation was performed.

Evidence: DIRECT_EVIDENCE — `test_p1d3_d2b_official_isolated_full_receipt` passed; test is marked live but uses `_official_live(root, ...)` with an isolated temporary root.

## 18. RECEIPT V2

The isolated receipt uses `cycle-prepared-co-publication/2` and carries `cycle-source-manifest/2`; co-publication receipt verification succeeds and `live_publish_status == success` for the isolated synthetic service harness.

Evidence: CONTRACT_PROVED — test asserts `PUBLICATION_BINDING_VERSION` (source constant `cycle-prepared-co-publication/2`) and manifest v2; DIRECT_EVIDENCE — isolated test passed. This is not evidence of active LIVE adoption.

## 19. REGRESSION RESULTS

The specified seven-file focused suite passed all 271 tests, including existing D1/D2A, package model, scenario/evidence, preparation, receipt and official isolated publication regressions. No tests were skipped in the final output. No global pytest was run.

A preceding run of the same focused suite had 269 passed and two failures because the new control-site assertion expected `BODY` for both ELSE fixtures. The observed value was correctly `ELSE`; the final test expectations now preserve `BODY` for the two inactive-body fixtures and `ELSE` for both ELSE fixtures, and the final suite passes. No production behavior or assertion was relaxed.

## 20. EXACT COMMANDS/EXIT CODES

1. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`
   - Exit code: 0
   - Result: 271 passed, 0 failed, 0 skipped in 54.69s.
2. `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/typing_guard.py contextor/core/cycle_semantics/package_graph_consistency.py contextor/core/cycle_semantics/package_model.py`
   - Exit code: 0.
3. `git diff --check`
   - Exit code: 0. Git printed existing working-copy LF-to-CRLF notices for the two modified tracked files; no whitespace error was reported.
4. `git rev-parse HEAD`
   - Exit code: 0; HEAD remained `5c8badd975a73956742dfde0f4244183954d3c01`.

## 21. FILES_CHANGED

- NEW production: `contextor/core/cycle_semantics/typing_guard.py`
- MODIFIED production: `contextor/core/cycle_semantics/package_graph_consistency.py`
- MODIFIED production: `contextor/core/cycle_semantics/package_model.py`
- MODIFIED test: `tests/test_p1d3_package_cycle_integration.py`
- Report: `walkthrough.md` (report file; its self-diff is omitted)

No other source, test, or documentation file was changed.

## 22. FULL ACTUAL_DIFF

The following are the complete Git diffs for every source/test file changed in this task. The report does not include its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 790c857..964e414 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -9,0 +10 @@ from .model_identity import indexed_to_logical_module, logical_to_indexed_module
+from .typing_guard import recognize_typing_guard
@@ -248,0 +250,4 @@ def assess_package_graph_consistency(
+        typing_guard = recognize_typing_guard(
+            sources[module_id],
+            indexed,
+        )
@@ -249,0 +255,6 @@ def assess_package_graph_consistency(
+            if (
+                typing_guard is not None
+                and node is typing_guard.marker_statement
+            ):
+                continue
+
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index aede764..5d9a8c6 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -13,0 +14,5 @@ from contextor.core.cycle_semantics.package_layout import build_package_layout
+from contextor.core.cycle_semantics.typing_guard import (
+    RecognizedTypingGuard,
+    matches_typing_guard,
+    recognize_typing_guard,
+)
@@ -182,0 +188 @@ def _compile(
+    typing_guard: RecognizedTypingGuard | None = None,
@@ -189,0 +196,19 @@ def _compile(
+        if (
+            _depth == 0
+            and typing_guard is not None
+            and stmt is typing_guard.marker_statement
+        ):
+            steps.append(
+                _Step(
+                    "TYPING_MARKER_IMPORT",
+                    target="typing",
+                    symbol="TYPE_CHECKING",
+                    binding=(
+                        "TYPE_CHECKING"
+                        if typing_guard.form == "NAME"
+                        else "typing"
+                    ),
+                )
+            )
+            continue
+
@@ -307,0 +333,9 @@ def _compile(
+            elif (
+                _depth == 0
+                and typing_guard is not None
+                and matches_typing_guard(
+                    condition,
+                    typing_guard.form,
+                )
+            ):
+                selected = stmt.orelse
@@ -658 +692,11 @@ def evaluate_package_import_order(
-        program = _compile(tree, name, name in packages)
+        indexed_id = nodes[name].indexed_module_ids[0]
+        typing_guard = recognize_typing_guard(
+            indexed_sources[indexed_id],
+            frozenset(indexed_sources),
+        )
+        program = _compile(
+            tree,
+            name,
+            name in packages,
+            typing_guard=typing_guard,
+        )
@@ -783 +827,18 @@ def evaluate_package_import_order(
-        if step.op in {
+        if step.op == "TYPING_MARKER_IMPORT":
+            if not step.binding:
+                return result("UNKNOWN")
+
+            namespaces[module][step.binding] = (
+                "\x00TYPING_MARKER:" + module + ":" + step.binding
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "TYPING_MARKER_IMPORT",
+                    target="typing",
+                    symbol="TYPE_CHECKING",
+                )
+            )
+
+        elif step.op in {
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 050ff01..9985068 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -17,0 +18 @@ from contextor.core.cycle_semantics.evidence import (
+from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
@@ -37,0 +39 @@ from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
+from contextor.core.cycle_semantics.typing_guard import recognize_typing_guard
@@ -139,0 +142,47 @@ D2A_INITIALIZER_SAFE = {
+D2B_NAME_SAFE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B_ATTR_SAFE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "import typing\n"
+        "if typing.TYPE_CHECKING:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B_ELSE_HAZARD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    pass\n"
+        "else:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    ),
+    "pkg/b.py": "from pkg.a import value\n",
+}
+
+D2B_ELSE_SAFE = {
+    **D2B_ELSE_HAZARD,
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "value = 1\n"
+        "if TYPE_CHECKING:\n"
+        "    pass\n"
+        "else:\n"
+        "    import pkg.b\n"
+    ),
+}
+
@@ -1261,0 +1311,270 @@ def test_p1d3_d2a_official_isolated_full_receipt(
+
+
+def _assert_p1d3_d2b_supported_fixture(
+    tmp_path, isolated_dirs, fixture, expected, expected_branch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    assert graph.hard_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+    }
+    assert all(
+        not getattr(item, "type_only", False)
+        for item in index.modules["pkg.a"].imports
+    )
+    assert any(
+        item.module == "pkg.b" and not getattr(item, "type_only", False)
+        for item in index.modules["pkg.a"].imports
+    )
+    site_report = analyze_cyclic_import_sites(graph.hard_edges, parsed)
+    site_edge = next(
+        edge
+        for edge in site_report.components[0].internal_edges
+        if edge.source == "pkg.a" and edge.target == "pkg.b"
+    )
+    assert site_edge.status == "LEXICAL_CANDIDATES"
+    assert site_edge.sites[0].controls[0].kind == "IF"
+    assert site_edge.sites[0].controls[0].branch == expected_branch
+    assert set(evidence.scenarios.components[0].members) == {"pkg.a", "pkg.b"}
+    scenario = evidence.scenarios.components[0]
+    assert scenario.model_kind == "REGULAR_PACKAGE"
+    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+    if fixture is D2B_ELSE_HAZARD:
+        assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    else:
+        assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    guard = recognize_typing_guard(
+        parsed["pkg.a"].tree,
+        frozenset(index.modules),
+    )
+    assert guard is not None
+    assert any(
+        event.operation == "TYPING_MARKER_IMPORT"
+        and event.target == "typing"
+        and event.symbol == "TYPE_CHECKING"
+        for assessment in scenario.entry_assessments
+        for event in assessment.events
+    )
+    assessment_a = next(
+        item for item in scenario.entry_assessments
+        if item.entry_module == "pkg.a"
+    )
+    starts_b = any(
+        event.operation == "START_IMPORT" and event.target == "pkg.b"
+        for event in assessment_a.events
+    )
+    assert starts_b is any(
+        fixture is candidate
+        for candidate in (D2B_ELSE_HAZARD, D2B_ELSE_SAFE)
+    )
+    for entry, succeeds in expected.items():
+        actual = run_synthetic_import(root, entry)
+        assert (actual.returncode == 0) is succeeds
+        modeled = next(
+            item for item in scenario.entry_assessments
+            if item.entry_module == entry
+        )
+        assert (modeled.outcome == "MODEL_PASS") is succeeds
+        if fixture is D2B_ELSE_HAZARD and entry == "pkg.a":
+            assert "partially initialized module" in actual.stderr
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, evidence,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, evidence, captured.original_worker_source_snapshots,
+    )
+    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+
+
+def test_p1d3_d2b_name_guard_inactive(tmp_path, isolated_dirs):
+    _assert_p1d3_d2b_supported_fixture(
+        tmp_path, isolated_dirs, D2B_NAME_SAFE,
+        {"pkg.a": True, "pkg.b": True}, "BODY",
+    )
+
+
+def test_p1d3_d2b_attribute_guard_inactive(tmp_path, isolated_dirs):
+    _assert_p1d3_d2b_supported_fixture(
+        tmp_path, isolated_dirs, D2B_ATTR_SAFE,
+        {"pkg.a": True, "pkg.b": True}, "BODY",
+    )
+
+
+def test_p1d3_d2b_else_activates_import(tmp_path, isolated_dirs):
+    _assert_p1d3_d2b_supported_fixture(
+        tmp_path, isolated_dirs, D2B_ELSE_HAZARD,
+        {"pkg.a": False, "pkg.b": True}, "ELSE",
+    )
+
+
+def test_p1d3_d2b_else_reordered_safe(tmp_path, isolated_dirs):
+    _assert_p1d3_d2b_supported_fixture(
+        tmp_path, isolated_dirs, D2B_ELSE_SAFE,
+        {"pkg.a": True, "pkg.b": True}, "ELSE",
+    )
+
+
+@pytest.mark.parametrize("name,source,extra", [
+    ("N01-no-marker", "if TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N02-assigned-before", "TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N03-assigned-after", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\nTYPE_CHECKING = True\n", {}),
+    ("N04-aliased-name", "from typing import TYPE_CHECKING as TC\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N05-aliased-module", "import typing as t\nif typing.TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N06-not", "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N07-is-false", "from typing import TYPE_CHECKING\nif TYPE_CHECKING is False:\n    import pkg.b\n", {}),
+    ("N08-equals-false", "import typing\nif typing.TYPE_CHECKING == False:\n    import pkg.b\n", {}),
+    ("N09-function-marker", "def load():\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N10-class-marker", "class C:\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N11-attribute-reassigned", "import typing\ntyping.TYPE_CHECKING = True\nif typing.TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N12-shadow-import", "from typing import TYPE_CHECKING\nfrom other import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N13-local-typing-module", D2B_NAME_SAFE["pkg/a.py"], {"typing.py": "pass\n"}),
+    ("N14-local-typing-package", D2B_NAME_SAFE["pkg/a.py"], {"typing/__init__.py": "pass\n"}),
+    ("N15-marker-after-import", "import pkg.b\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n", {}),
+    ("N16-marker-conditional", "if True:\n    from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N17-marker-duplicated", "from typing import TYPE_CHECKING\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pkg.b\n", {}),
+    ("N18-nested-guard", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    if TYPE_CHECKING:\n        import pkg.b\n", {}),
+])
+def test_p1d3_d2b_unsupported_typing_guards(
+    tmp_path, isolated_dirs, name, source, extra,
+):
+    fixture = {
+        "pkg/__init__.py": "pass\n",
+        "pkg/a.py": source,
+        "pkg/b.py": "from pkg.a import value\n",
+        **extra,
+    }
+    root = write_synthetic_repository(tmp_path / name, fixture)
+    index, graph = _d2a_canonical_index_graph(root)
+    trees = {
+        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
+        for module, item in index.modules.items()
+    }
+    assert recognize_typing_guard(
+        trees["pkg.a"], frozenset(index.modules),
+    ) is None
+    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
+    assert all(
+        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for component in scenarios.components
+    )
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    if plan.status == "READY_FOR_REINDEX_NON_ATOMIC":
+        captured = index_repository(
+            str(root), source_capture_module_ids=plan.selected_module_ids,
+        )
+        prepared = prepare_original_worker_cycle_manifest(
+            captured, graph.hard_edges, _snapshot(root, index, graph),
+        )
+        assert (
+            prepared.manifest is None
+            or prepared.manifest.source_manifest_sha256 is None
+        )
+
+
+def test_p1d3_d2b_original_worker_prepares_v2(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    index, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, snapshot,
+    )
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert prepared.manifest.version == "cycle-source-manifest/2"
+    component = prepared.manifest.components[0]
+    assert component.model_kind == "REGULAR_PACKAGE"
+    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert tuple(row[0] for row in component.source_signatures) == (
+        "pkg.__init__", "pkg.a", "pkg.b",
+    )
+    assert component.model_evidence_sha256
+
+
+def test_p1d3_d2b_forged_marker_event_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
+    scenario = evidence.scenarios.components[0]
+    assessment = next(
+        item for item in scenario.entry_assessments
+        if any(event.operation == "TYPING_MARKER_IMPORT" for event in item.events)
+    )
+    event = next(
+        item for item in assessment.events
+        if item.operation == "TYPING_MARKER_IMPORT"
+    )
+    forged_assessment = replace(
+        assessment,
+        events=tuple(
+            replace(item, operation="FORGED_TYPING_MARKER_IMPORT")
+            if item is event else item
+            for item in assessment.events
+        ),
+    )
+    forged_scenario = replace(
+        scenario,
+        entry_assessments=tuple(
+            forged_assessment if item is assessment else item
+            for item in scenario.entry_assessments
+        ),
+    )
+    component = evidence.components[0]
+    subgraph = tuple(
+        (module, tuple(sorted(graph.hard_edges[module])))
+        for module in component.reachable_modules
+    )
+    forged_component = replace(
+        component,
+        evidence_token=_component_token(
+            component.members, subgraph,
+            component.source_signatures, forged_scenario,
+        ),
+    )
+    forged = replace(
+        evidence,
+        components=(forged_component,),
+        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
+    )
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged, captured.original_worker_source_snapshots,
+    )
+    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"
+
+
+@pytest.mark.live
+def test_p1d3_d2b_official_isolated_full_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    with _official_live(root, monkeypatch) as (client, server, identity, calls):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        assert result.cycle_source_preparation_preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        state, metadata = _persisted(root)
+        receipt = state.cycle_source_publication
+        assert receipt.version == PUBLICATION_BINDING_VERSION
+        assert receipt.prepared_manifest.version == MANIFEST_VERSION
+        component = receipt.prepared_manifest.components[0]
+        assert component.model_kind == "REGULAR_PACKAGE"
+        assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        assert verify_co_published_cycle_manifest(
+            state, revision=metadata.revision,
+            state_id=metadata.state_id, repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+        assert result.live_publish_status == "success"
+        assert calls == [root.resolve()]
diff --git a/contextor/core/cycle_semantics/typing_guard.py b/contextor/core/cycle_semantics/typing_guard.py
new file mode 100644
index 0000000..705df06
--- /dev/null
+++ b/contextor/core/cycle_semantics/typing_guard.py
@@ -0,0 +1,255 @@
+"""Pure recognition of the restricted typing.TYPE_CHECKING idiom."""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class RecognizedTypingGuard:
+    form: str
+    marker_statement: ast.Import | ast.ImportFrom
+
+
+def matches_typing_guard(
+    condition: ast.AST,
+    form: str,
+) -> bool:
+    if form == "NAME":
+        return (
+            isinstance(condition, ast.Name)
+            and condition.id == "TYPE_CHECKING"
+        )
+
+    if form == "ATTRIBUTE":
+        return (
+            isinstance(condition, ast.Attribute)
+            and condition.attr == "TYPE_CHECKING"
+            and isinstance(condition.value, ast.Name)
+            and condition.value.id == "typing"
+        )
+
+    return False
+
+
+def recognize_typing_guard(
+    tree: ast.Module,
+    indexed_ids: frozenset[str],
+) -> RecognizedTypingGuard | None:
+    if not isinstance(tree, ast.Module) or not isinstance(indexed_ids, frozenset):
+        return None
+
+    if "typing" in indexed_ids or "typing.__init__" in indexed_ids:
+        return None
+
+    markers: list[tuple[int, ast.Import | ast.ImportFrom, str]] = []
+    for position, statement in enumerate(tree.body):
+        if (
+            isinstance(statement, ast.ImportFrom)
+            and statement.module == "typing"
+            and statement.level == 0
+            and len(statement.names) == 1
+            and statement.names[0].name == "TYPE_CHECKING"
+            and statement.names[0].asname is None
+        ):
+            markers.append((position, statement, "NAME"))
+        elif (
+            isinstance(statement, ast.Import)
+            and len(statement.names) == 1
+            and statement.names[0].name == "typing"
+            and statement.names[0].asname is None
+        ):
+            markers.append((position, statement, "ATTRIBUTE"))
+
+    if len(markers) != 1:
+        return None
+
+    marker_position, marker_statement, form = markers[0]
+    protected_name = "TYPE_CHECKING" if form == "NAME" else "typing"
+
+    for position, statement in enumerate(tree.body[:marker_position]):
+        if isinstance(statement, ast.Pass):
+            continue
+        if (
+            position == 0
+            and isinstance(statement, ast.Expr)
+            and isinstance(statement.value, ast.Constant)
+            and type(statement.value.value) is str
+        ):
+            continue
+        return None
+
+    top_level_guards = {
+        id(statement)
+        for statement in tree.body
+        if isinstance(statement, ast.If)
+        and matches_typing_guard(statement.test, form)
+    }
+    guard_positions = [
+        position
+        for position, statement in enumerate(tree.body)
+        if isinstance(statement, ast.If)
+        and matches_typing_guard(statement.test, form)
+    ]
+    if not guard_positions or any(
+        position <= marker_position for position in guard_positions
+    ):
+        return None
+
+    class BindingAudit(ast.NodeVisitor):
+        valid = True
+
+        def reject(self) -> None:
+            self.valid = False
+
+        def visit_Name(self, node: ast.Name) -> None:
+            if node.id == protected_name and isinstance(
+                node.ctx, (ast.Store, ast.Del)
+            ):
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_Import(self, node: ast.Import) -> None:
+            for alias in node.names:
+                bound = alias.asname or alias.name.split(".", 1)[0]
+                if bound == protected_name:
+                    if node is marker_statement:
+                        continue
+                    self.reject()
+                if (
+                    form == "ATTRIBUTE"
+                    and alias.name == "typing"
+                    and node is not marker_statement
+                ):
+                    self.reject()
+
+        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
+            for alias in node.names:
+                bound = alias.asname or alias.name
+                if bound == protected_name:
+                    if node is marker_statement:
+                        continue
+                    self.reject()
+                if (
+                    node.module == "typing"
+                    and any(alias.name == "TYPE_CHECKING" for alias in node.names)
+                    and node is not marker_statement
+                ):
+                    self.reject()
+                if alias.name == "*":
+                    self.reject()
+
+        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self._visit_arguments(node.args)
+            self.generic_visit(node)
+
+        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self._visit_arguments(node.args)
+            self.generic_visit(node)
+
+        def visit_Lambda(self, node: ast.Lambda) -> None:
+            self._visit_arguments(node.args)
+            self.generic_visit(node)
+
+        def _visit_arguments(self, arguments: ast.arguments) -> None:
+            if any(
+                argument.arg == protected_name
+                for argument in (
+                    *arguments.posonlyargs,
+                    *arguments.args,
+                    *arguments.kwonlyargs,
+                )
+            ) or (
+                arguments.vararg is not None
+                and arguments.vararg.arg == protected_name
+            ) or (
+                arguments.kwarg is not None
+                and arguments.kwarg.arg == protected_name
+            ):
+                self.reject()
+
+        def visit_ClassDef(self, node: ast.ClassDef) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_Global(self, node: ast.Global) -> None:
+            if protected_name in node.names:
+                self.reject()
+
+        def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
+            if protected_name in node.names:
+                self.reject()
+
+        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_Attribute(self, node: ast.Attribute) -> None:
+            if (
+                form == "ATTRIBUTE"
+                and node.attr == "TYPE_CHECKING"
+                and isinstance(node.value, ast.Name)
+                and node.value.id == "typing"
+                and isinstance(node.ctx, (ast.Store, ast.Del))
+            ):
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_MatchAs(self, node: ast.MatchAs) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_MatchStar(self, node: ast.MatchStar) -> None:
+            if node.name == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
+            if node.rest == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+        def visit_TypeAlias(self, node: ast.AST) -> None:
+            name = getattr(node, "name", None)
+            if isinstance(name, ast.Name) and name.id == protected_name:
+                self.reject()
+            self.generic_visit(node)
+
+    audit = BindingAudit()
+    audit.visit(tree)
+    if not audit.valid:
+        return None
+
+    if form == "ATTRIBUTE":
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Attribute) and (
+                node.attr == "TYPE_CHECKING"
+                and isinstance(node.value, ast.Name)
+                and node.value.id == "typing"
+                and isinstance(node.ctx, (ast.Store, ast.Del))
+            ):
+                return None
+
+    module_guards = {
+        id(statement)
+        for statement in tree.body
+        if isinstance(statement, ast.If)
+        and matches_typing_guard(statement.test, form)
+    }
+    for node in ast.walk(tree):
+        if (
+            isinstance(node, ast.If)
+            and matches_typing_guard(node.test, form)
+            and id(node) not in module_guards
+        ):
+            return None
+
+    return RecognizedTypingGuard(form, marker_statement)
```

## 23. CONTRACT CONFLICTS

None observed during implementation or the specified validations. The four expected lexical control branches were preserved; ELSE imports report an `ELSE` control frame, as expected from their actual AST locations.

## 24. UNSUPPORTED RUNTIME ASSUMPTIONS

The model uses the explicitly restricted ordinary standard-library convention that `typing.TYPE_CHECKING` is false. It does not authenticate arbitrary `sys.modules`, import hooks, monkeypatches, external process state, or active loaded-code identity. General Python runtime safety and active Contextor runtime adoption remain UNKNOWN and are not claimed.

## 25. FINAL GO/PARTIAL/NO_GO

**GO for the scoped D2B-1 contract and acceptance gates.** All specified focused tests and syntax/whitespace checks passed. The result does not authorize or implement D2B-2, try/except semantics, hard-to-soft edge migration, persistent schema changes, or active runtime adoption certification. Stop at D2B-1 pending the next explicit `proceduj`.
