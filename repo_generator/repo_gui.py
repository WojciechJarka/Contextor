

# Repo_Guardian/repo_generator/repo_gui.py

# ============================================================
# Repo Guardian - Repo Builder GUI
# ============================================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

import os
import subprocess
import shutil

from repo_guardian.ui.theme import apply_theme, HeaderTooltipManager, BG, SURFACE, BORDER, TEXT, PRIMARY, PAD_SM, PAD_MD, PAD_LG
from repo_guardian.ui.path_memory import load_state, save_state


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


    btn = ttk.Button(
        frame,
        text=text,
        command=command,
        style="Secondary.TButton",
    )
    btn.pack(side=tk.LEFT)
    return btn

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


        state = load_state()

        # Files memory
        self.files = state.get("repo_gui_files", [])
        saved_selections = state.get("repo_gui_selected", [])

        # Filters memory
        exts = state.get("repo_gui_skip_exts")
        self.skip_exts = set(exts) if exts is not None else set()

        skips = state.get("repo_gui_skip_dirs")
        self.skip_dirs = set(skips) if skips is not None else set(DEFAULT_SKIP_DIRS)
        self.current_preset = state.get("repo_gui_current_preset", None)

        # Split memory
        self.split_enabled_val = state.get("repo_gui_split_enabled", False)
        self.split_size_val = state.get("repo_gui_split_size", 200)



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
        
        # Populate file list and selections
        for path in self.files:
            self.listbox.insert(tk.END, path)
            
        for idx in saved_selections:
            try:
                self.listbox.selection_set(idx)
            except Exception:
                pass



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

        sub_label = ttk.Label(
            self.root,
            text="Select files to include in generated context",
            style="Sub.TLabel",
        )
        sub_label.pack(
            anchor="w",
            padx=PAD_LG,
            pady=(2, PAD_MD)
        )
        self.tooltip = HeaderTooltipManager(sub_label, "Select files to include in generated context")

        toolbar=ttk.Frame(
            self.root
        )

        toolbar.pack(
            padx=PAD_LG,
            fill=tk.X
        )


        btn_repo = create_icon_button(
            toolbar,
            "SELECT REPO",
            self.add_repository,
            "big_plus"
        )
        self.tooltip.bind_tooltip(btn_repo, "Add a full repository folder. Automatically filters out skipped directories/extensions.")

        btn_files = create_icon_button(
            toolbar,
            "ADD FILES",
            self.add_files,
            "small_plus"
        )
        self.tooltip.bind_tooltip(btn_files, "Manually add specific files to the generation list.")

        btn_rem = create_icon_button(
            toolbar,
            "REMOVE SELECTED",
            self.remove_selected,
            "big_minus"
        )
        self.tooltip.bind_tooltip(btn_rem, "Remove selected files from the generation list.")

        btn_clear = create_icon_button(
            toolbar,
            "REMOVE ALL",
            self.remove_all,
            "small_minus"
        )
        self.tooltip.bind_tooltip(btn_clear, "Clear the entire generation list.")


        # ====================================================
        # FILE LIST
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


        btn_sa = ttk.Button(
            controls,
            text="Select all",
            command=self.select_all,
            style="Ghost.TButton",
        )
        btn_sa.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(btn_sa, "Select all files in the list for generation.")

        btn_ua = ttk.Button(
            controls,
            text="Unselect all",
            command=self.unselect_all,
            style="Ghost.TButton",
        )
        btn_ua.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(btn_ua, "Deselect all files.")


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


        btn_ff = ttk.Button(
            bottom,
            text="File filters",
            command=self.open_filters,
            style="Secondary.TButton",
        )
        btn_ff.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(btn_ff, "Configure extensions and directories to ignore when adding a repository.")

        btn_of = ttk.Button(
            bottom,
            text="Output Folder",
            command=self.open_output_folder,
            style="Secondary.TButton",
        )
        btn_of.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(btn_of, "Open folder where the generated repository text files are saved.")

        btn_eo = ttk.Button(
            bottom,
            text="Empty output",
            command=self.clear_output,
            style="Danger.Ghost.TButton",
        )
        btn_eo.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(btn_eo, "Delete all previously generated text files.")

        # ========================================================
        # SPLIT CONTROLS
        # ========================================================
        split_frame = ttk.Frame(bottom)
        split_frame.pack(side=tk.RIGHT, padx=PAD_SM)

        self.split_enabled = tk.BooleanVar(value=self.split_enabled_val)
        chk_split = ttk.Checkbutton(
            split_frame,
            text="File split",
            variable=self.split_enabled
        )
        chk_split.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(chk_split, "Automatic file split into fragments of defined size")

        self.split_size = tk.IntVar(value=self.split_size_val)
        entry_split = ttk.Entry(
            split_frame,
            textvariable=self.split_size,
            width=5
        )
        entry_split.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(entry_split, "Result file split size")
        
        ttk.Label(split_frame, text="KB").pack(side=tk.LEFT, padx=(PAD_SM, 0))

        btn_gen = ttk.Button(
            self.root,
            text="Generate repository",
            command=self.generate,
            style="Primary.TButton",
        )
        btn_gen.pack(padx=PAD_LG, pady=(0, PAD_LG), fill=tk.X)
        self.tooltip.bind_tooltip(btn_gen, "Bundle all selected files into a single text file (LLM Context).")



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

            if skip.lower() == filename_lower:

                return True


        return False



    def is_extension_allowed(self,path):

        ext=os.path.splitext(
            path
        )[1].lower()


        if ext not in DEFAULT_EXTENSIONS:
            return False

        return ext not in self.skip_exts

    # ========================================================
    # DODAWANIE REPOZYTORIUM
    # ========================================================

    def add_repository(self):

        folder=filedialog.askdirectory(parent=self.root)


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
            "Repo added",
            f"Files added: {added}\n"
            f"Skipped: {blocked}",
            parent=self.root
        )



    # ========================================================
    # DODAWANIE POJEDYNCZYCH PLIKÓW
    # ========================================================

    def add_files(self):

        selected=filedialog.askopenfilenames(
            title="Select files",
            parent=self.root
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
                "Skipped files",
                "Elements are on the excluded list:\n\n"
                +
                "\n".join(
                    blocked[:10]
                )
                +
                (
                    "\n..."
                    if len(blocked)>10
                    else ""
                ),
                parent=self.root
            )


        elif added:


            messagebox.showinfo(
                "Files added",
                f"Added: {added}",
                parent=self.root
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
            "Confirmation",
            "Clear all files from the list?",
            parent=self.root
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
            "File filters"
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

        st_test = load_state()
        presets_test = st_test.get("repo_gui_presets", {})
        
        original_skip_exts = set(self.skip_exts)
        original_skip_dirs = set(self.skip_dirs)
        
        if self.current_preset and self.current_preset not in presets_test:
            self.current_preset = None

        preset_label_var = tk.StringVar(master=window, value=f"Active Preset: {self.current_preset}" if self.current_preset else "Active Preset: None")
        ttk.Label(window, textvariable=preset_label_var, style="Sub.TLabel", foreground=PRIMARY).pack(
            anchor="w", padx=PAD_LG, pady=(PAD_MD, 0)
        )

        filter_sub = ttk.Label(
            window,
            text="Configure extensions and directories to IGNORE",
            style="Sub.TLabel"
        )
        filter_sub.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_SM))
        f_tooltip = HeaderTooltipManager(filter_sub, "Configure extensions and directories to IGNORE")

        ttk.Label(
            window,
            text="File extensions (✓ = IGNORE)",
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=PAD_LG,
            pady=(PAD_MD, PAD_SM)
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
                value=(ext in self.skip_exts)
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
            text="Skipped directories (✓ = IGNORE)",
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


            var=tk.BooleanVar(
                master=window,
                value=(directory in self.skip_dirs)
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

        preset_buttons=ttk.Frame(window)
        preset_buttons.pack(padx=PAD_LG, pady=(0, PAD_SM), fill=tk.X)
        
        def save_preset():
            st = load_state()
            presets = st.get("repo_gui_presets", {})

            dlg = tk.Toplevel(window)
            dlg.title("Save Preset")
            dlg.geometry("340x360")
            dlg.configure(bg=BG)
            dlg.transient(window)
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

                ext_list = [ext for ext, var in ext_vars.items() if var.get()]
                skip_list = [d for d, var in dir_vars.items() if var.get()]
                presets[name] = {"skip_ext": ext_list, "skip": skip_list}
                save_state(repo_gui_presets=presets)
                self.current_preset = name
                preset_label_var.set(f"Active Preset: {name}")
                messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=dlg)
                dlg.destroy()

            btn_row = ttk.Frame(dlg)
            btn_row.pack(fill=tk.X, padx=PAD_MD, pady=PAD_MD)
            ttk.Button(btn_row, text="Save", command=do_save, style="Primary.TButton").pack(side=tk.RIGHT)
            ttk.Button(btn_row, text="Cancel", command=dlg.destroy, style="Ghost.TButton").pack(side=tk.RIGHT, padx=(0, PAD_SM))
            dlg.bind("<Return>", lambda e: do_save())

        def load_preset():
            st = load_state()
            presets = st.get("repo_gui_presets", {})
            
            def on_select(name):
                if name == "default":
                    for ext, var in ext_vars.items():
                        var.set(False)
                    for d, var in dir_vars.items():
                        var.set(True)
                    self.current_preset = None
                    preset_label_var.set("Active Preset: None")
                    sel_win.destroy()
                    return

                preset = presets[name]
                for ext, var in ext_vars.items():
                    if "ext" in preset:
                        var.set(ext not in preset["ext"])
                    else:
                        var.set(ext in preset.get("skip_ext", []))
                for d, var in dir_vars.items():
                    var.set(d in preset.get("skip", []))
                self.current_preset = name
                preset_label_var.set(f"Active Preset: {name}")
                sel_win.destroy()

            sel_win = tk.Toplevel(window)
            sel_win.title("Load Preset")
            sel_win.geometry("300x300")
            sel_win.configure(bg=BG)
            sel_win.transient(window)
            
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
            st = load_state()
            presets = st.get("repo_gui_presets", {})
            if not presets:
                messagebox.showinfo("Presets", "No saved presets found.")
                return
            
            def on_select(name):
                confirm = messagebox.askyesno("Confirm Delete", f"Delete preset '{name}'?", parent=sel_win)
                if confirm:
                    del presets[name]
                    save_state(repo_gui_presets=presets)
                    if self.current_preset == name:
                        self.current_preset = None
                        preset_label_var.set("Active Preset: None")
                    messagebox.showinfo("Deleted", f"Preset '{name}' deleted.")
                sel_win.destroy()

            sel_win = tk.Toplevel(window)
            sel_win.title("Delete Preset")
            sel_win.geometry("300x300")
            sel_win.configure(bg=BG)
            sel_win.transient(window)
            
            listb = tk.Listbox(sel_win, bg=SURFACE, fg=TEXT, selectbackground=PRIMARY, selectforeground="#ffffff", borderwidth=0, highlightthickness=1)
            listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
            for p in sorted(presets.keys()):
                listb.insert(tk.END, p)
            
            def del_btn():
                sel = listb.curselection()
                if sel: on_select(listb.get(sel[0]))
            ttk.Button(sel_win, text="Delete", command=del_btn, style="Danger.Ghost.TButton").pack(pady=PAD_SM)

        def load_default_preset():
            for ext, var in ext_vars.items():
                var.set(True)
            for d, var in dir_vars.items():
                var.set(True)
            self.current_preset = None
            preset_label_var.set("Active Preset: None")

        b_def_pre = ttk.Button(preset_buttons, text="Default", command=load_default_preset, style="Secondary.TButton")
        b_def_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        f_tooltip.bind_tooltip(b_def_pre, "Restore to default (all checkboxes checked, no active preset).")

        b_save_pre = ttk.Button(preset_buttons, text="Save Preset", command=save_preset, style="Secondary.TButton")
        b_save_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        f_tooltip.bind_tooltip(b_save_pre, "Save the current filter configuration as a reusable preset.")
        
        b_load_pre = ttk.Button(preset_buttons, text="Load Preset", command=load_preset, style="Secondary.TButton")
        b_load_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        f_tooltip.bind_tooltip(b_load_pre, "Load a previously saved filter configuration.")
        
        b_del_pre = ttk.Button(preset_buttons, text="Delete Preset", command=delete_preset, style="Danger.Ghost.TButton")
        b_del_pre.pack(side=tk.LEFT)
        f_tooltip.bind_tooltip(b_del_pre, "Delete a saved filter preset.")

        buttons=ttk.Frame(window)
        buttons.pack(padx=PAD_LG, pady=(0, PAD_LG), fill=tk.X)

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



        def handle_close(is_confirm=False):
            current_exts = {ext for ext,var in ext_vars.items() if var.get()}
            current_skips = {d for d,var in dir_vars.items() if var.get()}
            changed_from_start = (current_exts != original_skip_exts or current_skips != original_skip_dirs)

            if self.current_preset:
                st = load_state()
                presets = st.get("repo_gui_presets", {})
                if self.current_preset in presets:
                    p = presets[self.current_preset]
                    preset_changed = False
                    old_ext = p.get("ext")
                    if old_ext is not None:
                        preset_skip_exts = {ext for ext in DEFAULT_EXTENSIONS if ext not in old_ext}
                    else:
                        preset_skip_exts = set(p.get("skip_ext", []))
                    
                    if sorted(list(current_exts)) != sorted(list(preset_skip_exts)): preset_changed = True
                    if sorted(list(current_skips)) != sorted(p.get("skip", [])): preset_changed = True
                    
                    if preset_changed:
                        ans = messagebox.askyesnocancel("Update Preset?", f"Preset '{self.current_preset}' has unsaved changes.\n\nYES = Update preset and apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.", parent=window)
                        if ans is None:
                            return
                        if ans is True:
                            presets[self.current_preset] = {"skip_ext": list(current_exts), "skip": list(current_skips)}
                            save_state(repo_gui_presets=presets)
                            self.skip_exts = current_exts
                            self.skip_dirs = current_skips
                        else:
                            self.skip_exts = original_skip_exts
                            self.skip_dirs = original_skip_dirs
                            
                        save_state(
                            repo_gui_skip_exts=list(self.skip_exts),
                            repo_gui_skip_dirs=list(self.skip_dirs),
                            repo_gui_current_preset=self.current_preset
                        )
                        window.destroy()
                        return

            if is_confirm:
                self.skip_exts = current_exts
                self.skip_dirs = current_skips
                save_state(
                    repo_gui_skip_exts=list(self.skip_exts),
                    repo_gui_skip_dirs=list(self.skip_dirs),
                    repo_gui_current_preset=self.current_preset
                )
                window.destroy()
            else:
                if changed_from_start:
                    ans = messagebox.askyesnocancel("Unsaved changes", "You have unsaved changes.\n\nYES = Apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.", parent=window)
                    if ans is None:
                        return
                    if ans is True:
                        self.skip_exts = current_exts
                        self.skip_dirs = current_skips
                    else:
                        self.skip_exts = original_skip_exts
                        self.skip_dirs = original_skip_dirs
                        
                    save_state(
                        repo_gui_skip_exts=list(self.skip_exts),
                        repo_gui_skip_dirs=list(self.skip_dirs),
                        repo_gui_current_preset=self.current_preset
                    )
                    window.destroy()
                else:
                    window.destroy()



        btn_sa_f = ttk.Button(
            buttons,
            text="Select all",
            command=select_all_filters,
            style="Ghost.TButton",
        )
        btn_sa_f.pack(side=tk.LEFT, padx=(0, PAD_SM))
        f_tooltip.bind_tooltip(btn_sa_f, "Check all extensions and directories.")

        btn_ua_f = ttk.Button(
            buttons,
            text="Unselect all",
            command=clear_filters,
            style="Ghost.TButton",
        )
        btn_ua_f.pack(side=tk.LEFT)
        f_tooltip.bind_tooltip(btn_ua_f, "Uncheck all extensions and directories.")

        btn_sv_f = ttk.Button(
            buttons,
            text="Confirm",
            command=lambda: handle_close(is_confirm=True),
            style="Primary.TButton",
        )
        btn_sv_f.pack(side=tk.RIGHT)
        f_tooltip.bind_tooltip(btn_sv_f, "Confirm changes and close the filter manager.")
        
        window.protocol("WM_DELETE_WINDOW", lambda: handle_close(is_confirm=False))



    # ========================================================
    # OUTPUT
    # ========================================================

    def open_output_folder(self):

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

        import sys
        if sys.platform.startswith("win"):
            os.startfile(self.output_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", self.output_dir])
        else:
            subprocess.run(["xdg-open", self.output_dir])


    def clear_output(self):

        if not os.path.exists(
            self.output_dir
        ):
            return

        confirm = messagebox.askyesno(
            "Empty output",
            "Are you sure you want to clear output?\nThis operation cannot be undone.",
            parent=self.root
        )
        if not confirm:
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
                    "Error",
                    str(e),
                    parent=self.root
                )



    # ========================================================
    # GENEROWANIE TXT
    # ========================================================

    def generate(self):

        selected_indexes=self.listbox.curselection()


        if not selected_indexes:

            messagebox.showwarning(
                "No selection",
                "Select files to generate.",
                parent=self.root
            )

            return



        files_to_generate=[
            self.files[i]
            for i in selected_indexes
        ]

        if files_to_generate:
            try:
                cpath = os.path.commonpath(files_to_generate)
                if os.path.isfile(cpath):
                    prefix = os.path.basename(os.path.dirname(cpath))
                    if not prefix:
                        prefix = os.path.basename(cpath).split('.')[0]
                else:
                    prefix = os.path.basename(cpath)
            except ValueError:
                prefix = "repo"
                
            prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-')).strip()
            if not prefix:
                prefix = "repo"
        else:
            prefix = "repo"

        output_file=os.path.join(
            self.output_dir,
            f"{prefix}_full_repo.txt"
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
                    f"#~~~~~~[FILE START: {relative} ]~~~~~~#\n"
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
                        "\nREAD ERROR:\n"
                    )

                    out.write(
                        str(e)
                    )



                out.write(
                    f"\n#~~~~~~[FILE END: {relative} ]~~~~~~#\n\n"
                )

        if self.split_enabled.get():
            try:
                limit_bytes = self.split_size.get() * 1024
                
                if os.path.getsize(output_file) > limit_bytes:
                    with open(output_file, "r", encoding="utf-8") as source:
                        lines = source.readlines()
                        
                    chunks = []
                    current_chunk = []
                    current_size = 0
                    for line in lines:
                        encoded = line.encode("utf-8")
                        line_len = len(encoded)
                        
                        if current_size + line_len > limit_bytes and current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = [line]
                            current_size = line_len
                        else:
                            current_chunk.append(line)
                            current_size += line_len
                    
                    if current_chunk:
                        chunks.append(current_chunk)
                        
                    total_chunks = len(chunks)
                    for idx, chunk_lines in enumerate(chunks, 1):
                        part_file = os.path.join(self.output_dir, f"{prefix}_part_{idx}_from_{total_chunks}.txt")
                        with open(part_file, "w", encoding="utf-8") as pf:
                            pf.writelines(chunk_lines)
            except Exception as e:
                pass


        messagebox.showinfo(
            "Done",
            "Repository generated:\n\n"
            + output_file,
            parent=self.root
        )




# ============================================================
# START
# ============================================================

def run_repo_generator(parent=None):

    if parent:
        root = tk.Toplevel(parent)
    else:
        root = tk.Tk()

    from repo_guardian.ui.path_memory import load_state, save_state
    state = load_state()
    geom = state.get("repo_gui_geometry", "800x600")
    root.geometry(geom)

    apply_theme(root)

    app=RepoGenerator(root)

    def on_closing():
        selections = list(app.listbox.curselection())
        save_state(
            repo_gui_geometry=root.geometry(),
            repo_gui_files=app.files,
            repo_gui_selected=selections,
            repo_gui_skip_exts=list(app.skip_exts),
            repo_gui_skip_dirs=list(app.skip_dirs),
            repo_gui_current_preset=app.current_preset,
            repo_gui_split_enabled=app.split_enabled.get(),
            repo_gui_split_size=app.split_size.get()
        )

        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    if parent is None:
        root.mainloop()
    return root



if __name__=="__main__":

    run_repo_generator()
