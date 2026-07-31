# -*- coding: utf-8 -*-
"""
ui/exclude_gui.py

Interface for maintaining project exclusion manifests.
Controls soft-exclusion of files/directories from analysis scope.
Exclusions are logical (state-based), not physical (no file moving).
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

from pathlib import Path
import json
import shutil
import os

from repo_guardian.ui.theme import BG, SURFACE, BORDER, TEXT, PRIMARY, PAD_SM, PAD_MD, PAD_LG, HeaderTooltipManager


MANIFEST_NAME = "manifest.json"


# Auto-exclude categories have been removed in favor of hardcoded logic in the backend.


def get_state_file():

    repo = find_repo_root()

    if not repo:

        return (
            Path(__file__).resolve().parent /
            "exclude_state.json"
        )


    repo_name = repo.name

    safe_name = (
        repo_name
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


    return (
        Path(__file__).resolve().parent /
        f"exclude_state_{safe_name}.json"
    )

def get_preset_file():
    repo = find_repo_root()
    if not repo:
        return (Path(__file__).resolve().parent / "exclude_presets.json")
    repo_name = repo.name
    safe_name = (repo_name.replace(" ", "_").replace("/", "_").replace("\\", "_"))
    return (Path(__file__).resolve().parent / f"exclude_presets_{safe_name}.json")


def load_presets_dict():
    p_file = get_preset_file()
    if not p_file.exists(): return {}
    try:
        with open(p_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_presets_dict(d):
    p_file = get_preset_file()
    with open(p_file, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=4, ensure_ascii=False)

def reapply_excludes(repo_root, items):
    # This function originally moved items to temporary directory.
    # Now it only acts as a state cleaner - soft excludes only.
    _save_exclude_state_raw({"candidates": items, "excluded": items})


def _load_exclude_state_raw():
    """Load raw state dict from disk. Returns dict with 'candidates' and 'excluded' keys."""
    state_file = get_state_file()
    if not state_file.exists():
        return {"candidates": [], "excluded": []}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Backwards compatibility: old format stored only {"excluded": [...]}
            if "candidates" not in data:
                old_excluded = data.get("excluded", [])
                return {"candidates": list(old_excluded), "excluded": list(old_excluded)}
            return data
    except Exception:
        return {"candidates": [], "excluded": []}


def _save_exclude_state_raw(data: dict):
    """Save raw state dict to disk."""
    state_file = get_state_file()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_exclude_state():
    """Public helper: returns the list of actively excluded paths (for analysis filters)."""
    return _load_exclude_state_raw().get("excluded", [])


def save_exclude_state(items):
    """Public helper: save a flat list as excluded (backwards-compatible API)."""
    _save_exclude_state_raw({"candidates": items, "excluded": items})


def save_manifest(repo, items):
    pass  # No longer needed - we don't move files

def move_to_temporary(path):
    pass  # No longer needed

def restore_from_temporary(relative):
    pass  # No longer needed


def find_repo_root():

    from repo_guardian.ui.path_memory import load_state

    state = load_state()

    repo = state.get(
        "repository",
        ""
    )

    if repo:

        return Path(repo)

    return None



# We already defined empty move/restore at the top



def run_exclude_window(parent=None):

    win = tk.Toplevel(parent) if parent else tk.Toplevel()

    win.title("Exclude Manager")
    
    from repo_guardian.ui.path_memory import load_state, save_state
    state = load_state()
    exclude_pos = state.get("exclude_pos", "")
    if exclude_pos:
        win.geometry(exclude_pos)

    win.minsize(800, 600)
    win.configure(bg=BG)

    ttk.Label(win, text="Exclude Manager", style="Header.TLabel").pack(
        anchor="w", padx=PAD_LG, pady=(PAD_LG, 0)
    )
    sub_label = ttk.Label(
        win,
        text="Files and directories temporarily excluded from analysis",
        style="Sub.TLabel",
    )
    sub_label.pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))

    e_tooltip = HeaderTooltipManager(sub_label, "Files and directories temporarily excluded from analysis")

    # --- Internal state (Soft Excludes) ---
    # candidates: all paths added to the manager (shown in list)
    # excluded_set: subset of candidates that are currently soft-excluded
    _state = _load_exclude_state_raw()
    current_preset_name = _state.get("current_preset", None)

    candidates: list = _state.get("candidates", [])
    excluded_set: set = set(_state.get("excluded", []))
    
    original_candidates = list(candidates)
    original_excluded_set = set(excluded_set)

    presets = load_presets_dict()
    if current_preset_name and current_preset_name not in presets:
        current_preset_name = None

    def _persist():
        """Save current in-memory state to disk."""
        _save_exclude_state_raw({
            "candidates": candidates,
            "excluded": list(excluded_set),
            "current_preset": current_preset_name,
        })

    preset_label_var = tk.StringVar(value=f"Active Preset: {current_preset_name}" if current_preset_name else "Active Preset: None")
    ttk.Label(win, textvariable=preset_label_var, style="Sub.TLabel", foreground=PRIMARY).pack(
        anchor="w", padx=PAD_LG, pady=(0, PAD_MD)
    )

    list_frame = ttk.Frame(win, style="Card.TFrame")
    list_frame.pack(fill="both", expand=True, padx=PAD_LG)

    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox = tk.Listbox(
        list_frame,
        selectmode=tk.MULTIPLE,
        yscrollcommand=scrollbar.set,
        bg=SURFACE,
        fg=TEXT,
        selectbackground=PRIMARY,
        selectforeground="#ffffff",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        relief="flat",
        borderwidth=0,
        font=("Segoe UI", 10),
    )

    listbox.pack(
        fill="both",
        expand=True,
    )
    scrollbar.config(command=listbox.yview)


    def refresh(keep_selection: list = None):
        """Repopulate the listbox. Optionally re-select given indices."""
        listbox.delete(0, tk.END)

        for item in candidates:
            if item in excluded_set:
                label = f"[Excluded] - select this file / folder and press Restore  |  {item}"
            else:
                label = f"[Active]   - select this file / folder and press Exclude   |  {item}"
            listbox.insert(tk.END, label)

        if keep_selection:
            for idx in keep_selection:
                try:
                    listbox.selection_set(idx)
                except Exception:
                    pass


    def add_item():

        repo = find_repo_root()

        if not repo:

            messagebox.showwarning(
                "Error",
                "No selected repo",
                parent=win
            )

            return


        choice_win = tk.Toplevel(win)

        choice_win.title(
            "Add exclusion"
        )

        choice_win.geometry(
            "260x150"
        )
        choice_win.configure(bg=BG)
        choice_win.transient(win)


        def add_directory():

            path = filedialog.askdirectory(
                initialdir=str(repo),
                parent=choice_win
            )

            process_selected_path(
                path
            )

            choice_win.destroy()


        def add_file():

            path = filedialog.askopenfilename(
                initialdir=str(repo),
                filetypes=[
                    (
                        "All files",
                        "*.*"
                    )
                ],
                parent=choice_win
            )

            process_selected_path(
                path
            )

            choice_win.destroy()


        ttk.Button(
            choice_win,
            text="Add directory",
            style="Secondary.TButton",
            command=add_directory
        ).pack(
            padx=PAD_MD,
            pady=(PAD_MD, PAD_SM),
            fill="x"
        )


        ttk.Button(
            choice_win,
            text="Add file",
            style="Secondary.TButton",
            command=add_file
        ).pack(
            padx=PAD_MD,
            pady=(0, PAD_MD),
            fill="x"
        )



    def process_selected_path(path):

        repo = find_repo_root()

        if not path:

            return


        p = Path(path)


        try:

            rel = str(
                p.relative_to(repo)
            )

        except Exception:

            messagebox.showwarning(
                "Error",
                "Selected element is not in the repo",
                parent=win
            )

            return


        if rel not in candidates:
            candidates.append(rel)
            _persist()
            refresh()
            # Highlight newly added item
            new_idx = candidates.index(rel)
            listbox.selection_set(new_idx)
            listbox.see(new_idx)


    def exclude_selected():
        """Mark selected [Active] entries as [Excluded]."""
        selected = list(listbox.curselection())
        if not selected:
            messagebox.showinfo("Exclude", "Please select at least one item.", parent=win)
            return

        moved = []
        for index in selected:
            rel = candidates[index]
            if rel not in excluded_set:
                excluded_set.add(rel)
                moved.append(rel)

        _persist()
        refresh(keep_selection=selected)

        if moved:
            messagebox.showinfo(
                "Excluded",
                "Soft-excluded (hidden from analysis):\n\n" + "\n".join(moved),
                parent=win
            )
        else:
            messagebox.showinfo(
                "Excluded",
                "Selected items were already excluded.",
                parent=win
            )


    def remove_selected():
        selected = list(reversed(listbox.curselection()))
        if not selected:
            messagebox.showinfo("Delete", "Please select at least one item.", parent=win)
            return

        removed_entirely = []
        for index in selected:
            rel = candidates[index]
            if rel in excluded_set:
                excluded_set.remove(rel)
            candidates.pop(index)
            removed_entirely.append(rel)

        _persist()
        refresh()
        messagebox.showinfo("Deleted", "Removed from manager entirely:\n\n" + "\n".join(removed_entirely), parent=win)

    def restore_selected():
        """
        For [Excluded] items  -> removes them from excluded_set (back to Active).
        """
        selected = list(listbox.curselection())
        if not selected:
            messagebox.showinfo("Restore", "Please select at least one item.", parent=win)
            return

        restored_to_active = []
        for index in selected:
            rel = candidates[index]
            if rel in excluded_set:
                excluded_set.remove(rel)
                restored_to_active.append(rel)

        _persist()
        refresh(keep_selection=selected)

        if restored_to_active:
            messagebox.showinfo("Restored", "Restored to Active:\n\n" + "\n".join(restored_to_active), parent=win)
        else:
            messagebox.showinfo("Restored", "Selected items were already Active.", parent=win)


    def restore_all():
        candidates.clear()
        excluded_set.clear()
        _persist()
        refresh()

    def save_preset():
        if not find_repo_root():
            messagebox.showwarning("Error", "No selected repo", parent=win)
            return
        presets = load_presets_dict()

        dlg = tk.Toplevel(win)
        dlg.title("Save Preset")
        dlg.geometry("340x360")
        dlg.configure(bg=BG)
        dlg.transient(win)
        dlg.grab_set()

        ttk.Label(dlg, text="Existing presets:", style="Sub.TLabel").pack(
            anchor="w", padx=PAD_MD, pady=(PAD_MD, PAD_SM)
        )

        listb = tk.Listbox(
            dlg, bg=SURFACE, fg=TEXT, selectbackground=PRIMARY,
            selectforeground="#ffffff", borderwidth=0, highlightthickness=1,
            highlightbackground=BORDER, font=("Segoe UI", 10), height=8
        )
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_MD)
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)

        ttk.Label(dlg, text="Preset name:", style="Sub.TLabel").pack(
            anchor="w", padx=PAD_MD, pady=(PAD_SM, 2)
        )
        name_entry = ttk.Entry(dlg, font=("Segoe UI", 10))
        name_entry.pack(fill=tk.X, padx=PAD_MD)
        name_entry.focus_set()

        def on_listbox_select(event):
            sel = listb.curselection()
            if sel:
                name_entry.delete(0, tk.END)
                name_entry.insert(0, listb.get(sel[0]))

        listb.bind("<<ListboxSelect>>", on_listbox_select)

        def do_save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Error", "Please enter a preset name.", parent=dlg)
                return
            if name.lower() == "default":
                messagebox.showwarning("Error", "The name 'default' is reserved and read-only.", parent=dlg)
                return
            if name in presets:
                if not messagebox.askyesno(
                    "Overwrite?",
                    f"Preset '{name}' already exists.\nDo you want to overwrite it?",
                    parent=dlg
                ):
                    return

            presets[name] = {
                "candidates": list(candidates),
                "excluded": list(excluded_set),
            }
            save_presets_dict(presets)
            nonlocal current_preset_name
            current_preset_name = name
            preset_label_var.set(f"Active Preset: {name}")
            _persist()
            messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=dlg)
            dlg.destroy()

        btn_row = ttk.Frame(dlg)
        btn_row.pack(fill=tk.X, padx=PAD_MD, pady=PAD_MD)
        ttk.Button(btn_row, text="Save", command=do_save, style="Primary.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Cancel", command=dlg.destroy, style="Ghost.TButton").pack(side=tk.RIGHT, padx=(0, PAD_SM))
        dlg.bind("<Return>", lambda e: do_save())


    def load_preset():
        if not find_repo_root():
            messagebox.showwarning("Error", "No selected repo", parent=win)
            return
        presets = load_presets_dict()

        def on_select(name):
            nonlocal current_preset_name
            if name == "default":
                candidates.clear()
                excluded_set.clear()
                current_preset_name = None
                preset_label_var.set("Active Preset: None")
                _persist()
                refresh()
                sel_win.destroy()
                return

            preset_data = presets[name]
            candidates.clear()
            excluded_set.clear()

            if isinstance(preset_data, list):
                # Backwards compat: old preset format was a flat list
                candidates.extend(preset_data)
                for x in preset_data:
                    excluded_set.add(x)
            elif isinstance(preset_data, dict):
                candidates.extend(preset_data.get("candidates", []))
                for x in preset_data.get("excluded", []):
                    excluded_set.add(x)

            current_preset_name = name
            preset_label_var.set(f"Active Preset: {name}")
            _persist()
            refresh()
            listbox.selection_set(0, tk.END)
            sel_win.destroy()

        sel_win = tk.Toplevel(win)
        sel_win.title("Load Preset")
        sel_win.geometry("300x300")
        sel_win.configure(bg=BG)
        sel_win.transient(win)

        listb = tk.Listbox(sel_win, bg=SURFACE, fg=TEXT, selectbackground=PRIMARY, selectforeground="#ffffff", borderwidth=0, highlightthickness=1)
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
        listb.insert(tk.END, "default")
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)

        def load_btn():
            sel = listb.curselection()
            if sel: on_select(listb.get(sel[0]))
        ttk.Button(sel_win, text="Load", command=load_btn, style="Primary.TButton").pack(pady=PAD_SM)

    def delete_preset():
        presets = load_presets_dict()
        if not presets:
            messagebox.showinfo("Presets", "No saved presets found for this repository.", parent=win)
            return

        def on_select(name):
            confirm = messagebox.askyesno("Confirm Delete", f"Delete preset '{name}'?", parent=sel_win)
            if confirm:
                del presets[name]
                save_presets_dict(presets)
                nonlocal current_preset_name
                if current_preset_name == name:
                    current_preset_name = None
                    preset_label_var.set("Active Preset: None")
                    _persist()
                messagebox.showinfo("Deleted", f"Preset '{name}' deleted.", parent=sel_win)
            sel_win.destroy()

        sel_win = tk.Toplevel(win)
        sel_win.title("Delete Preset")
        sel_win.geometry("300x300")
        sel_win.configure(bg=BG)
        sel_win.transient(win)

        listb = tk.Listbox(sel_win, bg=SURFACE, fg=TEXT, selectbackground=PRIMARY, selectforeground="#ffffff", borderwidth=0, highlightthickness=1)
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)

        def del_btn():
            sel = listb.curselection()
            if sel: on_select(listb.get(sel[0]))
        ttk.Button(sel_win, text="Delete", command=del_btn, style="Danger.Ghost.TButton").pack(pady=PAD_SM)

    def auto_exclude_non_python():
        """Scan repo root and exclude all non-Python structures (dirs without .py files, non-.py files)."""
        repo = find_repo_root()
        if not repo:
            messagebox.showwarning("Error", "No selected repo", parent=win)
            return

        added = []
        try:
            for item in sorted(repo.iterdir()):
                rel = item.relative_to(repo).as_posix()
                if rel in candidates:
                    continue
                if item.is_dir():
                    has_python = any(item.rglob("*.py"))
                    if not has_python:
                        candidates.append(rel)
                        excluded_set.add(rel)
                        added.append(rel)
                elif item.is_file():
                    if item.suffix.lower() != ".py":
                        candidates.append(rel)
                        excluded_set.add(rel)
                        added.append(rel)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=win)
            return

        _persist()
        refresh()

        if added:
            messagebox.showinfo(
                "Done",
                f"Excluded {len(added)} non-Python item(s):\n\n" + "\n".join(added[:20]) + ("\n..." if len(added) > 20 else ""),
                parent=win
            )
        else:
            messagebox.showinfo("Done", "No new non-Python structures found.", parent=win)

    actions = ttk.Frame(win)
    actions.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

    list_frame = ttk.LabelFrame(actions, text="List Management", padding=PAD_SM)
    list_frame.pack(side="left", fill="y", padx=(0, PAD_MD))

    b_add = ttk.Button(list_frame, text="+ Add", style="Secondary.TButton", command=add_item)
    b_add.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_add, "Add new files or directories to the list.")

    b_rem = ttk.Button(list_frame, text="- Del", style="Danger.Ghost.TButton", command=remove_selected)
    b_rem.pack(side="left")
    e_tooltip.bind_tooltip(b_rem, "Delete selected items from the list entirely.")

    state_frame = ttk.LabelFrame(actions, text="Exclusion State", padding=PAD_SM)
    state_frame.pack(side="left", fill="both", expand=True)

    b_exc = ttk.Button(state_frame, text="Exclude", style="Secondary.TButton", command=exclude_selected)
    b_exc.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_exc, "Mark selected items as Excluded (soft-filter).")

    b_res = ttk.Button(state_frame, text="Restore", style="Secondary.TButton", command=restore_selected)
    b_res.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_res, "Restore Excluded items to Active.")

    b_res_all = ttk.Button(state_frame, text="Restore all", style="Danger.Ghost.TButton", command=restore_all)
    b_res_all.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_res_all, "Clear the entire exclusion list.")

    b_auto = ttk.Button(state_frame, text="Auto-exclude non-Python", style="Secondary.TButton", command=auto_exclude_non_python)
    b_auto.pack(side="right")
    e_tooltip.bind_tooltip(b_auto, "Auto-exclude all top-level non-Python structures in the root.")

    preset_actions = ttk.Frame(win)
    preset_actions.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

    def load_default_preset():
        nonlocal current_preset_name
        current_preset_name = None
        preset_label_var.set("Active Preset: None")
        candidates.clear()
        excluded_set.clear()
        _persist()
        refresh()

    b_def = ttk.Button(preset_actions, text="Default", command=load_default_preset, style="Secondary.TButton")
    b_def.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_def, "Restore to default (no active preset, clear exclusions).")

    b_sv = ttk.Button(preset_actions, text="Save Preset", command=save_preset, style="Secondary.TButton")
    b_sv.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_sv, "Save the current exclusion list as a reusable preset for this repo.")

    b_ld = ttk.Button(preset_actions, text="Load Preset", command=load_preset, style="Secondary.TButton")
    b_ld.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_ld, "Load a saved exclusion preset.")

    b_dl = ttk.Button(preset_actions, text="Delete Preset", command=delete_preset, style="Danger.Ghost.TButton")
    b_dl.pack(side="left")
    e_tooltip.bind_tooltip(b_dl, "Delete a saved exclusion preset.")

    # --------------------------------------------------------
    # INFO SECTION
    # --------------------------------------------------------
    info_frame = ttk.LabelFrame(win, text="How filtering works under the hood")
    info_frame.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

    info_text_1 = (
        "• Auto-ignored by engine (always): All non-Python files (.json, .md, etc.),\n"
        "  as well as heavy structures like __pycache__, .git, venv, node_modules, dist, .idea."
    )
    ttk.Label(info_frame, text=info_text_1, foreground=TEXT).pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
    info_text_2 = (
        "• Exclude non-Python structures: Adds top-level non-Python directories to the list above,\n"
        "  preventing the engine from even attempting to traverse them. Strictly a performance optimization."
    )
    ttk.Label(info_frame, text=info_text_2, foreground=TEXT).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

    def handle_close(is_confirm=False):
        changed_from_start = (set(candidates) != set(original_candidates) or excluded_set != original_excluded_set)
        
        nonlocal current_preset_name
        if current_preset_name:
            presets = load_presets_dict()
            p_data = presets.get(current_preset_name, {})
            preset_changed = (sorted(candidates) != sorted(p_data.get("candidates", []))) or (sorted(list(excluded_set)) != sorted(p_data.get("excluded", [])))
            
            if preset_changed:
                ans = messagebox.askyesnocancel(
                    "Update Preset?",
                    f"Preset '{current_preset_name}' has unsaved changes.\n\nYES = Update preset and apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.",
                    parent=win
                )
                if ans is None:
                    return
                if ans is True:
                    presets[current_preset_name] = {
                        "candidates": list(candidates),
                        "excluded": list(excluded_set),
                    }
                    save_presets_dict(presets)
                    _persist()
                else:
                    _save_exclude_state_raw({
                        "candidates": original_candidates,
                        "excluded": list(original_excluded_set),
                        "current_preset": current_preset_name,
                    })
                win.destroy()
                return

        if is_confirm:
            _persist()
            win.destroy()
        else:
            if changed_from_start:
                ans = messagebox.askyesnocancel(
                    "Unsaved changes",
                    "You have unsaved changes.\n\nYES = Apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.",
                    parent=win
                )
                if ans is None:
                    return
                if ans is True:
                    _persist()
                else:
                    _save_exclude_state_raw({
                        "candidates": original_candidates,
                        "excluded": list(original_excluded_set),
                        "current_preset": current_preset_name,
                    })
                win.destroy()
            else:
                win.destroy()

    bottom_frame = ttk.Frame(win)
    bottom_frame.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))
    
    def _on_close(is_confirm):
        import re
        geom = win.geometry()
        m = re.search(r"(?:[+-]\d+){2}$", geom)
        pos = m.group(0) if m else ""
        from repo_guardian.ui.path_memory import save_state
        save_state(exclude_pos=pos)
        handle_close(is_confirm=is_confirm)

    ttk.Button(bottom_frame, text="Confirm", style="Primary.TButton", command=lambda: _on_close(is_confirm=True)).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", lambda: _on_close(is_confirm=False))
    
    from repo_guardian.ui.path_memory import load_state
    saved = load_state()
    if "exclude_pos" in saved:
        win.geometry(f"+{saved['exclude_pos']}")

    refresh()
    return win
