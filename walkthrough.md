# CONTEXTOR P1D3-WARN-4H — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: Initial/final HEAD `18f5628ef73693dc9e325c8665fd188899c1daee`; initial worktree clean.
- DIRECT_EVIDENCE: Contextor MCP pre-edit resolved `contextor.ui.gui` at revision 875 and reported 16 fresh structural DFS cycles.
- DIRECT_EVIDENCE: The supplied SEARCH block in `gui.py` occurred once. The new test file was absent.

## EXACT SEARCH / REPLACE

- DIRECT_EVIDENCE: Applied only the architect-authored replacement in `contextor/ui/gui.py`; added the supplied test file with exact content.
- DIRECT_EVIDENCE: Literal new-file comparison passed. No facade default, validator, or graph files changed.

## GUI FLAG FORWARDING

- CODE_PATH_PROVED: Desktop `ContextorGUI.analyze` now forwards `cycle_source_preparation_preview=True` and `cycle_partial_source_publication_opt_in=True` to `run_full_analysis_exclusive`.
- CONTRACT_PROVED: T01 executes the GUI task closure and checks those exact kwargs, while excluding `cycle_source_publication_opt_in`.

## REAL FULL / DURABLE RECEIPT / LIVE INSTALLATION

- CONTRACT_PROVED: T02–T04 use isolated synthetic repositories and the existing official LIVE fixture. They check successful FULL publication, matching revision and state ID, durable `CanonicalPartialSCCReceipt`, receipt verification, installed warning projection, and unchanged structural cycles and hard edges.
- DIRECT_EVIDENCE: This was test fixture execution only; no active user's FULL/LIVE operation was invoked.

## MIXED UNKNOWN AND HAZARD CASES

- CONTRACT_PROVED: TWO_PASS yields 2 model PASS and 0 active warning paths; PASS_AND_UNKNOWN and PASS_AND_HAZARD each yield 1 model PASS and 1 active warning path. The Desktop presentation retains the nonaccepted warning.

## FAILED PREPARATION

- CONTRACT_PROVED: T05 injects a second capture failure through the test's monkeypatch; no partial receipt is published, and both warnings remain active.

## ACYCLIC FAST PATH

- CONTRACT_PROVED: T06 checks an acyclic isolated repository: one index call, no second source capture, no partial receipt, and zero structural or active cycle warnings.

## NEW TESTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/ui/gui.py tests/test_cycle_semantics_desktop_full_partial_activation.py` — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_desktop_full_partial_activation.py` — 6 passed; one third-party Authlib deprecation warning.

## FOCUSED REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_desktop_warning_presentation.py tests/test_original_worker_full_partial_receipt_optin.py tests/test_original_worker_full_preparation_optin.py tests/test_cycle_semantics_live_cycle_warning_query.py` — 61 passed; one third-party Authlib deprecation warning.
- `git diff --check` and new-file `git diff --no-index --check` — no whitespace errors.

## POST-CHANGE MCP AUDIT

- DIRECT_EVIDENCE: Contextor MCP `get_module_context` at revision 877 reported `canonical_state=fresh`, `workspace_sync=verified` for both changed files. Graph/cycle families fresh, structural DFS cycle count 16 (unchanged). `cycle_semantics=stale`.
- UNKNOWN: MCP workspace synchronization does not establish active Desktop/backend loaded-code adoption.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_cycle_semantics_desktop_full_partial_activation.py`

`walkthrough.md` overwritten as report only.

## FULL_DIFFS

### contextor/ui/gui.py

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index a90eb6c..f855fad 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1312,6 +1312,8 @@ class ContextorGUI:
                 log=log,
                 progress_callback=progress_callback,
                 is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
+                cycle_source_preparation_preview=True,
+                cycle_partial_source_publication_opt_in=True,
             )
             from contextor.ui.cycle_warning_presentation import (
                 filter_installed_desktop_cycle_errors,
```

### tests/test_cycle_semantics_desktop_full_partial_activation.py

```diff
diff --git a/tests/test_cycle_semantics_desktop_full_partial_activation.py b/tests/test_cycle_semantics_desktop_full_partial_activation.py
new file mode 100644
index 0000000..8298119
--- /dev/null
+++ b/tests/test_cycle_semantics_desktop_full_partial_activation.py
@@ -0,0 +1,290 @@
+"""WARN-4H: Desktop FULL activates existing partial SCC publication.
+
+All real analyses use synthetic temporary repositories and isolated LIVE.
+No production repository or existing LIVE service is contacted.
+"""
+
+from __future__ import annotations
+
+import copy
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.core.api.facade as facade_module
+from contextor.core.analysis.full_analysis_coordinator import (
+    run_full_analysis_exclusive,
+)
+from contextor.core.cycle_semantics.partial_scc_publication import (
+    CanonicalPartialSCCReceipt,
+    verify_co_published_partial_scc_preparation,
+)
+from contextor.ui import gui
+from contextor.ui.gui import ContextorGUI
+from contextor.ui.cycle_warning_presentation import (
+    filter_installed_desktop_cycle_errors,
+)
+from tests.test_original_worker_official_full_live_publication import (
+    _official_live,
+)
+from tests.test_original_worker_full_partial_receipt_optin import (
+    _persisted,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_UNKNOWN,
+    PASS_AND_HAZARD,
+    TWO_PASS,
+    _repo,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _desktop_full(root):
+    return run_full_analysis_exclusive(
+        str(root),
+        owner="desktop_analysis",
+        cycle_source_preparation_preview=True,
+        cycle_partial_source_publication_opt_in=True,
+    )
+
+
+def _cycle_errors(errors):
+    return [
+        error for error in errors
+        if error.kind == "ArchitectureCycle"
+    ]
+
+
+def test_t01_gui_passes_both_exact_optins(
+    tmp_path, monkeypatch,
+):
+    """Execute the actual GUI task closure without a Tk window."""
+    calls = []
+    results = []
+
+    controller = SimpleNamespace(
+        repo_path_var=SimpleNamespace(
+            get=lambda: str(tmp_path),
+        ),
+        root=object(),
+        progress_bar=SimpleNamespace(is_cancelled=False),
+        log_box=None,
+        cpu_indicator=None,
+        stop_btn=None,
+        _busy_buttons=lambda: (),
+        _live_recovery_incident=lambda _path: None,
+    )
+
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect",
+        lambda _path: None,
+    )
+
+    def fake_full(path, **kwargs):
+        calls.append((path, kwargs))
+        return [], SimpleNamespace(
+            live_publish_status="not_attempted",
+        )
+
+    def fake_progress(root, bar, task, **kwargs):
+        results.append(task())
+        return "synthetic-task-completed"
+
+    monkeypatch.setattr(
+        gui, "run_full_analysis_exclusive", fake_full,
+    )
+    monkeypatch.setattr(
+        gui, "run_with_progress", fake_progress,
+    )
+
+    ContextorGUI.analyze(controller)
+
+    assert controller._full_analysis_done == (
+        "synthetic-task-completed"
+    )
+    assert len(calls) == 1
+    assert len(results) == 1
+
+    path, kwargs = calls[0]
+
+    assert path == str(tmp_path.resolve())
+    assert kwargs["owner"] == "desktop_analysis"
+    assert kwargs["cycle_source_preparation_preview"] is True
+    assert kwargs["cycle_partial_source_publication_opt_in"] is True
+    assert "cycle_source_publication_opt_in" not in kwargs
+    assert kwargs["is_cancelled"]() is False
+
+    assert results[0][0] == []
+
+
+@pytest.mark.parametrize(
+    "sources,model_pass,active",
+    [
+        (TWO_PASS, 2, 0),
+        (PASS_AND_UNKNOWN, 1, 1),
+        (PASS_AND_HAZARD, 1, 1),
+    ],
+)
+def test_t02_t04_real_full_publishes_partial_to_live(
+    tmp_path, isolated_dirs, monkeypatch,
+    sources, model_pass, active,
+):
+    """FULL -> durable partial receipt -> LIVE -> Desktop messages."""
+    root = _repo(tmp_path, sources)
+
+    with _official_live(
+        root, monkeypatch,
+    ) as (client, server, identity, calls):
+
+        errors, result = _desktop_full(root)
+
+        state, metadata = _persisted(root)
+
+        assert result.live_publish_status == "success"
+        assert result.live_publish_revision == metadata.revision
+        assert result.live_publish_expected_state_id == (
+            metadata.state_id
+        )
+        assert result.live_publish_service_instance_id == (
+            server.endpoint.service_instance_id
+        )
+
+        assert metadata.repo_id == identity.repo_id
+        assert calls == [root.resolve()]
+
+        receipt = state.cycle_partial_source_publication
+
+        assert type(receipt) is CanonicalPartialSCCReceipt
+        assert verify_co_published_partial_scc_preparation(
+            state,
+            revision=metadata.revision,
+            state_id=metadata.state_id,
+            repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+
+        assert state.cycle_source_publication is None
+        assert len(state.cycles) == 2
+        assert len(_cycle_errors(errors)) == 2
+
+        original_cycles = copy.deepcopy(state.cycles)
+        original_edges = copy.deepcopy(
+            state.dependency_graph.hard_edges
+        )
+
+        view = client.get_installed_cycle_warning_projection()
+
+        assert view["status"] == "ok"
+        assert view["revision"] == metadata.revision
+        assert view["structural_count"] == 2
+        assert view["model_pass_count"] == model_pass
+        assert view["active_warning_count"] == active
+
+        displayed = filter_installed_desktop_cycle_errors(
+            errors, result, str(root),
+        )
+
+        assert len(_cycle_errors(displayed)) == active
+        assert len(_cycle_errors(errors)) == 2
+        assert state.cycles == original_cycles
+        assert state.dependency_graph.hard_edges == original_edges
+
+
+def test_t05_failed_second_capture_preserves_all_warnings(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    """A failed evidence pass must not silently accept any cycle."""
+    root = _repo(tmp_path, TWO_PASS)
+
+    original_index = facade_module.index_repository
+
+    def missing_capture(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            raise RuntimeError("synthetic second-pass failure")
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        missing_capture,
+    )
+
+    with _official_live(
+        root, monkeypatch,
+    ) as (client, server, identity, calls):
+
+        errors, result = _desktop_full(root)
+        state, metadata = _persisted(root)
+
+        assert result.live_publish_status == "success"
+        assert result.cycle_source_preparation_preview.status == (
+            "UNAVAILABLE"
+        )
+        assert state.cycle_partial_source_publication is None
+        assert len(state.cycles) == 2
+
+        view = client.get_installed_cycle_warning_projection()
+
+        assert view["status"] == "ok"
+        assert view["structural_count"] == 2
+        assert view["model_pass_count"] == 0
+        assert view["active_warning_count"] == 2
+
+        displayed = filter_installed_desktop_cycle_errors(
+            errors, result, str(root),
+        )
+
+        assert len(_cycle_errors(displayed)) == 2
+        assert len(_cycle_errors(errors)) == 2
+
+
+def test_t06_acyclic_full_skips_second_index(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    """Enabling the opt-in must not reindex an acyclic repository."""
+    root = _repo(
+        tmp_path,
+        {"a": "value = 1\n"},
+    )
+
+    original_index = facade_module.index_repository
+    selections = []
+
+    def observed_index(*args, **kwargs):
+        selections.append(
+            kwargs.get("source_capture_module_ids")
+        )
+        return original_index(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "index_repository",
+        observed_index,
+    )
+
+    with _official_live(
+        root, monkeypatch,
+    ) as (client, server, identity, calls):
+
+        errors, result = _desktop_full(root)
+        state, metadata = _persisted(root)
+
+        assert result.live_publish_status == "success"
+        assert state.cycles == []
+        assert state.cycle_partial_source_publication is None
+        assert selections == [None]
+
+        view = client.get_installed_cycle_warning_projection()
+
+        assert view["status"] == "ok"
+        assert view["structural_count"] == 0
+        assert view["model_pass_count"] == 0
+        assert view["active_warning_count"] == 0
+
+        assert filter_installed_desktop_cycle_errors(
+            errors, result, str(root),
+        ) is errors
```

## CONTRACT_CONFLICTS

None observed in the literal anchor, compilation, or focused tests.

## REMAINING UNKNOWN

- UNKNOWN: Active Desktop/backend loaded-code adoption; no restart occurred.
- UNKNOWN: Global pytest result; prohibited in this stage.
- UNKNOWN: Semantic cycle family is stale in MCP.

## FINAL IMPLEMENTER OBSERVATION

The literal WARN-4H change passed the new isolated tests and specified focused regressions. Structural DFS cycle count remained 16. Architectural acceptance remains with ChatGPT. STOP after WARN-4H.
