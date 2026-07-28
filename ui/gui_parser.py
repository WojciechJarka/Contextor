# repo_guardian/ui/gui_parser.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import re

from repo_guardian.ui.path_memory import load_state, save_state
from repo_guardian.ui.progress_widget import create_progress_bar, run_with_progress
from repo_guardian.ui.theme import BG, PAD_SM, PAD_MD, PAD_LG


def matches_term(data, search_term, is_py_query):
    """
    Rekurencyjne przeszukiwanie struktury.

    is_py_query = True:
        szukamy pliku (.py)

    is_py_query = False:
        szukamy artefaktu/funkcji
    """

    if isinstance(data, dict):

        return any(
            matches_term(v, search_term, is_py_query)
            for v in data.values()
        )

    elif isinstance(data, list):

        return any(
            matches_term(i, search_term, is_py_query)
            for i in data
        )

    elif isinstance(data, str):

        if is_py_query:

            return bool(
                re.search(
                    rf"\.{re.escape(search_term)}(\.|$)",
                    data
                )
            )

        else:

            return bool(
                re.search(
                    rf"(?<!\.)\b{re.escape(search_term)}\b",
                    data
                )
            )

    return False



def consumer_only_match(value, term):
    """
    Sprawdza czy trafienie pochodzi wyłącznie
    z consumers.

    Jeśli term jest tylko nazwą modułu/pliku
    w consumers, blok powinien zostać pominięty.
    """

    if not isinstance(value, dict):

        return False


    consumers = value.get(
        "consumers",
        []
    )


    if term not in consumers:

        return False


    artifact = value.get(
        "artifact",
        ""
    )


    key_hits = False


    return (
        not artifact == term
        and
        not key_hits
    )



def parse_and_filter_json(
    json_path,
    search_term,
    output_dir="output",
    public_api_only=False,
):

    if not os.path.exists(json_path):

        raise FileNotFoundError(
            f"Plik {json_path} nie istnieje."
        )


    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)



    artifacts = data.get(
        "artifacts",
        {}
    )


    if not artifacts:

        raise Exception(
            "Raport nie zawiera sekcji artifacts"
        )



    is_py_query = (
        search_term.lower().endswith(".py")
    )


    term = (
        search_term[:-3]
        if is_py_query
        else search_term
    )


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



        # ===================================
        # szukanie pliku python
        # ===================================

        if is_py_query:


            if (
                f"{term_lower}::" in key_lower
                or
                key_lower.startswith(term_lower)
                or
                f".{term_lower}" in key_lower
            ):

                match = True



        # ===================================
        # szukanie artefaktu
        # ===================================

        else:


            artifact_name = ""

            if isinstance(value, dict):

                artifact_name = str(
                    value.get(
                        "artifact",
                        ""
                    )
                ).lower()



            if (

                key_lower.startswith(
                    term_lower + "::"
                )

                or

                f".{term_lower}::" in key_lower

                or

                f"::{term_lower}" in key_lower

                or

                key_lower == term_lower

                or

                artifact_name == term_lower

            ):

                match = True



            # Dopasowanie przez wartości,
            # ale tylko jeśli nie jest to
            # przypadek nazwy pliku w consumers

            if matches_term(
                value,
                term,
                is_py_query
            ):

                if not consumer_only_match(
                    value,
                    term
                ):

                    match = True



        if match:

            filtered_artifacts[key] = value



    parsed_data = {

        "runtime": data.get(
            "runtime",
            {}
        ),

        "module_count": data.get(
            "module_count",
            0
        ),

        "artifact_count": len(
            filtered_artifacts
        ),

        "shared_artifact_count": data.get(
            "shared_artifact_count",
            0
        ),

        "artifacts": filtered_artifacts

    }



    sanitized_name = (
        search_term
        .replace(".", "_")
        .replace("/", "_")
    )


    output_filename = (
        f"parsed_{sanitized_name}.json"
    )


    os.makedirs(
        output_dir,
        exist_ok=True
    )


    output_path = os.path.join(
        output_dir,
        output_filename
    )


    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            parsed_data,
            f,
            indent=2,
            ensure_ascii=False
        )


    return output_path




def run_parser_window():

    parser_win = tk.Toplevel()

    parser_win.title(
        "Parser JSON"
    )

    parser_win.geometry(
        "540x350"
    )
    parser_win.configure(bg=BG)

    ttk.Label(parser_win, text="Parsuj JSON", style="Header.TLabel").pack(
        anchor="w", padx=PAD_LG, pady=(PAD_LG, 0)
    )
    ttk.Label(
        parser_win,
        text="Przefiltruj raport artefaktów po nazwie pliku lub symbolu",
        style="Sub.TLabel",
    ).pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))

    ttk.Label(
        parser_win,
        text="Plik JSON",
        style="Field.TLabel",
    ).pack(
        anchor="w",
        padx=PAD_LG,
    )


    json_path_var = tk.StringVar()

    state = load_state()

    json_path_var.set(
        state["json_file"]
    )


    frame_file = ttk.Frame(
        parser_win
    )

    frame_file.pack(
        fill="x",
        padx=PAD_LG,
        pady=(2, PAD_MD)
    )
    frame_file.columnconfigure(0, weight=1)


    ttk.Entry(
        frame_file,
        textvariable=json_path_var,
    ).grid(
        row=0, column=0, sticky="ew", padx=(0, PAD_SM)
    )



    def browse_json():

        output_dir = os.path.abspath(
            "output"
        )


        if not os.path.exists(output_dir):

            output_dir = os.getcwd()


        path = filedialog.askopenfilename(
            initialdir=output_dir,
            filetypes=[
                (
                    "JSON files",
                    "*.json"
                )
            ]
        )


        if path:

            json_path_var.set(
                path
            )

            save_state(
                json_file=path
            )



    ttk.Button(
        frame_file,
        text="Browse…",
        style="Secondary.TButton",
        command=browse_json
    ).grid(
        row=0, column=1
    )



    ttk.Label(
        parser_win,
        text="Nazwa pliku lub symbolu (np. main.py lub main)",
        style="Field.TLabel",
    ).pack(
        anchor="w",
        padx=PAD_LG,
    )



    name_entry = ttk.Entry(
        parser_win,
    )


    name_entry.insert(
        0,
        state["search_term"]
    )


    name_entry.pack(
        fill="x",
        padx=PAD_LG,
        pady=(2, PAD_LG)
    )

    public_api_only_var = tk.BooleanVar(value=state.get("public_api_only", False))
    ttk.Checkbutton(
        parser_win,
        text="Tylko Public API (ukryj elementy z consumer_count=0 i prywatne)",
        variable=public_api_only_var,
        style="TCheckbutton"
    ).pack(anchor="w", padx=PAD_LG, pady=(0, PAD_LG))


    def execute_parsing():

        json_path = json_path_var.get()

        term = name_entry.get()
        public_api = public_api_only_var.get()

        save_state(
            search_term=term,
            public_api_only=public_api
        )


        if not json_path or not term:

            messagebox.showwarning(
                "Błąd",
                "Wypełnij obie ścieżki"
            )

            return


        def task():
            return parse_and_filter_json(
                json_path,
                term,
                public_api_only=public_api
            )


        def on_success(out):

            messagebox.showinfo(
                "Sukces",
                f"Plik wyjściowy:\n{out}"
            )

            parser_win.destroy()


        def on_error(exc):

            messagebox.showerror(
                "Błąd",
                str(exc)
            )


        run_with_progress(
            parser_win,
            progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=[parse_btn]
        )



    parse_btn = ttk.Button(
        parser_win,
        text="Parsuj JSON",
        style="Primary.TButton",
        command=execute_parsing
    )

    parse_btn.pack(
        padx=PAD_LG,
        pady=(0, PAD_MD),
        fill="x"
    )

    progress_bar = create_progress_bar(parser_win)
