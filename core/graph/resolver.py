# -*- coding: utf-8 -*-

"""
repo_guardian/core/resolver.py

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


from typing import (
    Iterable,
    Optional,
)


from repo_guardian.core.domain.imports import (
    ImportRef,
)

from repo_guardian.core.domain.resolution import (
    ResolutionResult,
)


PACKAGE_ROOT = "repo_guardian"


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

        self.full_name: Optional[str] = None



def build_trie(
    modules: Iterable[str]
) -> TrieNode:

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
) -> Optional[str]:

    if not name:

        return None


    node = trie


    for part in name.split("."):

        node = node.children.get(
            part
        )


        if node is None:

            return None



    if node.is_module:

        return node.full_name


    return None



def _longest_module_prefix(
    name: str,
    trie: TrieNode,
) -> Optional[str]:

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


    return ".".join(
        parts[:-remove]
    )



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

        return (
            f"{base}.{imported_module}"
            if base
            else imported_module
        )


    return base



# ==========================================================
# SYMBOL FALLBACK
# ==========================================================


def _resolve_symbol_fallback(
    candidate: str,
    symbols: list[str],
    trie: TrieNode,
) -> Optional[tuple[str,str]]:


    for symbol in sorted(symbols):

        target = (
            f"{candidate}.{symbol}"
            if candidate
            else symbol
        )


        module = _trie_lookup(
            target,
            trie
        )


        if module:

            return (
                module,
                symbol
            )


    return None



# ==========================================================
# PUBLIC API
# ==========================================================


def resolve_internal(
    imp: ImportRef,
    trie: TrieNode,
    current_module_id: str,
) -> ResolutionResult:


    candidate = _normalize_relative(
        current_module_id,
        imp.module or "",
        imp.level,
    )

    if candidate.startswith(f"{PACKAGE_ROOT}."):
        candidate = candidate[len(PACKAGE_ROOT) + 1:]



    # ------------------------------------------------------
    # exact module
    # ------------------------------------------------------

    module = _trie_lookup(
        candidate,
        trie
    )

    if module:

        return ResolutionResult(
            target_module=module,
            kind="MODULE",
        )



    # ------------------------------------------------------
    # prefix fallback
    # ------------------------------------------------------

    prefix = _longest_module_prefix(
        candidate,
        trie
    )


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
