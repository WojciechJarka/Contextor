"""
Appearance modes.

Light is the default. Switching must repaint everything, including the
classic Tk widgets that do not follow ttk styles, and must survive a
restart.
"""

import dataclasses
import re

import pytest

from contextor.ui import theme

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


@pytest.fixture
def tk_root():
    tk = pytest.importorskip("tkinter")

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")

    root.withdraw()

    yield root

    try:
        root.destroy()
    except tk.TclError:
        pass


# ==========================================================
# PALETTES
# ==========================================================


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_every_colour_is_a_valid_hex_value(mode):
    for field in dataclasses.fields(theme.Palette):
        value = getattr(theme.MODES[mode], field.name)
        assert HEX.match(value), f"{mode}.{field.name} = {value!r}"


def test_the_two_palettes_are_actually_different():
    light = dataclasses.asdict(theme.LIGHT)
    dark = dataclasses.asdict(theme.DARK)

    shared = [name for name, value in light.items() if dark[name] == value]

    # A few accents are deliberately shared; the bulk must differ.
    assert len(shared) < len(light) / 2, f"too many identical colours: {shared}"


def test_light_is_the_default():
    assert theme.DEFAULT_MODE == "light"
    assert theme.MODES[theme.DEFAULT_MODE] is theme.LIGHT


def test_backgrounds_and_text_are_inverted_between_modes():
    def brightness(value):
        r, g, b = (int(value[i : i + 2], 16) for i in (1, 3, 5))
        return r + g + b

    assert brightness(theme.LIGHT.bg) > brightness(theme.LIGHT.text)
    assert brightness(theme.DARK.bg) < brightness(theme.DARK.text)


# ==========================================================
# SWITCHING
# ==========================================================


def test_apply_theme_defaults_to_light(tk_root):
    theme.apply_theme(tk_root, "light")

    assert theme.active_mode() == "light"
    assert tk_root.cget("bg") == theme.LIGHT.bg


def test_apply_theme_without_a_mode_keeps_the_active_one(tk_root):
    """
    A secondary window re-applying the theme must not reset the app to
    light behind the user's back.
    """

    theme.apply_theme(tk_root, "dark")

    theme.apply_theme(tk_root)

    assert theme.active_mode() == "dark"


def test_switching_mode_updates_the_live_colour_names(tk_root):
    theme.apply_theme(tk_root, "light")
    assert theme.BG == theme.LIGHT.bg

    theme.set_theme(tk_root, "dark")
    assert theme.BG == theme.DARK.bg

    theme.set_theme(tk_root, "light")
    assert theme.BG == theme.LIGHT.bg


def test_switching_mode_repaints_plain_tk_widgets(tk_root):
    tk = pytest.importorskip("tkinter")

    theme.apply_theme(tk_root, "light")

    label = tk.Label(tk_root, text="x")
    listbox = tk.Listbox(tk_root)

    theme.set_theme(tk_root, "dark")

    assert label.cget("bg") == theme.DARK.bg
    assert label.cget("fg") == theme.DARK.text
    assert listbox.cget("bg") == theme.DARK.surface

    theme.set_theme(tk_root, "light")

    assert label.cget("bg") == theme.LIGHT.bg


def test_widgets_can_opt_out_of_repainting(tk_root):
    tk = pytest.importorskip("tkinter")

    theme.apply_theme(tk_root, "light")

    label = tk.Label(tk_root, text="x", bg="#ff00ff")
    label.contextor_no_retint = True

    theme.set_theme(tk_root, "dark")

    assert label.cget("bg") == "#ff00ff"


def test_unknown_mode_falls_back_to_light(tk_root):
    theme.apply_theme(tk_root, "solarized")

    assert theme.active_mode() == "light"
