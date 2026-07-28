"""
ui/gui_parser.py

Search tool GUI for filtering JSON output matrices, 
exploring semantic linkages and public API intersections.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import re

from repo_guardian.ui.path_memory import load_state, save_state
from repo_guardian.ui.progress_widget import create_progress_bar, run_with_progress
from repo_guardian.ui.theme import BG, PAD_SM, PAD_MD, PAD_LG, HeaderTooltipManager


def matches_term(data, search_term, is_py_query):
    if isinstance(data, dict):
        return any(matches_term(v, search_term, is_py_query) for v in data.values())
    elif isinstance(data, list):
        return any(matches_term(i, search_term, is_py_query) for i in data)
    elif isinstance(data, str):
        if is_py_query:
            return bool(re.search(rf"\.{re.escape(search_term)}(\.|$)", data))
        else:
            return bool(re.search(rf"(?<!\.)\b{re.escape(search_term)}\b", data))
    return False

def consumer_only_match(value, term):
    if not isinstance(value, dict):
        return False
    consumers = value.get("consumers", [])
    if term not in consumers:
        return False
    artifact = value.get("artifact", "")
    key_hits = False
    return (not artifact == term and not key_hits)

def parse_and_filter_json(json_path, search_term, output_dir="output", public_api_only=False):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File {json_path} does not exist.")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    artifacts = data.get("artifacts", {})
    if not artifacts:
        raise Exception("Report does not contain artifacts section")

    is_py_query = search_term.lower().endswith(".py")
    term = search_term[:-3] if is_py_query else search_term
    term_lower = term.lower()
    filtered_artifacts = {}

    for key, value in artifacts.items():
        if public_api_only and isinstance(value, dict):
            c_count = value.get("consumer_count", 0)
            art_name = str(value.get("artifact", ""))
            if c_count == 0:
                continue
            if art_name.startswith("_") and not (art_name.startswith("__") and art_name.endswith("__")):
                continue

        key_lower = key.lower()
        match = False

        if is_py_query:
            if (f"{term_lower}::" in key_lower or key_lower.startswith(term_lower) or f".{term_lower}" in key_lower):
                match = True
        else:
            artifact_name = ""
            if isinstance(value, dict):
                artifact_name = str(value.get("artifact", "")).lower()

            if (key_lower.startswith(term_lower + "::") or
                f".{term_lower}::" in key_lower or
                f"::{term_lower}" in key_lower or
                key_lower == term_lower or
                artifact_name == term_lower):
                match = True

            if matches_term(value, term, is_py_query):
                if not consumer_only_match(value, term):
                    match = True

        if match:
            filtered_artifacts[key] = value

    parsed_data = {
        "runtime": data.get("runtime", {}),
        "module_count": data.get("module_count", 0),
        "artifact_count": len(filtered_artifacts),
        "shared_artifact_count": data.get("shared_artifact_count", 0),
        "artifacts": filtered_artifacts
    }

    sanitized_name = search_term.replace(".", "_").replace("/", "_")
    output_filename = f"parsed_{sanitized_name}.json"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)

    return output_path

def run_parser_window():
    parser_win = tk.Toplevel()
    parser_win.title("Parser JSON")

    state = load_state()
    parser_geom = state.get("parser_geometry", "540x350")
    parser_win.geometry(parser_geom)
    parser_win.configure(bg=BG)

    ttk.Label(parser_win, text="Parse JSON", style="Header.TLabel").pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, 0))
    sub_label = ttk.Label(parser_win, text="Filter artifact report by file name or symbol (it must be a full artifact JSON report)", style="Sub.TLabel")
    sub_label.pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))
    
    p_tooltip = HeaderTooltipManager(sub_label, "Filter artifact report by file name or symbol (it must be a full artifact JSON report)")

    ttk.Label(parser_win, text="JSON File", style="Field.TLabel").pack(anchor="w", padx=PAD_LG)

    json_path_var = tk.StringVar(value=state.get("json_file", ""))
    frame_file = ttk.Frame(parser_win)
    frame_file.pack(fill="x", padx=PAD_LG, pady=(2, PAD_MD))
    frame_file.columnconfigure(0, weight=1)

    ttk.Entry(frame_file, textvariable=json_path_var).grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))

    def browse_json():
        output_dir = os.path.abspath("output")
        if not os.path.exists(output_dir):
            output_dir = os.getcwd()
        path = filedialog.askopenfilename(initialdir=output_dir, filetypes=[("JSON files", "*.json")])
        if path:
            json_path_var.set(path)
            save_state(json_file=path)

    b_browse = ttk.Button(frame_file, text="Browse…", style="Secondary.TButton", command=browse_json)
    b_browse.grid(row=0, column=1)
    p_tooltip.bind_tooltip(b_browse, "Select JSON file generated by Repo Guardian.")

    ttk.Label(parser_win, text="File name or symbol (e.g. main.py or main)", style="Field.TLabel").pack(anchor="w", padx=PAD_LG)

    name_entry = ttk.Entry(parser_win)
    name_entry.insert(0, state.get("search_term", ""))
    name_entry.pack(fill="x", padx=PAD_LG, pady=(2, PAD_LG))

    public_api_only_var = tk.BooleanVar(value=state.get("public_api_only", False))
    cb_api = ttk.Checkbutton(
        parser_win,
        text="Public API Only (hide elements with consumer_count=0 and private)",
        variable=public_api_only_var,
        style="TCheckbutton"
    )
    cb_api.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_LG))
    p_tooltip.bind_tooltip(cb_api, "Filter out private and unused artifacts from the parsed report.")

    def on_closing():
        save_state(
            parser_geometry=parser_win.geometry(),
            search_term=name_entry.get(),
            public_api_only=public_api_only_var.get()
        )
        parser_win.destroy()

    def execute_parsing():
        json_path = json_path_var.get()
        term = name_entry.get()
        public_api = public_api_only_var.get()

        if not json_path or not term:
            messagebox.showwarning("Error", "Fill in both paths")
            return

        def task():
            return parse_and_filter_json(json_path, term, public_api_only=public_api)

        def on_success(out):
            messagebox.showinfo("Success", f"Output file:\n{out}")
            on_closing()

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        run_with_progress(
            parser_win, progress_bar, task,
            on_success=on_success, on_error=on_error, buttons=[parse_btn]
        )

    parse_btn = ttk.Button(parser_win, text="Parse JSON", style="Primary.TButton", command=execute_parsing)
    parse_btn.pack(padx=PAD_LG, pady=(0, PAD_MD), fill="x")
    p_tooltip.bind_tooltip(parse_btn, "Execute filtering and generate a new parsed JSON report.")

    progress_bar = create_progress_bar(parser_win)

    parser_win.protocol("WM_DELETE_WINDOW", on_closing)
