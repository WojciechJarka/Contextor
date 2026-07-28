from collections import defaultdict
from pathlib import Path
from .extractor import SymbolVisitor, extract_symbol_facts

def build_symbol_index(modules, root_path=None):
    index = defaultdict(list)

    for module_id, module in modules.items():
        ast_tree = getattr(module, "ast_tree", None)
        if ast_tree is None:
            path = Path(root_path) / module.path if root_path else module.path
            facts = extract_symbol_facts(path)
        else:
            visitor = SymbolVisitor()
            visitor.visit(ast_tree)
            facts = visitor.facts

        if facts.errors:
            continue

        for symbol in facts.all_symbols():
            index[symbol].append(module_id)

    return {symbol: sorted(mods) for symbol, mods in index.items()}
