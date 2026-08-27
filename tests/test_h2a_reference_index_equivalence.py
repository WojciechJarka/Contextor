"""
tests/test_h2a_reference_index_equivalence.py

Equivalence test verifying 100% 1:1 parity between legacy build_symbol_references
and the new RepositoryReferenceIndex across representative fixtures.
"""

from contextor.core.reference.engine import (
    _legacy_build_symbol_references,
    build_symbol_references,
)
from contextor.core.reference.index import build_repository_reference_index
from contextor.core.symbol_engine.indexer import index_repository


def test_reference_index_exact_equivalence_representative_fixture(tmp_path):
    """
    Representative fixture covering:
    1. Direct imports
    2. Aliased imports
    3. From-imports
    4. Qualified attribute access & method calls
    5. Re-exports (transitive and aliased)
    6. Two identical leaf names in different modules
    7. No references (unreferenced symbols)
    8. Dynamic / soft references (getattr)
    9. Class inheritance relationships
    10. Callbacks and event bindings
    """
    # 1. Provider A (defines ServiceA, Worker, run, helper)
    (tmp_path / "provider_a.py").write_text(
        "class ServiceA:\n"
        "    def run(self):\n"
        "        return 1\n"
        "\n"
        "class Worker:\n"
        "    pass\n"
        "\n"
        "def helper():\n"
        "    pass\n"
        "\n"
        "UNREFERENCED = 42\n",
        encoding="utf-8",
    )

    # 2. Provider B (defines ServiceB, Worker with same leaf name as Provider A)
    (tmp_path / "provider_b.py").write_text(
        "class ServiceB:\n"
        "    def execute(self):\n"
        "        pass\n"
        "\n"
        "class Worker:\n"
        "    pass\n",
        encoding="utf-8",
    )

    # 3. Facade with explicit re-exports
    (tmp_path / "facade.py").write_text(
        "from provider_a import ServiceA as PublicService, helper\n"
        "__all__ = ['PublicService', 'helper']\n",
        encoding="utf-8",
    )

    # 4. Consumer 1: Direct import, aliased import, qualified call, inheritance
    (tmp_path / "consumer_1.py").write_text(
        "import provider_a\n"
        "from facade import PublicService\n"
        "from provider_b import Worker as BWorker\n"
        "\n"
        "class SubService(PublicService):\n"
        "    pass\n"
        "\n"
        "def main():\n"
        "    svc = PublicService()\n"
        "    svc.run()\n"
        "    provider_a.helper()\n"
        "    b_worker = BWorker()\n",
        encoding="utf-8",
    )

    # 5. Consumer 2: Event bindings, callbacks, dynamic getattr, qualified attribute
    (tmp_path / "consumer_2.py").write_text(
        "from provider_a import helper\n"
        "from provider_b import ServiceB\n"
        "\n"
        "def on_click(handler=None):\n"
        "    pass\n"
        "\n"
        "def setup(event_emitter, obj):\n"
        "    event_emitter.bind('event', helper)\n"
        "    on_click(callback=helper)\n"
        "    getattr(obj, 'execute')()\n"
        "    val = provider_a.UNREFERENCED if False else None\n",
        encoding="utf-8",
    )

    modules = index_repository(str(tmp_path)).modules
    ref_index = build_repository_reference_index(modules, str(tmp_path))

    # Define targets to test
    test_cases = [
        ("provider_a", ["ServiceA", "Worker", "run", "helper", "UNREFERENCED"]),
        ("provider_b", ["ServiceB", "Worker", "execute"]),
        ("facade", ["PublicService", "helper"]),
    ]

    for definer_mod, symbols in test_cases:
        legacy_res = _legacy_build_symbol_references(
            modules,
            symbols,
            str(tmp_path),
            definer_module=definer_mod,
        )

        new_res = ref_index.build_symbol_references(
            symbols,
            definer_module=definer_mod,
        )

        direct_fn_res = build_symbol_references(
            modules,
            symbols,
            str(tmp_path),
            definer_module=definer_mod,
            reference_index=ref_index,
        )

        assert new_res == legacy_res, (
            f"Equivalence failed for {definer_mod} symbols {symbols}!\n"
            f"Legacy: {legacy_res}\n"
            f"New:    {new_res}"
        )

        assert direct_fn_res == legacy_res, (
            f"build_symbol_references wrapper failed for {definer_mod}!"
        )


def test_reference_api_exports_and_engine_all():
    """
    Verifies that:
    1. contextor.core.reference exports canonical public APIs.
    2. contextor.core.reference.engine.__all__ contains only actual module-level bindings.
    3. _legacy_build_symbol_references is not in __all__ but is directly importable by name.
    """
    import contextor.core.reference as pkg
    import contextor.core.reference.engine as engine

    # Package-level exports
    assert "RepositoryReferenceIndex" in pkg.__all__
    assert "build_repository_reference_index" in pkg.__all__
    assert "build_symbol_references" in pkg.__all__
    for name in pkg.__all__:
        assert hasattr(pkg, name), f"Package missing declared export: {name}"

    # Engine-level __all__
    assert "RepositoryReferenceIndex" not in engine.__all__
    assert "build_repository_reference_index" not in engine.__all__
    assert "_legacy_build_symbol_references" not in engine.__all__
    for name in engine.__all__:
        assert hasattr(engine, name), f"engine.__all__ references unbound symbol: {name}"

    # Direct importability of legacy helper
    from contextor.core.reference.engine import _legacy_build_symbol_references
    assert callable(_legacy_build_symbol_references)
