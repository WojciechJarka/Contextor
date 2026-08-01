"""
contextor/ui/theme.py

Common visual layer for the Tk/ttk windows of the application.

Zero external dependencies - pure ttk.Style with a custom
theme (palette, typography, spacing, hover/pressed/disabled states).

Styles are registered at the Tcl interpreter level, so
`apply_theme(root)` called once on the main window also applies
to all Toplevels opened from the same root.

Two palettes are available, light and dark. Light is the default.

Consumers must read the colour names through the module
(`theme.BG`), never `from theme import BG`: the latter binds the value
at import time and would keep the palette that happened to be active
when the module was first imported.
"""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

__all__ = [
    "DARK",
    "LIGHT",
    "MODES",
    "HeaderTooltipManager",
    "Palette",
    "active_mode",
    "apply_theme",
    "palette",
    "retint",
    "set_theme",
]


# ==========================================================
# PALETTE
# ==========================================================


@dataclass(frozen=True)
class Palette:
    """
    Every colour the interface uses, for one appearance mode.
    """

    bg: str  # window background
    surface: str  # card / field background
    border: str  # dividers, borders
    text: str  # main text
    muted: str  # secondary text / captions
    primary: str  # accent (main action)
    primary_hover: str
    primary_pressed: str
    on_primary: str  # text on top of an accent fill
    danger: str
    danger_hover: str
    danger_ghost_hover: str
    danger_ghost_pressed: str
    disabled_bg: str
    disabled_fg: str
    button_hover: str
    button_pressed: str
    ghost_hover: str
    ghost_pressed: str
    console_bg: str  # log box
    console_fg: str
    console_accent: str  # CPU indicator
    timer_fg: str  # progress ETA readout


LIGHT = Palette(
    bg="#f5f6fa",
    surface="#ffffff",
    border="#dfe3ea",
    text="#1f2430",
    muted="#6b7280",
    primary="#2f6fed",
    primary_hover="#255ed1",
    primary_pressed="#1e4dae",
    on_primary="#ffffff",
    danger="#e5484d",
    danger_hover="#c7383d",
    danger_ghost_hover="#fdeeee",
    danger_ghost_pressed="#fbe4e4",
    disabled_bg="#e9ebf0",
    disabled_fg="#9aa0ab",
    button_hover="#eef1f6",
    button_pressed="#e3e7ee",
    ghost_hover="#eceef2",
    ghost_pressed="#e9ebf0",
    console_bg="#1e1e1e",
    console_fg="#d4d4d4",
    console_accent="#4ec9b0",
    timer_fg="#005cc5",
)


DARK = Palette(
    bg="#1b1e27",
    surface="#252a35",
    border="#39404f",
    text="#e6e9ef",
    muted="#98a1b2",
    primary="#4c8bf5",
    primary_hover="#5f99f7",
    primary_pressed="#3d7ae0",
    on_primary="#0f131a",
    danger="#f0565b",
    danger_hover="#d94a4f",
    danger_ghost_hover="#3a2529",
    danger_ghost_pressed="#472a2e",
    disabled_bg="#2b303b",
    disabled_fg="#6b7484",
    button_hover="#2f3542",
    button_pressed="#39404f",
    ghost_hover="#2a303c",
    ghost_pressed="#333a48",
    console_bg="#12151c",
    console_fg="#d4d4d4",
    console_accent="#4ec9b0",
    timer_fg="#7ab8ff",
)


MODES = {"light": LIGHT, "dark": DARK}

DEFAULT_MODE = "light"

_active_mode = DEFAULT_MODE


def palette() -> Palette:
    """
    The palette currently in effect.
    """

    return MODES[_active_mode]


def active_mode() -> str:
    return _active_mode


# Live colour names. Rebound by _publish() whenever the mode changes, so
# `theme.BG` always reflects the active palette.
BG = LIGHT.bg
SURFACE = LIGHT.surface
BORDER = LIGHT.border
TEXT = LIGHT.text
MUTED = LIGHT.muted
PRIMARY = LIGHT.primary
PRIMARY_HOVER = LIGHT.primary_hover
PRIMARY_PRESSED = LIGHT.primary_pressed
DANGER = LIGHT.danger
DANGER_HOVER = LIGHT.danger_hover
DISABLED_BG = LIGHT.disabled_bg
DISABLED_FG = LIGHT.disabled_fg


def _publish(colors: Palette) -> None:
    globals().update(
        BG=colors.bg,
        SURFACE=colors.surface,
        BORDER=colors.border,
        TEXT=colors.text,
        MUTED=colors.muted,
        PRIMARY=colors.primary,
        PRIMARY_HOVER=colors.primary_hover,
        PRIMARY_PRESSED=colors.primary_pressed,
        DANGER=colors.danger,
        DANGER_HOVER=colors.danger_hover,
        DISABLED_BG=colors.disabled_bg,
        DISABLED_FG=colors.disabled_fg,
    )


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


# ==========================================================
# STYLES
# ==========================================================


def apply_theme(root: tk.Misc, mode: str | None = None) -> ttk.Style:
    """
    Configures ttk.Style for a consistent, modern application look.
    Call once, on the main window (root = tk.Tk()).

    `mode` of None keeps whatever mode is already active, so a secondary
    window re-applying the theme cannot silently reset the whole
    application back to light.
    """
    global _active_mode

    if mode is not None:
        _active_mode = mode if mode in MODES else DEFAULT_MODE

    colors = palette()

    _publish(colors)

    style = ttk.Style(root)

    # 'clam' is the only built-in theme that fully respects
    # custom background/border colors on Windows.
    style.theme_use("clam")

    root.configure(bg=colors.bg)

    style.configure("TFrame", background=colors.bg)
    style.configure("Card.TFrame", background=colors.surface)

    style.configure(
        "TLabelframe",
        background=colors.bg,
        bordercolor=colors.border,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=colors.bg,
        foreground=colors.text,
        font=FONT_SECTION,
    )

    style.configure("TLabel", background=colors.bg, foreground=colors.text, font=FONT_BASE)
    style.configure("Header.TLabel", background=colors.bg, foreground=colors.text, font=FONT_HEADER)
    style.configure(
        "Sub.TLabel", background=colors.bg, foreground=colors.muted, font=FONT_SUBHEADER
    )
    style.configure("Field.TLabel", background=colors.bg, foreground=colors.muted, font=FONT_MUTED)
    style.configure("Status.TLabel", background=colors.bg, foreground=colors.muted, font=FONT_MUTED)

    # Progress readouts: styled rather than coloured inline, so they
    # follow the palette instead of being repainted by hand.
    style.configure(
        "Timer.TLabel",
        background=colors.bg,
        foreground=colors.timer_fg,
        font=("Consolas", 9, "bold"),
    )
    style.configure(
        "Flicker.TLabel",
        background=colors.bg,
        foreground=colors.text,
        font=("Consolas", 9, "bold"),
    )
    style.configure(
        "Cpu.TLabel",
        background=colors.console_bg,
        foreground=colors.console_accent,
        font=("Consolas", 8),
        padding=(5, 2),
    )

    style.configure(
        "TCheckbutton",
        background=colors.bg,
        foreground=colors.text,
        font=FONT_BASE,
    )
    style.map(
        "TCheckbutton",
        background=[("active", colors.bg)],
        foreground=[("disabled", colors.disabled_fg)],
    )

    style.configure(
        "TEntry",
        fieldbackground=colors.surface,
        bordercolor=colors.border,
        lightcolor=colors.border,
        darkcolor=colors.border,
        borderwidth=1,
        relief="solid",
        padding=6,
        foreground=colors.text,
        insertcolor=colors.text,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", colors.primary)],
        lightcolor=[("focus", colors.primary)],
        darkcolor=[("focus", colors.primary)],
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
        background=colors.danger,
        foreground="#ffffff",
    )
    style.map(
        "Danger.TButton",
        background=[
            ("disabled", colors.disabled_bg),
            ("pressed", colors.danger_hover),
            ("active", colors.danger_hover),
        ],
        foreground=[("disabled", colors.disabled_fg)],
    )

    style.configure(
        "TButton",
        font=FONT_BUTTON,
        padding=(12, 7),
        borderwidth=0,
        relief="flat",
        background=colors.surface,
        foreground=colors.text,
    )
    style.map(
        "TButton",
        background=[
            ("disabled", colors.disabled_bg),
            ("pressed", colors.button_pressed),
            ("active", colors.button_hover),
        ],
        foreground=[("disabled", colors.disabled_fg)],
    )

    style.configure(
        "Primary.TButton",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(14, 9),
        borderwidth=0,
        relief="flat",
        background=colors.primary,
        foreground=colors.on_primary,
    )
    style.map(
        "Primary.TButton",
        background=[
            ("disabled", colors.disabled_bg),
            ("pressed", colors.primary_pressed),
            ("active", colors.primary_hover),
        ],
        foreground=[("disabled", colors.disabled_fg)],
    )

    style.configure(
        "Secondary.TButton",
        font=FONT_BUTTON,
        padding=(12, 7),
        borderwidth=1,
        relief="solid",
        background=colors.surface,
        foreground=colors.text,
        bordercolor=colors.border,
    )
    style.map(
        "Secondary.TButton",
        background=[
            ("disabled", colors.disabled_bg),
            ("pressed", colors.button_pressed),
            ("active", colors.button_hover),
        ],
        bordercolor=[("active", colors.primary)],
        foreground=[("disabled", colors.disabled_fg)],
    )

    style.configure(
        "Ghost.TButton",
        font=FONT_MUTED,
        padding=(10, 5),
        borderwidth=0,
        relief="flat",
        background=colors.bg,
        foreground=colors.muted,
    )
    style.map(
        "Ghost.TButton",
        background=[("pressed", colors.ghost_pressed), ("active", colors.ghost_hover)],
        foreground=[("active", colors.text)],
    )

    style.configure(
        "Danger.Ghost.TButton",
        font=FONT_MUTED,
        padding=(10, 5),
        borderwidth=0,
        relief="flat",
        background=colors.bg,
        foreground=colors.danger,
    )
    style.map(
        "Danger.Ghost.TButton",
        background=[
            ("pressed", colors.danger_ghost_pressed),
            ("active", colors.danger_ghost_hover),
        ],
        foreground=[("active", colors.danger_hover)],
    )

    style.configure("TSeparator", background=colors.border)

    style.configure(
        "TProgressbar",
        troughcolor=colors.bg,
        bordercolor=colors.bg,
        background=colors.primary,
        lightcolor=colors.primary,
        darkcolor=colors.primary,
        thickness=6,
    )

    return style


# ==========================================================
# RE-TINTING PLAIN TK WIDGETS
# ==========================================================
#
# ttk widgets follow ttk.Style and update themselves when the styles are
# reconfigured. Classic Tk widgets (Listbox, Text, Canvas, and the
# Frames/Labels/Toplevels built with tk rather than ttk) carry their
# colours per instance, so switching mode has to repaint them.


def _retint_widget(widget: tk.Misc, colors: Palette) -> None:
    name = widget.winfo_class()

    if name in ("Toplevel", "Tk", "Frame", "Labelframe", "TkFrame"):
        widget.configure(bg=colors.bg)

    elif name == "Label":
        widget.configure(bg=colors.bg, fg=colors.text)

    elif name == "Listbox":
        widget.configure(
            bg=colors.surface,
            fg=colors.text,
            selectbackground=colors.primary,
            selectforeground=colors.on_primary,
            highlightbackground=colors.border,
        )

    elif name in ("Text", "Canvas"):
        widget.configure(bg=colors.console_bg, fg=colors.console_fg, insertbackground=colors.text)

    elif name == "Scrollbar":
        # The classic scrollbar bundled with ScrolledText defaults to the
        # OS button colour and stays light otherwise.
        widget.configure(
            bg=colors.surface,
            troughcolor=colors.bg,
            activebackground=colors.border,
            highlightbackground=colors.border,
            borderwidth=0,
        )


def retint(widget: tk.Misc) -> None:
    """
    Repaints classic Tk widgets under `widget` for the active palette.

    Widgets whose colours are deliberate rather than themed can opt out
    by setting the attribute `contextor_no_retint` to True.
    """

    colors = palette()

    if not getattr(widget, "contextor_no_retint", False):
        try:
            _retint_widget(widget, colors)
        except tk.TclError:
            # Some widgets do not accept every option; never let a
            # cosmetic repaint break the interface.
            pass

    for child in widget.winfo_children():
        retint(child)


def set_theme(root: tk.Misc, mode: str) -> None:
    """
    Switches appearance mode and repaints every open window.
    """

    apply_theme(root, mode)

    retint(root)

    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            retint(window)


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
            except tk.TclError:
                pass

        def _on_leave(event):
            try:
                self.target_label.configure(text=self.default_text)
            except tk.TclError:
                pass

        widget.bind("<Enter>", _on_enter, add="+")
        widget.bind("<Leave>", _on_leave, add="+")
