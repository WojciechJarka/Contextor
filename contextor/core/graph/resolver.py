"""
contextor/core/resolver.py

IMPORT RESOLUTION ENGINE

Responsibilities:

- mapping ImportRef → project module
- absolute imports
- relative imports
- fallback symbol resolution

Classification:

MODULE:
    existing module

FALLBACK:
    module does not exist directly,
    but possible target found

UNKNOWN:
    no match


Does not analyze:
- AST
- quality
- risk
- architecture
"""

from collections.abc import Iterable

from contextor.core.domain.imports import (
    ImportRef,
)
from contextor.core.domain.resolution import (
    ResolutionResult,
)

# ==========================================================
# TRIE
# ==========================================================


class TrieNode:
    __slots__ = (
        "children",
        "is_module",
        "full_name",
    )

    def __init__(self):

        self.children: dict[str, TrieNode] = {}

        self.is_module = False

        self.full_name: str | None = None


def build_trie(modules: Iterable[str]) -> TrieNode:

    root = TrieNode()

    for module in sorted(modules):
        node = root

        for part in module.split("."):
            if part not in node.children:
                node.children[part] = TrieNode()

            node = node.children[part]

        node.is_module = True

        node.full_name = module

    return root


# ==========================================================
# LOOKUP
# ==========================================================


def _trie_lookup(
    name: str,
    trie: TrieNode,
) -> str | None:

    if not name:
        return None

    node = trie

    for part in name.split("."):
        node = node.children.get(part)

        if node is None:
            return None

    if node.is_module:
        return node.full_name

    return None


def _longest_module_prefix(
    name: str,
    trie: TrieNode,
) -> str | None:

    if not name:
        return None

    node = trie

    best = None

    parts = []

    for part in name.split("."):
        if part not in node.children:
            break

        node = node.children[part]

        parts.append(part)

        if node.is_module:
            best = ".".join(parts)

    return best


# ==========================================================
# PACKAGE ROOT DETECTION
# ==========================================================


def detect_package_root(modules, trie: TrieNode) -> str | None:
    """
    Infers the import prefix that analyzed modules use to address
    themselves.

    A repository whose files are indexed as 'core.graph' but which
    imports them as '<package>.core.graph' needs that '<package>.'
    prefix stripped before resolution.

    The prefix cannot be read off the module ids - it appears only in
    the import statements. So: count leading components that do not
    resolve on their own but do resolve once removed, and take the
    clear winner.
    """

    scores: dict[str, int] = {}

    for module in modules.values():
        for imp in getattr(module, "imports", None) or []:
            name = getattr(imp, "module", None)

            if not name or "." not in name:
                continue

            head, rest = name.split(".", 1)

            # Already resolvable as-is: nothing to strip.
            if _longest_module_prefix(name, trie):
                continue

            if _longest_module_prefix(rest, trie):
                scores[head] = scores.get(head, 0) + 1

    if not scores:
        return None

    return max(
        sorted(scores),
        key=lambda head: scores[head],
    )


# ==========================================================
# RELATIVE IMPORTS
# ==========================================================


def _resolve_relative_base(
    current_module_id: str,
    level: int,
) -> str:

    parts = current_module_id.split(".")

    # level=1 means the directory of the current module

    remove = level

    if remove >= len(parts):
        return ""

    return ".".join(parts[:-remove])


def _normalize_relative(
    current_module_id: str,
    imported_module: str,
    level: int,
) -> str:

    if level <= 0:
        return imported_module

    base = _resolve_relative_base(
        current_module_id,
        level,
    )

    if imported_module:
        return f"{base}.{imported_module}" if base else imported_module

    return base


# ==========================================================
# SYMBOL FALLBACK
# ==========================================================


def _resolve_symbol_fallback(
    candidate: str,
    symbols: list[str],
    trie: TrieNode,
) -> tuple[str, str] | None:

    for symbol in sorted(symbols):
        target = f"{candidate}.{symbol}" if candidate else symbol

        module = _trie_lookup(target, trie)

        if module:
            return (module, symbol)

    return None


# ==========================================================
# PUBLIC API
# ==========================================================


def resolve_internal(
    imp: ImportRef,
    trie: TrieNode,
    current_module_id: str,
    package_root: str | None,
) -> ResolutionResult:

    candidate = _normalize_relative(
        current_module_id,
        imp.module or "",
        imp.level,
    )

    if package_root and candidate.startswith(f"{package_root}."):
        candidate = candidate[len(package_root) + 1 :]

    # ------------------------------------------------------
    # exact module
    # ------------------------------------------------------

    module = _trie_lookup(candidate, trie)

    if module:
        return ResolutionResult(
            target_module=module,
            kind="MODULE",
        )

    # ------------------------------------------------------
    # prefix fallback
    # ------------------------------------------------------

    prefix = _longest_module_prefix(candidate, trie)

    if prefix:
        return ResolutionResult(
            target_module=prefix,
            kind="FALLBACK",
        )

    # ------------------------------------------------------
    # symbol fallback
    # ------------------------------------------------------

    symbol_result = _resolve_symbol_fallback(
        candidate,
        imp.names,
        trie,
    )

    if symbol_result:
        module, symbol = symbol_result

        return ResolutionResult(
            target_module=module,
            kind="FALLBACK",
            used_symbol=symbol,
        )

    return ResolutionResult(
        target_module=None,
        kind="UNKNOWN",
    )
