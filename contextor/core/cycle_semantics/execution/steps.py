from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Step:
    op: str
    target: str | None = None
    symbol: str | None = None
    binding: str | None = None
    explicit_alias: bool = False
    function_body: tuple[_Step, ...] = ()
    function_local: bool = False
    class_local: bool = False
    source_line: int | None = None
    source_column: int | None = None
    annotation_builtin_names: tuple[str, ...] = ()
    definition_id: str | None = None
    defines_init_subclass: bool = False
    base_names: tuple[str, ...] = ()
    explicit_metaclass_name: str | None = None
    passive_metaclass_body: bool = False
