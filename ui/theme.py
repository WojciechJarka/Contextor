# -*- coding: utf-8 -*-
"""
repo_guardian/ui/theme.py

Wspólna warstwa wizualna dla okien Tk/ttk aplikacji.

Zero zewnętrznych zależności - czysty ttk.Style z własnym
motywem (paleta, typografia, spacing, stany hover/pressed/disabled).

Style są rejestrowane na poziomie interpretera Tcl, więc
`apply_theme(root)` wywołane raz na oknie głównym obowiązuje
też we wszystkich Toplevel-ach otwartych z tego samego roota.
"""

import tkinter as tk
from tkinter import ttk


# ==========================================================
# PALETTE
# ==========================================================

BG = "#f5f6fa"          # tło okna
SURFACE = "#ffffff"      # tło kart / pól
BORDER = "#dfe3ea"       # linie podziału, obwódki
TEXT = "#1f2430"         # tekst główny
MUTED = "#6b7280"        # tekst drugorzędny / podpisy
PRIMARY = "#2f6fed"      # akcent (główna akcja)
PRIMARY_HOVER = "#255ed1"
PRIMARY_PRESSED = "#1e4dae"
DANGER = "#e5484d"
DANGER_HOVER = "#c7383d"
DISABLED_BG = "#e9ebf0"
DISABLED_FG = "#9aa0ab"

FONT_FAMILY = "Segoe UI"
FONT_BASE = (FONT_FAMILY, 10)
FONT_MUTED = (FONT_FAMILY, 9)
FONT_HEADER = (FONT_FAMILY, 15, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 9)
FONT_SECTION = (FONT_FAMILY, 10, "bold")
FONT_BUTTON = (FONT_FAMILY, 10)
FONT_MONO = ("Consolas", 9)

PAD_SM = 6
PAD_MD = 12
PAD_LG = 18


def apply_theme(root: tk.Misc) -> ttk.Style:
    """
    Konfiguruje ttk.Style pod spójny, nowoczesny wygląd aplikacji.
    Wywołać raz, na oknie głównym (root = tk.Tk()).
    """
    style = ttk.Style(root)

    # 'clam' to jedyny wbudowany motyw, który w pełni respektuje
    # niestandardowe kolory tła/obwódki na Windows.
    style.theme_use("clam")

    root.configure(bg=BG)

    style.configure(
        "TFrame",
        background=BG,
    )

    style.configure(
        "Card.TFrame",
        background=SURFACE,
    )

    style.configure(
        "TLabelframe",
        background=BG,
        bordercolor=BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=BG,
        foreground=TEXT,
        font=FONT_SECTION,
    )

    style.configure(
        "TLabel",
        background=BG,
        foreground=TEXT,
        font=FONT_BASE,
    )
    style.configure(
        "Header.TLabel",
        background=BG,
        foreground=TEXT,
        font=FONT_HEADER,
    )
    style.configure(
        "Sub.TLabel",
        background=BG,
        foreground=MUTED,
        font=FONT_SUBHEADER,
    )
    style.configure(
        "Field.TLabel",
        background=BG,
        foreground=MUTED,
        font=FONT_MUTED,
    )
    style.configure(
        "Status.TLabel",
        background=BG,
        foreground=MUTED,
        font=FONT_MUTED,
    )

    style.configure(
        "TEntry",
        fieldbackground=SURFACE,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        relief="solid",
        padding=6,
        foreground=TEXT,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", PRIMARY)],
        lightcolor=[("focus", PRIMARY)],
        darkcolor=[("focus", PRIMARY)],
    )

    # ------------------------------------------------------
    # Buttons
    # ------------------------------------------------------

    style.configure(
        "TButton",
        font=FONT_BUTTON,
        padding=(12, 7),
        borderwidth=0,
        relief="flat",
        background=SURFACE,
        foreground=TEXT,
    )
    style.map(
        "TButton",
        background=[
            ("disabled", DISABLED_BG),
            ("pressed", BORDER),
            ("active", "#eef1f6"),
        ],
        foreground=[
            ("disabled", DISABLED_FG),
        ],
    )

    style.configure(
        "Primary.TButton",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(14, 9),
        borderwidth=0,
        relief="flat",
        background=PRIMARY,
        foreground="#ffffff",
    )
    style.map(
        "Primary.TButton",
        background=[
            ("disabled", DISABLED_BG),
            ("pressed", PRIMARY_PRESSED),
            ("active", PRIMARY_HOVER),
        ],
        foreground=[
            ("disabled", DISABLED_FG),
        ],
    )

    style.configure(
        "Secondary.TButton",
        font=FONT_BUTTON,
        padding=(12, 7),
        borderwidth=1,
        relief="solid",
        background=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
    )
    style.map(
        "Secondary.TButton",
        background=[
            ("disabled", DISABLED_BG),
            ("pressed", "#e3e7ee"),
            ("active", "#eef1f6"),
        ],
        bordercolor=[
            ("active", PRIMARY),
        ],
        foreground=[
            ("disabled", DISABLED_FG),
        ],
    )

    style.configure(
        "Ghost.TButton",
        font=FONT_MUTED,
        padding=(10, 5),
        borderwidth=0,
        relief="flat",
        background=BG,
        foreground=MUTED,
    )
    style.map(
        "Ghost.TButton",
        background=[
            ("pressed", "#e9ebf0"),
            ("active", "#eceef2"),
        ],
        foreground=[
            ("active", TEXT),
        ],
    )

    style.configure(
        "Danger.Ghost.TButton",
        font=FONT_MUTED,
        padding=(10, 5),
        borderwidth=0,
        relief="flat",
        background=BG,
        foreground=DANGER,
    )
    style.map(
        "Danger.Ghost.TButton",
        background=[
            ("pressed", "#fbe4e4"),
            ("active", "#fdeeee"),
        ],
        foreground=[
            ("active", DANGER_HOVER),
        ],
    )

    style.configure(
        "TSeparator",
        background=BORDER,
    )

    style.configure(
        "TProgressbar",
        troughcolor=BG,
        bordercolor=BG,
        background=PRIMARY,
        lightcolor=PRIMARY,
        darkcolor=PRIMARY,
        thickness=6,
    )

    return style


# ==========================================================
# TOOLTIP
# ==========================================================


class Tooltip:
    """
    Lekki, prawdziwy tooltip (Toplevel bez ramki) pokazywany
    po zatrzymaniu kursora na widgecie - zamiast nadpisywania
    tytułu okna.
    """

    _DELAY_MS = 400

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self._after_id = None
        self._tip = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _cancel(self):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tip is not None:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        self._tip.configure(bg=TEXT)

        label = tk.Label(
            self._tip,
            text=self.text,
            justify="left",
            bg=TEXT,
            fg="#ffffff",
            font=FONT_MUTED,
            padx=8,
            pady=5,
            wraplength=320,
        )
        label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None
