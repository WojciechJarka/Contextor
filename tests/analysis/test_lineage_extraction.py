import ast
import codecs
import hashlib
import sys

import pytest

from contextor.core.analysis.incremental.preparation import prepare_source_update
from contextor.core.analysis.lineage_extraction import (
    LineageExtractionLimits,
    build_local_occurrence_id,
    extract_lineage_source_facts,
    parse_local_occurrence_id,
)
from contextor.core.domain.lineage_facts import (
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    ResolutionKind,
)
from contextor.core.source import parse_source_with_fingerprint
from contextor.core.symbol_engine import indexer as indexer_module

FINGERPRINT = "a" * 64


def _decoded_anchors(facts):
    return [(anchor, parse_local_occurrence_id(anchor.local_id)) for anchor in facts.anchors]


def test_local_occurrence_id_round_trip_and_multi_name_disambiguation():
    first = build_local_occurrence_id("global_declaration", "0.1", "x:y%z", ordinal=0)
    second = build_local_occurrence_id("global_declaration", "0.1", "other", ordinal=1)
    assert first != second
    assert parse_local_occurrence_id(first) == ("global_declaration", "0.1", 0, "x:y%z")
    assert parse_local_occurrence_id(second) == ("global_declaration", "0.1", 1, "other")


def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monkeypatch):
    tree = ast.parse("import pkg.mod as pm\nvalue = 1\ndef run(arg):\n    local = arg\n    return local\n")
    monkeypatch.setattr("builtins.open", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("extractor performed filesystem I/O")))
    first = extract_lineage_source_facts(tree, source_key="pkg/mod.py", source_fingerprint=FINGERPRINT)
    second = extract_lineage_source_facts(tree, source_key="pkg/mod.py", source_fingerprint=FINGERPRINT)
    assert first == second
    assert first.status is LineageFamilyStatus.FRESH
    assert first.flows and first.surfaces == ()
    assert len({item.local_id for item in first.anchors}) == len(first.anchors)
    module = sys.modules["contextor.core.analysis.lineage_extraction"]
    assert "PersistentIdentityRegistry" not in vars(module)
    assert "RepositoryAnalysisState" not in vars(module)
    assert "SemanticEndpoint" not in vars(module)


def test_typed_parameter_ids_bind_and_defaults_need_no_ast_reread():
    tree = ast.parse("def run(a, /, b=1, *items, flag=2, **extra):\n    return b\n")
    facts = extract_lineage_source_facts(tree, source_key="pkg.py", source_fingerprint=FINGERPRINT)
    parsed_parameters = {
        parse_local_occurrence_id(anchor.local_id)
        for anchor in facts.anchors
        if anchor.kind == "parameter"
    }
    assert {(kind, ordinal, name) for kind, _path, ordinal, name in parsed_parameters} == {
        ("parameter_posonly", 0, "a"),
        ("parameter_poskw", 0, "b"),
        ("parameter_vararg", 0, "items"),
        ("parameter_kwonly", 0, "flag"),
        ("parameter_varkw", 0, "extra"),
    }
    binds = [flow for flow in facts.flows if flow.relation is LineageRelation.BINDS]
    assert len(binds) == 5
    assert all(
        flow.source.kind is ExtractedSymbolicKind.PARAMETER
        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and flow.source.source_local_id is not None
        for flow in binds
    )
    for flow in binds:
        kind, _path, _ordinal, name = parse_local_occurrence_id(flow.source.source_local_id)
        assert kind.startswith("parameter_")
        assert name
    defaults = [flow for flow in facts.flows if flow.relation is LineageRelation.DEFAULTS_TO_PARAMETER]
    assert len(defaults) == 2
    assert all(
        isinstance(flow.source, ExtractedOccurrenceRef)
        and flow.target.kind is ExtractedSymbolicKind.PARAMETER
        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        for flow in defaults
    )


def test_lexical_owners_parameters_comprehensions_and_declarations():
    tree = ast.parse("seed = 1\ndef outer(x=(y := seed)):\n    global g, h\n    def inner(arg):\n        nonlocal x\n        return arg\n    values = [item for item in range(3)]\n    return inner\n")
    facts = extract_lineage_source_facts(tree, source_key="pkg.py", source_fingerprint=FINGERPRINT)
    decoded = _decoded_anchors(facts)
    by_name = {}
    for anchor, (kind, _path, ordinal, name) in decoded:
        if name is not None:
            by_name.setdefault((kind, name), []).append((anchor, ordinal))
    module_anchor = next(anchor for anchor, (kind, *_rest) in decoded if kind == "module")
    outer = by_name[("function", "outer")][0][0]
    inner = by_name[("function", "inner")][0][0]
    assert outer.owner_local_id == module_anchor.local_id
    assert inner.owner_local_id == outer.local_id
    assert by_name[("parameter_poskw", "x")][0][0].owner_local_id == outer.local_id
    assert by_name[("parameter_poskw", "arg")][0][0].owner_local_id == inner.local_id
    assert by_name[("binding", "y")][0][0].owner_local_id == module_anchor.local_id
    comprehension = next(anchor for anchor, (kind, *_rest) in decoded if kind == "comprehension")
    assert by_name[("binding", "item")][0][0].owner_local_id == comprehension.local_id
    assert {name: ordinal for _anchor, (kind, _path, ordinal, name) in decoded if kind == "global_declaration"} == {"g": 0, "h": 1}
    assert by_name[("nonlocal_declaration", "x")][0][0].owner_local_id == inner.local_id


def test_attribute_and_subscript_store_are_not_1b_binding_anchors():
    facts = extract_lineage_source_facts(ast.parse("obj.attr = value\nitems[index] = value\nplain = value\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT)
    names = {name for _anchor, (kind, _path, _ordinal, name) in _decoded_anchors(facts) if kind == "binding"}
    assert "plain" in names and "attr" not in names and "items" not in names


def test_resource_limits_fail_closed_without_partial_fresh_slice():
    node_limited = extract_lineage_source_facts(ast.parse("x = 1\ny = 2\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT, limits=LineageExtractionLimits(max_nodes=1, max_ast_depth=100))
    assert node_limited.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert node_limited.resource_limit_reason == "node_limit"
    assert node_limited.anchors == () and node_limited.flows == () and node_limited.surfaces == ()
    depth_limited = extract_lineage_source_facts(ast.parse("def f():\n    if True:\n        x = 1\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT, limits=LineageExtractionLimits(max_nodes=100, max_ast_depth=1))
    assert depth_limited.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert depth_limited.resource_limit_reason == "ast_depth_limit"


@pytest.mark.parametrize("use_bom", [False, True])
def test_parsed_source_fingerprint_is_exact_raw_sha256_and_encoding_safe(tmp_path, use_bom):
    path = tmp_path / "encoded.py"
    raw = codecs.BOM_UTF8 + "value = 'ą'\n".encode("utf-8") if use_bom else b"# -*- coding: cp1250 -*-\n" + "value = 'ą'\n".encode("cp1250")
    path.write_bytes(raw)
    parsed = parse_source_with_fingerprint(path)
    assert isinstance(parsed.tree, ast.AST)
    assert parsed.source_fingerprint == hashlib.sha256(raw).hexdigest()


def test_full_index_transports_transient_lineage_on_cache_miss_and_hit(tmp_path, monkeypatch):
    source = tmp_path / "pkg.py"
    source.write_text("value = 1\n", encoding="utf-8")
    class FakeCache:
        def __init__(self): self.data = None
        def get(self, _path): return self.data
        def set(self, _path, data): self.data = data
    cache = FakeCache()
    monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: cache)
    first = indexer_module._process_single_file(str(source), str(tmp_path))
    second = indexer_module._process_single_file(str(source), str(tmp_path))
    assert second["lineage_facts"] == first["lineage_facts"]
    assert first["lineage_facts"].source_key == "pkg.py"
    assert first["lineage_facts"].source_fingerprint == hashlib.sha256(source.read_bytes()).hexdigest()


def test_repository_index_collects_source_keyed_transient_lineage(tmp_path, monkeypatch):
    (tmp_path / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    class FakeCache:
        def get(self, _path): return None
        def set(self, _path, _data): return None
    monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: FakeCache())
    result = indexer_module.index_repository(str(tmp_path))
    assert set(result.lineage_facts_by_source) == {"pkg.py"}


def test_incremental_preparation_carries_transient_lineage_and_errors_do_not(tmp_path):
    path = tmp_path / "pkg.py"
    path.write_text("value = 1\n", encoding="utf-8")
    prepared = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
    assert not prepared.has_error and prepared.extracted_lineage_facts is not None
    assert prepared.extracted_lineage_facts.surfaces == ()
    path.write_text("def broken(:\n", encoding="utf-8")
    broken = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
    assert broken.has_error and broken.error_status == "SYNTAX_ERROR" and broken.extracted_lineage_facts is None
    missing = prepare_source_update(file_path=tmp_path / "missing.py", module_path="missing", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="missing.py")
    assert missing.has_error and missing.error_status == "ERROR" and missing.extracted_lineage_facts is None
