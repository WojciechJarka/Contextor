"""Source-byte and index-identity binding for conditional namespace paths."""

from __future__ import annotations

import hashlib
from dataclasses import asdict

from contextor.core.source import SourceSnapshot
from contextor.core.cycle_semantics.namespace_path_model import (
    SearchPortion,
)
from contextor.core.cycle_semantics.namespace_source_binding import (
    IndexedSourcePath,
    bind_indexed_namespace_resolution,
)


def _snapshot(text):
    raw = text.encode("utf-8")
    return SourceSnapshot(
        raw,
        hashlib.sha256(raw).hexdigest(),
    )


def _base():
    roots = (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/ns/child.py",
            }),
        ),
    )
    bindings = (
        IndexedSourcePath(
            "pkg.__init__", "root", "pkg/__init__.py"
        ),
        IndexedSourcePath(
            "pkg.ns.child", "root", "pkg/ns/child.py"
        ),
    )
    snapshots = {
        "pkg.__init__": _snapshot("value = 1\n"),
        "pkg.ns.child": _snapshot("value = 7\n"),
    }
    fingerprints = {
        name: snapshot.source_fingerprint
        for name, snapshot in snapshots.items()
    }
    return roots, bindings, fingerprints, snapshots


def _bind(
    roots,
    bindings,
    fingerprints,
    snapshots,
    requested="pkg.ns.child",
    *,
    finder=True,
):
    return bind_indexed_namespace_resolution(
        roots,
        bindings,
        fingerprints,
        snapshots,
        requested,
        standard_finder_assumed=finder,
    )


def test_m01_namespace_source_bytes_are_bound():
    args = _base()
    result = _bind(*args)

    assert result.status == "SOURCE_BOUND_CONDITIONAL"
    assert result.reason is None
    assert len(result.selected_sources) == 2
    assert result.selected_sources[0][0] == "pkg.__init__"
    assert result.selected_sources[1][0] == "pkg.ns.child"
    assert result.resolution.steps[1].kind == "NAMESPACE_PACKAGE"
    assert len(result.evidence_sha256) == 64


def test_m02_two_portions_bind_distinct_children():
    roots = (
        SearchPortion("first", frozenset({"nsp/left.py"})),
        SearchPortion("second", frozenset({"nsp/right.py"})),
    )
    bindings = (
        IndexedSourcePath("nsp.left", "first", "nsp/left.py"),
        IndexedSourcePath("nsp.right", "second", "nsp/right.py"),
    )
    snapshots = {
        "nsp.left": _snapshot("value = 1"),
        "nsp.right": _snapshot("value = 2"),
    }
    hashes = {
        key: value.source_fingerprint
        for key, value in snapshots.items()
    }

    result = _bind(
        roots, bindings, hashes, snapshots, "nsp.right"
    )

    assert result.status == "SOURCE_BOUND_CONDITIONAL"
    assert result.selected_sources == ((
        "nsp.right",
        "second:nsp/right.py",
        hashes["nsp.right"],
    ),)


def test_m03_finder_assumption_is_not_automatic():
    result = _bind(*_base(), finder=False)

    assert result.status == "INDETERMINATE"
    assert result.reason == "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
    assert result.evidence_sha256 is None


def test_m04_modified_raw_bytes_are_rejected():
    roots, rows, hashes, snapshots = _base()
    snapshots["pkg.ns.child"] = _snapshot("value = 99")

    result = _bind(roots, rows, hashes, snapshots)

    assert result.status == "INDETERMINATE"
    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"


def test_m05_forged_fingerprint_is_rejected():
    roots, rows, hashes, snapshots = _base()
    hashes["pkg.ns.child"] = "0" * 64

    result = _bind(roots, rows, hashes, snapshots)

    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"


def test_m06_incorrect_module_path_is_rejected():
    roots, rows, hashes, snapshots = _base()

    bad_rows = (
        rows[0],
        IndexedSourcePath(
            "pkg.ns.child",
            "root",
            "pkg/child.py",
        ),
    )

    result = _bind(
        roots, bad_rows, hashes, snapshots
    )

    assert result.reason == "SOURCE_MODULE_PATH_MISMATCH"


def test_m07_unbound_python_inventory_entry_is_rejected():
    roots, rows, hashes, snapshots = _base()
    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({"pkg/extra.py"}),
        ),
    )

    result = _bind(roots, rows, hashes, snapshots)

    assert result.reason == "INVENTORY_SOURCE_BINDING_MISMATCH"


def test_m08_missing_capture_is_rejected():
    roots, rows, hashes, snapshots = _base()
    del snapshots["pkg.ns.child"]

    result = _bind(roots, rows, hashes, snapshots)

    assert result.reason == "SOURCE_INDEX_DOMAIN_MISMATCH"


def test_m09_duplicate_module_identity_is_rejected():
    roots, rows, hashes, snapshots = _base()

    result = _bind(
        roots,
        rows + (rows[0],),
        hashes,
        snapshots,
    )

    assert result.reason == "DUPLICATE_SOURCE_BINDING"


def test_m10_alternative_loader_remains_indeterminate():
    roots, rows, hashes, snapshots = _base()
    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({
                "pkg/ns/child.cp310-win_amd64.pyd",
            }),
        ),
    )

    result = _bind(roots, rows, hashes, snapshots)

    assert result.status == "INDETERMINATE"
    assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"


def test_m11_inventory_order_changes_digest():
    roots, rows, hashes, snapshots = _base()

    extra_root = SearchPortion(
        "other",
        frozenset({"notes.txt"}),
    )

    first = _bind(
        roots + (extra_root,),
        rows,
        hashes,
        snapshots,
    )
    second = _bind(
        (extra_root,) + roots,
        rows,
        hashes,
        snapshots,
    )

    assert first.status == "SOURCE_BOUND_CONDITIONAL"
    assert second.status == "SOURCE_BOUND_CONDITIONAL"
    assert first.evidence_sha256 != second.evidence_sha256


def test_m12_source_byte_budget_fails_closed():
    roots, rows, hashes, snapshots = _base()

    oversized = b"x" * (2 * 1024 * 1024 + 1)
    digest = hashlib.sha256(oversized).hexdigest()

    snapshots["pkg.ns.child"] = SourceSnapshot(
        oversized,
        digest,
    )
    hashes["pkg.ns.child"] = digest

    result = _bind(roots, rows, hashes, snapshots)

    assert result.reason == "SOURCE_BYTE_LIMIT"
    assert result.evidence_sha256 is None


def test_m13_deterministic_without_live_authority():
    args = _base()

    first = _bind(*args)
    second = _bind(*args)

    assert first == second
    assert asdict(first) == asdict(second)
    assert first.authority == (
        "CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_"
        "NOT_RUNTIME_OR_LIVE_CERTIFIED"
    )
    assert first.status == "SOURCE_BOUND_CONDITIONAL"


def test_m14_unindexed_shadowing_source_blocks_binding():
    roots, rows, hashes, snapshots = _base()

    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({"pkg/ns.py"}),
        ),
    )

    result = _bind(roots, rows, hashes, snapshots)

    assert result.status == "INDETERMINATE"
    assert result.reason == "MODULE_IS_NOT_A_PACKAGE"
    assert result.evidence_sha256 is None
    assert result.selected_sources == ()
    assert result.resolution is not None
    assert result.resolution.status == "INDETERMINATE"
    assert result.resolution.steps[-1].kind == "MODULE_FILE"
    assert result.resolution.steps[-1].source == "root:pkg/ns.py"


def test_m15_indexed_shadowing_source_still_blocks_child():
    roots, rows, hashes, snapshots = _base()

    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({"pkg/ns.py"}),
        ),
    )

    rows = rows + (
        IndexedSourcePath("pkg.ns", "root", "pkg/ns.py"),
    )
    snapshots["pkg.ns"] = _snapshot("value = 3\n")
    hashes["pkg.ns"] = snapshots["pkg.ns"].source_fingerprint

    result = _bind(roots, rows, hashes, snapshots)

    assert result.status == "INDETERMINATE"
    assert result.reason == "MODULE_IS_NOT_A_PACKAGE"
    assert result.evidence_sha256 is None
    assert result.selected_sources == ()
    assert result.resolution is not None
    assert result.resolution.steps[-1].kind == "MODULE_FILE"
    assert result.resolution.steps[-1].source == "root:pkg/ns.py"
