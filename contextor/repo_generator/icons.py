import tkinter as tk
from tkinter import ttk

from contextor.ui import theme
from contextor.ui.theme import PAD_SM


def draw_icon(canvas, icon_type):
    canvas.delete("all")
    if icon_type == "big_plus":
        canvas.create_line(17, 5, 17, 30, fill="green", width=5)
        canvas.create_line(5, 17, 30, 17, fill="green", width=5)
    elif icon_type == "small_plus":
        for x in (8, 17, 26):
            canvas.create_line(x, 12, x, 22, fill="green", width=2)
            canvas.create_line(x - 5, 17, x + 5, 17, fill="green", width=2)
    elif icon_type == "big_minus":
        canvas.create_line(5, 17, 30, 17, fill="red", width=5)
    elif icon_type == "small_minus":
        for x in (8, 17, 26):
            canvas.create_line(x - 5, 17, x + 5, 17, fill="red", width=3)


def create_icon_button(parent, text, command, icon_type):
    frame = ttk.Frame(parent)
    frame.pack(side=tk.LEFT, padx=(0, PAD_SM))
    canvas = tk.Canvas(frame, width=35, height=35, highlightthickness=0, bg=theme.BG)
    canvas.pack(side=tk.LEFT)
    draw_icon(canvas, icon_type)
    btn = ttk.Button(frame, text=text, command=command, style="Secondary.TButton")
    btn.pack(side=tk.LEFT)
    return btn
