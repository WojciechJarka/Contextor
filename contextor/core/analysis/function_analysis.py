"""
contextor/core/analysis/function_analysis.py

Advanced Function-level AST intelligence.
Extracts facts: signatures, complexity, nesting, exception flow, data shape and unused params.
"""

import ast


class ControlFlowAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1
        self.max_depth = 0
        self.current_depth = 0
        self.raises = []
        self.catches = []

    def generic_visit(self, node):
        super().generic_visit(node)

    def _increase_depth(self, node):
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node):
        self.complexity += 1
        self._increase_depth(node)

    def visit_For(self, node):
        self.complexity += 1
        self._increase_depth(node)

    def visit_While(self, node):
        self.complexity += 1
        self._increase_depth(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        if node.type:
            if isinstance(node.type, ast.Name):
                self.catches.append(node.type.id)
            elif isinstance(node.type, ast.Attribute):
                self.catches.append(node.type.attr)
        self._increase_depth(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Raise(self, node):
        if node.exc:
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                self.raises.append(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                self.raises.append(node.exc.id)
        self.generic_visit(node)


class UnusedParameterAnalyzer(ast.NodeVisitor):
    def __init__(self, args):
        self.args = set(args)
        self.used = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.args:
            self.used.add(node.id)
        self.generic_visit(node)


class DataShapeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.returned_keys = set()

    def visit_Return(self, node):
        if node.value and isinstance(node.value, ast.Dict):
            for k in node.value.keys:
                if k and isinstance(k, ast.Constant):
                    self.returned_keys.add(k.value)
        self.generic_visit(node)


def build_signature(node: ast.FunctionDef):
    args = [arg.arg for arg in getattr(node.args, "args", [])]
    if getattr(node.args, "vararg", None):
        args.append("*" + node.args.vararg.arg)
    if getattr(node.args, "kwarg", None):
        args.append("**" + node.args.kwarg.arg)
    return f"{node.name}(" + ", ".join(args) + ")"


def _extract_arg_annotations(node: ast.FunctionDef) -> list:
    args = getattr(node.args, "args", [])
    result = []
    for arg in args:
        annotation = None
        if getattr(arg, "annotation", None) is not None:
            try:
                annotation = ast.unparse(arg.annotation)
            except Exception:
                annotation = None
        result.append({"name": arg.arg, "annotation": annotation})
    return result


def analyze_control_flow(node, args):
    cf = ControlFlowAnalyzer()
    cf.visit(node)

    upa = UnusedParameterAnalyzer(args)
    upa.visit(node)

    dsa = DataShapeAnalyzer()
    dsa.visit(node)

    unused = list(set(args) - upa.used)

    return {
        "complexity": cf.complexity,
        "max_depth": cf.max_depth,
        "raises": sorted(list(set(cf.raises))),
        "catches": sorted(list(set(cf.catches))),
        "unused_params": sorted(unused),
        "dto_schema": sorted(list(dsa.returned_keys)),
    }


def analyze_functions(tree):
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args_list = [arg.arg for arg in getattr(node.args, "args", [])]
            cf_metrics = analyze_control_flow(node, args_list)

            result[node.name] = {
                "signature": build_signature(node),
                "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                "visibility": "private" if node.name.startswith("_") else "public",
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", None),
                "docstring": ast.get_docstring(node),
                "return_annotation": ast.unparse(node.returns)
                if getattr(node, "returns", None) is not None
                else None,
                "arg_annotations": _extract_arg_annotations(node),
                "metrics": cf_metrics,
            }
    return result
