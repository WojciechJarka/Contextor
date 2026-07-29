"""
ui/gui.py

Core presentation layer. GuardianGUI manages root Tkinter window,
state persistence, sub-windows and orchestrates the analysis process.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from repo_guardian.core.api.facade import GuardianFacade
from repo_guardian.ui.path_memory import load_state, save_state
from repo_guardian.ui.gui_parser import run_parser_window
from repo_guardian.ui.exclude_check import check_stale_excludes
from repo_guardian.ui.exclude_gui import run_exclude_window
from repo_guardian.ui.system_actions import handle_open_output_folder, handle_empty_output_folder
from repo_guardian.ui.progress_widget import create_progress_bar, create_log_box, run_with_progress
from repo_guardian.ui.theme import apply_theme, HeaderTooltipManager, BG, PAD_SM, PAD_MD, PAD_LG
from repo_generator.repo_gui import run_repo_generator

class GuardianGUI:
    """
    Main application controller and view wrapper.
    Responsible for initializing Tkinter components, maintaining UI state
    (repository path, layer, single file target) and dispatching
    analysis events to GuardianFacade.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Reposter")
        
        self.state = load_state()
        gui_geom = self.state.get("gui_geometry", "760x640")
        self.root.geometry(gui_geom)
        self.root.minsize(680, 560)
        
        apply_theme(self.root)
        
        self.repo_path_var = tk.StringVar(value=self.state.get("repository", "").replace("\\", "/"))
        self.layer_path_var = tk.StringVar(value=self.state.get("layer", "").replace("\\", "/"))
        self.file_path_var = tk.StringVar(value=self.state.get("python_file", "").replace("\\", "/"))
        
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
            self.parser_win = run_parser_window(parent=self.root)

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
                    "Detected files/directories that returned to the repo.\n\nReapply exclusions?\n\n" + "\n".join(conflicts)
                )
                if answer:
                    from repo_guardian.ui.exclude_gui import reapply_excludes
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
        
        ttk.Label(header, text="Reposter", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        sub_label = ttk.Label(header, text="Static architecture analysis · Read-only mode", style="Sub.TLabel")
        sub_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.tooltip = HeaderTooltipManager(sub_label, "Static architecture analysis · Read-only mode")
        
        warn_label = tk.Label(
            header,
            text="⚠  WARNING: ADD ALL NON-PYTHON STRUCTURES TO THE EXCLUDE LIST BEFORE RUNNING ANY ANALYSIS — OTHERWISE ERRORS WILL OCCUR.",
            fg="#ff4040",
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            wraplength=680,
            justify="left",
        )
        warn_label.grid(row=2, column=0, sticky="w", pady=(6, 0))

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
        project_section = ttk.Labelframe(self.container, text="Project", padding=(PAD_MD, PAD_SM, PAD_MD, PAD_MD))
        project_section.grid(row=1, column=0, sticky="ew")
        project_section.columnconfigure(0, weight=1)
        
        self._add_path_row(
            project_section, 0, "Repository root", self.repo_path_var, self.browse_repository,
            "This must be the ROOT directory of the analyzed project."
        )
        ttk.Separator(project_section).grid(row=2, column=0, columnspan=2, sticky="ew", pady=PAD_MD)
        
        self._add_path_row(
            project_section, 3, "Layer — optional subdirectory of the root", self.layer_path_var, self.browse_layer,
            "Subdirectory of the analyzed repo for which you want a separate layer report."
        )
        ttk.Separator(project_section).grid(row=5, column=0, columnspan=2, sticky="ew", pady=PAD_MD)
        
        self._add_path_row(
            project_section, 6, "Single file — optional .py file to analyze", self.file_path_var, self.browse_file,
            "A single .py file for which you want a report in the context of the entire repo."
        )

    def _setup_actions(self):
        """
        Configures primary analysis buttons (Full Repo, Layer, Single File)
        and binds them to their respective execution callbacks.
        """
        actions_section = ttk.Frame(self.container)
        actions_section.grid(row=2, column=0, sticky="ew", pady=(PAD_LG, 0))
        for i in range(3):
            actions_section.columnconfigure(i, weight=1)
            
        self.analyze_btn = ttk.Button(actions_section, text="Analyze Repository", style="Primary.TButton", command=self.analyze)
        self.analyze_btn.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))
        
        self.analyze_layer_btn = ttk.Button(actions_section, text="Analyze Layer", style="Secondary.TButton", command=self.analyze_layer)
        self.analyze_layer_btn.grid(row=0, column=1, sticky="ew", padx=PAD_SM)
        
        self.analyze_single_btn = ttk.Button(actions_section, text="Analyze Single File", style="Secondary.TButton", command=self.analyze_single)
        self.analyze_single_btn.grid(row=0, column=2, sticky="ew", padx=(PAD_SM, 0))

        self.tooltip.bind_tooltip(self.analyze_btn, "Run full analysis of the entire repository and produce global metrics.")
        self.tooltip.bind_tooltip(self.analyze_layer_btn, "Run scoped analysis on a specific folder (layer) within the repository.")
        self.tooltip.bind_tooltip(self.analyze_single_btn, "Run analysis for a single file, assessing its context within the full repository.")

    def _setup_progress(self):
        """
        Sets up the indeterminate progress bar and the 
        scrolled text box for streaming stdout log messages.
        """
        progress_section = ttk.Frame(self.container)
        progress_section.grid(row=3, column=0, sticky="nsew", pady=(PAD_LG, 0))
        progress_section.columnconfigure(0, weight=1)
        
        self.progress_bar = create_progress_bar(progress_section)
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
        
        out_btn = ttk.Button(bottom_frame, text="Output Folder", style="Ghost.TButton", command=self.open_output_folder)
        out_btn.pack(side="left")
        
        emp_btn = ttk.Button(bottom_frame, text="Empty Output", style="Danger.Ghost.TButton", command=self.empty_output_folder)
        emp_btn.pack(side="left", padx=(PAD_SM, 0))
        
        exc_btn = ttk.Button(bottom_frame, text="Exclude", style="Ghost.TButton", command=self.open_exclude_window)
        exc_btn.pack(side="left", padx=(PAD_SM, 0))
        
        rb_btn = ttk.Button(bottom_frame, text="Repo Builder", style="Ghost.TButton", command=self.open_repo_builder)
        rb_btn.pack(side="left", padx=(PAD_SM, 0))
        
        p_btn = ttk.Button(bottom_frame, text="Parse JSON", style="Ghost.TButton", command=self.open_parser_window)
        p_btn.pack(side="right")

        self.tooltip.bind_tooltip(out_btn, "Open directory containing all analysis reports.")
        self.tooltip.bind_tooltip(emp_btn, "Permanently delete all contents in the Output Folder.")
        self.tooltip.bind_tooltip(exc_btn, "Manage ignored files/directories for the repository.")
        self.tooltip.bind_tooltip(rb_btn, "Open tool to bundle source code into a text file for LLMs.")
        self.tooltip.bind_tooltip(p_btn, "Utility tool to read analysis JSON outputs (it must be a full artifact JSON report).")

    # ======================================================
    # CALLBACKS
    # ======================================================

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
            messagebox.showwarning("Missing repository", "Select Repository (root) first, before choosing a layer.")
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
            messagebox.showwarning("Invalid layer", "Layer cannot be the same directory as the repository root.\nSelect a subdirectory instead.")
            return
            
        if root_resolved not in layer_resolved.parents:
            messagebox.showwarning("Invalid layer", f"Selected directory is outside the repository root.\nLayer must be a subdirectory of:\n{root_resolved}")
            return
            
        self.layer_path_var.set(str(layer_resolved).replace("\\", "/"))
        save_state(layer=str(layer_resolved).replace("\\", "/"))

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if file_path:
            file_path = file_path.replace("\\", "/")
            self.file_path_var.set(file_path)
            save_state(python_file=file_path)

    def analyze(self):
        path = self.repo_path_var.get()
        if not path:
            messagebox.showwarning("Missing repository", "Please select ROOT directory of scanned project")
            return

        def task(log=None):
            return GuardianFacade.analyze_project(path, log=log)

        def on_success(errors):
            if not errors:
                messagebox.showinfo("OK", "No issues found. Repository is healthy!")
                return
            msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
            messagebox.showwarning("Issues Detected", msg)

        def on_error(exc):
            messagebox.showerror("error", str(exc))

        run_with_progress(
            self.root, self.progress_bar, task,
            on_success=on_success, on_error=on_error,
            buttons=[self.analyze_btn, self.analyze_layer_btn, self.analyze_single_btn],
            log_box=self.log_box
        )

    def analyze_layer(self):
        root_dir = self.repo_path_var.get()
        layer_dir = self.layer_path_var.get()
        
        if not root_dir:
            messagebox.showwarning("Missing repository", "Please select ROOT directory of scanned project")
            return
        if not layer_dir:
            messagebox.showwarning("Missing layer", "Please select a layer (subdirectory) to analyze.")
            return
            
        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(layer_dir).resolve()
        except Exception:
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return
            
        if layer_resolved == root_resolved or root_resolved not in layer_resolved.parents:
            messagebox.showwarning("Invalid layer", "Layer must be a subdirectory of the selected repository root.")
            return

        def task(log=None):
            return GuardianFacade.analyze_layer(str(root_resolved), str(layer_resolved), log=log)

        def on_success(output_pattern):
            messagebox.showinfo("Done", f"Generated 5 layer reports:\n{output_pattern}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        run_with_progress(
            self.root, self.progress_bar, task,
            on_success=on_success, on_error=on_error,
            buttons=[self.analyze_btn, self.analyze_layer_btn, self.analyze_single_btn],
            log_box=self.log_box
        )

    def analyze_single(self):
        file_path = self.file_path_var.get()
        if not file_path.endswith(".py"):
            messagebox.showwarning("Invalid file", "Select Python file first.")
            return
            
        repo_root = self.repo_path_var.get()
        if not repo_root:
            messagebox.showwarning("Missing repository root", "Please select ROOT directory of scanned project")
            return

        def task(log=None):
            return GuardianFacade.analyze_single_file(file_path, repo_root, log=log)

        def on_success(output):
            messagebox.showinfo("Done", f"Single file report created:\n{output}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        run_with_progress(
            self.root, self.progress_bar, task,
            on_success=on_success, on_error=on_error,
            buttons=[self.analyze_btn, self.analyze_layer_btn, self.analyze_single_btn],
            log_box=self.log_box
        )

    def open_output_folder(self):
        project_root = Path(__file__).resolve().parent.parent
        handle_open_output_folder(project_root)

    def empty_output_folder(self):
        project_root = Path(__file__).resolve().parent.parent
        handle_empty_output_folder(project_root)

    def on_closing(self):
        save_state(
            gui_geometry=self.root.geometry(),
            repository=self.repo_path_var.get(),
            layer=self.layer_path_var.get(),
            python_file=self.file_path_var.get()
        )
        self.root.destroy()

def run():
    root = tk.Tk()
    app = GuardianGUI(root)
    root.mainloop()
