# -*- coding: utf-8 -*-
"""
repo_guardian/core/validator/collisions.py

Semantic name collision validation handling both identical and differing code implementations,
attaching code snippets for JSON reporting.
"""

import ast
from collections import defaultdict
from pathlib import Path
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
        # Pobieramy fizyczną ścieżkę do pliku tak samo jak w działającym detektorze
        file_path_str = getattr(module, "absolute_path", None) or getattr(module, "path", None)
        if not file_path_str:
            continue

        file_path = Path(file_path_str)
        if not file_path.exists():
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

        # Zbieramy definicje oraz ich wycinek kodu źródłowego za pomocą AST
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Wyciągamy surowy kod węzła klasy lub jego treść
                try:
                    code_snippet = ast.get_source_segment(source, node) or ""
                except Exception:
                    code_snippet = node.name
                
                name_map[node.name].append({
                    "type": "class",
                    "file": module_path,
                    "code": code_snippet
                })

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                try:
                    code_snippet = ast.get_source_segment(source, node) or ""
                except Exception:
                    code_snippet = node.name

                name_map[node.name].append({
                    "type": "function",
                    "file": module_path,
                    "code": code_snippet
                })

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            code_snippet = ast.get_source_segment(source, node) or ""
                        except Exception:
                            code_snippet = target.id

                        name_map[target.id].append({
                            "type": "variable",
                            "file": module_path,
                            "code": code_snippet
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
