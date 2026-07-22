# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/collisions.py

Semantic name collision validation handling both identical and differing code implementations,
attaching code snippets for JSON reporting.
"""

from collections import defaultdict
from ..domain.module import Module
from ..domain.validation import ValidationError


def validate_name_collisions(
    modules: dict[str, Module],
) -> list[ValidationError]:
    """
    Detect name occurrences across files for the same artifact type.
    Captures both differing implementations (conflicts) and identical implementations (duplicates),
    attaching code snippets to the validation error for reporting.
    """
    errors: list[ValidationError] = []
    name_map = defaultdict(list)

    for module_path, module in modules.items():
        classes = getattr(module, "class_definitions", {})
        functions = getattr(module, "function_definitions", {})
        variables = getattr(module, "variable_definitions", {})

        if isinstance(classes, list):
            classes = {c: getattr(module, f"get_class_code", lambda x: "")(c) for c in classes}
        if isinstance(functions, list):
            functions = {f: "" for f in functions}

        for cls_name, cls_code in classes.items():
            name_map[cls_name].append({
                "type": "class", 
                "file": module_path, 
                "code": cls_code
            })

        for func_name, func_code in functions.items():
            name_map[func_name].append({
                "type": "function", 
                "file": module_path, 
                "code": func_code
            })

        for var_name, var_code in variables.items():
            name_map[var_name].append({
                "type": "variable", 
                "file": module_path, 
                "code": var_code
            })

    for name, occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        
        # Sprawdzamy kolizję tylko wtedy, gdy nazwa występuje w WIELU RÓŻNYCH PLIKACH
        if len(unique_files) > 1:
            types_found = {occ["type"] for occ in occurrences}
            
            # Tylko ten sam typ artefaktu (np. klasa z klasą, funkcja z funkcją)
            if len(types_found) == 1:
                codes = [occ["code"] for occ in occurrences]
                artifact_type = next(iter(types_found))
                files_str = ", ".join(unique_files)
                
                # Przygotowujemy słownik ze snippetami kodu dla każdego pliku
                code_snippets = {
                    occ["file"]: occ["code"] for occ in occurrences
                }

                # Przypadek 1: Kod się RÓŻNI (faktyczna kolizja / ryzyko semantyczne)
                if len(set(codes)) > 1:
                    error = ValidationError(
                        kind="NAME_COLLISION",
                        message=f"Semantic name collision for {artifact_type} '{name}' with DIFFERENT implementations across files: {files_str}",
                        nodes=list(unique_files),
                    )
                    error.code_snippets = code_snippets
                    error.artifact_type = artifact_type
                    error.is_identical = False
                    errors.append(error)
                
                # Przypadek 2: Kod jest IDENTYCZNY (świadomy duplikat / współdzielona definicja)
                else:
                    error = ValidationError(
                        kind="IDENTICAL_DEFINITION_DUPLICATE",
                        message=f"Identical definition for {artifact_type} '{name}' across files: {files_str}",
                        nodes=list(unique_files),
                    )
                    error.code_snippets = code_snippets
                    error.artifact_type = artifact_type
                    error.is_identical = True
                    errors.append(error)

    return errors
