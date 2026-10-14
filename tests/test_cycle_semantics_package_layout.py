import ast
import json
from dataclasses import asdict, FrozenInstanceError

import pytest

from contextor.core.cycle_semantics.package_layout import (
    build_package_layout,
    plan_package_import,
)
from contextor.core.cycle_semantics.provenance import (
    extract_import_provenance,
)


def _plan(importer, module_ids, source):
    tree = ast.parse(source)
    facts = extract_import_provenance(
        tree,
        module_id=importer,
        source_key=importer.replace(".", "/") + ".py",
        source_path="C:/synthetic/source.py",
        source_fingerprint="synthetic",
    )
    assert len(facts.occurrences) == 1
    return plan_package_import(
        importer,
        facts.occurrences[0],
        build_package_layout(module_ids),
    )


def test_regular_package_parent_load_chain():
    p = _plan(
        "pkg.user",
        [
            "pkg.__init__",
            "pkg.sub.__init__",
            "pkg.sub.item",
            "pkg.user",
        ],
        "import pkg.sub.item",
    )
    assert tuple(
        (x.name, x.kind, x.indexed_module_ids)
        for x in p.entries[0].load_chain
    ) == (
        ("pkg", "REGULAR_PACKAGE", ("pkg.__init__",)),
        ("pkg.sub", "REGULAR_PACKAGE", ("pkg.sub.__init__",)),
        ("pkg.sub.item", "MODULE_FILE", ("pkg.sub.item",)),
    )
    assert p.entries[0].local_binding == "pkg"
    assert p.entries[0].resolution == "LAYOUT_CHAIN_CANDIDATE"


def test_dotted_import_alias_binds_alias():
    p = _plan(
        "pkg.user",
        ["pkg.__init__", "pkg.sub", "pkg.user"],
        "import pkg.sub as alias",
    )
    assert p.entries[0].local_binding == "alias"
    assert p.entries[0].resolution == "LAYOUT_CHAIN_CANDIDATE"


def test_from_package_member_remains_ambiguous():
    p = _plan(
        "pkg.user",
        ["pkg.__init__", "pkg.child", "pkg.user"],
        "from pkg import child as c",
    )
    item = p.entries[0]
    assert item.possible_child_module == "pkg.child"
    assert item.resolution == "MEMBER_OR_SUBMODULE_UNRESOLVED"
    assert item.local_binding == "c"
    assert tuple(x.name for x in item.load_chain) == ("pkg",)


def test_relative_from_package_initializer():
    p = _plan(
        "pkg.__init__",
        ["pkg.__init__", "pkg.child"],
        "from . import child",
    )
    assert p.entries[0].requested_name == "pkg"
    assert p.entries[0].possible_child_module == "pkg.child"


def test_relative_import_parent_and_beyond_top():
    ids = [
        "pkg.__init__",
        "pkg.deep.__init__",
        "pkg.deep.mod",
        "pkg.child",
    ]
    p = _plan(
        "pkg.deep.mod",
        ids,
        "from .. import child",
    )
    assert p.entries[0].requested_name == "pkg"

    p = _plan(
        "pkg.deep.mod",
        ids,
        "from ... import child",
    )
    assert p.status == "RELATIVE_BEYOND_TOP_LEVEL"
    assert not p.entries


def test_namespace_candidates_are_not_runtime_proof():
    layout = build_package_layout(
        ["pkg.a", "pkg.sub.b"]
    )
    assert tuple(
        (n.name, n.kind)
        for n in layout.nodes
    ) == (
        ("pkg", "NAMESPACE_CANDIDATE"),
        ("pkg.a", "MODULE_FILE"),
        ("pkg.sub", "NAMESPACE_CANDIDATE"),
        ("pkg.sub.b", "MODULE_FILE"),
    )
    assert layout.authority == (
        "REPOSITORY_LAYOUT_CANDIDATES_ONLY"
    )


def test_conflicting_indexed_module_and_package_fail_closed():
    layout = build_package_layout(
        ["pkg", "pkg.__init__", "pkg.sub"]
    )
    assert layout.nodes[0].kind == "AMBIGUOUS_LAYOUT"

    p = _plan(
        "pkg.sub",
        ["pkg", "pkg.__init__", "pkg.sub"],
        "import pkg.sub",
    )
    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"


def test_from_plain_module_not_guessed_as_child():
    p = _plan(
        "pkg.user",
        ["pkg.__init__", "pkg.mod", "pkg.user"],
        "from pkg.mod import method",
    )
    assert p.entries[0].possible_child_module is None
    assert p.entries[0].resolution == "MEMBER_BINDING_UNRESOLVED"


def test_external_import_not_claimed_resolved():
    p = _plan(
        "pkg.user",
        ["pkg.user"],
        "import external.nested",
    )
    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"
    assert all(
        node.kind == "UNKNOWN_MODULE"
        for node in p.entries[0].load_chain
    )


def test_future_directive_keeps_runtime_import_evidence():
    p = _plan(
        "pkg.user",
        ["pkg.user"],
        "from __future__ import annotations",
    )
    assert p.status == "PLANNED"
    assert p.entries[0].requested_name == "__future__"
    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"


def test_duplicate_invalid_and_unindexed_importer():
    with pytest.raises(ValueError):
        build_package_layout(["pkg.mod", "pkg.mod"])

    with pytest.raises(TypeError):
        build_package_layout("pkg.mod")

    tree = ast.parse("import pkg")
    occ = extract_import_provenance(
        tree,
        module_id="unknown",
        source_key="unknown.py",
        source_path="C:/unknown.py",
        source_fingerprint="synthetic",
    ).occurrences[0]

    result = plan_package_import(
        "unknown",
        occ,
        build_package_layout(["pkg.user"]),
    )
    assert result.status == "IMPORTER_NOT_INDEXED"
    assert result.entries == ()


def test_deterministic_immutable_and_json_serializable():
    p = _plan(
        "pkg.user",
        ["pkg.__init__", "pkg.user"],
        "import pkg",
    )
    assert p == _plan(
        "pkg.user",
        ["pkg.user", "pkg.__init__"],
        "import pkg",
    )
    json.dumps(asdict(p))
    assert p.authority == "STATIC_LAYOUT_NOT_RUNTIME_PROOF"

    with pytest.raises(FrozenInstanceError):
        p.status = "FAKE_SUCCESS"
