# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/collisions.py

Semantic name collision validation.
"""

from collections import defaultdict
from ..domain.module import Module
from ..domain.validation import ValidationError


def validate_name_collisions(
    modules: dict[str, Module],
) -> list[ValidationError]:
    """
    Detect semantic name collisions (e.g. classes or functions 
    with identical names defined in different modules).
    """
    errors: list[ValidationError] = []
    name_map = defaultdict(list)

    for module_path, module in modules.items():
        # Pobieramy klasy i funkcje z obiektu Module (dostosuj jeśli nazwy atrybutów się różnią)
        classes = getattr(module, "classes", [])
        functions = getattr(module, "functions", [])
        variables = getattr(module, "variables", [])

        for cls in classes:
            name_map[cls].append({"type": "class", "file": module_path})

        for func in functions:
            name_map[func].append({"type": "function", "file": module_path})

        for var in variables:
            name_map[var].append({"type": "variable", "file": module_path})

    for name, occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        
        # Jeśli nazwa występuje w więcej niż jednym pliku i definiuje różne rzeczy / koliduje
        if len(unique_files) > 1:
            types_found = {occ["type"] for occ in occurrences}
            
            if len(types_found) > 1 or len(occurrences) > len(unique_files):
                files_str = ", ".join(unique_files)
                errors.append(
                    ValidationError(
                        kind="NAME_COLLISION",
                        message=f"Semantic name collision for '{name}' across files: {files_str}",
                        nodes=list(unique_files),
                    )
                )

    return errors
