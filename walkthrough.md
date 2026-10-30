# CONTEXTOR P1D3-WARN-5C — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `fdbdc9e07004928587e00b2b869badea3cd9753d`; initial worktree had only the prior `walkthrough.md` report modified. The seven authorized Python targets were clean or, for the new test, absent.
- DIRECT_EVIDENCE: Contextor MCP `get_file_edit_context` resolved the six existing authorized files at revision 884 and reported 16 fresh structural DFS cycles.
- DIRECT_EVIDENCE: All **12** SEARCH blocks occurred exactly once in their specified files. No anchor adaptation was made.

## EXACT_SEARCH_REPLACE

- DIRECT_EVIDENCE: Applied every supplied SEARCH → REPLACE literally to the six existing Python files and created the exact supplied `tests/test_cycle_semantics_capture_capacity.py`. Literal new-file content comparison passed.
- DIRECT_EVIDENCE: No graph, LIVE warning contract, facade default or unrelated file was edited.

## CAPACITY_CONTRACTS

- CODE_PATH_PROVED: Planner selected-module cap, original-worker binding module cap and indexer selected-capture cap are now all **256**, as specified. The indexer aggregate retained raw-byte cap is **32 MiB**, with the existing **2 MiB** per-source transport limit.
- CODE_PATH_PROVED: `scenarios.py` keeps 64 component entries and 4,096 top-level statements, and changes the AST-node budget to **393,216**.
- CONTRACT_PROVED: New T01 asserts the three 256-module caps align; T02 checks a 257-module request is rejected.

## ORIGINAL_WORKER_217_MODULE_VERIFICATION

- CONTRACT_PROVED: The new test in `test_original_worker_reindex_planning.py` builds a synthetic 217-module selected cohort, performs genuine first and second index passes, checks 217 original-worker source snapshots and AST modes, then verifies `REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC`.
- CONTRACT_PROVED: The existing over-cap test was extended from 15 to 255 helper modules and passed, exercising a selected cohort beyond the 256 cap.
- These are isolated synthetic repositories, not an active-repository FULL or source provenance certification for the user's repo.

## AGGREGATE_BYTES_FAIL_CLOSED

- CONTRACT_PROVED: New T03 lowers the aggregate byte cap only in its isolated test and observes `UNAVAILABLE / CAPTURE_TOTAL_BYTE_LIMIT` with empty source snapshots and AST modes.
- CONTRACT_PROVED: New T04 checks default indexing returns `NOT_REQUESTED` and no original-worker source snapshots.

## AST_BUDGET_FAIL_CLOSED

- CONTRACT_PROVED: The existing AST budget regression uses a test-local 256-node cap and still receives `AST_NODE_BUDGET_EXCEEDED`.
- CONTRACT_PROVED: A 17,000-element synthetic source no longer hits the expanded default AST budget but remains `INDETERMINATE` for its unsupported source semantics. This does not claim runtime safety.

## TARGETED_TESTS

- `& .\.venv\Scripts\python.exe -m py_compile` on all seven authorized Python files — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_capture_capacity.py tests/test_original_worker_reindex_planning.py tests/test_cycle_semantics_scenarios.py` — **33 passed**.
- `git diff --check --` on the six changed tracked Python files and new-file `git diff --no-index --check` — no source/test whitespace errors. The report embeds literal diff context lines that contain single-space blank lines.

## FOCUSED_REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_original_worker_full_partial_receipt_optin.py tests/test_original_worker_full_preparation_optin.py tests/test_cycle_semantics_live_installed_partial_claims.py` — **58 passed**.
- No global pytest or active-repository FULL was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Contextor MCP `get_live_events(after_revision=884)` returned two `desktop_watcher` update_file records for `original_worker_reindex_planning.py` and `original_worker_binding.py`, revisions 885 and 886, both status=`UNCHANGED`, resync_required=false. MCP then reported `workspace_sync=verified` for those two files.
- DIRECT_EVIDENCE: Subsequent `desktop_watcher` events advanced the canonical revision to 889: `indexer.py` UPDATED at 887, `scenarios.py` UPDATED at 888, and `test_original_worker_reindex_planning.py` UPDATED at 889. MCP then reported `workspace_sync=verified` for these three files as well as the first two.
- DIRECT_EVIDENCE: At revision 889, `test_cycle_semantics_scenarios.py` remained `workspace_sync=out_of_sync`; the new `test_cycle_semantics_capture_capacity.py` was not yet resolved in the project graph. A bounded event read after revision 889 returned no additional canonical events.
- DIRECT_EVIDENCE: Canonical graph/cycles remained fresh with **16** structural DFS cycles through revision 889; no additional structural cycle appeared in the available count. `cycle_semantics=stale`.
- UNKNOWN: Active LIVE/Desktop/MCP loaded-code adoption of these local changes; no restart or reload was performed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/original_worker_reindex_planning.py`
- `contextor/core/cycle_semantics/original_worker_binding.py`
- `contextor/core/symbol_engine/indexer.py`
- `contextor/core/cycle_semantics/scenarios.py`
- `tests/test_original_worker_reindex_planning.py`
- `tests/test_cycle_semantics_scenarios.py`
- `tests/test_cycle_semantics_capture_capacity.py`

`walkthrough.md` overwritten as report only.

## FULL_DIFFS

### contextor/core/cycle_semantics/original_worker_reindex_planning.py

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_reindex_planning.py b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
index a99a484..6b482e0 100644
--- a/contextor/core/cycle_semantics/original_worker_reindex_planning.py
+++ b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
@@ -18,7 +18,7 @@ from .model_source_closure import compute_cycle_model_source_closures
 from .scc import analyze_import_cycle_topology
 
 
-_MAX_SELECTED = 16
+_MAX_SELECTED = 256
 _READY = "READY_FOR_REINDEX_NON_ATOMIC"
 _VERIFIED = "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
```

### contextor/core/cycle_semantics/original_worker_binding.py

```diff
diff --git a/contextor/core/cycle_semantics/original_worker_binding.py b/contextor/core/cycle_semantics/original_worker_binding.py
index 9bba63e..8dfedcd 100644
--- a/contextor/core/cycle_semantics/original_worker_binding.py
+++ b/contextor/core/cycle_semantics/original_worker_binding.py
@@ -21,7 +21,7 @@ _ACCEPTED_MODES = frozenset({
     "PARSED_FROM_WORKER_READ",
     "CACHE_SHA256_EQUIVALENT",
 })
-_MAX_MODULES = 16
+_MAX_MODULES = 256
 _MAX_SOURCE_BYTES = 2 * 1024 * 1024
 _MAX_TOTAL_BYTES = 32 * 1024 * 1024
```

### contextor/core/symbol_engine/indexer.py

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2790e9e..5ccbbdd 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -1543,6 +1543,10 @@ class RepositoryIndex:
     original_worker_capture_reason: str | None = None
 
 
+_MAX_ORIGINAL_WORKER_CAPTURE_MODULES = 256
+_MAX_ORIGINAL_WORKER_CAPTURE_TOTAL_BYTES = 32 * 1024 * 1024
+
+
 def index_repository(
     root: str,
     excludes: list[str] = None,
@@ -1565,15 +1569,20 @@ def index_repository(
             type(name) is not str or not name
             for name in source_capture_module_ids
         )
-        or len(source_capture_module_ids) > 16
+        or len(source_capture_module_ids)
+        > _MAX_ORIGINAL_WORKER_CAPTURE_MODULES
     ):
-        raise ValueError("source_capture_module_ids must be <=16 module names")
+        raise ValueError(
+            "source_capture_module_ids exceeds bounded module capacity"
+        )
     else:
         selected_captures = source_capture_module_ids
 
-    # At most 16 selected results of 2 MiB each (32 MiB raw payload).
+    # A bounded selected cohort. Its aggregate retained raw-byte budget
+    # is enforced separately from the per-source worker transport limit.
     # This does not bound unrelated indexing memory overhead.
     capture_per_source_max = 2 * 1024 * 1024
+    captured_total_bytes = 0
     captures: dict[str, SourceSnapshot] = {}
     capture_modes: dict[str, str] = {}
     capture_errors: dict[str, str] = {}
@@ -1583,6 +1592,7 @@ def index_repository(
         return capture_per_source_max if module_id in selected_captures else None
 
     def record_capture(result: dict, path: Path) -> None:
+        nonlocal captured_total_bytes
         if not selected_captures:
             return
         module_id = ".".join(path.relative_to(root_path).with_suffix("").parts)
@@ -1620,8 +1630,22 @@ def index_repository(
         ):
             capture_errors[module_id] = "INVALID_WORKER_CAPTURE"
             return
-        captures[module_id] = SourceSnapshot(raw=raw, source_fingerprint=fingerprint)
+        if module_id in captures:
+            capture_errors[module_id] = "DUPLICATE_WORKER_CAPTURE"
+            return
+        if (
+            captured_total_bytes + len(raw)
+            > _MAX_ORIGINAL_WORKER_CAPTURE_TOTAL_BYTES
+        ):
+            capture_errors[module_id] = "CAPTURE_TOTAL_BYTE_LIMIT"
+            return
+
+        captures[module_id] = SourceSnapshot(
+            raw=raw,
+            source_fingerprint=fingerprint,
+        )
         capture_modes[module_id] = mode
+        captured_total_bytes += len(raw)
 
     def capture_result_fields() -> dict[str, object]:
         if not selected_captures:
```

### contextor/core/cycle_semantics/scenarios.py

```diff
diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
index 0959757..04590ec 100644
--- a/contextor/core/cycle_semantics/scenarios.py
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -18,7 +18,7 @@ from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycl
 
 MAX_COMPONENT_ENTRIES = 64
 MAX_CLOSURE_STATEMENTS = 4096
-MAX_CLOSURE_AST_NODES = 16384
+MAX_CLOSURE_AST_NODES = 393216
 
 
 @dataclass(frozen=True)
```

### tests/test_original_worker_reindex_planning.py

```diff
diff --git a/tests/test_original_worker_reindex_planning.py b/tests/test_original_worker_reindex_planning.py
index 7a85a07..eacf062 100644
--- a/tests/test_original_worker_reindex_planning.py
+++ b/tests/test_original_worker_reindex_planning.py
@@ -155,7 +155,7 @@ def test_p1d2e_t04_large_closure_rejected_before_reindex(
     root = _repo(tmp_path)
 
     imports = [b"import b", b"import helper"]
-    for number in range(15):
+    for number in range(255):
         name = f"h{number}"
         (root / f"{name}.py").write_bytes(b"value = 1\n")
         imports.append(f"import {name}".encode("ascii"))
@@ -172,6 +172,55 @@ def test_p1d2e_t04_large_closure_rejected_before_reindex(
     assert plan.selected_module_ids == frozenset()
 
 
+def test_warn_5c_217_module_cohort_remains_verified(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    imports = [b"import b", b"import helper"]
+
+    for number in range(214):
+        name = f"h{number}"
+        (root / f"{name}.py").write_bytes(b"value = 1\n")
+        imports.append(f"import {name}".encode("ascii"))
+
+    (root / "a.py").write_bytes(
+        b"\n".join(imports) + b"\nvalue = 1\n"
+    )
+
+    first, graph = _index_and_graph(root)
+    plan = plan_original_worker_reindex(first, graph)
+
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.reason is None
+    assert len(plan.selected_module_ids) == 217
+
+    second, second_graph = _index_and_graph(
+        root,
+        plan.selected_module_ids,
+    )
+
+    assert second.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert len(second.original_worker_source_snapshots) == 217
+    assert len(second.original_worker_ast_modes) == 217
+
+    verified = _verify(
+        first,
+        graph,
+        plan,
+        second,
+        second_graph,
+    )
+
+    assert verified.status == (
+        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
+    )
+    assert verified.source_modules == tuple(
+        sorted(plan.selected_module_ids)
+    )
+
+
 def test_p1d2e_t05_source_change_between_passes_rejected(
     tmp_path, isolated_dirs,
 ):
```

### tests/test_cycle_semantics_scenarios.py

```diff
diff --git a/tests/test_cycle_semantics_scenarios.py b/tests/test_cycle_semantics_scenarios.py
index 2979b7b..9006b99 100644
--- a/tests/test_cycle_semantics_scenarios.py
+++ b/tests/test_cycle_semantics_scenarios.py
@@ -7,7 +7,6 @@ import pytest
 from contextor.core.cycle_semantics.scenarios import (
     analyze_cycle_scenarios,
     MAX_COMPONENT_ENTRIES,
-    MAX_CLOSURE_AST_NODES,
 )
 
 
@@ -168,11 +167,26 @@ def test_downstream_scc_hazard_not_attributed_to_upstream_scc():
     ]
 
 
-def test_ast_budget_one_large_statement():
-    n = MAX_CLOSURE_AST_NODES + 2
-    literal = ",".join("1" for _ in range(n))
+def test_ast_budget_one_large_statement(monkeypatch):
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.scenarios.MAX_CLOSURE_AST_NODES",
+        256,
+    )
+    literal = ",".join("1" for _ in range(260))
     r = _assess(
         {"a": "import b\nx=[" + literal + "]", "b": "import a"},
         {"a": {"b"}, "b": {"a"}},
     )
     assert r.components[0].reason == "AST_NODE_BUDGET_EXCEEDED"
+
+
+def test_expanded_ast_capacity_does_not_accept_unsupported_source():
+    literal = ",".join("1" for _ in range(17000))
+    r = _assess(
+        {"a": "import b\nx=[" + literal + "]", "b": "import a"},
+        {"a": {"b"}, "b": {"a"}},
+    )
+    component = r.components[0]
+
+    assert component.reason != "AST_NODE_BUDGET_EXCEEDED"
+    assert component.classification == "INDETERMINATE"
```

### tests/test_cycle_semantics_capture_capacity.py

```diff
diff --git a/tests/test_cycle_semantics_capture_capacity.py b/tests/test_cycle_semantics_capture_capacity.py
new file mode 100644
index 0000000..c026574
--- /dev/null
+++ b/tests/test_cycle_semantics_capture_capacity.py
@@ -0,0 +1,82 @@
+"""WARN-5C bounded source capture cohort regression tests."""
+
+from __future__ import annotations
+
+import pytest
+
+from contextor.core.cycle_semantics import (
+    original_worker_binding,
+    original_worker_reindex_planning,
+)
+from contextor.core.symbol_engine import indexer
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def test_t01_module_cap_contracts_are_aligned():
+    assert (
+        original_worker_reindex_planning._MAX_SELECTED
+        == original_worker_binding._MAX_MODULES
+        == indexer._MAX_ORIGINAL_WORKER_CAPTURE_MODULES
+        == 256
+    )
+
+
+def test_t02_over_limit_capture_selection_rejected(tmp_path):
+    selected = frozenset(
+        f"module_{index}" for index in range(257)
+    )
+
+    with pytest.raises(ValueError):
+        indexer.index_repository(
+            str(tmp_path),
+            source_capture_module_ids=selected,
+        )
+
+
+def test_t03_total_byte_budget_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+
+    (root / "a.py").write_bytes(
+        b"value = '" + b"a" * 70 + b"'\n"
+    )
+    (root / "b.py").write_bytes(
+        b"value = '" + b"b" * 70 + b"'\n"
+    )
+
+    monkeypatch.setattr(
+        indexer,
+        "_MAX_ORIGINAL_WORKER_CAPTURE_TOTAL_BYTES",
+        100,
+    )
+
+    result = indexer.index_repository(
+        str(root),
+        source_capture_module_ids=frozenset({"a", "b"}),
+    )
+
+    assert result.original_worker_capture_status == "UNAVAILABLE"
+    assert result.original_worker_capture_reason == (
+        "CAPTURE_TOTAL_BYTE_LIMIT"
+    )
+    assert result.original_worker_source_snapshots == {}
+    assert result.original_worker_ast_modes == {}
+
+
+def test_t04_default_indexing_does_not_capture_sources(
+    tmp_path, isolated_dirs,
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "a.py").write_bytes(b"value = 1\n")
+
+    result = indexer.index_repository(str(root))
+
+    assert result.original_worker_capture_status == "NOT_REQUESTED"
+    assert result.original_worker_source_snapshots == {}
```

## REMAINING_UNKNOWN

- UNKNOWN: Why the Desktop watcher had not synchronized the final two files at the post-change audit point. No cause is assigned from this evidence.
- UNKNOWN: Current active-repository original-worker preparation outcome after these source edits; no FULL was run.
- UNKNOWN: Runtime loaded-code adoption; source workspace state and focused tests do not prove it.
- UNKNOWN: Global pytest outcome; prohibited in this stage.

## FINAL_IMPLEMENTER_OBSERVATION

The literal WARN-5C changes passed 33 targeted and 58 focused regression tests. The mandatory MCP audit preserved a 16-cycle structural count but showed partial workspace synchronization and stale cycle semantics. No architectural GO is claimed. STOP after WARN-5C.
