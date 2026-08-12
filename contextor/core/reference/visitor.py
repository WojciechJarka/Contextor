"""
contextor/core/reference/visitor.py

AST visitor detecting symbol usage facts:
calls, imports, callbacks, event bindings, and inheritance.
"""

import ast

from .resolution import (
    _attribute_name,
    _classify_match,
    _resolve_alias,
)


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
    """

    def __init__(self, target_symbols):
        self.target_symbols = set(target_symbols)

        self.called = set()
        self.callback_called = set()
        self.called_ambiguous = set()
        self.event_bound = set()
        self.inherited = []

        self.aliases = {}
        self.instances = {}
        self.context_stack = []

    # ======================================================
    # CONTEXT
    # ======================================================

    def _current_context(self):
        if not self.context_stack:
            return None

        return self.context_stack[-1]

    def visit_FunctionDef(self, node):
        self.context_stack.append(node.name)
        self.generic_visit(node)
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

            resolved = _resolve_alias(name, self.aliases)

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

            resolved = _resolve_alias(name, self.aliases)

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

            resolved = _resolve_alias(name, self.aliases)

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
        for item in node.names:
            local_name = item.asname or item.name

            imported_name = (
                f"{node.module}.{item.name}"
                if node.module
                else item.name
            )

            self.aliases[local_name] = imported_name

        self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            local_name = item.asname or item.name.split(".")[-1]

            self.aliases[local_name] = item.name

        self.generic_visit(node)

    # ======================================================
    # INSTANCE TRACKING
    # ======================================================

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            constructor = _attribute_name(node.value.func)
            constructor = _resolve_alias(
                constructor,
                self.aliases,
            )

            if constructor:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.instances[target.id] = constructor

        self.generic_visit(node)

    # ======================================================
    # CALL DETECTION
    # ======================================================

    def visit_Call(self, node):
        self._detect_callback_arguments(node)
        self._detect_positional_callbacks(node)

        called_name = _attribute_name(node.func)

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

            resolved_dyn = _resolve_alias(
                dynamic_name,
                self.aliases,
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

        for arg in node.args:
            arg_name = _attribute_name(arg)

            if not arg_name:
                continue

            resolved_arg = _resolve_alias(
                arg_name,
                self.aliases,
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

        resolved = _resolve_alias(
            called_name,
            self.aliases,
        )

        if resolved in self.target_symbols:
            self.called.add(
                (
                    resolved,
                    getattr(node, "lineno", None),
                    self._current_context(),
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

        return None

    # ======================================================
    # INHERITANCE
    # ======================================================

    def visit_ClassDef(self, node):
        self.context_stack.append(node.name)

        for base in node.bases:
            base_name = _attribute_name(base)

            resolved = _resolve_alias(
                base_name,
                self.aliases,
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
        self.context_stack.pop()
