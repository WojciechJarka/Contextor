"""
contextor/core/domain/module.py

Repository module model.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from contextor.core.source import SourceError, parse_source

from .imports import ImportRef


@lru_cache(maxsize=1024)
def _parse(absolute_path: str, _fingerprint: tuple):
    """
    Parses a source file.

    The fingerprint (mtime, size) is part of the cache key on purpose:
    keying on the path alone returned a stale tree after the file was
    edited, which the long-lived GUI process hit routinely.
    """

    try:
        return parse_source(absolute_path)
    except SourceError:
        return None


def _get_cached_ast(absolute_path: str):
    try:
        stat = Path(absolute_path).stat()
    except OSError:
        return None

    return _parse(absolute_path, (stat.st_mtime_ns, stat.st_size))


@dataclass(frozen=True)
class Module:
    """
    Reprezentuje moduł projektu.
    """

    module_id: str

    path: str

    absolute_path: str

    # Excluded from the generated __hash__: a list is unhashable, so with
    # frozen=True the auto-generated hash raised TypeError even though the
    # class advertised itself as hashable. Equality still considers it.
    imports: list[ImportRef] = field(hash=False)

    @property
    def ast_tree(self):
        return _get_cached_ast(self.absolute_path)
