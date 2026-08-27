"""
tests/test_h2a_hard_reset_regression.py

Hard-Reset regression test verifying that full analysis builds reference facts
strictly from current workspace and ignores absent or corrupted previous canonical state.
"""

import json
from pathlib import Path

from contextor.core.api.facade import ContextorFacade
from contextor.core.paths import repo_cache_dir


def test_full_analysis_hard_reset_with_corrupted_previous_canonical(tmp_path):
    """
    Verifies that Full Analysis:
    1. Rebuilds the reference index solely from current workspace.
    2. Completely ignores absent or corrupted previous canonical state.
    3. Produces output identical to clean baseline.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "provider.py").write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "consumer.py").write_text(
        "from pkg.provider import Service\n"
        "def main():\n"
        "    s = Service()\n"
        "    return s.run()\n",
        encoding="utf-8",
    )

    # 1. Clean Full Analysis Run
    errors_1, result_1 = ContextorFacade.analyze_project(str(tmp_path))
    assert not errors_1, f"Analysis errors: {errors_1}"
    assert result_1.artifacts, "Artifacts must be populated in analysis result"

    # 2. Corrupt Canonical Cache / Previous State
    cache_dir = repo_cache_dir(str(tmp_path))
    if cache_dir.exists():
        for item in cache_dir.iterdir():
            if item.is_file():
                item.write_text("CORRUPTED_GARBAGE_DATA_12345", encoding="utf-8")

    # 3. Re-run Full Analysis (Hard Reset)
    errors_2, result_2 = ContextorFacade.analyze_project(str(tmp_path))
    assert not errors_2, f"Second analysis errors: {errors_2}"

    # 4. Assert exact parity of regenerated artifacts
    assert result_2.artifacts == result_1.artifacts
    assert len(result_2.artifacts) == len(result_1.artifacts)
