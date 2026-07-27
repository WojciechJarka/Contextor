# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pathlib import Path
import json
import shutil
import os

from repo_guardian.ui.theme import BG, SURFACE, BORDER, TEXT, PRIMARY, PAD_SM, PAD_MD, PAD_LG


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

def reapply_excludes(repo_root, items):

    repo_root = Path(repo_root)

    restored_items = []


    for item in items:

        source = repo_root / item


        if source.exists():

            move_to_temporary(
                source
            )

            restored_items.append(
                item
            )


    save_exclude_state(
        restored_items
    )


    save_manifest(
        repo_root,
        restored_items
    )

    # aktualizacja manifestu

    save_manifest(
        repo_root,
        items
    )

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

    temporary = repo / "temporary"

    temporary.mkdir(
        exist_ok=True
    )

    manifest = []


    for item in items:

        original = repo / item

        if original.exists():

            item_type = (
                "directory"
                if original.is_dir()
                else "file"
            )

        else:

            item_type = "unknown"


        manifest.append(
            {
                "original": item,
                "temporary": str(
                    Path("temporary") / item
                ),
                "type": item_type
            }
        )


    with open(
        temporary / MANIFEST_NAME,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "items": manifest
            },
            f,
            indent=4,
            ensure_ascii=False
        )


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



def move_to_temporary(path):

    repo = find_repo_root()

    if not repo:

        raise Exception(
            "Brak zapisanego repo root"
        )

    temporary = repo / "temporary"

    relative = path.relative_to(repo)

    destination = temporary / relative

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.move(
        str(path),
        str(destination)
    )



def restore_from_temporary(relative):

    repo = find_repo_root()

    temporary = repo / "temporary"

    source = temporary / relative

    destination = repo / relative


    if source.exists():

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        shutil.move(
            str(source),
            str(destination)
        )



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
    ttk.Label(
        win,
        text="Pliki i katalogi tymczasowo wyłączone z analizy",
        style="Sub.TLabel",
    ).pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))

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
                "Brak wybranego repo"
            )

            return


        choice_win = tk.Toplevel()

        choice_win.title(
            "Dodaj wykluczenie"
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
            text="Dodaj katalog",
            style="Secondary.TButton",
            command=add_directory
        ).pack(
            padx=PAD_MD,
            pady=(PAD_MD, PAD_SM),
            fill="x"
        )


        ttk.Button(
            choice_win,
            text="Dodaj plik",
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
                "Wybrany element nie jest w repo"
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

        repo = find_repo_root()

        moved = []


        for index in reversed(
            listbox.curselection()
        ):

            rel = items[index]

            source = repo / rel


            if source.exists():

                move_to_temporary(
                    source
                )

                moved.append(
                    rel
                )


        save_manifest(
            repo,
            items
        )


        refresh()


        if moved:

            messagebox.showinfo(
                "Wykluczono",
                "Przeniesiono do temporary:\n\n"
                +
                "\n".join(
                    moved
                )
            )



    def restore_selected():

        selected = list(
            reversed(
                listbox.curselection()
            )
        )


        restored = []


        for index in selected:

            rel = items[index]


            restore_from_temporary(
                Path(rel)
            )


            restored.append(
                rel
            )


            items.pop(
                index
            )


        save_exclude_state(
            items
        )


        refresh()


        if restored:

            messagebox.showinfo(
                "Przywrócono",
                "Przywrócono z temporary:\n\n"
                +
                "\n".join(
                    restored
                )
            )



    def restore_all():

        for rel in items:

            restore_from_temporary(
                Path(rel)
            )


        items.clear()

        save_exclude_state(
            items
        )


        repo = find_repo_root()

        manifest = repo / "temporary" / MANIFEST_NAME

        if manifest.exists():

            manifest.unlink()


        refresh()



    actions = ttk.Frame(win)
    actions.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

    ttk.Button(
        actions,
        text="+ Dodaj",
        style="Secondary.TButton",
        command=add_item
    ).pack(side="left", padx=(0, PAD_SM))

    ttk.Button(
        actions,
        text="Wyklucz zaznaczone",
        style="Secondary.TButton",
        command=exclude_selected
    ).pack(side="left", padx=(0, PAD_SM))

    ttk.Button(
        actions,
        text="Przywróć zaznaczone",
        style="Secondary.TButton",
        command=restore_selected
    ).pack(side="left", padx=(0, PAD_SM))

    ttk.Button(
        actions,
        text="Przywróć wszystko",
        style="Danger.Ghost.TButton",
        command=restore_all
    ).pack(side="left")

    refresh()
