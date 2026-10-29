# CONTEXTOR P1D3-WARN-4G — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: Initial and final HEAD: `898d5eb5b8186c0e924224a043d9874137ce890a`. Initial worktree clean.
- DIRECT_EVIDENCE: Contextor MCP `get_file_edit_context` resolved `contextor.ui.gui` at revision 872. Structural DFS cycle count: 16, fresh.
- DIRECT_EVIDENCE: Both new files were absent; the specified SEARCH in `gui.py` occurred exactly once.

## SEARCH / REPLACE RESULT

- DIRECT_EVIDENCE: Applied the exact architect-authored `gui.py` replacement; added both new files with supplied content.
- DIRECT_EVIDENCE: Literal content comparison for both new files passed. No other production or test files edited.

## NEW TEST RESULTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/ui/gui.py contextor/ui/cycle_warning_presentation.py tests/test_cycle_semantics_desktop_warning_presentation.py` — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_desktop_warning_presentation.py` — 13 passed, one third-party Authlib deprecation warning.

## FOCUSED REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_live_cycle_warning_query.py tests/test_cycle_semantics_live_warning_diagnostics_summary.py tests/test_gui_live_startup.py` — 69 passed, one third-party Authlib deprecation warning.
- `git diff --check` and new-file `git diff --no-index --check` — no whitespace errors.

## DESKTOP PRESENTATION CONTRACT

- CODE_PATH_PROVED: Desktop `ContextorGUI.analyze` invokes `filter_installed_desktop_cycle_errors` before returning errors to its success callback.
- CONTRACT_PROVED: T01–T03 filter only installed MODEL_PASS cycle errors, retaining UNKNOWN/HAZARD cycles and unrelated errors. Canonical `state.cycles` remains two cycles in the test fixtures.
- CONTRACT_PROVED: T04 retains an error with a noncanonical message even when its nodes match a model PASS path.

## FAIL-CLOSED CASES

- CONTRACT_PROVED: T05–T07 retain all errors for unpublished, wrong revision, or wrong service identity.
- CONTRACT_PROVED: T08–T09 reject invalid path partition or repository identity.
- CONTRACT_PROVED: T10–T12 retain errors for unavailable owner, failed query, or no cycle error; the no-cycle path does not query LIVE.

## MCP POST-CHANGE AUDIT

- DIRECT_EVIDENCE: Contextor MCP `get_module_context` at revision 875 reported `canonical_state=fresh`, `workspace_sync=verified` for all three changed files. Graph and cycle families were fresh. Structural DFS cycle count remained **16**; no new structural hard-edge cycle was observed in this count.
- DIRECT_EVIDENCE: `cycle_semantics=stale`. MCP workspace sync does not prove active loaded-code adoption.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `contextor/ui/cycle_warning_presentation.py`
- `tests/test_cycle_semantics_desktop_warning_presentation.py`

`walkthrough.md` overwritten as report only.

## FULL_DIFFS

### contextor/ui/gui.py

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 16d138c..a90eb6c 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1313,6 +1313,14 @@ class ContextorGUI:
                 progress_callback=progress_callback,
                 is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
             )
+            from contextor.ui.cycle_warning_presentation import (
+                filter_installed_desktop_cycle_errors,
+            )
+            errors = filter_installed_desktop_cycle_errors(
+                errors,
+                analysis_result,
+                path,
+            )
             return errors, analysis_result
 
         def on_success(outcome):
```

### contextor/ui/cycle_warning_presentation.py

```diff
diff --git a/contextor/ui/cycle_warning_presentation.py b/contextor/ui/cycle_warning_presentation.py
new file mode 100644
index 0000000..a1a810e
--- /dev/null
+++ b/contextor/ui/cycle_warning_presentation.py
@@ -0,0 +1,224 @@
+"""Fail-closed Desktop presentation of installed cycle warnings.
+
+This module only filters presentation errors, never canonical cycles,
+validation evidence, LIVE state, receipts or structural diagnostics.
+A published generation with matching owner identity is mandatory.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Any
+
+from contextor.core.cycle_semantics.cycle_warning_projection import (
+    InstalledCycleWarningProjection,
+)
+from contextor.core.cycle_semantics.cycle_warning_transitions import (
+    _validated_states,
+)
+from contextor.core.cycle_semantics.live_cycle_warning_query import (
+    _AUTHORITY as _PROJECTION_AUTHORITY,
+    _BINDING as _PROJECTION_BINDING,
+)
+from contextor.core.domain.validation import ValidationError
+from contextor.core.repository_identity import read_repository_identity
+
+
+_FIELDS = frozenset({
+    "status",
+    "binding_state",
+    "revision",
+    "state_id",
+    "repo_id",
+    "root_path",
+    "service_instance_id",
+    "process_start_identity",
+    "activity_epoch",
+    "graph_sha256",
+    "structural_paths",
+    "model_pass_paths",
+    "active_warning_paths",
+    "structural_count",
+    "model_pass_count",
+    "active_warning_count",
+    "authority",
+})
+
+
+def _accepted_paths(
+    result: Any,
+    repo_path: str,
+    report: Any,
+) -> frozenset[tuple[str, ...]] | None:
+    """Validate the published generation before accepting any cycle path."""
+    if type(report) is not dict or set(report) != _FIELDS:
+        return None
+
+    if getattr(result, "live_publish_status", None) != "success":
+        return None
+
+    revision = getattr(result, "live_publish_revision", None)
+    expected_revision = getattr(
+        result, "live_publish_expected_revision", None
+    )
+    expected_state_id = getattr(
+        result, "live_publish_expected_state_id", None
+    )
+    expected_service = getattr(
+        result, "live_publish_service_instance_id", None
+    )
+    expected_process = getattr(
+        result, "live_publish_process_start_identity", None
+    )
+
+    if (
+        type(revision) is not int
+        or revision < 1
+        or type(expected_revision) is not int
+        or revision != expected_revision
+        or type(expected_state_id) is not str
+        or not expected_state_id
+        or type(expected_service) is not str
+        or not expected_service
+        or type(expected_process) is not str
+        or not expected_process
+    ):
+        return None
+
+    if (
+        report["status"] != "ok"
+        or report["binding_state"] != _PROJECTION_BINDING
+        or report["authority"] != _PROJECTION_AUTHORITY
+        or type(report["revision"]) is not int
+        or report["revision"] != revision
+        or report["state_id"] != expected_state_id
+        or report["service_instance_id"] != expected_service
+        or report["process_start_identity"] != expected_process
+        or type(report["activity_epoch"]) is not str
+        or not report["activity_epoch"]
+    ):
+        return None
+
+    identity = read_repository_identity(repo_path)
+    if identity is None:
+        return None
+
+    if (
+        report["repo_id"] != identity.repo_id
+        or Path(report["root_path"]).resolve()
+        != Path(identity.root_path).resolve()
+        or Path(repo_path).resolve()
+        != Path(identity.root_path).resolve()
+    ):
+        return None
+
+    digest = report["graph_sha256"]
+    if (
+        type(digest) is not str
+        or len(digest) != 64
+        or any(char not in "0123456789abcdef" for char in digest)
+    ):
+        return None
+
+    for paths_field, count_field in (
+        ("structural_paths", "structural_count"),
+        ("model_pass_paths", "model_pass_count"),
+        ("active_warning_paths", "active_warning_count"),
+    ):
+        paths = report[paths_field]
+        count = report[count_field]
+        if (
+            type(paths) is not tuple
+            or type(count) is not int
+            or count != len(paths)
+        ):
+            return None
+
+    projection = InstalledCycleWarningProjection(
+        status="FRESH",
+        reason=None,
+        revision=revision,
+        structural_paths=report["structural_paths"],
+        model_pass_paths=report["model_pass_paths"],
+        active_warning_paths=report["active_warning_paths"],
+    )
+
+    if _validated_states(projection) is None:
+        return None
+
+    return frozenset(report["model_pass_paths"])
+
+
+def filter_installed_desktop_cycle_errors(
+    errors: Any,
+    analysis_result: Any,
+    repo_path: str,
+) -> Any:
+    """Filter only proven MODEL_PASS cycle errors from Desktop messages.
+
+    The caller runs this after full analysis, on the worker thread.
+    Any missing or mismatched evidence preserves the original errors.
+    """
+    if type(errors) is not list or not errors:
+        return errors
+
+    if not any(
+        type(error) is ValidationError
+        and error.kind == "ArchitectureCycle"
+        for error in errors
+    ):
+        return errors
+
+    if getattr(analysis_result, "live_publish_status", None) != "success":
+        return errors
+
+    try:
+        from contextor.core.live_state import connect
+
+        client = connect(Path(repo_path))
+        if client is None:
+            return errors
+
+        report = client.request(
+            "get_installed_cycle_warning_projection",
+            timeout=2.0,
+        )
+
+        accepted = _accepted_paths(
+            analysis_result,
+            repo_path,
+            report,
+        )
+
+        if accepted is None or not accepted:
+            return errors
+
+        filtered = []
+        for error in errors:
+            if (
+                type(error) is ValidationError
+                and error.kind == "ArchitectureCycle"
+                and type(error.nodes) in (list, tuple)
+                and all(
+                    type(node) is str and node
+                    for node in error.nodes
+                )
+            ):
+                path = tuple(error.nodes)
+                expected_message = (
+                    "Cyclic dependency detected in architecture: "
+                    + " -> ".join(path)
+                )
+                if (
+                    path in accepted
+                    and error.message == expected_message
+                ):
+                    continue
+
+            filtered.append(error)
+
+        return filtered
+
+    except Exception:
+        # A presentation query must not hide diagnostics or fail analysis.
+        return errors
```

### tests/test_cycle_semantics_desktop_warning_presentation.py

```diff
diff --git a/tests/test_cycle_semantics_desktop_warning_presentation.py b/tests/test_cycle_semantics_desktop_warning_presentation.py
new file mode 100644
index 0000000..976de70
--- /dev/null
+++ b/tests/test_cycle_semantics_desktop_warning_presentation.py
@@ -0,0 +1,270 @@
+"""WARN-4G: Desktop only hides exactly installed MODEL_PASS cycle errors."""
+
+from __future__ import annotations
+
+from types import SimpleNamespace
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.domain.validation import ValidationError
+from contextor.ui.cycle_warning_presentation import (
+    _accepted_paths,
+    filter_installed_desktop_cycle_errors,
+)
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture,
+    _owner,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    PASS_AND_UNKNOWN,
+    PASS_AND_HAZARD,
+    TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _analysis_result(metadata, server):
+    return SimpleNamespace(
+        live_publish_status="success",
+        live_publish_revision=metadata.revision,
+        live_publish_expected_revision=metadata.revision,
+        live_publish_expected_state_id=metadata.state_id,
+        live_publish_service_instance_id=(
+            server.endpoint.service_instance_id
+        ),
+        live_publish_process_start_identity=(
+            server.endpoint.process_start_identity
+        ),
+    )
+
+
+def _cycle(path):
+    return ValidationError(
+        kind="ArchitectureCycle",
+        message=(
+            "Cyclic dependency detected in architecture: "
+            + " -> ".join(path)
+        ),
+        nodes=list(path),
+    )
+
+
+def _other():
+    return ValidationError(
+        kind="ForbiddenDependency",
+        message="Unrelated architecture error",
+        nodes=["a", "b"],
+    )
+
+
+def _connect(monkeypatch, client):
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect",
+        lambda _root: client,
+    )
+
+
+@pytest.mark.parametrize("sources,expected_remaining", [
+    (TWO_PASS, 0),
+    (PASS_AND_UNKNOWN, 1),
+    (PASS_AND_HAZARD, 1),
+])
+def test_t01_t03_real_owner_acceptance_filters_only_pass(
+    tmp_path, isolated_dirs, monkeypatch,
+    sources, expected_remaining,
+):
+    root, state, metadata = _fixture(tmp_path, sources)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        errors = [_cycle(path) for path in state.cycles]
+        other = _other()
+        errors.append(other)
+
+        result = filter_installed_desktop_cycle_errors(
+            errors,
+            _analysis_result(metadata, server),
+            str(root),
+        )
+
+        remaining_cycles = [
+            item for item in result
+            if item.kind == "ArchitectureCycle"
+        ]
+
+        assert len(remaining_cycles) == expected_remaining
+        assert result[-1] is other
+        assert len(errors) == 3
+        assert len(state.cycles) == 2
+
+
+def test_t04_noncanonical_message_is_not_removed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        invalid = _cycle(state.cycles[0])
+        invalid.message = "Unrelated warning with same nodes"
+
+        result = filter_installed_desktop_cycle_errors(
+            [invalid],
+            _analysis_result(metadata, server),
+            str(root),
+        )
+
+        assert result == [invalid]
+
+
+def test_t05_unpublished_full_preserves_all_errors(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        errors = [_cycle(path) for path in state.cycles]
+        publication = _analysis_result(metadata, server)
+        publication.live_publish_status = "pending_verification"
+
+        assert filter_installed_desktop_cycle_errors(
+            errors, publication, str(root)
+        ) is errors
+
+
+def test_t06_wrong_revision_preserves_all_errors(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        errors = [_cycle(path) for path in state.cycles]
+        publication = _analysis_result(metadata, server)
+        publication.live_publish_revision += 1
+
+        assert filter_installed_desktop_cycle_errors(
+            errors, publication, str(root)
+        ) is errors
+
+
+def test_t07_wrong_service_preserves_all_errors(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+        errors = [_cycle(path) for path in state.cycles]
+        publication = _analysis_result(metadata, server)
+        publication.live_publish_service_instance_id = "foreign"
+
+        assert filter_installed_desktop_cycle_errors(
+            errors, publication, str(root)
+        ) is errors
+
+
+def test_t08_invalid_partition_never_suppresses(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        report = client.get_installed_cycle_warning_projection()
+        report["active_warning_paths"] = report["model_pass_paths"]
+
+        assert _accepted_paths(
+            _analysis_result(metadata, server),
+            str(root),
+            report,
+        ) is None
+
+
+def test_t09_wrong_repository_never_suppresses(
+    tmp_path, isolated_dirs,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        report = client.get_installed_cycle_warning_projection()
+        report["repo_id"] = "foreign-repository"
+
+        assert _accepted_paths(
+            _analysis_result(metadata, server),
+            str(root),
+            report,
+        ) is None
+
+
+def test_t10_missing_owner_preserves_all_errors(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect",
+        lambda _root: None,
+    )
+
+    errors = [_cycle(path) for path in state.cycles]
+
+    assert filter_installed_desktop_cycle_errors(
+        errors,
+        SimpleNamespace(live_publish_status="success"),
+        str(root),
+    ) is errors
+
+
+def test_t11_query_failure_preserves_all_errors(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    class FailingClient:
+        def request(self, *_args, **_kwargs):
+            raise RuntimeError("unavailable")
+
+    _connect(monkeypatch, FailingClient())
+    errors = [_cycle(path) for path in state.cycles]
+
+    with _owner(state, metadata) as (server, client):
+        assert filter_installed_desktop_cycle_errors(
+            errors,
+            _analysis_result(metadata, server),
+            str(root),
+        ) is errors
+
+
+def test_t12_no_cycles_does_not_query_live(
+    tmp_path, monkeypatch,
+):
+    def forbidden(_root):
+        raise AssertionError("LIVE must not be queried")
+
+    monkeypatch.setattr(
+        "contextor.core.live_state.connect",
+        forbidden,
+    )
+
+    errors = [_other()]
+
+    assert filter_installed_desktop_cycle_errors(
+        errors,
+        SimpleNamespace(live_publish_status="success"),
+        str(tmp_path),
+    ) is errors
+
+
+def test_t13_presenter_is_connected_to_desktop_full_scan():
+    import inspect
+    from contextor.ui.gui import ContextorGUI
+
+    source = inspect.getsource(ContextorGUI.analyze)
+
+    assert "filter_installed_desktop_cycle_errors(" in source
+    assert "return errors, analysis_result" in source
```

## REMAINING UNKNOWN

- UNKNOWN: Active loaded-code adoption; no backend or Desktop restart was performed.
- UNKNOWN: Global pytest outcome; the suite was not run.
- UNKNOWN: Semantic cycle family remains stale in MCP.

## FINAL IMPLEMENTER OBSERVATION

WARN-4G's literal local implementation passed the new test and specified focused regressions. This is source and isolated test evidence; architectural acceptance remains with ChatGPT. STOP after WARN-4G.
