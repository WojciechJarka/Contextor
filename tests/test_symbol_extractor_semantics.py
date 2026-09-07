"""Focused semantic tests for public symbol and signature extraction."""

from contextor.core.symbol_engine.extractor import extract_symbol_facts


def test_decorated_signatures_exclude_decorators_and_nested_defs_are_not_artifacts(
    tmp_path,
):
    source = tmp_path / "sample.py"
    source.write_text(
        "@tool(\n"
        "    name='public',\n"
        ")\n"
        "def public(value: int = 1) -> str:\n"
        "    def local_helper():\n"
        "        return 'local'\n"
        "    return str(value)\n"
        "\n"
        "class Service:\n"
        "    @classmethod\n"
        "    async def run(cls, item: str) -> None:\n"
        "        async def local_async():\n"
        "            return None\n"
        "        class LocalClass:\n"
        "            def hidden(self):\n"
        "                pass\n"
        "        await local_async()\n",
        encoding="utf-8",
    )

    facts = extract_symbol_facts(source)

    assert facts.functions == {"public"}
    assert facts.classes == {"Service"}
    assert facts.methods == {"Service.run"}
    assert facts.signatures == {
        "public": "def public(value: int=1) -> str",
        "Service.run": "async def run(cls, item: str) -> None",
    }
    assert all("@" not in signature for signature in facts.signatures.values())


def test_assignments_are_globals_only_at_module_scope(tmp_path):
    source = tmp_path / "scope_fixture.py"
    source.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "MODULE_ASSIGN = 1\n"
        "MODULE_ANN: int\n"
        "MODULE_ANN_DEFAULT: int = 3\n"
        "\n"
        "@dataclass\n"
        "class Data:\n"
        "    field: int\n"
        "    default: int = 0\n"
        "\n"
        "    def method(self):\n"
        "        return self.field\n"
        "\n"
        "class Outer:\n"
        "    CLASS_ASSIGN = 1\n"
        "    CLASS_ANN: int\n"
        "    CLASS_ANN_DEFAULT: int = 3\n"
        "\n"
        "    class Inner:\n"
        "        INNER_FIELD = 1\n"
        "\n"
        "    def method(self):\n"
        "        return self.CLASS_ASSIGN\n"
        "\n"
        "def factory():\n"
        "    local_assign = 1\n"
        "    local_ann: int\n"
        "\n"
        "    class LocalClass:\n"
        "        LOCAL_FIELD = 1\n"
        "\n"
        "    return local_assign\n",
        encoding="utf-8",
    )

    facts = extract_symbol_facts(source)

    assert facts.globals == {
        "MODULE_ASSIGN",
        "MODULE_ANN",
        "MODULE_ANN_DEFAULT",
    }
    assert {
        "Data",
        "Outer",
        "Inner",
    } <= facts.classes
    assert facts.functions == {"factory"}
    assert facts.methods == {"Data.method", "Outer.method"}
    assert {
        "MODULE_ASSIGN",
        "MODULE_ANN",
        "MODULE_ANN_DEFAULT",
        "CLASS_ASSIGN",
        "CLASS_ANN",
        "CLASS_ANN_DEFAULT",
        "INNER_FIELD",
    } <= facts.assignments
    assert not {
        "local_assign",
        "local_ann",
        "LOCAL_FIELD",
    } & facts.globals


def test_class_assignments_inside_nested_scopes_never_become_globals(tmp_path):
    source = tmp_path / "nested_scope_fixture.py"
    source.write_text(
        "class ModuleClass:\n"
        "    module_class_field = 1\n"
        "\n"
        "    class NestedClass:\n"
        "        nested_class_field = 1\n"
        "\n"
        "def make_class():\n"
        "    class FunctionClass:\n"
        "        function_class_field = 1\n"
        "\n"
        "    return FunctionClass\n",
        encoding="utf-8",
    )

    facts = extract_symbol_facts(source)

    assert facts.globals == set()
    assert not {
        "module_class_field",
        "nested_class_field",
        "function_class_field",
    } & facts.globals
