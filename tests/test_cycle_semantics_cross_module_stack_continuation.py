import ast

from contextor.core.cycle_semantics.execution.calls import (
    _RestrictedFunction,
    _snapshot_named_decorators,
)
from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(sources):
    return evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        "pkg.app",
    )


def _events(model, operation):
    return tuple(
        event
        for event in model.events
        if event.operation == operation
    )


def _calls(model):
    return tuple(
        (event.module, event.symbol)
        for event in _events(model, "CALL_FUNCTION")
    )


def _starts(model):
    return tuple(
        (event.module, event.target)
        for event in _events(model, "START_IMPORT")
        if (
            event.target is not None
            and event.target.startswith("pkg.")
            and event.module != "\x00ENTRY"
        )
    )


def _local_imports(model):
    return tuple(
        (event.module, event.target, event.symbol)
        for event in _events(model, "FUNCTION_LOCAL_IMPORT")
    )


def _assert_unique_module_starts(model):
    targets = tuple(target for _module, target in _starts(model))
    assert len(targets) == len(set(targets))


def _with_f_call(sources):
    model_sources = dict(sources)
    model_sources["pkg.app"] += "f()\n"
    return _model(model_sources)


def test_foreign_bottom_then_local_upper_uses_each_defining_module():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": (
            "def bottom(fn):\n"
            "    import pkg.bottom_effect\n"
            "    return fn\n"
        ),
        "pkg.bottom_effect": "pass\n",
        "pkg.upper_effect": "pass\n",
        "pkg.app": (
            "from pkg.decorators import bottom\n"
            "def upper(fn):\n"
            "    import pkg.upper_effect\n"
            "    return fn\n"
            "@upper\n"
            "@bottom\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    assert _starts(modeled) == (
        ("pkg.app", "pkg.decorators"),
        ("pkg.decorators", "pkg.bottom_effect"),
        ("pkg.app", "pkg.upper_effect"),
    )
    assert _local_imports(modeled) == (
        ("pkg.decorators", "pkg.bottom_effect", "pkg"),
        ("pkg.app", "pkg.upper_effect", "pkg"),
    )
    assert not any(
        event.operation == "BIND" and event.symbol == "f"
        for event in modeled.events
    )
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "MODEL_PASS"
    assert _calls(called) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
        ("pkg.app", "f"),
    )


def test_local_bottom_then_foreign_upper_preserves_effect_order():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": (
            "def upper(fn):\n"
            "    import pkg.upper_effect\n"
            "    return fn\n"
        ),
        "pkg.upper_effect": "pass\n",
        "pkg.bottom_effect": "pass\n",
        "pkg.app": (
            "from pkg.decorators import upper\n"
            "def bottom(fn):\n"
            "    import pkg.bottom_effect\n"
            "    return fn\n"
            "@upper\n"
            "@bottom\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    assert _starts(modeled) == (
        ("pkg.app", "pkg.decorators"),
        ("pkg.app", "pkg.bottom_effect"),
        ("pkg.decorators", "pkg.upper_effect"),
    )
    assert _local_imports(modeled) == (
        ("pkg.app", "pkg.bottom_effect", "pkg"),
        ("pkg.decorators", "pkg.upper_effect", "pkg"),
    )
    bottom_call = next(
        index
        for index, event in enumerate(modeled.events)
        if event.operation == "CALL_FUNCTION" and event.symbol == "bottom"
    )
    bottom_effect = next(
        index
        for index, event in enumerate(modeled.events)
        if event.operation == "FUNCTION_LOCAL_IMPORT"
        and event.target == "pkg.bottom_effect"
    )
    upper_call = next(
        index
        for index, event in enumerate(modeled.events)
        if event.operation == "CALL_FUNCTION" and event.symbol == "upper"
    )
    upper_effect = next(
        index
        for index, event in enumerate(modeled.events)
        if event.operation == "FUNCTION_LOCAL_IMPORT"
        and event.target == "pkg.upper_effect"
    )
    assert bottom_call < bottom_effect < upper_call < upper_effect
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "MODEL_PASS"
    assert _calls(called)[-1] == ("pkg.app", "f")


def test_two_foreign_decorators_execute_in_distinct_modules():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.lower": (
            "def lower(fn):\n"
            "    import pkg.lower_effect\n"
            "    return fn\n"
        ),
        "pkg.upper": (
            "def upper(fn):\n"
            "    import pkg.upper_effect\n"
            "    return fn\n"
        ),
        "pkg.lower_effect": "pass\n",
        "pkg.upper_effect": "pass\n",
        "pkg.app": (
            "from pkg.lower import lower\n"
            "from pkg.upper import upper\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (
        ("pkg.app", "lower"),
        ("pkg.app", "upper"),
    )
    assert _starts(modeled) == (
        ("pkg.app", "pkg.lower"),
        ("pkg.app", "pkg.upper"),
        ("pkg.lower", "pkg.lower_effect"),
        ("pkg.upper", "pkg.upper_effect"),
    )
    assert _local_imports(modeled) == (
        ("pkg.lower", "pkg.lower_effect", "pkg"),
        ("pkg.upper", "pkg.upper_effect", "pkg"),
    )
    assert tuple(
        event.symbol for event in _events(modeled, "FROM")
    ) == ("lower", "upper")
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "MODEL_PASS"
    assert _calls(called)[-1] == ("pkg.app", "f")


def test_foreign_bottom_natural_completion_passes_none_to_upper():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def bottom(fn):\n    pass\n",
        "pkg.app": (
            "from pkg.decorators import bottom\n"
            "def upper(value):\n"
            "    return value\n"
            "@upper\n"
            "@bottom\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "UNKNOWN"
    assert _calls(called) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "f"
        for event in called.events
    )


def test_foreign_bottom_bare_return_passes_none_to_upper():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def bottom(fn):\n    return\n",
        "pkg.app": (
            "from pkg.decorators import bottom\n"
            "def upper(value):\n"
            "    return value\n"
            "@upper\n"
            "@bottom\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "UNKNOWN"
    assert _calls(called) == (
        ("pkg.app", "bottom"),
        ("pkg.app", "upper"),
    )
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "f"
        for event in called.events
    )


def test_snapshot_identity_survives_namespace_rebinding():
    bottom = _RestrictedFunction(
        defining_module="pkg.lower",
        body=(),
        parameters=("fn",),
    )
    upper = _RestrictedFunction(
        defining_module="pkg.upper",
        body=(),
        parameters=("fn",),
    )
    replacement = _RestrictedFunction(
        defining_module="pkg.replacement",
        body=(),
        parameters=("fn",),
    )
    namespace = {
        "top_alias": upper,
        "bottom_alias": bottom,
    }

    snapshot = _snapshot_named_decorators(
        ("top_alias", "bottom_alias"),
        namespace,
    )
    assert snapshot is not None

    namespace["top_alias"] = replacement

    assert snapshot.names == ("top_alias", "bottom_alias")
    assert snapshot.values[0] is upper
    assert snapshot.values[1] is bottom
    assert namespace["top_alias"] is replacement

    application_order = tuple(
        reversed(tuple(zip(snapshot.names, snapshot.values)))
    )
    assert tuple(name for name, _value in application_order) == (
        "bottom_alias",
        "top_alias",
    )
    assert application_order[0][1] is bottom
    assert application_order[1][1] is upper


def test_noncallable_upper_stops_after_lower_effect_without_binding_f():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def upper(fn):\n    return fn\n",
        "pkg.bottom_effect": "pass\n",
        "pkg.app": (
            "from pkg.decorators import upper\n"
            "upper = None\n"
            "def bottom(fn):\n"
            "    import pkg.bottom_effect\n"
            "    return fn\n"
            "@upper\n"
            "@bottom\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "UNKNOWN"
    assert _calls(modeled) == (("pkg.app", "bottom"),)
    assert _starts(modeled) == (
        ("pkg.app", "pkg.decorators"),
        ("pkg.app", "pkg.bottom_effect"),
    )
    assert _local_imports(modeled) == (
        ("pkg.app", "pkg.bottom_effect", "pkg"),
    )
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "upper"
        for event in modeled.events
    )
    assert not any(
        event.operation == "BIND" and event.symbol == "f"
        for event in modeled.events
    )
    _assert_unique_module_starts(modeled)


def test_same_module_stack_keeps_bottom_up_event_sequence():
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.a": "pass\n",
        "pkg.b": "pass\n",
        "pkg.c": "pass\n",
        "pkg.app": (
            "def top_decorator(fn):\n"
            "    import pkg.a\n"
            "    return fn\n"
            "def middle_decorator(fn):\n"
            "    import pkg.b\n"
            "    return fn\n"
            "def bottom_decorator(fn):\n"
            "    import pkg.c\n"
            "    return fn\n"
            "@top_decorator\n"
            "@middle_decorator\n"
            "@bottom_decorator\n"
            "def f():\n"
            "    pass\n"
        ),
    }

    modeled = _model(sources)
    assert modeled.outcome == "MODEL_PASS"
    relevant = tuple(
        (event.operation, event.module, event.target, event.symbol)
        for event in modeled.events
        if (
            event.operation == "CALL_FUNCTION"
            or (
                event.operation == "START_IMPORT"
                and event.target in {"pkg.a", "pkg.b", "pkg.c"}
            )
            or (
                event.operation == "FUNCTION_LOCAL_IMPORT"
                and event.target in {"pkg.a", "pkg.b", "pkg.c"}
            )
        )
    )
    assert relevant == (
        ("CALL_FUNCTION", "pkg.app", None, "bottom_decorator"),
        ("START_IMPORT", "pkg.app", "pkg.c", None),
        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.c", "pkg"),
        ("CALL_FUNCTION", "pkg.app", None, "middle_decorator"),
        ("START_IMPORT", "pkg.app", "pkg.b", None),
        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.b", "pkg"),
        ("CALL_FUNCTION", "pkg.app", None, "top_decorator"),
        ("START_IMPORT", "pkg.app", "pkg.a", None),
        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.a", "pkg"),
    )
    _assert_unique_module_starts(modeled)

    called = _with_f_call(sources)
    assert called.outcome == "MODEL_PASS"
    assert _calls(called)[-1] == ("pkg.app", "f")


def test_single_imported_decorator_remains_model_pass():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "MODEL_PASS"
    assert _calls(modeled) == (("pkg.app", "identity"),)
    _assert_unique_module_starts(modeled)


def test_imported_class_decorator_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "class C:\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert modeled.events == ()


def test_external_functools_lru_cache_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.app": (
                "from functools import lru_cache\n"
                "@lru_cache\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert modeled.target_module == "functools"
    assert modeled.reached_unmodeled_import is not None
    assert (
        modeled.reached_unmodeled_import.operation,
        modeled.reached_unmodeled_import.target,
        modeled.reached_unmodeled_import.symbol,
    ) == ("FROM", "functools", "lru_cache")
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "lru_cache"
        for event in modeled.events
    )
