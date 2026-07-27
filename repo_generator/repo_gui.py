# Repo_Guardian/repo_generator/repo_gui.py

# ============================================================
# Repo Guardian - Repo Builder GUI
# ============================================================

import tkinter as tk
from tkinter import filedialog, messagebox

import os
import subprocess
import shutil


# ============================================================
# KONFIGURACJA
# ============================================================

DEFAULT_EXTENSIONS = {
    ".py",
    ".json",
    ".parquet",
    ".txt",
    ".md",
    ".bat",
    ".vbs",
    ".js",
    ".sh",
    ".xml",
    ".yaml",
    ".yml",
    ".csv",
    ".ini",
    ".toml",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx"
}


# To NIE jest aktywny filtr przy starcie.
# Jest tylko domyślną zawartością okna filtrów.
# Po zapisaniu użytkownik decyduje co faktycznie pomijać.

DEFAULT_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",

    # środowiska Python / WinPython
    "winpython",
    "python",
    "Python",
    "python310",
    "python311",
    "Lib",
    "Scripts",
    "Include",

    # cache
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox"
}


# ============================================================
# IKONY CANVAS
# ============================================================

def draw_icon(canvas, icon_type):

    canvas.delete("all")


    if icon_type == "big_plus":

        canvas.create_line(
            17, 5,
            17, 30,
            fill="green",
            width=5
        )

        canvas.create_line(
            5, 17,
            30, 17,
            fill="green",
            width=5
        )


    elif icon_type == "small_plus":

        for x in (8, 17, 26):

            canvas.create_line(
                x,
                12,
                x,
                22,
                fill="green",
                width=2
            )

            canvas.create_line(
                x - 5,
                17,
                x + 5,
                17,
                fill="green",
                width=2
            )


    elif icon_type == "big_minus":

        canvas.create_line(
            5,
            17,
            30,
            17,
            fill="red",
            width=5
        )


    elif icon_type == "small_minus":

        for x in (8, 17, 26):

            canvas.create_line(
                x - 5,
                17,
                x + 5,
                17,
                fill="red",
                width=3
            )



def create_icon_button(
        parent,
        text,
        command,
        icon_type
):

    frame = tk.Frame(parent)

    frame.pack(
        side=tk.LEFT,
        padx=5
    )


    canvas = tk.Canvas(
        frame,
        width=35,
        height=35,
        highlightthickness=0
    )

    canvas.pack(
        side=tk.LEFT
    )


    draw_icon(
        canvas,
        icon_type
    )


    tk.Button(
        frame,
        text=text,
        command=command,
        height=2
    ).pack(
        side=tk.LEFT
    )



# ============================================================
# GŁÓWNA KLASA
# ============================================================

class RepoGenerator:


    def __init__(self, root):

        self.root = root

        self.root.title(
            "Repo Builder - Context Generator"
        )


        self.root.geometry(
            "1100x700"
        )


        # lista fizycznie dodanych plików
        self.files = []


        # aktywne filtry
        # domyślnie wszystko dozwolone
        self.extensions = set(
            DEFAULT_EXTENSIONS
        )


        # UWAGA:
        # tutaj nie kopiujemy DEFAULT_SKIP_DIRS
        # ponieważ filtr ma być sterowany oknem

        self.skip_dirs = set(
            DEFAULT_SKIP_DIRS
        )


        self.output_dir = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            "OUTPUT"
        )


        os.makedirs(
            self.output_dir,
            exist_ok=True
        )


        self.build_gui()



    # ========================================================
    # GUI
    # ========================================================

    def build_gui(self):

        tk.Label(
            self.root,
            text="Repo Builder - wybór kontekstu",
            font=("Arial", 14)
        ).pack(
            pady=10
        )


        toolbar = tk.Frame(
            self.root
        )

        toolbar.pack()



        create_icon_button(
            toolbar,
            "WYBIERZ REPO",
            self.add_repository,
            "big_plus"
        )


        create_icon_button(
            toolbar,
            "DODAJ PLIKI",
            self.add_files,
            "small_plus"
        )


        create_icon_button(
            toolbar,
            "USUŃ ZAZNACZONE",
            self.remove_selected,
            "big_minus"
        )


        create_icon_button(
            toolbar,
            "USUŃ WSZYSTKIE",
            self.remove_all,
            "small_minus"
        )

# ====================================================
        # PANEL LISTY PLIKÓW
        # ====================================================

        frame = tk.Frame(
            self.root,
            relief=tk.GROOVE,
            borderwidth=2
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )


        scrollbar = tk.Scrollbar(
            frame
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )


        self.listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            yscrollcommand=scrollbar.set
        )


        self.listbox.pack(
            fill=tk.BOTH,
            expand=True
        )


        scrollbar.config(
            command=self.listbox.yview
        )



        # ====================================================
        # PRZYCISKI LISTY
        # ====================================================

        list_controls = tk.Frame(
            frame
        )


        list_controls.pack(
            side=tk.BOTTOM,
            fill=tk.X,
            pady=5
        )



        tk.Button(
            list_controls,
            text="ZAZNACZ WSZYSTKIE",
            command=self.select_all,
            width=20
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        tk.Button(
            list_controls,
            text="ODZNACZ WSZYSTKIE",
            command=self.unselect_all,
            width=20
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        # ====================================================
        # DOLNY PANEL
        # ====================================================

        bottom = tk.Frame(
            self.root
        )


        bottom.pack(
            pady=10
        )



        tk.Button(
            bottom,
            text="FILTRY PLIKÓW",
            command=self.open_filters,
            width=20
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        tk.Button(
            bottom,
            text="OUTPUT FOLDER",
            command=self.open_output_folder,
            width=20
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        tk.Button(
            bottom,
            text="OPRÓŻNIJ OUTPUT",
            command=self.clear_output,
            width=20
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        tk.Button(
            self.root,
            text="GENERUJ REPOZYTORIUM",
            command=self.generate,
            bg="green",
            fg="white",
            height=2
        ).pack(
            pady=10
        )



    # ========================================================
    # POMOCNICZE FILTROWANIE
    # ========================================================

    def is_directory_blocked(self, path):

        parts = path.replace(
            "\\",
            "/"
        ).split("/")


        for part in parts:

            for skip in self.skip_dirs:

                if part.lower() == skip.lower():

                    return True


        return False



    def is_extension_allowed(self, path):

        ext = os.path.splitext(
            path
        )[1].lower()


        return ext in self.extensions



    # ========================================================
    # DODAWANIE REPOZYTORIUM
    # ========================================================

    def add_repository(self):

        folder = filedialog.askdirectory()


        if not folder:

            return



        added = 0

        blocked = 0


        new_files = []



        for root, dirs, files in os.walk(folder):


            # odcinamy katalogi zanim os.walk wejdzie do środka

            dirs[:] = [

                d for d in dirs

                if not any(

                    d.lower() == skip.lower()

                    for skip in self.skip_dirs

                )

            ]



            for filename in files:


                full_path = os.path.join(
                    root,
                    filename
                )


                if self.is_directory_blocked(
                    full_path
                ):

                    blocked += 1

                    continue



                if not self.is_extension_allowed(
                    full_path
                ):

                    blocked += 1

                    continue



                if full_path in self.files:

                    continue



                self.files.append(
                    full_path
                )


                new_files.append(
                    full_path
                )


                added += 1



        # aktualizacja GUI tylko raz
        # zamiast 450 refreshów

        for path in new_files:

            self.listbox.insert(
                tk.END,
                path
            )


        if new_files:

            self.select_all()



        messagebox.showinfo(
            "Repo dodane",
            f"Dodano plików: {added}\n"
            f"Pominięto: {blocked}"
        )



    # ========================================================
    # DODAWANIE POJEDYNCZYCH PLIKÓW
    # ========================================================

    def add_files(self):

        selected = filedialog.askopenfilenames(
            title="Wybierz pliki"
        )


        added = 0

        blocked = []



        for path in selected:



            if self.is_directory_blocked(
                path
            ):

                blocked.append(
                    path
                )

                continue



            if not self.is_extension_allowed(
                path
            ):

                blocked.append(
                    path
                )

                continue



            if path in self.files:

                continue



            self.files.append(
                path
            )


            self.listbox.insert(
                tk.END,
                path
            )


            added += 1



        if added:

            self.select_all()



        if blocked:


            messagebox.showwarning(
                "Pliki pominięte",
                "Następujące pliki są na liście wykluczonych:\n\n"
                +
                "\n".join(
                    blocked[:10]
                )
                +
                (
                    "\n..."
                    if len(blocked) > 10
                    else ""
                )
            )


        elif added:


            messagebox.showinfo(
                "Pliki dodane",
                f"Dodano: {added}"
            )


    # ========================================================
    # USUWANIE ZAZNACZONYCH
    # ========================================================

    def remove_selected(self):

        selected = list(
            self.listbox.curselection()
        )


        if not selected:

            return



        selected.reverse()



        for index in selected:


            self.listbox.delete(
                index
            )


            del self.files[index]



    # ========================================================
    # USUWANIE WSZYSTKICH
    # ========================================================

    def remove_all(self):

        if not self.files:

            return



        if messagebox.askyesno(
            "Potwierdzenie",
            "Usunąć wszystkie pliki?"
        ):


            self.files.clear()


            self.listbox.delete(
                0,
                tk.END
            )



    # ========================================================
    # OPERACJE NA LIŚCIE
    # ========================================================

    def select_all(self):

        if self.listbox.size() == 0:

            return



        self.listbox.selection_clear(
            0,
            tk.END
        )


        self.listbox.selection_set(
            0,
            tk.END
        )


        self.listbox.activate(
            0
        )



    def unselect_all(self):

        self.listbox.selection_clear(
            0,
            tk.END
        )



    # ========================================================
    # OUTPUT
    # ========================================================

    def open_output_folder(self):

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )


        subprocess.Popen(
            [
                "explorer",
                self.output_dir
            ]
        )



    def clear_output(self):

        if not os.path.exists(
            self.output_dir
        ):

            return



        items = os.listdir(
            self.output_dir
        )


        if not items:


            messagebox.showinfo(
                "OUTPUT",
                "Folder OUTPUT jest pusty."
            )

            return



        if not messagebox.askyesno(
            "Potwierdzenie",
            "Usunąć zawartość OUTPUT?"
        ):

            return



        for item in items:


            path = os.path.join(
                self.output_dir,
                item
            )


            try:


                if os.path.isdir(
                    path
                ):

                    shutil.rmtree(
                        path
                    )


                else:

                    os.remove(
                        path
                    )


            except Exception as e:


                messagebox.showerror(
                    "Błąd",
                    str(e)
                )



        messagebox.showinfo(
            "OUTPUT",
            "Folder OUTPUT opróżniony."
        )



    # ========================================================
    # OKNO FILTRÓW
    # ========================================================

    def open_filters(self):

        window = tk.Toplevel(
            self.root
        )


        window.title(
            "Filtry plików"
        )


        window.geometry(
            "750x650"
        )



        # ====================================================
        # ROZSZERZENIA
        # ====================================================

        tk.Label(
            window,
            text="ROZSZERZENIA PLIKÓW",
            font=("Arial", 12)
        ).pack(
            pady=5
        )



        ext_vars = {}



        ext_frame = tk.Frame(
            window
        )


        ext_frame.pack(
            fill=tk.X,
            padx=20
        )



        columns = 5



        for index, ext in enumerate(
            sorted(DEFAULT_EXTENSIONS)
        ):


            var = tk.BooleanVar(
                value=True
            )


            ext_vars[ext] = var



            tk.Checkbutton(
                ext_frame,
                text=ext,
                variable=var
            ).grid(
                row=index // columns,
                column=index % columns,
                sticky="w",
                padx=10,
                pady=2
            )



        # ====================================================
        # KATALOGI
        # ====================================================

        tk.Label(
            window,
            text="POMIJANE KATALOGI",
            font=("Arial", 12)
        ).pack(
            pady=10
        )



        dir_vars = {}



        dir_frame = tk.Frame(
            window
        )


        dir_frame.pack(
            fill=tk.X,
            padx=20
        )



        columns = 5



        for index, directory in enumerate(
            sorted(DEFAULT_SKIP_DIRS)
        ):


            var = tk.BooleanVar(
                value=True
            )


            dir_vars[directory] = var



            tk.Checkbutton(
                dir_frame,
                text=directory,
                variable=var
            ).grid(
                row=index // columns,
                column=index % columns,
                sticky="w",
                padx=10,
                pady=2
            )



        # ====================================================
        # PRZYCISKI FILTRÓW
        # ====================================================

        buttons = tk.Frame(
            window
        )


        buttons.pack(
            pady=15
        )



        def select_all_filters():


            for var in ext_vars.values():

                var.set(True)



            for var in dir_vars.values():

                var.set(True)




        def clear_filters():


            for var in ext_vars.values():

                var.set(False)



            for var in dir_vars.values():

                var.set(False)





        def save_filters():


            self.extensions = {

                ext

                for ext, var in ext_vars.items()

                if var.get()

            }

            self.skip_dirs = {

                directory

                for directory, var in dir_vars.items()

                if var.get()

            }



            window.destroy()


        tk.Button(
            buttons,
            text="ZAZNACZ WSZYSTKIE",
            command=select_all_filters,
            width=18
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        tk.Button(
            buttons,
            text="ODZNACZ WSZYSTKIE",
            command=clear_filters,
            width=18
        ).pack(
            side=tk.LEFT,
            padx=5
        )



        tk.Button(
            buttons,
            text="ZAPISZ",
            command=save_filters,
            width=12
        ).pack(
            side=tk.LEFT,
            padx=5
        )



    # ========================================================
    # GENEROWANIE REPOZYTORIUM TXT
    # ========================================================

    def generate(self):

        selected_indexes = self.listbox.curselection()



        if not selected_indexes:


            messagebox.showwarning(
                "Brak zaznaczenia",
                "Zaznacz pliki do wygenerowania."
            )

            return



        files_to_generate = [

            self.files[i]

            for i in selected_indexes

        ]



        output_file = os.path.join(
            self.output_dir,
            "repozytorium_custom.txt"
        )



        try:



            # bezpieczne wyznaczenie katalogu bazowego

            try:

                base_path = os.path.commonpath(
                    files_to_generate
                )


                if os.path.isfile(
                    base_path
                ):

                    base_path = os.path.dirname(
                        base_path
                    )


            except Exception:


                base_path = os.path.dirname(
                    files_to_generate[0]
                )



            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as out:



                for full_path in files_to_generate:



                    if not self.is_extension_allowed(
                        full_path
                    ):

                        continue



                    relative_path = os.path.relpath(
                        full_path,
                        base_path
                    )



                    out.write(
                        f"#~~~~~~[START PLIKU: {relative_path} ]~~~~~~#\n"
                    )



                    try:


                        with open(
                            full_path,
                            "r",
                            encoding="utf-8",
                            errors="ignore"
                        ) as source:


                            out.write(
                                source.read()
                            )



                    except Exception as e:


                        out.write(
                            "\n\nBŁĄD ODCZYTU:\n"
                        )


                        out.write(
                            str(e)
                        )



                    out.write(
                        f"\n#~~~~~~[KONIEC PLIKU: {relative_path} ]~~~~~~#\n\n"
                    )



            messagebox.showinfo(

                "Gotowe",

                "Repozytorium wygenerowane:\n\n"

                + output_file

            )



        except Exception as e:


            messagebox.showerror(

                "Błąd",

                str(e)

            )



# ============================================================
# START PROGRAMU
# ============================================================

def run_repo_generator():

    root = tk.Tk()



    app = RepoGenerator(
        root
    )



    root.mainloop()



if __name__ == "__main__":

    run_repo_generator()
