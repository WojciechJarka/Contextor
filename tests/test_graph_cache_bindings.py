from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.graph.graph import build_graph
from contextor.core.graph.incremental import _CACHE, get_cached_graph


def test_package_binding_change_invalidates_graph_cache():
    modules = {
        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", "/pkg/__init__.py", []),
        "pkg.child": Module("pkg.child", "pkg/child.py", "/pkg/child.py", []),
        "consumer": Module(
            "consumer",
            "consumer.py",
            "/consumer.py",
            [ImportRef("pkg", 0, ["child"], True)],
        ),
    }
    unbound = {"pkg.__init__": {"bindings": {}, "star_sources": []}}
    bound = {
        "pkg.__init__": {
            "bindings": {"child": "pkg.__init__.child"},
            "star_sources": [],
        }
    }

    def build(facts):
        return get_cached_graph(
            modules,
            lambda current: build_graph(
                current, reexport_facts_by_module=facts
            ),
            reexport_facts_by_module=facts,
        )

    original_cache = _CACHE.copy()
    try:
        _CACHE.clear()
        first, first_hit = build(unbound)
        same, same_hit = build(unbound)
        changed, changed_hit = build(bound)
        repeated, repeated_hit = build(bound)
        assert first_hit is False
        assert same_hit is True
        assert same is first
        assert changed_hit is False
        assert changed.soft_edges["consumer"] == set()
        assert first.soft_edges["consumer"] == {"pkg.child"}
        assert repeated_hit is True
        assert repeated is changed
        assert len(_CACHE) == 2
    finally:
        _CACHE.clear()
        _CACHE.update(original_cache)


def test_legacy_two_argument_graph_cache_call_remains_supported():
    modules = {"empty": Module("empty", "empty.py", "/empty.py", [])}
    original_cache = _CACHE.copy()
    try:
        _CACHE.clear()
        first, first_hit = get_cached_graph(modules, build_graph)
        second, second_hit = get_cached_graph(modules, build_graph)
        assert first_hit is False
        assert second_hit is True
        assert second is first
    finally:
        _CACHE.clear()
        _CACHE.update(original_cache)
