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



def run_exclude_window():

    win = tk.Toplevel()

    win.title(
        "Exclude Manager"
    )

    win.geometry(
        "700x520"
    )
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
    candidates: list = _state.get("candidates", [])
    excluded_set: set = set(_state.get("excluded", []))

    def _persist():
        """Save current in-memory state to disk."""
        _save_exclude_state_raw({
            "candidates": candidates,
            "excluded": list(excluded_set)
        })

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


    def restore_selected():
        """
        For [Excluded] items  -> removes them from excluded_set (back to Active).
        For [Active] items    -> removes them entirely from candidates list.
        """
        selected = list(reversed(listbox.curselection()))
        if not selected:
            messagebox.showinfo("Restore", "Please select at least one item.", parent=win)
            return

        restored_to_active = []
        removed_entirely = []

        for index in selected:
            rel = candidates[index]
            if rel in excluded_set:
                excluded_set.remove(rel)
                restored_to_active.append(rel)
            else:
                candidates.pop(index)
                removed_entirely.append(rel)

        _persist()
        refresh()

        parts = []
        if restored_to_active:
            parts.append("Restored to Active:\n" + "\n".join(restored_to_active))
        if removed_entirely:
            parts.append("Removed from manager:\n" + "\n".join(removed_entirely))

        if parts:
            messagebox.showinfo("Restored", "\n\n".join(parts), parent=win)


    def restore_all():
        candidates.clear()
        excluded_set.clear()
        _persist()
        refresh()

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

    def save_preset():
        if not find_repo_root():
            messagebox.showwarning("Error", "No selected repo", parent=win)
            return
        name = simpledialog.askstring("Save Preset", "Enter preset name:", parent=win)
        if not name: return
        presets = load_presets_dict()
        presets[name] = {
            "candidates": list(candidates),
            "excluded": list(excluded_set)
        }
        save_presets_dict(presets)
        messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=win)

    def load_preset():
        if not find_repo_root():
            messagebox.showwarning("Error", "No selected repo", parent=win)
            return
        presets = load_presets_dict()
        if not presets:
            messagebox.showinfo("Presets", "No saved presets found for this repository.", parent=win)
            return

        def on_select(name):
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
        for p in presets.keys():
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
                messagebox.showinfo("Deleted", f"Preset '{name}' deleted.", parent=sel_win)
            sel_win.destroy()

        sel_win = tk.Toplevel(win)
        sel_win.title("Delete Preset")
        sel_win.geometry("300x300")
        sel_win.configure(bg=BG)
        sel_win.transient(win)

        listb = tk.Listbox(sel_win, bg=SURFACE, fg=TEXT, selectbackground=PRIMARY, selectforeground="#ffffff", borderwidth=0, highlightthickness=1)
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
        for p in presets.keys():
            listb.insert(tk.END, p)

        def del_btn():
            sel = listb.curselection()
            if sel: on_select(listb.get(sel[0]))
        ttk.Button(sel_win, text="Delete", command=del_btn, style="Danger.Ghost.TButton").pack(pady=PAD_SM)

    actions = ttk.Frame(win)
    actions.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

    b_add = ttk.Button(actions, text="+ Add", style="Secondary.TButton", command=add_item)
    b_add.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_add, "Add new files or directories to the exclusion list.")

    b_exc = ttk.Button(actions, text="Exclude selected", style="Secondary.TButton", command=exclude_selected)
    b_exc.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_exc, "Mark selected Active items as Excluded (soft-filter).")

    b_res = ttk.Button(actions, text="Restore selected", style="Secondary.TButton", command=restore_selected)
    b_res.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_res, "Restore Excluded items to Active, or remove Active items from the list.")

    b_res_all = ttk.Button(actions, text="Restore all", style="Danger.Ghost.TButton", command=restore_all)
    b_res_all.pack(side="left")
    e_tooltip.bind_tooltip(b_res_all, "Clear the entire exclusion list for this repository.")

    preset_actions = ttk.Frame(win)
    preset_actions.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

    b_sv = ttk.Button(preset_actions, text="Save Preset", command=save_preset, style="Secondary.TButton")
    b_sv.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_sv, "Save the current exclusion list as a reusable preset for this repo.")

    b_ld = ttk.Button(preset_actions, text="Load Preset", command=load_preset, style="Secondary.TButton")
    b_ld.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_ld, "Load a saved exclusion preset.")

    b_dl = ttk.Button(preset_actions, text="Delete Preset", command=delete_preset, style="Danger.Ghost.TButton")
    b_dl.pack(side="left")
    e_tooltip.bind_tooltip(b_dl, "Delete a saved exclusion preset.")

    refresh()
