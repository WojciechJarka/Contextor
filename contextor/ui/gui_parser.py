"""
ui/gui_parser.py

Search tool GUI for filtering JSON output matrices,
exploring semantic linkages and public API intersections.
"""

import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from contextor.ui import theme
from contextor.ui.path_memory import load_state, save_state
from contextor.ui.progress_widget import create_progress_bar, run_with_progress
from contextor.ui.theme import PAD_LG, PAD_MD, PAD_SM, HeaderTooltipManager


# ==========================================================
# WARNING: INDEXED DEPENDENCY
# This parser expects a Compact Artifacts Report (schema v2) 
# where modules are mapped to integer indices.
# ==========================================================
def parse_and_filter_json(json_path, search_term, output_dir="output", public_api_only=False):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File {json_path} does not exist.")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    artifacts = data.get("artifacts", {})
    modules = data.get("modules", [])
    if not artifacts or not modules:
        raise Exception("Report must be a compact artifact report containing 'artifacts' and 'modules'.")

    is_py_query = search_term.lower().endswith(".py")
    term = search_term[:-3] if is_py_query else search_term
    filtered_artifacts = {}
    
    # Pre-compute matching module indices for file-based queries
    matching_module_indices = set()
    if is_py_query:
        for i, mod in enumerate(modules):
            # Matches e.g. "contextor.main", "contextor.core.main" for term="main"
            if mod == term or mod.endswith(f".{term}") or f".{term}." in mod or mod.startswith(f"{term}."):
                matching_module_indices.add(i)

    for key, value in artifacts.items():
        if public_api_only and isinstance(value, dict):
            c_count = value.get("consumer_count", 0)
            art_name = str(value.get("artifact", ""))
            if c_count == 0:
                continue
            if art_name.startswith("_") and not (
                art_name.startswith("__") and art_name.endswith("__")
            ):
                continue
                
        match = False

        if is_py_query:
            # === REGUŁY DLA PLIKU (np. main.py) ===
            definer_idx = value.get("definer_module")
            consumers_idx = value.get("consumer_module_indices", [])
            
            if definer_idx in matching_module_indices:
                match = True
            elif matching_module_indices.intersection(consumers_idx):
                match = True

        else:
            # === REGUŁY DLA SYMBOLU (np. main) ===
            art_name = str(value.get("artifact", ""))
            art_id = str(value.get("artifact_id", key))
            sig = str(value.get("signature", ""))
            
            if term == art_name or f"::{term}" in art_id or f" {term}(" in sig or term in art_id:
                match = True

        if match:
            filtered_artifacts[key] = value

    parsed_data = {
        "_format_version": data.get("_format_version", "2"),
        "_format_note": data.get("_format_note", ""),
        "report_header": data.get("report_header", {}),
        "runtime": data.get("runtime", {}),
        "debug_info": data.get("debug_info", {}),
        "module_count": data.get("module_count", 0),
        "artifact_count": len(filtered_artifacts),
        "shared_artifact_count": data.get("shared_artifact_count", 0),
        "modules": modules,
        "artifacts": filtered_artifacts,
    }

    sanitized_name = search_term.replace(".", "_").replace("/", "_")
    prefix = "parsed_api_compact" if public_api_only else "parsed_compact"
    
    from datetime import datetime
    datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{prefix}_{sanitized_name}_{datestamp}.json"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)

    return output_path



def run_parser_window(parent=None):
    parser_win = tk.Toplevel(parent) if parent else tk.Toplevel()
    parser_win.title("Parser JSON")

    state = load_state()
    parser_pos = state.get("parser_pos", "")
    if parser_pos:
        parser_win.geometry(parser_pos)

    parser_win.minsize(700, 250)
    parser_win.configure(bg=theme.BG)
    theme.retint(parser_win)

    ttk.Label(parser_win, text="Parse JSON", style="Header.TLabel").pack(
        anchor="w", padx=PAD_LG, pady=(PAD_LG, 0)
    )
    sub_label = ttk.Label(
        parser_win,
        text="Filter artifact report by file name or symbol (it must be a full artifact JSON report)",
        style="Sub.TLabel",
    )
    sub_label.pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))

    p_tooltip = HeaderTooltipManager(
        sub_label,
        "Filter artifact report by file name or symbol (it must be a full artifact JSON report)",
    )

    ttk.Label(parser_win, text="JSON File", style="Field.TLabel").pack(anchor="w", padx=PAD_LG)

    json_path_var = tk.StringVar(value=state.get("json_file", ""))
    frame_file = ttk.Frame(parser_win)
    frame_file.pack(fill="x", padx=PAD_LG, pady=(2, PAD_MD))
    frame_file.columnconfigure(0, weight=1)

    ttk.Entry(frame_file, textvariable=json_path_var).grid(
        row=0, column=0, sticky="ew", padx=(0, PAD_SM)
    )

    def browse_json():
        output_dir = os.path.abspath("output")
        if not os.path.exists(output_dir):
            output_dir = os.getcwd()
        path = filedialog.askopenfilename(
            initialdir=output_dir, filetypes=[("JSON files", "*.json")]
        )
        if path:
            json_path_var.set(path)
            save_state(json_file=path)

    b_browse = ttk.Button(
        frame_file, text="Browse…", style="Secondary.TButton", command=browse_json
    )
    b_browse.grid(row=0, column=1)
    p_tooltip.bind_tooltip(b_browse, "Select JSON file generated by Contextor.")

    ttk.Label(
        parser_win, text="File name or symbol (e.g. main.py or main)", style="Field.TLabel"
    ).pack(anchor="w", padx=PAD_LG)

    search_var = tk.StringVar(value=state.get("search_term", ""))
    name_entry = ttk.Entry(parser_win, textvariable=search_var)
    name_entry.pack(fill="x", padx=PAD_LG, pady=(2, PAD_LG))

    public_api_var = tk.BooleanVar(value=state.get("public_api_only", False))
    cb_api = ttk.Checkbutton(
        parser_win,
        text="Public API Only (hide elements with consumer_count=0 and private)",
        variable=public_api_var,
        style="TCheckbutton",
    )
    cb_api.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_LG))
    p_tooltip.bind_tooltip(
        cb_api, "Filter out private and unused artifacts from the parsed report."
    )

    def on_closing():
        import re

        geom = parser_win.geometry()
        m = re.match(r"^(\d+x\d+)([+-]?\d+)([+-]?\d+)$", geom.replace("+-", "-"))
        if m:
            size = m.group(1)
            x, y = max(0, int(m.group(2))), max(0, int(m.group(3)))
            pos = f"{size}+{x}+{y}"
        else:
            pos = ""

        save_state(
            parser_pos=pos, search_term=search_var.get(), public_api_only=public_api_var.get()
        )
        parser_win.destroy()

    def execute_parsing():
        json_path = json_path_var.get()
        term = search_var.get()
        public_api = public_api_var.get()

        if not json_path or not term:
            messagebox.showwarning("Error", "Fill in both paths", parent=parser_win)
            return

        def task():
            return parse_and_filter_json(json_path, term, public_api_only=public_api)

        def on_success(out):
            messagebox.showinfo("Success", f"Output file:\n{out}", parent=parser_win)

        def on_error(exc):
            messagebox.showerror("Error", str(exc), parent=parser_win)

        run_with_progress(
            parser_win,
            progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=[parse_btn],
        )

    parse_btn = ttk.Button(
        parser_win, text="Parse JSON", style="Primary.TButton", command=execute_parsing
    )
    parse_btn.pack(padx=PAD_LG, pady=(0, PAD_MD), fill="x")
    p_tooltip.bind_tooltip(parse_btn, "Execute filtering and generate a new parsed JSON report.")

    progress_bar = create_progress_bar(parser_win)

    parser_win.protocol("WM_DELETE_WINDOW", on_closing)
    return parser_win
