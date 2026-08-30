import json

import pytest

from contextor.core.reference.index import (
    RepositoryReferenceIndex,
    SinglePassConsumerVisitor,
    extract_compact_reference_facts,
)
from contextor.core.symbol_engine.indexer import index_repository


def _normalized(index):
    return {
        key: value
        for key, value in vars(index).items()
        if key not in {"modules", "root_path"}
    }


def _representative_modules(tmp_path):
    sources = {
        "provider_a.py": (
            "class Service:\n"
            "    def run(self): pass\n"
            "class Worker: pass\n"
            "def helper(): pass\n"
            "UNUSED = 1\n"
        ),
        "provider_b.py": "class Worker: pass\nclass Service: pass\n",
        "facade_a.py": (
            "from provider_a import Service as PublicService, helper\n"
            "__all__ = ['PublicService', 'helper']\n"
        ),
        "facade_b.py": "from facade_a import *\n",
        "facade_c.py": (
            "from facade_b import PublicService as FinalService\n"
            "__all__ = ['FinalService']\n"
        ),
        "consumer.py": (
            "import provider_a as pa\n"
            "from facade_c import FinalService\n"
            "from provider_b import Worker as OtherWorker\n"
            "class Child(FinalService): pass\n"
            "def use(emitter, obj):\n"
            "    service = FinalService()\n"
            "    service.run()\n"
            "    pa.helper()\n"
            "    emitter.bind('done', pa.helper)\n"
            "    configure(callback=pa.helper)\n"
            "    getattr(obj, 'run')()\n"
            "    value = pa.UNUSED\n"
            "    OtherWorker()\n"
        ),
        "star_consumer.py": "from facade_a import *\nhelper()\n",
        "empty.py": "",
    }
    for name, source in sources.items():
        (tmp_path / name).write_text(source, encoding="utf-8")
    return index_repository(str(tmp_path)).modules


def test_ast_build_exactly_equals_compact_facts_build(tmp_path):
    modules = _representative_modules(tmp_path)
    compact = {
        module_id: extract_compact_reference_facts(module_id, module)
        for module_id, module in modules.items()
    }

    json.dumps(compact)
    ast_built = RepositoryReferenceIndex.build(modules, str(tmp_path))
    compact_built = RepositoryReferenceIndex.from_compact_facts(
        modules, str(tmp_path), compact
    )

    assert _normalized(ast_built) == _normalized(compact_built)
    for module_id in modules:
        assert compact[module_id]["status"] == "available"
    assert compact["empty"]["facts"] is not None


def test_compact_build_matches_all_projected_reference_fields(tmp_path):
    modules = _representative_modules(tmp_path)
    compact = {
        module_id: extract_compact_reference_facts(module_id, module)
        for module_id, module in modules.items()
    }
    ast_built = RepositoryReferenceIndex.build(modules, str(tmp_path))
    compact_built = RepositoryReferenceIndex.from_compact_facts(
        modules, str(tmp_path), compact
    )

    cases = {
        "provider_a": ["Service", "Worker", "run", "helper", "UNUSED"],
        "provider_b": ["Worker", "Service"],
        "facade_a": ["PublicService", "helper"],
        "facade_c": ["FinalService"],
    }
    for module_id, symbols in cases.items():
        assert ast_built.build_symbol_references(
            symbols, module_id
        ) == compact_built.build_symbol_references(symbols, module_id)


def test_compact_extraction_failure_is_not_treated_as_empty(tmp_path, monkeypatch):
    modules = _representative_modules(tmp_path)
    original_visit = SinglePassConsumerVisitor.visit

    def fail_for_consumer(self, node):
        if self.current_module == "consumer":
            raise LookupError("forced extraction failure")
        return original_visit(self, node)

    monkeypatch.setattr(SinglePassConsumerVisitor, "visit", fail_for_consumer)
    compact = {
        module_id: extract_compact_reference_facts(module_id, module)
        for module_id, module in modules.items()
    }

    assert compact["consumer"] == {
        "status": "failure",
        "facts": None,
        "error_type": "LookupError",
        "message": "forced extraction failure",
    }
    with pytest.raises(RuntimeError, match="consumer: LookupError"):
        RepositoryReferenceIndex.from_compact_facts(
            modules, str(tmp_path), compact
        )


def test_compact_build_rejects_missing_module_facts(tmp_path):
    modules = _representative_modules(tmp_path)
    compact = {
        module_id: extract_compact_reference_facts(module_id, module)
        for module_id, module in modules.items()
        if module_id != "empty"
    }

    with pytest.raises(ValueError, match="empty"):
        RepositoryReferenceIndex.from_compact_facts(
            modules, str(tmp_path), compact
        )
