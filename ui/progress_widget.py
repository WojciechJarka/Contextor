# -*- coding: utf-8 -*-
"""
repo_guardian/ui/progress_widget.py

Pasek postępu oraz konsola logów do wpięcia u dołu okna GUI.
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext


def create_progress_bar(parent, **pack_kwargs):
    """
    Tworzy pasek postępu (indeterminate) i pakuje go w podanym
    rodziku (np. root albo Toplevel). Zwraca obiekt ttk.Progressbar.
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
    Tworzy ukryte domyślnie lub widoczne pole tekstowe na logi (ScrolledText)
    nad paskiem postępu. Zwraca widget tekstowy.
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
    Uruchamia `task` w osobnym wątku, animując pasek postępu
    oraz opcjonalnie obsługując logowanie przez funkcję log(msg).
    
    Funkcja task może przyjmować argument log_callback (opcjonalnie),
    np. def task(log=None): ... log("robę coś...")
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
        write_log("[SUKCES] Operacja zakończona pomyślnie.")
        if on_success:
            on_success(result)

    def finish_error(exc):
        progressbar.stop()
        set_buttons_state("normal")
        write_log(f"[BŁĄD] {exc}")
        if on_error:
            on_error(exc)

    def worker():
        try:
            # Sprawdzamy czy task przyjmuje argument logujący, czy nie
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
