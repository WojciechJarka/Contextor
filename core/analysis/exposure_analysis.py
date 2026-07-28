# -*- coding: utf-8 -*-

import ast

def analyze_symbol_exposure(module_id: str, all_symbols: list, modules: dict, root_path: str = None) -> dict:
    """
    Dynamic scanner capturing uses of symbols defined
    in this module via reflection (getattr/hasattr), framework
    calls (api_exposure) and serialization.
    """
    result = {}
    
    for symbol in all_symbols:
        result[symbol] = {
            "reflection": [],
            "serialization": [],
            "cli_exposure": False,
            "api_exposure": False,
            "registry_exposure": False
        }

    short_module = module_id.split(".")[-1]
    
    for mid, mod in modules.items():
        tree = getattr(mod, "_ast_cache", None)
        if not tree:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    
                if func_name in ("getattr", "hasattr", "setattr", "import_module"):
                    if node.args and isinstance(node.args[-1], ast.Constant) and isinstance(node.args[-1].value, str):
                        val = node.args[-1].value
                        if val in all_symbols or f"{short_module}.{val}" in all_symbols:
                            key = val if val in all_symbols else f"{short_module}.{val}"
                            if mid not in result[key]["reflection"]:
                                result[key]["reflection"].append(mid)
                                
                elif func_name in ("dumps", "dump", "asdict"):
                    if node.args and isinstance(node.args[0], ast.Name):
                        val = node.args[0].id
                        if val in all_symbols or f"{short_module}.{val}" in all_symbols:
                            key = val if val in all_symbols else f"{short_module}.{val}"
                            if mid not in result[key]["serialization"]:
                                result[key]["serialization"].append(mid)

            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and mid == module_id:
                for dec in node.decorator_list:
                    d_name = ""
                    if isinstance(dec, ast.Name):
                        d_name = dec.id
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        d_name = dec.func.id
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        d_name = dec.func.attr
                        
                    if d_name in ("command", "group", "cli"):
                        if node.name in result:
                            result[node.name]["cli_exposure"] = True
                    elif d_name in ("get", "post", "route", "api", "app"):
                        if node.name in result:
                            result[node.name]["api_exposure"] = True
                    elif d_name in ("register", "register_handler", "subscribe", "receiver"):
                        if node.name in result:
                            result[node.name]["registry_exposure"] = True
                            
    return result
