"""
ui/gui.py

Core presentation layer. ContextorGUI manages root Tkinter window,
state persistence, sub-windows and orchestrates the analysis process.
"""

import os
import threading
import time
import tkinter as tk
import uuid
from datetime import datetime
from queue import Empty, Queue
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from contextor.core.analysis.full_analysis_coordinator import (
    FullAnalysisBusyError,
    acquire_full_analysis,
    release_full_analysis,
    run_full_analysis_exclusive,
)
from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state import (
    DesktopLiveEventFeed,
    DesktopLiveWatcher,
    SecondDesktopActive,
    connect_or_start,
    connect,
    migrate_legacy_snapshot,
)
from contextor.core.live_state.watcher import RECOVERY_DEFERRED
from contextor.core.repository_identity import (
    RepositoryIdentityError,
    read_repository_identity,
)
from contextor.core.paths import prune_startup_caches
from contextor.repo_generator import run_repo_generator
from contextor.mcp_backend_control import (
    BackendOwnerAlreadyClaimed,
    BackendOwnerInstanceRevoked,
    claim_backend_owner,
    get_backend_status,
    start_backend,
    stop_backend,
)
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
from contextor.ui.system_actions import (
    handle_empty_output_folder,
    handle_open_output_folder,
    handle_open_runtime_logs_folder,
)
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
FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS = 1.5
BACKEND_OWNER_CLAIM_MAX_ATTEMPTS = 3
BACKEND_OWNER_CLAIM_RETRY_DELAYS_SECONDS = (
    0.5,
    1.0,
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
        self._selected_live_repo_path = self.repo_path_var.get()
        self._repo_path_trace_id = self.repo_path_var.trace_add(
            "write",
            self._sync_selected_live_repository_path,
        )

        self.exclude_win = None
        self.repo_builder_win = None
        self.parser_win = None
        self.owner_token = uuid.uuid4().hex
        self.desktop_instance_id = uuid.uuid4().hex
        self.backend_owner_token = uuid.uuid4().hex
        self.backend_owner_claim = None
        self._backend_owner_claim_error = None
        self._backend_owner_claim_thread = None
        self._backend_owner_claim_state = "idle"
        self._backend_owner_claim_attempt = 0
        self.live_client = None
        self.live_clients = {}
        self.live_watcher = None
        self.live_event_feed = None
        self.live_watchers = {}
        self.live_event_feeds = {}
        self._live_start_retry_attempt = 0
        self._live_start_retry_after_id = None
        self._live_recovery_after_id = None
        self.live_status_var = tk.StringVar(value="LIVE: waiting for analysis")
        self.repo_id_var = tk.StringVar(value="Repo ID: unregistered")
        self._live_status_queue: Queue[str] = Queue()
        self._live_status_draining = False
        self._live_recovery_queue: Queue[tuple[str, str]] = Queue()
        self._live_recovery_prompt_pending: set[str] = set()
        self._live_recovery_lock = threading.Lock()
        self._live_recovery_incidents: dict[str, dict[str, Any]] = {}
        self._live_recovery_generations: dict[str, int] = {}
        self.last_live_state: dict[str, Any] | None = None

        self._closing = False
        self._live_start_lock = threading.Lock()
        self._live_start_inflight: set[str] = set()
        self._live_start_threads: dict[str, threading.Thread] = {}
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, self._start_post_paint_tasks)
        self._live_recovery_after_id = self.root.after(
            100, self._drain_live_recovery_queue
        )

    def _claim_current_backend_for_desktop(self):
        claim = claim_backend_owner(
            host_owner_identity=self.desktop_instance_id,
            host_kind="desktop",
            owner_token=self.backend_owner_token,
            probe_timeout=2.0,
            lock_timeout=5.0,
        )

        self.backend_owner_claim = claim
        self._backend_owner_claim_error = None

        return claim

    def _claim_backend_owner_on_startup(self):
        status = start_backend(
            timeout=20.0,
            probe_timeout=2.0,
        )

        if (
            not status.ready
            or status.record is None
        ):
            raise RuntimeError(
                "persistent MCP backend did not become authenticated and ready"
            )

        try:
            claim = self._claim_current_backend_for_desktop()

        except BackendOwnerInstanceRevoked:
            deadline = time.monotonic() + 5.0

            while time.monotonic() < deadline:
                current = get_backend_status(
                    probe_timeout=0.5,
                )

                if (
                    current.state == "stopped"
                    and current.ready is False
                    and current.record is None
                ):
                    break

                time.sleep(0.05)

            else:
                raise RuntimeError(
                    "revoked persistent MCP backend did not self-terminate before timeout"
                )

            replacement = start_backend(
                timeout=20.0,
                probe_timeout=2.0,
            )

            if (
                not replacement.ready
                or replacement.record is None
            ):
                raise RuntimeError(
                    "replacement persistent MCP backend did not become authenticated and ready"
                )

            claim = self._claim_current_backend_for_desktop()

            if claim.backend_instance_id != replacement.record.instance_id:
                raise RuntimeError(
                    "Desktop backend owner claim does not match replacement backend instance"
                )

            return claim

        if claim.backend_instance_id != status.record.instance_id:
            raise RuntimeError(
                "Desktop backend owner claim does not match active backend instance"
            )

        return claim

    def _start_backend_owner_claim(self):
        if getattr(self, "_closing", False):
            return

        current_thread = getattr(
            self,
            "_backend_owner_claim_thread",
            None,
        )

        if (
            current_thread is not None
            and current_thread.is_alive()
        ):
            return

        def worker():
            self._backend_owner_claim_state = "claiming"
            self._backend_owner_claim_attempt = 0

            for attempt in range(
                1,
                BACKEND_OWNER_CLAIM_MAX_ATTEMPTS + 1,
            ):
                if getattr(self, "_closing", False):
                    self._backend_owner_claim_state = "aborted"
                    return

                self._backend_owner_claim_attempt = attempt

                try:
                    claim = self._claim_backend_owner_on_startup()

                except Exception as exc:
                    self._backend_owner_claim_error = exc

                    terminal = (
                        isinstance(
                            exc,
                            BackendOwnerAlreadyClaimed,
                        )
                        or attempt
                        >= BACKEND_OWNER_CLAIM_MAX_ATTEMPTS
                    )

                    if terminal:
                        self._backend_owner_claim_state = "failed"

                        self._set_live_status(
                            f"Backend ownership failed: {exc}",
                            category="MCP_CALL",
                        )
                        return

                    self._backend_owner_claim_state = "retrying"

                    self._set_live_status(
                        (
                            "Backend ownership unavailable; "
                            f"retrying ({attempt + 1}/"
                            f"{BACKEND_OWNER_CLAIM_MAX_ATTEMPTS})..."
                        ),
                        category="MCP_CALL",
                    )

                    delay = (
                        BACKEND_OWNER_CLAIM_RETRY_DELAYS_SECONDS[
                            attempt - 1
                        ]
                    )

                    deadline = time.monotonic() + delay

                    while time.monotonic() < deadline:
                        if getattr(self, "_closing", False):
                            self._backend_owner_claim_state = "aborted"
                            return

                        remaining = deadline - time.monotonic()

                        time.sleep(
                            min(
                                0.05,
                                max(0.0, remaining),
                            )
                        )

                    self._backend_owner_claim_state = "claiming"
                    continue

                self.backend_owner_claim = claim
                self._backend_owner_claim_error = None
                self._backend_owner_claim_state = "claimed"

                if attempt > 1:
                    self._set_live_status(
                        "Backend ownership restored.",
                        category="MCP_CALL",
                    )

                return

        thread = threading.Thread(
            target=worker,
            name="contextor-backend-owner-claim",
            daemon=True,
        )

        self._backend_owner_claim_thread = thread
        thread.start()

    def _start_post_paint_tasks(self):
        if getattr(self, "_closing", False):
            return
        self._start_backend_owner_claim()
        self._set_live_status("LIVE: initializing in background")
        def cleanup_worker():
            try:
                cache_cleanup = prune_startup_caches()
                if any(section["errors"] for section in cache_cleanup.values()):
                    self._set_live_status("LIVE: cache cleanup incomplete")
            except Exception as exc:
                self._set_live_status(f"LIVE: cache cleanup failed: {exc}")
        threading.Thread(target=cleanup_worker, name="contextor-startup-cache-cleanup", daemon=True).start()
        self._check_stale_excludes()
        repo_path = self.repo_path_var.get()
        if repo_path and Path(repo_path).is_dir():
            self._start_live_watcher(repo_path)

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
        if not repo_saved or getattr(self, "_closing", False):
            return
        def worker():
            try:
                conflicts = check_stale_excludes(repo_saved)
            except Exception:
                return
            if not conflicts or getattr(self, "_closing", False):
                return
            def prompt():
                if getattr(self, "_closing", False):
                    return
                if self.repo_path_var.get() != repo_saved:
                    return
                answer = messagebox.askyesno("Outdated exclusions", "Detected files/directories that returned to the repo.\n\nReapply exclusions?\n\n" + "\n".join(conflicts))
                if answer:
                    from contextor.ui.exclude_gui import reapply_excludes
                    reapply_excludes(repo_saved, conflicts)
            try:
                self.root.after(0, prompt)
            except Exception:
                pass
        threading.Thread(target=worker, name="contextor-startup-exclude-check", daemon=True).start()

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

        self.mcp_logs_btn = ttk.Button(
            title_frame,
            text="MCP Logs",
            style="Ghost.TButton",
            command=self.open_mcp_logs,
        )
        self.mcp_logs_btn.pack(side="left", padx=(PAD_SM, 0))

        self.restart_backend_btn = ttk.Button(
            title_frame,
            text="Restart Backend",
            style="Ghost.TButton",
            command=self._restart_backend,
        )
        self.restart_backend_btn.pack(side="left", padx=(PAD_SM, 0))

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
            self.mcp_logs_btn,
            "Open the folder containing LIVE and MCP operation logs.",
        )
        self.tooltip.bind_tooltip(
            self.restart_backend_btn,
            "Stop the current persistent MCP backend and start a fresh instance using the current code on disk.",
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

    def _sync_selected_live_repository_path(self, *_args):
        repo_path_var = getattr(self, "repo_path_var", None)
        if repo_path_var is None or not hasattr(repo_path_var, "get"):
            self._selected_live_repo_path = ""
            return
        self._selected_live_repo_path = repo_path_var.get()
        selected = self._selected_live_repo_path
        if selected:
            try:
                repository_key = str(Path(selected).expanduser().resolve())
            except (OSError, ValueError):
                repository_key = str(selected)
            with self._live_recovery_lock:
                incident = self._live_recovery_incidents.get(repository_key)
                if incident is not None and repository_key not in self._live_recovery_prompt_pending:
                    self._live_recovery_prompt_pending.add(repository_key)
                    self._live_recovery_queue.put((repository_key, incident["reason"]))

    def _live_recovery_incident(self, repository_path: str) -> dict[str, Any] | None:
        try:
            repository_key = str(Path(repository_path).expanduser().resolve())
        except (OSError, ValueError):
            repository_key = str(repository_path)
        with self._live_recovery_lock:
            incident = self._live_recovery_incidents.get(repository_key)
            return dict(incident) if incident is not None else None

    def _set_live_recovery_verification_state(
        self, repository_path: str, generation: int, state: str
    ) -> bool:
        try:
            repository_key = str(Path(repository_path).expanduser().resolve())
        except (OSError, ValueError):
            repository_key = str(repository_path)
        with self._live_recovery_lock:
            incident = self._live_recovery_incidents.get(repository_key)
            if incident is None or incident.get("generation") != generation:
                return False
            incident["verification_state"] = state
            return True

    def _watcher_recovery_admission(self, repository_path: str):
        try:
            repository_key = str(Path(repository_path).expanduser().resolve())
        except (OSError, ValueError):
            repository_key = str(repository_path)

        def admit(submission_callable):
            with self._live_recovery_lock:
                if repository_key in self._live_recovery_incidents:
                    return RECOVERY_DEFERRED
                return submission_callable()

        return admit

    def _is_selected_live_repository(self, path):
        if not hasattr(self, "_selected_live_repo_path"):
            return True
        selected = self._selected_live_repo_path
        if not selected:
            return False
        try:
            return Path(selected).expanduser().resolve() == Path(path).expanduser().resolve()
        except Exception:
            return str(selected).replace("\\", "/") == str(path).replace("\\", "/")

    def _discard_pending_live_statuses(self):
        queue = getattr(self, "_live_status_queue", None)
        if queue is None:
            return
        while True:
            try:
                queue.get_nowait()
            except Empty:
                return

    def browse_repository(self):
        directory = filedialog.askdirectory()
        if directory:
            directory = directory.replace("\\", "/")
            self.repo_path_var.set(directory)
            self._selected_live_repo_path = directory
            self.layer_path_var.set("")
            save_state(repository=directory)
            ContextorGUI._discard_pending_live_statuses(self)
            self._set_live_status(f"LIVE: switching to {Path(directory).name}")
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
            self.restart_backend_btn,
        ]

    def _restart_backend(self):
        """
        Restart the persistent MCP backend without blocking the Tk main loop.
        """

        operation_title = "Restart Backend"

        def _identity(status):
            record = status.record
            if record is None:
                return None

            return (
                record.instance_id,
                record.pid,
                record.creation_time,
            )

        def task(log=None, progress_callback=None):
            before = get_backend_status(
                probe_timeout=2.0,
            )
            before_identity = _identity(before)

            stop_backend(
                timeout=5.0,
            )

            stopped = get_backend_status(
                probe_timeout=0.5,
            )

            if (
                stopped.state != "stopped"
                or stopped.ready
                or stopped.record is not None
            ):
                raise RuntimeError(
                    "persistent MCP backend did not reach a confirmed stopped state"
                )

            after = start_backend(
                timeout=20.0,
                probe_timeout=2.0,
            )

            if not after.ready or after.record is None:
                raise RuntimeError(
                    "new persistent MCP backend did not become authenticated and ready"
                )

            after_identity = _identity(after)

            if (
                before_identity is not None
                and after_identity == before_identity
            ):
                raise RuntimeError(
                    "backend restart returned the previous backend process identity"
                )

            new_owner_claim = claim_backend_owner(
                host_owner_identity=self.desktop_instance_id,
                host_kind="desktop",
                owner_token=self.backend_owner_token,
                probe_timeout=2.0,
                lock_timeout=5.0,
            )

            if new_owner_claim.backend_instance_id != after.record.instance_id:
                raise RuntimeError(
                    "Desktop backend owner claim does not match restarted backend instance"
                )

            return before, after, new_owner_claim

        def on_success(result):
            before, after, new_owner_claim = result

            self.backend_owner_claim = new_owner_claim
            self._backend_owner_claim_error = None

            old_pid = (
                "none"
                if before.record is None
                else str(before.record.pid)
            )
            old_instance = (
                "none"
                if before.record is None
                else before.record.instance_id
            )

            messagebox.showinfo(
                "MCP backend restarted",
                (
                    "Persistent MCP backend restarted successfully.\n\n"
                    f"Old PID: {old_pid}\n"
                    f"Old instance: {old_instance}\n"
                    f"New PID: {after.record.pid}\n"
                    f"New instance: {after.record.instance_id}\n"
                    f"Endpoint: {after.endpoint}"
                ),
            )

        def on_error(exc):
            messagebox.showerror(
                operation_title,
                f"Backend restart failed.\n\n{exc}",
            )

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

    def _request_full_analysis_recovery(
        self,
        repository_path: str,
        reason: str,
        *,
        publication_revision: int | None = None,
        publication_outcome: str | None = None,
        queue_prompt: bool = True,
    ) -> int | None:
        """Queue a confirmed recovery incident without calling Tk."""
        if getattr(self, "_closing", False):
            return None

        try:
            repository_key = str(
                Path(repository_path).expanduser().resolve()
            )
        except (OSError, ValueError):
            repository_key = str(repository_path)

        if not repository_key:
            return None

        lock = getattr(self, "_live_recovery_lock", None)
        if lock is None:
            return None

        with lock:
            incidents = getattr(self, "_live_recovery_incidents", None)
            if incidents is None:
                incidents = self._live_recovery_incidents = {}
            generations = getattr(self, "_live_recovery_generations", None)
            if generations is None:
                generations = self._live_recovery_generations = {}
            generation = generations.get(repository_key, 0) + 1
            generations[repository_key] = generation
            incident = {
                "generation": generation,
                "reason": str(reason),
                "required": True,
                "verification_state": "required",
            }
            if (
                isinstance(publication_revision, int)
                and not isinstance(publication_revision, bool)
                and publication_revision > 0
            ):
                incident["publication_revision"] = publication_revision
            if publication_outcome in {"accepted", "rejected"}:
                incident["publication_outcome"] = publication_outcome
            incidents[repository_key] = incident
            pending = self._live_recovery_prompt_pending
            if queue_prompt and repository_key not in pending:
                pending.add(repository_key)
                self._live_recovery_queue.put((repository_key, str(reason)))
            return generation

    def _drain_live_recovery_queue(self) -> None:
        """Process recovery dialogs exclusively on the Tk event loop."""
        self._live_recovery_after_id = None
        if getattr(self, "_closing", False):
            return

        try:
            repository_key, reason = (
                self._live_recovery_queue.get_nowait()
            )
        except Empty:
            pass
        else:
            with self._live_recovery_lock:
                incident = self._live_recovery_incidents.get(repository_key)
                if incident is None:
                    self._live_recovery_prompt_pending.discard(
                        repository_key
                    )
                else:
                    reason = incident["reason"]
            if incident is None:
                pass
            elif not ContextorGUI._is_selected_live_repository(
                self, repository_key
            ):
                with self._live_recovery_lock:
                    self._live_recovery_prompt_pending.discard(
                        repository_key
                    )
            else:
                self._set_live_status(
                    "LIVE: recovery required; incremental updates are deferred."
                )
                try:
                    run_analysis = messagebox.askyesno(
                        "Contextor — Recovery Required",
                        (
                            "A potential inconsistency has been detected "
                            "in the repository's canonical LIVE state.\n\n"
                            "A full repository analysis is recommended "
                            "to restore a consistent architectural baseline.\n\n"
                            "Incremental LIVE updates may be unreliable "
                            "until recovery is complete.\n\n"
                            f"Repository: {repository_key}\n\n"
                            f"Reason: {reason}\n\n"
                            "Run a full repository analysis now?"
                        ),
                        parent=self.root,
                    )
                except Exception:
                    with self._live_recovery_lock:
                        self._live_recovery_prompt_pending.discard(
                            repository_key
                        )
                    raise

                with self._live_recovery_lock:
                    incident = self._live_recovery_incidents.get(repository_key)
                    generation = incident["generation"] if incident else None
                if run_analysis:
                    self.analyze(
                        recovery_repository=repository_key,
                        recovery_generation=generation,
                    )
                else:
                    with self._live_recovery_lock:
                        self._live_recovery_prompt_pending.discard(
                            repository_key
                        )

        finally:
            if not getattr(self, "_closing", False):
                self._live_recovery_after_id = self.root.after(
                    100, self._drain_live_recovery_queue
                )

    def analyze(
        self,
        *,
        recovery_repository: str | None = None,
        recovery_generation: int | None = None,
    ):
        path = recovery_repository or self.repo_path_var.get()
        if not path:
            messagebox.showwarning(
                "Missing repository", "Please select ROOT directory of scanned project"
            )
            return

        try:
            path = str(Path(path).expanduser().resolve())
        except (OSError, ValueError):
            pass
        starting_incident = self._live_recovery_incident(path)
        starting_generation = (
            starting_incident.get("generation")
            if starting_incident is not None
            else None
        )
        if (
            recovery_generation is not None
            and starting_generation != recovery_generation
        ):
            return
        if recovery_generation is not None:
            self._set_live_recovery_verification_state(
                path, recovery_generation, "full_analysis"
            )

        pre_seq = 0
        try:
            from contextor.core.live_state import connect
            live_client = connect(Path(path))
            if live_client is not None:
                resp = live_client.get_events(limit=1)
                pre_seq = int(resp.get("latest_seq", 0))
        except Exception:
            pre_seq = 0

        def task(log=None, progress_callback=None):
            errors, analysis_result = run_full_analysis_exclusive(
                path,
                owner="desktop_analysis",
                log=log,
                progress_callback=progress_callback,
                is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
            )
            return errors, analysis_result

        def on_success(outcome):
            errors, analysis_result = outcome
            incident_before_publish_result = self._live_recovery_incident(path)
            analysis_recovery_generation = None
            if getattr(analysis_result, "live_publish_status", None) == "recovery_required":
                analysis_recovery_generation = self._request_full_analysis_recovery(
                    path,
                    getattr(analysis_result, "live_publish_warning", None)
                    or "Canonical LIVE publish requires recovery verification.",
                    publication_revision=getattr(
                        analysis_result, "live_publish_revision", None
                    ),
                    publication_outcome="accepted",
                    queue_prompt=False,
                )
            current_incident = self._live_recovery_incident(path)
            if current_incident is None:
                self._start_live_watcher(path, initial_seq=pre_seq)
                if not errors:
                    messagebox.showinfo("OK", "No issues found. Repository is healthy!")
                    return
                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
                messagebox.showwarning("Issues Detected", msg)
                return

            self._start_live_watcher(path, initial_seq=pre_seq)
            generation = None
            if (
                analysis_recovery_generation is not None
                and current_incident["generation"] == analysis_recovery_generation
                and (
                    (
                        incident_before_publish_result is None
                        and starting_generation is None
                    )
                    or (
                        incident_before_publish_result is not None
                        and incident_before_publish_result.get("generation")
                        == starting_generation
                    )
                )
            ):
                generation = analysis_recovery_generation
            elif (
                analysis_recovery_generation is None
                and starting_generation is not None
                and current_incident["generation"] == starting_generation
            ):
                generation = starting_generation
            if generation is None:
                self._set_live_status(
                    "LIVE recovery verification failed; full repository analysis may be required."
                )
                if errors:
                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
                    messagebox.showwarning("Issues Detected", msg)
                else:
                    messagebox.showinfo(
                        "Analysis complete",
                        "No static issues found. LIVE recovery verification failed; "
                        "full repository analysis may be required.",
                    )
                return

            self._set_live_recovery_verification_state(
                path, generation, "verifying"
            )

            verification_client = None
            try:
                verification_client = connect(Path(path))
                if verification_client is None:
                    verification = {"status": "error", "error": "recovery_live_missing"}
                else:
                    verification = verification_client.verify_recovery(generation)
            except Exception as exc:
                verification = {
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }

            certificate = verification.get("certificate") if isinstance(verification, dict) else None
            try:
                identity = read_repository_identity(path)
            except Exception:
                identity = None
            cert_valid = (
                isinstance(verification, dict)
                and verification.get("status") == "ok"
                and isinstance(certificate, dict)
                and certificate.get("incident_generation") == generation
                and identity is not None
                and certificate.get("repo_id") == identity.repo_id
                and certificate.get("root_path") == str(Path(identity.root_path).resolve())
                and isinstance(certificate.get("revision"), int)
                and not isinstance(certificate.get("revision"), bool)
                and certificate.get("revision", 0) > 0
                and isinstance(certificate.get("state_id"), str)
                and bool(certificate.get("state_id"))
            )
            cleared = False
            if cert_valid:
                with self._live_recovery_lock:
                    latest = self._live_recovery_incidents.get(path)
                    if latest is not None and latest.get("generation") == generation:
                        try:
                            completed = verification_client.complete_recovery_verification(
                                certificate["certificate_id"], generation
                            )
                        except Exception as exc:
                            completed = {"status": "error", "error": str(exc)}
                        if (
                            isinstance(completed, dict)
                            and completed.get("status") == "ok"
                            and completed.get("released") is True
                            and completed.get("certificate_id")
                            == certificate["certificate_id"]
                            and completed.get("incident_generation") == generation
                        ):
                            watcher = self.live_watchers.get(identity.repo_id)
                            if watcher is not None:
                                watcher.complete_recovery_certificate()
                            del self._live_recovery_incidents[path]
                            self._live_recovery_prompt_pending.discard(path)
                            cleared = True

            if cleared:
                self._set_live_status(
                    "LIVE recovery verified; incremental updates resumed."
                )
                if not errors:
                    messagebox.showinfo("OK", "LIVE recovery verified; incremental updates resumed.")
                else:
                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
                    messagebox.showwarning("Issues Detected", msg)
                return

            if (
                isinstance(certificate, dict)
                and isinstance(certificate.get("certificate_id"), str)
                and verification_client is not None
            ):
                try:
                    verification_client.cancel_recovery_verification(
                        certificate["certificate_id"], generation
                    )
                except Exception:
                    pass
            self._set_live_recovery_verification_state(
                path, generation, "failed"
            )

            self._set_live_status(
                "LIVE recovery verification failed; full repository analysis may be required."
            )
            if not errors:
                messagebox.showinfo(
                    "Analysis complete",
                    "No static issues found. LIVE recovery verification failed; "
                    "full repository analysis may be required.",
                )
            else:
                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
                messagebox.showwarning("Issues Detected", msg)

        def on_error(exc):
            if recovery_generation is not None:
                self._set_live_recovery_verification_state(
                    path, recovery_generation, "analysis_failed"
                )
            self._set_live_status(f"Repository analysis failed: {exc}", category="LIVE_STATE")
            messagebox.showerror("error", str(exc))

        self.progress_bar.is_cancelled = False

        self._full_analysis_done = run_with_progress(
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

        canonical_operation = (
            isinstance(event, dict)
            and event.get("category", category) == "LIVE_STATE"
            and event.get("operation") in {"publish", "update_file"}
        )

        if canonical_operation:
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
            "enqueue_mono": time.monotonic(),
        }

        self._live_status_queue.put(item)
        try:
            from contextor.core.runtime_trace import trace_event
            event_dict = event if isinstance(event, dict) else {}
            trace_event(
                "GUI", "STATUS_QUEUED", op=event_dict.get("trace_op"),
                rev=event_dict.get("canonical_revision") or event_dict.get("revision"),
                seq=event_dict.get("seq"), q=self._live_status_queue.qsize(),
                category=category, status=message[:80],
            )
        except Exception:
            pass
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
        try:
            from contextor.core.runtime_trace import trace_event
            event_dict = item.get("event") if isinstance(item, dict) else {}
            event_dict = event_dict if isinstance(event_dict, dict) else {}
            queued_at = item.get("enqueue_mono") if isinstance(item, dict) else None
            trace_event(
                "GUI", "STATUS_RENDERED", op=event_dict.get("trace_op"),
                rev=event_dict.get("canonical_revision") or event_dict.get("revision"),
                seq=event_dict.get("seq"), q=self._live_status_queue.qsize(),
                wait_ms=(time.monotonic() - queued_at) * 1000.0 if queued_at is not None else None,
            )
        except Exception:
            pass

        def next_message():
            self._live_status_draining = False
            self._drain_live_status_queue()

        if hasattr(self, "root") and hasattr(self.root, "after"):
            self.root.after(1250, next_message)
        else:
            self._live_status_draining = False

    def _start_live_watcher(self, path, initial_seq: int | None = None):
        if getattr(self, "_closing", False):
            return
        try:
            path_key = str(Path(path).expanduser().resolve())
        except Exception:
            path_key = str(path)
        lock = getattr(self, "_live_start_lock", None)
        if lock is None:
            lock = self._live_start_lock = threading.Lock()
        inflight = getattr(self, "_live_start_inflight", None)
        if inflight is None:
            inflight = self._live_start_inflight = set()
        threads = getattr(self, "_live_start_threads", None)
        if threads is None:
            threads = self._live_start_threads = {}
        with lock:
            if getattr(self, "_closing", False) or path_key in inflight:
                return
            inflight.add(path_key)
        def runner():
            try:
                ContextorGUI._start_live_watcher_blocking(self, path, initial_seq=initial_seq)
            finally:
                with lock:
                    inflight.discard(path_key)
                    threads.pop(path_key, None)
        thread = threading.Thread(target=runner, name="contextor-live-desktop-start", daemon=True)
        with lock:
            threads[path_key] = thread
        thread.start()

    def _start_live_watcher_blocking(self, path, initial_seq: int | None = None):
        """Connect and retain one independent LIVE watcher per repository ID."""
        if getattr(self, "_closing", False):
            return
        try:
            identity = ContextorGUI._refresh_repo_identity(self, path)
        except RepositoryIdentityError as exc:
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status(f"LIVE identity error: {exc}")
            return
        if identity is None:
            if ContextorGUI._is_selected_live_repository(self, path):
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
            existing_client = clients.get(identity.repo_id)
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_watcher = existing_watcher
                self.live_event_feed = feeds.get(identity.repo_id)
                if existing_client is not None:
                    self.live_client = existing_client
                if self._live_recovery_incident(path) is None:
                    self._set_live_status(
                        f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
                    )
                else:
                    self._set_live_status(
                        "LIVE: recovery required; incremental updates are deferred."
                    )
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
            return

        try:
            connect_kwargs = {
                "owner_pid": os.getpid(),
                "owner_token": getattr(self, "owner_token", None),
            }
            import inspect

            parameters = inspect.signature(connect_or_start).parameters
            if "desktop_instance_id" in parameters:
                connect_kwargs["desktop_instance_id"] = getattr(self, "desktop_instance_id", None)
            if "client_kind" in parameters:
                connect_kwargs["client_kind"] = "desktop"
            client = connect_or_start(path, **connect_kwargs)
            clients[identity.repo_id] = client
            if getattr(self, "_closing", False):
                return
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_client = client
            cache = migrate_legacy_snapshot(path)
            if getattr(self, "_live_start_retry_after_id", None) is not None:
                if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                    try:
                        self.root.after_cancel(self._live_start_retry_after_id)
                    except Exception:
                        pass
                self._live_start_retry_after_id = None
            self._live_start_retry_attempt = 0
        except SecondDesktopActive as exc:
            self._live_start_retry_attempt = 0
            self._live_start_retry_after_id = None
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status(f"LIVE: {exc}")
            return
        except (OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError) as exc:
            if getattr(self, "_closing", False):
                return
            current_attempt = getattr(self, "_live_start_retry_attempt", 0) + 1
            self._live_start_retry_attempt = current_attempt
            if current_attempt < LIVE_START_MAX_ATTEMPTS:
                delay_idx = min(current_attempt - 1, len(LIVE_START_RETRY_DELAYS_MS) - 1)
                delay_ms = LIVE_START_RETRY_DELAYS_MS[delay_idx]
                if ContextorGUI._is_selected_live_repository(self, path):
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
            if ContextorGUI._is_selected_live_repository(self, path):
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
            current = client.snapshot() if hasattr(client, "snapshot") else {}
            state_revision = getattr(state, "revision", None)
            live_state = current.get("state") if isinstance(current, dict) else None
            live_revision = current.get("revision") if isinstance(current, dict) else None
            state_id = getattr(state, "state_id", None)
            if state_revision is not None and live_revision == int(state_revision):
                if state_id and getattr(live_state, "state_id", None) == state_id:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        if self._live_recovery_incident(path) is None:
                            self._set_live_status("LIVE: shared state attached; watcher active")
                        else:
                            self._set_live_status(
                                "LIVE: recovery required; incremental updates are deferred."
                            )
                else:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        self._set_live_status(
                            "LIVE: generation conflict; analysis required"
                        )
                        self._request_full_analysis_recovery(
                            path,
                            "Canonical state identity mismatch.",
                        )
            else:
                startup_lease = None
                try:
                    startup_lease = acquire_full_analysis(
                        path,
                        owner="desktop_startup_publish",
                        writer_kind="startup_publish",
                        timeout=0.0,
                        poll_interval=0.01,
                    )
                except FullAnalysisBusyError:
                    if ContextorGUI._is_selected_live_repository(self, path):
                        self._set_live_status(
                            "LIVE: canonical writer busy; cache publish skipped"
                        )
                else:
                    try:
                        published = client.publish(
                            state,
                            origin="desktop_analysis",
                        )
                    finally:
                        release_full_analysis(startup_lease)
                    if (
                        isinstance(published, dict)
                        and published.get("resync_required") is True
                    ):
                        outcome = (
                            "accepted" if published.get("status") == "ok"
                            else "rejected"
                        )
                        revision = published.get("revision")
                        self._request_full_analysis_recovery(
                            path,
                            "Canonical LIVE publish requires recovery verification.",
                            publication_revision=revision,
                            publication_outcome=outcome,
                        )
                        if ContextorGUI._is_selected_live_repository(self, path):
                            self._set_live_status(
                                f"LIVE: recovery required after {outcome} publish "
                                f"(revision {revision})"
                            )
                        return
                    if (
                        isinstance(published, dict)
                        and published.get("status") == "ok"
                    ):
                        if ContextorGUI._is_selected_live_repository(self, path):
                            self._set_live_status(
                                "LIVE: shared state published; watcher active"
                            )
                    else:
                        if ContextorGUI._is_selected_live_repository(self, path):
                            self._set_live_status(
                                "LIVE: shared state attach failed; analysis required"
                            )
                            recovery_errors = frozenset({
                                "canonical_persistence_revision_conflict",
                                "canonical_persistence_failed",
                                "canonical_revision_discontinuity",
                                "canonical_revision_changed_during_update",
                            })
                            error_code = (
                                published.get("error")
                                if isinstance(published, dict)
                                else None
                            )
                            if (
                                published.get("resync_required") is True
                                if isinstance(published, dict)
                                else False
                            ) or error_code in recovery_errors:
                                self._request_full_analysis_recovery(
                                    path,
                                    f"Canonical LIVE consistency error: {error_code or 'resync_required'}.",
                                )
        else:
            if ContextorGUI._is_selected_live_repository(self, path):
                self._set_live_status("LIVE: no snapshot; waiting for analysis")
        existing_watcher = watchers.get(identity.repo_id)
        if existing_watcher is not None:
            existing_client = clients.get(identity.repo_id)
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_watcher = existing_watcher
                self.live_event_feed = feeds.get(identity.repo_id)
                if existing_client is not None:
                    self.live_client = existing_client
                incident = self._live_recovery_incident(path)
                if incident is None:
                    self._set_live_status(
                        f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
                    )
                else:
                    self._set_live_status(
                        "LIVE: recovery required; incremental updates are deferred."
                    )
            return

        def status_callback(message, event=None, name=identity.repo_name):
            if not ContextorGUI._is_selected_live_repository(self, path):
                return
            incident = self._live_recovery_incident(path)
            if incident is not None and any(
                marker in message.lower()
                for marker in (
                    "watcher active",
                    "shared state attached",
                    "shared state published",
                )
            ):
                return
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
            self.live_clients[identity.repo_id] = new_client
            if ContextorGUI._is_selected_live_repository(self, path):
                self.live_client = new_client
            feed = feeds.get(identity.repo_id)
            if feed is not None:
                feed.client = new_client

        def on_resync():
            self._request_full_analysis_recovery(
                path,
                "Startup canonical baseline requires full analysis.",
            )
            return False

        if getattr(self, "_closing", False):
            return
        watcher = DesktopLiveWatcher(
            path,
            client,
            owner_pid=os.getpid(),
            owner_token=getattr(self, "owner_token", None),
            desktop_instance_id=getattr(self, "desktop_instance_id", None),
            on_status=status_callback,
            on_reconnect=on_reconnect,
            on_resync=on_resync,
            recovery_admission=self._watcher_recovery_admission(path),
        )
        if initial_seq is not None:
            feed = DesktopLiveEventFeed(
                client,
                status_callback,
                initial_seq=initial_seq,
            )
            if hasattr(feed, "poll_once"):
                feed.poll_once()
        else:
            feed = DesktopLiveEventFeed(
                client,
                status_callback,
            )

        watchers[identity.repo_id] = watcher
        feeds[identity.repo_id] = feed
        if ContextorGUI._is_selected_live_repository(self, path):
            self.live_watcher = watcher
            self.live_event_feed = feed
        if hasattr(feed, "replay_authority_events"):
            feed.replay_authority_events()
        if getattr(self, "_closing", False):
            return
        watcher.start()
        feed.start()
        incident = self._live_recovery_incident(path)
        if incident is not None and ContextorGUI._is_selected_live_repository(self, path):
            self._set_live_status(
                "LIVE: recovery required; incremental updates are deferred."
            )

    def _refresh_repo_identity(self, path):
        """Refresh the permanent repository identity shown beside LIVE status."""
        try:
            identity = read_repository_identity(path)
            label = f"Repo ID: {identity.repo_id}" if identity else "Repo ID: unregistered"
        except RepositoryIdentityError as exc:
            label = "Repo ID: invalid"
            identity = None
            identity_error = exc
        else:
            identity_error = None
        def apply_label():
            if getattr(self, "_closing", False):
                return
            repo_path_var = getattr(self, "repo_path_var", None)
            if repo_path_var is None or repo_path_var.get() == str(path):
                self.repo_id_var.set(label)
        if threading.current_thread() is threading.main_thread():
            apply_label()
        else:
            try:
                self.root.after(0, apply_label)
            except Exception:
                pass
        if identity_error is not None:
            raise identity_error
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

        publication_result = {}

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_single_file(
                str(file_resolved), str(root_resolved), log=log,
                progress_callback=progress_callback,
                publication_result=publication_result,
            )

        def on_success(output):
            if publication_result.get("status") == "recovery_required":
                self._request_full_analysis_recovery(
                    str(root_resolved),
                    "Canonical LIVE publish requires recovery verification.",
                )
                self._set_live_status(
                    "LIVE: recovery required after accepted publish "
                    f"(revision {publication_result.get('revision')})"
                )
            elif publication_result.get("status") != "failed":
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

    def open_mcp_logs(self):
        handle_open_runtime_logs_folder()

    def on_closing(self):
        import re
        import time

        self._closing = True
        recovery_after_id = getattr(
            self, "_live_recovery_after_id", None
        )
        self._live_recovery_after_id = None

        if recovery_after_id is not None:
            try:
                self.root.after_cancel(recovery_after_id)
            except (tk.TclError, RuntimeError):
                pass

        close_cmd_log()

        # Route Desktop shutdown through the same cancellation path as Stop
        # analyze so an active full-analysis lease reaches its existing
        # coordinator finally/release before this process exits.
        if hasattr(self, "progress_bar"):
            self.progress_bar.is_cancelled = True

        full_analysis_done = getattr(self, "_full_analysis_done", None)
        if full_analysis_done is not None and not full_analysis_done.is_set():
            # Wait only for the task body. The daemon worker is allowed to
            # finish UI callbacks after this bound; process exit remains the
            # safe fallback for a task that ignores cooperative cancellation.
            full_analysis_done.wait(timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS)

        terminate_active_process_pools(
            timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS,
        )

        if (
            full_analysis_done is not None
            and not full_analysis_done.is_set()
        ):
            full_analysis_done.wait(
                timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS
            )

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
        gui_desktop_id = getattr(self, "desktop_instance_id", None)
        for client in clients:
            is_owner = getattr(client, "is_owner", False)
            client_token = getattr(client, "owner_token", None)
            service_pid = getattr(client, "service_pid", None)

            if (
                gui_desktop_id is not None
                and getattr(client, "desktop_instance_id", None) == gui_desktop_id
                and hasattr(client, "release_desktop_claim")
            ):
                try:
                    desktop_identity = getattr(client, "desktop_process_identity", None)
                    if desktop_identity is not None:
                        client.release_desktop_claim(gui_desktop_id, desktop_identity)
                except Exception:
                    pass

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


def run(*, single_instance=None):
    root = tk.Tk()
    # The controller registers itself on the widget tree, which keeps it
    # alive for the lifetime of the window; no local reference needed.
    ContextorGUI(root)
    if single_instance is not None:
        def activate_existing_window():
            root.deiconify()
            try:
                root.state("normal")
                root.lift()
                root.attributes("-topmost", True)
                root.after(100, lambda: root.attributes("-topmost", False))
                root.focus_force()
                try:
                    root.bell()
                except Exception:
                    pass
            except Exception:
                pass
        single_instance.register_activation(root, activate_existing_window)
    root.mainloop()
