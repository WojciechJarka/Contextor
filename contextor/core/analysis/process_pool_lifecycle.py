from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from multiprocessing.util import Finalize
from pathlib import Path
import sys
from typing import Any, Callable, Iterator


_registry_lock = threading.RLock()
_registry_pid = os.getpid()
_active_executors: dict[int, Any] = {}

_reusable_executors: dict[str, Any] = {}
_reusable_registry_values: dict[str, str | None] = {}
_reusable_generations: dict[str, int] = {}
_reusable_use_locks: dict[str, threading.RLock] = {}
_reusable_generation_counter = 0


def _ensure_process_local_registry_locked() -> None:
    global _registry_pid
    global _reusable_generation_counter

    current_pid = os.getpid()
    if current_pid == _registry_pid:
        return

    _active_executors.clear()
    _reusable_executors.clear()
    _reusable_registry_values.clear()
    _reusable_generations.clear()
    _reusable_use_locks.clear()
    _reusable_generation_counter = 0
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


def _reusable_pool_use_lock(
    pool_key: str,
) -> threading.RLock:
    if not pool_key:
        raise ValueError(
            "Reusable process-pool key must be non-empty."
        )

    with _registry_lock:
        _ensure_process_local_registry_locked()

        lock = _reusable_use_locks.get(
            pool_key
        )

        if lock is None:
            lock = threading.RLock()
            _reusable_use_locks[
                pool_key
            ] = lock

        return lock


def _drop_reusable_executor(
    pool_key: str,
    executor: Any,
) -> None:
    with _registry_lock:
        _ensure_process_local_registry_locked()

        if (
            _reusable_executors.get(
                pool_key
            )
            is not executor
        ):
            return

        _reusable_executors.pop(
            pool_key,
            None,
        )
        _reusable_registry_values.pop(
            pool_key,
            None,
        )
        _reusable_generations.pop(
            pool_key,
            None,
        )
        _active_executors.pop(
            id(executor),
            None,
        )


def _create_reusable_process_pool(
    pool_key: str,
    registry_value: str | None,
) -> tuple[Any, int]:
    global _reusable_generation_counter

    factory_kwargs: dict[str, Any] = {}

    if registry_value:
        factory_kwargs[
            "initializer"
        ] = _initialize_mcp_managed_worker

        factory_kwargs[
            "initargs"
        ] = (
            os.getpid(),
            None,
            (),
        )

    executor = ProcessPoolExecutor(
        **factory_kwargs
    )

    with _registry_lock:
        _ensure_process_local_registry_locked()

        _reusable_generation_counter += 1
        generation = (
            _reusable_generation_counter
        )

        _active_executors[
            id(executor)
        ] = executor

        _reusable_executors[
            pool_key
        ] = executor

        _reusable_registry_values[
            pool_key
        ] = registry_value

        _reusable_generations[
            pool_key
        ] = generation

    return executor, generation


@contextmanager
def managed_reusable_process_pool(
    pool_key: str,
) -> Iterator[tuple[Any, bool, int]]:
    """
    Lease one process-local reusable ProcessPoolExecutor.

    Normal context exit preserves the executor and its workers.

    Any exception escaping the lease invalidates and terminates that
    generation so the next lease must create a fresh executor.

    A change of CONTEXTOR_MCP_PROCESS_REGISTRY also rotates the
    generation before reuse, preventing workers registered under one
    registry scope from silently surviving into another scope.
    """

    use_lock = _reusable_pool_use_lock(
        pool_key
    )

    with use_lock:
        registry_value = os.environ.get(
            "CONTEXTOR_MCP_PROCESS_REGISTRY"
        )

        with _registry_lock:
            _ensure_process_local_registry_locked()

            executor = (
                _reusable_executors.get(
                    pool_key
                )
            )

            previous_registry_value = (
                _reusable_registry_values.get(
                    pool_key
                )
            )

            generation = (
                _reusable_generations.get(
                    pool_key
                )
            )

        if (
            executor is not None
            and previous_registry_value
            != registry_value
        ):
            terminate_process_pool(
                executor
            )

            _drop_reusable_executor(
                pool_key,
                executor,
            )

            executor = None
            generation = None

        reused = executor is not None

        if executor is None:
            executor, generation = (
                _create_reusable_process_pool(
                    pool_key,
                    registry_value,
                )
            )

        assert generation is not None

        try:
            yield (
                executor,
                reused,
                generation,
            )
        except BaseException:
            terminate_process_pool(
                executor
            )

            _drop_reusable_executor(
                pool_key,
                executor,
            )

            raise


def _initialize_mcp_managed_worker(
    owner_pid: int,
    original_initializer: Callable[..., Any] | None,
    original_initargs: tuple[Any, ...],
) -> None:
    registry_value = os.environ.get(
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    )
    if registry_value:
        from contextor.mcp_process_registry import (
            register_process,
            remove_record,
        )
        record_path = register_process(
            Path(registry_value),
            pid=os.getpid(),
            parent_pid=owner_pid,
            kind="process-pool-worker",
            executable=sys.executable,
        )
        Finalize(
            None,
            remove_record,
            args=(record_path,),
            exitpriority=0,
        )
    if original_initializer is not None:
        original_initializer(*original_initargs)


@contextmanager
def managed_process_pool(
    executor_factory: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Iterator[Any]:
    factory_kwargs = dict(kwargs)
    registry_value = os.environ.get(
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    )
    if (
        executor_factory is ProcessPoolExecutor
        and registry_value
    ):
        original_initializer = factory_kwargs.pop(
            "initializer",
            None,
        )
        original_initargs = tuple(
            factory_kwargs.pop("initargs", ()) or ()
        )
        factory_kwargs["initializer"] = (
            _initialize_mcp_managed_worker
        )
        factory_kwargs["initargs"] = (
            os.getpid(),
            original_initializer,
            original_initargs,
        )
    executor = executor_factory(
        *args,
        **factory_kwargs,
    )
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
        executors = tuple(
            _active_executors.values()
        )

    target_ids = {
        id(executor)
        for executor in executors
    }

    terminated = 0

    for executor in executors:
        terminated += terminate_process_pool(
            executor,
            timeout=timeout,
        )

    with _registry_lock:
        _ensure_process_local_registry_locked()

        for executor_id in target_ids:
            _active_executors.pop(
                executor_id,
                None,
            )

        for (
            pool_key,
            executor,
        ) in tuple(
            _reusable_executors.items()
        ):
            if id(executor) not in target_ids:
                continue

            _reusable_executors.pop(
                pool_key,
                None,
            )
            _reusable_registry_values.pop(
                pool_key,
                None,
            )
            _reusable_generations.pop(
                pool_key,
                None,
            )

    return terminated


__all__ = [
    "active_process_pool_count",
    "managed_process_pool",
    "managed_reusable_process_pool",
    "terminate_active_process_pools",
    "terminate_process_pool",
]
