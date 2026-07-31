import os
import subprocess

def restore():
    repo_dir = r"c:\Temp\Contextor_Repo"
    target_file = os.path.join(repo_dir, "ui", "exclude_gui.py")
    print(f"Restoring {target_file} from git HEAD...")
    try:
        content = subprocess.check_output(["git", "show", "HEAD:ui/exclude_gui.py"], cwd=repo_dir)
        with open(target_file, "wb") as f:
            f.write(content)
        print("Restore successful! Now applying the missing position saving...")
        
        # Apply the fix directly here!
        with open(target_file, "r", encoding="utf-8") as f:
            text = f.read()
            
        old_close = """    def _on_close(is_confirm):
        handle_close(is_confirm=is_confirm)

    ttk.Button(bottom_frame, text="Confirm", style="Primary.TButton", command=lambda: _on_close(is_confirm=True)).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", lambda: _on_close(is_confirm=False))
    
    refresh()
    return win"""

        new_close = """    def _on_close(is_confirm):
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
    return win"""

        if old_close in text:
            text = text.replace(old_close, new_close)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(text)
            print("Position saving feature applied successfully.")
        else:
            print("Warning: Could not find the expected string to patch the position saving feature.")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    restore()
