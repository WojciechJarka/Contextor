"""Conservative, source-independent inventory of Python import package layout.

Never executes imports, mutates the canonical graph or certifies runtime targets.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from contextor.core.cycle_semantics.provenance import ImportOccurrence


@dataclass(frozen=True)
class PackageLayoutNode:
    name: str
    kind: str
    indexed_module_ids: tuple[str, ...]


@dataclass(frozen=True)
class PackageLayout:
    nodes: tuple[PackageLayoutNode, ...]
    authority: str = "REPOSITORY_LAYOUT_CANDIDATES_ONLY"


@dataclass(frozen=True)
class ImportNamePlan:
    requested_name: str
    local_binding: str
    load_chain: tuple[PackageLayoutNode, ...]
    member_name: str | None
    possible_child_module: str | None
    resolution: str


@dataclass(frozen=True)
class ImportSitePlan:
    module_id: str
    occurrence_ordinal: int
    line: int
    status: str
    entries: tuple[ImportNamePlan, ...]
    authority: str = "STATIC_LAYOUT_NOT_RUNTIME_PROOF"


def _dotted(name: str) -> bool:
    return bool(name) and all(
        part.isidentifier()
        for part in name.split(".")
    )


def build_package_layout(
    indexed_modules: Iterable[str],
) -> PackageLayout:
    """Classify indexed modules, regular packages and namespace candidates.

    A namespace is only a candidate: external portions and runtime import hooks
    are not modeled. File/package conflicts are explicitly marked ambiguous.
    """
    if isinstance(indexed_modules, (str, bytes)):
        raise TypeError(
            "indexed_modules must be an iterable of module IDs"
        )

    try:
        supplied = list(indexed_modules)
    except TypeError:
        raise TypeError(
            "indexed_modules must be iterable"
        ) from None

    if any(
        not isinstance(item, str) or not _dotted(item)
        for item in supplied
    ):
        raise ValueError("invalid indexed module ID")

    if len(supplied) != len(set(supplied)):
        raise ValueError("duplicate indexed module ID")

    ids = set(supplied)
    origins: dict[str, set[str]] = {}

    for index_id in ids:
        if index_id.endswith(".__init__"):
            name = index_id.removesuffix(".__init__")
            origins.setdefault(name, set()).add(index_id)
        else:
            origins.setdefault(index_id, set()).add(index_id)

    children: set[str] = set()

    for name in origins:
        parts = name.split(".")
        for length in range(1, len(parts)):
            children.add(".".join(parts[:length]))

    nodes = []

    for name in sorted(set(origins) | children):
        choices = tuple(sorted(origins.get(name, ())))
        is_init = f"{name}.__init__" in choices
        is_file = name in choices
        has_children = name in children

        if (
            (is_init and is_file)
            or (is_file and has_children and not is_init)
        ):
            kind = "AMBIGUOUS_LAYOUT"
        elif is_init:
            kind = "REGULAR_PACKAGE"
        elif is_file:
            kind = "MODULE_FILE"
        else:
            kind = "NAMESPACE_CANDIDATE"

        nodes.append(
            PackageLayoutNode(name, kind, choices)
        )

    return PackageLayout(tuple(nodes))


def _module_context(
    module_id: str,
    names: set[str],
) -> tuple[str, ...] | None:
    if module_id not in names:
        return None

    return tuple(module_id.split(".")[:-1])


def _chain(
    name: str,
    lookup: dict[str, PackageLayoutNode],
) -> tuple[PackageLayoutNode, ...]:
    parts = name.split(".")
    result = []

    for length in range(1, len(parts) + 1):
        path = ".".join(parts[:length])
        node = lookup.get(path)

        result.append(
            node
            if node is not None
            else PackageLayoutNode(
                path, "UNKNOWN_MODULE", ()
            )
        )

    return tuple(result)


def plan_package_import(
    module_id: str,
    occurrence: ImportOccurrence,
    layout: PackageLayout,
) -> ImportSitePlan:
    """Plan lexical package-loading candidates without executing imports.

    A possible submodule never proves a from-import member's runtime target.
    """
    if not isinstance(layout, PackageLayout):
        raise TypeError("layout must be PackageLayout")

    if not isinstance(occurrence, ImportOccurrence):
        raise TypeError(
            "occurrence must be ImportOccurrence"
        )

    if not isinstance(module_id, str) or not _dotted(module_id):
        raise ValueError("invalid importer ID")

    lookup = {
        node.name: node
        for node in layout.nodes
    }

    indexed = {
        origin
        for node in layout.nodes
        for origin in node.indexed_module_ids
    }

    context = _module_context(module_id, indexed)

    if context is None:
        return ImportSitePlan(
            module_id,
            occurrence.ordinal,
            occurrence.line,
            "IMPORTER_NOT_INDEXED",
            (),
        )

    if occurrence.form not in {"IMPORT", "IMPORT_FROM"}:
        return ImportSitePlan(
            module_id,
            occurrence.ordinal,
            occurrence.line,
            "UNSUPPORTED_FORM",
            (),
        )

    if occurrence.form == "IMPORT_FROM":
        if (
            not isinstance(occurrence.level, int)
            or occurrence.level < 0
        ):
            return ImportSitePlan(
                module_id,
                occurrence.ordinal,
                occurrence.line,
                "INVALID_LEVEL",
                (),
            )

        if occurrence.level:
            climb = occurrence.level - 1

            if not context or climb >= len(context):
                return ImportSitePlan(
                    module_id,
                    occurrence.ordinal,
                    occurrence.line,
                    "RELATIVE_BEYOND_TOP_LEVEL",
                    (),
                )

            base = list(
                context[:len(context) - climb]
            )

            if occurrence.module is not None:
                if not _dotted(occurrence.module):
                    return ImportSitePlan(
                        module_id,
                        occurrence.ordinal,
                        occurrence.line,
                        "INVALID_MODULE_NAME",
                        (),
                    )
                base.extend(
                    occurrence.module.split(".")
                )

            requested_base = ".".join(base)

        else:
            requested_base = occurrence.module or ""

            if not _dotted(requested_base):
                return ImportSitePlan(
                    module_id,
                    occurrence.ordinal,
                    occurrence.line,
                    "INVALID_MODULE_NAME",
                    (),
                )

    else:
        if occurrence.level != 0:
            return ImportSitePlan(
                module_id,
                occurrence.ordinal,
                occurrence.line,
                "INVALID_LEVEL",
                (),
            )

        requested_base = ""

    output = []

    for requested, alias in occurrence.aliases:
        if (
            not isinstance(requested, str)
            or (
                requested != "*"
                and not _dotted(requested)
            )
        ):
            return ImportSitePlan(
                module_id,
                occurrence.ordinal,
                occurrence.line,
                "INVALID_MEMBER_NAME",
                (),
            )

        if alias is not None and (
            not isinstance(alias, str)
            or not alias.isidentifier()
        ):
            return ImportSitePlan(
                module_id,
                occurrence.ordinal,
                occurrence.line,
                "INVALID_BINDING",
                (),
            )

        if occurrence.form == "IMPORT":
            if requested == "*":
                return ImportSitePlan(
                    module_id,
                    occurrence.ordinal,
                    occurrence.line,
                    "INVALID_MEMBER_NAME",
                    (),
                )

            chain = _chain(requested, lookup)
            local = alias or requested.split(".")[0]

            outcome = (
                "LAYOUT_CHAIN_CANDIDATE"
                if all(
                    node.kind not in {
                        "UNKNOWN_MODULE",
                        "AMBIGUOUS_LAYOUT",
                    }
                    for node in chain
                )
                else "LAYOUT_UNRESOLVED"
            )

            output.append(
                ImportNamePlan(
                    requested,
                    local,
                    chain,
                    None,
                    None,
                    outcome,
                )
            )

        else:
            chain = _chain(requested_base, lookup)
            local = alias or requested

            possible_child = (
                f"{requested_base}.{requested}"
                if (
                    requested != "*"
                    and chain[-1].kind in {
                        "REGULAR_PACKAGE",
                        "NAMESPACE_CANDIDATE",
                        "AMBIGUOUS_LAYOUT",
                    }
                    and f"{requested_base}.{requested}" in lookup
                )
                else None
            )

            outcome = (
                "STAR_EXPORTS_UNRESOLVED"
                if requested == "*"
                else "MEMBER_OR_SUBMODULE_UNRESOLVED"
                if possible_child is not None
                else "MEMBER_BINDING_UNRESOLVED"
            )

            if any(
                node.kind in {
                    "UNKNOWN_MODULE",
                    "AMBIGUOUS_LAYOUT",
                }
                for node in chain
            ):
                outcome = "LAYOUT_UNRESOLVED"

            output.append(
                ImportNamePlan(
                    requested_base,
                    local,
                    chain,
                    requested,
                    possible_child,
                    outcome,
                )
            )

    return ImportSitePlan(
        module_id,
        occurrence.ordinal,
        occurrence.line,
        "PLANNED",
        tuple(output),
    )
