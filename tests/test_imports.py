"""
Import hygiene.

Circular imports between layers can stay invisible for a long time: they
only surface when something happens to import the modules in the wrong
order. `contextor.core.domain` used to reach up into
`contextor.core.graph.graph` for a symbol that domain itself defines,
and that only worked because the package happened to be imported via a
path that fully initialized the graph module first.

Each module is imported in a fresh interpreter so no cached module can
mask a cycle.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Entry points and layer roots. Importing any of these first must work.
IMPORT_TARGETS = [
    "contextor",
    "contextor.cli",
    "contextor.core",
    "contextor.core.domain",
    "contextor.core.errors",
    "contextor.core.graph.graph",
    "contextor.core.graph.resolver",
    "contextor.core.paths",
    "contextor.core.api.facade",
    "contextor.core.symbol_engine.indexer",
    "contextor.core.reporting_engine.engine",
    "contextor.core.reporting_layer.artifact_usage_report",
    "contextor.core.validator",
]


@pytest.mark.parametrize("module", IMPORT_TARGETS)
def test_module_imports_standalone(module):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"importing {module} first failed:\n{result.stderr}"


def test_domain_does_not_depend_on_the_graph_layer():
    """
    Layering rule the codebase states in its own docstrings: domain
    models must not import from the graph layer.
    """

    source = (PROJECT_ROOT / "contextor" / "core" / "domain").rglob("*.py")

    offenders = [
        path.name for path in source if "contextor.core.graph" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"domain must not import the graph layer: {offenders}"
