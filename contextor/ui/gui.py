"""
ui/gui.py

Core presentation layer. ContextorGUI manages root Tkinter window,
state persistence, sub-windows and orchestrates the analysis process.
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from contextor.core.api.facade import ContextorFacade
from contextor.repo_generator import run_repo_generator
from contextor.ui import theme
from contextor.ui.exclude_check import check_stale_excludes
from contextor.ui.exclude_gui import run_exclude_window
from contextor.ui.gui_parser import run_parser_window
from contextor.ui.path_memory import load_state, save_state
from contextor.ui.progress_widget import (
    create_cpu_indicator,
    create_log_box,
    create_progress_bar,
    run_with_progress,
)
from contextor.ui.system_actions import handle_empty_output_folder, handle_open_output_folder
from contextor.ui.test_runner import (
    TestSuiteUnavailable,
    format_summary,
    run_test_suite,
)
from contextor.ui.theme import (
    PAD_LG,
    PAD_MD,
    PAD_SM,
    HeaderTooltipManager,
    apply_theme,
)


class ContextorGUI:
    """
    Main application controller and view wrapper.
    Responsible for initializing Tkinter components, maintaining UI state
    (repository path, layer, single file target) and dispatching
    analysis events to ContextorFacade.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Contextor")

        self.state = load_state()
        gui_pos = self.state.get("gui_pos", "")
        if gui_pos:
            self.root.geometry(gui_pos)
        self.root.minsize(680, 560)

        self.theme_mode = self.state.get("theme", "light")
        if self.theme_mode not in theme.MODES:
            self.theme_mode = "light"
        apply_theme(self.root, self.theme_mode)

        self.repo_path_var = tk.StringVar(value=self.state.get("repository", "").replace("\\", "/"))
        self.layer_path_var = tk.StringVar(value=self.state.get("layer", "").replace("\\", "/"))
        self.file_path_var = tk.StringVar(
            value=self.state.get("python_file", "").replace("\\", "/")
        )

        self.exclude_win = None
        self.repo_builder_win = None
        self.parser_win = None

        self._check_stale_excludes()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_exclude_window(self):
        if self.exclude_win and self.exclude_win.winfo_exists():
            self.exclude_win.lift()
            self.exclude_win.focus_force()
        else:
            self.exclude_win = run_exclude_window(parent=self.root)

    def open_repo_builder(self):
        if self.repo_builder_win and self.repo_builder_win.winfo_exists():
            self.repo_builder_win.lift()
            self.repo_builder_win.focus_force()
        else:
            self.repo_builder_win = run_repo_generator(parent=self.root)

    def open_parser_window(self):
        if self.parser_win and self.parser_win.winfo_exists():
            self.parser_win.lift()
            self.parser_win.focus_force()
        else:
            self.parser_win = run_parser_window(repo_path=self.repo_path_var.get(), parent=self.root)

    def open_rewrite_tool(self):
        import os
        from tkinter import filedialog, messagebox
        output_dir = os.path.abspath("output")
        if not os.path.exists(output_dir):
            output_dir = os.getcwd()
        json_path = filedialog.askopenfilename(
            title="Select indexed compact JSON to rewrite",
            initialdir=output_dir, 
            filetypes=[("JSON files", "*.json")]
        )
        if json_path:
            from contextor.ui.gui_parser import rewrite_index_to_text
            try:
                out_path = rewrite_index_to_text(json_path, self.repo_path_var.get())
                messagebox.showinfo("Success", f"Rewritten text JSON saved to:\n{out_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rewrite JSON:\n{e}")

    def _check_stale_excludes(self):
        """
        Validates if previously excluded files are still present
        in the project or if they returned. Triggers prompt if true.
        """
        repo_saved = self.repo_path_var.get()
        if repo_saved:
            conflicts = check_stale_excludes(repo_saved)
            if conflicts:
                answer = messagebox.askyesno(
                    "Outdated exclusions",
                    "Detected files/directories that returned to the repo.\n\nReapply exclusions?\n\n"
                    + "\n".join(conflicts),
                )
                if answer:
                    from contextor.ui.exclude_gui import reapply_excludes

                    reapply_excludes(repo_saved, conflicts)

    def _build_ui(self):
        """
        Constructs the main grid layout container and orchestrates
        the creation of all child widgets (header, paths, actions).
        """
        self.container = ttk.Frame(self.root, padding=(PAD_LG, PAD_MD, PAD_LG, PAD_MD))
        self.container.pack(fill="both", expand=True)
        self.container.columnconfigure(0, weight=1)

        self._setup_header()
        self._setup_project_section()
        self._setup_actions()
        self._setup_progress()
        self._setup_toolbar()
        self.container.rowconfigure(3, weight=1)

    def _setup_header(self):
        header = ttk.Frame(self.container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, PAD_LG))
        header.columnconfigure(0, weight=1)

        header.columnconfigure(1, weight=0)

        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")

        # Top-right corner of the window.
        self.theme_btn = ttk.Button(
            header,
            text=self._theme_button_text(),
            style="Ghost.TButton",
            width=10,
            command=self.toggle_theme,
        )
        self.theme_btn.grid(row=0, column=1, sticky="ne")
        ttk.Label(title_frame, text="Contextor", style="Header.TLabel").pack(side="left")

        self.cmd_var = tk.BooleanVar(value=False)

        def toggle_cmd():
            import ctypes
            import sys

            if sys.platform == "win32":
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 5 if self.cmd_var.get() else 0)

        ttk.Checkbutton(
            title_frame, text="Open CMD log", variable=self.cmd_var, command=toggle_cmd
        ).pack(side="left", padx=(20, 0))

        self.test_suite_btn = ttk.Button(
            title_frame,
            text="Test suite",
            style="Ghost.TButton",
            command=self.run_test_suite,
        )
        self.test_suite_btn.pack(side="left", padx=(PAD_SM, 0))

        sub_label = ttk.Label(
            header, text="Static architecture analysis · Read-only mode", style="Sub.TLabel"
        )
        sub_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.tooltip = HeaderTooltipManager(
            sub_label, "Static architecture analysis · Read-only mode"
        )
        self.tooltip.bind_tooltip(
            self.test_suite_btn,
            "Run Contextor's own test suite and report the results.",
        )
        self.tooltip.bind_tooltip(
            self.theme_btn,
            "Switch between light and dark appearance.",
        )

        # Non-Python content no longer has to be excluded by hand: files
        # that are not analyzable Python are skipped and listed in the
        # report. Excluding them up front is now an optimization, not a
        # prerequisite, so this is a hint rather than a red warning.
        hint_label = ttk.Label(
            header,
            text=(
                "Files that are not analyzable Python are skipped automatically "
                "and listed in the report. Use Exclude to skip large vendored "
                "directories and speed up analysis."
            ),
            style="Sub.TLabel",
            wraplength=680,
            justify="left",
        )
        hint_label.grid(row=2, column=0, sticky="w", pady=(6, 0))

    def _add_path_row(self, parent, row, label_text, var, command, tooltip_text=None):
        ttk.Label(parent, text=label_text, style="Field.TLabel").grid(
            row=row, column=0, sticky="w", pady=(PAD_SM, 2), columnspan=2
        )
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row + 1, column=0, sticky="ew", padx=(0, PAD_SM))
        button = ttk.Button(parent, text="Browse…", style="Secondary.TButton", command=command)
        button.grid(row=row + 1, column=1, sticky="e")
        if tooltip_text:
            self.tooltip.bind_tooltip(entry, tooltip_text)
            self.tooltip.bind_tooltip(button, tooltip_text)

    def _setup_project_section(self):
        project_section = ttk.Labelframe(
            self.container, text="Project", padding=(PAD_MD, PAD_SM, PAD_MD, PAD_MD)
        )
        project_section.grid(row=1, column=0, sticky="ew")
        project_section.columnconfigure(0, weight=1)

        self._add_path_row(
            project_section,
            0,
            "Repository root",
            self.repo_path_var,
            self.browse_repository,
            "This must be the ROOT directory of the analyzed project.",
        )
        ttk.Separator(project_section).grid(row=2, column=0, columnspan=2, sticky="ew", pady=PAD_MD)

        self._add_path_row(
            project_section,
            3,
            "Layer — optional subdirectory of the root",
            self.layer_path_var,
            self.browse_layer,
            "Subdirectory of the analyzed repo for which you want a separate layer report.",
        )
        ttk.Separator(project_section).grid(row=5, column=0, columnspan=2, sticky="ew", pady=PAD_MD)

        self._add_path_row(
            project_section,
            6,
            "Single file — optional .py file to analyze",
            self.file_path_var,
            self.browse_file,
            "A single .py file for which you want a report in the context of the entire repo.",
        )

    def _setup_actions(self):
        """
        Configures primary analysis buttons (Full Repo, Layer, Single File)
        and binds them to their respective execution callbacks.
        """
        actions_section = ttk.Frame(self.container)
        actions_section.grid(row=2, column=0, sticky="ew", pady=(PAD_LG, 0))
        for i in range(4):
            actions_section.columnconfigure(i, weight=1)

        self.analyze_btn = ttk.Button(
            actions_section,
            text="Analyze Repository",
            style="Primary.TButton",
            command=self.analyze,
        )
        self.analyze_btn.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))

        self.analyze_layer_btn = ttk.Button(
            actions_section,
            text="Analyze Layer",
            style="Primary.TButton",
            command=self.analyze_layer,
        )
        self.analyze_layer_btn.grid(row=0, column=1, sticky="ew", padx=PAD_SM)

        self.analyze_single_btn = ttk.Button(
            actions_section,
            text="Analyze Single File",
            style="Primary.TButton",
            command=self.analyze_single,
        )
        self.analyze_single_btn.grid(row=0, column=2, sticky="ew", padx=(PAD_SM, 0))

        self.stop_btn = ttk.Button(
            actions_section,
            text="Stop analyze",
            command=self.stop_analysis,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=3, sticky="ew", padx=(PAD_LG, 0))

        self.tooltip.bind_tooltip(
            self.analyze_btn,
            "Run full analysis of the entire repository and produce global metrics.",
        )
        self.tooltip.bind_tooltip(
            self.analyze_layer_btn,
            "Run scoped analysis on a specific folder (layer) within the repository.",
        )
        self.tooltip.bind_tooltip(
            self.analyze_single_btn,
            "Run analysis for a single file, assessing its context within the full repository.",
        )
        self.tooltip.bind_tooltip(self.stop_btn, "Abort ongoing analysis.")

    def _setup_progress(self):
        """
        Sets up the indeterminate progress bar and the
        scrolled text box for streaming stdout log messages.
        """
        progress_section = ttk.Frame(self.container)
        progress_section.grid(row=3, column=0, sticky="nsew", pady=(PAD_LG, 0))
        progress_section.columnconfigure(0, weight=1)

        self.progress_bar = create_progress_bar(progress_section)
        self.cpu_indicator = create_cpu_indicator(progress_section)
        self.log_box = create_log_box(progress_section, height=8)
        self.log_box.configure(relief="flat", borderwidth=0)

    def _setup_toolbar(self):
        """
        Builds the bottom toolbar providing access to auxiliary
        windows: Output Folder, Exclude Editor, Repo Builder, JSON Parser.
        """
        ttk.Separator(self.container).grid(row=4, column=0, sticky="ew", pady=(PAD_MD, PAD_SM))
        bottom_frame = ttk.Frame(self.container)
        bottom_frame.grid(row=5, column=0, sticky="ew")

        out_btn = ttk.Button(
            bottom_frame,
            text="Output Folder",
            style="Ghost.TButton",
            command=self.open_output_folder,
        )
        out_btn.pack(side="left")

        emp_btn = ttk.Button(
            bottom_frame,
            text="Empty Output",
            style="Danger.Ghost.TButton",
            command=self.empty_output_folder,
        )
        emp_btn.pack(side="left", padx=(PAD_SM, 0))

        exc_btn = ttk.Button(
            bottom_frame, text="Exclude", style="Ghost.TButton", command=self.open_exclude_window
        )
        exc_btn.pack(side="left", padx=(PAD_SM, 0))

        rb_btn = ttk.Button(
            bottom_frame, text="Repo Builder", style="Ghost.TButton", command=self.open_repo_builder
        )
        rb_btn.pack(side="left", padx=(PAD_SM, 0))

        p_btn = ttk.Button(
            bottom_frame, text="Parse JSON", style="Ghost.TButton", command=self.open_parser_window
        )
        p_btn.pack(side="right")
        
        rewrite_btn = ttk.Button(
            bottom_frame, text="Rewrite Index -> Txt", style="Ghost.TButton", command=self.open_rewrite_tool
        )
        rewrite_btn.pack(side="right", padx=(0, PAD_SM))

        self.tooltip.bind_tooltip(out_btn, "Open directory containing all analysis reports.")
        self.tooltip.bind_tooltip(emp_btn, "Permanently delete all contents in the Output Folder.")
        self.tooltip.bind_tooltip(exc_btn, "Manage ignored files/directories for the repository.")
        self.tooltip.bind_tooltip(
            rb_btn, "Open tool to bundle source code into a text file for LLMs."
        )
        self.tooltip.bind_tooltip(
            p_btn,
            "Utility tool to read analysis JSON outputs (it must be a full artifact JSON report).",
        )
        self.tooltip.bind_tooltip(
            rewrite_btn,
            "Rewrite indexed compact report to full text strings for human reading.",
        )

    # ======================================================
    # CALLBACKS
    # ======================================================

    def stop_analysis(self):
        if hasattr(self, "progress_bar"):
            self.progress_bar.is_cancelled = True

    def browse_repository(self):
        directory = filedialog.askdirectory()
        if directory:
            directory = directory.replace("\\", "/")
            self.repo_path_var.set(directory)
            self.layer_path_var.set("")
            save_state(repository=directory)

    def browse_layer(self):
        root_dir = self.repo_path_var.get()
        if not root_dir:
            messagebox.showwarning(
                "Missing repository", "Select Repository (root) first, before choosing a layer."
            )
            return

        directory = filedialog.askdirectory(initialdir=root_dir)
        if not directory:
            return

        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(directory).resolve()
        except Exception:
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return

        if layer_resolved == root_resolved:
            messagebox.showwarning(
                "Invalid layer",
                "Layer cannot be the same directory as the repository root.\nSelect a subdirectory instead.",
            )
            return

        if root_resolved not in layer_resolved.parents:
            messagebox.showwarning(
                "Invalid layer",
                f"Selected directory is outside the repository root.\nLayer must be a subdirectory of:\n{root_resolved}",
            )
            return

        self.layer_path_var.set(str(layer_resolved).replace("\\", "/"))
        save_state(layer=str(layer_resolved).replace("\\", "/"))

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if file_path:
            file_path = file_path.replace("\\", "/")
            self.file_path_var.set(file_path)
            save_state(python_file=file_path)

    def _theme_button_text(self) -> str:
        return "Dark mode" if self.theme_mode == "light" else "Light mode"

    def toggle_theme(self):
        """
        Switches between light and dark appearance and remembers the choice.
        """

        self.theme_mode = "dark" if self.theme_mode == "light" else "light"

        theme.set_theme(self.root, self.theme_mode)

        self.theme_btn.config(text=self._theme_button_text())

        save_state(theme=self.theme_mode)

    def _busy_buttons(self):
        """
        Buttons disabled while a long-running operation is in progress.
        """

        return [
            self.analyze_btn,
            self.analyze_layer_btn,
            self.analyze_single_btn,
            self.test_suite_btn,
        ]

    def run_test_suite(self):
        """
        Runs Contextor's own test suite and reports the outcome.
        """

        def task(log=None, progress_callback=None):
            return run_test_suite(
                log=log,
                progress_callback=progress_callback,
                show_console=self.cmd_var.get(),
            )

        def on_success(result):
            summary = format_summary(result)

            if result["exit_code"] == 0 and result["total"] > 0:
                messagebox.showinfo(
                    "Test suite passed",
                    f"All {result['passed']} tests passed.\n\n{summary}",
                )
                return

            messagebox.showwarning("Test suite failed", summary)

        def on_error(exc):
            if isinstance(exc, TestSuiteUnavailable):
                messagebox.showwarning("Test suite unavailable", str(exc))
                return
            messagebox.showerror("Test suite", str(exc))

        def on_cancel():
            messagebox.showinfo("Test suite", "Test run cancelled.")

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            on_cancel=on_cancel,
            buttons=self._busy_buttons(),
            log_box=self.log_box,
            cpu_indicator=self.cpu_indicator,
            stop_button=self.stop_btn,
        )

    def analyze(self):
        path = self.repo_path_var.get()
        if not path:
            messagebox.showwarning(
                "Missing repository", "Please select ROOT directory of scanned project"
            )
            return

        def task(log=None, progress_callback=None):
            errors, _ = ContextorFacade.analyze_project(
                path, log=log, progress_callback=progress_callback
            )
            return errors

        def on_success(errors):
            if not errors:
                messagebox.showinfo("OK", "No issues found. Repository is healthy!")
                return
            msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
            messagebox.showwarning("Issues Detected", msg)

        def on_error(exc):
            messagebox.showerror("error", str(exc))

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=self._busy_buttons(),
            log_box=self.log_box,
            cpu_indicator=self.cpu_indicator,
            stop_button=self.stop_btn,
        )

    def analyze_layer(self):
        root_dir = self.repo_path_var.get()
        layer_dir = self.layer_path_var.get()

        if not root_dir:
            messagebox.showwarning(
                "Missing repository", "Please select ROOT directory of scanned project"
            )
            return
        if not layer_dir:
            messagebox.showwarning(
                "Missing layer", "Please select a layer (subdirectory) to analyze."
            )
            return

        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(layer_dir).resolve()
        except Exception:
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return

        if layer_resolved == root_resolved or root_resolved not in layer_resolved.parents:
            messagebox.showwarning(
                "Invalid layer", "Layer must be a subdirectory of the selected repository root."
            )
            return

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_layer(
                str(root_resolved),
                str(layer_resolved),
                log=log,
                progress_callback=progress_callback,
            )

        def on_success(output_pattern):
            messagebox.showinfo("Done", f"Generated 5 layer reports:\n{output_pattern}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=self._busy_buttons(),
            log_box=self.log_box,
            cpu_indicator=self.cpu_indicator,
            stop_button=self.stop_btn,
        )

    def analyze_single(self):
        file_path = self.file_path_var.get()
        if not file_path.endswith(".py"):
            messagebox.showwarning("Invalid file", "Select Python file first.")
            return

        repo_root = self.repo_path_var.get()
        if not repo_root:
            messagebox.showwarning(
                "Missing repository root", "Please select ROOT directory of scanned project"
            )
            return

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_single_file(
                file_path, repo_root, log=log, progress_callback=progress_callback
            )

        def on_success(output):
            messagebox.showinfo("Done", f"Single file report created:\n{output}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=self._busy_buttons(),
            log_box=self.log_box,
            cpu_indicator=self.cpu_indicator,
            stop_button=self.stop_btn,
        )

    def open_output_folder(self):
        handle_open_output_folder()

    def empty_output_folder(self):
        handle_empty_output_folder()

    def on_closing(self):
        import re

        geom = self.root.geometry()
        m = re.match(r"^(\d+x\d+)([+-]?\d+)([+-]?\d+)$", geom.replace("+-", "-"))
        if m:
            size = m.group(1)
            x, y = max(0, int(m.group(2))), max(0, int(m.group(3)))
            pos = f"{size}+{x}+{y}"
        else:
            pos = ""

        save_state(
            gui_pos=pos,
            theme=self.theme_mode,
            repository=self.repo_path_var.get(),
            layer=self.layer_path_var.get(),
            python_file=self.file_path_var.get(),
        )
        self.root.destroy()


def run():
    root = tk.Tk()
    # The controller registers itself on the widget tree, which keeps it
    # alive for the lifetime of the window; no local reference needed.
    ContextorGUI(root)
    root.mainloop()
