"""Command-line control for the persistent Contextor MCP backend."""

from __future__ import annotations

import argparse
import json
import sys

from contextor.mcp_backend_control import (
    BackendControlError,
    BackendStatus,
    get_backend_status,
    start_backend,
    stop_backend,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextor backend",
        description=(
            "Control the persistent local Contextor MCP backend."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "start",
        help=(
            "Start the persistent backend or reuse an "
            "already-ready instance."
        ),
    )

    subparsers.add_parser(
        "status",
        help="Report authenticated backend readiness.",
    )

    subparsers.add_parser(
        "stop",
        help="Stop the identity-verified persistent backend.",
    )

    return parser


def _emit_status(
    status: BackendStatus,
) -> None:
    print(
        json.dumps(
            status.to_dict(),
            sort_keys=True,
        )
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = _build_parser().parse_args(argv)

    try:
        if args.command == "start":
            status = start_backend()

        elif args.command == "status":
            status = get_backend_status()

        else:
            status = stop_backend()

    except BackendControlError as exc:
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 1

    _emit_status(status)

    if args.command == "status":
        return 0 if status.ready else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
