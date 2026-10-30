"""Conditional PEP 420 path-based resolution for supplied inventories.

This is not filesystem provenance, authenticated runtime search state,
or authorization to suppress a structural cycle warning.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchPortion:
    root_id: str
    files: frozenset[str]


@dataclass(frozen=True)
class PathCandidate:
    name: str
    kind: str
    source: str | None
    portions: tuple[str, ...]


@dataclass(frozen=True)
class NamespacePathResult:
    status: str
    requested_name: str
    kind: str | None
    source: str | None
    portions: tuple[str, ...]
    steps: tuple[PathCandidate, ...]
    reason: str | None
    authority: str = (
        "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
    )


def resolve_namespace_path(
    roots: tuple[SearchPortion, ...],
    requested_name: str,
    *,
    standard_finder_assumed: bool = False,
) -> NamespacePathResult:
    """Model .py, regular-package and namespace search precedence.

    The supplied file inventory and finder policy are assumptions.
    Runtime sys.modules, custom finders, alternative loaders,
    import-time path mutation and external portions are not certified.
    """
    steps: list[PathCandidate] = []

    def reject(reason: str) -> NamespacePathResult:
        return NamespacePathResult(
            "INDETERMINATE",
            requested_name,
            None,
            None,
            (),
            tuple(steps),
            reason,
        )

    if not standard_finder_assumed:
        return reject("IMPORT_FINDER_ENVIRONMENT_NOT_PROVED")

    if (
        type(roots) is not tuple
        or not roots
        or type(requested_name) is not str
        or not requested_name
        or any(
            not part.isidentifier()
            for part in requested_name.split(".")
        )
    ):
        return reject("INVALID_SEARCH_INPUT")

    seen: set[str] = set()
    directory_sets: dict[str, frozenset[str]] = {}

    for root in roots:
        if (
            type(root) is not SearchPortion
            or type(root.root_id) is not str
            or not root.root_id
            or root.root_id in seen
            or type(root.files) is not frozenset
            or any(
                type(path) is not str
                or not path
                or path.startswith("/")
                or "\\" in path
                or any(
                    part in ("", ".", "..")
                    for part in path.split("/")
                )
                or path.endswith("/")
                for path in root.files
            )
        ):
            return reject("INVALID_SEARCH_INVENTORY")

        seen.add(root.root_id)
        dirs: set[str] = set()

        for filename in root.files:
            parts = filename.split("/")
            for index in range(1, len(parts)):
                dirs.add("/".join(parts[:index]))

        directory_sets[root.root_id] = frozenset(dirs)

    active: list[tuple[SearchPortion, str]] = [
        (root, "") for root in roots
    ]
    fragments = requested_name.split(".")

    for depth, fragment in enumerate(fragments):
        name = ".".join(fragments[:depth + 1])
        namespace_parts: list[tuple[SearchPortion, str]] = []
        selected: tuple[str, str, SearchPortion, str] | None = None

        for root, parent in active:
            candidate = (
                (parent + "/" if parent else "") + fragment
            )

            # Tagged extension modules such as module.cp310-win_amd64.pyd
            # and module.cpython-310-x86_64-linux-gnu.so are not
            # recognized by testing only the bare ".pyd"/".so" suffix.
            # Reject conservatively; this is not a loader selection proof.
            alternative_prefixes = (
                candidate + ".",
                candidate + "/__init__.",
            )
            if any(
                filename.startswith(alternative_prefixes)
                and filename.endswith((".pyc", ".pyd", ".so"))
                for filename in root.files
            ):
                return reject("ALTERNATIVE_LOADER_CANDIDATE")

            if candidate + "/__init__.py" in root.files:
                selected = (
                    "REGULAR_PACKAGE",
                    candidate + "/__init__.py",
                    root,
                    candidate,
                )
                break

            if candidate + ".py" in root.files:
                selected = (
                    "MODULE_FILE",
                    candidate + ".py",
                    root,
                    candidate,
                )
                break

            if candidate in directory_sets[root.root_id]:
                namespace_parts.append((root, candidate))

        if selected is not None:
            kind, filename, root, directory = selected
            source = root.root_id + ":" + filename
            portions: tuple[str, ...] = ()

            active = (
                [(root, directory)]
                if kind == "REGULAR_PACKAGE"
                else []
            )

        elif namespace_parts:
            kind = "NAMESPACE_PACKAGE"
            source = None
            portions = tuple(
                root.root_id + ":" + directory
                for root, directory in namespace_parts
            )
            active = namespace_parts

        else:
            return reject("TARGET_NOT_IN_SUPPLIED_INVENTORY")

        steps.append(
            PathCandidate(name, kind, source, portions)
        )

        if (
            depth < len(fragments) - 1
            and kind == "MODULE_FILE"
        ):
            return reject("MODULE_IS_NOT_A_PACKAGE")

    last = steps[-1]

    return NamespacePathResult(
        "CONDITIONAL",
        requested_name,
        last.kind,
        last.source,
        last.portions,
        tuple(steps),
        None,
    )
