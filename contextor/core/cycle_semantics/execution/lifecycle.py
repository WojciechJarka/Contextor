from __future__ import annotations

from typing import Callable

from .state import _FunctionFrame


def _complete_module_frame(
    module: str,
    *,
    bootstrap: str,
    frames: list[tuple[str, int] | _FunctionFrame],
    states: dict[str, str],
    namespaces: dict[str, dict[str, object | None]],
    emit_event: Callable[
        [str, str, str | None, str | None],
        None,
    ],
) -> None:
    frames.pop()

    if module != bootstrap:
        states[module] = "READY"
        emit_event(module, "READY", None, None)

        if "." in module:
            parent, child = module.rsplit(".", 1)
            namespaces[parent][child] = module

            emit_event(
                parent,
                "BIND_CHILD",
                module,
                child,
            )


def _start_module_frame(
    target: str,
    *,
    importer: str,
    frames: list[tuple[str, int] | _FunctionFrame],
    states: dict[str, str],
    emit_event: Callable[
        [str, str, str | None, str | None],
        None,
    ],
) -> None:
    states[target] = "INITIALIZING"
    emit_event(importer, "START_IMPORT", target, None)
    frames.append((target, 0))
