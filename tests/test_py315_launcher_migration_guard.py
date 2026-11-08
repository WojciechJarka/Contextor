"""Windows launcher contracts for the Python 3.15 migration guard."""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = (
    "run_contextor.bat",
    "GUI_test_suite_installer.bat",
    "MCP_installer.bat",
)
GUARD = ".contextor_py315_cutover.guard"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows BAT contract")
@pytest.mark.parametrize("launcher", LAUNCHERS)
@pytest.mark.parametrize("bang_path", (False, True))
def test_guarded_launcher_exits_before_application_work(tmp_path, launcher, bang_path):
    checkout = tmp_path / ("checkout!bang" if bang_path else "checkout")
    checkout.mkdir()
    script = checkout / launcher
    script.write_bytes((ROOT / launcher).read_bytes())
    (checkout / GUARD).touch()
    marker = checkout / "application_started.txt"
    (checkout / "main.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmd.exe", "/D", "/C", str(script)],
        cwd=checkout,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 86
    assert "CONTEXTOR_CUTOVER_ACTIVE" in result.stdout
    assert not (checkout / ".venv").exists()
    assert not marker.exists()


def test_installers_do_not_install_editable_distribution():
    for name in ("GUI_test_suite_installer.bat", "MCP_installer.bat"):
        source = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "pip install -e" not in source


def test_launchers_have_no_hardcoded_python_310_fallback():
    for name in LAUNCHERS:
        source = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "c:\\spiralprophet\\python\\wpy64-31090" not in source


@pytest.mark.parametrize(
    "name", ("run_contextor.bat", "GUI_test_suite_installer.bat")
)
def test_venv_bootstrap_requires_validated_cpython_315(name):
    source = (ROOT / name).read_text(encoding="utf-8").lower()
    assert "c:\\python315\\python.exe" in source
    assert "python -i -b -c" in source
    assert "sys.implementation.name == 'cpython'" in source
    assert "sys.version_info[:2] == (3, 15)" in source
    assert "python --version" not in source
    assert "for /d %%d" not in source


def test_mcp_installer_uses_only_project_local_venv():
    source = (ROOT / "MCP_installer.bat").read_text(encoding="utf-8").lower()
    assert 'set "python_exe=%cd%\\.venv\\scripts\\python.exe"' in source
    assert 'if not exist "%python_exe%"' in source
    assert "python --version" not in source
    assert "for /d %%d" not in source


def test_py315_project_metadata_and_ruff_contract():
    config = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    assert (
        config["project"]["requires-python"]
        == ">=3.15,<3.16"
    )
    assert (
        config["tool"]["ruff"]["target-version"]
        == "py315"
    )
    assert (
        "ruff>=0.17.0"
        in config["project"]["optional-dependencies"]["dev"]
    )

    assert (
        "pytest>=7.4"
        in config["project"]["optional-dependencies"]["dev"]
    )


def test_launcher_optional_ruff_uses_project_venv():
    source = (
        ROOT / "run_contextor.bat"
    ).read_text(encoding="utf-8").lower()

    assert source.count("goto check_ruff") == 2
    assert ":check_ruff\n" in source

    assert "m.version('ruff')" in source
    assert ">= (0,17,0)" in source

    assert (
        'if not exist "%venv_dir%\\scripts\\ruff.exe" '
        'goto install_ruff'
    ) in source

    assert (
        '"%venv_py%" -m pip install "ruff>=0.17.0"'
    ) in source

    assert ":install_ruff\n" in source
    assert ":ruff_unavailable\n" in source

    optional_failure = source.split(
        ":ruff_unavailable\n", 1
    )[1].split(
        ":check_backend_autostart\n", 1
    )[0]

    assert "goto check_backend_autostart" in optional_failure
    assert "continuing without optional lint tooling" in (
        optional_failure
    )
