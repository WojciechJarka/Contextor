# -*- coding: utf-8 -*-
"""
ui/exclude_gui.py

Interface for maintaining project exclusion manifests.
Controls moving files to/from exclude zones outside project scope.
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
    # Now it only acts as a state cleaner just in case.
    save_exclude_state(items)

def load_exclude_state():

    state_file = get_state_file()
    if not state_file.exists():

        return []

    try:

        with open(
            state_file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            return data.get(
                "excluded",
                []
            )

    except Exception:

        return []



def save_exclude_state(items):
    state_file = get_state_file()
    with open(
        state_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "excluded": items
            },
            f,
            indent=4,
            ensure_ascii=False
        )

def save_manifest(repo, items):
    pass # No longer needed - we don't move files

def move_to_temporary(path):
    pass # No longer needed

def restore_from_temporary(relative):
    pass # No longer needed


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
        "620x520"
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

    items = load_exclude_state()

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


    def refresh():

        listbox.delete(
            0,
            tk.END
        )

        repo = find_repo_root()

        for item in items:

            original = repo / item

            if original.exists():

                status = "[ACTIVE]"

            else:

                status = "[EXCLUDED]"


            listbox.insert(
                tk.END,
                f"{status} {item}"
            )


    def add_item():

        repo = find_repo_root()

        if not repo:

            messagebox.showwarning(
                "Error",
                "No selected repo"
            )

            return


        choice_win = tk.Toplevel()

        choice_win.title(
            "Add exclusion"
        )

        choice_win.geometry(
            "260x150"
        )
        choice_win.configure(bg=BG)


        def add_directory():

            path = filedialog.askdirectory(
                initialdir=str(repo)
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
                ]
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
                "Selected element is not in the repo"
            )

            return


        if rel not in items:

            items.append(
                rel
            )

            save_exclude_state(
                items
            )

            refresh()



    def exclude_selected():
        moved = []
        for index in reversed(listbox.curselection()):
            rel = items[index]
            moved.append(rel)

        # Logiczne wykluczenie to sam zapis stanu (nie ma już przenoszenia)
        refresh()

        if moved:
            messagebox.showinfo(
                "Excluded",
                "Logically excluded:\n\n" + "\n".join(moved)
            )


        if moved:

            messagebox.showinfo(
                "Excluded",
                "Moved to temporary:\n\n"
                +
                "\n".join(
                    moved
                )
            )



    def restore_selected():
        selected = list(reversed(listbox.curselection()))
        restored = []
        for index in selected:
            rel = items[index]
            restored.append(rel)
            items.pop(index)

        save_exclude_state(items)
        refresh()

        if restored:
            messagebox.showinfo(
                "Restored",
                "Restored from exclusion:\n\n" + "\n".join(restored)
            )



    def restore_all():
        items.clear()
        save_exclude_state(items)
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
            messagebox.showwarning("Error", "No selected repo")
            return
        name = simpledialog.askstring("Save Preset", "Enter preset name:", parent=win)
        if not name: return
        presets = load_presets_dict()
        presets[name] = list(items)
        save_presets_dict(presets)
        messagebox.showinfo("Saved", f"Preset '{name}' saved.")

    def load_preset():
        if not find_repo_root():
            messagebox.showwarning("Error", "No selected repo")
            return
        presets = load_presets_dict()
        if not presets:
            messagebox.showinfo("Presets", "No saved presets found for this repository.")
            return
        
        def on_select(name):
            preset_items = presets[name]
            items.clear()
            items.extend(preset_items)
            save_exclude_state(items)
            refresh()
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
            messagebox.showinfo("Presets", "No saved presets found for this repository.")
            return
            
        def on_select(name):
            confirm = messagebox.askyesno("Confirm Delete", f"Delete preset '{name}'?", parent=sel_win)
            if confirm:
                del presets[name]
                save_presets_dict(presets)
                messagebox.showinfo("Deleted", f"Preset '{name}' deleted.")
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
    e_tooltip.bind_tooltip(b_exc, "Mark selected files as excluded (soft-filter).")

    b_res = ttk.Button(actions, text="Restore selected", style="Secondary.TButton", command=restore_selected)
    b_res.pack(side="left", padx=(0, PAD_SM))
    e_tooltip.bind_tooltip(b_res, "Remove selected files from the exclusion list.")

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
