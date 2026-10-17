"""Conditional reexport evidence without runtime execution."""

import ast
import json
from dataclasses import asdict
from pathlib import Path

from contextor.core.cycle_semantics.conditional_export import (
    analyze_conditional_reexport_order,
)


CHAIN = (
    "repo.__init__",
    "repo.main",
    "repo.filters",
    "ui.__init__",
    "ui.gui",
    "repo.__init__",
)


def _sources():
    return {
        "repo.__init__": ast.parse(
            "from repo.main import run_repo_generator"
        ),
        "repo.main": ast.parse(
            "from repo.filters import FilterWindow\n"
            "def run_repo_generator(parent=None):\n"
            "    pass"
        ),
        "repo.filters": ast.parse(
            "from ui import theme"
        ),
        "ui.__init__": ast.parse(
            "from .gui import run"
        ),
        "ui.gui": ast.parse(
            "from repo import run_repo_generator\n"
            "def run():\n"
            "    pass"
        ),
    }


def _analyze(sources=None, chain=CHAIN):
    return analyze_conditional_reexport_order(
        _sources() if sources is None else sources,
        chain,
        "run_repo_generator",
    )


def test_c26_valid_conditional_source_chain():
    result = _analyze()

    assert result.status == (
        "CONDITIONAL_DELAYED_REEXPORT"
    )
    assert result.provider_definition_line > (
        result.hops[1].line
    )
    assert len(result.hops) == 5
    assert result.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c26_relative_package_import_evidence():
    result = _analyze()

    assert result.hops[3].source_id == "ui.__init__"
    assert result.hops[3].target_id == "ui.gui"
    assert result.hops[3].requested_member == "run"


def test_c26_missing_import_hop_unknown():
    sources = _sources()
    sources["repo.filters"] = ast.parse("pass")

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == (
        "IMPORT_HOP_NOT_UNIQUELY_PROVED"
    )


def test_c26_duplicate_import_hop_unknown():
    sources = _sources()
    sources["repo.filters"] = ast.parse(
        "from ui import theme\n"
        "from ui import theme"
    )

    assert _analyze(sources).status == "UNKNOWN"


def test_c26_multimember_import_unknown():
    sources = _sources()
    sources["repo.filters"] = ast.parse(
        "from ui import theme, run"
    )

    assert _analyze(sources).status == "UNKNOWN"


def test_c26_definition_before_outgoing_import_unknown():
    sources = _sources()
    sources["repo.main"] = ast.parse(
        "def run_repo_generator():\n"
        "    pass\n"
        "from repo.filters import FilterWindow"
    )

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == (
        "PROVIDER_DEFINITION_NOT_DELAYED"
    )


def test_c26_prior_package_effect_unknown():
    sources = _sources()
    sources["repo.__init__"] = ast.parse(
        "setattr(module, 'run_repo_generator', fake)\n"
        "from repo.main import run_repo_generator"
    )

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == (
        "EARLIER_PACKAGE_EFFECT_UNSUPPORTED"
    )


def test_c26_closing_symbol_mismatch_unknown():
    sources = _sources()
    sources["ui.gui"] = ast.parse(
        "from repo import different_name"
    )

    assert _analyze(sources).status == "UNKNOWN"


def test_c26_real_contextor_sources_without_import():
    root = (
        Path(__file__).resolve().parents[1]
        / "contextor"
    )

    paths = {
        "contextor.repo_generator.__init__":
            root / "repo_generator" / "__init__.py",
        "contextor.repo_generator.main":
            root / "repo_generator" / "main.py",
        "contextor.repo_generator.filters":
            root / "repo_generator" / "filters.py",
        "contextor.ui.__init__":
            root / "ui" / "__init__.py",
        "contextor.ui.gui":
            root / "ui" / "gui.py",
    }

    sources = {
        name: ast.parse(
            path.read_text(encoding="utf-8")
        )
        for name, path in paths.items()
    }

    chain = (
        "contextor.repo_generator.__init__",
        "contextor.repo_generator.main",
        "contextor.repo_generator.filters",
        "contextor.ui.__init__",
        "contextor.ui.gui",
        "contextor.repo_generator.__init__",
    )

    result = analyze_conditional_reexport_order(
        sources,
        chain,
        "run_repo_generator",
    )

    assert result.status == (
        "CONDITIONAL_DELAYED_REEXPORT"
    )
    assert result.provider_definition_line > (
        result.hops[1].line
    )
    assert result.prefix_execution_status == (
        "UNVERIFIED_TRANSITIVE_PREFIX"
    )
    assert result.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c26_determinism_immutability_json():
    sources = _sources()

    before = {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in sources.items()
    }

    first = _analyze(sources)
    second = _analyze(sources)

    assert first == second
    assert len(first.hops) == 5

    assert before == {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in sources.items()
    }

    json.dumps(asdict(first))


def test_c26_invalid_chain_unknown():
    assert _analyze(
        chain=(
            "repo.__init__",
            "repo.main",
            "repo.__init__",
        )
    ).status == "UNKNOWN"


def test_c26f_invalid_opaque_provider_unknown():
    sources = _sources()
    sources["repo.main"] = ast.parse(
        "from repo.filters import FilterWindow\n"
        "def run_repo_generator():\n"
        "    from repo.filters import *"
    )

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == "SOURCE_NOT_COMPILABLE"
    assert result.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_c26f_skipped_guard_cannot_hide_syntax_error():
    sources = _sources()
    sources["ui.gui"] = ast.parse(
        "from repo import run_repo_generator\n"
        'if __name__ == "__main__":\n'
        "    def invalid():\n"
        "        from repo import *"
    )

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == "SOURCE_NOT_COMPILABLE"


def test_c26f_missing_ast_location_fails_closed():
    sources = _sources()

    sources["repo.__init__"] = ast.Module(
        body=[
            ast.ImportFrom(
                module="repo.main",
                names=[
                    ast.alias(
                        name="run_repo_generator",
                        asname=None,
                    )
                ],
                level=0,
            )
        ],
        type_ignores=[],
    )

    result = _analyze(sources)

    assert result.status == "UNKNOWN"
    assert result.reason == "SOURCE_NOT_COMPILABLE"
