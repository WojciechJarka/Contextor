"""
ui/progress_widget.py

UI components for tracking long-running analysis tasks.
Contains indeterminate progress bars, determinate progress bars, and log consoles.
"""

import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

from contextor.core.errors import AnalysisCancelled
from contextor.core.program_log import emit_program_log
from contextor.ui import theme


def truncate_path(path_str, max_len=55):
    if not path_str or len(path_str) <= max_len:
        return path_str

    path_str = path_str.replace("\\", "/")
    parts = path_str.split("/")
    filename = parts[-1]

    if len(filename) >= max_len - 4:
        return "..." + filename[-(max_len - 4) :]

    return "..." + path_str[-(max_len - 3) :]


def _format_eta(completed, total, elapsed):
    """Return an honest global ETA without claiming completion mid-task."""

    if total <= 0 or completed <= 0:
        return "ETA: estimating…"
    remaining = elapsed * max(0, total - completed) / completed
    mins, secs = divmod(int(remaining), 60)
    return f"ETA: {mins}m {secs}s"


def create_progress_bar(parent, **pack_kwargs):
    """
    Creates a container with an indeterminate progress bar and a determinate
    progress bar beneath it. Also includes a label for flickering filename.
    Returns the container frame.
    """
    options = {
        "side": "bottom",
        "fill": "x",
        "padx": 10,
        "pady": (0, 10),
    }
    options.update(pack_kwargs)

    container = ttk.Frame(parent)
    container.pack(**options)

    # Label for flickering file name and time
    text_frame = ttk.Frame(container)
    text_frame.pack(side="top", fill="x")

    time_label = ttk.Label(text_frame, text="", style="Timer.TLabel", width=25)
    time_label.pack(side="left")

    flicker_label = ttk.Label(text_frame, text="", style="Flicker.TLabel", width=55, anchor="e")
    flicker_label.pack(side="right")

    # Indeterminate bar
    bar_indet = ttk.Progressbar(container, mode="indeterminate", length=200)
    bar_indet.pack(side="top", fill="x", pady=(0, 2))

    # Determinate bar
    bar_det = ttk.Progressbar(container, mode="determinate", length=200, maximum=100)
    bar_det.pack(side="top", fill="x")

    container.indet = bar_indet
    container.det = bar_det
    container.flicker_label = flicker_label
    container.time_label = time_label

    return container


def create_log_box(parent, height=5, **pack_kwargs):
    """
    Creates a default hidden or visible text field for logs (ScrolledText)
    above the progress bar. Returns a text widget.
    """
    options = {
        "side": "bottom",
        "fill": "x",
        "padx": 10,
        "pady": (0, 5),
    }
    options.update(pack_kwargs)

    log_box = scrolledtext.ScrolledText(
        parent,
        height=height,
        state="disabled",
        bg=theme.palette().console_bg,
        fg=theme.palette().console_fg,
        font=("Consolas", 9),
    )
    return log_box


def create_cpu_indicator(parent, **pack_kwargs):
    """
    Creates a small, dark label/text widget indicating the number of CPU cores
    in use by the multiprocessing pool.
    """
    import os

    cores = os.cpu_count() or 1

    options = {
        "side": "top",
        "anchor": "e",
        "padx": 10,
        "pady": (0, 2),
    }
    options.update(pack_kwargs)

    # Styled rather than coloured inline so it follows the palette.
    lbl = ttk.Label(parent, text=f"CPU Threads in use: {cores}", style="Cpu.TLabel")

    return lbl


def run_with_progress(
    root,
    progress_container,
    task,
    on_success=None,
    on_error=None,
    buttons=None,
    log_box=None,
    cpu_indicator=None,
    stop_button=None,
    on_cancel=None,
    operation_name=None,
):
    """
    Runs `task` in a separate thread, animating the progress bar
    and optionally handling logging via log(msg) function.

    The task function can take a log_callback argument (optional),
    and a progress_callback argument (optional).
    """

    def set_buttons_state(state):
        for btn in buttons or []:
            btn.config(state=state)
        if stop_button:
            stop_button.config(state="normal" if state == "disabled" else "disabled")

    def write_log(msg):
        if log_box:
            log_box.config(state="normal")
            log_box.insert(tk.END, msg + "\n")
            log_box.see(tk.END)
            log_box.config(state="disabled")

    start_time = time.time()
    start_monotonic = time.monotonic()
    progress_state = {
        "active": True,
        "completed": 0,
        "total": 0,
        "filename": "",
    }

    def refresh_eta():
        """Keep ETA alive while an opaque report/write stage is running."""

        if not progress_state["active"]:
            return
        completed = progress_state["completed"]
        total = progress_state["total"]
        if total > 0:
            perc = (completed / total) * 100
            elapsed = time.time() - start_time
            progress_container.time_label.config(
                text=f"[{perc:5.1f}%] {_format_eta(completed, total, elapsed)}"
            )
        root.after(1000, refresh_eta)

    def update_progress(completed, total, filename):
        short_filename = truncate_path(str(filename))
        progress_state.update(
            completed=completed,
            total=total,
            filename=short_filename,
        )
        if total > 0:
            perc = (completed / total) * 100
            progress_container.det["value"] = perc
            progress_container.flicker_label.config(
                text=short_filename, anchor="e", justify="right"
            )

            elapsed = time.time() - start_time
            progress_container.time_label.config(
                text=f"[{perc:5.1f}%] {_format_eta(completed, total, elapsed)}"
            )
        else:
            progress_container.flicker_label.config(
                text=short_filename, anchor="e", justify="right"
            )

    def reset_progress_display():
        """Clear determinate state after every terminal operation outcome."""

        progress_state["active"] = False
        progress_container.indet.stop()
        progress_container.det["value"] = 0
        progress_container.flicker_label.config(text="")
        progress_container.time_label.config(text="")

    def finish_success(result):
        reset_progress_display()
        set_buttons_state("normal")
        if isinstance(result, dict) and result.get("exit_code", 0) != 0:
            message = f"[FAILED] Operation completed with exit code {result['exit_code']}."
        elif operation_name:
            duration = round(time.monotonic() - start_monotonic)
            message = f"[SUCCESS] {operation_name} completed. (duration: {duration} s)"
        else:
            message = "[SUCCESS] Operation completed successfully."
        emit_program_log(message)
        write_log(message)
        if on_success:
            on_success(result)

    def finish_error(exc):
        reset_progress_display()
        set_buttons_state("normal")
        message = f"[ERROR] {exc}"
        emit_program_log(message)
        write_log(message)
        if on_error:
            on_error(exc)

    def finish_cancelled():
        reset_progress_display()
        set_buttons_state("normal")
        message = "[CANCELLED] Analysis stopped by user."
        emit_program_log(message)
        write_log(message)
        if on_cancel:
            on_cancel()

    def worker():
        try:
            import inspect

            sig = inspect.signature(task)
            kwargs = {}
            if "log" in sig.parameters:
                kwargs["log"] = lambda msg: root.after(0, write_log, msg)
            if "progress_callback" in sig.parameters:
                last_call = [0]
                last_filename = [None]

                def p_callback(completed, total, filename):
                    now = time.time()
                    is_stage_change = filename != last_filename[0]
                    if is_stage_change or now - last_call[0] > 0.1:
                        root.after(0, update_progress, completed, total, filename)
                        last_call[0] = now
                        last_filename[0] = filename
                    return not getattr(progress_container, "is_cancelled", False)

                kwargs["progress_callback"] = p_callback

            result = task(**kwargs)
        except AnalysisCancelled:
            # Expected outcome of pressing Stop - not a failure.
            root.after(0, finish_cancelled)
        except Exception as exc:
            import traceback

            traceback.print_exc()
            root.after(0, finish_error, exc)
        else:
            root.after(0, finish_success, result)

    set_buttons_state("disabled")
    progress_container.indet.start(10)
    progress_container.det["value"] = 0
    progress_container.flicker_label.config(text="")
    # Some secondary GUI tasks have no measurable item callback. Keep their
    # indeterminate operation explicit instead of reusing a stale 100%/0s ETA.
    progress_container.time_label.config(text="[ -- ] ETA: estimating…")
    root.after(1000, refresh_eta)

    if log_box:
        log_box.config(state="normal")
        log_box.delete("1.0", tk.END)
        log_box.config(state="disabled")
        if cpu_indicator:
            cpu_indicator.pack(before=log_box, side="top", anchor="e", padx=10, pady=(0, 2))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
