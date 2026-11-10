import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


OLD = """\
def f():
    import pkg.old
"""

NEW = """\
def f():
    import pkg.new
"""


CASES = [
    pytest.param(
        OLD + "\nf()\n",
        None,
        {"ok": True, "old": True, "new": False},
        id="direct-call",
    ),
    pytest.param(
        OLD + "\ng = f\ng()\n",
        None,
        {"ok": True, "old": True, "new": False,
         "alias_is_current": True},
        id="alias-call",
    ),
    pytest.param(
        OLD + "\ng = f\nf = None\ng()\n",
        None,
        {"ok": True, "old": True, "new": False,
         "alias_is_current": False},
        id="alias-survives-rebinding",
    ),
    pytest.param(
        OLD + "\ng = f\n" + NEW + "\ng()\n",
        None,
        {"ok": True, "old": True, "new": False,
         "alias_is_current": False},
        id="old-alias-survives-redefinition",
    ),
    pytest.param(
        OLD + "\ng = f\n" + NEW + "\nf()\n",
        None,
        {"ok": True, "old": False, "new": True,
         "alias_is_current": False},
        id="new-definition-call",
    ),
    pytest.param(
        OLD + "\ng = f\ng = None\ng()\n",
        None,
        {"ok": False, "old": False, "new": False,
         "error": "TypeError"},
        id="noncallable-rebinding",
    ),
    pytest.param(
        OLD,
        "from pkg import f\nf()\n",
        {"ok": True, "old": True, "new": False},
        id="foreign-function-cpython-control",
    ),
]


RUNNER = """\
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])

ok = True
error = None

try:
    importlib.import_module(sys.argv[2])
except Exception as exc:
    ok = False
    error = type(exc).__name__

pkg = sys.modules.get("pkg")

alias_is_current = None

if pkg is not None:
    namespace = vars(pkg)
    if "g" in namespace and "f" in namespace:
        alias_is_current = namespace["g"] is namespace["f"]

print(json.dumps({
    "ok": ok,
    "error": error,
    "old": "pkg.old" in sys.modules,
    "new": "pkg.new" in sys.modules,
    "alias_is_current": alias_is_current,
}))
"""


@pytest.mark.parametrize(
    "package_source,consumer_source,expected",
    CASES,
)
def test_restricted_function_identity_cpython(
    package_source,
    consumer_source,
    expected,
):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        package = root / "pkg"
        package.mkdir()

        (package / "__init__.py").write_text(
            package_source,
            encoding="utf-8",
        )
        (package / "old.py").write_text(
            "pass\n",
            encoding="utf-8",
        )
        (package / "new.py").write_text(
            "pass\n",
            encoding="utf-8",
        )

        entry = "pkg"

        if consumer_source is not None:
            (root / "consumer.py").write_text(
                consumer_source,
                encoding="utf-8",
            )
            entry = "consumer"

        process = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                RUNNER,
                str(root),
                entry,
            ],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

        assert process.returncode == 0, process.stderr

        observed = json.loads(process.stdout)

        for key, value in expected.items():
            assert observed[key] == value, (
                key,
                expected,
                observed,
                process.stderr,
            )
