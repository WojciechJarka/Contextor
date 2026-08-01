import tkinter as tk
from tkinter import messagebox, ttk

from contextor.repo_generator.config import DEFAULT_EXTENSIONS, DEFAULT_SKIP_DIRS
from contextor.ui import theme
from contextor.ui.path_memory import load_state, save_state
from contextor.ui.theme import PAD_LG, PAD_MD, PAD_SM, HeaderTooltipManager


class FilterWindow:
    def __init__(self, parent_gui):
        self.parent_gui = parent_gui
        self.window = tk.Toplevel(self.parent_gui.root)
        self.window.title("File filters")
        self.window.geometry("750x650")
        self.window.configure(bg=theme.BG)
        self.window.transient(self.parent_gui.root)

        self.original_skip_exts = set(self.parent_gui.skip_exts)
        self.original_skip_dirs = set(self.parent_gui.skip_dirs)

        st_test = load_state()
        presets_test = st_test.get("repo_gui_presets", {})

        if self.parent_gui.current_preset and self.parent_gui.current_preset not in presets_test:
            self.parent_gui.current_preset = None

        self.preset_label_var = tk.StringVar(
            master=self.window,
            value=f"Active Preset: {self.parent_gui.current_preset}"
            if self.parent_gui.current_preset
            else "Active Preset: None",
        )
        ttk.Label(
            self.window,
            textvariable=self.preset_label_var,
            style="Sub.TLabel",
            foreground=theme.PRIMARY,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, 0))

        filter_sub = ttk.Label(
            self.window, text="Configure extensions and directories to IGNORE", style="Sub.TLabel"
        )
        filter_sub.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_SM))
        self.f_tooltip = HeaderTooltipManager(
            filter_sub, "Configure extensions and directories to IGNORE"
        )

        ttk.Label(
            self.window, text="File extensions (✓ = IGNORE)", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))

        self.ext_vars = {}
        ext_frame = ttk.Frame(self.window)
        ext_frame.pack(fill=tk.X, padx=PAD_LG)

        for index, ext in enumerate(sorted(DEFAULT_EXTENSIONS)):
            var = tk.BooleanVar(master=self.window, value=(ext in self.parent_gui.skip_exts))
            self.ext_vars[ext] = var
            ttk.Checkbutton(ext_frame, text=ext, variable=var).grid(
                row=index // 5, column=index % 5, sticky="w", padx=10, pady=2
            )

        ttk.Label(
            self.window, text="Skipped directories (✓ = IGNORE)", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))

        self.dir_vars = {}
        dir_frame = ttk.Frame(self.window)
        dir_frame.pack(fill=tk.X, padx=PAD_LG)

        for index, directory in enumerate(sorted(DEFAULT_SKIP_DIRS)):
            var = tk.BooleanVar(master=self.window, value=(directory in self.parent_gui.skip_dirs))
            self.dir_vars[directory] = var
            ttk.Checkbutton(dir_frame, text=directory, variable=var).grid(
                row=index // 5, column=index % 5, sticky="w", padx=10, pady=2
            )

        ttk.Separator(self.window).pack(fill=tk.X, padx=PAD_LG, pady=PAD_MD)

        preset_buttons = ttk.Frame(self.window)
        preset_buttons.pack(padx=PAD_LG, pady=(0, PAD_SM), fill=tk.X)

        b_def_pre = ttk.Button(
            preset_buttons,
            text="Default",
            command=self.load_default_preset,
            style="Secondary.TButton",
        )
        b_def_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.f_tooltip.bind_tooltip(
            b_def_pre, "Restore to default (all checkboxes checked, no active preset)."
        )

        b_save_pre = ttk.Button(
            preset_buttons, text="Save Preset", command=self.save_preset, style="Secondary.TButton"
        )
        b_save_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.f_tooltip.bind_tooltip(
            b_save_pre, "Save the current filter configuration as a reusable preset."
        )

        b_load_pre = ttk.Button(
            preset_buttons, text="Load Preset", command=self.load_preset, style="Secondary.TButton"
        )
        b_load_pre.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.f_tooltip.bind_tooltip(b_load_pre, "Load a previously saved filter configuration.")

        b_del_pre = ttk.Button(
            preset_buttons,
            text="Delete Preset",
            command=self.delete_preset,
            style="Danger.Ghost.TButton",
        )
        b_del_pre.pack(side=tk.LEFT)
        self.f_tooltip.bind_tooltip(b_del_pre, "Delete a saved filter preset.")

        buttons = ttk.Frame(self.window)
        buttons.pack(padx=PAD_LG, pady=(0, PAD_LG), fill=tk.X)

        btn_sa_f = ttk.Button(
            buttons, text="Select all", command=self.select_all_filters, style="Ghost.TButton"
        )
        btn_sa_f.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.f_tooltip.bind_tooltip(btn_sa_f, "Check all extensions and directories.")

        btn_ua_f = ttk.Button(
            buttons, text="Unselect all", command=self.clear_filters, style="Ghost.TButton"
        )
        btn_ua_f.pack(side=tk.LEFT)
        self.f_tooltip.bind_tooltip(btn_ua_f, "Uncheck all extensions and directories.")

        btn_sv_f = ttk.Button(
            buttons,
            text="Confirm",
            command=lambda: self.handle_close(is_confirm=True),
            style="Primary.TButton",
        )
        btn_sv_f.pack(side=tk.RIGHT)
        self.f_tooltip.bind_tooltip(btn_sv_f, "Confirm changes and close the filter manager.")

        self.window.protocol("WM_DELETE_WINDOW", lambda: self.handle_close(is_confirm=False))

    def save_preset(self):
        if hasattr(self, "save_dlg") and self.save_dlg.winfo_exists():
            self.save_dlg.lift()
            return
        st = load_state()
        presets = st.get("repo_gui_presets", {})
        self.save_dlg = tk.Toplevel(self.window)
        self.save_dlg.title("Save Preset")
        self.save_dlg.geometry("340x360")
        self.save_dlg.configure(bg=theme.BG)
        self.save_dlg.transient(self.window)
        self.save_dlg.grab_set()
        ttk.Label(self.save_dlg, text="Existing presets:", style="Sub.TLabel").pack(
            anchor="w", padx=PAD_MD, pady=(PAD_MD, PAD_SM)
        )
        listb = tk.Listbox(
            self.save_dlg,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            selectbackground=theme.PRIMARY,
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            font=("Segoe UI", 10),
            height=8,
        )
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_MD)
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)
        ttk.Label(self.save_dlg, text="Preset name:", style="Sub.TLabel").pack(
            anchor="w", padx=PAD_MD, pady=(PAD_SM, 2)
        )
        name_entry = ttk.Entry(self.save_dlg, font=("Segoe UI", 10))
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
                messagebox.showwarning("Error", "Please enter a preset name.", parent=self.save_dlg)
                return
            if name.lower() == "default":
                messagebox.showwarning(
                    "Error", "The name 'default' is reserved and read-only.", parent=self.save_dlg
                )
                return
            if name in presets:
                if not messagebox.askyesno(
                    "Overwrite?",
                    f"Preset '{name}' already exists.\nDo you want to overwrite it?",
                    parent=self.save_dlg,
                ):
                    return
            ext_list = [ext for ext, var in self.ext_vars.items() if var.get()]
            skip_list = [d for d, var in self.dir_vars.items() if var.get()]
            presets[name] = {"skip_ext": ext_list, "skip": skip_list}
            save_state(repo_gui_presets=presets)
            self.parent_gui.current_preset = name
            self.preset_label_var.set(f"Active Preset: {name}")
            messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=self.save_dlg)
            self.save_dlg.destroy()

        btn_row = ttk.Frame(self.save_dlg)
        btn_row.pack(fill=tk.X, padx=PAD_MD, pady=PAD_MD)
        ttk.Button(btn_row, text="Save", command=do_save, style="Primary.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(
            btn_row, text="Cancel", command=self.save_dlg.destroy, style="Ghost.TButton"
        ).pack(side=tk.RIGHT, padx=(0, PAD_SM))
        self.save_dlg.bind("<Return>", lambda e: do_save())

    def load_preset(self):
        if hasattr(self, "load_dlg") and self.load_dlg.winfo_exists():
            self.load_dlg.lift()
            return
        st = load_state()
        presets = st.get("repo_gui_presets", {})

        def on_select(name):
            if name == "default":
                for var in self.ext_vars.values():
                    var.set(False)
                for var in self.dir_vars.values():
                    var.set(True)
                self.parent_gui.current_preset = None
                self.preset_label_var.set("Active Preset: None")
                self.load_dlg.destroy()
                return
            preset = presets[name]
            for ext, var in self.ext_vars.items():
                if "ext" in preset:
                    var.set(ext not in preset["ext"])
                else:
                    var.set(ext in preset.get("skip_ext", []))
            for directory, var in self.dir_vars.items():
                var.set(directory in preset.get("skip", []))
            self.parent_gui.current_preset = name
            self.preset_label_var.set(f"Active Preset: {name}")
            self.load_dlg.destroy()

        self.load_dlg = tk.Toplevel(self.window)
        self.load_dlg.title("Load Preset")
        self.load_dlg.geometry("300x300")
        self.load_dlg.configure(bg=theme.BG)
        self.load_dlg.transient(self.window)
        self.load_dlg.grab_set()
        listb = tk.Listbox(
            self.load_dlg,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            selectbackground=theme.PRIMARY,
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=1,
        )
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
        listb.insert(tk.END, "default")
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)

        def load_btn():
            sel = listb.curselection()
            if sel:
                on_select(listb.get(sel[0]))

        ttk.Button(self.load_dlg, text="Load", command=load_btn, style="Primary.TButton").pack(
            pady=PAD_SM
        )

    def delete_preset(self):
        if hasattr(self, "del_dlg") and self.del_dlg.winfo_exists():
            self.del_dlg.lift()
            return
        st = load_state()
        presets = st.get("repo_gui_presets", {})
        if not presets:
            messagebox.showinfo("Presets", "No saved presets found.", parent=self.window)
            return

        def on_select(name):
            confirm = messagebox.askyesno(
                "Confirm Delete", f"Delete preset '{name}'?", parent=self.del_dlg
            )
            if confirm:
                del presets[name]
                save_state(repo_gui_presets=presets)
                if self.parent_gui.current_preset == name:
                    self.parent_gui.current_preset = None
                    self.preset_label_var.set("Active Preset: None")
                messagebox.showinfo("Deleted", f"Preset '{name}' deleted.", parent=self.window)
            self.del_dlg.destroy()

        self.del_dlg = tk.Toplevel(self.window)
        self.del_dlg.title("Delete Preset")
        self.del_dlg.geometry("300x300")
        self.del_dlg.configure(bg=theme.BG)
        self.del_dlg.transient(self.window)
        self.del_dlg.grab_set()
        listb = tk.Listbox(
            self.del_dlg,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            selectbackground=theme.PRIMARY,
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=1,
        )
        listb.pack(fill=tk.BOTH, expand=True, padx=PAD_SM, pady=PAD_SM)
        for p in sorted(presets.keys()):
            listb.insert(tk.END, p)

        def del_btn():
            sel = listb.curselection()
            if sel:
                on_select(listb.get(sel[0]))

        ttk.Button(self.del_dlg, text="Delete", command=del_btn, style="Danger.Ghost.TButton").pack(
            pady=PAD_SM
        )

    def load_default_preset(self):
        for var in self.ext_vars.values():
            var.set(True)
        for var in self.dir_vars.values():
            var.set(True)
        self.parent_gui.current_preset = None
        self.preset_label_var.set("Active Preset: None")

    def select_all_filters(self):
        for var in self.ext_vars.values():
            var.set(True)
        for var in self.dir_vars.values():
            var.set(True)

    def clear_filters(self):
        for var in self.ext_vars.values():
            var.set(False)
        for var in self.dir_vars.values():
            var.set(False)

    def handle_close(self, is_confirm=False):
        current_exts = {ext for ext, var in self.ext_vars.items() if var.get()}
        current_skips = {d for d, var in self.dir_vars.items() if var.get()}
        changed_from_start = (
            current_exts != self.original_skip_exts or current_skips != self.original_skip_dirs
        )

        if self.parent_gui.current_preset:
            st = load_state()
            presets = st.get("repo_gui_presets", {})
            if self.parent_gui.current_preset in presets:
                p = presets[self.parent_gui.current_preset]
                preset_changed = False
                old_ext = p.get("ext")
                if old_ext is not None:
                    preset_skip_exts = {ext for ext in DEFAULT_EXTENSIONS if ext not in old_ext}
                else:
                    preset_skip_exts = set(p.get("skip_ext", []))

                if sorted(list(current_exts)) != sorted(list(preset_skip_exts)):
                    preset_changed = True
                if sorted(list(current_skips)) != sorted(p.get("skip", [])):
                    preset_changed = True

                if preset_changed:
                    ans = messagebox.askyesnocancel(
                        "Update Preset?",
                        f"Preset '{self.parent_gui.current_preset}' has unsaved changes.\n\nYES = Update preset and apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.",
                        parent=self.window,
                    )
                    if ans is None:
                        return
                    if ans is True:
                        presets[self.parent_gui.current_preset] = {
                            "skip_ext": list(current_exts),
                            "skip": list(current_skips),
                        }
                        save_state(repo_gui_presets=presets)
                        self.parent_gui.skip_exts = current_exts
                        self.parent_gui.skip_dirs = current_skips
                    else:
                        self.parent_gui.skip_exts = self.original_skip_exts
                        self.parent_gui.skip_dirs = self.original_skip_dirs
                    save_state(
                        repo_gui_skip_exts=list(self.parent_gui.skip_exts),
                        repo_gui_skip_dirs=list(self.parent_gui.skip_dirs),
                        repo_gui_current_preset=self.parent_gui.current_preset,
                    )
                    self.window.destroy()
                    return

        if is_confirm:
            self.parent_gui.skip_exts = current_exts
            self.parent_gui.skip_dirs = current_skips
            save_state(
                repo_gui_skip_exts=list(self.parent_gui.skip_exts),
                repo_gui_skip_dirs=list(self.parent_gui.skip_dirs),
                repo_gui_current_preset=self.parent_gui.current_preset,
            )
            self.window.destroy()
        else:
            if changed_from_start:
                ans = messagebox.askyesnocancel(
                    "Unsaved changes",
                    "You have unsaved changes.\n\nYES = Apply changes.\nNO = Discard changes and close.\nCANCEL = Return to window.",
                    parent=self.window,
                )
                if ans is None:
                    return
                if ans is True:
                    self.parent_gui.skip_exts = current_exts
                    self.parent_gui.skip_dirs = current_skips
                else:
                    self.parent_gui.skip_exts = self.original_skip_exts
                    self.parent_gui.skip_dirs = self.original_skip_dirs
                save_state(
                    repo_gui_skip_exts=list(self.parent_gui.skip_exts),
                    repo_gui_skip_dirs=list(self.parent_gui.skip_dirs),
                    repo_gui_current_preset=self.parent_gui.current_preset,
                )
                self.window.destroy()
            else:
                self.window.destroy()
