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
    return None

def _extract_signature(node):
    if not hasattr(ast, "unparse"):
        return ""
    try:
        # Instead of constructing a dummy, unparse the whole node and extract the signature line
        unparsed = ast.unparse(node)
        # Function signature is everything before the first colon followed by a newline or just the first line
        sig = unparsed.split(":\n")[0]
        if sig.endswith(":"):
            sig = sig[:-1]
        
        # In case the body is one line (e.g., def foo(): pass), it might not have :\n
        # So we can just split by \n and take the first line as a fallback
        if '\n' in sig:
            sig = sig.split("\n")[0]
            if sig.endswith(":"):
                sig = sig[:-1]
                
        return sig
    except Exception:
        return ""

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
            full_name = f"{self.class_stack[-1]}.{node.name}"
            self.facts.methods.add(full_name)
        else:
            full_name = node.name
            self.facts.functions.add(full_name)
            
        sig = _extract_signature(node)
        if sig:
            self.facts.signatures[full_name] = sig
            
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    def visit_AsyncFunctionDef(self, node):
        if self.class_stack:
            full_name = f"{self.class_stack[-1]}.{node.name}"
            self.facts.methods.add(full_name)
        else:
            full_name = node.name
            self.facts.functions.add(full_name)
            
        sig = _extract_signature(node)
        if sig:
            self.facts.signatures[full_name] = sig

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
