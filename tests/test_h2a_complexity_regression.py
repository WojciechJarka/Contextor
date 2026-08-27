"""
tests/test_h2a_complexity_regression.py

Complexity regression tests verifying single-pass O(N) AST traversal and O(1) projection.
"""

from unittest.mock import patch
import ast
from pathlib import Path

from contextor.core.reference.engine import build_symbol_references
from contextor.core.reference.index import (
    RepositoryReferenceIndex,
    SinglePassConsumerVisitor,
    build_repository_reference_index,
)
from contextor.core.symbol_engine.indexer import index_repository
import contextor.core.source as src_mod


def test_single_pass_complexity_and_zero_projection_traversals(tmp_path):
    """
    Verifies that:
    1. For N consumer modules, building RepositoryReferenceIndex visits consumer ASTs at most N times.
    2. Subsequent projections across M definers trigger ZERO additional AST visits,
       ZERO parse_source calls, and ZERO stat calls.
    """
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text(
            f"import mod_{(i+1)%5}\n"
            f"class Cls{i}:\n"
            f"    def do_{i}(self):\n"
            f"        pass\n"
            f"def call_{i}():\n"
            f"    return mod_{(i+1)%5}.call_{(i+1)%5}()\n",
            encoding="utf-8",
        )

    modules = index_repository(str(tmp_path)).modules
    module_count = len(modules)
    assert module_count == 5

    # 1. Measure AST visits during index build (exactly 1 visitor per consumer module)
    with patch("contextor.core.reference.index.SinglePassConsumerVisitor", wraps=SinglePassConsumerVisitor) as spy_cls:
        ref_index = build_repository_reference_index(modules, str(tmp_path))
        assert spy_cls.call_count == module_count, (
            f"Expected {module_count} consumer visitors during index build, got {spy_cls.call_count}"
        )

    # 2. Measure operations during definer projections
    with patch.object(src_mod, "read_source", wraps=src_mod.read_source) as spy_read, \
         patch.object(src_mod, "parse_source", wraps=src_mod.parse_source) as spy_parse, \
         patch.object(SinglePassConsumerVisitor, "visit") as spy_visit_proj, \
         patch.object(Path, "stat", wraps=Path.stat) as spy_stat:

        for i in range(5):
            res = ref_index.build_symbol_references(
                [f"Cls{i}", f"do_{i}", f"call_{i}"],
                definer_module=f"mod_{i}",
            )
            assert f"Cls{i}" in res

        # Assert zero operations during projection
        assert spy_visit_proj.call_count == 0, "Projections must not perform AST visits!"
        assert spy_read.call_count == 0, "Projections must not read source files!"
        assert spy_parse.call_count == 0, "Projections must not parse source ASTs!"
        assert spy_stat.call_count == 0, "Projections must not stat file paths!"
