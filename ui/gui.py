# -*- coding: utf-8 -*-
"""
repo_guardian/ui/gui.py

GUI (tkinter) – warstwa prezentacyjna.

WAŻNE:
GUI NIE używa CLI.
GUI korzysta bezpośrednio z core pipeline:
(index → graph → validate → report)

Wykorzystuje incremental cache dla grafów.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pathlib import Path
import os
import shutil
import subprocess
import sys

from repo_guardian.core.facade import GuardianFacade

from repo_guardian.ui.gui_parser import run_parser_window
from repo_guardian.ui.path_memory import load_state, save_state
from repo_guardian.ui.exclude_check import check_stale_excludes
from repo_guardian.ui.exclude_gui import run_exclude_window
from repo_guardian.ui.progress_widget import create_progress_bar, create_log_box, run_with_progress
from repo_guardian.core.validator.collisions import validate_name_collisions
from repo_guardian.ui.theme import apply_theme, Tooltip, PAD_SM, PAD_MD, PAD_LG
from repo_generator.repo_gui import run_repo_generator

def run():
    root = tk.Tk()

    root.title(
        "Repo Guardian"
    )

    root.geometry(
        "760x640"
    )
    root.minsize(680, 560)

    apply_theme(root)

    repo_path_var = tk.StringVar()
    layer_path_var = tk.StringVar()
    file_path_var = tk.StringVar()

    state = load_state()
    repo_saved = state.get(
        "repository",
        ""
    )

    if repo_saved:
        conflicts = check_stale_excludes(
            repo_saved
        )

        if conflicts:
            answer = messagebox.askyesno(
                "Nieaktualne wyjątki",
                "Wykryto pliki/katalogi, które wróciły do repo.\n\n"
                "Czy ponowić wyjątki?\n\n"
                +
                "\n".join(
                    conflicts
                )
            )

            if answer:
                from repo_guardian.ui.exclude_gui import reapply_excludes

                reapply_excludes(
                    repo_saved,
                    conflicts
                )

    repo_path_var.set(
        state.get(
            "repository",
            ""
        )
    )

    file_path_var.set(
        state.get(
            "python_file",
            ""
        )
    )

    # ======================================================
    # FILE PICKERS
    # ======================================================

    def browse_repository():
        directory = filedialog.askdirectory()

        if directory:
            repo_path_var.set(
                directory
            )

            # nowy root unieważnia poprzedni wybór warstwy -
            # mogła należeć do zupełnie innego repo
            layer_path_var.set("")

            save_state(repository=directory)

    def browse_layer():
        root_dir = repo_path_var.get()

        if not root_dir:
            messagebox.showwarning(
                "Missing repository",
                "Select Repository (root) first, before choosing a layer."
            )
            return

        directory = filedialog.askdirectory(
            initialdir=root_dir
        )

        if not directory:
            return

        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(directory).resolve()
        except Exception:
            messagebox.showerror(
                "Invalid path",
                "Could not resolve selected paths."
            )
            return

        if layer_resolved == root_resolved:
            messagebox.showwarning(
                "Invalid layer",
                "Layer cannot be the same directory as the repository root.\n"
                "Select a subdirectory instead."
            )
            return

        if root_resolved not in layer_resolved.parents:
            messagebox.showwarning(
                "Invalid layer",
                "Selected directory is outside the repository root.\n"
                "Layer must be a subdirectory of:\n"
                f"{root_resolved}"
            )
            return

        layer_path_var.set(
            str(layer_resolved)
        )

    def browse_file():
        file_path = filedialog.askopenfilename(
            filetypes=[
                (
                    "Python files",
                    "*.py"
                )
            ]
        )

        if file_path:
            file_path_var.set(
                file_path
            )

            save_state(python_file=file_path)

    # ======================================================
    # ANALYSIS
    # ======================================================

    def analyze():
        path = repo_path_var.get()

        if not path:
            messagebox.showwarning(
                "Missing repository",
                "Please select ROOT directory of scanned project"
            )
            return

        def task(log=None):
            errors = GuardianFacade.analyze_project(path, log=log)
            return errors

        def on_success(errors):
            if not errors:
                messagebox.showinfo(
                    "OK",
                    "No issues found. Repository is healthy!"
                )
                return

            msg = "\n".join(
                [
                    f"{e.kind}: {e.message}"
                    for e in errors
                ]
            )

            messagebox.showwarning(
                "Issues Detected",
                msg
            )

        def on_error(exc):
            messagebox.showerror(
                "error",
                str(exc)
            )

        run_with_progress(
            root,
            progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=[analyze_btn, analyze_layer_btn, analyze_single_btn],
            log_box=log_box
        )

    def analyze_layer():
        root_dir = repo_path_var.get()
        layer_dir = layer_path_var.get()

        if not root_dir:
            messagebox.showwarning(
                "Missing repository",
                "Please select ROOT directory of scanned project"
            )
            return

        if not layer_dir:
            messagebox.showwarning(
                "Missing layer",
                "Please select a layer (subdirectory) to analyze."
            )
            return

        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(layer_dir).resolve()
        except Exception:
            messagebox.showerror(
                "Invalid path",
                "Could not resolve selected paths."
            )
            return

        if (
            layer_resolved == root_resolved
            or root_resolved not in layer_resolved.parents
        ):
            messagebox.showwarning(
                "Invalid layer",
                "Layer must be a subdirectory of the selected repository root."
            )
            return

        def task(log=None):
            output_pattern = GuardianFacade.analyze_layer(
                str(root_resolved), str(layer_resolved), log=log
            )
            return output_pattern

        def on_success(output_pattern):
            messagebox.showinfo(
                "Done",
                f"Wygenerowano 5 raportów warstwy:\n{output_pattern}"
            )

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        run_with_progress(
            root,
            progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=[analyze_btn, analyze_layer_btn, analyze_single_btn],
            log_box=log_box
        )

    def analyze_single():
        file_path = file_path_var.get()

        if not file_path.endswith(".py"):
            messagebox.showwarning(
                "Invalid file",
                "Select Python file first."
            )
            return

        repo_root = repo_path_var.get()

        if not repo_root:
            messagebox.showwarning(
                "Missing repository root",
                "Please select ROOT directory of scanned project"
            )
            return

        def task(log=None):
            output = GuardianFacade.analyze_single_file(file_path, repo_root, log=log)
            return output

        def on_success(output):
            messagebox.showinfo(
                "Done",
                f"Single file report created:\n{output}"
            )

        def on_error(exc):
            messagebox.showerror(
                "Error",
                str(exc)
            )

        run_with_progress(
            root,
            progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=[analyze_btn, analyze_layer_btn, analyze_single_btn],
            log_box=log_box
        )

    # ======================================================
    # UI
    # ======================================================

    container = ttk.Frame(root, padding=(PAD_LG, PAD_MD, PAD_LG, PAD_MD))
    container.pack(fill="both", expand=True)
    container.columnconfigure(0, weight=1)

    # -------------------------
    # Header
    # -------------------------

    header = ttk.Frame(container)
    header.grid(row=0, column=0, sticky="ew", pady=(0, PAD_LG))
    header.columnconfigure(0, weight=1)

    ttk.Label(header, text="Repo Guardian", style="Header.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(
        header,
        text="Static architecture analysis · Read-only mode",
        style="Sub.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    # -------------------------
    # Project section (root / layer / single file)
    # -------------------------

    project_section = ttk.Labelframe(
        container, text="Project", padding=(PAD_MD, PAD_SM, PAD_MD, PAD_MD)
    )
    project_section.grid(row=1, column=0, sticky="ew")
    project_section.columnconfigure(1, weight=1)

    def add_path_row(parent, row, label_text, var, command, tooltip_text=None):
        ttk.Label(parent, text=label_text, style="Field.TLabel").grid(
            row=row, column=0, sticky="w", pady=(PAD_SM, 2), columnspan=2
        )
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row + 1, column=0, sticky="ew", padx=(0, PAD_SM))
        button = ttk.Button(parent, text="Browse…", style="Secondary.TButton", command=command)
        button.grid(row=row + 1, column=1, sticky="e")
        if tooltip_text:
            Tooltip(entry, tooltip_text)
            Tooltip(button, tooltip_text)
        return entry, button

    add_path_row(
        project_section,
        0,
        "Repository root",
        repo_path_var,
        browse_repository,
        "Musi to być katalog GŁÓWNY (root) analizowanego projektu.",
    )

    ttk.Separator(project_section).grid(
        row=2, column=0, columnspan=2, sticky="ew", pady=PAD_MD
    )

    add_path_row(
        project_section,
        3,
        "Layer — optional subdirectory of the root",
        layer_path_var,
        browse_layer,
        "Podkatalog analizowanego repo, dla którego chcesz osobny raport warstwy.",
    )

    ttk.Separator(project_section).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=PAD_MD
    )

    add_path_row(
        project_section,
        6,
        "Single file — optional .py file to analyze",
        file_path_var,
        browse_file,
        "Pojedynczy plik .py, dla którego chcesz raport w kontekście całego repo.",
    )

    # -------------------------
    # Actions
    # -------------------------

    actions_section = ttk.Frame(container)
    actions_section.grid(row=2, column=0, sticky="ew", pady=(PAD_LG, 0))
    actions_section.columnconfigure(0, weight=1)
    actions_section.columnconfigure(1, weight=1)
    actions_section.columnconfigure(2, weight=1)

    analyze_btn = ttk.Button(
        actions_section,
        text="Analyze Repository",
        style="Primary.TButton",
        command=analyze,
    )
    analyze_btn.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))

    analyze_layer_btn = ttk.Button(
        actions_section,
        text="Analyze Layer",
        style="Secondary.TButton",
        command=analyze_layer,
    )
    analyze_layer_btn.grid(row=0, column=1, sticky="ew", padx=PAD_SM)

    analyze_single_btn = ttk.Button(
        actions_section,
        text="Analyze Single File",
        style="Secondary.TButton",
        command=analyze_single,
    )
    analyze_single_btn.grid(row=0, column=2, sticky="ew", padx=(PAD_SM, 0))

    # -------------------------
    # Progress + log (fills remaining space)
    # -------------------------

    progress_section = ttk.Frame(container)
    progress_section.grid(row=3, column=0, sticky="nsew", pady=(PAD_LG, 0))
    progress_section.columnconfigure(0, weight=1)
    container.rowconfigure(3, weight=1)

    def open_output_folder():
        project_root = Path(__file__).resolve().parent.parent

        output_dir = project_root / "output"

        if not output_dir.exists():
            messagebox.showinfo(
                "Output folder",
                "Folder 'output' nie istnieje.\n"
                "Uruchom analizę repozytorium, aby został utworzony."
            )
            return

        if sys.platform.startswith("win"):
            os.startfile(output_dir)

        elif sys.platform == "darwin":
            subprocess.run(
                ["open", str(output_dir)]
            )

        else:
            subprocess.run(
                ["xdg-open", str(output_dir)]
            )

    def empty_output_folder():
        project_root = Path(__file__).resolve().parent.parent

        output_dir = project_root / "output"

        if not output_dir.exists():
            messagebox.showinfo(
                "Output folder",
                "Folder 'output' nie istnieje. Nie ma czego czyścić."
            )
            return

        confirm = messagebox.askyesno(
            "Opróżnij output",
            f"Na pewno usunąć całą zawartość folderu:\n{output_dir}\n\n"
            "Tej operacji nie można cofnąć."
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
                "Częściowy błąd",
                "Nie udało się usunąć niektórych elementów:\n"
                +
                "\n".join(errors)
            )

        else:
            messagebox.showinfo(
                "Gotowe",
                "Zawartość folderu 'output' została usunięta."
            )

    # -------------------------
    # Progress bar + log console
    # -------------------------

    progress_bar = create_progress_bar(progress_section)
    log_box = create_log_box(progress_section, height=8)
    log_box.configure(relief="flat", borderwidth=0)

    # -------------------------
    # Bottom toolbar (utility actions)
    # -------------------------

    ttk.Separator(container).grid(row=4, column=0, sticky="ew", pady=(PAD_MD, PAD_SM))

    bottom_frame = ttk.Frame(container)
    bottom_frame.grid(row=5, column=0, sticky="ew")

    ttk.Button(
        bottom_frame,
        text="Output Folder",
        style="Ghost.TButton",
        command=open_output_folder,
    ).pack(side="left")

    ttk.Button(
        bottom_frame,
        text="Empty Output",
        style="Danger.Ghost.TButton",
        command=empty_output_folder,
    ).pack(side="left", padx=(PAD_SM, 0))

    ttk.Button(
        bottom_frame,
        text="Exclude",
        style="Ghost.TButton",
        command=run_exclude_window,
    ).pack(side="left", padx=(PAD_SM, 0))

    ttk.Button(
        bottom_frame,
        text="Repo Builder",
        style="Ghost.TButton",
        command=run_repo_generator,
    ).pack(side="left", padx=(PAD_SM, 0))

    ttk.Button(
        bottom_frame,
        text="Parsuj JSON",
        style="Ghost.TButton",
        command=run_parser_window,
    ).pack(side="right")

    root.mainloop()
