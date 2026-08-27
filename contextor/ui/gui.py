"""
ui/gui.py

Core presentation layer. ContextorGUI manages root Tkinter window,
state persistence, sub-windows and orchestrates the analysis process.
"""

import os
import threading
import tkinter as tk
import uuid
from datetime import datetime
from queue import Empty, Queue
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state import DesktopLiveEventFeed, DesktopLiveWatcher, connect_or_start
from contextor.core.repository_identity import (
    RepositoryIdentityError,
    read_repository_identity,
)
from contextor.core.paths import prune_startup_caches
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
from contextor.core.program_log import close_cmd_log, configure_program_log, open_cmd_log
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

LIVE_START_MAX_ATTEMPTS = 4
LIVE_START_RETRY_DELAYS_MS = (1000, 2000, 5000)

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
        self.owner_token = uuid.uuid4().hex
        self.live_client = None
        self.live_clients = {}
        self.live_watcher = None
        self.live_event_feed = None
        self.live_watchers = {}
        self.live_event_feeds = {}
        self._live_start_retry_attempt = 0
        self._live_start_retry_after_id = None
        self.live_status_var = tk.StringVar(value="LIVE: waiting for analysis")
        self.repo_id_var = tk.StringVar(value="Repo ID: unregistered")
        self._live_status_queue: Queue[str] = Queue()
        self._live_status_draining = False
        self.last_live_state: dict[str, Any] | None = None

        cache_cleanup = prune_startup_caches()
        if any(section["errors"] for section in cache_cleanup.values()):
            self.live_status_var.set("LIVE: cache cleanup incomplete")

        self._check_stale_excludes()
        self._build_ui()

        if self.repo_path_var.get() and Path(self.repo_path_var.get()).is_dir():
            self.root.after_idle(lambda: self._start_live_watcher(self.repo_path_var.get()))

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
        self.container.rowconfigure(4, weight=1)

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

        self.cmd_log_checkbox = ttk.Checkbutton(
            title_frame,
            text="Open CMD log",
            variable=self.cmd_var,
            command=self._toggle_cmd_log,
        )
        self.cmd_log_checkbox.pack(side="left", padx=(20, 0))

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
            self.cmd_log_checkbox,
            "Open a separate CMD window with low-volume technical logs from the whole program.",
        )
        self.tooltip.bind_tooltip(
            self.test_suite_btn,
            "Run Contextor's complete test suite, including LIVE tests.",
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
        live_status_row = ttk.Frame(self.container)
        live_status_row.grid(
            row=1, column=0, sticky="ew", padx=(PAD_MD, PAD_MD), pady=(0, PAD_SM)
        )
        live_status_row.columnconfigure(0, weight=1)

        self.live_status_label = ttk.Label(
            live_status_row,
            textvariable=self.live_status_var,
            style="Cpu.TLabel",
            anchor="w",
        )
        self.live_status_label.grid(row=0, column=0, sticky="ew")
        self.tooltip.bind_tooltip(
            self.live_status_label,
            "LIVE status bar: desktop watcher activity and the latest shared canonical LIVE update.",
        )
        self.repo_id_label = ttk.Label(
            live_status_row,
            textvariable=self.repo_id_var,
            style="Cpu.TLabel",
            anchor="e",
        )
        self.repo_id_label.grid(row=0, column=1, sticky="e", padx=(PAD_MD, 0))
        self.tooltip.bind_tooltip(
            self.repo_id_label,
            "Durable repository ID binding the selected root, registry, snapshots and canonical LIVE state.",
        )

        project_section = ttk.Labelframe(
            self.container, text="Project", padding=(PAD_MD, PAD_SM, PAD_MD, PAD_MD)
        )
        project_section.grid(row=2, column=0, sticky="ew")
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
        actions_section.grid(row=3, column=0, sticky="ew", pady=(PAD_LG, 0))
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
        progress_section.grid(row=4, column=0, sticky="nsew", pady=(PAD_LG, 0))
        progress_section.columnconfigure(0, weight=1)

        self.progress_bar = create_progress_bar(progress_section)
        self.cpu_indicator = create_cpu_indicator(progress_section)
        self.log_box = create_log_box(progress_section, height=8)
        self.log_box.configure(relief="flat", borderwidth=0)
        self.log_box.pack(before=self.progress_bar, fill="x", padx=10, pady=(0, 5))

    def _toggle_cmd_log(self):
        """Toggle the separate CMD tail for the whole Contextor process."""

        if self.cmd_var.get():
            configure_program_log()
            if not open_cmd_log():
                self.cmd_var.set(False)
        else:
            close_cmd_log()

    def _setup_toolbar(self):
        """
        Builds the bottom toolbar providing access to auxiliary
        windows: Output Folder, Exclude Editor, Repo Builder, JSON Parser.
        """
        ttk.Separator(self.container).grid(row=5, column=0, sticky="ew", pady=(PAD_MD, PAD_SM))
        bottom_frame = ttk.Frame(self.container)
        bottom_frame.grid(row=6, column=0, sticky="ew")

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
            self._start_live_watcher(directory)

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

    def _run_test_suite(self):
        """
        Runs the selected Contextor test suite and reports the outcome.
        """

        suite_title = "Test suite"

        def task(log=None, progress_callback=None):
            return run_test_suite(
                log=log,
                progress_callback=progress_callback,
                live_only=False,
            )

        def on_success(result):
            summary = format_summary(result)

            if result["exit_code"] == 0 and result["total"] > 0:
                messagebox.showinfo(
                    f"{suite_title} passed",
                    f"All {result['passed']} tests passed.\n\n{summary}",
                )
                return

            messagebox.showwarning(f"{suite_title} failed", summary)

        def on_error(exc):
            if isinstance(exc, TestSuiteUnavailable):
                messagebox.showwarning(f"{suite_title} unavailable", str(exc))
                return
            messagebox.showerror(suite_title, str(exc))

        def on_cancel():
            messagebox.showinfo(suite_title, "Test run cancelled.")

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

    def run_test_suite(self):
        """Runs every test, including the canonical LIVE suite."""

        self._run_test_suite()

    def analyze(self):
        path = self.repo_path_var.get()
        if not path:
            messagebox.showwarning(
                "Missing repository", "Please select ROOT directory of scanned project"
            )
            return

        pre_seq = 0
        try:
            from pathlib import Path
            from contextor.core.live_state import connect
            live_client = connect(Path(path))
            if live_client is not None:
                resp = live_client.get_events(limit=1)
                pre_seq = int(resp.get("latest_seq", 0))
        except Exception:
            pre_seq = 0

        def task(log=None, progress_callback=None):
            errors, _ = ContextorFacade.analyze_project(
                path, log=log, progress_callback=progress_callback
            )
            return errors

        def on_success(errors):
            self._start_live_watcher(path, initial_seq=pre_seq)
            if getattr(self, "live_event_feed", None) is not None:
                self.live_event_feed.poll_once()
            if not errors:
                messagebox.showinfo("OK", "No issues found. Repository is healthy!")
                return
            msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
            messagebox.showwarning("Issues Detected", msg)

        def on_error(exc):
            self._set_live_status(f"Repository analysis failed: {exc}", category="LIVE_STATE")
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
            operation_name="Repository analysis",
        )

    def _set_live_status(
        self,
        message: str,
        *,
        category: str = "LIVE_STATE",
        event: dict | None = None,
    ):
        """Append one status to the shared GUI queue, never overwriting a peer event."""
        if not hasattr(self, "live_status_var"):
            return

        if not (message.startswith("[LIVE]") or message.startswith("[MCP]")):
            prefix = "[MCP] " if category == "MCP_CALL" else "[LIVE] "
            message = f"{prefix}{message}"

        time_str = ""
        if isinstance(event, dict) and event.get("timestamp"):
            try:
                dt = datetime.fromisoformat(event["timestamp"])
                if dt.tzinfo is not None:
                    dt = dt.astimezone()
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = datetime.now().strftime("%H:%M:%S")
        else:
            time_str = datetime.now().strftime("%H:%M:%S")

        formatted = f"{message}  {time_str}"

        if category == "LIVE_STATE" and isinstance(event, dict):
            self.last_live_state = {
                "revision": event.get("canonical_revision"),
                "status": event.get("status"),
                "timestamp": event.get("timestamp"),
                "source": event.get("source") or event.get("origin"),
            }

        item = {
            "formatted": formatted,
            "category": category,
            "event": event,
            "message": message,
        }

        self._live_status_queue.put(item)
        if threading.current_thread() is threading.main_thread():
            if hasattr(self, "_drain_live_status_queue"):
                self._drain_live_status_queue()
        elif hasattr(self, "root") and hasattr(self.root, "after"):
            self.root.after(0, self._drain_live_status_queue)

    def _drain_live_status_queue(self):
        """Display queued desktop and MCP messages one at a time on Tk's thread."""
        if getattr(self, "_live_status_draining", False):
            return
        try:
            item = self._live_status_queue.get_nowait()
        except Empty:
            return
        self._live_status_draining = True
        display_text = item["formatted"] if isinstance(item, dict) else str(item)
        self.live_status_var.set(display_text)

        def next_message():
            self._live_status_draining = False
            self._drain_live_status_queue()

        if hasattr(self, "root") and hasattr(self.root, "after"):
            self.root.after(1250, next_message)
        else:
            self._live_status_draining = False

    def _start_live_watcher(self, path, initial_seq: int | None = None):
        """Connect and retain one independent LIVE watcher per repository ID."""
        try:
            identity = ContextorGUI._refresh_repo_identity(self, path)
        except RepositoryIdentityError as exc:
            self._set_live_status(f"LIVE identity error: {exc}")
            return
        if identity is None:
            self._set_live_status("LIVE: repository not registered; run an analysis")
            return
        watchers = getattr(self, "live_watchers", None)
        if watchers is None:
            watchers = self.live_watchers = {}
        feeds = getattr(self, "live_event_feeds", None)
        if feeds is None:
            feeds = self.live_event_feeds = {}
        clients = getattr(self, "live_clients", None)
        if clients is None:
            clients = self.live_clients = {}

        existing_watcher = watchers.get(identity.repo_id)
        if existing_watcher is not None:
            self.live_watcher = existing_watcher
            self.live_event_feed = feeds.get(identity.repo_id)
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
            if hasattr(self.live_event_feed, "poll_once"):
                self.live_event_feed.poll_once()
            return

        try:
            from contextor.core.live_state import migrate_legacy_snapshot
            from contextor.core.paths import repo_cache_dir

            cache = migrate_legacy_snapshot(path)
            client = connect_or_start(
                path,
                owner_pid=os.getpid(),
                owner_token=getattr(self, "owner_token", None),
            )
            self.live_client = client
            clients[identity.repo_id] = client
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
        except (OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError) as exc:
            current_attempt = getattr(self, "_live_start_retry_attempt", 0) + 1
            self._live_start_retry_attempt = current_attempt
            if current_attempt < LIVE_START_MAX_ATTEMPTS:
                delay_idx = min(current_attempt - 1, len(LIVE_START_RETRY_DELAYS_MS) - 1)
                delay_ms = LIVE_START_RETRY_DELAYS_MS[delay_idx]
                self._set_live_status(
                    f"LIVE connection delayed; retrying ({current_attempt + 1}/{LIVE_START_MAX_ATTEMPTS})..."
                )
                if hasattr(self, "root") and hasattr(self.root, "after"):
                    self._live_start_retry_after_id = self.root.after(
                        delay_ms, lambda: ContextorGUI._start_live_watcher(self, path, initial_seq=initial_seq)
                    )
                return
            self._live_start_retry_attempt = 0
            self._live_start_retry_after_id = None
            self._set_live_status(f"LIVE connection error: {exc}")
            return

        from contextor.core.analysis.state_manager import load_engine_state

        state = load_engine_state(
            str(cache),
            "",
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )
        if state is not None:
            client.publish(state, origin="desktop_analysis")
            self._set_live_status("LIVE: shared state published; watcher active")
        else:
            self._set_live_status("LIVE: no snapshot; waiting for analysis")
        existing_watcher = watchers.get(identity.repo_id)
        if existing_watcher is not None:
            self.live_watcher = existing_watcher
            self.live_event_feed = feeds.get(identity.repo_id)
            if hasattr(self.live_event_feed, "poll_once"):
                self.live_event_feed.poll_once()
            return

        def status_callback(message, event=None, name=identity.repo_name):
            if event is None and (message.startswith("LIVE update successful:") or message.startswith("Updating LIVE:")):
                return
            cat = event.get("category", "LIVE_STATE") if isinstance(event, dict) else "LIVE_STATE"
            if message.startswith("[LIVE] "):
                body = message[7:]
                msg = f"[LIVE] [{name}] {body}"
            elif message.startswith("[MCP] "):
                body = message[6:]
                msg = f"[MCP] [{name}] {body}"
            else:
                msg = f"[{name}] {message}"
            self._set_live_status(msg, category=cat, event=event)

        def on_reconnect(new_client):
            self.live_client = new_client
            self.live_clients[identity.repo_id] = new_client
            feed = feeds.get(identity.repo_id)
            if feed is not None:
                feed.client = new_client

        self.live_watcher = DesktopLiveWatcher(
            path,
            client,
            owner_pid=os.getpid(),
            owner_token=getattr(self, "owner_token", None),
            on_status=status_callback,
            on_reconnect=on_reconnect,
        )
        if initial_seq is not None:
            self.live_event_feed = DesktopLiveEventFeed(client, status_callback, initial_seq=initial_seq)
        else:
            self.live_event_feed = DesktopLiveEventFeed(client, status_callback)
        watchers[identity.repo_id] = self.live_watcher
        feeds[identity.repo_id] = self.live_event_feed
        self.live_watcher.start()
        self.live_event_feed.start()
        if hasattr(self.live_event_feed, "poll_once"):
            self.live_event_feed.poll_once()

    def _refresh_repo_identity(self, path):
        """Refresh the permanent repository identity shown beside LIVE status."""

        try:
            identity = read_repository_identity(path)
        except RepositoryIdentityError:
            self.repo_id_var.set("Repo ID: invalid")
            raise
        self.repo_id_var.set(
            f"Repo ID: {identity.repo_id}" if identity else "Repo ID: unregistered"
        )
        return identity

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

        if (
            not root_resolved.is_dir()
            or not layer_resolved.is_dir()
            or layer_resolved == root_resolved
            or root_resolved not in layer_resolved.parents
        ):
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
            self._start_live_watcher(str(root_resolved))
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
            operation_name="Layer analysis",
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

        try:
            root_resolved = Path(repo_root).resolve()
            file_resolved = Path(file_path).resolve()
        except (OSError, RuntimeError):
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return
        if (
            not root_resolved.is_dir()
            or not file_resolved.is_file()
            or root_resolved not in file_resolved.parents
        ):
            messagebox.showwarning(
                "Invalid file",
                "Selected Python file must be inside the selected repository root.\n"
                f"Repository root:\n{root_resolved}",
            )
            return

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_single_file(
                str(file_resolved), str(root_resolved), log=log, progress_callback=progress_callback
            )

        def on_success(output):
            self._start_live_watcher(str(root_resolved))
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
            operation_name="Single-file analysis",
        )

    def open_output_folder(self):
        handle_open_output_folder()

    def empty_output_folder(self):
        handle_empty_output_folder()

    def on_closing(self):
        import re
        import time

        close_cmd_log()

        if getattr(self, "_live_start_retry_after_id", None) is not None:
            if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                try:
                    self.root.after_cancel(self._live_start_retry_after_id)
                except Exception:
                    pass
            self._live_start_retry_after_id = None
        self._live_start_retry_attempt = 0

        watchers = list(getattr(self, "live_watchers", {}).values())
        feeds = list(getattr(self, "live_event_feeds", {}).values())
        for watcher in watchers:
            watcher.stop()
        for feed in feeds:
            feed.stop()

        clients = list(getattr(self, "live_clients", {}).values())
        live_client = getattr(self, "live_client", None)
        if live_client is not None and live_client not in clients:
            clients.append(live_client)

        gui_owner_token = getattr(self, "owner_token", None)
        for client in clients:
            is_owner = getattr(client, "is_owner", False)
            client_token = getattr(client, "owner_token", None)
            service_pid = getattr(client, "service_pid", None)

            can_shutdown = (
                is_owner is True
                and gui_owner_token is not None
                and client_token is not None
                and client_token == gui_owner_token
                and service_pid is not None
            )
            if not can_shutdown:
                continue

            try:
                client.request("shutdown", timeout=1.5)
            except Exception:
                pass
            if service_pid is not None:
                from contextor.core.live_state.runtime import _is_pid_alive, _terminate_pid_tree

                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    if not _is_pid_alive(service_pid):
                        break
                    time.sleep(0.05)
                if _is_pid_alive(service_pid):
                    _terminate_pid_tree(service_pid)

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