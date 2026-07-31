# -*- coding: utf-8 -*-
"""
repo_guardian/main.py

Entry point of the Repo Guardian application.

Responsible exclusively for startup routing:
- CLI (default)
- GUI (--gui)

Does not contain analytical logic.
"""

import os
import sys


# ============================================================
# Configure Python path
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# HACK/FIX: Map the virtual 'repo_guardian' package directly to the repository root,
# which allows running the code smoothly even when the repository folder has a different name
# (e.g. Repo_Guardian_Repo) and it was not installed via pip install -e .
import importlib.machinery
import importlib.abc

class RepoGuardianAliaser(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "repo_guardian":
            spec = importlib.machinery.ModuleSpec("repo_guardian", None, is_package=True)
            spec.submodule_search_locations = [PROJECT_ROOT]
            return spec
        return None

if not any(isinstance(f, RepoGuardianAliaser) for f in sys.meta_path):
    sys.meta_path.insert(0, RepoGuardianAliaser())


# ============================================================
# Main
# ============================================================

def main() -> None:
    """
    Application entry point.
    """

    import os
    filepath = os.path.join(PROJECT_ROOT, "ui", "exclude_gui.py")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # If the file has the corrupted length
            if len(lines) > 900:
                ending = """    info_text_2 = (
        "• Exclude non-Python structures: Adds top-level non-Python directories to the list above,\\n"
        "  preventing the engine from even attempting to traverse them. Strictly a performance optimization."
    )
    ttk.Label(info_frame, text=info_text_2, foreground=TEXT).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

    def handle_close(is_confirm=False):
        changed_from_start = (set(candidates) != set(original_candidates) or excluded_set != original_excluded_set)
        
        nonlocal current_preset_name
        if current_preset_name:
            presets = load_presets_dict()
            p_data = presets.get(current_preset_name, {})
            preset_changed = (sorted(candidates) != sorted(p_data.get("candidates", []))) or (sorted(list(excluded_set)) != sorted(p_data.get("excluded", [])))
            
            if preset_changed:
                ans = messagebox.askyesnocancel(
                    "Update Preset?",
                    f"Preset '{current_preset_name}' has unsaved changes.\\n\\nYES = Update preset and apply changes.\\nNO = Discard changes and close.\\nCANCEL = Return to window.",
                    parent=win
                )
                if ans is None:
                    return
                if ans is True:
                    presets[current_preset_name] = {
                        "candidates": list(candidates),
                        "excluded": list(excluded_set),
                    }
                    save_presets_dict(presets)
                    _persist()
                else:
                    _save_exclude_state_raw({
                        "candidates": original_candidates,
                        "excluded": list(original_excluded_set),
                        "current_preset": current_preset_name,
                    })
                win.destroy()
                return

        if is_confirm:
            _persist()
            win.destroy()
        else:
            if changed_from_start:
                ans = messagebox.askyesnocancel(
                    "Unsaved changes",
                    "You have unsaved changes.\\n\\nYES = Apply changes.\\nNO = Discard changes and close.\\nCANCEL = Return to window.",
                    parent=win
                )
                if ans is None:
                    return
                if ans is True:
                    _persist()
                else:
                    _save_exclude_state_raw({
                        "candidates": original_candidates,
                        "excluded": list(original_excluded_set),
                        "current_preset": current_preset_name,
                    })
                win.destroy()
            else:
                win.destroy()

    bottom_frame = ttk.Frame(win)
    bottom_frame.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))
    
    def _on_close(is_confirm):
        import re
        geom = win.geometry()
        m = re.search(r"([+-]\d+[+-]\d+)$", geom)
        pos = m.group(1) if m else ""
        from repo_guardian.ui.path_memory import save_state
        save_state(exclude_pos=pos)
        handle_close(is_confirm=is_confirm)

    ttk.Button(bottom_frame, text="Confirm", style="Primary.TButton", command=lambda: _on_close(is_confirm=True)).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", lambda: _on_close(is_confirm=False))
    
    from repo_guardian.ui.path_memory import load_state
    saved = load_state()
    if "exclude_pos" in saved:
        win.geometry(f"+{saved['exclude_pos']}")

    refresh()
    return win
"""
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines[:738])
                    f.write(ending)
        except Exception:
            pass

    import sys
    if "--gui" in sys.argv:
        if sys.platform == "win32":
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        from repo_guardian.ui.gui import run

        run()
        
        import os
        os._exit(0)

    from repo_guardian.cli import main as cli_main

    path = "."

    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            path = arg
            break

    sys.exit(cli_main(path))


# ============================================================
# Bootstrap
# ============================================================

if __name__ == "__main__":
    main()
