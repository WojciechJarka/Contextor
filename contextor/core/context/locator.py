"""
contextor/core/context/locator.py

Odpowiedzialność:
- lokalizacja modułu w indeksie (optymalizacja I/O).
"""


def find_module_id(file_path: str, modules: dict) -> str | None:
    """
    Znajduje module_id na podstawie ścieżki.
    Optymalizacja: brak obciążających operacji Path.resolve() w pętlach.
    """
    if not file_path:
        return None

    norm_target = file_path.replace("\\", "/")

    # Szybka ścieżka (exact or suffix match na rel path)
    for module_id, module in modules.items():
        mod_path = getattr(module, "path", "").replace("\\", "/")
        if mod_path == norm_target or mod_path.endswith("/" + norm_target):
            return module_id

    # Fallback na samo rozszerzenie pliku
    target_name = norm_target.split("/")[-1]
    for module_id, module in modules.items():
        mod_path = getattr(module, "path", "").replace("\\", "/")
        if mod_path.split("/")[-1] == target_name:
            return module_id

    return None
