

# Repo_Guardian/repo_generator/repo_gui.py

# ============================================================
# Repo Guardian - Repo Builder GUI
# ============================================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import os
import subprocess
import shutil

from repo_guardian.ui.theme import apply_theme, BG, SURFACE, BORDER, TEXT, PRIMARY, PAD_SM, PAD_MD, PAD_LG


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

    # środowiska Python
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
# IKONY
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

    frame = ttk.Frame(parent)

    frame.pack(
        side=tk.LEFT,
        padx=(0, PAD_SM)
    )


    canvas = tk.Canvas(
        frame,
        width=35,
        height=35,
        highlightthickness=0,
        bg=BG,
    )

    canvas.pack(
        side=tk.LEFT
    )


    draw_icon(
        canvas,
        icon_type
    )


    ttk.Button(
        frame,
        text=text,
        command=command,
        style="Secondary.TButton",
    ).pack(
        side=tk.LEFT
    )


# ============================================================
# KLASA GŁÓWNA
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


        self.files = []


        self.extensions = set(
            DEFAULT_EXTENSIONS
        )


        # aktywne filtry katalogów
        # STARTOWO pełna lista aktywna
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

        ttk.Label(
            self.root,
            text="Repo Builder",
            style="Header.TLabel",
        ).pack(
            anchor="w",
            padx=PAD_LG,
            pady=(PAD_LG, 0)
        )

        ttk.Label(
            self.root,
            text="Wybierz pliki, które trafią do wygenerowanego kontekstu",
            style="Sub.TLabel",
        ).pack(
            anchor="w",
            padx=PAD_LG,
            pady=(2, PAD_MD)
        )

        toolbar=ttk.Frame(
            self.root
        )

        toolbar.pack(
            padx=PAD_LG,
            fill=tk.X
        )


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
        # LISTA PLIKÓW
        # ====================================================

        frame=ttk.Frame(
            self.root,
            style="Card.TFrame",
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=PAD_LG,
            pady=PAD_MD
        )


        scrollbar=ttk.Scrollbar(
            frame
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )


        self.listbox=tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
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

        self.listbox.pack(
            fill=tk.BOTH,
            expand=True
        )


        scrollbar.config(
            command=self.listbox.yview
        )


        controls=ttk.Frame(
            frame
        )

        controls.pack(
            side=tk.BOTTOM,
            fill=tk.X,
            pady=(PAD_SM, 0)
        )


        ttk.Button(
            controls,
            text="Zaznacz wszystkie",
            command=self.select_all,
            style="Ghost.TButton",
        ).pack(
            side=tk.LEFT,
            padx=(0, PAD_SM)
        )


        ttk.Button(
            controls,
            text="Odznacz wszystkie",
            command=self.unselect_all,
            style="Ghost.TButton",
        ).pack(
            side=tk.LEFT
        )


        # ====================================================
        # DOLNY PANEL
        # ====================================================

        bottom=ttk.Frame(
            self.root
        )

        bottom.pack(
            padx=PAD_LG,
            pady=(0, PAD_SM),
            fill=tk.X
        )


        ttk.Button(
            bottom,
            text="Filtry plików",
            command=self.open_filters,
            style="Secondary.TButton",
        ).pack(
            side=tk.LEFT,
            padx=(0, PAD_SM)
        )


        ttk.Button(
            bottom,
            text="Output Folder",
            command=self.open_output_folder,
            style="Secondary.TButton",
        ).pack(
            side=tk.LEFT,
            padx=(0, PAD_SM)
        )


        ttk.Button(
            bottom,
            text="Opróżnij output",
            command=self.clear_output,
            style="Danger.Ghost.TButton",
        ).pack(
            side=tk.LEFT
        )


        ttk.Button(
            self.root,
            text="Generuj repozytorium",
            command=self.generate,
            style="Primary.TButton",
        ).pack(
            padx=PAD_LG,
            pady=(0, PAD_LG),
            fill=tk.X
        )



    # ========================================================
    # FILTRY
    # ========================================================

    def is_directory_blocked(self,path):

        parts=path.replace(
            "\\",
            "/"
        ).split("/")


        for part in parts:

            for skip in self.skip_dirs:

                if part.lower()==skip.lower():

                    return True


        return False



    def is_filename_blocked(self,filename):

        filename_lower=filename.lower()


        for skip in self.skip_dirs:

            if skip.lower() in filename_lower:

                return True


        return False



    def is_extension_allowed(self,path):

        ext=os.path.splitext(
            path
        )[1].lower()


        return ext in self.extensions

    # ========================================================
    # DODAWANIE REPOZYTORIUM
    # ========================================================

    def add_repository(self):

        folder=filedialog.askdirectory()


        if not folder:
            return



        added=0
        blocked=0

        new_files=[]



        for root,dirs,files in os.walk(folder):


            # filtr katalogów zanim os.walk wejdzie dalej

            dirs[:]=[
                d
                for d in dirs
                if not any(
                    d.lower()==skip.lower()
                    for skip in self.skip_dirs
                )
            ]



            for filename in files:


                full_path=os.path.join(
                    root,
                    filename
                )


                if self.is_directory_blocked(
                    full_path
                ):

                    blocked+=1
                    continue



                if self.is_filename_blocked(
                    filename
                ):

                    blocked+=1
                    continue



                if not self.is_extension_allowed(
                    full_path
                ):

                    blocked+=1
                    continue



                if full_path in self.files:

                    continue



                self.files.append(
                    full_path
                )


                new_files.append(
                    full_path
                )


                added+=1



        # jeden refresh GUI

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

        selected=filedialog.askopenfilenames(
            title="Wybierz pliki"
        )


        if not selected:
            return



        added=0
        blocked=[]



        for path in selected:


            filename=os.path.basename(
                path
            )


            if self.is_directory_blocked(
                path
            ):


                blocked.append(
                    path
                )

                continue



            if self.is_filename_blocked(
                filename
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


            added+=1



        if added:

            self.select_all()



        if blocked:


            messagebox.showwarning(
                "Pliki pominięte",
                "Elementy są na liście wykluczonych:\n\n"
                +
                "\n".join(
                    blocked[:10]
                )
                +
                (
                    "\n..."
                    if len(blocked)>10
                    else ""
                )
            )


        elif added:


            messagebox.showinfo(
                "Pliki dodane",
                f"Dodano: {added}"
            )



    # ========================================================
    # USUWANIE
    # ========================================================

    def remove_selected(self):

        selected=list(
            self.listbox.curselection()
        )


        selected.reverse()



        for index in selected:

            self.listbox.delete(
                index
            )

            del self.files[index]



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
    # ZAZNACZANIE
    # ========================================================

    def select_all(self):

        if self.listbox.size()==0:

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
    # OKNO FILTRÓW
    # ========================================================

    def open_filters(self):

        window=tk.Toplevel(
            self.root
        )

        window.title(
            "Filtry plików"
        )

        window.geometry(
            "750x650"
        )
        window.configure(bg=BG)


        # wymuszenie właściciela zmiennych Tk
        window.transient(
            self.root
        )


        # ====================================================
        # ROZSZERZENIA
        # ====================================================

        ttk.Label(
            window,
            text="Rozszerzenia plików",
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=PAD_LG,
            pady=(PAD_LG, PAD_SM)
        )


        ext_vars={}


        ext_frame=ttk.Frame(
            window
        )

        ext_frame.pack(
            fill=tk.X,
            padx=PAD_LG
        )


        for index,ext in enumerate(
            sorted(DEFAULT_EXTENSIONS)
        ):

            var=tk.BooleanVar(
                master=window,
                value=True
            )

            ext_vars[ext]=var


            ttk.Checkbutton(
                ext_frame,
                text=ext,
                variable=var
            ).grid(
                row=index//5,
                column=index%5,
                sticky="w",
                padx=10,
                pady=2
            )



        # ====================================================
        # KATALOGI
        # ====================================================

        ttk.Label(
            window,
            text="Pomijane katalogi",
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=PAD_LG,
            pady=(PAD_MD, PAD_SM)
        )


        dir_vars={}


        dir_frame=ttk.Frame(
            window
        )

        dir_frame.pack(
            fill=tk.X,
            padx=PAD_LG
        )


        for index,directory in enumerate(
            sorted(DEFAULT_SKIP_DIRS)
        ):


            # KLUCZOWA POPRAWKA:
            # katalogi startują ZAZNACZONE

            var=tk.BooleanVar(
                master=window,
                value=True
            )


            dir_vars[directory]=var



            ttk.Checkbutton(
                dir_frame,
                text=directory,
                variable=var
            ).grid(
                row=index//5,
                column=index%5,
                sticky="w",
                padx=10,
                pady=2
            )



        # ====================================================
        # STEROWANIE FILTRAMI
        # ====================================================

        ttk.Separator(window).pack(fill=tk.X, padx=PAD_LG, pady=PAD_MD)

        buttons=ttk.Frame(
            window
        )

        buttons.pack(
            padx=PAD_LG,
            pady=(0, PAD_LG),
            fill=tk.X
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


            self.extensions={
                ext
                for ext,var in ext_vars.items()
                if var.get()
            }


            self.skip_dirs={
                d
                for d,var in dir_vars.items()
                if var.get()
            }


            window.destroy()



        ttk.Button(
            buttons,
            text="Zaznacz wszystkie",
            command=select_all_filters,
            style="Ghost.TButton",
        ).pack(
            side=tk.LEFT,
            padx=(0, PAD_SM)
        )


        ttk.Button(
            buttons,
            text="Odznacz wszystkie",
            command=clear_filters,
            style="Ghost.TButton",
        ).pack(
            side=tk.LEFT
        )


        ttk.Button(
            buttons,
            text="Zapisz",
            command=save_filters,
            style="Primary.TButton",
        ).pack(
            side=tk.RIGHT
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


        for item in os.listdir(
            self.output_dir
        ):

            path=os.path.join(
                self.output_dir,
                item
            )

            try:

                if os.path.isdir(path):

                    shutil.rmtree(path)

                else:

                    os.remove(path)

            except Exception as e:

                messagebox.showerror(
                    "Błąd",
                    str(e)
                )



    # ========================================================
    # GENEROWANIE TXT
    # ========================================================

    def generate(self):

        selected_indexes=self.listbox.curselection()


        if not selected_indexes:

            messagebox.showwarning(
                "Brak zaznaczenia",
                "Zaznacz pliki do wygenerowania."
            )

            return



        files_to_generate=[
            self.files[i]
            for i in selected_indexes
        ]



        output_file=os.path.join(
            self.output_dir,
            "repozytorium_custom.txt"
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


                relative=os.path.basename(
                    full_path
                )


                out.write(
                    f"#~~~~~~[START PLIKU: {relative} ]~~~~~~#\n"
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
                        "\nBŁĄD ODCZYTU:\n"
                    )

                    out.write(
                        str(e)
                    )



                out.write(
                    f"\n#~~~~~~[KONIEC PLIKU: {relative} ]~~~~~~#\n\n"
                )



        messagebox.showinfo(
            "Gotowe",
            "Repozytorium wygenerowane:\n\n"
            + output_file
        )



# ============================================================
# START
# ============================================================

def run_repo_generator():

    root=tk.Tk()

    apply_theme(root)

    app=RepoGenerator(
        root
    )

    root.mainloop()



if __name__=="__main__":

    run_repo_generator()
