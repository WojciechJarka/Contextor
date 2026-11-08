"""Source-bound conditional PEP 420 regression contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pytest

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


def _external_case(source, *, child=None):
    roots, bindings, hashes, snapshots = _case()
    snapshots["pkg.ns.a"] = _snapshot(source)
    hashes["pkg.ns.a"] = snapshots["pkg.ns.a"].source_fingerprint
    if child is not None:
        snapshots["pkg.ns.b"] = _snapshot(child)
        hashes["pkg.ns.b"] = snapshots["pkg.ns.b"].source_fingerprint
    return roots, bindings, hashes, snapshots


def _external_result(source, *, assume=False, child=None):
    return evaluate_source_bound_conditional_namespace_import_order(
        *_external_case(source, child=child),
        "pkg.ns.a",
        standard_finder_assumed=True,
        assume_passive_external_imports=assume,
    )


_FROZEN_CLASS = (
    "@dataclass(frozen=True)\n"
    "class Graph:\n"
    "    hard_edges: dict[str, set[str]]\n"
    "    soft_edges: dict[str, set[str]]\n"
    "    def without_module(self, name: str) -> \"Graph\":\n"
    "        return self\n"
)


def _dataclass_result(source, *, decorate=False, external=True, child=None):
    return evaluate_source_bound_conditional_namespace_import_order(
        *_external_case(source, child=child),
        "pkg.ns.a",
        standard_finder_assumed=True,
        target_python_version=(3, 15),
        assume_passive_external_imports=external,
        assume_frozen_dataclass_decoration=decorate,
    )


def test_frozen_dataclass_t01_default_unknown():
    result = _dataclass_result(
        "from dataclasses import dataclass\n" + _FROZEN_CLASS
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "UNKNOWN"
    assert tuple(x.target for x in model.assumed_external_imports) == (
        "dataclasses",
    )
    assert model.assumed_dataclass_decorations == ()
    assert result.class_decorator_policy == "STOP_AT_UNMODELED"


def test_frozen_dataclass_t02_exact_conditional_pass():
    result = _dataclass_result(
        "from dataclasses import dataclass\n" + _FROZEN_CLASS,
        decorate=True,
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert model.outcome == "MODEL_PASS"
    assert model.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    assert len(model.assumed_external_imports) == 1
    assert model.assumed_external_imports[0].target == "dataclasses"
    assert len(model.assumed_dataclass_decorations) == 1
    row = model.assumed_dataclass_decorations[0]
    assert (row.module, row.class_name, row.decorator) == (
        "pkg.ns.a", "Graph", "dataclasses.dataclass(frozen=True)"
    )
    assert (row.line, row.column) == (2, 1)
    assert result.class_decorator_policy == "ASSUME_PASSIVE_FROZEN_DATACLASS"
    operations = [event.operation for event in model.events]
    assert operations.index("ASSUMED_FROZEN_DATACLASS_DECORATION") < (
        operations.index("DEFINE_PASSIVE_CLASS")
    )


def test_frozen_dataclass_t03_internal_hazard_retained():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "import pkg.ns.b\n"
        "@dataclass(frozen=True)\n"
        "class Graph:\n"
        "    value: int\n",
        decorate=True,
        child="from pkg.ns.a import Graph\n",
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "CONDITIONAL_EARLY_BINDING_HAZARD"
    assert model.outcome == "EARLY_BINDING_HAZARD"
    assert (model.target_module, model.symbol) == ("pkg.ns.a", "Graph")
    assert len(model.assumed_external_imports) == 1
    assert model.assumed_dataclass_decorations == ()


def test_frozen_dataclass_t04_class_bound_before_import():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Graph:\n"
        "    value: int\n"
        "import pkg.ns.b\n",
        decorate=True,
        child="from pkg.ns.a import Graph\n",
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert len(model.assumed_dataclass_decorations) == 1
    assert any(
        event.operation == "FROM" and event.symbol == "Graph"
        for event in model.events
    )


@pytest.mark.parametrize(
    "decorator",
    ["other(frozen=True)", "dataclass(frozen=False)",
     "dataclass(frozen=flag)", "dataclass",
     "dataclass(slots=True, frozen=True)"],
)
def test_frozen_dataclass_t05_t06_nonexact_unknown(decorator):
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        f"@{decorator}\nclass Graph:\n    value: int\n",
        decorate=True,
    )
    assert result.outcome == "UNKNOWN"
    assert (
        result.conditional_assessment.model_assessment
        .assumed_dataclass_decorations
    ) == ()


def test_frozen_dataclass_t07_dynamic_field_unknown():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Graph:\n"
        "    value: int = field(default_factory=make)\n",
        decorate=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()


@pytest.mark.parametrize(
    "class_text",
    [
        "class Graph:\n    import os\n",
        "class Graph:\n    run()\n",
        "class Graph(metaclass=Meta):\n    value: int\n",
        "class Graph(Base):\n    value: int\n",
    ],
)
def test_frozen_dataclass_t08_class_effects_unknown(class_text):
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n" + class_text,
        decorate=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()


def test_frozen_dataclass_t09_rebound_decorator_unknown():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "dataclass = 1\n"
        "@dataclass(frozen=True)\n"
        "class Graph:\n    value: int\n",
        decorate=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()


def test_frozen_dataclass_t10_builtin_shadow_unknown():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "dict = 1\n"
        "@dataclass(frozen=True)\n"
        "class Graph:\n    value: dict[str, int]\n",
        decorate=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()


def test_frozen_dataclass_t11_unreached_definition():
    result = _dataclass_result(
        "from dataclasses import dataclass\n"
        "def later():\n"
        "    @dataclass(frozen=True)\n"
        "    class Graph:\n"
        "        value: int\n",
        decorate=True,
    )
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.conditional_assessment.model_assessment.assumed_dataclass_decorations == ()


def test_frozen_dataclass_t12_fingerprint_mismatch():
    roots, bindings, hashes, snapshots = _external_case(
        "from dataclasses import dataclass\n" + _FROZEN_CLASS
    )
    snapshots["pkg.ns.a"] = _snapshot("changed = True\n")
    result = evaluate_source_bound_conditional_namespace_import_order(
        roots, bindings, hashes, snapshots, "pkg.ns.a",
        standard_finder_assumed=True,
        target_python_version=(3, 15),
        assume_passive_external_imports=True,
        assume_frozen_dataclass_decoration=True,
    )
    assert (result.outcome, result.reason) == (
        "UNKNOWN", "SOURCE_FINGERPRINT_MISMATCH"
    )
    assert result.conditional_assessment is None


def test_frozen_dataclass_t13_invalid_policy():
    result = evaluate_source_bound_conditional_namespace_import_order(
        *_external_case("pass\n"), "pkg.ns.a",
        assume_passive_external_imports=True,
        assume_frozen_dataclass_decoration="yes",
    )
    assert (result.outcome, result.reason) == (
        "UNKNOWN", "INVALID_DATACLASS_DECORATOR_ASSUMPTION"
    )


def test_frozen_dataclass_t14_requires_external_policy():
    result = _dataclass_result("pass\n", decorate=True, external=False)
    assert (result.outcome, result.reason) == (
        "UNKNOWN", "DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY"
    )


def test_frozen_dataclass_t15_deterministic():
    args = _external_case(
        "from dataclasses import dataclass\n" + _FROZEN_CLASS
    )
    before = dict(args[3])
    first = evaluate_source_bound_conditional_namespace_import_order(
        *args, "pkg.ns.a", standard_finder_assumed=True,
        target_python_version=(3, 15),
        assume_passive_external_imports=True,
        assume_frozen_dataclass_decoration=True,
    )
    second = evaluate_source_bound_conditional_namespace_import_order(
        *args, "pkg.ns.a", standard_finder_assumed=True,
        target_python_version=(3, 15),
        assume_passive_external_imports=True,
        assume_frozen_dataclass_decoration=True,
    )
    assert first == second
    assert first.conditional_assessment.model_assessment.events == (
        second.conditional_assessment.model_assessment.events
    )
    assert first.conditional_assessment.model_assessment.assumed_dataclass_decorations == (
        second.conditional_assessment.model_assessment.assumed_dataclass_decorations
    )
    assert json.dumps(asdict(first), sort_keys=True) == json.dumps(
        asdict(second), sort_keys=True
    )
    assert args[3] == before


def test_external_policy_t01_default_still_unknown():
    result = _external_result("import os\nvalue=1\nimport pkg.ns.b\n")
    model = result.conditional_assessment.model_assessment
    assert (result.outcome, result.reason) == (
        "UNKNOWN", "RESTRICTED_MODEL_UNKNOWN"
    )
    assert result.external_import_policy == "STOP_AT_UNMODELED"
    assert result.conditional_assessment.external_import_policy == "STOP_AT_UNMODELED"
    assert model.outcome == "UNKNOWN"
    assert model.reached_unmodeled_import.target == "os"
    assert model.assumed_external_imports == ()


def test_external_policy_t02_opt_in_safe_order():
    result = _external_result(
        "import os\nvalue=1\nimport pkg.ns.b\n", assume=True
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.external_import_policy == "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
    assert result.conditional_assessment.external_import_policy == "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
    assert model.outcome == "MODEL_PASS"
    assert model.evidence_scope == (
        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
        "ASSUMPTION_NOT_RUNTIME_PROOF"
    )
    assert model.reached_unmodeled_import is None
    assert len(model.assumed_external_imports) == 1
    blocker = model.assumed_external_imports[0]
    assert (
        blocker.importer, blocker.operation, blocker.target,
        blocker.symbol, blocker.line, blocker.column,
    ) == ("pkg.ns.a", "IMPORT", "os", None, 1, 0)
    assert "ASSUMED_EXTERNAL_IMPORT" in (
        event.operation for event in model.events
    )


def test_external_policy_t03_early_hazard_remains_conditional():
    source = "import os\nimport pkg.ns.b\nvalue=1\n"
    default = _external_result(source)
    result = _external_result(source, assume=True)
    model = result.conditional_assessment.model_assessment
    assert default.outcome == "UNKNOWN"
    assert default.conditional_assessment.model_assessment.target_module == "os"
    assert result.outcome == "CONDITIONAL_EARLY_BINDING_HAZARD"
    assert model.outcome == "EARLY_BINDING_HAZARD"
    assert model.target_module == "pkg.ns.a"
    assert model.symbol == "value"
    assert len(model.assumed_external_imports) == 1
    assert model.assumed_external_imports[0].target == "os"


def test_external_policy_t04_internal_missing_not_skipped():
    result = _external_result(
        "import pkg.ns.missing\nvalue=1\n", assume=True
    )
    assert result.outcome == "UNKNOWN"
    if result.conditional_assessment is not None:
        model = result.conditional_assessment.model_assessment
        assert model.outcome == "UNKNOWN"
        assert model.target_module == "pkg.ns.missing"
        assert model.assumed_external_imports == ()


def test_external_policy_t05_opaque_use_unknown():
    result = _external_result(
        "import os\nvalue = os.path\nimport pkg.ns.b\n",
        assume=True,
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "UNKNOWN"
    assert tuple(x.target for x in model.assumed_external_imports) == ("os",)


def test_external_policy_t06_earlier_unsupported_effect_stops():
    result = _external_result(
        "import os\nunknown_function()\nimport pkg.ns.b\n",
        assume=True,
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "UNKNOWN"
    assert tuple(x.target for x in model.assumed_external_imports) == ("os",)
    assert not any(
        event.target == "pkg.ns.b" and event.operation == "START_IMPORT"
        for event in model.events
    )


def test_external_policy_t07_from_import():
    result = _external_result(
        "from dataclasses import dataclass\nvalue=1\nimport pkg.ns.b\n",
        assume=True,
    )
    model = result.conditional_assessment.model_assessment
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert model.outcome == "MODEL_PASS"
    assert len(model.assumed_external_imports) == 1
    blocker = model.assumed_external_imports[0]
    assert (
        blocker.operation, blocker.target, blocker.symbol,
        blocker.line, blocker.column,
    ) == ("FROM", "dataclasses", "dataclass", 1, 0)


def test_external_policy_t08_invalid_policy():
    args = _external_case("import os\nvalue=1\nimport pkg.ns.b\n")
    result = evaluate_source_bound_conditional_namespace_import_order(
        *args, "pkg.ns.a", standard_finder_assumed=True,
        assume_passive_external_imports="yes",
    )
    assert (result.outcome, result.reason) == (
        "UNKNOWN", "INVALID_EXTERNAL_IMPORT_ASSUMPTION"
    )
    assert result.external_import_policy == "STOP_AT_UNMODELED"


def test_external_policy_t09_fingerprint_retained():
    roots, bindings, hashes, snapshots = _external_case(
        "import os\nvalue=1\nimport pkg.ns.b\n"
    )
    snapshots["pkg.ns.a"] = _snapshot("import os\nvalue=2\nimport pkg.ns.b\n")
    result = evaluate_source_bound_conditional_namespace_import_order(
        roots, bindings, hashes, snapshots, "pkg.ns.a",
        standard_finder_assumed=True,
        assume_passive_external_imports=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
    assert result.conditional_assessment is None


def test_external_policy_t10_deterministic_and_unmutated():
    args = _external_case("import os\nvalue=1\nimport pkg.ns.b\n")
    before = dict(args[3])
    first = evaluate_source_bound_conditional_namespace_import_order(
        *args, "pkg.ns.a", standard_finder_assumed=True,
        assume_passive_external_imports=True,
    )
    second = evaluate_source_bound_conditional_namespace_import_order(
        *args, "pkg.ns.a", standard_finder_assumed=True,
        assume_passive_external_imports=True,
    )
    assert first == second
    assert first.conditional_assessment.model_assessment.events == (
        second.conditional_assessment.model_assessment.events
    )
    assert first.conditional_assessment.model_assessment.assumed_external_imports == (
        second.conditional_assessment.model_assessment.assumed_external_imports
    )
    assert json.dumps(asdict(first), sort_keys=True) == json.dumps(
        asdict(second), sort_keys=True
    )
    assert args[3] == before


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
