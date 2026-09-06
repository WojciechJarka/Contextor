import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools import extract_indexed_report_context as tool_module


REQUEST = {
    "query": "contextor/mcp/tools/extract_indexed_report_context.py",
    "report_path": "",
    "resolve_indices": False,
    "public_api_only": False,
    "max_items": 20,
    "fields": None,
    "evidence_limit": 3,
    "representation": "indexed",
}


def _setup(tmp_path):
    source = tmp_path / "contextor" / "mcp" / "tools" / "extract_indexed_report_context.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "artifacts": {
                    "A1/1": {
                        "definer_module": "266/1",
                        "consumer_module_indices": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry._state["module_registry"]["path_to_id"] = {
            "contextor.mcp.tools.extract_indexed_report_context": "266/1"
        }
        registry._state["module_registry"]["id_to_path"] = {
            "266/1": "contextor.mcp.tools.extract_indexed_report_context"
        }
        registry._state["artifact_registry"]["path_to_id"] = {
            "contextor.mcp.tools.extract_indexed_report_context::value": "A1/1"
        }
        registry._state["artifact_registry"]["id_to_path"] = {
            "A1/1": "contextor.mcp.tools.extract_indexed_report_context::value"
        }

    state = SimpleNamespace(
        modules={
            "contextor.mcp.tools.extract_indexed_report_context": SimpleNamespace(
                path="contextor/mcp/tools/extract_indexed_report_context.py"
            )
        },
        resync_required=False,
    )
    return report_path, registry, state


def test_fresh_live_reuses_engine_registry_with_exact_byte_parity(tmp_path, monkeypatch):
    report_path, registry, state = _setup(tmp_path)
    engine = SimpleNamespace(state=state, provenance="live", registry=registry)
    monkeypatch.setattr(
        tool_module.report_helpers,
        "get_canonical_report",
        lambda *_args: report_path,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    counts = {"engine": 0, "read_transaction": 0, "fallback": 0}
    original_read = registry.read_transaction
    original_fallback = tool_module.report_query.catalog_from_registry

    @contextmanager
    def counted_read():
        counts["read_transaction"] += 1
        with original_read():
            yield

    def counted_fallback(*args, **kwargs):
        counts["fallback"] += 1
        return original_fallback(*args, **kwargs)

    monkeypatch.setattr(registry, "read_transaction", counted_read)
    monkeypatch.setattr(tool_module.report_query, "catalog_from_registry", counted_fallback)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: counts.__setitem__("engine", counts["engine"] + 1) or engine,
    )

    optimized = tool_module.extract_indexed_report_context(
        repo_path=str(tmp_path), **REQUEST
    )

    monkeypatch.setattr(engine, "provenance", "snapshot")
    fallback = tool_module.extract_indexed_report_context(
        repo_path=str(tmp_path), **REQUEST
    )

    assert optimized == fallback
    result = json.loads(optimized)
    assert result["resolution"]["matches"][0]["id"] == "266/1"
    assert result["artifact_count"] == 1
    assert result["truncated"] is False
    assert result["representation"] == "indexed"
    assert result["resolve_via"] == "lookup_index_entries"
    assert len(optimized.encode("utf-8")) == len(fallback.encode("utf-8"))
    assert counts == {"engine": 2, "read_transaction": 1, "fallback": 1}


@pytest.mark.parametrize(
    "engine_factory",
    [
        lambda _state, _registry: None,
        lambda state, _registry: SimpleNamespace(
            state=state, provenance="snapshot", registry=_registry
        ),
        lambda state, _registry: SimpleNamespace(state=state, provenance="live"),
        lambda state, registry: SimpleNamespace(
            state=SimpleNamespace(modules=state.modules, resync_required=True),
            provenance="live",
            registry=registry,
        ),
    ],
)
def test_nonusable_engine_keeps_catalog_fallback(tmp_path, monkeypatch, engine_factory):
    report_path, registry, state = _setup(tmp_path)
    engine = engine_factory(state, registry)
    monkeypatch.setattr(
        tool_module.report_helpers,
        "get_canonical_report",
        lambda *_args: report_path,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    calls = {"fallback": 0}
    original = tool_module.report_query.catalog_from_registry

    def counted(*args, **kwargs):
        calls["fallback"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(tool_module.report_query, "catalog_from_registry", counted)
    result = json.loads(
        tool_module.extract_indexed_report_context(
            repo_path=str(tmp_path), **REQUEST
        )
    )

    assert result["resolution"]["matches"][0]["id"] == "266/1"
    assert calls["fallback"] == 1
