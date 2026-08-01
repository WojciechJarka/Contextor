"""
contextor/cli.py

CLI Layer.

Thin wrapper over ContextorFacade. All analytical work - indexing,
graph building, validation, report generation - lives in the facade,
so the CLI and the GUI cannot drift apart in what they produce.
"""

import argparse
import sys
from pathlib import Path

from contextor.core.api.facade import ContextorFacade
from contextor.core.errors import AnalysisCancelled
from contextor.core.paths import output_dir

__version__ = "1.0.4"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextor",
        description=(
            "Static architectural analysis of a Python repository. "
            "Generates JSON and Markdown context reports."
        ),
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory of the repository to analyze (default: current directory).",
    )

    parser.add_argument(
        "--layer",
        metavar="DIR",
        help="Optional subdirectory of the repository to report on separately.",
    )

    parser.add_argument(
        "--file",
        metavar="PY_FILE",
        help="Optional single .py file to analyze in the context of the repository.",
    )

    parser.add_argument(
        "--output",
        metavar="DIR",
        help="Directory to write reports into (default: the Contextor output directory).",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"Contextor {__version__}",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    # Backwards compatibility: main("some/path") used to be a valid call.
    if isinstance(argv, str):
        argv = [argv]

    args = _build_parser().parse_args(argv)

    if args.output:
        import os

        os.environ["CONTEXTOR_OUTPUT_DIR"] = args.output

    root = Path(args.path).expanduser()

    if not root.is_dir():
        print(f"[ERROR] Not a directory: {root}", file=sys.stderr)
        return 2

    root = str(root.resolve())

    log = None if args.quiet else (lambda message: print(f"[INFO] {message}"))

    try:
        errors = ContextorFacade.analyze_project(root, log=log)

        if args.layer:
            layer = Path(args.layer).expanduser().resolve()

            if not layer.is_dir():
                print(f"[ERROR] Not a directory: {layer}", file=sys.stderr)
                return 2

            ContextorFacade.analyze_layer(root, str(layer), log=log)

        if args.file:
            target = Path(args.file).expanduser().resolve()

            if not target.is_file():
                print(f"[ERROR] Not a file: {target}", file=sys.stderr)
                return 2

            ContextorFacade.analyze_single_file(str(target), root, log=log)

    except AnalysisCancelled:
        print("[INFO] Analysis cancelled.")
        return 130

    if not args.quiet:
        print(f"[INFO] Reports written to: {output_dir()}")

    for error in errors:
        print(f"[{error.kind}] {error.message}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
