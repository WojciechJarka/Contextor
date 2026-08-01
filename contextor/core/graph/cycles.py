"""
contextor/core/cycles.py

DIRECTED GRAPH CYCLE DETECTOR

Responsibilities:

- detecting cycles in the dependency graph
- returning cycle paths

Does not evaluate:
- risk
- quality
- architectural debt


Source of truth:

    ProjectGraph.hard_edges


Output:

[
    [
        "core.a",
        "core.b",
        "core.a"
    ]
]


Each cycle is represented
deterministically.
"""

import hashlib
import json
from pathlib import Path

from contextor.core.errors import checkpoint
from contextor.core.paths import app_cache_dir

# Cache entries are keyed by a hash of the graph itself, so they live in
# the user cache directory rather than the process working directory.
# Anchoring to the CWD made every analyzed repository share one file.
_CYCLES_CACHE_SUBDIR = "cycles"

# Bounded so the directory cannot grow without limit across projects.
_CYCLES_CACHE_MAX_ENTRIES = 64


def _hash_edges(edges: dict[str, set[str]]) -> str:
    canonical = {k: sorted(v) for k, v in sorted(edges.items())}
    dumped = json.dumps(canonical)
    return hashlib.blake2b(
        dumped.encode("utf-8"),
        digest_size=16,
    ).hexdigest()


def _cycles_cache_file(edge_hash: str) -> Path:
    return app_cache_dir() / _CYCLES_CACHE_SUBDIR / f"{edge_hash}.json"


def _read_cycles_cache(edge_hash: str):
    cache_file = _cycles_cache_file(edge_hash)

    try:
        with open(cache_file, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return None

    if cache.get("hash") != edge_hash:
        return None

    return cache.get("cycles")


def _prune_cycles_cache(cache_dir: Path) -> None:
    try:
        entries = sorted(
            (p for p in cache_dir.iterdir() if p.suffix == ".json"),
            key=lambda p: p.stat().st_mtime,
        )
    except OSError:
        return

    for stale in entries[:-_CYCLES_CACHE_MAX_ENTRIES]:
        try:
            stale.unlink()
        except OSError:
            pass


def _write_cycles_cache(edge_hash: str, cycles: list[list[str]]) -> None:
    cache_file = _cycles_cache_file(edge_hash)

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        temp_file = cache_file.with_suffix(".json.tmp")

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"hash": edge_hash, "cycles": cycles}, f)

        temp_file.replace(cache_file)

        _prune_cycles_cache(cache_file.parent)

    except OSError:
        pass


# ==========================================================
# NORMALIZATION
# ==========================================================


def _canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    """
    Normalizes a cycle.

    Removes differences like:

        A,B,C,A

    and

        B,C,A,B


    into a single representation.
    """

    if not cycle:
        return tuple()

    nodes = cycle[:-1]

    rotations = []

    for index in range(len(nodes)):
        rotated = nodes[index:] + nodes[:index]

        rotations.append(tuple(rotated))

    return min(rotations)


# ==========================================================
# DFS ENGINE
# ==========================================================


def detect_cycles(edges: dict[str, set[str]], progress_callback=None) -> list[list[str]]:
    """
    Detects directed cycles (with disk Cache support for performance).
    """

    edge_hash = _hash_edges(edges)

    cached = _read_cycles_cache(edge_hash)

    if cached is not None:
        return cached

    state = {node: 0 for node in edges}

    # Current DFS path. `position` mirrors it as node -> index so the
    # cycle slice is O(1) instead of a linear scan.
    path: list[str] = []

    position: dict[str, int] = {}

    found: set[tuple[str, ...]] = set()

    def visit(start: str):
        """
        Iterative DFS.

        Deliberately not recursive: dependency chains in real
        repositories routinely exceed the interpreter recursion limit,
        which previously aborted the whole analysis with RecursionError.
        """

        state[start] = 1

        position[start] = len(path)

        path.append(start)

        # Each frame keeps its own successor iterator, so resuming a
        # frame continues exactly where it was suspended.
        frames = [
            (
                start,
                iter(sorted(edges.get(start, set()))),
            )
        ]

        while frames:
            _, targets = frames[-1]

            descended = False

            for target in targets:
                target_state = state.get(target, 0)

                # ------------------------------------------------
                # back edge = cycle
                # ------------------------------------------------

                if target_state == 1:
                    index = position.get(target)

                    if index is None:
                        continue

                    cycle = path[index:] + [target]

                    found.add(_canonical_cycle(cycle))

                elif target_state == 0:
                    state[target] = 1

                    position[target] = len(path)

                    path.append(target)

                    frames.append(
                        (
                            target,
                            iter(sorted(edges.get(target, set()))),
                        )
                    )

                    descended = True

                    break

            if descended:
                continue

            frames.pop()

            finished = path.pop()

            del position[finished]

            state[finished] = 2

    # ------------------------------------------------------
    # deterministic traversal
    # ------------------------------------------------------

    nodes = set(edges.keys())

    for targets in edges.values():
        nodes.update(targets)

    for node in sorted(nodes):
        checkpoint(progress_callback, "Detecting cycles...")

        if state.get(node, 0) == 0:
            visit(node)

    result = [list(cycle) + [cycle[0]] for cycle in sorted(found)]

    _write_cycles_cache(edge_hash, result)

    return result


# ==========================================================
# COMPATIBILITY ALIAS
# ==========================================================


find_cycles = detect_cycles
