# -*- coding: utf-8 -*-
"""
ui/progress_widget.py

UI components for tracking long-running analysis tasks.
Contains indeterminate progress bars and log consoles.
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext


def create_progress_bar(parent, **pack_kwargs):
    """
    Creates an indeterminate progress bar and packs it in the given
    parent (e.g. root or Toplevel). Returns a ttk.Progressbar object.
    """

    options = {
        "side": "bottom",
        "fill": "x",
        "padx": 10,
        "pady": (0, 10),
    }
    options.update(pack_kwargs)

    bar = ttk.Progressbar(
        parent,
        mode="indeterminate",
        length=200
    )

    bar.pack(**options)

    return bar


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
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=("Consolas", 9)
    )
    
    return log_box


def run_with_progress(root, progressbar, task, on_success=None, on_error=None, buttons=None, log_box=None):
    """
    Runs `task` in a separate thread, animating the progress bar
    and optionally handling logging via log(msg) function.
    
    The task function can take a log_callback argument (optional),
    e.g. def task(log=None): ... log("doing something...")
    """

    def set_buttons_state(state):
        for btn in (buttons or []):
            btn.config(state=state)

    def write_log(msg):
        if log_box:
            log_box.config(state="normal")
            log_box.insert(tk.END, msg + "\n")
            log_box.see(tk.END)
            log_box.config(state="disabled")

    def finish_success(result):
        progressbar.stop()
        set_buttons_state("normal")
        write_log("[SUCCESS] Operation completed successfully.")
        if on_success:
            on_success(result)

    def finish_error(exc):
        progressbar.stop()
        set_buttons_state("normal")
        write_log(f"[ERROR] {exc}")
        if on_error:
            on_error(exc)

    def worker():
        try:
            # Check if the task accepts a logging argument or not
            import inspect
            sig = inspect.signature(task)
            if len(sig.parameters) > 0:
                result = task(log=lambda msg: root.after(0, write_log, msg))
            else:
                result = task()
        except Exception as exc:
            root.after(0, finish_error, exc)
        else:
            root.after(0, finish_success, result)

    set_buttons_state("disabled")
    progressbar.start(10)
    
    if log_box:
        log_box.config(state="normal")
        log_box.delete("1.0", tk.END)
        log_box.config(state="disabled")
        log_box.pack(before=progressbar, fill="x", padx=10, pady=(0, 5))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
