"""
tests/test_usage_delta.py

Pure unit tests for UsageDelta model and diff_usage_facts helper.
"""

from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta, diff_usage_facts


def test_usage_delta_identical_facts_returns_empty_delta():
    facts = ModuleUsageFacts(
        imports=("math",),
        direct_calls=("math.sqrt",),
    )
    delta = diff_usage_facts("mod_a", facts, facts)
    assert delta.is_empty
    assert delta.added_direct_calls == ()
    assert delta.removed_direct_calls == ()


def test_usage_delta_empty_to_populated():
    old_facts = ModuleUsageFacts()
    new_facts = ModuleUsageFacts(
        imports=("os",),
        direct_calls=("os.path.join",),
        qualified_refs=("os.path",),
    )
    delta = diff_usage_facts("mod_a", old_facts, new_facts)
    assert not delta.is_empty
    assert delta.added_imports == ("os",)
    assert delta.added_direct_calls == ("os.path.join",)
    assert delta.added_qualified_refs == ("os.path",)
    assert delta.removed_direct_calls == ()


def test_usage_delta_populated_to_empty():
    old_facts = ModuleUsageFacts(
        imports=("os",),
        direct_calls=("os.path.join",),
    )
    new_facts = ModuleUsageFacts()
    delta = diff_usage_facts("mod_a", old_facts, new_facts)
    assert not delta.is_empty
    assert delta.removed_imports == ("os",)
    assert delta.removed_direct_calls == ("os.path.join",)
    assert delta.added_direct_calls == ()


def test_usage_delta_direct_call_target_changed():
    old_facts = ModuleUsageFacts(direct_calls=("target.foo",))
    new_facts = ModuleUsageFacts(direct_calls=("target.bar",))
    delta = diff_usage_facts("mod_a", old_facts, new_facts)
    assert delta.removed_direct_calls == ("target.foo",)
    assert delta.added_direct_calls == ("target.bar",)


def test_usage_delta_alias_and_qualified_changed():
    old_facts = ModuleUsageFacts(aliases=(("sqrt", "math.sqrt"),))
    new_facts = ModuleUsageFacts(aliases=(("pow", "math.pow"),))
    delta = diff_usage_facts("mod_a", old_facts, new_facts)
    assert delta.removed_aliases == (("sqrt", "math.sqrt"),)
    assert delta.added_aliases == (("pow", "math.pow"),)


def test_usage_delta_inheritance_and_channels():
    old_facts = ModuleUsageFacts(inheritance_refs=(("Child", "BaseOld"),))
    new_facts = ModuleUsageFacts(inheritance_refs=(("Child", "BaseNew"),))
    delta = diff_usage_facts("mod_a", old_facts, new_facts)
    assert delta.removed_inheritance_refs == (("Child", "BaseOld"),)
    assert delta.added_inheritance_refs == (("Child", "BaseNew"),)
