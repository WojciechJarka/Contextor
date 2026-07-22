# -*- coding: utf-8 -*-
"""
repo_guardian/ui/progress_widget.py

Prosty, wielokrotnego użytku pasek postępu (ttk.Progressbar)
do wpięcia u dołu dowolnego okna GUI.

Core (build_index, build_graph, validate, itd.) nie raportuje
postępu krok po kroku, więc pasek pracuje w trybie "indeterminate"
(animacja przesuwającego się bloku) i jest uruchamiany na czas
wykonania operacji w osobnym wątku, żeby nie blokować pętli
zdarzeń tkintera (root.mainloop()).
"""

import threading
import tkinter as tk
from tkinter import ttk


def create_progress_bar(parent, **pack_kwargs):
    """
    Tworzy pasek postępu (indeterminate) i pakuje go w podanym
    rodzicu (np. root albo Toplevel). Zwraca obiekt ttk.Progressbar.

    Domyślne pakowanie: side="bottom", fill="x", padx=10, pady=(0, 10)
    Można nadpisać dowolny z tych parametrów przez pack_kwargs.
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


def run_with_progress(root, progressbar, task, on_success=None, on_error=None, buttons=None):
    """
    Uruchamia `task` (funkcja bezargumentowa) w osobnym wątku,
    animując pasek postępu przez cały czas jej trwania.

    root         - okno (root albo Toplevel) potrzebne do bezpiecznego
                   powrotu na wątek GUI przez root.after(...)
    progressbar  - obiekt zwrócony przez create_progress_bar()
    task         - funkcja wykonywana w tle (bez argumentów),
                   powinna zwrócić wynik albo rzucić wyjątek
    on_success   - callback(result) wywoływany w wątku GUI po sukcesie
    on_error     - callback(exception) wywoływany w wątku GUI po błędzie
    buttons      - lista widgetów (np. tk.Button) blokowanych
                   (state="disabled") na czas operacji, żeby
                   nie dało się odpalić dwóch operacji naraz
    """

    def set_buttons_state(state):
        for btn in (buttons or []):
            btn.config(state=state)

    def finish_success(result):
        progressbar.stop()
        set_buttons_state("normal")
        if on_success:
            on_success(result)

    def finish_error(exc):
        progressbar.stop()
        set_buttons_state("normal")
        if on_error:
            on_error(exc)

    def worker():
        try:
            result = task()
        except Exception as exc:
            root.after(0, finish_error, exc)
        else:
            root.after(0, finish_success, result)

    set_buttons_state("disabled")
    progressbar.start(10)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
