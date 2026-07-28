# -*- coding: utf-8 -*-

"""
repo_guardian/core/reference/visitor.py

Wizytor AST wykrywający fakty dotyczące użycia symboli:
wywołania, importy, callbacki, dziedziczenie.
"""

import ast

from .resolution import (
    _attribute_name,
    _resolve_alias,
    _classify_match,
)


class SymbolReferenceVisitor(ast.NodeVisitor):
    
    def __init__(self, target_symbols):
        self.target_symbols = set(target_symbols)
        self.called = set()
        self.called_ambiguous = set()
        self.event_bound = set()
        self.inherited = []
        self.aliases = {}
        self.instances = {}

    def _detect_positional_callbacks(self, node):
        func_name = _attribute_name(node.func)
        if not func_name:
            return
        method = func_name.split(".")[-1]
        
        EVENT_CALLBACK_METHODS = {"bind", "subscribe"}
        SINGLE_ARG_CALLBACK_METHODS = {"on"}
        
        if method in EVENT_CALLBACK_METHODS:
            if len(node.args) >= 2:
                name = _attribute_name(node.args[1])
                resolved = _resolve_alias(name, self.aliases)
                _, match = _classify_match(name, resolved, self.target_symbols, self.aliases)
                if match:
                    self.event_bound.add(match)
        elif method in SINGLE_ARG_CALLBACK_METHODS:
            if len(node.args) >= 1:
                name = _attribute_name(node.args[0])
                resolved = _resolve_alias(name, self.aliases)
                _, match = _classify_match(name, resolved, self.target_symbols, self.aliases)
                if match:
                    self.event_bound.add(match)

    def _detect_callback_arguments(self, node):
        callback_keys = {
            "command", "callback", "handler", "func",
            "on_click", "on_change", "on_submit"
        }
        for keyword in node.keywords:
            if keyword.arg not in callback_keys:
                continue
            name = _attribute_name(keyword.value)
            resolved = _resolve_alias(name, self.aliases)
            _, match = _classify_match(name, resolved, self.target_symbols, self.aliases)
            if match:
                self.event_bound.add(match)

    # ------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------

    def visit_ImportFrom(self, node):
        for item in node.names:
            local_name = item.asname or item.name
            imported_name = f"{node.module}.{item.name}" if node.module else item.name
            self.aliases[local_name] = imported_name
        self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            local_name = item.asname or item.name.split(".")[-1]
            self.aliases[local_name] = item.name
        self.generic_visit(node)

    # ------------------------------------------------------
    # INSTANCE TRACKING
    # ------------------------------------------------------

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            constructor = _attribute_name(node.value.func)
            constructor = _resolve_alias(constructor, self.aliases)
            if constructor:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.instances[target.id] = constructor
        self.generic_visit(node)

    # ------------------------------------------------------
    # CALL DETECTION
    # ------------------------------------------------------

    def visit_Call(self, node):
        self._detect_callback_arguments(node)
        self._detect_positional_callbacks(node)
        called_name = _attribute_name(node.func)
        resolved = _resolve_alias(called_name, self.aliases)

        if resolved in self.target_symbols:
            self.called.add(resolved)
            self.generic_visit(node)
            return

        if self._resolve_instance_method(resolved):
            self.generic_visit(node)
            return

        _, match = _classify_match(called_name, resolved, self.target_symbols, self.aliases)
        if match:
            self.called_ambiguous.add(match)

        self.generic_visit(node)

    def _resolve_instance_method(self, resolved):
        if not resolved:
            return False
        parts = resolved.split(".")
        if len(parts) != 2:
            return False
        
        instance_name, method = parts
        constructor = self.instances.get(instance_name)
        if not constructor:
            return False
            
        candidate = f"{constructor}.{method}"
        if candidate in self.target_symbols:
            self.called.add(candidate)
            return True
        return False

    # ------------------------------------------------------
    # INHERITANCE
    # ------------------------------------------------------

    def visit_ClassDef(self, node):
        for base in node.bases:
            base_name = _attribute_name(base)
            resolved = _resolve_alias(base_name, self.aliases)
            _, match = _classify_match(base_name, resolved, self.target_symbols, self.aliases)
            if match:
                self.inherited.append((node.name, match))
        self.generic_visit(node)
