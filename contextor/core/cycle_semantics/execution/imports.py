from __future__ import annotations

from typing import Mapping


def _chain(name: str) -> tuple[str, ...]:
    parts = name.split(".")

    return tuple(
        ".".join(parts[:index])
        for index in range(1, len(parts) + 1)
    )


def _missing_piece(
    name: str,
    states: Mapping[str, str],
) -> str | None:
    for piece in _chain(name):
        if piece not in states:
            return piece

        if states[piece] == "NEW":
            return piece

    return None
