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
from tkinter import filedialog, messagebox

from pathlib import Path
import os
import shutil
import subprocess
import sys

from repo_guardian.core.indexer import build_index
from repo_guardian.core.graph import build_graph
from repo_guardian.core.incremental import get_cached_graph
from repo_guardian.core.validator import validate

from repo_guardian.core.reporting import (
    generate_report,
    save_all_reports,
)

from repo_guardian.core.metrics import compute_graph_metrics
from repo_guardian.core.cycles import detect_cycles
from repo_guardian.core.debt import compute_debt

from repo_guardian.core.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)

from repo_guardian.ui.gui_parser import run_parser_window
from repo_guardian.ui.path_memory import load_state, save_state
from repo_guardian.ui.exclude_check import check_stale_excludes
from repo_guardian.ui.exclude_gui import run_exclude_window
from repo_guardian.ui.progress_widget import create_progress_bar, run_with_progress

def run():

    root = tk.Tk()

    root.title(
        "Repo Guardian v1"
    )

    root.geometry(
        "600x320"
    )


    repo_path_var = tk.StringVar()

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

            save_state(repository=directory)

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

        def task():

            modules = build_index(
                path
            )


            graph, cache_hit = get_cached_graph(
                modules,
                build_graph
            )


            errors = validate(
                modules,
                graph
            )


            repo_name = Path(path).name

            metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)
            cycles = detect_cycles(graph.hard_edges)
            debt = compute_debt(graph.hard_edges, graph.soft_edges, cycles, metrics)

            save_all_reports(
                repo_name=repo_name,
                modules=modules,
                graph=graph,
                metrics=metrics,
                cycles=cycles,
                debt=debt,
                runtime={"cache_hit": cache_hit},
                root_path=path
            )

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
            buttons=[analyze_btn, analyze_single_btn]
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

        def task():

            file = Path(
                file_path
            )

            modules = build_index(
                repo_root
            )

            graph, cache_hit = get_cached_graph(
                modules,
                build_graph
            )

            global_report = generate_report(
                graph,
                modules=modules,
                runtime={
                    "cache_hit": cache_hit
                }
            )


            report = generate_single_file_report(
                file_path,
                modules,
                graph,
                global_report,
                repo_root
            )


            output = (
                "output/"
                +
                f"single_{file.stem}.json"
            )


            save_single_file_report(
                report,
                output
            )

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
            buttons=[analyze_btn, analyze_single_btn]
        )

    # ======================================================
    # TOOLTIP
    # ======================================================


    def show_root_tooltip(event):

        root.title(
            "Repo Guardian v1 - It must be ROOT directory of scanned project"
        )


    def hide_root_tooltip(event):

        root.title(
            "Repo Guardian v1"
        )



    # ======================================================
    # UI
    # ======================================================


    tk.Label(
        root,
        text="Repo Guardian v1 (Read-Only Mode)"
    ).pack(
        pady=10
    )



    # -------------------------
    # Repository ROOT
    # -------------------------


    repo_frame = tk.Frame(
        root
    )

    repo_frame.pack(
        pady=5
    )


    tk.Entry(
        repo_frame,
        textvariable=repo_path_var,
        width=50
    ).pack(
        side=tk.LEFT,
        padx=5
    )


    repo_button = tk.Button(
        repo_frame,
        text="Browse Repository",
        command=browse_repository
    )


    repo_button.pack(
        side=tk.LEFT,
        padx=5
    )


    repo_button.bind(
        "<Enter>",
        show_root_tooltip
    )

    repo_button.bind(
        "<Leave>",
        hide_root_tooltip
    )

    # -------------------------
    # Single File
    # -------------------------


    file_frame = tk.Frame(
        root
    )

    file_frame.pack(
        pady=5
    )


    tk.Entry(
        file_frame,
        textvariable=file_path_var,
        width=50
    ).pack(
        side=tk.LEFT,
        padx=5
    )


    tk.Button(
        file_frame,
        text="Browse File",
        command=browse_file
    ).pack(
        side=tk.LEFT,
        padx=5
    )



    # -------------------------
    # Actions
    # -------------------------

    analyze_btn = tk.Button(
        root,
        text="Analyze Repository",
        command=analyze
    )

    analyze_btn.pack(
        pady=15
    )

    analyze_single_btn = tk.Button(
        root,
        text="Analyze Single File",
        command=analyze_single
    )

    analyze_single_btn.pack(
        pady=5
    )

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
    # Bottom Action
    # -------------------------

    # Pasek postępu spakowany jako pierwszy na dole
    progress_bar = create_progress_bar(root)

    bottom_frame = tk.Frame(root)

    bottom_frame.pack(
        side="bottom",
        fill="x",
        padx=10,
        pady=10
    )

    tk.Button(
        bottom_frame,
        text="Output Folder",
        command=open_output_folder
    ).pack(
        side="left"
    )


    tk.Button(
        bottom_frame,
        text="Opróżnij output",
        command=empty_output_folder
    ).pack(
        side="left",
        padx=20
    )


    tk.Button(
        bottom_frame,
        text="Exclude",
        command=run_exclude_window
    ).pack(
        side="left",
        padx=20
    )

    tk.Button(
        bottom_frame,
        text="Parsuj JSON",
        command=run_parser_window
    ).pack(
        side="right"
    )

    root.mainloop()
