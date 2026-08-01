# contextor/ui/path_memory.py

import json

from contextor.core.paths import ensure_dir, state_dir

# Stored in the user state directory rather than inside the package:
# an installed package directory is normally not writable.
STATE_FILE = state_dir() / "ui_state.json"

DEFAULT_STATE = {
    "repository": "",
    "layer": "",
    "python_file": "",
    "json_file": "",
    "search_term": "",
    "public_api_only": False,
    "theme": "light",
}


def load_state():
    """
    Loads recently used paths.
    """
    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        state = DEFAULT_STATE.copy()
        state.update(data)

        return state

    except Exception:
        return DEFAULT_STATE.copy()


def save_state(**kwargs):
    """
    Updates selected fields and saves the file.
    """

    state = load_state()

    state.update(kwargs)

    ensure_dir(STATE_FILE.parent)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
