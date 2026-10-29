# CONTEXTOR P1D3-WARN-4F — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `a5b8d69a07323dc486014fee2f293915d5281c3c`; initial worktree clean.
- DIRECT_EVIDENCE: Contextor MCP pre-edit resolved `contextor.core.live_state.ipc`, revision 869, structural DFS cycle count 16, fresh.
- DIRECT_EVIDENCE: Both new authorized files were absent. The specified `ipc.py` SEARCH block occurred exactly once.

## FILES_CHANGED

- `contextor/core/live_state/ipc.py`
- `contextor/core/cycle_semantics/live_warning_diagnostics_summary.py`
- `tests/test_cycle_semantics_live_warning_diagnostics_summary.py`

`walkthrough.md` overwritten as report only.

## EXACT SEARCH / REPLACE

- DIRECT_EVIDENCE: Replaced the unique specified diagnostics query block in `ipc.py` with the architect-authored block. Added the supplied source and test bodies.
- DIRECT_EVIDENCE: An initial patch construction stripped the leading indentation from `try:`; it was restored to the specified text before compilation.
- CODE_PATH_PROVED: The projection returns the original summary when its authority or state validation fails.

## NEW TEST RESULTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/live_state/ipc.py contextor/core/cycle_semantics/live_warning_diagnostics_summary.py tests/test_cycle_semantics_live_warning_diagnostics_summary.py` — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_live_warning_diagnostics_summary.py` — 15 passed.

## FOCUSED REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_live_cycle_warning_query.py tests/test_cycle_semantics_live_warning_transition_checkpoint.py tests/test_cycle_semantics_mcp_live_warning_view.py tests/test_mcp_diagnostics.py` — 114 passed; one third-party Authlib deprecation warning.
- `git diff --check` and new-file `git diff --no-index --check` — no whitespace errors.

## MODEL_PASS / ACTIVE ATTENTION CHECKS

- CONTRACT_PROVED: T01–T03 show mixed PASS/UNKNOWN and PASS/HAZARD keep one active warning; TWO_PASS has two model PASS paths and zero active warnings.
- CONTRACT_PROVED: T04–T05 show missing or invalid partial receipts keep two active warnings.
- CONTRACT_PROVED: T06–T07 show syntax errors and name collisions still require attention.
- CONTRACT_PROVED: T14 checks narrow MCP transport; T15 checks repeated queries leave cycles, hard edges, events and activity sequence unchanged.

## STALE / INVALID AUTHORITY CHECKS

- CONTRACT_PROVED: T08–T09 preserve stale structural availability. T10–T11 preserve raw warnings under degraded recovery or incomplete authority. T12–T13 reject revision and count mismatches.

## POST-CHANGE MCP AUDIT

- DIRECT_EVIDENCE: `get_file_edit_context` resolved all three changed modules at revision 871 with no warnings.
- DIRECT_EVIDENCE: `get_module_context` at revision 872 reported `workspace_sync=verified` and `canonical_state=fresh` for all three files; graph and cycles fresh; structural DFS cycle count 16.
- DIRECT_EVIDENCE: `cycle_semantics=stale`.

## FULL_DIFFS

### contextor/core/live_state/ipc.py

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 277ff93..ed4976f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2590,6 +2590,30 @@ class CanonicalLiveServer:
                         query_kind,
                         dict(payload),
                     )
+
+                    if (
+                        query_kind == "diagnostics_summary"
+                        and not self._stop.is_set()
+                        and self._pending_recovery_certificate is None
+                        and not self._recovery_release_degraded
+                    ):
+                        try:
+                            from contextor.core.cycle_semantics.live_warning_diagnostics_summary import (
+                                project_locked_warning_diagnostics_summary,
+                            )
+                            result = project_locked_warning_diagnostics_summary(
+                                result,
+                                self._owner_cycle_warning_report_locked(),
+                                canonical_revision=self._revision,
+                                activity_epoch=self._activity_epoch,
+                                authority_identity=self._authority_identity,
+                            )
+                        except Exception:
+                            # Never let an optional warning projection
+                            # invalidate the canonical diagnostics query.
+                            # Preserve the original structural warning count.
+                            pass
+
                 except Exception as exc:
                     return {
                         "status": "error",
```

### contextor/core/cycle_semantics/live_warning_diagnostics_summary.py

```diff
diff --git a/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
new file mode 100644
index 0000000..b8aa88a
--- /dev/null
+++ b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
@@ -0,0 +1,198 @@
+"""Warning-aware diagnostics summary for one installed LIVE generation.
+
+Canonical structural cycle counts are preserved. Only a validated,
+owner-captured static-model acceptance partition can reduce active
+cycle warnings. This does not establish runtime execution safety.
+
+This pure function does not authenticate the caller or hold a lock.
+The LIVE owner must invoke it while holding its canonical state lock.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from typing import Any
+
+from .cycle_warning_projection import InstalledCycleWarningProjection
+from .cycle_warning_transitions import _validated_states
+from .live_cycle_warning_query import (
+    _AUTHORITY as _PROJECTION_AUTHORITY,
+    _BINDING as _PROJECTION_BINDING,
+)
+
+
+_IDENTITY_KEYS = (
+    "repo_id",
+    "root_path",
+    "service_instance_id",
+    "process_start_identity",
+)
+
+_PROJECTION_FIELDS = frozenset({
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
+_WARNING_SEMANTICS = (
+    "INSTALLED_STATIC_MODEL_ACCEPTANCE_NOT_RUNTIME_SAFETY"
+)
+
+
+def _nonnegative_count(value: Any) -> bool:
+    return value is None or (
+        type(value) is int and value >= 0
+    )
+
+
+def project_locked_warning_diagnostics_summary(
+    summary: Any,
+    warning_report: Any,
+    *,
+    canonical_revision: int,
+    activity_epoch: str,
+    authority_identity: Mapping[str, Any],
+) -> Any:
+    """Return an additive warning-aware summary, or unchanged original.
+
+    Invalid evidence never suppresses a structural cycle warning.
+    Structural evidence and source summary objects are never mutated.
+    """
+    if type(summary) is not dict:
+        return summary
+
+    try:
+        if (
+            type(canonical_revision) is not int
+            or canonical_revision < 1
+            or type(activity_epoch) is not str
+            or not activity_epoch
+            or not isinstance(authority_identity, Mapping)
+            or type(warning_report) is not dict
+            or set(warning_report) != _PROJECTION_FIELDS
+        ):
+            return summary
+
+        if (
+            warning_report["status"] != "ok"
+            or warning_report["binding_state"] != _PROJECTION_BINDING
+            or warning_report["authority"] != _PROJECTION_AUTHORITY
+            or type(warning_report["revision"]) is not int
+            or warning_report["revision"] != canonical_revision
+            or warning_report["activity_epoch"] != activity_epoch
+        ):
+            return summary
+
+        if any(
+            type(authority_identity.get(key)) is not str
+            or not authority_identity[key]
+            or warning_report[key] != authority_identity[key]
+            for key in _IDENTITY_KEYS
+        ):
+            return summary
+
+        if (
+            type(warning_report["state_id"]) is not str
+            or not warning_report["state_id"]
+            or type(warning_report["graph_sha256"]) is not str
+            or len(warning_report["graph_sha256"]) != 64
+            or any(
+                char not in "0123456789abcdef"
+                for char in warning_report["graph_sha256"]
+            )
+        ):
+            return summary
+
+        cycles = summary.get("cycles")
+        syntax = summary.get("syntax_errors")
+        collisions = summary.get("name_collisions")
+
+        if (
+            type(cycles) is not dict
+            or type(syntax) is not dict
+            or type(collisions) is not dict
+            or cycles.get("availability") != "fresh"
+            or type(cycles.get("count")) is not int
+            or cycles["count"] < 0
+            or type(summary.get("attention_required")) is not bool
+            or not _nonnegative_count(syntax.get("count"))
+            or not _nonnegative_count(collisions.get("count"))
+        ):
+            return summary
+
+        structural = warning_report["structural_paths"]
+        accepted = warning_report["model_pass_paths"]
+        active = warning_report["active_warning_paths"]
+
+        for field, paths in (
+            ("structural_count", structural),
+            ("model_pass_count", accepted),
+            ("active_warning_count", active),
+        ):
+            if (
+                type(paths) is not tuple
+                or type(warning_report[field]) is not int
+                or warning_report[field] < 0
+                or warning_report[field] != len(paths)
+            ):
+                return summary
+
+        if warning_report["structural_count"] != cycles["count"]:
+            return summary
+
+        projection = InstalledCycleWarningProjection(
+            status="FRESH",
+            reason=None,
+            revision=canonical_revision,
+            structural_paths=structural,
+            model_pass_paths=accepted,
+            active_warning_paths=active,
+        )
+
+        if _validated_states(projection) is None:
+            return summary
+
+        active_count = warning_report["active_warning_count"]
+
+        result = dict(summary)
+        result["cycles"] = {
+            **cycles,
+            "active_warning_count": active_count,
+            "model_pass_count": warning_report["model_pass_count"],
+            "warning_availability": "fresh",
+            "warning_semantics": _WARNING_SEMANTICS,
+        }
+        result["attention_required"] = any(
+            type(value) is int and value > 0
+            for value in (
+                syntax["count"],
+                collisions["count"],
+                active_count,
+            )
+        )
+        return result
+
+    except (
+        AttributeError,
+        KeyError,
+        TypeError,
+        ValueError,
+        IndexError,
+        RecursionError,
+        OverflowError,
+    ):
+        return summary
```

### tests/test_cycle_semantics_live_warning_diagnostics_summary.py

```diff
diff --git a/tests/test_cycle_semantics_live_warning_diagnostics_summary.py b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
new file mode 100644
index 0000000..0bab1ec
--- /dev/null
+++ b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
@@ -0,0 +1,319 @@
+"""WARN-4F: installed warning eligibility controls MCP attention only."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.diagnostics_projection import (
+    diagnostics_summary_for_state,
+)
+from contextor.core.live_state.runtime import (
+    _repository_canonical_query_handler,
+)
+from contextor.core.cycle_semantics.live_warning_diagnostics_summary import (
+    project_locked_warning_diagnostics_summary,
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
+def _install_query_handler(server):
+    server._canonical_query_handler = _repository_canonical_query_handler
+
+
+def _summary(client):
+    response = client.canonical_query(
+        "diagnostics_summary",
+        payload={},
+    )
+    assert response["status"] == "ok"
+    return response["result"]
+
+
+@pytest.mark.parametrize("sources,accepted,active", [
+    (PASS_AND_UNKNOWN, 1, 1),
+    (PASS_AND_HAZARD, 1, 1),
+    (TWO_PASS, 2, 0),
+])
+def test_t01_t03_installed_partial_scc_controls_attention(
+    tmp_path, isolated_dirs, sources, accepted, active,
+):
+    _, state, metadata = _fixture(tmp_path, sources)
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+
+        original = diagnostics_summary_for_state(state)
+        structural = copy.deepcopy(state.cycles)
+        events = copy.deepcopy(server._events)
+
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] == 2
+        assert summary["cycles"]["model_pass_count"] == accepted
+        assert summary["cycles"]["active_warning_count"] == active
+        assert summary["cycles"]["warning_availability"] == "fresh"
+        assert summary["attention_required"] is (active > 0)
+
+        assert original["cycles"]["count"] == 2
+        assert "active_warning_count" not in original["cycles"]
+        assert state.cycles == structural
+        assert server._events == events
+
+
+def test_t04_no_partial_receipt_preserves_all_warnings(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(
+        tmp_path, TWO_PASS, partial=False,
+    )
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] == 2
+        assert summary["cycles"]["model_pass_count"] == 0
+        assert summary["cycles"]["active_warning_count"] == 2
+        assert summary["attention_required"] is True
+
+
+def test_t05_invalid_partial_receipt_cannot_suppress(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    receipt = state.cycle_partial_source_publication
+    state.cycle_partial_source_publication = replace(
+        receipt,
+        claims_sha256="0" * 64,
+    )
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] == 2
+        assert summary["cycles"]["model_pass_count"] == 0
+        assert summary["cycles"]["active_warning_count"] == 2
+        assert summary["attention_required"] is True
+
+
+def test_t06_real_syntax_error_remains_attention(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    state.syntax_diagnostics_state = "fresh"
+    state.syntax_diagnostics_by_path = {
+        "broken.py": {
+            "status": "checked_with_errors",
+            "errors": [{"message": "invalid syntax"}],
+        },
+    }
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] == 2
+        assert summary["cycles"]["active_warning_count"] == 0
+        assert summary["syntax_errors"]["count"] == 1
+        assert summary["attention_required"] is True
+
+
+def test_t07_collision_remains_attention(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    state.collisions_state = "fresh"
+    state.collisions = [object()]
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["active_warning_count"] == 0
+        assert summary["name_collisions"]["count"] == 1
+        assert summary["attention_required"] is True
+
+
+def test_t08_stale_structural_inventory_never_claims_zero(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    state.cycles_state = "stale"
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] is None
+        assert "active_warning_count" not in summary["cycles"]
+        assert summary["cycles"]["availability"] == "stale"
+
+
+def test_t09_resync_never_suppresses_or_certifies(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+    state.resync_required = True
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] is None
+        assert "active_warning_count" not in summary["cycles"]
+        assert summary["cycles"]["availability"] == "stale"
+
+
+def test_t10_recovery_degraded_preserves_raw_summary(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        try:
+            server._recovery_release_degraded = True
+            summary = _summary(client)
+
+            assert summary["cycles"]["count"] == 2
+            assert "active_warning_count" not in summary["cycles"]
+            assert summary["attention_required"] is True
+        finally:
+            server._recovery_release_degraded = False
+
+
+def test_t11_incomplete_authority_preserves_raw_warnings(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+        server._authority_identity["process_start_identity"] = None
+
+        summary = _summary(client)
+
+        assert summary["cycles"]["count"] == 2
+        assert "active_warning_count" not in summary["cycles"]
+        assert summary["attention_required"] is True
+
+
+def test_t12_pure_projection_rejects_wrong_revision(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        with server._lock:
+            raw = diagnostics_summary_for_state(state)
+            report = server._owner_cycle_warning_report_locked()
+            original = copy.deepcopy(raw)
+
+            result = project_locked_warning_diagnostics_summary(
+                raw,
+                report,
+                canonical_revision=server._revision + 1,
+                activity_epoch=server._activity_epoch,
+                authority_identity=server._authority_identity,
+            )
+
+        assert result is raw
+        assert raw == original
+        assert "active_warning_count" not in result["cycles"]
+
+
+def test_t13_pure_projection_rejects_count_mismatch(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        with server._lock:
+            raw = diagnostics_summary_for_state(state)
+            report = server._owner_cycle_warning_report_locked()
+            damaged = dict(report, structural_count=99)
+
+            result = project_locked_warning_diagnostics_summary(
+                raw,
+                damaged,
+                canonical_revision=server._revision,
+                activity_epoch=server._activity_epoch,
+                authority_identity=server._authority_identity,
+            )
+
+        assert result is raw
+        assert raw["cycles"]["count"] == 2
+        assert raw["attention_required"] is True
+
+
+def test_t14_narrow_mcp_transport_uses_owner_summary(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    from contextor.mcp.runtime import (
+        query_live_diagnostics_summary_narrow,
+    )
+
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+
+        monkeypatch.setattr(
+            "contextor.core.live_state.connect",
+            lambda _root: client,
+        )
+
+        result = query_live_diagnostics_summary_narrow(root)
+
+        assert result.status == "ok"
+        assert result.revision == metadata.revision
+        assert result.summary["cycles"]["count"] == 2
+        assert result.summary["cycles"]["model_pass_count"] == 2
+        assert result.summary["cycles"]["active_warning_count"] == 0
+        assert result.summary["attention_required"] is False
+
+
+def test_t15_repeated_query_is_read_only(
+    tmp_path, isolated_dirs,
+):
+    _, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _install_query_handler(server)
+
+        before = copy.deepcopy((
+            state.cycles,
+            state.dependency_graph.hard_edges,
+            server._events,
+            server._activity_seq,
+        ))
+
+        first = _summary(client)
+        second = _summary(client)
+
+        assert first == second
+        assert (
+            state.cycles,
+            state.dependency_graph.hard_edges,
+            server._events,
+            server._activity_seq,
+        ) == before
```

## CONTRACT_CONFLICTS

None observed in the exact anchor, compilation, or focused tests.

## REMAINING UNKNOWN

- UNKNOWN: Active loaded-code adoption; no service restart or active user's FULL/LIVE operation was performed.
- UNKNOWN: Global pytest result; prohibited in this stage.
- UNKNOWN: Semantic cycle freshness remains stale in MCP.

## FINAL IMPLEMENTER OBSERVATION

The exact WARN-4F change passed the new module and listed focused regressions. Structural DFS cycle count remained 16. This is local source/test evidence; architectural acceptance remains with ChatGPT. STOP after WARN-4F.
