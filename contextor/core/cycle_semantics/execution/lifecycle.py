from __future__ import annotations

from typing import Callable


def _complete_module_frame(
    module: str,
    *,
    bootstrap: str,
    frames: list[tuple[str, int]],
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
