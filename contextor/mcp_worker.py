"""Subprocess entry point for process-pool analyses requested over MCP."""

from __future__ import annotations

import argparse
import faulthandler
import importlib
import importlib.metadata
import json
import multiprocessing
import os
import sys
from datetime import datetime
import traceback
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def _log(message: str) -> None:
    print(
        f"{datetime.now().isoformat(timespec='milliseconds')} "
        f"pid={os.getpid()} {message}",
        file=sys.stderr,
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    trace_handle = None
    trace_path = os.environ.get("CONTEXTOR_WORKER_TRACE")
    if trace_path:
        trace_handle = open(trace_path, "a", encoding="utf-8", buffering=1)
        faulthandler.enable(file=trace_handle, all_threads=True)
        faulthandler.dump_traceback_later(20, repeat=True, file=trace_handle)
        warnings.resetwarnings()
        warnings.simplefilter("default")

    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("project", "layer", "single_file"))
    parser.add_argument("repo_path")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args(argv)

    root = Path(args.repo_path).resolve()
    _log(f"worker_enter operation={args.operation} root={root}")
    _log(f"runtime executable={sys.executable} version={sys.version!r}")
    _log(f"runtime sys_path={json.dumps(sys.path)}")
    for package_name in ("contextor", "fastmcp", "mcp", "pydantic", "anyio"):
        try:
            module = importlib.import_module(package_name)
            try:
                version = importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                version = "local/unversioned"
            _log(
                f"package name={package_name} version={version} "
                f"file={getattr(module, '__file__', None)}"
            )
        except Exception as exc:
            _log(f"package name={package_name} import_error={exc!r}")
    _log(
        "environment "
        + json.dumps(
            {
                key: os.environ.get(key)
                for key in (
                    "CONTEXTOR_CACHE_DIR",
                    "CONTEXTOR_DISABLE_PROCESS_POOL",
                    "PYTHONPATH",
                    "PYTHONHOME",
                    "PYTHONIOENCODING",
                    "PYTHONUNBUFFERED",
                    "VIRTUAL_ENV",
                )
            },
            sort_keys=True,
        )
    )
    try:
        from contextor.core.api.facade import ContextorFacade
        _log("facade_imported")

        if args.operation == "project":
            _, analysis_result = ContextorFacade.analyze_project(str(root), log=_log)
            _log("facade_analyze_project_returned")
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
        _log("worker_success")
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        faulthandler.cancel_dump_traceback_later()
        if trace_handle is not None:
            trace_handle.close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
