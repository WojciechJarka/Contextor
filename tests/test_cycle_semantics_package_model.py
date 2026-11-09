import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)
from contextor.core.cycle_semantics.model_environment import (
    STANDARD_BUILTINS_PRECONDITION,
)


def _model(source, entry):
    return evaluate_package_import_order(
        {
            key: ast.parse(code)
            for key, code in source.items()
        },
        entry,
    )


def test_builtin_environment_precondition_is_metadata_not_dataclass_field():
    sources = {
        "pkg.__init__": ast.parse(
            "class E(ValueError):\n"
            "    pass\n"
            "from .child import token\n"
        ),
        "pkg.child": ast.parse("from . import E\ntoken = 7\n"),
    }
    options = {
        "annotation_semantics": "DEFERRED",
        "_compile_on_first_import": True,
    }
    ordinary = evaluate_package_import_order(sources, "pkg", **options)
    assert ordinary.outcome == "MODEL_PASS"
    assert ordinary.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert (
        ordinary.builtin_environment_precondition
        == STANDARD_BUILTINS_PRECONDITION
    )
    assert "builtin_environment_precondition" not in asdict(ordinary)

    shadowed = dict(sources)
    shadowed["pkg.__init__"] = ast.parse(
        "ValueError = 1\n"
        "class E(ValueError):\n"
        "    pass\n"
        "from .child import token\n"
    )
    assert (
        evaluate_package_import_order(shadowed, "pkg", **options).outcome
        == "UNKNOWN"
    )

    conditional_sources = {
        "pkg.__init__": ast.parse(
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class D:\n"
            "    @property\n"
            "    def value(self):\n"
            "        return 1\n"
            "from .child import token\n"
        ),
        "pkg.child": ast.parse("from . import D\ntoken = 7\n"),
    }
    conditional = evaluate_package_import_order(
        conditional_sources, "pkg", **options,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )
    assert conditional.outcome == "MODEL_PASS"
    assert conditional.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    assert (
        conditional.builtin_environment_precondition
        == STANDARD_BUILTINS_PRECONDITION
    )
    assert len(conditional.assumed_external_imports) == 1
    assert len(conditional.assumed_dataclass_decorations) == 1
    assert "builtin_environment_precondition" not in asdict(conditional)


def test_frozen_dataclass_default_model_unknown():
    result = _model(
        {"pkg.__init__": (
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
        )},
        "pkg",
    )
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()


def test_frozen_dataclass_private_policy_requires_external():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(
            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
        )},
        "pkg",
        _compile_on_first_import=True,
        _assume_frozen_dataclass_decoration=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()


def test_frozen_dataclass_direct_conditional_record():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
        )},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )
    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    assert len(result.assumed_dataclass_decorations) == 1
    assert result.assumed_dataclass_decorations[0].class_name == "Graph"


def test_frozen_dataclass_rebound_name_does_not_bind_class():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(
            "from dataclasses import dataclass\n"
            "dataclass = 1\n"
            "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
        )},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "Graph"
        for event in result.events
    )


def _r8_frozen_dataclass_result(
    class_source,
    *,
    assume=True,
    annotation_semantics="DEFERRED",
):
    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(
                "from dataclasses import dataclass\n"
                + class_source
                + "\nfrom .child import token\n"
            ),
            "pkg.child": ast.parse("token = 7\n"),
        },
        "pkg",
        annotation_semantics=annotation_semantics,
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=assume,
    )


def _r8_assert_rejected(result, class_name="ImportRef"):
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert not any(
        event.operation in {
            "ASSUMED_FROZEN_DATACLASS_DECORATION",
            "DEFINE_PASSIVE_CLASS",
        }
        and event.symbol == class_name
        for event in result.events
    )


def test_r8_importref_shape_crosses_class_definition():
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        '    """Raw AST import representation."""\n'
        "    module: str | None\n"
        "    level: int\n"
        "    names: list[str]\n"
        "    is_from_import: bool\n"
        "    is_local: bool = False\n"
        "    type_only: bool = False\n"
        "    is_lazy: bool = False\n"
    )

    result = _r8_frozen_dataclass_result(source)

    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )

    assert len(result.assumed_dataclass_decorations) == 1

    decoration = result.assumed_dataclass_decorations[0]
    assert decoration.class_name == "ImportRef"
    assert decoration.decorator == (
        "dataclasses.dataclass(frozen=True)"
    )
    assert (decoration.line, decoration.column) == (2, 1)

    events = list(result.events)

    decorated_at = next(
        index for index, event in enumerate(events)
        if event.operation
        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
        and event.symbol == "ImportRef"
    )

    defined_at = next(
        index for index, event in enumerate(events)
        if event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "ImportRef"
    )

    child_import_at = next(
        index for index, event in enumerate(events)
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    )

    assert decorated_at < defined_at < child_import_at
    assert result.reached_unmodeled_import is None


@pytest.mark.parametrize(
    "annotation",
    [
        "str | None",
        "None | str",
        "int | None",
        "None | int",
        "list[str] | None",
        "None | list[str]",
    ],
)
def test_r8_restricted_optional_annotation(annotation):
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        f"    value: {annotation}\n"
    )

    result = _r8_frozen_dataclass_result(source)

    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1


@pytest.mark.parametrize(
    "literal",
    [
        "False",
        "True",
        "None",
        "0",
        "1.5",
        "2j",
        "'text'",
        "b'bytes'",
    ],
)
def test_r8_constant_field_defaults(literal):
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        "    required: str\n"
        f"    optional: str = {literal}\n"
    )

    result = _r8_frozen_dataclass_result(source)

    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1


@pytest.mark.parametrize(
    "field_source",
    [
        "value: bool = factory()",
        "value: list[str] = []",
        "value: bool = SOME_NAME",
        "value: bool = 1 + 2",
        "value: bool = (1, 2)",
        "value: bool = {}",
        "value: str | int",
        "value: str | UnknownName",
        "value: str | None | None",
        "value: str + None",
        "value: str | None = factory()",
        "first: bool = False\n    later: int",
    ],
)
def test_r8_rejects_unsupported_dataclass_fields(
    field_source,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        f"    {field_source}\n"
    )

    result = _r8_frozen_dataclass_result(source)

    _r8_assert_rejected(result)


def test_r8_optional_class_requires_explicit_assumption():
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        "    module: str | None\n"
        "    is_local: bool = False\n"
    )

    result = _r8_frozen_dataclass_result(
        source,
        assume=False,
    )

    _r8_assert_rejected(result)


@pytest.mark.parametrize(
    "annotation_semantics",
    [None, "STRINGIFIED"],
)
def test_r8_optional_class_requires_deferred_annotations(
    annotation_semantics,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class ImportRef:\n"
        "    module: str | None\n"
        "    is_local: bool = False\n"
    )

    result = _r8_frozen_dataclass_result(
        source,
        annotation_semantics=annotation_semantics,
    )

    _r8_assert_rejected(result)


def _r9_builtin_base_result(source):
    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(
                source + "\nfrom .child import token\n"
            ),
            "pkg.child": ast.parse("token = 7\n"),
            "pkg.side": ast.parse("ValueError = 123\n"),
        },
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )


def test_r9_sourceerror_shape_crosses_builtin_base():
    source = (
        "class SourceError(ValueError):\n"
        '    """Structured source error."""\n'
        "    def __init__(self, message: str, *, "
        'error_status: str = "ERROR", '
        "line_number: int | None = None, "
        "column_number: int | None = None, "
        "detail_message: str | None = None) -> None:\n"
        "        super().__init__(message)\n"
        "        self.error_status = error_status\n"
    )

    result = _r9_builtin_base_result(source)

    assert result.outcome == "MODEL_PASS"
    assert result.assumed_dataclass_decorations == ()

    events = list(result.events)

    defined = next(
        i for i, event in enumerate(events)
        if event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "SourceError"
    )

    imported = next(
        i for i, event in enumerate(events)
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    )

    assert defined < imported
    assert result.reached_unmodeled_import is None


def test_r9_simple_builtin_exception_subclass():
    result = _r9_builtin_base_result(
        "class CustomError(ValueError):\n"
        "    pass\n"
    )

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )


@pytest.mark.parametrize(
    "declaration",
    [
        "class CustomError(Exception):",
        "class CustomError(BaseException):",
        "class CustomError(UnknownBase):",
        "class CustomError(pkg.ValueError):",
        "class CustomError(ValueError, Exception):",
        "class CustomError(ValueError, metaclass=Meta):",
        "@decorator\nclass CustomError(ValueError):",
    ],
)
def test_r9_rejects_unmodeled_bases(declaration):
    result = _r9_builtin_base_result(
        declaration + "\n    pass\n"
    )

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )


def test_r9_rejects_shadowed_builtin_before_class_body():
    result = _r9_builtin_base_result(
        "ValueError = 123\n"
        "class CustomError(ValueError):\n"
        "    import pkg.side\n"
    )

    assert result.outcome == "UNKNOWN"
    assert result.symbol == "ValueError"

    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )

    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.side"
        for event in result.events
    )


def test_r9_rejects_imported_base_shadowing():
    result = _r9_builtin_base_result(
        "from .side import ValueError\n"
        "class CustomError(ValueError):\n"
        "    pass\n"
    )

    assert result.outcome == "UNKNOWN"
    assert result.symbol == "ValueError"

    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )


def test_r9_rejects_executable_class_body():
    result = _r9_builtin_base_result(
        "class CustomError(ValueError):\n"
        "    execute_unknown_code()\n"
    )

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )


def test_r9_existing_plain_class_unchanged():
    result = _r9_builtin_base_result(
        "class PlainClass:\n"
        "    pass\n"
    )

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "PlainClass"
        for event in result.events
    )


def _r10_qualified_ast_result(
    class_source,
    *,
    prelude="import ast\n",
    after_class="",
    assume=True,
    annotation_semantics="DEFERRED",
):
    source = (
        prelude
        + "from dataclasses import dataclass\n"
        + class_source
        + "\n"
        + after_class
        + "from .child import token\n"
    )

    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse("token = 7\n"),
        },
        "pkg",
        annotation_semantics=annotation_semantics,
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=assume,
    )


def _r10_assert_rejected(result):
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()

    assert not any(
        event.operation in {
            "ASSUMED_FROZEN_DATACLASS_DECORATION",
            "DEFINE_PASSIVE_CLASS",
        }
        and event.symbol == "ParsedSourceInput"
        for event in result.events
    )


def test_r10_parsed_source_input_crosses_class():
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
        "    source_fingerprint: str\n"
    )

    result = _r10_qualified_ast_result(source)

    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )

    assert len(result.assumed_dataclass_decorations) == 1

    decoration = result.assumed_dataclass_decorations[0]

    assert decoration.class_name == "ParsedSourceInput"
    assert decoration.decorator == (
        "dataclasses.dataclass(frozen=True)"
    )

    events = list(result.events)

    decorated = next(
        index for index, event in enumerate(events)
        if event.operation
        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
        and event.symbol == "ParsedSourceInput"
    )

    bound = next(
        index for index, event in enumerate(events)
        if event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "ParsedSourceInput"
    )

    imported = next(
        index for index, event in enumerate(events)
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    )

    assert decorated < bound < imported
    assert result.reached_unmodeled_import is None


def test_r10_both_source_dataclasses_cross():
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
        "    source_fingerprint: str\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class SourceSnapshot:\n"
        "    raw: bytes\n"
        "    source_fingerprint: str\n"
    )

    result = _r10_qualified_ast_result(source)

    assert result.outcome == "MODEL_PASS"

    assert tuple(
        record.class_name
        for record in result.assumed_dataclass_decorations
    ) == (
        "ParsedSourceInput",
        "SourceSnapshot",
    )


@pytest.mark.parametrize(
    "annotation",
    [
        "ast.AST",
        "ast.AST | None",
        "None | ast.AST",
        "list[ast.AST]",
    ],
)
def test_r10_restricted_qualified_annotations(annotation):
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        f"    tree: {annotation}\n"
    )

    result = _r10_qualified_ast_result(source)

    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1


@pytest.mark.parametrize(
    "annotation",
    [
        "ast.Unknown",
        "ast.AST.child",
        "ast.AST()",
        "os.AST",
        "unknown.AST",
        "ast.AST | str",
        "ast.AST | None | None",
    ],
)
def test_r10_rejects_unsupported_qualified_annotations(
    annotation,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        f"    tree: {annotation}\n"
    )

    result = _r10_qualified_ast_result(source)

    _r10_assert_rejected(result)


@pytest.mark.parametrize(
    "prelude",
    [
        "",
        "import os as ast\n",
        "import ast\nast = 42\n",
    ],
)
def test_r10_rejects_unproven_ast_binding(prelude):
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
    )

    result = _r10_qualified_ast_result(
        source,
        prelude=prelude,
    )

    _r10_assert_rejected(result)


def test_r10_later_ast_rebinding_does_not_retroactively_fail():
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
    )

    result = _r10_qualified_ast_result(
        source,
        after_class="ast = 42\n",
    )

    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1

    events = list(result.events)

    bound = next(
        index for index, event in enumerate(events)
        if event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "ParsedSourceInput"
    )

    rebound = next(
        index for index, event in enumerate(events)
        if event.operation == "BIND"
        and event.symbol == "ast"
    )

    assert bound < rebound


def test_r10_requires_explicit_dataclass_assumption():
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
    )

    result = _r10_qualified_ast_result(
        source,
        assume=False,
    )

    _r10_assert_rejected(result)


@pytest.mark.parametrize(
    "annotation_semantics",
    [None, "STRINGIFIED"],
)
def test_r10_requires_deferred_annotation_semantics(
    annotation_semantics,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class ParsedSourceInput:\n"
        "    tree: ast.AST\n"
    )

    result = _r10_qualified_ast_result(
        source,
        annotation_semantics=annotation_semantics,
    )

    _r10_assert_rejected(result)


def _r11_module_result(
    module_source,
    *,
    import_type="from .imports import ImportRef\n",
    import_dataclass="from dataclasses import dataclass, field\n",
    prelude="",
    annotation_semantics="DEFERRED",
    assume=True,
):
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.imports": (
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class ImportRef:\n"
            "    module: str | None\n"
        ),
        "pkg.module": (
            import_dataclass
            + import_type
            + prelude
            + module_source
            + "\nfrom .child import token\n"
        ),
        "pkg.child": "token = 7\n",
    }

    return evaluate_package_import_order(
        {
            key: ast.parse(value)
            for key, value in sources.items()
        },
        "pkg.module",
        annotation_semantics=annotation_semantics,
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=assume,
    )


def _r11_class_source():
    return (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        "    module_id: str\n"
        "    path: str\n"
        "    absolute_path: str\n"
        "    imports: list[ImportRef] = field(hash=False)\n"
        "    @property\n"
        "    def ast_tree(self):\n"
        "        return None\n"
    )


def _r11_assert_module_rejected(result):
    assert result.outcome == "UNKNOWN"
    assert not any(
        item.class_name == "Module"
        for item in result.assumed_dataclass_decorations
    )
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "Module"
        for event in result.events
    )


def test_r11_real_module_shape_crosses_class():
    result = _r11_module_result(_r11_class_source())

    assert result.outcome == "MODEL_PASS"

    assert tuple(
        item.class_name
        for item in result.assumed_dataclass_decorations
    ) == (
        "ImportRef",
        "Module",
    )

    events = list(result.events)

    imported_type = next(
        index for index, event in enumerate(events)
        if event.operation == "FROM"
        and event.target == "pkg.imports"
        and event.symbol == "ImportRef"
    )

    bound_field = next(
        index for index, event in enumerate(events)
        if event.operation == "CLASS_LOCAL_BIND"
        and event.symbol == "imports"
    )

    decorated = next(
        index for index, event in enumerate(events)
        if event.operation
        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
        and event.symbol == "Module"
    )

    bound_class = next(
        index for index, event in enumerate(events)
        if event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "Module"
    )

    imported_child = next(
        index for index, event in enumerate(events)
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    )

    assert (
        imported_type
        < bound_field
        < decorated
        < bound_class
        < imported_child
    )

    assert result.reached_unmodeled_import is None


def test_r11_named_passive_class_annotation_not_hardcoded():
    source = (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        "    reference: OtherType\n"
    )

    sources = {
        "pkg.__init__": "pass\n",
        "pkg.imports": (
            "class OtherType:\n"
            "    pass\n"
        ),
        "pkg.module": (
            "from dataclasses import dataclass\n"
            "from .imports import OtherType\n"
            + source
        ),
    }

    result = evaluate_package_import_order(
        {
            key: ast.parse(value)
            for key, value in sources.items()
        },
        "pkg.module",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )

    assert result.outcome == "MODEL_PASS"
    assert any(
        item.class_name == "Module"
        for item in result.assumed_dataclass_decorations
    )


@pytest.mark.parametrize(
    "import_type,prelude",
    [
        ("", ""),
        ("from pathlib import ImportRef\n", ""),
        ("from .imports import ImportRef\n", "ImportRef = 7\n"),
    ],
)
def test_r11_requires_proven_passive_type(
    import_type,
    prelude,
):
    result = _r11_module_result(
        _r11_class_source(),
        import_type=import_type,
        prelude=prelude,
    )

    _r11_assert_module_rejected(result)


@pytest.mark.parametrize(
    "import_dataclass,prelude",
    [
        ("from dataclasses import dataclass\n", ""),
        (
            "from dataclasses import dataclass\n"
            "from pathlib import Path as field\n",
            "",
        ),
        (
            "from dataclasses import dataclass, field\n",
            "field = 42\n",
        ),
    ],
)
def test_r11_requires_exact_field_factory_binding(
    import_dataclass,
    prelude,
):
    result = _r11_module_result(
        _r11_class_source(),
        import_dataclass=import_dataclass,
        prelude=prelude,
    )

    _r11_assert_module_rejected(result)

    assert not any(
        event.operation == "CLASS_LOCAL_BIND"
        and event.symbol == "imports"
        for event in result.events
    )


@pytest.mark.parametrize(
    "default_expression",
    [
        "field()",
        "field(default=1)",
        "field(hash=True)",
        "field(hash=0)",
        "field(hash=False, compare=True)",
        "other(hash=False)",
        "field(hash=False) or None",
    ],
)
def test_r11_rejects_other_default_calls(
    default_expression,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        f"    imports: list[ImportRef] = {default_expression}\n"
    )

    result = _r11_module_result(source)

    _r11_assert_module_rejected(result)


@pytest.mark.parametrize(
    "decorator",
    [
        "@property()",
        "@unknown",
        "@property\n    @unknown",
    ],
)
def test_r11_rejects_other_method_decorators(decorator):
    source = (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        "    imports: list[ImportRef] = field(hash=False)\n"
        f"    {decorator}\n"
        "    def ast_tree(self):\n"
        "        return None\n"
    )

    result = _r11_module_result(source)

    _r11_assert_module_rejected(result)


def test_r11_rejects_shadowed_builtin_property():
    result = _r11_module_result(
        _r11_class_source(),
        prelude="property = 12\n",
    )

    _r11_assert_module_rejected(result)


@pytest.mark.parametrize(
    "shadow_source",
    [
        "    property: str = 'shadow'\n",
        "    field: str = 'shadow'\n",
    ],
)
def test_r11_rejects_class_local_callable_shadow(
    shadow_source,
):
    source = _r11_class_source().replace(
        "    imports: list[ImportRef] = field(hash=False)\n",
        shadow_source
        + "    imports: list[ImportRef] = field(hash=False)\n",
    )

    result = _r11_module_result(source)

    _r11_assert_module_rejected(result)


def test_r11_rejects_unmodeled_async_property():
    source = (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        "    imports: list[ImportRef] = field(hash=False)\n"
        "    @property\n"
        "    async def ast_tree(self):\n"
        "        return None\n"
    )

    result = _r11_module_result(source)

    _r11_assert_module_rejected(result)


def test_r11_plain_class_property_remains_unmodeled():
    sources = {
        "pkg.__init__": (
            "class Plain:\n"
            "    @property\n"
            "    def value(self):\n"
            "        return 1\n"
        )
    }

    result = evaluate_package_import_order(
        {
            key: ast.parse(value)
            for key, value in sources.items()
        },
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )

    assert result.outcome == "UNKNOWN"


def test_r11_requires_explicit_conditional_assumption():
    result = _r11_module_result(
        _r11_class_source(),
        assume=False,
    )

    _r11_assert_module_rejected(result)


@pytest.mark.parametrize(
    "annotation_semantics",
    [None, "STRINGIFIED"],
)
def test_r11_requires_deferred_annotation_semantics(
    annotation_semantics,
):
    result = _r11_module_result(
        _r11_class_source(),
        annotation_semantics=annotation_semantics,
    )

    _r11_assert_module_rejected(result)


def test_r11_f1_plain_class_field_call_remains_unknown():
    result = _r11_module_result(
        "class Plain:\n"
        "    imports: list[ImportRef] = field(hash=False)\n"
    )

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "Plain"
        for event in result.events
    )


@pytest.mark.parametrize(
    "field_target",
    [
        "holder.imports",
        "holder['imports']",
    ],
)
def test_r11_f1_field_call_requires_simple_name_target(
    field_target,
):
    source = (
        "@dataclass(frozen=True)\n"
        "class Module:\n"
        f"    {field_target}: list[ImportRef] = field(hash=False)\n"
    )

    result = _r11_module_result(source)

    _r11_assert_module_rejected(result)


def test_external_assumption_normal_model_still_unknown():
    result = _model({"pkg.__init__": "import os\n"}, "pkg")
    assert result.outcome == "UNKNOWN"
    assert result.target_module == "os"
    assert result.assumed_external_imports == ()
    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert not any(
        event.operation == "ASSUMED_EXTERNAL_IMPORT"
        for event in result.events
    )


def test_external_assumption_refused_without_lazy_compilation():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse("import os\n")}, "pkg",
        _assume_passive_external_imports=True,
    )
    assert result.outcome == "UNKNOWN"
    assert result.assumed_external_imports == ()


def test_external_assumption_direct_conditional_scope():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse("import os\nvalue=1\n")},
        "pkg",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
    )
    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
        "ASSUMPTION_NOT_RUNTIME_PROOF"
    )
    assert tuple(x.target for x in result.assumed_external_imports) == ("os",)
    assert result.reached_unmodeled_import is None


def test_external_assumption_normal_pass_has_no_record():
    result = _model({"pkg.__init__": "value=1\n"}, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert result.assumed_external_imports == ()


def test_external_assumption_does_not_skip_indexed_import():
    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse("from .child import value\n"),
            "pkg.child": ast.parse("value=7\n"),
        },
        "pkg",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
    )
    assert result.outcome == "MODEL_PASS"
    assert result.assumed_external_imports == ()
    assert any(event.target == "pkg.child" for event in result.events)


def test_external_assumption_called_local_import_keeps_location():
    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(
                "def activate():\n    import os\nactivate()\n"
            )
        },
        "pkg",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
    )
    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_external_imports) == 1
    row = result.assumed_external_imports[0]
    assert (row.importer, row.operation, row.target) == (
        "pkg", "IMPORT", "os"
    )
    assert (row.line, row.column) == (2, 4)
    assert "CALL_FUNCTION" in (event.operation for event in result.events)


def test_external_assumption_uncalled_function_has_no_record():
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse("def activate():\n    import os\nvalue=1\n")},
        "pkg",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
    )
    assert result.outcome == "MODEL_PASS"
    assert result.assumed_external_imports == ()


def test_reached_unmodeled_import_direct_import():
    result = _model({"pkg.__init__": "import os\nvalue=1\n"}, "pkg")

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "os"
    blocker = result.reached_unmodeled_import
    assert blocker is not None
    assert blocker.importer == "pkg"
    assert blocker.operation == "IMPORT"
    assert blocker.target == "os"
    assert blocker.symbol is None
    assert blocker.line == 1
    assert blocker.column == 0

    encoded = json.dumps(asdict(result), sort_keys=True)
    assert json.loads(encoded)["reached_unmodeled_import"] == {
        "column": 0,
        "importer": "pkg",
        "line": 1,
        "operation": "IMPORT",
        "symbol": None,
        "target": "os",
    }
    assert encoded == json.dumps(asdict(result), sort_keys=True)


def test_reached_unmodeled_import_from_import():
    result = _model(
        {"pkg.__init__": "from dataclasses import dataclass\n"},
        "pkg",
    )

    assert result.outcome == "UNKNOWN"
    blocker = result.reached_unmodeled_import
    assert blocker is not None
    assert blocker.operation == "FROM"
    assert blocker.target == "dataclasses"
    assert blocker.symbol == "dataclass"
    assert blocker.line == 1
    assert blocker.column == 0


def test_reached_unmodeled_import_called_function_body():
    result = _model(
        {
            "pkg.__init__": (
                "def activate():\n"
                "    import os\n"
                "activate()\n"
            ),
        },
        "pkg",
    )

    assert result.outcome == "UNKNOWN"
    blocker = result.reached_unmodeled_import
    assert blocker is not None
    assert blocker.importer == "pkg"
    assert blocker.operation == "IMPORT"
    assert blocker.target == "os"
    assert blocker.line == 2
    assert blocker.column == 4
    assert "CALL_FUNCTION" in (event.operation for event in result.events)


def test_uncalled_function_import_has_no_reached_blocker():
    result = _model(
        {
            "pkg.__init__": (
                "def activate():\n"
                "    import os\n"
                "value=1\n"
            ),
        },
        "pkg",
    )

    assert result.outcome == "MODEL_PASS"
    assert result.reached_unmodeled_import is None


def test_earlier_unsupported_statement_has_no_reached_blocker():
    result = _model(
        {
            "pkg.__init__": (
                "value=1\n"
                "unsupported_call()\n"
                "import os\n"
            ),
        },
        "pkg",
    )

    assert result.outcome == "UNKNOWN"
    assert result.reached_unmodeled_import is None


def test_indexed_import_has_no_reached_blocker():
    result = _model(
        {
            "pkg.__init__": "from .child import value\n",
            "pkg.child": "value=7\n",
        },
        "pkg",
    )

    assert result.outcome == "MODEL_PASS"
    assert result.reached_unmodeled_import is None


def _actual(tmp_path, source, entry):
    for module_id, code in source.items():
        parts = module_id.split(".")

        if parts[-1] == "__init__":
            path = tmp_path.joinpath(
                *parts[:-1],
                "__init__.py",
            )
        else:
            path = tmp_path.joinpath(
                *parts[:-1],
                parts[-1] + ".py",
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            code + "\n",
            encoding="utf-8",
        )

    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            (
                "import importlib,sys;"
                "sys.path.insert(0,sys.argv[1]);"
                "importlib.import_module(sys.argv[2])"
            ),
            str(tmp_path),
            entry,
        ],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )

    return process.returncode == 0


def test_parent_initializer_precedes_submodule(tmp_path):
    source = {
        "pkg.__init__": "value=7",
        "pkg.sub": "from pkg import value",
    }

    result = _model(source, "pkg.sub")

    assert result.outcome == "MODEL_PASS"

    assert [
        (event.module, event.operation)
        for event in result.events
        if event.operation == "READY"
    ] == [
        ("pkg", "READY"),
        ("pkg.sub", "READY"),
    ]

    assert _actual(tmp_path, source, "pkg.sub")


def test_warn_5g_module_docstrings_preserve_safe_order(tmp_path):
    source = {
        "pkg.__init__": (
            '"""Package documentation."""\n'
            "value=2\n"
            "import pkg.sub"
        ),
        "pkg.sub": (
            '"""Submodule documentation."""\n'
            "import pkg\n"
            "x=pkg.value"
        ),
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_warn_5g_docstrings_do_not_hide_early_binding_hazard(
    tmp_path,
):
    source = {
        "pkg.__init__": (
            '"""Package documentation."""\n'
            "import pkg.sub\n"
            "value=2"
        ),
        "pkg.sub": (
            '"""Submodule documentation."""\n'
            "import pkg\n"
            "x=pkg.value"
        ),
    }

    result = _model(source, "pkg")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_warn_5g_nonleading_string_expression_remains_unknown():
    source = {
        "pkg.__init__": (
            "pass\n"
            "'not a module docstring'"
        ),
    }

    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_warn_5g_nested_string_expression_remains_unknown():
    source = {
        "pkg.__init__": (
            "if True:\n"
            "    'not a module docstring'"
        ),
    }

    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_warn_5g_docstring_does_not_hide_unsupported_effect():
    source = {
        "pkg.__init__": (
            '"""Package documentation."""\n'
            'raise RuntimeError("unsupported")'
        ),
    }

    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_package_early_attribute_failure(tmp_path):
    source = {
        "pkg.__init__": "import pkg.sub\nvalue=2",
        "pkg.sub": "import pkg\nx=pkg.value",
    }

    result = _model(source, "pkg")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_same_imports_reordered_pass(tmp_path):
    source = {
        "pkg.__init__": "value=2\nimport pkg.sub",
        "pkg.sub": "import pkg\nx=pkg.value",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_child_attribute_bound_after_ready(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=7",
        "entry": "import pkg.sub\nx=pkg.sub",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"

    operations = [
        (event.module, event.operation, event.target)
        for event in result.events
    ]

    assert operations.index(
        ("pkg.sub", "READY", None)
    ) < operations.index(
        ("pkg", "BIND_CHILD", "pkg.sub")
    )

    assert _actual(tmp_path, source, "entry")


def test_package_relative_reexport(tmp_path):
    source = {
        "pkg.__init__": "from .sub import value",
        "pkg.sub": "value=7",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_package_explicit_reexport(tmp_path):
    source = {
        "pkg.__init__": "from pkg.sub import value",
        "pkg.sub": "value=7",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_package_early_from_import_hazard(tmp_path):
    source = {
        "pkg.__init__": "from pkg.sub import value",
        "pkg.sub": "from pkg import value",
    }

    assert (
        _model(source, "pkg").outcome
        == "EARLY_BINDING_HAZARD"
    )

    assert not _actual(tmp_path, source, "pkg")


def test_dotted_alias_to_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=7",
        "entry": "import pkg.sub as s\nx=s.value",
    }

    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_from_package_child_loads_indexed_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "entry": "from pkg import child\nx=child.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_warn_5h_namespace_rejected_before_ast_compilation(
    monkeypatch,
):
    from contextor.core.cycle_semantics import package_model

    calls = []

    def forbidden_compile(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError(
            "unsupported layout must reject before compilation"
        )

    monkeypatch.setattr(
        package_model,
        "compile",
        forbidden_compile,
        raising=False,
    )

    result = _model(
        {"pkg.sub": "value=7"},
        "pkg.sub",
    )

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "pkg"
    assert result.events == ()
    assert calls == []


def test_warn_5h_regular_layout_still_checks_compile_time_errors():
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "def f():\n    break",
    }

    result = _model(source, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "pkg.a"
    assert result.events == ()


def test_warn_5h_regular_layout_still_proves_safe_import(tmp_path):
    source = {
        "pkg.__init__": "value=1\nimport pkg.a",
        "pkg.a": "import pkg\nx=pkg.value",
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_warn_5i_preparation_reused_between_entries(monkeypatch):
    from contextor.core.cycle_semantics import package_model

    source = {
        "pkg.__init__": "value=1\nimport pkg.a",
        "pkg.a": "import pkg\nx=pkg.value",
    }
    trees = {
        name: ast.parse(code)
        for name, code in source.items()
    }

    calls = {
        "layout": 0,
        "code": 0,
        "model": 0,
    }

    original_layout = package_model.build_package_layout
    original_compile = compile
    original_model = package_model._compile

    def counted_layout(*args, **kwargs):
        calls["layout"] += 1
        return original_layout(*args, **kwargs)

    def counted_compile(*args, **kwargs):
        calls["code"] += 1
        return original_compile(*args, **kwargs)

    def counted_model(*args, **kwargs):
        calls["model"] += 1
        return original_model(*args, **kwargs)

    monkeypatch.setattr(
        package_model, "build_package_layout", counted_layout
    )
    monkeypatch.setattr(
        package_model, "compile", counted_compile, raising=False
    )
    monkeypatch.setattr(
        package_model, "_compile", counted_model
    )

    session = package_model._PackageSourceSession()
    first = package_model.evaluate_package_import_order(
        trees, "pkg", _session=session
    )
    second = package_model.evaluate_package_import_order(
        trees, "pkg.a", _session=session
    )

    assert first.outcome == "MODEL_PASS"
    assert second.outcome == "MODEL_PASS"
    assert calls == {
        "layout": 1,
        "code": 2,
        "model": 2,
    }


def test_warn_5i_function_expansion_does_not_mutate_cache():
    from contextor.core.cycle_semantics import package_model

    trees = {
        "pkg.__init__": ast.parse(
            "def load():\n"
            "    import pkg.child\n"
            "value=7\n"
            "load()"
        ),
        "pkg.child": ast.parse(
            "import pkg\n"
            "x=pkg.value"
        ),
    }

    before = {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in trees.items()
    }

    session = package_model._PackageSourceSession()
    first = package_model.evaluate_package_import_order(
        trees, "pkg", _session=session
    )
    cached_second = package_model.evaluate_package_import_order(
        trees, "pkg.child", _session=session
    )
    fresh_second = package_model.evaluate_package_import_order(
        trees, "pkg.child"
    )

    assert first.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CALL_FUNCTION"
        for event in first.events
    )
    assert cached_second == fresh_second
    assert {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in trees.items()
    } == before

    assert all(
        type(program) is tuple
        for program in session.compiled_steps.values()
    )


def test_warn_5i_session_rejects_different_ast_identity():
    from contextor.core.cycle_semantics import package_model

    source = {
        "pkg.__init__": "value=1",
        "pkg.child": "import pkg",
    }
    first_trees = {
        name: ast.parse(code)
        for name, code in source.items()
    }
    second_trees = {
        name: ast.parse(code)
        for name, code in source.items()
    }

    session = package_model._PackageSourceSession()

    first = package_model.evaluate_package_import_order(
        first_trees, "pkg", _session=session
    )
    reused = package_model.evaluate_package_import_order(
        second_trees, "pkg", _session=session
    )

    assert first.outcome == "MODEL_PASS"
    assert reused.outcome == "UNKNOWN"
    assert reused.events == ()


def test_namespace_ambiguous_external_unknown():
    assert _model(
        {"pkg.sub": "value=7"},
        "pkg.sub",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg": "pass",
            "pkg.__init__": "pass",
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {"pkg.__init__": "import os"},
        "pkg",
    ).outcome == "UNKNOWN"


def test_unsupported_hooks_mutations_unknown():
    assert _model(
        {"pkg.__init__": "__path__=[]"},
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__":
                "def __getattr__(name):\n    pass"
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__": "sub=1\nimport pkg.sub",
            "pkg.sub": "pass",
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__": "pass",
            "pkg.sub": "pass",
            "entry": "from pkg import *",
        },
        "entry",
    ).outcome == "UNKNOWN"


def test_determinism_invalid_no_ast_mutation():
    sources = {
        "pkg.__init__": ast.parse("import pkg.sub"),
        "pkg.sub": ast.parse("import pkg"),
    }

    before = {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in sources.items()
    }

    first = evaluate_package_import_order(
        sources,
        "pkg",
    )

    second = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in sources.items()
    } == before

    json.dumps(asdict(first))

    assert (
        evaluate_package_import_order(None, "pkg").outcome
        == "UNKNOWN"
    )

    assert (
        evaluate_package_import_order(
            {"pkg.__init__": None},
            "pkg",
        ).outcome
        == "UNKNOWN"
    )


def test_explicit_alias_equal_root_binds_submodule(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=2",
        "entry": "import pkg.sub as pkg\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "ATTR"
        and event.target == "pkg.sub"
        and event.symbol == "value"
        for event in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_explicit_alias_equal_root_prevents_false_model_pass(tmp_path):
    source = {
        "pkg.__init__": "value=2",
        "pkg.sub": "pass",
        "entry": "import pkg.sub as pkg\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MISSING_ATTRIBUTE"
    assert result.target_module == "pkg.sub"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "entry")


def test_explicit_alias_equal_root_inside_package_initializer(tmp_path):
    source = {
        "pkg.__init__": "import pkg.sub as pkg\nx=pkg.value",
        "pkg.sub": "value=2",
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "ATTR"
        and event.target == "pkg.sub"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_plain_dotted_import_still_binds_root_package(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=2",
        "entry": "import pkg.sub\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MISSING_ATTRIBUTE"
    assert result.target_module == "pkg"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c2_relative_initializer_imports_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "value=7",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        e.operation == "BIND_CHILD"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c2_relative_import_from_submodule(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "pkg.user": "from . import child\nx=child.value",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c2_existing_attribute_precedes_child(tmp_path):
    source = {
        "pkg.__init__": "child=3",
        "pkg.child": "value=7",
        "entry": "from pkg import child",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_b0g4c2_constant_attribute_is_not_module(tmp_path):
    source = {
        "pkg.__init__": "child=3",
        "pkg.child": "value=7",
        "entry": "from pkg import child\nx=child.value",
    }
    assert _model(source, "entry").outcome == "UNKNOWN"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c2_child_already_initialized(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "entry": (
            "import pkg.child\n"
            "from pkg import child\n"
            "x=child.value"
        ),
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert sum(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    ) == 1
    assert _actual(tmp_path, source, "entry")


def test_b0g4c2_regular_attribute_reexport(tmp_path):
    source = {
        "pkg.__init__": "from .util import exposed",
        "pkg.util": "exposed=7",
        "pkg.user": "from pkg import exposed",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c3_reentrant_child_uses_same_thread_fallback(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "from pkg import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.target == "pkg.child"
        and event.module == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c2_missing_member_no_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "entry": "from pkg import missing",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_multiple_fromlist_members_supported(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a, b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c2_shadowing_sequence_stays_unknown():
    source = {
        "pkg.__init__": "child=1\nimport pkg.child",
        "pkg.child": "pass",
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_b0g4c2_operation_budget_unknown():
    source = {
        "pkg.__init__": "pass",
        "entry": "import pkg\n" * 10020,
    }
    assert _model(source, "entry").outcome == "UNKNOWN"


def test_b0g4c3_early_read_from_reentrant_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "from pkg import child\n"
            "x=child.value\n"
            "value=7"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg.child"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c3_bound_attribute_before_reentrant_read(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "value=7\n"
            "from pkg import child\n"
            "x=child.value"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_relative_reentrant_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "from . import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_explicit_from_alias(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "value=7\n"
            "from pkg import child as c\n"
            "x=c.value"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.symbol == "child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_nested_regular_package_fallback(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub.__init__": "from . import child",
        "pkg.sub.child": "from pkg.sub import child",
    }
    result = _model(source, "pkg.sub")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.target == "pkg.sub.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg.sub")


def test_b0g4c4_multi_member_missing_export(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "pass",
        "entry": "from pkg import child, missing",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert result.target_module == "pkg"
    assert result.symbol == "missing"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_preparation_before_local_binding_hazard(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "import entry\nx=entry.a",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "entry"
    assert result.symbol == "a"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_all_prepares_before_from_bindings(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    operations = [
        e.operation
        for e in result.events
        if e.module == "entry"
        and e.operation in {"PREPARE_FROM_MEMBER", "FROM"}
    ]
    assert operations == [
        "PREPARE_FROM_MEMBER",
        "PREPARE_FROM_MEMBER",
        "FROM",
        "FROM",
    ]
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_aliases_after_preparation(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "value=2",
        "entry": "from pkg import a as aa,b as bb\nx=aa.value",
    }
    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_multi_from_plain_module(tmp_path):
    source = {
        "provider": "x=1\ny=2",
        "entry": "from provider import x,y",
    }
    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_relative_multi_in_initializer(tmp_path):
    source = {
        "pkg.__init__": "from . import a,b",
        "pkg.a": "value=1",
        "pkg.b": "from pkg import a\nx=a.value",
    }
    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c4_relative_multi_in_module(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "value=2",
        "pkg.user": "from . import a,b",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c4_nested_relative_multi(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub.__init__": "from . import a,b",
        "pkg.sub.a": "pass",
        "pkg.sub.b": "pass",
    }
    assert _model(source, "pkg.sub").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.sub")


def test_b0g4c4_attribute_precedence_during_preparation(tmp_path):
    source = {
        "pkg.__init__": "a=7",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT" and e.target == "pkg.a"
        for e in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_reentrant_child_chain(tmp_path):
    source = {
        "pkg.__init__": "from . import a,b",
        "pkg.a": "from pkg import b",
        "pkg.b": "from pkg import a",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        e.operation == "FROM_REENTRANT_CHILD"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c4_later_child_loads_before_missing_export(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import missing,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert ("pkg.b", "READY") in [
        (e.module, e.operation)
        for e in result.events
    ]
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_sibling_uses_prepared_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "from pkg import a\nx=a.value",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_namespace_layout_remains_unknown():
    source = {
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    assert _model(source, "entry").outcome == "UNKNOWN"


def test_b0g4c5_deferred_function_import_not_executed(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "value=7"
        ),
        "pkg.child": "import pkg\nx=pkg.missing",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_call_activates_early_binding_hazard(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "load()\n"
            "value=7"
        ),
        "pkg.child": "import pkg\nx=pkg.value",
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_binding_before_call_passes(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "value=7\n"
            "load()"
        ),
        "pkg.child": "import pkg\nx=pkg.value",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_function_local_import_not_exported(tmp_path):
    source = {
        "pkg.__init__": (
            "def activate():\n"
            "    import pkg.child as local_only\n"
            "activate()"
        ),
        "pkg.child": "from pkg import local_only",
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "local_only"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_repeated_calls_import_child_once(tmp_path):
    source = {
        "pkg.__init__": (
            "def activate():\n"
            "    import pkg.child\n"
            "activate()\n"
            "activate()"
        ),
        "pkg.child": "value=7",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert sum(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    ) == 1
    assert sum(
        e.operation == "CALL_FUNCTION"
        for e in result.events
    ) == 2
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_plain_flat_module_function_call(tmp_path):
    source = {
        "a": (
            "def load():\n"
            "    import b\n"
            "load()\n"
            "value=7"
        ),
        "b": "import a\nx=a.value",
    }
    result = _model(source, "a")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert not _actual(tmp_path, source, "a")


def test_b0g4c5_exported_definition_is_available(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    pass"
        ),
        "pkg.user": "from pkg import load",
    }
    result = _model(source, "pkg.user")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c5_foreign_function_call_unknown():
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child"
        ),
        "pkg.child": "pass",
        "pkg.user": (
            "from pkg import load\n"
            "load()"
        ),
    }
    assert _model(source, "pkg.user").outcome == "UNKNOWN"


def test_b0g4c5_call_without_local_definition_unknown():
    source = {
        "pkg.__init__": "missing()",
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_b0g4c5_shadowed_function_call_unknown(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    pass\n"
            "load=3\n"
            "load()"
        ),
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_definition_effects_updated_contract():
    samples = (
        (
            "def f(x=1):\n    import pkg.child",
            "MODEL_PASS",
        ),
        (
            "def f(x):\n    import pkg.child",
            "MODEL_PASS",
        ),
        (
            "@decorator\ndef f():\n    import pkg.child",
            "UNKNOWN",
        ),
        (
            "def f() -> int:\n    import pkg.child",
            "UNKNOWN",
        ),
        (
            "def f():\n    helper()",
            "MODEL_PASS",
        ),
        (
            "async def f():\n    import pkg.child",
            "MODEL_PASS",
        ),
        (
            "def f():\n    return 1",
            "MODEL_PASS",
        ),
    )

    for code, expected in samples:
        result = _model(
            {"pkg.__init__": code, "pkg.child": "pass"},
            "pkg",
        )

        assert result.outcome == expected


def test_b0g4c15_uncalled_function_local_from_supported(tmp_path):
    source = {
        "pkg.__init__": (
            "def f():\n"
            "    from pkg import child"
        ),
        "pkg.child": "pass",
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert any(
        event.operation == "DEFINE_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    )

    assert not any(
        event.operation in {
            "FUNCTION_LOCAL_FROM",
            "FUNCTION_LOCAL_FROM_REENTRANT_CHILD",
        }
        for event in result.events
    )

    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_deterministic_ast_unchanged():
    source = {
        "pkg.__init__": ast.parse(
            "def activate():\n"
            "    import pkg.child\n"
            "activate()"
        ),
        "pkg.child": ast.parse("pass"),
    }

    before = {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in source.items()
    }

    first = evaluate_package_import_order(source, "pkg")
    second = evaluate_package_import_order(source, "pkg")

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in source.items()
    } == before

    json.dumps(asdict(first))


@pytest.mark.parametrize(
    "condition,expected,active",
    [
        ("False", "MODEL_PASS", False),
        ("True", "EARLY_BINDING_HAZARD", True),
    ],
)
def test_p1d3_d1_literal_branch_activation(tmp_path, condition, expected, active):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": f"if {condition}:\n    import pkg.b\nvalue = 1",
        "pkg.b": "from pkg.a import value",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == expected
    assert any(
        event.operation == "START_IMPORT" and event.target == "pkg.b"
        for event in result.events
    ) is active
    assert _actual(tmp_path, source, "pkg.a") is (not active)


def test_p1d3_d1_false_else_and_name_guard(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "if False:\n    pass\nelse:\n    import pkg.b\n"
            "if __name__ == '__main__':\n    import pkg.missing\n"
            "value = 1"
        ),
        "pkg.b": "pass",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a")


@pytest.mark.parametrize(
    "body,expected,operation",
    [
        ("class Loader:\n    import pkg.b\nvalue = 1", "EARLY_BINDING_HAZARD", "CLASS_LOCAL_IMPORT"),
        ("value = 1\nclass Loader:\n    import pkg.b", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
        ("class Loader:\n    from pkg.b import value", "MODEL_PASS", "CLASS_LOCAL_FROM"),
        ("class Loader:\n    import pkg.b as local_child", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
    ],
)
def test_p1d3_d1_class_import_timing(tmp_path, body, expected, operation):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": body,
        "pkg.b": "from pkg.a import value" if "value = 1" in body else "value = 2",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == expected
    if expected == "MODEL_PASS":
        assert any(e.operation == operation for e in result.events)
    else:
        assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a") is (expected == "MODEL_PASS")


def test_p1d3_d1_class_local_binding_does_not_escape(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "class Loader:\n    import pkg.b as local_child",
        "pkg.b": "from pkg.a import local_child",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg.a"
    assert result.symbol == "local_child"
    assert not any(e.operation == "DEFINE_PASSIVE_CLASS" for e in result.events)
    assert not _actual(tmp_path, source, "pkg.a")


def test_p1d3_d1_class_local_reentrant_child_from(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "class Loader:\n    from pkg import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_FROM_REENTRANT_CHILD"
        and event.target == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_p1d3_d1_uncalled_method_import_is_deferred(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "class Loader:\n    def load(self):\n        import pkg.b\nvalue = 1",
        "pkg.b": "from pkg.a import value",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert not any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a")


@pytest.mark.parametrize("condition", ["unknown_condition", "1"])
def test_p1d3_d1_unsupported_condition(condition):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": f"if {condition}:\n    import pkg.b",
        "pkg.b": "pass",
    }
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


@pytest.mark.parametrize("body", [
    "class Loader(Base):\n    import pkg.b",
    "class Loader(metaclass=Meta):\n    import pkg.b",
    "@decorator\nclass Loader:\n    import pkg.b",
    "class Loader:\n    helper()",
    "class Loader:\n    x = helper()",
    "class Loader:\n    class Nested:\n        pass",
    "class Loader:\n    if True:\n        import pkg.b",
    "class Loader:\n    from pkg.b import *",
])
def test_p1d3_d1_unsupported_class_effects(body):
    source = {"pkg.__init__": "pass", "pkg.a": body, "pkg.b": "pass"}
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


def test_p1d3_d1_invalid_unselected_branch_fails_compile():
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "if False:\n    return 1\nelse:\n    pass",
    }
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


def test_p1d3_d1_deterministic_events_and_ast_unchanged():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse("if True:\n    class Loader:\n        import pkg.b"),
        "pkg.b": ast.parse("from pkg.a import Loader"),
    }
    before = {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()}
    first = evaluate_package_import_order(sources, "pkg.a")
    second = evaluate_package_import_order(sources, "pkg.a")
    assert first == second
    assert first.events == second.events
    assert first.outcome == "EARLY_BINDING_HAZARD"
    assert {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()} == before


def test_p10_eager_contract_unchanged_and_lazy_opt_in():
    source = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse(
            "def later():\n"
            "    import pkg.bad\n"
            "value = 1\n"
        ),
        "pkg.bad": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    eager = evaluate_package_import_order(
        source,
        "pkg.a",
        annotation_semantics="DEFERRED",
    )
    lazy = evaluate_package_import_order(
        source,
        "pkg.a",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )

    assert eager.outcome == "UNKNOWN"
    assert eager.target_module == "pkg.bad"
    assert eager.events == ()

    assert lazy.outcome == "MODEL_PASS"
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.bad"
        for event in lazy.events
    )


def test_p10_private_mode_invalid_flag_fails_closed():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse("pass"),
    }

    for invalid in (None, 1, "True"):
        result = evaluate_package_import_order(
            sources,
            "pkg.a",
            _compile_on_first_import=invalid,
        )
        assert result.outcome == "UNKNOWN"


def test_p10_private_mode_rejects_session_combination():
    from contextor.core.cycle_semantics.package_model import (
        _PackageSourceSession,
    )

    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse("pass"),
    }

    result = evaluate_package_import_order(
        sources,
        "pkg.a",
        _session=_PackageSourceSession(),
        _compile_on_first_import=True,
    )

    assert result.outcome == "UNKNOWN"


def test_p11_strict_mode_remains_whole_module_unknown():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse(
            "value = 1\n"
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    strict = evaluate_package_import_order(
        sources,
        "pkg.a",
        annotation_semantics="DEFERRED",
    )

    opt_in = evaluate_package_import_order(
        sources,
        "pkg.a",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )

    assert strict.outcome == "UNKNOWN"
    assert strict.target_module == "pkg.a"
    assert strict.events == ()

    assert opt_in.outcome == "UNKNOWN"
    assert opt_in.target_module == "pkg.a"
    assert any(
        event.operation == "BIND"
        and event.module == "pkg.a"
        and event.symbol == "value"
        for event in opt_in.events
    )
