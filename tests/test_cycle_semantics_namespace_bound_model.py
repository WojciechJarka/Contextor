"""Source-bound conditional PEP 420 regression contracts."""

from __future__ import annotations

import hashlib

from contextor.core.source import SourceSnapshot
from contextor.core.cycle_semantics.namespace_bound_model import (
    evaluate_source_bound_conditional_namespace_import_order,
)
from contextor.core.cycle_semantics.namespace_path_model import (
    SearchPortion,
)
from contextor.core.cycle_semantics.namespace_source_binding import (
    IndexedSourcePath,
)


def _snapshot(text):
    raw = text.encode("utf-8")
    return SourceSnapshot(
        raw=raw,
        source_fingerprint=hashlib.sha256(raw).hexdigest(),
    )


def _case(*, hazard=False):
    texts = {
        "pkg.__init__": "pass\n",
        "pkg.ns.a": (
            "import pkg.ns.b\n"
            "value = 1\n"
            if hazard
            else
            "value = 1\n"
            "import pkg.ns.b\n"
        ),
        "pkg.ns.b": "from pkg.ns.a import value\n",
    }

    snapshots = {
        module_id: _snapshot(text)
        for module_id, text in texts.items()
    }

    fingerprints = {
        module_id: snapshot.source_fingerprint
        for module_id, snapshot in snapshots.items()
    }

    bindings = (
        IndexedSourcePath(
            "pkg.__init__",
            "root",
            "pkg/__init__.py",
        ),
        IndexedSourcePath(
            "pkg.ns.a",
            "root",
            "pkg/ns/a.py",
        ),
        IndexedSourcePath(
            "pkg.ns.b",
            "root",
            "pkg/ns/b.py",
        ),
    )

    roots = (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/ns/a.py",
                "pkg/ns/b.py",
            }),
        ),
    )

    return roots, bindings, fingerprints, snapshots


def _evaluate(
    args,
    entry="pkg.ns.a",
    *,
    finder=True,
):
    return evaluate_source_bound_conditional_namespace_import_order(
        *args,
        entry,
        standard_finder_assumed=finder,
    )


def test_p6_source_bound_conditional_pass():
    result = _evaluate(_case())

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.source_evidence_sha256 is not None
    assert len(result.source_evidence_sha256) == 64
    assert result.conditional_assessment is not None
    assert result.conditional_assessment.outcome == (
        "CONDITIONAL_MODEL_PASS"
    )
    assert result.authority == (
        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_p6_source_bound_hazard():
    result = _evaluate(_case(hazard=True))

    assert result.outcome == (
        "CONDITIONAL_EARLY_BINDING_HAZARD"
    )
    assert result.conditional_assessment is not None
    assert result.conditional_assessment.model_assessment is not None
    assert (
        result.conditional_assessment
        .model_assessment.symbol
    ) == "value"


def test_p6_entry_order_is_not_assumed():
    result = _evaluate(
        _case(hazard=True),
        entry="pkg.ns.b",
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"


def test_p6_finder_assumption_is_required():
    result = _evaluate(
        _case(),
        finder=False,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
    )
    assert result.conditional_assessment is None


def _p9_source_bound_annotated_case():
    roots, bindings, hashes, snapshots = _case()

    snapshots["pkg.ns.a"] = _snapshot(
        "class Holder:\n"
        "    def method(self, x: Later) -> Later:\n"
        "        pass\n"
        "value = 1\n"
        "import pkg.ns.b\n"
    )

    hashes["pkg.ns.a"] = (
        snapshots["pkg.ns.a"].source_fingerprint
    )

    return roots, bindings, hashes, snapshots


def test_p9_source_bound_default_stays_unknown():
    result = _evaluate(
        _p9_source_bound_annotated_case(),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"


def test_p9_source_bound_deferred_cpython315():
    result = evaluate_source_bound_conditional_namespace_import_order(
        *_p9_source_bound_annotated_case(),
        "pkg.ns.a",
        standard_finder_assumed=True,
        target_python_version=(3, 15),
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.source_evidence_sha256 is not None
    assert result.conditional_assessment is not None
    assert (
        result.conditional_assessment.target_python_version
        == (3, 15)
    )
    assert result.authority == (
        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_p9_source_bound_deferred_still_checks_hash():
    roots, bindings, hashes, snapshots = (
        _p9_source_bound_annotated_case()
    )

    hashes["pkg.ns.a"] = "0" * 64

    result = evaluate_source_bound_conditional_namespace_import_order(
        roots,
        bindings,
        hashes,
        snapshots,
        "pkg.ns.a",
        standard_finder_assumed=True,
        target_python_version=(3, 15),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
    assert result.source_evidence_sha256 is None


def test_p9_source_bound_bad_interpreter_rejected():
    result = evaluate_source_bound_conditional_namespace_import_order(
        *_p9_source_bound_annotated_case(),
        "pkg.ns.a",
        standard_finder_assumed=True,
        target_python_version=(3, 14),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "TARGET_INTERPRETER_UNVERIFIED"
    assert result.source_evidence_sha256 is None


def test_p6_changed_bytes_fail_closed():
    roots, bindings, hashes, snapshots = _case()
    snapshots["pkg.ns.a"] = _snapshot(
        "value = 99\nimport pkg.ns.b\n"
    )

    result = _evaluate(
        (roots, bindings, hashes, snapshots)
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
    assert result.source_evidence_sha256 is None
    assert result.conditional_assessment is None


def test_p6_missing_indexed_snapshot_fails():
    roots, bindings, hashes, snapshots = _case()
    del snapshots["pkg.ns.a"]

    result = _evaluate(
        (roots, bindings, hashes, snapshots)
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "SOURCE_INDEX_DOMAIN_MISMATCH"


def test_p6_syntax_failure_after_valid_binding():
    roots, bindings, hashes, snapshots = _case()

    snapshots["pkg.ns.a"] = _snapshot(
        "def invalid(:\n"
    )
    hashes["pkg.ns.a"] = (
        snapshots["pkg.ns.a"].source_fingerprint
    )

    result = _evaluate(
        (roots, bindings, hashes, snapshots)
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "SOURCE_PARSE_FAILED:pkg.ns.a"
    )
    assert result.source_evidence_sha256 is not None
    assert result.conditional_assessment is None


def test_p6_unindexed_namespace_entry_rejected():
    result = _evaluate(
        _case(),
        entry="pkg.ns",
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "ENTRY_SOURCE_NOT_INDEXED"
    assert result.conditional_assessment is None


def test_p6_unindexed_shadowing_source_rejected():
    roots, bindings, hashes, snapshots = _case()

    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({
                "pkg/ns/__init__.py",
            }),
        ),
    )

    result = _evaluate(
        (roots, bindings, hashes, snapshots)
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "INVENTORY_SOURCE_BINDING_MISMATCH"
    )


def test_p6_eager_external_import_unknown():
    roots, bindings, hashes, snapshots = _case()

    snapshots["pkg.ns.a"] = _snapshot(
        "import os\n"
        "value = 1\n"
        "import pkg.ns.b\n"
    )
    hashes["pkg.ns.a"] = (
        snapshots["pkg.ns.a"].source_fingerprint
    )

    result = _evaluate(
        (roots, bindings, hashes, snapshots)
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
    assert result.source_evidence_sha256 is not None

    assert result.conditional_assessment is not None

    model = (
        result.conditional_assessment.model_assessment
    )

    assert model is not None
    assert model.outcome == "UNKNOWN"
    assert model.reached_unmodeled_import is not None

    blocker = model.reached_unmodeled_import

    assert blocker.importer == "pkg.ns.a"
    assert blocker.operation == "IMPORT"
    assert blocker.target == "os"
    assert blocker.symbol is None
    assert blocker.line == 1
    assert blocker.column == 0


def test_p6_two_portions_source_bound():
    roots = (
        SearchPortion(
            "first",
            frozenset({"ns/a.py"}),
        ),
        SearchPortion(
            "second",
            frozenset({"ns/b.py"}),
        ),
    )

    bindings = (
        IndexedSourcePath(
            "ns.a",
            "first",
            "ns/a.py",
        ),
        IndexedSourcePath(
            "ns.b",
            "second",
            "ns/b.py",
        ),
    )

    snapshots = {
        "ns.a": _snapshot(
            "value = 1\nimport ns.b\n"
        ),
        "ns.b": _snapshot(
            "from ns.a import value\n"
        ),
    }

    hashes = {
        key: item.source_fingerprint
        for key, item in snapshots.items()
    }

    result = _evaluate(
        (roots, bindings, hashes, snapshots),
        entry="ns.a",
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.source_evidence_sha256 is not None


def test_p6_deterministic_digest_and_outcome():
    args = _case()

    first = _evaluate(args)
    second = _evaluate(args)

    assert first == second
    assert first.outcome == "CONDITIONAL_MODEL_PASS"
    assert (
        first.source_evidence_sha256
        == second.source_evidence_sha256
    )


def test_p7_source_bound_308_module_cohort():
    names = tuple(
        f"ns.m{index:05d}"
        for index in range(308)
    )

    roots = (
        SearchPortion(
            "root",
            frozenset(
                name.replace(".", "/") + ".py"
                for name in names
            ),
        ),
    )

    bindings = tuple(
        IndexedSourcePath(
            name,
            "root",
            name.replace(".", "/") + ".py",
        )
        for name in names
    )

    raw = b"pass\n"
    digest = hashlib.sha256(raw).hexdigest()
    snapshot = SourceSnapshot(raw, digest)

    fingerprints = {
        name: digest
        for name in names
    }

    snapshots = {
        name: snapshot
        for name in names
    }

    result = evaluate_source_bound_conditional_namespace_import_order(
        roots,
        bindings,
        fingerprints,
        snapshots,
        "ns.m00000",
        standard_finder_assumed=True,
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.source_evidence_sha256 is not None
    assert result.conditional_assessment is not None
    assert result.conditional_assessment.outcome == (
        "CONDITIONAL_MODEL_PASS"
    )
    assert result.authority == (
        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_p8_unreachable_module_still_source_bound():
    roots, bindings, hashes, snapshots = _case()

    extra = "pkg.ns.unused"
    path = "pkg/ns/unused.py"

    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({path}),
        ),
    )

    bindings = bindings + (
        IndexedSourcePath(extra, "root", path),
    )

    raw = b"raise RuntimeError('unused')\n"
    digest = hashlib.sha256(raw).hexdigest()

    snapshots[extra] = SourceSnapshot(raw, digest)
    hashes[extra] = digest

    result = _evaluate(
        (roots, bindings, hashes, snapshots),
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.source_evidence_sha256 is not None


def test_p8_unreachable_module_bad_hash_still_rejected():
    roots, bindings, hashes, snapshots = _case()

    extra = "pkg.ns.unused"
    path = "pkg/ns/unused.py"

    roots = (
        SearchPortion(
            "root",
            roots[0].files | frozenset({path}),
        ),
    )

    bindings = bindings + (
        IndexedSourcePath(extra, "root", path),
    )

    raw = b"raise RuntimeError('unused')\n"
    digest = hashlib.sha256(raw).hexdigest()

    snapshots[extra] = SourceSnapshot(raw, digest)
    hashes[extra] = "0" * 64

    result = _evaluate(
        (roots, bindings, hashes, snapshots),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
    assert result.source_evidence_sha256 is None
    assert result.conditional_assessment is None
