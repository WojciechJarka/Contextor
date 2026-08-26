"""
contextor/core/reference/visitor.py

AST visitor detecting symbol usage facts:
calls, imports, callbacks, event bindings, inheritance, and non-call qualified attribute refs.
"""

import ast
from typing import Optional

from .resolution import (
    _attribute_name,
    _absolute_import_module,
    _classify_match,
    _resolve_alias,
    _resolve_reexport,
)


EVENT_BINDING_METHODS = {
    "bind",
    "subscribe",
    "on",
}


def _is_event_binding_call(called_name: Optional[str]) -> bool:
    if not called_name:
        return False
    return called_name.rsplit(".", 1)[-1] in EVENT_BINDING_METHODS


class SymbolReferenceVisitor(ast.NodeVisitor):
    """
    Collects reference facts for a predefined set of target symbols.

    Usage categories are intentionally separated:

    - called:
        direct runtime calls
    - callback_called:
        target callable passed to another callable
    - event_bound:
        explicit event/subscription binding
    - called_ambiguous:
        short-name fallback matches without confirmed resolution
    - inherited:
        class inheritance relationships
    - qualified_refs:
        non-call qualified attribute references
    """

    def __init__(
        self,
        target_symbols,
        reexports=None,
        current_module=None,
        local_symbols=None,
    ):
        self.target_symbols = set(target_symbols)

        self.called = set()
        self.callback_called = set()
        self.called_ambiguous = set()
        self.event_bound = set()
        self.inherited = []
        self.qualified_refs = set()
        self.reference_evidence = set()

        self._call_funcs = set()
        self.aliases = {}
        self.instances = {}
        self.context_stack = []
        self.canonical_context_stack = []
        self.class_stack = []
        self.symbol_called = set()
        self.reexports = dict(reexports or {})
        self.current_module = current_module
        self.local_symbols = dict(local_symbols or {})

    def _resolve_name(self, name):
        resolved = _resolve_reexport(
            _resolve_alias(name, self.aliases),
            self.reexports,
        )
        if resolved != name:
            return resolved
        if name in self.local_symbols:
            return self.local_symbols[name]
        if name and name.startswith(("self.", "cls.")) and self.class_stack:
            local_method = f"{self.class_stack[-1]}.{name.split('.', 1)[1]}"
            return self.local_symbols.get(local_method, resolved)
        return resolved

    # ======================================================
    # CONTEXT
    # ======================================================

    def _current_context(self):
        if not self.context_stack:
            return None

        return self.context_stack[-1]

    def _current_canonical_context(self):
        if not self.canonical_context_stack:
            return None
        return self.canonical_context_stack[-1]

    def _visit_function_definition_expressions(self, node):
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

    def visit_FunctionDef(self, node):
        self._visit_function_definition_expressions(node)
        is_nested = bool(self.context_stack)
        canonical_caller = None
        if not is_nested:
            local_name = (
                f"{self.class_stack[-1]}.{node.name}"
                if self.class_stack
                else node.name
            )
            canonical_caller = (
                f"{self.current_module}::{local_name}"
                if self.current_module and local_name in self.local_symbols
                else None
            )
        self.context_stack.append(node.name)
        self.canonical_context_stack.append(canonical_caller)
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self.canonical_context_stack.pop()
            self.context_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    # ======================================================
    # EVENT / CALLBACK DETECTION
    # ======================================================

    def _detect_positional_callbacks(self, node):
        """
        Detect explicit event/subscription APIs.

        These are classified separately from generic callback
        arguments because they represent event binding semantics.
        """

        func_name = _attribute_name(node.func)

        if not func_name:
            return

        method = func_name.split(".")[-1]

        event_callback_methods = {"bind", "subscribe"}
        single_arg_callback_methods = {"on"}

        if method in event_callback_methods:
            if len(node.args) < 2:
                return

            name = _attribute_name(node.args[1])
            resolved = self._resolve_name(name)

            if resolved or name:
                self.reference_evidence.add(
                    (
                        resolved or name,
                        "event_bindings",
                        self._current_context() or "",
                        getattr(node, "lineno", 0),
                    )
                )

            classification, match = _classify_match(
                name,
                resolved,
                self.target_symbols,
                self.aliases,
            )

            if classification == "confirmed" and match:
                self.event_bound.add(
                    (
                        match,
                        getattr(node, "lineno", None),
                        self._current_context(),
                    )
                )

        elif method in single_arg_callback_methods:
            if len(node.args) < 1:
                return

            name = _attribute_name(node.args[0])
            resolved = self._resolve_name(name)

            if resolved or name:
                self.reference_evidence.add(
                    (
                        resolved or name,
                        "event_bindings",
                        self._current_context() or "",
                        getattr(node, "lineno", 0),
                    )
                )

            classification, match = _classify_match(
                name,
                resolved,
                self.target_symbols,
                self.aliases,
            )

            if classification == "confirmed" and match:
                self.event_bound.add(
                    (
                        match,
                        getattr(node, "lineno", None),
                        self._current_context(),
                    )
                )

    def _detect_callback_arguments(self, node):
        """
        Detect target callables passed as keyword arguments.

        Passing a callable as an argument is NOT itself a direct call
        and is NOT necessarily an event binding. It is recorded as
        callback usage.
        """

        callback_keys = {
            "command",
            "callback",
            "handler",
            "func",
            "on_click",
            "on_change",
            "on_submit",
        }

        for keyword in node.keywords:
            if keyword.arg not in callback_keys:
                continue

            name = _attribute_name(keyword.value)
            resolved = self._resolve_name(name)

            if resolved or name:
                self.reference_evidence.add(
                    (
                        resolved or name,
                        "callback_calls",
                        self._current_context() or "",
                        getattr(node, "lineno", 0),
                    )
                )

            classification, match = _classify_match(
                name,
                resolved,
                self.target_symbols,
                self.aliases,
            )

            if classification == "confirmed" and match:
                self.callback_called.add(
                    (
                        match,
                        getattr(node, "lineno", None),
                        self._current_context(),
                    )
                )

    # ======================================================
    # IMPORTS
    # ======================================================

    def visit_ImportFrom(self, node):
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
            self.reference_evidence.add(
                (
                    imported_name,
                    "api_imports",
                    "",
                    getattr(node, "lineno", 0),
                )
            )

        self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            local_name = item.asname or item.name.split(".")[-1]

            self.aliases[local_name] = item.name
            self.reference_evidence.add(
                (
                    item.name,
                    "api_imports",
                    "",
                    getattr(node, "lineno", 0),
                )
            )

        self.generic_visit(node)

    # ======================================================
    # INSTANCE TRACKING
    # ======================================================

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            constructor = _attribute_name(node.value.func)
            constructor = self._resolve_name(constructor)

            if constructor:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.instances[target.id] = constructor

        self.generic_visit(node)

    # ======================================================
    # QUALIFIED ATTRIBUTE REFERENCES (NON-CALL)
    # ======================================================

    def visit_Attribute(self, node):
        if node not in self._call_funcs:
            name = _attribute_name(node)
            if name and "." in name:
                resolved = self._resolve_name(name)
                if resolved or name:
                    self.reference_evidence.add(
                        (
                            resolved or name,
                            "qualified_refs",
                            self._current_context() or "",
                            getattr(node, "lineno", 0),
                        )
                    )
                classification, match = _classify_match(
                    name,
                    resolved,
                    self.target_symbols,
                    self.aliases,
                )
                if classification == "confirmed" and match:
                    self.qualified_refs.add(
                        (
                            match,
                            getattr(node, "lineno", None),
                            self._current_context(),
                        )
                    )

        self.generic_visit(node)

    # ======================================================
    # CALL DETECTION
    # ======================================================

    def _mark_call_func_tree(self, func):
        for child in ast.walk(func):
            if isinstance(child, ast.Attribute):
                self._call_funcs.add(child)

    def visit_Call(self, node):
        self._mark_call_func_tree(node.func)
        called_name = _attribute_name(node.func)
        is_event_binding = _is_event_binding_call(called_name)

        if is_event_binding:
            self._detect_positional_callbacks(node)
        else:
            self._detect_callback_arguments(node)
            self._detect_positional_callbacks(node)

        # --------------------------------------------------
        # Dynamic getattr(obj, "name")
        # --------------------------------------------------

        if (
            called_name == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            dynamic_name = node.args[1].value
            resolved_dyn = self._resolve_name(dynamic_name)

            self.reference_evidence.add(
                (
                    resolved_dyn or dynamic_name,
                    "called_ambiguous",
                    self._current_context() or "",
                    getattr(node, "lineno", 0),
                )
            )

            _, dyn_match = _classify_match(
                dynamic_name,
                resolved_dyn,
                self.target_symbols,
                self.aliases,
            )

            if dyn_match:
                self.called_ambiguous.add(
                    (
                        dyn_match,
                        getattr(node, "lineno", None),
                        self._current_context(),
                    )
                )

        # --------------------------------------------------
        # Positional higher-order arguments
        # --------------------------------------------------
        #
        # A callable passed as an argument is callback usage,
        # not a direct runtime call.
        #

        if not is_event_binding:
            for arg in node.args:
                arg_name = _attribute_name(arg)

                if not arg_name:
                    continue

                resolved_arg = self._resolve_name(arg_name)

                if resolved_arg or arg_name:
                    self.reference_evidence.add(
                        (
                            resolved_arg or arg_name,
                            "callback_calls",
                            self._current_context() or "",
                            getattr(node, "lineno", 0),
                        )
                    )

                classification, arg_match = _classify_match(
                    arg_name,
                    resolved_arg,
                    self.target_symbols,
                    self.aliases,
                )

                if classification == "confirmed" and arg_match:
                    self.callback_called.add(
                        (
                            arg_match,
                            getattr(node, "lineno", None),
                            self._current_context(),
                        )
                    )

        # --------------------------------------------------
        # Direct call
        # --------------------------------------------------

        resolved = self._resolve_name(called_name)

        if resolved or called_name:
            candidate = self._resolve_instance_method(resolved)
            target_to_record = candidate or resolved or called_name
            if target_to_record != "getattr":
                self.reference_evidence.add(
                    (
                        target_to_record,
                        "direct_calls",
                        self._current_context() or "",
                        getattr(node, "lineno", 0),
                    )
                )

        if resolved in self.target_symbols:
            self.called.add(
                (
                    resolved,
                    getattr(node, "lineno", None),
                    self._current_context(),
                )
            )
            canonical_caller = self._current_canonical_context()
            if canonical_caller is not None:
                self.symbol_called.add(
                    (
                        resolved,
                        getattr(node, "lineno", None),
                        canonical_caller,
                    )
                )

            self.generic_visit(node)
            return

        # --------------------------------------------------
        # Instance method resolution
        # --------------------------------------------------

        candidate = self._resolve_instance_method(resolved)

        if candidate:
            self.called.add(
                (
                    candidate,
                    getattr(node, "lineno", None),
                    self._current_context(),
                )
            )
            canonical_caller = self._current_canonical_context()
            if canonical_caller is not None:
                self.symbol_called.add(
                    (
                        candidate,
                        getattr(node, "lineno", None),
                        canonical_caller,
                    )
                )

            self.generic_visit(node)
            return

        # --------------------------------------------------
        # Ambiguous short-name fallback
        # --------------------------------------------------

        _, match = _classify_match(
            called_name,
            resolved,
            self.target_symbols,
            self.aliases,
        )

        if match:
            self.called_ambiguous.add(
                (
                    match,
                    getattr(node, "lineno", None),
                    self._current_context(),
                )
            )

        self.generic_visit(node)

    def _resolve_instance_method(self, resolved):
        """
        Resolve calls such as:

            obj.method()

        when `obj` was previously assigned from a known
        constructor.
        """

        if not resolved:
            return None

        parts = resolved.split(".")

        if len(parts) != 2:
            return None

        instance_name, method = parts

        constructor = self.instances.get(instance_name)

        if not constructor:
            return None

        candidate = f"{constructor}.{method}"

        if candidate in self.target_symbols:
            return candidate

        return candidate

    # ======================================================
    # INHERITANCE
    # ======================================================

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)

        for base in node.bases:
            base_name = _attribute_name(base)
            resolved = self._resolve_name(base_name)

            if resolved or base_name:
                self.reference_evidence.add(
                    (
                        resolved or base_name,
                        "inheritance",
                        node.name,
                        getattr(node, "lineno", 0),
                    )
                )

            classification, match = _classify_match(
                base_name,
                resolved,
                self.target_symbols,
                self.aliases,
            )

            if classification == "confirmed" and match:
                self.inherited.append(
                    (
                        node.name,
                        match,
                        getattr(node, "lineno", None),
                    )
                )

        self.generic_visit(node)
        self.class_stack.pop()
