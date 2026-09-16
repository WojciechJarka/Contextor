from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator


_registry_lock = threading.RLock()
_registry_pid = os.getpid()
_active_executors: dict[int, Any] = {}


def _ensure_process_local_registry_locked() -> None:
    global _registry_pid

    current_pid = os.getpid()
    if current_pid == _registry_pid:
        return

    _active_executors.clear()
    _registry_pid = current_pid


def _register_executor(executor: Any) -> None:
    with _registry_lock:
        _ensure_process_local_registry_locked()
        _active_executors[id(executor)] = executor


def _unregister_executor(executor: Any) -> None:
    with _registry_lock:
        _ensure_process_local_registry_locked()
        _active_executors.pop(id(executor), None)


def active_process_pool_count() -> int:
    with _registry_lock:
        _ensure_process_local_registry_locked()
        return len(_active_executors)


@contextmanager
def managed_process_pool(
    executor_factory: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Iterator[Any]:
    executor = executor_factory(*args, **kwargs)
    _register_executor(executor)
    try:
        with executor as entered:
            yield entered
    finally:
        _unregister_executor(executor)


def _executor_processes(executor: Any) -> tuple[Any, ...]:
    processes = getattr(executor, "_processes", None)
    if not isinstance(processes, dict):
        return ()
    return tuple(
        process
        for process in processes.values()
        if process is not None
    )


def _process_is_alive(process: Any) -> bool:
    try:
        return bool(process.is_alive())
    except Exception:
        return False


def _join_process_until(
    process: Any,
    deadline: float,
) -> None:
    remaining = max(0.0, deadline - time.monotonic())
    try:
        process.join(timeout=remaining)
    except Exception:
        pass


def terminate_process_pool(
    executor: Any,
    *,
    timeout: float = 1.5,
) -> int:
    processes = _executor_processes(executor)

    shutdown = getattr(executor, "shutdown", None)
    if callable(shutdown):
        try:
            shutdown(
                wait=False,
                cancel_futures=True,
            )
        except TypeError:
            try:
                shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass

    targets = [
        process
        for process in processes
        if _process_is_alive(process)
    ]

    for process in targets:
        try:
            process.terminate()
        except Exception:
            pass

    deadline = time.monotonic() + max(0.0, timeout)
    for process in targets:
        _join_process_until(process, deadline)

    survivors = [
        process
        for process in targets
        if _process_is_alive(process)
    ]

    for process in survivors:
        try:
            kill = getattr(process, "kill", None)
            if callable(kill):
                kill()
            else:
                process.terminate()
        except Exception:
            pass

    kill_deadline = time.monotonic() + max(0.0, timeout)
    for process in survivors:
        _join_process_until(process, kill_deadline)

    return len(targets)


def terminate_active_process_pools(
    *,
    timeout: float = 1.5,
) -> int:
    with _registry_lock:
        _ensure_process_local_registry_locked()
        executors = tuple(_active_executors.values())

    terminated = 0
    for executor in executors:
        terminated += terminate_process_pool(
            executor,
            timeout=timeout,
        )
    return terminated


__all__ = [
    "active_process_pool_count",
    "managed_process_pool",
    "terminate_active_process_pools",
    "terminate_process_pool",
]
