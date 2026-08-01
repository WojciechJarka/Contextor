"""
contextor/core/analysis/state_analysis.py

State and Closure Scoping Analyzer.
Tracks variable bindings, global/nonlocal mutations, self.* modifications,
and closures to determine strict function purity and UI interactions.
"""

import ast


class StateMutationAnalyzer(ast.NodeVisitor):
    def __init__(self, args_list):
        self.args = set(args_list)
        self.mutated_args = set()
        self.globals_used = set()
        self.globals_mutated = set()
        self.nonlocals = set()
        self.self_mutations = set()
        self.has_io = False

        self.io_functions = {"print", "open", "read", "write", "send", "recv", "input"}
        self.ui_keywords = {"tk.", "ttk.", "Tk", "Toplevel", "StringVar"}

    def visit_Global(self, node):
        self.globals_mutated.update(node.names)
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.nonlocals.update(node.names)
        self.generic_visit(node)

    def _check_target(self, target):
        if isinstance(target, ast.Name):
            if target.id in self.args:
                self.mutated_args.add(target.id)
            else:
                self.globals_mutated.add(target.id)
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name):
                if target.value.id == "self":
                    self.self_mutations.add(target.attr)
                elif target.value.id in self.args:
                    self.mutated_args.add(target.value.id)
        elif isinstance(target, ast.Subscript):
            if isinstance(target.value, ast.Name) and target.value.id in self.args:
                self.mutated_args.add(target.value.id)

    def visit_Assign(self, node):
        for target in node.targets:
            self._check_target(target)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._check_target(node.target)
        self.generic_visit(node)

    def visit_Call(self, node):
        # UI and I/O check (e.g. tk.StringVar().set() variables)
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.attr == "set":
                    self.has_io = True
                if node.func.value.id in ("tk", "ttk"):
                    self.has_io = True
            if node.func.attr in self.io_functions:
                self.has_io = True
        elif isinstance(node.func, ast.Name):
            if node.func.id in self.io_functions or node.func.id in self.ui_keywords:
                self.has_io = True
        self.generic_visit(node)


class ClosureAnalyzer(ast.NodeVisitor):
    def __init__(self, enclosing_vars):
        self.enclosing_vars = set(enclosing_vars)
        self.captured = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.enclosing_vars:
            self.captured.add(node.id)
        self.generic_visit(node)


def analyze_state_and_closures(node):
    """
    Executed on a single FunctionDef. Returns information about state and closures.
    """
    args_list = [arg.arg for arg in getattr(node.args, "args", [])]

    sma = StateMutationAnalyzer(args_list)
    sma.visit(node)

    # Extract all local variables from Assign within the current function
    local_vars = set()
    for child in node.body:
        if isinstance(child, ast.Assign):
            for t in child.targets:
                if isinstance(t, ast.Name):
                    local_vars.add(t.id)

    enclosing_vars = set(args_list) | local_vars
    captured_vars = []

    # Search for nested definitions (Closure Scoping)
    for child in node.body:
        if isinstance(child, ast.FunctionDef):
            ca = ClosureAnalyzer(enclosing_vars)
            ca.visit(child)
            captured_vars.extend(list(ca.captured))

    is_pure = (
        not sma.mutated_args
        and not sma.globals_mutated
        and not sma.self_mutations
        and not sma.has_io
    )

    return {
        "mutated_args": sorted(list(sma.mutated_args)),
        "globals_mutated": sorted(list(sma.globals_mutated)),
        "nonlocals_used": sorted(list(sma.nonlocals)),
        "self_mutations": sorted(list(sma.self_mutations)),
        "captured_in_closures": sorted(list(set(captured_vars))),
        "is_pure": is_pure,
    }


def analyze_module_states(tree):
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            state_metrics = analyze_state_and_closures(node)
            result[node.name] = state_metrics
    return result
