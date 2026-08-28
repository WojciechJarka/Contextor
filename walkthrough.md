# Contextor zero-fit output-guard pagination closure

## Walkthrough

VERDICT=IMPLEMENTATION_PASS
MCP_TOOL_COUNT=25
ZERO_FIT_PAGE_CAN_RETURN_SUCCESS=NO
PAGINATION_PROGRESS_INVARIANT=PASS
ZERO_FIT_RESULT_STATUS=confirmation_required
ZERO_FIT_RESPONSE_BYTES=441
TESTS_RUN=pytest -q tests/test_mcp_diagnostics.py tests/test_mcp_documentation.py tests/mcp/tools/test_public_mcp_docs_parity.py
TESTS_PASSED=28
TESTS_FAILED=0
MANUAL_RESTART_REQUIRED=YES
FILES_CHANGED=contextor/mcp/tools/get_name_collisions.py; tests/test_mcp_diagnostics.py
COMPLETE_RAW_DIFFS=YES

Contextor MCP architectural discovery confirmed the current get_name_collisions implementation and fresh canonical collision family. The correction is limited to semantic validation of a zero-fit bounded response and focused regression coverage; diagnostics architecture, public signature, runtime state, and documentation were not changed.

When largest_fitting_prefix produces zero details while matches remain, the candidate is rejected unless it is non-continuing or advances the offset. Control falls through to the existing confirmation/output guard, so no successful response advertises has_more with a non-advancing next_offset. Normal pages assert returned > 0 and next_offset > offset whenever has_more is true.

## Complete raw unified diffs for this correction task

diff --git a/contextor/mcp/tools/get_name_collisions.py b/contextor/mcp/tools/get_name_collisions.py
new file mode 100644
index 0000000..c6f5f30
--- /dev/null
+++ b/contextor/mcp/tools/get_name_collisions.py
@@ -0,0 +1,237 @@
+"""Bounded projection of canonical name-collision diagnostics."""
+
+from __future__ import annotations
+
+import json
+from pathlib import Path
+from typing import Any
+
+from contextor.mcp import diagnostics
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.output_guard import (
+    LARGE_OUTPUT_WARNING_BYTES,
+    guard_large_output,
+    largest_fitting_prefix,
+)
+
+
+def _severity(error: Any) -> str:
+    value = getattr(error, "severity", None)
+    if value in {"critical", "warning", "info"}:
+        return value
+    from contextor.core.reporting_engine.formatting import _collision_severity
+
+    return _collision_severity(
+        getattr(error, "artifact_type", "unknown"),
+        getattr(error, "symbol_details", []) or [],
+        getattr(error, "code_snippets", {}) or {},
+    )
+
+
+def _sort_key(error: Any) -> tuple:
+    return (
+        str(getattr(error, "kind", "")),
+        str(getattr(error, "artifact_type", "")),
+        tuple(sorted(str(node) for node in (getattr(error, "nodes", []) or []))),
+        str(getattr(error, "message", "")),
+        bool(getattr(error, "is_identical", False)),
+    )
+
+
+def _detail(
+    error: Any,
+    representation: str,
+    *,
+    result_index: int | None = None,
+    severity_value: str | None = None,
+) -> dict[str, Any]:
+    base = {
+        "collision_type": getattr(error, "kind", "NAME_COLLISION"),
+        "artifact_type": getattr(error, "artifact_type", "unknown"),
+        "severity": severity_value if severity_value is not None else _severity(error),
+        "is_identical": bool(getattr(error, "is_identical", False)),
+        "modules": sorted(str(node) for node in (getattr(error, "nodes", []) or [])),
+    }
+    if representation != "summary":
+        base["result_index"] = result_index
+    if representation in {"indexed", "summary"}:
+        return base
+    base.update(
+        {
+            "message": getattr(error, "message", ""),
+            "symbol_details": getattr(error, "symbol_details", []) or [],
+            "conflicting_code": getattr(error, "code_snippets", {}) or {},
+        }
+    )
+    return base
+
+
+def _error_payload(message: str) -> str:
+    return json.dumps({"error": message}, indent=2)
+
+
+def get_name_collisions(
+    repo_path: str,
+    severity: str | None = None,
+    artifact_type: str | None = None,
+    collision_type: str | None = None,
+    module: str | None = None,
+    conflicting_only: bool = False,
+    identical_only: bool = False,
+    representation: str = "auto",
+    offset: int = 0,
+    limit: int | None = 20,
+    allow_large_output: bool = False,
+) -> str:
+    if offset < 0:
+        return _error_payload("offset must be >= 0")
+    if limit is not None and limit <= 0:
+        return _error_payload("limit must be > 0 or null")
+    if severity is not None and severity not in {"critical", "warning", "info"}:
+        return json.dumps({"error": "Unsupported severity", "allowed": ["critical", "warning", "info"]}, indent=2)
+    if conflicting_only and identical_only:
+        return _error_payload("conflicting_only and identical_only are mutually exclusive")
+    if representation not in {"auto", "summary", "bounded", "indexed", "named"}:
+        return json.dumps({"error": "Unsupported representation", "allowed": ["auto", "summary", "bounded", "indexed", "named"]}, indent=2)
+
+    root = Path(repo_path).expanduser().resolve()
+    engine = mcp_runtime.get_or_init_engine(root)
+    state = getattr(engine, "state", None) if engine is not None else None
+    availability = getattr(state, "collisions_state", "unavailable") if state is not None else "unavailable"
+    if availability != "fresh":
+        payload = {
+            "total": None,
+            "matched": None,
+            "offset": offset,
+            "returned": 0,
+            "has_more": False,
+            "next_offset": None,
+            "severity_counts": {"critical": None, "warning": None, "info": None},
+            "conflicting": None,
+            "identical": None,
+            "representation": representation,
+            "truncated": offset > 0,
+            "estimated_full_bytes": None,
+            "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
+            "attention_required": False,
+            "availability": availability,
+            "details": [],
+            "guidance": "Collision diagnostics are not fresh; rerun analyze_project and retry.",
+            "diagnostics_summary": diagnostics.diagnostics_summary(root, state),
+        }
+        return json.dumps(payload, indent=2, ensure_ascii=False)
+
+    errors = list(getattr(state, "collisions", []) or [])
+    selected: list[tuple[Any, str]] = []
+    for error in errors:
+        identical = bool(getattr(error, "is_identical", False))
+        if artifact_type and str(getattr(error, "artifact_type", "")) != artifact_type:
+            continue
+        if collision_type and str(getattr(error, "kind", "")) != collision_type:
+            continue
+        if module and module not in {str(node) for node in (getattr(error, "nodes", []) or [])}:
+            continue
+        if conflicting_only and identical:
+            continue
+        if identical_only and not identical:
+            continue
+        item_severity = _severity(error)
+        if severity and item_severity != severity:
+            continue
+        selected.append((error, item_severity))
+
+    selected.sort(key=lambda item: _sort_key(item[0]))
+    matched = len(selected)
+    severity_counts = {name: sum(item[1] == name for item in selected) for name in ("critical", "warning", "info")}
+    identical_count = sum(bool(getattr(error, "is_identical", False)) for error, _ in selected)
+    if limit is None:
+        page = selected[offset:]
+    else:
+        page = selected[offset : offset + limit]
+
+    if representation == "auto":
+        if matched == 0:
+            effective = "named"
+        elif limit is None:
+            effective = "indexed"
+        else:
+            effective = "named"
+    else:
+        effective = representation
+
+    def details_for(kind: str) -> list[dict[str, Any]]:
+        return [
+            _detail(
+                error,
+                kind,
+                result_index=offset + index,
+                severity_value=item_severity,
+            )
+            for index, (error, item_severity) in enumerate(page)
+        ]
+
+    visible_details = [] if effective == "summary" else details_for(effective)
+    estimated_full_bytes = None
+
+    def make_payload(details: list[dict[str, Any]], kind: str) -> dict[str, Any]:
+        returned = len(details)
+        if kind == "summary":
+            has_more = False
+            next_offset = None
+            truncated = bool(matched)
+        else:
+            has_more = offset + returned < matched
+            next_offset = offset + returned if has_more else None
+            truncated = offset > 0 or has_more
+        return {
+            "total": len(errors),
+            "matched": matched,
+            "offset": offset,
+            "returned": returned,
+            "has_more": has_more,
+            "next_offset": next_offset,
+            "severity_counts": severity_counts,
+            "conflicting": matched - identical_count,
+            "identical": identical_count,
+            "representation": kind,
+            "truncated": truncated,
+            "estimated_full_bytes": estimated_full_bytes,
+            "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
+            "attention_required": bool(matched),
+            "availability": "fresh",
+            "details": details,
+            "diagnostics_summary": diagnostics.diagnostics_summary(root, state),
+        }
+
+    if representation == "auto" and effective == "named" and matched:
+        candidate = json.dumps(make_payload(visible_details, effective), indent=2, ensure_ascii=False)
+        if not allow_large_output and len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES:
+            effective = "indexed"
+            visible_details = details_for(effective)
+
+    if effective == "summary":
+        visible_details = []
+
+    def build(count: int) -> str:
+        details = visible_details[:count]
+        return json.dumps(make_payload(details, effective), indent=2, ensure_ascii=False)
+
+    candidate = build(len(visible_details))
+    if len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
+        bounded = largest_fitting_prefix(len(visible_details), build, min_count=0)
+        if bounded is not None:
+            bounded_text = bounded[0]
+            bounded_payload = json.loads(bounded_text)
+            returned = int(bounded_payload.get("returned", 0))
+            has_more = bool(bounded_payload.get("has_more", False))
+            next_offset = bounded_payload.get("next_offset")
+            if not has_more:
+                return bounded_text
+            if returned > 0 and isinstance(next_offset, int) and next_offset > offset:
+                return bounded_text
+    return guard_large_output(
+        candidate,
+        allow_large_output=allow_large_output,
+        requested_count=limit,
+        retry_instruction="Repeat with representation='indexed' or a smaller limit, or set allow_large_output=true.",
+    )
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
new file mode 100644
index 0000000..81ae0d9
--- /dev/null
+++ b/tests/test_mcp_diagnostics.py
@@ -0,0 +1,281 @@
+import json
+from types import SimpleNamespace
+
+from contextor import mcp_server
+from contextor.mcp.diagnostics import (
+    diagnostics_summary,
+    diagnostics_summary_for_completed_job,
+    diagnostics_summary_for_state,
+    inject_diagnostics_summary,
+)
+from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
+from contextor.mcp import runtime as mcp_runtime
+from contextor.mcp.tools.get_name_collisions import get_name_collisions
+import contextor.mcp.tools.get_name_collisions as collision_tool
+from contextor.mcp.tools.get_analysis_status import get_analysis_status
+
+
+def _collision(kind="NAME_COLLISION", identical=False, module="pkg.a"):
+    return SimpleNamespace(
+        kind=kind,
+        message=f"{kind} foo",
+        nodes=[module, "pkg.b"],
+        artifact_type="function",
+        is_identical=identical,
+        symbol_details=[],
+        code_snippets={module: "def foo():\n    return 1", "pkg.b": "def foo():\n    return 2"},
+    )
+
+
+def test_diagnostics_summary_does_not_fabricate_unavailable_counts():
+    summary = diagnostics_summary_for_state(SimpleNamespace(
+        collisions_state="deferred", cycles_state="unavailable", collisions=None, cycles=None
+    ))
+    assert summary["name_collisions"]["count"] is None
+    assert summary["cycles"]["count"] is None
+    assert summary["availability"]["name_collisions"] == "deferred"
+
+
+def test_get_name_collisions_filters_without_invented_ids(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(
+        collisions_state="fresh", collisions=[_collision(), _collision("IDENTICAL_DEFINITION_DUPLICATE", True, "pkg.c")],
+        cycles_state="fresh", cycles=[], summary_data={}
+    )
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    first = json.loads(get_name_collisions(str(repo), conflicting_only=True))
+    second = json.loads(get_name_collisions(str(repo), conflicting_only=True))
+    assert first["matched"] == 1
+    assert "collision_id" not in first["details"][0]
+    assert first["conflicting"] == 1
+
+
+def test_attention_required_tracks_each_available_family():
+    clean = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    assert diagnostics_summary_for_state(clean)["attention_required"] is False
+    result = diagnostics_summary_for_state(clean)
+    assert result["syntax_errors"] == {"count": None, "availability": "unavailable"}
+    syntax_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})
+    assert syntax_result["syntax_errors"] == {"count": 1, "availability": "fresh"}
+    assert syntax_result["attention_required"] is True
+    zero_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": []})
+    assert zero_result["syntax_errors"] == {"count": 0, "availability": "fresh"}
+    assert zero_result["attention_required"] is False
+    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[_collision()], cycles_state="fresh", cycles=[]))["attention_required"] is True
+    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[["a", "b", "a"]]))["attention_required"] is True
+
+
+def test_historical_job_does_not_promote_global_syntax_freshness(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    monkeypatch.setattr("contextor.mcp.analysis_jobs._latest_analysis_job", lambda _root: {"status": "completed", "skipped_python_files": [{"reason": "not valid Python"}]})
+    summary = diagnostics_summary(repo)
+    assert summary["syntax_errors"] == {"count": None, "availability": "unavailable"}
+    assert diagnostics_summary_for_completed_job(summary, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})["syntax_errors"] == {"count": 1, "availability": "fresh"}
+
+
+def test_analysis_status_uses_only_the_exact_completed_project_job_for_syntax(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    (repo / ".contextor" / "analysis_jobs").mkdir(parents=True)
+    job_id = "a" * 32
+    (repo / ".contextor" / "analysis_jobs" / f"{job_id}.json").write_text(json.dumps({
+        "job_id": job_id, "operation": "project", "repo_path": str(repo), "status": "completed",
+        "skipped_python_files": [{"reason": "not valid Python"}], "live_publish_status": "success",
+    }), encoding="utf-8")
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    result = json.loads(get_analysis_status(str(repo), job_id))
+    assert result["diagnostics_summary"]["syntax_errors"] == {"count": 1, "availability": "fresh"}
+
+
+def test_wrapper_injects_health_for_analytical_not_found(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "not_found", "repo_path": repo_path}), "synthetic_query")
+    result = json.loads(wrapped(str(repo)))
+    assert "diagnostics_summary" in result
+
+
+def test_wrapper_applies_shared_guard_after_diagnostics_injection(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    before = LARGE_OUTPUT_WARNING_BYTES - 40
+    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "ok", "payload": "x" * before}), "synthetic_query")
+    raw = wrapped(str(repo))
+    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+    result = json.loads(raw)
+    assert "diagnostics_summary" in result
+    assert result["status"] == "confirmation_required"
+    large = mcp_server._instrument_mcp_tool(lambda repo_path, allow_large_output=False: json.dumps({"status": "ok", "payload": "x" * (LARGE_OUTPUT_WARNING_BYTES + 100)}), "synthetic_query")
+    bounded_raw = large(str(repo))
+    assert len(bounded_raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+    bounded = json.loads(bounded_raw)
+    assert "diagnostics_summary" in bounded
+    unbounded_raw = large(str(repo), allow_large_output=True)
+    assert len(unbounded_raw.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES
+    unbounded = json.loads(unbounded_raw)
+    assert "diagnostics_summary" in unbounded
+    pre_injection = json.dumps({"status": "ok", "payload": "x" * before})
+    post_injection = inject_diagnostics_summary(pre_injection, repo, "synthetic_query", allow_large_output=True)
+    assert len(pre_injection.encode("utf-8")) < LARGE_OUTPUT_WARNING_BYTES
+    assert len(post_injection.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES
+
+
+def test_get_name_collisions_indexed_representation_is_bounded(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    errors = [_collision(module=f"pkg.mod{i}") for i in range(30)]
+    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[], summary_data={})
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    result = json.loads(get_name_collisions(str(repo), representation="indexed", limit=3))
+    assert result["returned"] == 3
+    assert result["truncated"] is True
+    assert all("conflicting_code" not in item for item in result["details"])
+
+
+def test_always_on_collision_health_uses_len_without_iteration():
+    class LenOnly:
+        def __len__(self):
+            return 7
+
+        def __iter__(self):
+            raise AssertionError("collision sequence iterated")
+
+    result = diagnostics_summary_for_state(SimpleNamespace(
+        collisions_state="fresh", collisions=LenOnly(), cycles_state="fresh", cycles=[]
+    ))
+    assert result["name_collisions"]["count"] == 7
+    assert result["name_collisions"]["critical"] is None
+    assert result["name_collisions"]["warning"] is None
+    assert result["name_collisions"]["info"] is None
+    assert result["attention_required"] is True
+
+
+def test_name_collisions_paging_and_deterministic_result_indices(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    errors = [_collision(module=f"pkg.mod{i:04d}") for i in range(45)]
+    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    page1 = json.loads(get_name_collisions(str(repo), representation="indexed", offset=0, limit=20))
+    page2 = json.loads(get_name_collisions(str(repo), representation="indexed", offset=20, limit=20))
+    final = json.loads(get_name_collisions(str(repo), representation="indexed", offset=40, limit=20))
+    assert page1["matched"] == 45
+    assert [d["result_index"] for d in page1["details"]] == list(range(20))
+    assert [d["result_index"] for d in page2["details"]] == list(range(20, 40))
+    assert not ({d["result_index"] for d in page1["details"]} & {d["result_index"] for d in page2["details"]})
+    assert page1["next_offset"] == 20 and page1["has_more"] is True
+    assert page2["next_offset"] == 40 and page2["has_more"] is True
+    assert final["has_more"] is False and final["next_offset"] is None
+    assert final["returned"] == 5
+    for result in (page1, page2, final):
+        if result["has_more"]:
+            assert result["returned"] > 0
+            assert result["next_offset"] > result["offset"]
+
+
+def test_name_collisions_paging_validation_and_summary_shape(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[_collision()], cycles_state="fresh", cycles=[])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    assert json.loads(get_name_collisions(str(repo), offset=-1))["error"] == "offset must be >= 0"
+    assert json.loads(get_name_collisions(str(repo), limit=-1))["error"] == "limit must be > 0 or null"
+    assert json.loads(get_name_collisions(str(repo), limit=0))["error"] == "limit must be > 0 or null"
+    beyond = json.loads(get_name_collisions(str(repo), representation="indexed", offset=9, limit=2))
+    assert beyond["details"] == [] and beyond["returned"] == 0 and beyond["next_offset"] is None
+    summary = json.loads(get_name_collisions(str(repo), representation="summary", limit=20))
+    assert summary["matched"] == 1
+    assert summary["returned"] == 0
+    assert summary["details"] == []
+    assert summary["has_more"] is False
+    assert summary["next_offset"] is None
+    assert summary["truncated"] is True
+
+
+def test_auto_large_fixture_materializes_only_requested_page(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    errors = []
+    for i in range(1000):
+        error = _collision(module=f"pkg.mod{i:04d}")
+        error.code_snippets = {"a": "x" * 4000}
+        errors.append(error)
+    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    original = collision_tool._detail
+    calls = []
+
+    def counted(error, representation, **kwargs):
+        if representation in {"named", "bounded"}:
+            calls.append(error)
+        return original(error, representation, **kwargs)
+
+    monkeypatch.setattr(collision_tool, "_detail", counted)
+    raw = get_name_collisions(str(repo), representation="auto", offset=0, limit=20)
+    result = json.loads(raw)
+    assert result["matched"] == 1000
+    assert result["returned"] <= 20
+    assert len(calls) <= 20
+    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+    assert result["representation"] == "indexed"
+
+
+def test_named_zero_fit_returns_confirmation_required_without_stalled_page(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    error = _collision()
+    error.code_snippets = {"pkg.a": "x" * (LARGE_OUTPUT_WARNING_BYTES * 2)}
+    state = SimpleNamespace(collisions_state="fresh", collisions=[error], cycles_state="fresh", cycles=[])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    raw = get_name_collisions(
+        str(repo), representation="named", offset=0, limit=1, allow_large_output=False
+    )
+    result = json.loads(raw)
+    assert result["status"] == "confirmation_required"
+    assert not (result.get("has_more") is True and result.get("next_offset") == 0)
+    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
+
+
+def test_wrapper_retry_guidance_matches_tool_signature(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
+    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
+    oversized = json.dumps({"status": "ok", "payload": "x" * (LARGE_OUTPUT_WARNING_BYTES + 100)})
+    with_allow = mcp_server._instrument_mcp_tool(lambda repo_path, allow_large_output=False: oversized, "with_allow")
+    without_allow = mcp_server._instrument_mcp_tool(lambda repo_path: oversized, "without_allow")
+    assert "allow_large_output" in with_allow(str(repo))
+    assert "allow_large_output" not in without_allow(str(repo))
+
+
+def test_cheap_filters_run_before_severity_and_severity_filter_survives(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    errors = [_collision(module=f"other.mod{i}") for i in range(100)]
+    errors.extend(_collision(module="target.module") for _ in range(7))
+    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[])
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    original = collision_tool._severity
+    calls = []
+
+    def counted(error):
+        calls.append(error)
+        return original(error)
+
+    monkeypatch.setattr(collision_tool, "_severity", counted)
+    result = json.loads(get_name_collisions(str(repo), module="target.module", severity="warning"))
+    assert result["matched"] == 7
+    assert len(calls) == 7
+
+
+def test_registered_name_collision_tool_and_shared_summary_wrapper():
+    assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
+    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 25
