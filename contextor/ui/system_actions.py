"""
contextor/ui/system_actions.py

GUI controller actions delegated to manage system operations (I/O, opening windows, clearing output).
"""

import os
import shutil
import subprocess
import sys
from tkinter import messagebox

from contextor.core.paths import output_dir as resolve_output_dir


def handle_open_output_folder():
    # Resolved centrally so the GUI always opens the directory the
    # reporting layer actually writes to.
    output_dir = resolve_output_dir()

    if not output_dir.exists():
        messagebox.showinfo(
            "Output folder", "Output folder does not exist.\nRun repository analysis to create it."
        )
        return

    if sys.platform.startswith("win"):
        os.startfile(output_dir)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(output_dir)])
    else:
        subprocess.run(["xdg-open", str(output_dir)])


def handle_empty_output_folder():
    output_dir = resolve_output_dir()

    if not output_dir.exists():
        messagebox.showinfo("Output folder", "Output folder does not exist. Nothing to clear.")
        return

    confirm = messagebox.askyesno(
        "Empty output",
        f"Are you sure you want to delete all contents of the folder:\n{output_dir}\n\n"
        "This operation cannot be undone.",
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
        except OSError as exc:
            errors.append(f"{entry.name}: {exc}")

    if errors:
        messagebox.showwarning(
            "Partial error", "Failed to delete some items:\n" + "\n".join(errors)
        )
    else:
        messagebox.showinfo("Done", "The contents of the 'output' folder have been deleted.")
