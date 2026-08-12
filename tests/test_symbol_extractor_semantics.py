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
