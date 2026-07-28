# -*- coding: utf-8 -*-
"""
repo_guardian/ui/system_actions.py

GUI controller actions delegated to manage system operations (I/O, opening windows, clearing output).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

def handle_open_output_folder(project_root: Path):
    output_dir = project_root / "output"

    if not output_dir.exists():
        messagebox.showinfo(
            "Output folder",
            "Output folder does not exist.\n"
            "Run repository analysis to create it."
        )
        return

    if sys.platform.startswith("win"):
        os.startfile(output_dir)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(output_dir)])
    else:
        subprocess.run(["xdg-open", str(output_dir)])


def handle_empty_output_folder(project_root: Path):
    output_dir = project_root / "output"

    if not output_dir.exists():
        messagebox.showinfo(
            "Output folder",
            "Output folder does not exist. Nothing to clear."
        )
        return

    confirm = messagebox.askyesno(
        "Empty output",
        f"Are you sure you want to delete all contents of the folder:\n{output_dir}\n\n"
        "This operation cannot be undone."
    )

    if not confirm:
        return

    errors = []
    for entry in output_dir.iterdir():
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        except Exception as exc:
            errors.append(f"{entry.name}: {exc}")

    if errors:
        messagebox.showwarning(
            "Partial error",
            "Failed to delete some items:\n" + "\n".join(errors)
        )
    else:
        messagebox.showinfo(
            "Done",
            "The contents of the 'output' folder have been deleted."
        )
