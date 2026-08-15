"""Small polling tail used inside the optional Windows CMD log window."""

from __future__ import annotations

import sys
import time
from pathlib import Path


def follow(path: Path, *, poll_interval: float = 0.2, initial_lines: int = 200) -> None:
    """Print the current tail and follow appended UTF-8 text until interrupted."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
        for line in lines[-initial_lines:]:
            print(line, end="", flush=True)
        while True:
            line = handle.readline()
            if line:
                print(line, end="", flush=True)
            else:
                time.sleep(poll_interval)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python -m contextor.core.program_log_tail <log-path>")
        return 2
    try:
        follow(Path(args[0]))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
