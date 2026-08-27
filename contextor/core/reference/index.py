"""
contextor/core/reference/index.py

Run-scoped repository symbol reference index.

Replaces definer-driven O(N_definers * N_candidates) repeated AST scans with
a single-pass O(N_consumers) discovery phase that precomputes all call,
callback, event, inheritance, qualified attribute, and import reference facts
for the current analysis run.

Non-Negotiable Invariants:
- Rebuilt from current-run modules / ASTs on each full analysis run (HARD RESET compliant).
- Never uses or trusts previous canonical / LIVE analytical facts as input.
- Preserves 1:1 semantic parity with legacy reference resolution.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .resolution import (
    IGNORED_AMBIGUOUS_METHODS,
    _absolute_import_module,
    _attribute_name,
    _classify_match,
    _resolve_alias,
    _resolve_reexport,
)
from .shared import (
    _build_reexport_map,
    _empty_reference,
    _normalize_references,
)
from .visitor import _is_event_binding_call


@dataclass(slots=True)
class CallEvent:
    called_name: Optional[str]
    resolved: Optional[str]
    candidate: Optional[str]
    lineno: Optional[int]
    context: Optional[str]


class SinglePassConsumerVisitor(ast.NodeVisitor):
    """
    Extracts all symbol reference events from a single consumer module AST in one pass.
    """

    def __init__(self, current_module: str, reexports: dict[str, str]):
        self.current_module = current_module
        self.reexports = reexports

        self.aliases: dict[str, str] = {}
        self.instances: dict[str, str] = {}
        self.context_stack: list[str] = []
        self.class_stack: list[str] = []
        self._call_funcs: set[ast.AST] = set()

        # Extracted reference event streams
        self.call_events: list[CallEvent] = []
        self.callback_calls: list[tuple[Optional[str], Optional[str], Optional[int], Optional[str]]] = []
        self.event_bindings: list[tuple[Optional[str], Optional[str], Optional[int], Optional[str]]] = []
        self.qualified_refs: list[tuple[Optional[str], Optional[str], Optional[int], Optional[str]]] = []
        self.inheritance: list[tuple[str, Optional[str], Optional[str], Optional[int]]] = []

    def _resolve_name(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        return _resolve_reexport(
            _resolve_alias(name, self.aliases),
            self.reexports,
        )

    def _current_context(self) -> Optional[str]:
        return self.context_stack[-1] if self.context_stack else None

    def _instance_method_candidate(self, resolved: Optional[str]) -> Optional[str]:
        if not resolved:
            return None
        parts = resolved.split(".")
        if len(parts) != 2:
            return None
        instance_name, method = parts
        constructor = self.instances.get(instance_name)
        if not constructor:
            return None
        return f"{constructor}.{method}"

    # --------------------------------------------------
    # IMPORTS & ALIASES
    # --------------------------------------------------

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        source_module = _absolute_import_module(
            self.current_module, node.module, node.level or 0
        )
        for item in node.names:
            local_name = item.asname or item.name
            imported_name = (
                f"{source_module}.{item.name}"
                if source_module
                else item.name
            )
            self.aliases[local_name] = imported_name
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            local_name = item.asname or item.name.split(".")[-1]
            self.aliases[local_name] = item.name
        self.generic_visit(node)

    # --------------------------------------------------
    # FUNCTION CONTEXT
    # --------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        arguments = (
            *getattr(node.args, "posonlyargs", ()),
            *node.args.args,
            *node.args.kwonlyargs,
        )
        for argument in arguments:
            if argument.annotation is not None:
                self.visit(argument.annotation)
        for argument in (node.args.vararg, node.args.kwarg):
            if argument is not None and argument.annotation is not None:
                self.visit(argument.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        for type_parameter in getattr(node, "type_params", ()):
            self.visit(type_parameter)

        self.context_stack.append(node.name)
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self.context_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    # --------------------------------------------------
    # INSTANCE TRACKING
    # --------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            constructor = _attribute_name(node.value.func)
            constructor = self._resolve_name(constructor)
            if constructor:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.instances[target.id] = constructor
        self.generic_visit(node)

    # --------------------------------------------------
    # QUALIFIED ATTRIBUTES (NON-CALL)
    # --------------------------------------------------

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node not in self._call_funcs:
            name = _attribute_name(node)
            if name and "." in name:
                resolved = self._resolve_name(name)
                self.qualified_refs.append((
                    name,
                    resolved,
                    getattr(node, "lineno", None),
                    self._current_context(),
                ))
        self.generic_visit(node)

    # --------------------------------------------------
    # CALLS & CALLBACKS
    # --------------------------------------------------

    def _mark_call_func_tree(self, func: ast.AST) -> None:
        for child in ast.walk(func):
            if isinstance(child, ast.Attribute):
                self._call_funcs.add(child)

    def visit_Call(self, node: ast.Call) -> None:
        self._mark_call_func_tree(node.func)
        called_name = _attribute_name(node.func)
        is_event_binding = _is_event_binding_call(called_name)

        if is_event_binding:
            self._detect_positional_callbacks(node)
        else:
            self._detect_callback_arguments(node)
            self._detect_positional_callbacks(node)

        # Dynamic getattr(obj, "symbol_name")
        if (
            called_name == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            dynamic_name = node.args[1].value
            resolved_dyn = self._resolve_name(dynamic_name)
            self.call_events.append(CallEvent(
                called_name=dynamic_name,
                resolved=resolved_dyn,
                candidate=None,
                lineno=getattr(node, "lineno", None),
                context=self._current_context(),
            ))

        # Positional higher-order arguments
        if not is_event_binding:
            for arg in node.args:
                arg_name = _attribute_name(arg)
                if not arg_name:
                    continue
                resolved_arg = self._resolve_name(arg_name)
                self.callback_calls.append((
                    arg_name,
                    resolved_arg,
                    getattr(node, "lineno", None),
                    self._current_context(),
                ))

        # Direct & instance method calls
        resolved = self._resolve_name(called_name)
        lineno = getattr(node, "lineno", None)
        ctx = self._current_context()
        candidate = self._instance_method_candidate(resolved)

        self.call_events.append(CallEvent(
            called_name=called_name,
            resolved=resolved,
            candidate=candidate,
            lineno=lineno,
            context=ctx,
        ))

        self.generic_visit(node)

    def _detect_positional_callbacks(self, node: ast.Call) -> None:
        func_name = _attribute_name(node.func)
        if not func_name:
            return
        method = func_name.split(".")[-1]
        lineno = getattr(node, "lineno", None)
        ctx = self._current_context()

        if method in {"bind", "subscribe"}:
            if len(node.args) >= 2:
                name = _attribute_name(node.args[1])
                resolved = self._resolve_name(name)
                self.event_bindings.append((name, resolved, lineno, ctx))
        elif method in {"on"}:
            if len(node.args) >= 1:
                name = _attribute_name(node.args[0])
                resolved = self._resolve_name(name)
                self.event_bindings.append((name, resolved, lineno, ctx))

    def _detect_callback_arguments(self, node: ast.Call) -> None:
        callback_keys = {
            "command", "callback", "handler", "func",
            "on_click", "on_change", "on_submit",
        }
        lineno = getattr(node, "lineno", None)
        ctx = self._current_context()

        for keyword in node.keywords:
            if keyword.arg not in callback_keys:
                continue
            name = _attribute_name(keyword.value)
            resolved = self._resolve_name(name)
            self.callback_calls.append((name, resolved, lineno, ctx))

    # --------------------------------------------------
    # INHERITANCE
    # --------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        for base in node.bases:
            base_name = _attribute_name(base)
            resolved = self._resolve_name(base_name)
            self.inheritance.append((
                node.name,
                base_name,
                resolved,
                getattr(node, "lineno", None),
            ))
        self.generic_visit(node)
        self.class_stack.pop()


class RepositoryReferenceIndex:
    """
    Run-scoped repository-wide reference index built in a single AST pass.
    """

    __test__ = False

    def __init__(
        self,
        modules: dict,
        root_path: str,
        reexports: dict[str, str],
        direct_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
        instance_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
        callbacks_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
        events_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
        inheritance_by_target: dict[str, list[tuple[str, str, Optional[int]]]],
        qualified_refs_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]],
        imports_by_target: dict[str, list[str]],
        star_imports_by_source: dict[str, list[str]],
        ambiguous_calls_by_leaf: dict[str, list[tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], Optional[str], dict[str, str]]]],
        ambiguous_callbacks_by_leaf: dict[str, list[tuple[str, Optional[str], Optional[str], Optional[int], Optional[str], dict[str, str]]]],
        ambiguous_events_by_leaf: dict[str, list[tuple[str, Optional[str], Optional[str], Optional[int], Optional[str], dict[str, str]]]],
        ambiguous_inheritance_by_leaf: dict[str, list[tuple[str, str, Optional[str], Optional[str], Optional[int], dict[str, str]]]],
        ambiguous_qualified_by_leaf: dict[str, list[tuple[str, Optional[str], Optional[str], Optional[int], Optional[str], dict[str, str]]]],
    ):
        self.modules = modules
        self.root_path = root_path
        self.reexports = reexports
        self.direct_calls_by_target = direct_calls_by_target
        self.instance_calls_by_target = instance_calls_by_target
        self.callbacks_by_target = callbacks_by_target
        self.events_by_target = events_by_target
        self.inheritance_by_target = inheritance_by_target
        self.qualified_refs_by_target = qualified_refs_by_target
        self.imports_by_target = imports_by_target
        self.star_imports_by_source = star_imports_by_source
        self.ambiguous_calls_by_leaf = ambiguous_calls_by_leaf
        self.ambiguous_callbacks_by_leaf = ambiguous_callbacks_by_leaf
        self.ambiguous_events_by_leaf = ambiguous_events_by_leaf
        self.ambiguous_inheritance_by_leaf = ambiguous_inheritance_by_leaf
        self.ambiguous_qualified_by_leaf = ambiguous_qualified_by_leaf

    @classmethod
    def build(cls, modules: dict, root_path: str) -> "RepositoryReferenceIndex":
        reexports = _build_reexport_map(modules)

        direct_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
        instance_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
        callbacks_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
        events_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
        inheritance_by_target: dict[str, list[tuple[str, str, Optional[int]]]] = defaultdict(list)
        qualified_refs_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
        imports_by_target: dict[str, list[str]] = defaultdict(list)
        star_imports_by_source: dict[str, list[str]] = defaultdict(list)

        ambiguous_calls_by_leaf: dict[str, list] = defaultdict(list)
        ambiguous_callbacks_by_leaf: dict[str, list] = defaultdict(list)
        ambiguous_events_by_leaf: dict[str, list] = defaultdict(list)
        ambiguous_inheritance_by_leaf: dict[str, list] = defaultdict(list)
        ambiguous_qualified_by_leaf: dict[str, list] = defaultdict(list)

        for module_id, module in modules.items():
            tree = getattr(module, "ast_tree", None)
            if tree is None:
                continue
            visitor = SinglePassConsumerVisitor(module_id, reexports)
            visitor.visit(tree)
            aliases = visitor.aliases

            # 1. Calls
            for event in visitor.call_events:
                if event.resolved:
                    direct_calls_by_target[event.resolved].append((module_id, event.lineno, event.context))
                if event.candidate:
                    instance_calls_by_target[event.candidate].append((module_id, event.lineno, event.context))

                name_to_check = event.called_name or event.resolved
                if name_to_check:
                    leaf = name_to_check.split(".")[-1]
                    ambiguous_calls_by_leaf[leaf].append((
                        module_id, event.called_name, event.resolved, event.candidate, event.lineno, event.context, aliases
                    ))

            # 2. Callbacks
            for name, resolved, lineno, ctx in visitor.callback_calls:
                if resolved:
                    callbacks_by_target[resolved].append((module_id, lineno, ctx))
                name_to_check = name or resolved
                if name_to_check:
                    leaf = name_to_check.split(".")[-1]
                    ambiguous_callbacks_by_leaf[leaf].append((
                        module_id, name, resolved, lineno, ctx, aliases
                    ))

            # 3. Events
            for name, resolved, lineno, ctx in visitor.event_bindings:
                if resolved:
                    events_by_target[resolved].append((module_id, lineno, ctx))
                name_to_check = name or resolved
                if name_to_check:
                    leaf = name_to_check.split(".")[-1]
                    ambiguous_events_by_leaf[leaf].append((
                        module_id, name, resolved, lineno, ctx, aliases
                    ))

            # 4. Inheritance
            for child_name, base_name, resolved, lineno in visitor.inheritance:
                if resolved:
                    inheritance_by_target[resolved].append((module_id, child_name, lineno))
                name_to_check = base_name or resolved
                if name_to_check:
                    leaf = name_to_check.split(".")[-1]
                    ambiguous_inheritance_by_leaf[leaf].append((
                        module_id, child_name, base_name, resolved, lineno, aliases
                    ))

            # 5. Qualified Refs
            for name, resolved, lineno, ctx in visitor.qualified_refs:
                if resolved:
                    qualified_refs_by_target[resolved].append((module_id, lineno, ctx))
                name_to_check = name or resolved
                if name_to_check:
                    leaf = name_to_check.split(".")[-1]
                    ambiguous_qualified_by_leaf[leaf].append((
                        module_id, name, resolved, lineno, ctx, aliases
                    ))

            # 6. Imports
            for imp in getattr(module, "imports", []):
                imp_module = getattr(imp, "module", None)
                for imported_name in imp.names:
                    source_module = _absolute_import_module(
                        module_id, imp_module, getattr(imp, "level", 0)
                    )
                    if imported_name == "*":
                        star_imports_by_source[source_module].append(module_id)
                    else:
                        target_id = _resolve_reexport(f"{source_module}.{imported_name}", reexports)
                        imports_by_target[target_id].append(module_id)

        return cls(
            modules=modules,
            root_path=root_path,
            reexports=reexports,
            direct_calls_by_target=dict(direct_calls_by_target),
            instance_calls_by_target=dict(instance_calls_by_target),
            callbacks_by_target=dict(callbacks_by_target),
            events_by_target=dict(events_by_target),
            inheritance_by_target=dict(inheritance_by_target),
            qualified_refs_by_target=dict(qualified_refs_by_target),
            imports_by_target=dict(imports_by_target),
            star_imports_by_source=dict(star_imports_by_source),
            ambiguous_calls_by_leaf=dict(ambiguous_calls_by_leaf),
            ambiguous_callbacks_by_leaf=dict(ambiguous_callbacks_by_leaf),
            ambiguous_events_by_leaf=dict(ambiguous_events_by_leaf),
            ambiguous_inheritance_by_leaf=dict(ambiguous_inheritance_by_leaf),
            ambiguous_qualified_by_leaf=dict(ambiguous_qualified_by_leaf),
        )

    def build_symbol_references(
        self,
        target_symbols: list[str] | set[str],
        definer_module: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Projects symbol reference facts for the target symbols of definer_module in O(1).
        """
        bare_symbols = set(target_symbols)
        if definer_module:
            qualified_map = {f"{definer_module}.{s}": s for s in bare_symbols}
        else:
            qualified_map = {s: s for s in bare_symbols}

        target_symbols_set = set(qualified_map.keys())
        references = {symbol: _empty_reference() for symbol in target_symbols_set}

        for symbol in target_symbols_set:
            leaf = symbol.split(".")[-1]
            rec = references[symbol]

            # 1. Direct Calls
            for consumer_id, lineno, ctx in self.direct_calls_by_target.get(symbol, ()):
                rec["called_by"].append(consumer_id)
                rec["called_by_detail"].append({"module": consumer_id, "line": lineno, "context": ctx})

            # 2. Instance Method Calls
            for consumer_id, lineno, ctx in self.instance_calls_by_target.get(symbol, ()):
                rec["called_by"].append(consumer_id)
                rec["called_by_detail"].append({"module": consumer_id, "line": lineno, "context": ctx})

            # 3. Callbacks
            for consumer_id, lineno, ctx in self.callbacks_by_target.get(symbol, ()):
                rec["callback_called"].append(consumer_id)
                rec["callback_called_detail"].append({"module": consumer_id, "line": lineno, "context": ctx})

            # 4. Events
            for consumer_id, lineno, ctx in self.events_by_target.get(symbol, ()):
                rec["event_bound_by"].append(consumer_id)
                rec["event_bound_by_detail"].append({"module": consumer_id, "line": lineno, "context": ctx})

            # 5. Inheritance
            for consumer_id, child_name, lineno in self.inheritance_by_target.get(symbol, ()):
                rec["inherited_by"].append(consumer_id)
                rec["inherited_by_detail"].append({"module": consumer_id, "child": child_name, "line": lineno})

            # 6. Qualified Refs
            for consumer_id, lineno, ctx in self.qualified_refs_by_target.get(symbol, ()):
                rec["qualified_refs"].append(consumer_id)
                rec["qualified_refs_detail"].append({"module": consumer_id, "line": lineno, "context": ctx})

            # 7. Direct Imports
            for consumer_id in self.imports_by_target.get(symbol, ()):
                rec["imported_from"].append(consumer_id)

            # 8. Star Imports
            for source_prefix, consumers in self.star_imports_by_source.items():
                if symbol.startswith(source_prefix + ".") or any(
                    exported.startswith(source_prefix + ".") and orig == symbol
                    for exported, orig in self.reexports.items()
                ):
                    rec["imported_from"].extend(consumers)

            # 9. Ambiguous Calls for leaf
            for consumer_id, called_name, resolved, candidate, lineno, ctx, aliases in self.ambiguous_calls_by_leaf.get(leaf, ()):
                if resolved in target_symbols_set or (candidate and candidate in target_symbols_set):
                    continue
                _, match = _classify_match(called_name, resolved, target_symbols_set, aliases)
                if match == symbol:
                    rec["called_by_ambiguous"].append(consumer_id)
                    rec["called_by_ambiguous_detail"].append({
                        "module": consumer_id,
                        "reason": "short_name_match_no_confirmed_import",
                        "line": lineno,
                        "context": ctx,
                    })

        references = _normalize_references(references)
        return {
            qualified_map[qualified]: data
            for qualified, data in references.items()
        }


def build_repository_reference_index(modules: dict, root_path: str) -> RepositoryReferenceIndex:
    """
    Builds a run-scoped single-pass repository symbol reference index.
    """
    return RepositoryReferenceIndex.build(modules, root_path)
