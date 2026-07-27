# repo_guardian/ui/path_memory.py

from pathlib import Path
import json

STATE_FILE = Path(__file__).resolve().parent / "ui_state.json"

DEFAULT_STATE = {
    "repository": "",
    "python_file": "",
    "json_file": "",
    "search_term": ""
}


def load_state():
    """
    Wczytuje ostatnio używane ścieżki.
    """
    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        state = DEFAULT_STATE.copy()
        state.update(data)

        return state

    except Exception:
        return DEFAULT_STATE.copy()


def save_state(**kwargs):
    """
    Aktualizuje wybrane pola i zapisuje plik.
    """

    state = load_state()

    state.update(kwargs)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            indent=4,
            ensure_ascii=False
        )
