# -*- coding: utf-8 -*-
"""
repo_guardian/ui/theme.py

Common visual layer for the Tk/ttk windows of the application.

Zero external dependencies - pure ttk.Style with a custom
theme (palette, typography, spacing, hover/pressed/disabled states).

Styles are registered at the Tcl interpreter level, so
`apply_theme(root)` called once on the main window also applies
to all Toplevels opened from the same root.
"""

import tkinter as tk
from tkinter import ttk


# ==========================================================
# PALETTE
# ==========================================================

BG = "#f5f6fa"          # window background
SURFACE = "#ffffff"      # card / field background
BORDER = "#dfe3ea"       # dividers, borders
TEXT = "#1f2430"         # main text
MUTED = "#6b7280"        # secondary text / captions
PRIMARY = "#2f6fed"      # accent (main action)
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
    Configures ttk.Style for a consistent, modern application look.
    Call once, on the main window (root = tk.Tk()).
    """
    style = ttk.Style(root)

    # 'clam' is the only built-in theme that fully respects
    # custom background/border colors on Windows.
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
        "Danger.TButton",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(12, 7),
        borderwidth=0,
        relief="flat",
        background=DANGER,
        foreground="#ffffff",
    )
    style.map(
        "Danger.TButton",
        background=[
            ("disabled", DISABLED_BG),
            ("pressed", DANGER_HOVER),
            ("active", DANGER_HOVER),
        ],
        foreground=[
            ("disabled", DISABLED_FG),
        ],
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


class HeaderTooltipManager:
    """
    Lightweight tooltip manager that changes the text of a designated target label
    (usually the window sub-header) when hovering over interactive widgets,
    instead of displaying intrusive popup windows.
    """
    def __init__(self, target_label: ttk.Label, default_text: str):
        self.target_label = target_label
        self.default_text = default_text

    def bind_tooltip(self, widget: tk.Widget, text: str):
        def _on_enter(event):
            try:
                self.target_label.configure(text=text)
            except Exception:
                pass

        def _on_leave(event):
            try:
                self.target_label.configure(text=self.default_text)
            except Exception:
                pass

        widget.bind("<Enter>", _on_enter, add="+")
        widget.bind("<Leave>", _on_leave, add="+")
