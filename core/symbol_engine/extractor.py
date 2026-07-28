import ast
from pathlib import Path
from .domain import SymbolFacts

def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr
    return None

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self):
        self.facts = SymbolFacts()
        self.class_stack = []
        self.function_depth = 0

    def visit_ClassDef(self, node):
        self.facts.classes.add(node.name)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        if self.class_stack:
            self.facts.methods.add(f"{self.class_stack[-1]}.{node.name}")
        else:
            self.facts.functions.add(node.name)
            
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

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
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        facts.errors.append(str(exc))
        return facts

    visitor = SymbolVisitor()
    visitor.visit(tree)
    return visitor.facts

def extract_file_symbols(file_path: Path | str) -> dict:
    """Legacy Adapter"""
    facts = extract_symbol_facts(file_path)
    return facts.to_dict()
