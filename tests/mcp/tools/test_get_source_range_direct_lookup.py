import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import source_helpers
from contextor.mcp.tools.get_source_range import get_source_range


tool_module = importlib.import_module("contextor.mcp.tools.get_source_range")


def _engine(root: Path, records: list[tuple[str, str, str | None]]) -> SimpleNamespace:
    modules = {}
    for module_name, relative, absolute in records:
        modules[module_name] = SimpleNamespace(path=relative, absolute_path=absolute or "")
    return SimpleNamespace(state=SimpleNamespace(modules=modules, resync_required=False))


def _record(root: Path, relative: str, text: str = "one\ntwo\nthree\n") -> tuple[str, str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return relative[:-3].replace("/", "."), relative, str(path)


@pytest.fixture(autouse=True)
def _fresh_truth(monkeypatch):
    monkeypatch.setattr(query_helpers, "module_truth_unavailable", lambda *_args: None)


def test_exact_path_uses_no_full_projection_and_preserves_windows_output(tmp_path, monkeypatch):
    record = _record(tmp_path, "pkg/sample.py")
    engine = _engine(tmp_path, [record])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    projection_calls = 0

    def forbidden_projection(*_args):
        nonlocal projection_calls
        projection_calls += 1
        raise AssertionError("normal exact path must not build the full projection")

    monkeypatch.setattr(tool_module, "canonical_python_sources", forbidden_projection)
    resolve_calls = 0
    original_resolve = Path.resolve

    def counted_resolve(self, *args, **kwargs):
        nonlocal resolve_calls
        resolve_calls += 1
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", counted_resolve)
    baseline = get_source_range(str(tmp_path), "pkg/sample.py", 1, 2)
    windows = get_source_range(str(tmp_path), "pkg\\sample.py", 1, 2)

    assert baseline == windows
    assert json.loads(baseline)["text"] == "one\ntwo"
    assert projection_calls == 0
    assert resolve_calls == 4  # root + matched candidate per call


@pytest.mark.parametrize(
    ("file_path", "start_line", "end_line", "error"),
    [
        ("missing.py", 1, 1, "file_not_in_canonical_scope"),
        ("../outside.py", 1, 1, "file_not_in_canonical_scope"),
        ("module.txt", 1, 1, "file_not_in_canonical_scope"),
        ("module.py", 3, 1, "invalid_line_range"),
    ],
)
def test_direct_lookup_preserves_controlled_error_paths(tmp_path, monkeypatch, file_path, start_line, end_line, error):
    record = _record(tmp_path, "module.py")
    engine = _engine(tmp_path, [record])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    result = json.loads(get_source_range(str(tmp_path), file_path, start_line, end_line))

    assert result == {"status": "error", "error": error}


def test_duplicate_normalized_paths_keep_canonical_module_order(tmp_path, monkeypatch):
    _, relative, absolute = _record(tmp_path, "same.py")
    engine = _engine(tmp_path, [("z_module", relative, absolute), ("a_module", relative, absolute)])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    result = json.loads(get_source_range(str(tmp_path), "same.py", 1, 1))

    assert result["module"] == "a_module"


def test_empty_module_path_uses_legacy_projection_fallback(tmp_path, monkeypatch):
    _, _relative, absolute = _record(tmp_path, "empty.py")
    engine = _engine(tmp_path, [("empty_module", "", absolute)])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    original_projection = tool_module.canonical_python_sources
    calls = 0

    def counted_projection(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_projection(*args, **kwargs)

    monkeypatch.setattr(tool_module, "canonical_python_sources", counted_projection)
    result = json.loads(get_source_range(str(tmp_path), "empty.py", 1, 1))

    assert result["status"] == "ok"
    assert result["file_path"] == "empty.py"
    assert calls == 1


def test_absolute_path_divergence_uses_legacy_projection_fallback(tmp_path, monkeypatch):
    actual = tmp_path / "actual.py"
    actual.write_text("actual\n", encoding="utf-8")
    engine = _engine(tmp_path, [("diverged", "declared.py", str(actual))])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    original_projection = tool_module.canonical_python_sources
    calls = 0

    def counted_projection(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_projection(*args, **kwargs)

    monkeypatch.setattr(tool_module, "canonical_python_sources", counted_projection)
    result = json.loads(get_source_range(str(tmp_path), "declared.py", 1, 1))

    assert result["text"] == "actual"
    assert calls == 1


def test_module_truth_unavailable_missing_engine_and_resync_remain_fail_closed(tmp_path, monkeypatch):
    record = _record(tmp_path, "module.py")
    engine = _engine(tmp_path, [record])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, module: {"status": "error", "error": "module_truth_unavailable", "module": module},
    )
    assert json.loads(get_source_range(str(tmp_path), "module.py", 1, 1))["error"] == "module_truth_unavailable"

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
    assert json.loads(get_source_range(str(tmp_path), "module.py", 1, 1)) == {
        "status": "error", "error": "canonical_state_unavailable"
    }

    engine.state.resync_required = True
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    assert json.loads(get_source_range(str(tmp_path), "module.py", 1, 1)) == {
        "status": "error", "error": "canonical_state_unavailable"
    }


def test_exact_path_reads_once_without_ast_or_source_tokenization(tmp_path, monkeypatch):
    record = _record(tmp_path, "module.py")
    engine = _engine(tmp_path, [record])
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    read_calls = 0
    original_read_source = source_helpers.read_source

    def counted_read_source(*args, **kwargs):
        nonlocal read_calls
        read_calls += 1
        return original_read_source(*args, **kwargs)

    monkeypatch.setattr(source_helpers, "read_source", counted_read_source)
    ast_calls = 0
    tokenize_calls = 0
    original_parse = source_helpers.ast.parse
    original_tokenize = source_helpers.tokenize.generate_tokens

    def counted_parse(*args, **kwargs):
        nonlocal ast_calls
        ast_calls += 1
        return original_parse(*args, **kwargs)

    def counted_tokenize(*args, **kwargs):
        nonlocal tokenize_calls
        tokenize_calls += 1
        return original_tokenize(*args, **kwargs)

    monkeypatch.setattr(source_helpers.ast, "parse", counted_parse)
    monkeypatch.setattr(source_helpers.tokenize, "generate_tokens", counted_tokenize)
    result = json.loads(get_source_range(str(tmp_path), "module.py", 1, 2))

    assert result["status"] == "ok"
    assert read_calls == 1
    assert ast_calls == 0
    assert tokenize_calls == 0
