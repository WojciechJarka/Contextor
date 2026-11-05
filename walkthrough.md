# CONTEXTOR C16-B03-P1C0

## PREFLIGHT

Local HEAD 571f83e40853322c144f8b8c9a146791590dbeca; initial worktree clean. P1B implementation present. Contextor MCP preflight revision 1000, both owner modules workspace_sync=verified, cycle_semantics=stale. Intended edits: original_worker_binding.py, original_worker_reindex_planning.py, existing P1B integration test only.

## MCP_DISCOVERY

Contextor module contexts and exact symbol implementations identified assess_original_worker_cycle_closure and verify_original_worker_reindex as owners. Source inspection established parse_source_snapshot(SourceSnapshot, path), read_imports(path, tree=...), ordered ImportRef list equality, and existing earlier raw-byte SHA-256 and AST mode guards. No new extractor was introduced.

## EXACT_FILE_SCOPE

Changed contextor/core/cycle_semantics/original_worker_binding.py, contextor/core/cycle_semantics/original_worker_reindex_planning.py, tests/test_cycle_semantics_optional_child_worker_capture.py, plus walkthrough.md report. No other source/test files changed.

## CAPTURED_AST_IMPORT_REPLAY

For OPTIONAL_NAMED_CHILDREN, binding parses each already validated captured SourceSnapshot with parse_source_snapshot and calls existing indexer read_imports with the supplied tree. It does not reread source from disk or execute analyzed modules. Parse/extraction unavailability returns CLOSURE_IMPORT_REPLAY_UNAVAILABLE:<module_id>.

## IMPORTREF_FIELD_PARITY

Ordered equality of replayed and indexed ImportRef lists covers module, level, names, is_from_import, is_local, type_only and is_lazy through dataclass equality. Any discrepancy returns CLOSURE_IMPORT_FACTS_MISMATCH:<module_id>. Tests alter flags, names and order while keeping selected cohort unchanged.

## TWO_PASS_FACT_PARITY

After graph, inventory, fingerprint, selection and package-root checks, optional verifier compares ordered ImportRef lists for every selected module across discovery and captured indexes. Changed facts return REINDEX_IMPORT_FACTS_CHANGED:<module_id>. Captured AST replay remains an independent later check, demonstrated by mutating both passes identically and seeing binding reject them.

## SOURCE_BYTE_IDENTITY

Existing raw SHA-256, snapshot and AST-mode gates remain before replay. CRLF source bytes retain their raw fingerprint. Byte mismatch continues to fail at CLOSURE_SOURCE_DIGEST_MISMATCH before replay.

## P01_P06_RESULTS

P1B optional capture, child plus transitive sources, eventual reexport shadowing, CRLF byte identity, HARD_ONLY default and ordered import list all pass in the 16-test P1C0 integration module. No source cohort expansion or hard graph change was added in P1C0.

## N01_N10_RESULTS

N01 is_local, N02 type_only, N03 names, N04 list order: exact replay mismatch reason. N05 discovery-only fact change: exact two-pass reason. N06 unparsable captured bytes: exact replay-unavailable reason. N07 extractor returns unavailable: exact replay-unavailable reason. N08 earlier byte gate and N09 missing/extra captures remain covered by P1B tests. N10 verification result has no prepared manifest, MODEL_PASS or installed claim; no warning/publication path was invoked. All targeted assertions passed.

## TARGETED_PYTEST_RESULTS

P1B/P1C0 integration file: 16 PASS. Selected P1A planner, P0 named-member and original-worker legacy regressions including both prior limit tests: 51 PASS, 119 deselected. CPython 3.15.2, -B -q -rs -p no:cacheprovider, external --basetemp C:\Temp\Contextor_C16_P1C0_pytest_tmp. No full suite.

## LEGACY_HARD_ONLY_PARITY

Replay and cross-pass ImportRef comparisons execute only for OPTIONAL_NAMED_CHILDREN. Existing HARD_ONLY status/reason behavior and both over-capacity legacy regressions passed.

## SOURCE_BOUND_AUTHORITY_LIMITS

Captured AST and indexed import facts agree for selected source bytes, but two independent passes are not atomic cross-file capture, canonical owner authentication or runtime import safety. No semantic MODEL_PASS or publication claim is created.

## POST_CHANGE_MCP_AUDIT

Revision 1003: both modified owner modules and changed test module canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count 16; no observed new structural edges; cycle_semantics=stale and model_pass_count=0. Indexed source freshness does not prove loaded backend code adoption. No FULL, update_file, restart, dependency install or commit.

## FILES_CHANGED

- contextor/core/cycle_semantics/original_worker_binding.py
- contextor/core/cycle_semantics/original_worker_reindex_planning.py
- tests/test_cycle_semantics_optional_child_worker_capture.py

walkthrough.md is the report and excluded from source/test diff accounting.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_binding.py b/contextor/core/cycle_semantics/original_worker_binding.py
index 6316007..e3d2609 100644
--- a/contextor/core/cycle_semantics/original_worker_binding.py
+++ b/contextor/core/cycle_semantics/original_worker_binding.py
@@ -10,7 +10,7 @@ import hashlib
 from collections.abc import Mapping
 from dataclasses import dataclass
 
-from contextor.core.source import SourceSnapshot
+from contextor.core.source import SourceError, SourceSnapshot
 
 from .scc import analyze_import_cycle_topology
 from .model_source_closure import (
@@ -172,6 +172,10 @@ def assess_original_worker_cycle_closure(
 
     selected_snapshots: dict[str, SourceSnapshot] = {}
     selected_modes: dict[str, str] = {}
+    if source_selection == _OPTIONAL_NAMED_CHILDREN:
+        from contextor.core.source import parse_source_snapshot
+        from contextor.core.symbol_engine.indexer import read_imports
+
     total = 0
     for module_id in selected:
         snapshot = snapshots[module_id]
@@ -192,6 +196,19 @@ def assess_original_worker_cycle_closure(
         mode = modes[module_id]
         if type(mode) is not str or mode not in _ACCEPTED_MODES:
             return unavailable("CLOSURE_AST_MODE_INVALID:" + module_id)
+        if source_selection == _OPTIONAL_NAMED_CHILDREN:
+            from pathlib import Path
+
+            try:
+                path = Path(index.modules[module_id].absolute_path)
+                parsed = parse_source_snapshot(snapshot, path)
+                replayed, error = read_imports(path, tree=parsed.tree)
+            except (SourceError, SyntaxError, RecursionError):
+                return unavailable("CLOSURE_IMPORT_REPLAY_UNAVAILABLE:" + module_id)
+            if replayed is None or error is not None:
+                return unavailable("CLOSURE_IMPORT_REPLAY_UNAVAILABLE:" + module_id)
+            if replayed != index.modules[module_id].imports:
+                return unavailable("CLOSURE_IMPORT_FACTS_MISMATCH:" + module_id)
         selected_snapshots[module_id] = snapshot
         selected_modes[module_id] = mode
 
diff --git a/contextor/core/cycle_semantics/original_worker_reindex_planning.py b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
index e422eca..697c724 100644
--- a/contextor/core/cycle_semantics/original_worker_reindex_planning.py
+++ b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
@@ -260,6 +260,10 @@ def verify_original_worker_reindex(
         if (frozenset(discovery_selected) != plan.selected_module_ids
                 or frozenset(captured_selected) != plan.selected_module_ids):
             return unavailable("REINDEX_CLOSURE_CHANGED")
+        for module_id in sorted(plan.selected_module_ids):
+            if (discovery_index.modules[module_id].imports
+                    != captured_index.modules[module_id].imports):
+                return unavailable("REINDEX_IMPORT_FACTS_CHANGED:" + module_id)
 
     if discovery_index.skipped != captured_index.skipped:
         return unavailable("REINDEX_SKIPPED_FILES_CHANGED")
diff --git a/tests/test_cycle_semantics_optional_child_worker_capture.py b/tests/test_cycle_semantics_optional_child_worker_capture.py
index eda9ec4..aeb4e1c 100644
--- a/tests/test_cycle_semantics_optional_child_worker_capture.py
+++ b/tests/test_cycle_semantics_optional_child_worker_capture.py
@@ -233,3 +233,85 @@ def test_n12_verified_capture_has_no_publication_claim(tmp_path):
     assert not hasattr(result, "prepared_manifest")
     assert not hasattr(result, "model_pass")
     assert not hasattr(result, "installed_claim")
+
+
+def _replace_imports(index, module_id, imports):
+    return replace(index, modules={**index.modules, module_id: replace(
+        index.modules[module_id], imports=imports
+    )})
+
+
+@pytest.mark.parametrize("field,value", [
+    ("is_local", True),
+    ("type_only", True),
+    ("names", ["child", "helper"]),
+])
+def test_p1c0_n01_n03_captured_import_fact_replay(tmp_path, field, value):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    original = second.modules["pkg.a"].imports
+    changed = [replace(imp, **{field: value}) if imp.is_from_import else imp
+               for imp in original]
+    forged_first = _replace_imports(first, "pkg.a", changed)
+    forged_second = _replace_imports(second, "pkg.a", changed)
+    binding = assess_original_worker_cycle_closure(
+        forged_second, graph.hard_edges, source_selection=plan.source_selection
+    )
+    assert binding.reason == "CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
+    assert _verify((None, forged_first, graph, plan, forged_second, second_graph)).reason == (
+        "REINDEX_BINDING_CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
+    )
+
+
+def test_p1c0_n04_import_order_replay(tmp_path):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    changed = list(reversed(second.modules["pkg.a"].imports))
+    assert changed != second.modules["pkg.a"].imports
+    forged_first = _replace_imports(first, "pkg.a", changed)
+    forged_second = _replace_imports(second, "pkg.a", changed)
+    assert assess_original_worker_cycle_closure(
+        forged_second, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
+    assert _verify((None, forged_first, graph, plan, forged_second, second_graph)).reason == (
+        "REINDEX_BINDING_CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
+    )
+
+
+def test_p1c0_n05_discovery_import_fact_parity(tmp_path):
+    case = _case(tmp_path)
+    _, first, graph, plan, second, second_graph = case
+    changed = [replace(imp, is_local=True) if imp.is_from_import else imp
+               for imp in first.modules["pkg.a"].imports]
+    forged_first = _replace_imports(first, "pkg.a", changed)
+    assert _verify((None, forged_first, graph, plan, second, second_graph)).reason == (
+        "REINDEX_IMPORT_FACTS_CHANGED:pkg.a"
+    )
+
+
+def test_p1c0_n06_unparsable_captured_bytes(tmp_path):
+    case = _case(tmp_path)
+    _, _, graph, plan, second, _ = case
+    raw = b"def =\n"
+    digest = hashlib.sha256(raw).hexdigest()
+    snapshots = dict(second.original_worker_source_snapshots)
+    snapshots["pkg.child"] = SourceSnapshot(raw, digest)
+    fingerprints = dict(second.source_fingerprints_by_module)
+    fingerprints["pkg.child"] = digest
+    forged = replace(second, original_worker_source_snapshots=snapshots,
+                     source_fingerprints_by_module=fingerprints)
+    assert assess_original_worker_cycle_closure(
+        forged, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_IMPORT_REPLAY_UNAVAILABLE:pkg.child"
+
+
+def test_p1c0_n07_extractor_unavailable(tmp_path, monkeypatch):
+    case = _case(tmp_path)
+    _, _, graph, plan, second, _ = case
+    monkeypatch.setattr(
+        "contextor.core.symbol_engine.indexer.read_imports",
+        lambda path, *, tree: (None, "unavailable"),
+    )
+    assert assess_original_worker_cycle_closure(
+        second, graph.hard_edges, source_selection=plan.source_selection
+    ).reason == "CLOSURE_IMPORT_REPLAY_UNAVAILABLE:pkg.__init__"
```

## FINAL_VERDICT

C16_B03_P1C0_PASS

This certifies selected captured AST/import-fact agreement and two-pass selected-fact parity only; full B03 publication remains outside scope.
