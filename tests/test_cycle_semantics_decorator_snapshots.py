from contextor.core.cycle_semantics.execution.calls import (
    _DecoratorSnapshot,
    _new_restricted_function,
    _snapshot_named_decorators,
)


def test_snapshot_preserves_source_order_and_identity():
    upper = _new_restricted_function("pkg", ())
    lower = _new_restricted_function("pkg", ())

    namespace = {
        "upper": upper,
        "lower": lower,
    }

    snapshot = _snapshot_named_decorators(
        ("upper", "lower"),
        namespace,
    )

    assert isinstance(snapshot, _DecoratorSnapshot)
    assert snapshot.names == ("upper", "lower")
    assert snapshot.values[0] is upper
    assert snapshot.values[1] is lower


def test_rebinding_after_snapshot_preserves_objects():
    upper = _new_restricted_function("pkg", ())
    lower = _new_restricted_function("pkg", ())
    namespace = {"upper": upper, "lower": lower}

    snapshot = _snapshot_named_decorators(
        ("upper", "lower"),
        namespace,
    )

    namespace["upper"] = None
    namespace["lower"] = None

    assert snapshot.values[0] is upper
    assert snapshot.values[1] is lower


def test_repeated_name_preserves_duplicate_identity():
    decorator = _new_restricted_function("pkg", ())
    namespace = {"deco": decorator}

    snapshot = _snapshot_named_decorators(
        ("deco", "deco"),
        namespace,
    )

    assert snapshot.names == ("deco", "deco")
    assert snapshot.values[0] is decorator
    assert snapshot.values[1] is decorator


def test_none_binding_is_snapshot_value():
    snapshot = _snapshot_named_decorators(
        ("deco",),
        {"deco": None},
    )

    assert snapshot is not None
    assert snapshot.values == (None,)


def test_missing_name_rejects_entire_snapshot():
    decorator = _new_restricted_function("pkg", ())

    assert _snapshot_named_decorators(
        ("upper", "missing"),
        {"upper": decorator},
    ) is None


def test_invalid_names_and_empty_stack_rejected():
    decorator = _new_restricted_function("pkg", ())
    namespace = {"deco": decorator}

    for names in (
        (),
        ("",),
        ("__hidden",),
        ("not-valid",),
    ):
        assert _snapshot_named_decorators(
            names,
            namespace,
        ) is None


def test_snapshot_does_not_modify_namespace():
    decorator = _new_restricted_function("pkg", ())
    namespace = {"deco": decorator}
    before = dict(namespace)

    snapshot = _snapshot_named_decorators(
        ("deco",),
        namespace,
    )

    assert snapshot is not None
    assert namespace == before
    assert namespace["deco"] is decorator
