import ast
from .extractor import _call_name

class UsageVisitor(ast.NodeVisitor):
    def __init__(self, wanted_symbols):
        self.wanted = set(wanted_symbols)
        self.used = set()

    def visit_Name(self, node):
        if node.id in self.wanted:
            self.used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        name = _call_name(node)
        if name in self.wanted:
            self.used.add(name)
            
        short = name.split(".")[-1] if name else None
        if short in self.wanted:
            self.used.add(short)
            
        self.generic_visit(node)

def _read_module_tree(root_path, module):
    return getattr(module, "ast_tree", None)

def find_symbol_usage(modules, target_module, symbols, root_path):
    usage = {}
    wanted = set(symbols)
    if not wanted:
        return usage

    for module_id, module in modules.items():
        if module_id == target_module:
            continue

        tree = _read_module_tree(root_path, module)
        if tree is None:
            continue

        visitor = UsageVisitor(wanted)
        visitor.visit(tree)

        for symbol in visitor.used:
            usage.setdefault(symbol, []).append(module_id)

    return {key: sorted(set(value)) for key, value in usage.items()}
