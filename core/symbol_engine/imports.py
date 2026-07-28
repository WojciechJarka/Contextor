def _module_candidates(name: str) -> set[str]:
    if not name:
        return set()
    parts = name.split(".")
    return {".".join(parts[:index]) for index in range(1, len(parts) + 1)}

def _is_internal_import(name: str, known_modules: set[str]) -> bool:
    candidates = _module_candidates(name)
    if candidates.intersection(known_modules):
        return True
    return any(module.startswith(name + ".") for module in known_modules)

def classify_imports(module, known_modules: set) -> dict:
    internal, external, local, global_imports = set(), set(), set(), set()
    
    for imp in getattr(module, "imports", []):
        name = imp.module
        if not name:
            continue
            
        if _is_internal_import(name, known_modules):
            internal.add(name)
            if getattr(imp, "is_local", False):
                local.add(name)
        else:
            external.add(name)
            global_imports.add(name)

    return {
        "internal": sorted(internal),
        "external": sorted(external),
        "local": sorted(local),
        "global": sorted(global_imports),
    }
