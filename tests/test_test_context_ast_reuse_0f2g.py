import ast
from pathlib import Path
from types import SimpleNamespace

from contextor.core.analysis import test_context as test_context_module
from contextor.core.analysis.test_context import build_test_context
from contextor.core.single_file.builders.layer2_builders import TestContextBuilder
from contextor.core.single_file.builders.registry import BuildState, ContextPayload


def _module(path: Path, *, tree=True):
    return SimpleNamespace(
        path=str(path),
        absolute_path=str(path),
        ast_tree=ast.parse(path.read_text(encoding="utf-8")) if tree else None,
    )


def _fixture(tmp_path: Path, *, test_tree=True, copied_modules=False):
    target = tmp_path / "pkg" / "target.py"
    test_file = tmp_path / "tests" / "test_target.py"
    target.parent.mkdir()
    test_file.parent.mkdir()
    target.write_text("class Target: pass\n", encoding="utf-8")
    test_file.write_text(
        "from pkg.target import Target\n\ndef test_target():\n    assert Target()\n",
        encoding="utf-8",
    )
    canonical_modules = {
        "pkg.target": _module(target),
        "tests.test_target": _module(test_file, tree=test_tree),
    }
    engine_state = SimpleNamespace(
        modules=canonical_modules,
        module_parse_freshness={},
    )
    payload_modules = dict(canonical_modules) if copied_modules else canonical_modules
    payload = ContextPayload(
        file_path=str(target),
        module_id="pkg.target",
        modules=payload_modules,
        root_path=str(tmp_path),
        module=canonical_modules["pkg.target"],
        tree=canonical_modules["pkg.target"].ast_tree,
        source=target.read_text(encoding="utf-8"),
        project_graph=None,
        engine_state=engine_state,
    )
    state = BuildState()
    state.update({"public_api": ["Target"]})
    return payload, state, canonical_modules, test_file


def _builder_result(payload, state):
    return TestContextBuilder().build(payload, state)["test_context"]


def test_authoritative_current_ast_reuse_matches_wrapper_baseline_without_parse(tmp_path, monkeypatch):
    payload, state, modules, test_file = _fixture(tmp_path)
    baseline = build_test_context(
        "pkg.target",
        str(tmp_path),
        ["Target"],
        allowed_python_paths=[module.path for module in modules.values()],
    )
    original_parse = test_context_module.parse_source
    calls = []

    def fail_if_test_candidate(path):
        calls.append(str(path))
        if Path(path).resolve() == test_file.resolve():
            raise AssertionError("current authoritative AST must be reused")
        return original_parse(path)

    monkeypatch.setattr(test_context_module, "parse_source", fail_if_test_candidate)
    assert _builder_result(payload, state) == baseline
    assert calls == []


def test_modules_omitted_preserves_wrapper_parse_fallback_and_result(tmp_path, monkeypatch):
    payload, _state, modules, test_file = _fixture(tmp_path)
    original_parse = test_context_module.parse_source
    calls = []

    def tracked_parse(path):
        calls.append(Path(path).resolve())
        return original_parse(path)

    monkeypatch.setattr(test_context_module, "parse_source", tracked_parse)
    result = build_test_context(
        payload.module_id,
        payload.root_path,
        ["Target"],
        allowed_python_paths=[module.path for module in modules.values()],
    )
    assert test_file.resolve() in calls
    assert result == {
        "test_files": [str(test_file.parent / test_file.name)],
        "tested_symbols": ["Target"],
        "untested_public_symbols": [],
    }


def test_stale_candidate_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
    original_parse = test_context_module.parse_source
    calls = []
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
    )
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_missing_ast_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path, test_tree=False)
    original_parse = test_context_module.parse_source
    calls = []
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
    )
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_nonidentical_modules_mapping_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path, copied_modules=True)
    original_parse = test_context_module.parse_source
    calls = []
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
    )
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_missing_engine_state_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    payload = ContextPayload(
        file_path=payload.file_path,
        module_id=payload.module_id,
        modules=payload.modules,
        root_path=payload.root_path,
        module=payload.module,
        tree=payload.tree,
        source=payload.source,
        project_graph=payload.project_graph,
        engine_state=None,
    )
    original_parse = test_context_module.parse_source
    calls = []
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
    )
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_recovered_current_candidate_reuses_ast_only_after_freshness_restored(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    original_parse = test_context_module.parse_source
    stale_calls = []
    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (stale_calls.append(Path(path).resolve()) or original_parse(path)),
    )
    _builder_result(payload, state)
    assert test_file.resolve() in stale_calls

    payload.engine_state.module_parse_freshness.clear()
    monkeypatch.setattr(
        test_context_module,
        "parse_source",
        lambda path: (_ for _ in ()).throw(AssertionError("recovered AST must be reused")),
    )
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
