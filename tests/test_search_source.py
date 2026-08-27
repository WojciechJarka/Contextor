import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.domain.module import Module
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import source_helpers
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
from contextor.mcp.tools.get_source_range import get_source_range
from contextor.mcp.tools.search_source import search_source


def _engine(root: Path, files: dict[str, str]):
    modules = {}
    for index, (relative, text) in enumerate(files.items(), 1):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        module_name = relative[:-3].replace("/", ".").replace("\\", ".")
        modules[module_name] = Module(str(index), relative, str(path), [])
    return SimpleNamespace(state=SimpleNamespace(modules=modules, artifacts={}, resync_required=False))


@pytest.fixture(autouse=True)
def _fresh_truth(monkeypatch):
    monkeypatch.setattr(query_helpers, "module_truth_unavailable", lambda *_args: None)


def _call(monkeypatch, root, files, term, **kwargs):
    engine = _engine(root, files)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    return json.loads(search_source(str(root), term, **kwargs))


def test_search_source_finds_literals_strings_comments_docstrings_and_unknown(tmp_path, monkeypatch):
    source = '''"""Unique module documentation phrase.
More documentation context.
End documentation."""
# first unique comment marker
# second comment line
TIMEOUT = 109.9
MESSAGE = "Distinct source fragment"
'''
    numeric = _call(monkeypatch, tmp_path, {"pkg/sample.py": source}, "109.9")
    string = _call(monkeypatch, tmp_path, {"pkg/sample.py": source}, "source fragment")
    comment = _call(monkeypatch, tmp_path, {"pkg/sample.py": source}, "unique comment")
    docstring = _call(monkeypatch, tmp_path, {"pkg/sample.py": source}, "module documentation")
    missing = _call(monkeypatch, tmp_path, {"pkg/sample.py": source}, "does-not-exist")

    assert numeric["matches"][0]["match_kind"] == "statement"
    assert "TIMEOUT = 109.9" in numeric["matches"][0]["text"]
    assert string["total_matches"] == 1
    assert comment["matches"][0]["match_kind"] == "comment"
    assert comment["matches"][0]["span_end"] - comment["matches"][0]["span_start"] == 1
    assert docstring["matches"][0]["match_kind"] == "docstring"
    assert docstring["matches"][0]["span_start"] == 1
    assert docstring["matches"][0]["span_end"] == 3
    assert "End documentation." in docstring["matches"][0]["text"]
    assert missing == {
        "status": "ok", "search_term": "does-not-exist", "case_sensitive": False,
        "total_matches": 0, "matches": [], "truncated": False,
    }


def test_search_source_case_limit_none_order_scope_and_no_mutation(tmp_path, monkeypatch):
    files = {
        "z.py": "VALUE = 'Needle'\n# needle\n",
        "a.py": "VALUE = 'needle'\n",
    }
    engine = _engine(tmp_path, files)
    excluded = tmp_path / "excluded.py"
    excluded.write_text("VALUE = 'needle'\n", encoding="utf-8")
    before = dict(engine.state.modules)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    default = json.loads(search_source(str(tmp_path), "NEEDLE", limit=1))
    sensitive = json.loads(search_source(str(tmp_path), "NEEDLE", case_sensitive=True))
    full = json.loads(search_source(str(tmp_path), "needle", limit=None))

    assert default["total_matches"] == 3 and default["truncated"] is True
    assert default["matches"][0]["file_path"] == "a.py"
    assert sensitive["total_matches"] == 0
    assert [item["file_path"] for item in full["matches"]] == ["a.py", "z.py", "z.py"]
    assert all(item["file_path"] != "excluded.py" for item in full["matches"])
    assert engine.state.modules == before


@pytest.mark.parametrize("limit", [0, -1, True])
def test_search_source_rejects_invalid_limits(tmp_path, monkeypatch, limit):
    result = _call(monkeypatch, tmp_path, {"a.py": "x = 1\n"}, "x", limit=limit)
    assert result == {"status": "error", "error": "invalid_limit"}


def test_search_source_rejects_empty_term(tmp_path):
    assert json.loads(search_source(str(tmp_path), "")) == {
        "status": "error", "error": "invalid_search_term"
    }


@pytest.mark.parametrize("term", ["needle\nvalue", "needle\rvalue"])
def test_search_source_rejects_multiline_terms(tmp_path, term):
    assert json.loads(search_source(str(tmp_path), term)) == {
        "status": "error", "error": "invalid_search_term"
    }


def test_inline_comment_occurrences_resolve_by_column(tmp_path, monkeypatch):
    source = (
        "TIMEOUT = 109.9  # unrelated\n"
        "VALUE = 'special_marker'  # special_marker\n"
    )
    numeric = _call(monkeypatch, tmp_path, {"sample.py": source}, "109.9")
    marker = _call(monkeypatch, tmp_path, {"sample.py": source}, "special_marker")

    assert numeric["total_matches"] == 1
    assert numeric["matches"][0]["match_kind"] == "statement"
    assert marker["total_matches"] == 2
    assert {match["match_kind"] for match in marker["matches"]} == {
        "statement", "comment"
    }


def test_only_real_python_docstring_owners_are_docstrings(tmp_path, monkeypatch):
    source = '''"""module marker"""
if condition:
    "not a docstring marker"
class Owner:
    """class marker"""
    def method(self):
        """function marker"""
'''
    result = _call(monkeypatch, tmp_path, {"owners.py": source}, "marker", limit=None)
    kinds_by_line = {match["span_start"]: match["match_kind"] for match in result["matches"]}

    assert kinds_by_line[1] == "docstring"
    assert kinds_by_line[3] == "statement"
    assert kinds_by_line[5] == "docstring"
    assert kinds_by_line[7] == "docstring"


def test_deleted_canonical_source_fails_closed(tmp_path, monkeypatch):
    engine = _engine(tmp_path, {"deleted.py": "VALUE = 'needle'\n"})
    (tmp_path / "deleted.py").unlink()
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    result = json.loads(search_source(str(tmp_path), "needle"))

    assert result["status"] == "error"
    assert result["error"] == "source_unavailable"
    assert result["file_path"] == "deleted.py"


def test_logical_spans_full_multiline_string_and_fallback(tmp_path, monkeypatch):
    source = '''TEXT = """alpha
unique multiline marker
omega"""
value = 1
'''
    result = _call(monkeypatch, tmp_path, {"valid.py": source}, "multiline marker")
    match = result["matches"][0]
    assert match["match_kind"] == "multiline_string"
    assert match["content_mode"] == "full"
    assert match["span_start"] == 1 and match["span_end"] == 3
    assert match["text"] == source.split("\nvalue", 1)[0]

    invalid = _call(monkeypatch, tmp_path, {"broken.py": "value = ( unique_fallback\n"}, "unique_fallback")
    fallback = invalid["matches"][0]
    assert fallback["match_kind"] == "line"
    assert fallback["text"] == "value = ( unique_fallback"


def test_large_span_line_map_and_exact_range_expansion(tmp_path, monkeypatch):
    body = ["if unique_large_condition:"] + [f"    value_{index} = {index}" for index in range(1, 25)]
    source = "\n".join(body) + "\n"
    engine = _engine(tmp_path, {"large.py": source})
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    result = json.loads(search_source(str(tmp_path), "unique_large_condition"))
    match = result["matches"][0]
    assert match["content_mode"] == "line_map" and match["collapsed"] is True
    assert match["span_start"] == 1 and match["span_end"] == 25
    assert [item["line"] for item in match["lines"]] == list(range(1, 26))
    assert match["lines"][0]["matched"] is True
    assert match["lines"][0]["text"] == "if unique_large_condition:"
    assert all(len(item.get("preview", "")) <= 60 for item in match["lines"][1:])
    assert all(len(item.get("preview", "").strip().split()) <= 4 for item in match["lines"][1:])
    assert match["expand"] == {
        "tool": "get_source_range", "file_path": "large.py", "start_line": 1, "end_line": 25
    }

    expanded = json.loads(get_source_range(str(tmp_path), "large.py", 2, 4))
    assert expanded["status"] == "ok"
    assert expanded["text"] == "    value_1 = 1\n    value_2 = 2\n    value_3 = 3"


def test_long_match_after_character_2000_remains_visible(tmp_path, monkeypatch):
    source = "VALUE = '" + ("x" * 2100) + "needle'\n"
    result = _call(monkeypatch, tmp_path, {"huge.py": source}, "needle")
    match = result["matches"][0]
    assert "needle" in match["text"]
    assert match["span_start"] == match["span_end"] == 1


def test_span_analysis_runs_once_per_file_with_multiple_hits(tmp_path, monkeypatch):
    parse_calls = 0
    tokenize_calls = 0
    real_parse = source_helpers.ast.parse
    real_tokenize = source_helpers.tokenize.generate_tokens

    def counted_parse(*args, **kwargs):
        nonlocal parse_calls
        parse_calls += 1
        return real_parse(*args, **kwargs)

    def counted_tokenize(*args, **kwargs):
        nonlocal tokenize_calls
        tokenize_calls += 1
        return real_tokenize(*args, **kwargs)

    monkeypatch.setattr(source_helpers.ast, "parse", counted_parse)
    monkeypatch.setattr(source_helpers.tokenize, "generate_tokens", counted_tokenize)
    result = _call(
        monkeypatch,
        tmp_path,
        {"many.py": "FIRST = 'needle'\nSECOND = 'needle'\n# needle\n"},
        "needle",
        limit=None,
    )

    assert result["total_matches"] == 3
    assert parse_calls == 1
    assert tokenize_calls == 1


def test_search_source_large_output_guard_and_retry(tmp_path, monkeypatch):
    files = {
        f"pkg/file_{index:03}.py": f"VALUE = 'guard_needle_{'x' * 400}_{index}'\n"
        for index in range(45)
    }
    engine = _engine(tmp_path, files)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    bounded_raw = search_source(str(tmp_path), "guard_needle", limit=None)
    bounded = json.loads(bounded_raw)
    assert bounded["status"] == "ok"
    assert bounded["_output"]["auto_bounded"] is True
    assert bounded["_output"]["full_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES
    assert len(bounded_raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES

    full_raw = search_source(
        str(tmp_path), "guard_needle", limit=None, allow_large_output=True
    )
    assert len(full_raw.encode("utf-8")) == bounded["_output"]["full_output_bytes"]
    assert json.loads(full_raw)["total_matches"] == 45


def test_search_source_single_match_too_large_falls_back_to_confirmation(tmp_path, monkeypatch):
    files = {
        "pkg/huge.py": f"VALUE = 'guard_needle_{'x' * 18000}'\n"
    }
    engine = _engine(tmp_path, files)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    warning_raw = search_source(str(tmp_path), "guard_needle", limit=None)
    warning = json.loads(warning_raw)
    assert warning["status"] == "confirmation_required"
    assert warning["estimated_output_bytes"] > LARGE_OUTPUT_WARNING_BYTES
    assert "matches" not in warning
