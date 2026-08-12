import ast
import hashlib
from pathlib import Path

from contextor.core.source import SourceError, parse_source

from .domain import SymbolFacts


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _extract_signature(node):
    if not hasattr(ast, "unparse"):
        return ""
    try:
        function_type = (
            ast.AsyncFunctionDef
            if isinstance(node, ast.AsyncFunctionDef)
            else ast.FunctionDef
        )
        stub = function_type(
            name=node.name,
            args=node.args,
            body=[ast.Pass()],
            decorator_list=[],
            returns=node.returns,
            type_comment=getattr(node, "type_comment", None),
        )
        if hasattr(node, "type_params"):
            stub.type_params = node.type_params
        ast.fix_missing_locations(stub)
        return ast.unparse(stub).split(":\n", 1)[0].rstrip(":")
    except Exception:
        return ""


def _body_fingerprint(node):
    """Hash normalized executable body AST, ignoring layout and a leading docstring."""

    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    normalized = ast.dump(
        ast.Module(body=body, type_ignores=[]),
        annotate_fields=True,
        include_attributes=False,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self):
        self.facts = SymbolFacts()
        self.class_stack = []
        self.function_depth = 0

    def visit_ClassDef(self, node):
        if self.function_depth:
            self.generic_visit(node)
            return
        self.facts.classes.add(node.name)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        if self.function_depth:
            self.function_depth += 1
            self.generic_visit(node)
            self.function_depth -= 1
            return
        if self.class_stack:
            full_name = f"{self.class_stack[-1]}.{node.name}"
            self.facts.methods.add(full_name)
        else:
            full_name = node.name
            self.facts.functions.add(full_name)

        sig = _extract_signature(node)
        if sig:
            self.facts.signatures[full_name] = sig
        self.facts.body_fingerprints[full_name] = _body_fingerprint(node)

        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    def visit_Assign(self, node):
        if self.function_depth == 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.facts.globals.add(target.id)
                    self.facts.assignments.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if self.function_depth == 0 and isinstance(node.target, ast.Name):
            self.facts.globals.add(node.target.id)
            self.facts.assignments.add(node.target.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = _call_name(node.func)
        if name:
            self.facts.calls.add(name)
        self.generic_visit(node)


def extract_symbol_facts(file_path: Path | str) -> SymbolFacts:
    path = Path(file_path)
    facts = SymbolFacts()

    try:
        tree = parse_source(path)
    except SourceError as exc:
        facts.errors.append(str(exc))
        return facts

    visitor = SymbolVisitor()
    visitor.visit(tree)
    return visitor.facts


def extract_file_symbols(file_path: Path | str) -> dict:
    """Legacy Adapter"""
    facts = extract_symbol_facts(file_path)
    return facts.to_dict()
