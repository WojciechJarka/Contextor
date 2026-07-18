# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox

from pathlib import Path
import json
import shutil
import os


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
    if not STATE_FILE.exists():

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
        "600x500"
    )


    items = load_exclude_state()


    listbox = tk.Listbox(
        win,
        selectmode=tk.MULTIPLE,
        width=70,
        height=18
    )

    listbox.pack(
        pady=10
    )


    def refresh():

        listbox.delete(
            0,
            tk.END
        )

        for item in items:

            listbox.insert(
                tk.END,
                item
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
            "250x120"
        )


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


        tk.Button(
            choice_win,
            text="Dodaj katalog",
            width=20,
            command=add_directory
        ).pack(
            pady=10
        )


        tk.Button(
            choice_win,
            text="Dodaj plik",
            width=20,
            command=add_file
        ).pack(
            pady=5
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


        for index in reversed(
            listbox.curselection()
        ):

            rel = items[index]

            source = repo / rel


            if source.exists():

                move_to_temporary(
                    source
                )


        save_manifest(
            repo,
            items
        )


        refresh()



    def restore_selected():

        selected = list(
            reversed(
                listbox.curselection()
            )
        )


        for index in selected:

            rel = items[index]

            restore_from_temporary(
                Path(rel)
            )

            items.pop(
                index
            )


        save_exclude_state(
            items
        )

        refresh()



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



    tk.Button(
        win,
        text="+ Dodaj",
        command=add_item
    ).pack(
        pady=5
    )


    tk.Button(
        win,
        text="Wyklucz zaznaczone",
        command=exclude_selected
    ).pack(
        pady=5
    )


    tk.Button(
        win,
        text="Usuń zaznaczone / Przywróć",
        command=restore_selected
    ).pack(
        pady=5
    )


    tk.Button(
        win,
        text="Przywróć wszystko",
        command=restore_all
    ).pack(
        pady=5
    )


    refresh()
