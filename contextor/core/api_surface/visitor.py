"""
contextor/core/api_surface/visitor.py

AST API Surface Extractor (Visitor).
Ekstrahuje publiczną powierzchnię modułu:
funkcje, metody, klasy.
"""

import ast


def _visibility(name: str) -> str:
    return "private" if name.startswith("_") else "public"


def _annotation(node):
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _default_value(node):
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _signature(node):
    args = []
    defaults = node.args.defaults
    start_default_idx = len(node.args.args) - len(defaults)

    for i, arg in enumerate(node.args.args):
        default = defaults[i - start_default_idx] if i >= start_default_idx else None
        args.append(
            {
                "name": arg.arg,
                "annotation": _annotation(arg.annotation),
                "default": _default_value(default),
            }
        )

    return {"parameters": args, "returns": _annotation(node.returns)}


class APISurfaceVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = {}
        self.methods = {}
        self.classes = {}
        self.class_stack = []
        self.decorators = {}

    def _decorator_names(self, node):
        result = []
        for dec in node.decorator_list:
            try:
                result.append(ast.unparse(dec))
            except Exception:
                pass
        return result

    def visit_ClassDef(self, node):
        name = node.name
        self.classes[name] = {
            "kind": "class",
            "visibility": _visibility(name),
            "bases": [ast.unparse(base) for base in node.bases if base],
            "decorators": self._decorator_names(node),
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", None),
            "docstring": ast.get_docstring(node),
        }
        self.class_stack.append(name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        name = node.name
        full_name = name
        is_method = len(self.class_stack) > 0

        if is_method:
            full_name = f"{self.class_stack[-1]}.{name}"

        decorators = self._decorator_names(node)

        entry = {
            "kind": "method" if is_method else "function",
            "visibility": _visibility(name),
            "signature": _signature(node),
            "decorators": decorators,
            "classmethod": "classmethod" in decorators,
            "staticmethod": "staticmethod" in decorators,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", None),
            "docstring": ast.get_docstring(node),
        }

        if is_method:
            self.methods[full_name] = entry
        else:
            self.functions[name] = entry

        self.generic_visit(node)
