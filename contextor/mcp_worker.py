"""Subprocess entry point for process-pool analyses requested over MCP."""

from __future__ import annotations

import argparse
import multiprocessing
import sys
import traceback
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("project", "layer", "single_file"))
    parser.add_argument("repo_path")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args(argv)

    root = Path(args.repo_path).resolve()
    try:
        from contextor.core.api.facade import ContextorFacade

        if args.operation == "project":
            _, analysis_result = ContextorFacade.analyze_project(str(root), log=_log)
            if analysis_result is None:
                raise RuntimeError("Analysis returned no canonical state.")
        elif args.operation == "layer":
            if not args.target:
                raise ValueError("Layer analysis requires a target directory.")
            ContextorFacade.analyze_layer(str(root), args.target, log=_log)
        else:
            if not args.target:
                raise ValueError("Single-file analysis requires a target file.")
            ContextorFacade.analyze_single_file(args.target, str(root), log=_log)
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
