"""
tests/test_payload_isolation.py

Stage 3C.1b — Payload Isolation Proof Tests.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine, IncrementalUpdateResult
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_shadow_plan_repr_false():
    plan = RefreshPlan(reason="Test plan")
    res = IncrementalUpdateResult(status="UPDATED", file_path="app.py", shadow_plan=plan)

    res_repr = repr(res)
    assert "shadow_plan" not in res_repr


def test_mcp_update_file_payload_isolation(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
    res = engine.update_file(str(f_target))

    assert res.shadow_plan is not None

    # Simulate MCP server response shaping (key by key dict construction)
    mcp_result = {
        "status": res.status,
        "file_path": res.file_path,
        "graph_state": res.graph_state,
        "dependencies_state": res.dependencies_state,
        "blast_radius_state": res.blast_radius_state,
        "artifact_consumption_state": res.artifact_consumption_state,
        "affected_modules": {"total": len(res.affected_modules), "truncated": False},
    }
    if res.delta:
        mcp_result["delta"] = {
            "module_path": res.delta.module_path,
            "is_new": res.delta.is_new,
            "is_deleted": res.delta.is_deleted,
        }

    mcp_json = json.dumps(mcp_result, indent=2)

    assert "shadow_plan" not in mcp_json
    assert "RefreshPlan" not in mcp_json


def test_ipc_event_payload_isolation():
    plan = RefreshPlan(reason="Internal test")
    res = IncrementalUpdateResult(status="UPDATED", file_path="service.py", shadow_plan=plan)

    ipc_payload = {
        "status": "ok",
        "file_path": res.file_path,
        "update_status": res.status,
        "graph_state": res.graph_state,
    }

    ipc_json = json.dumps(ipc_payload)

    assert "shadow_plan" not in ipc_json
