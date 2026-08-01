import os
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from contextor.repo_generator.config import DEFAULT_EXTENSIONS, DEFAULT_SKIP_DIRS
from contextor.repo_generator.filters import FilterWindow
from contextor.repo_generator.icons import create_icon_button
from contextor.ui import theme
from contextor.ui.path_memory import load_state, save_state
from contextor.ui.theme import PAD_LG, PAD_MD, PAD_SM, HeaderTooltipManager, apply_theme


class RepoGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Repo Builder - Context Generator")
        self.root.minsize(800, 600)

        state = load_state()

        generator_pos = state.get("generator_pos", "")
        if generator_pos:
            self.root.geometry(generator_pos)

        self.files = state.get("repo_gui_files", [])
        saved_selections = state.get("repo_gui_selected", [])

        exts = state.get("repo_gui_skip_exts")
        self.skip_exts = set(exts) if exts is not None else set()

        skips = state.get("repo_gui_skip_dirs")
        self.skip_dirs = set(skips) if skips is not None else set(DEFAULT_SKIP_DIRS)
        self.current_preset = state.get("repo_gui_current_preset", None)

        self.split_enabled_val = state.get("repo_gui_split_enabled", False)
        self.split_size_val = state.get("repo_gui_split_size", 200)

        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT")
        os.makedirs(self.output_dir, exist_ok=True)

        self.build_gui()

        for path in self.files:
            self.listbox.insert(tk.END, path)

        for idx in saved_selections:
            try:
                self.listbox.selection_set(idx)
            except Exception:
                pass

        self.update_estimation_info()

    def build_gui(self):
        ttk.Label(self.root, text="Repo Builder", style="Header.TLabel").pack(
            anchor="w", padx=PAD_LG, pady=(PAD_LG, 0)
        )

        sub_label = ttk.Label(
            self.root, text="Select files to include in generated context", style="Sub.TLabel"
        )
        sub_label.pack(anchor="w", padx=PAD_LG, pady=(2, PAD_MD))
        self.tooltip = HeaderTooltipManager(
            sub_label, "Select files to include in generated context"
        )

        toolbar = ttk.Frame(self.root)
        toolbar.pack(padx=PAD_LG, fill=tk.X)

        btn_repo = create_icon_button(toolbar, "SELECT REPO", self.add_repository, "big_plus")
        self.tooltip.bind_tooltip(
            btn_repo,
            "Add a full repository folder. Automatically filters out skipped directories/extensions.",
        )

        btn_files = create_icon_button(toolbar, "ADD FILES", self.add_files, "small_plus")
        self.tooltip.bind_tooltip(btn_files, "Manually add specific files to the generation list.")

        btn_rem = create_icon_button(toolbar, "REMOVE SELECTED", self.remove_selected, "big_minus")
        self.tooltip.bind_tooltip(btn_rem, "Remove selected files from the generation list.")

        btn_clear = create_icon_button(toolbar, "REMOVE ALL", self.remove_all, "small_minus")
        self.tooltip.bind_tooltip(btn_clear, "Clear the entire generation list.")

        frame = ttk.Frame(self.root, style="Card.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=PAD_LG, pady=PAD_MD)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            yscrollcommand=scrollbar.set,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            selectbackground=theme.PRIMARY,
            selectforeground="#ffffff",
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Bindings for new features on the root to ensure they are captured regardless of focus
        self.root.bind("<Control-v>", self.on_paste)
        self.root.bind("<Control-V>", self.on_paste)
        self.root.bind("<Command-v>", self.on_paste)  # Mac

        self.listbox.bind("<Delete>", self.on_delete_key)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.update_estimation_info())

        # Info Frame above Select All/Unselect All
        info_frame = ttk.Frame(frame)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(PAD_SM, PAD_SM))
        self.info_label = ttk.Label(
            info_frame, text="Estimated file size: 0 KB | Estimated lines: 0", style="Sub.TLabel"
        )
        self.info_label.pack(side=tk.LEFT)

        controls = ttk.Frame(frame)
        controls.pack(side=tk.BOTTOM, fill=tk.X)

        btn_sa = ttk.Button(
            controls, text="Select all", command=self.select_all, style="Ghost.TButton"
        )
        btn_sa.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(btn_sa, "Select all files in the list for generation.")

        btn_ua = ttk.Button(
            controls, text="Unselect all", command=self.unselect_all, style="Ghost.TButton"
        )
        btn_ua.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(btn_ua, "Deselect all files.")

        bottom = ttk.Frame(self.root)
        bottom.pack(padx=PAD_LG, pady=(0, PAD_SM), fill=tk.X)

        btn_ff = ttk.Button(
            bottom, text="File filters", command=self.open_filters, style="Secondary.TButton"
        )
        btn_ff.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(
            btn_ff, "Configure extensions and directories to ignore when adding a repository."
        )

        btn_of = ttk.Button(
            bottom, text="Output Folder", command=self.open_output_folder, style="Secondary.TButton"
        )
        btn_of.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(
            btn_of, "Open folder where the generated repository text files are saved."
        )

        btn_eo = ttk.Button(
            bottom, text="Empty output", command=self.clear_output, style="Danger.Ghost.TButton"
        )
        btn_eo.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(btn_eo, "Delete all previously generated text files.")

        split_frame = ttk.Frame(bottom)
        split_frame.pack(side=tk.RIGHT, padx=PAD_SM)

        self.split_enabled = tk.BooleanVar(value=self.split_enabled_val)
        chk_split = ttk.Checkbutton(split_frame, text="File split", variable=self.split_enabled)
        chk_split.pack(side=tk.LEFT, padx=(0, PAD_SM))
        self.tooltip.bind_tooltip(chk_split, "Automatic file split into fragments of defined size")

        self.split_size = tk.IntVar(value=self.split_size_val)
        entry_split = ttk.Entry(split_frame, textvariable=self.split_size, width=5)
        entry_split.pack(side=tk.LEFT)
        self.tooltip.bind_tooltip(entry_split, "Result file split size")

        ttk.Label(split_frame, text="KB").pack(side=tk.LEFT, padx=(PAD_SM, 0))

        btn_gen = ttk.Button(
            self.root, text="Generate repository", command=self.generate, style="Primary.TButton"
        )
        btn_gen.pack(padx=PAD_LG, pady=(0, PAD_LG), fill=tk.X)
        self.tooltip.bind_tooltip(
            btn_gen, "Bundle all selected files into a single text file (LLM Context)."
        )

    # === NEW FEATURES ===

    def on_paste(self, event):
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            return  # Empty clipboard

        lines = clipboard_text.splitlines()
        added = 0
        for line in lines:
            path = line.strip().strip('"').strip("'")
            if not path:
                continue
            if os.path.exists(path) and os.path.isfile(path):
                if path not in self.files:
                    self.files.append(path)
                    self.listbox.insert(tk.END, path)
                    added += 1

        if added > 0:
            self.select_all()
            self.update_estimation_info()
            messagebox.showinfo(
                "Paste Paths",
                f"Successfully pasted and added {added} valid files.",
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Paste Paths", "No valid file paths found in clipboard.", parent=self.root
            )

    def on_delete_key(self, event):
        selected_indexes = list(self.listbox.curselection())
        if not selected_indexes:
            return

        count = len(selected_indexes)
        ans = messagebox.askyesnocancel(
            "Delete files",
            f"Are you sure you want to remove {count} files from the list?",
            parent=self.root,
        )
        if ans is True:  # Yes
            selected_indexes.sort(reverse=True)
            for idx in selected_indexes:
                self.listbox.delete(idx)
                del self.files[idx]
            self.update_estimation_info()

    def update_estimation_info(self):
        selected_indexes = self.listbox.curselection()
        total_size = 0
        total_lines = 0

        for i in selected_indexes:
            try:
                path = self.files[i]
                if os.path.exists(path) and os.path.isfile(path):
                    total_size += os.path.getsize(path)
                    with open(path, "rb") as f:
                        total_lines += sum(1 for _ in f)
            except Exception:
                pass

        size_kb = total_size / 1024
        self.info_label.config(
            text=f"Estimated file size: {size_kb:.2f} KB | Estimated lines: {total_lines}"
        )

    # === CORE ===

    def is_directory_blocked(self, path):
        parts = path.replace("\\", "/").split("/")
        for part in parts:
            for skip in self.skip_dirs:
                if part.lower() == skip.lower():
                    return True
        return False

    def is_filename_blocked(self, filename):
        filename_lower = filename.lower()
        for skip in self.skip_dirs:
            if skip.lower() == filename_lower:
                return True
        return False

    def is_extension_allowed(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in DEFAULT_EXTENSIONS:
            return False
        return ext not in self.skip_exts

    def add_repository(self):
        folder = filedialog.askdirectory(parent=self.root)
        if not folder:
            return

        added = 0
        blocked = 0
        new_files = []

        for root, dirs, files in os.walk(folder):
            dirs[:] = [
                d for d in dirs if not any(d.lower() == skip.lower() for skip in self.skip_dirs)
            ]
            for filename in files:
                full_path = os.path.join(root, filename)
                if self.is_directory_blocked(full_path):
                    blocked += 1
                    continue
                if self.is_filename_blocked(filename):
                    blocked += 1
                    continue
                if not self.is_extension_allowed(full_path):
                    blocked += 1
                    continue
                if full_path in self.files:
                    continue
                self.files.append(full_path)
                new_files.append(full_path)
                added += 1

        for path in new_files:
            self.listbox.insert(tk.END, path)

        if new_files:
            self.select_all()

        messagebox.showinfo(
            "Repo added", f"Files added: {added}\nSkipped: {blocked}", parent=self.root
        )

    def add_files(self):
        selected = filedialog.askopenfilenames(title="Select files", parent=self.root)
        if not selected:
            return

        added = 0
        blocked = []

        for path in selected:
            filename = os.path.basename(path)
            if self.is_directory_blocked(path):
                blocked.append(path)
                continue
            if self.is_filename_blocked(filename):
                blocked.append(path)
                continue
            if not self.is_extension_allowed(path):
                blocked.append(path)
                continue
            if path in self.files:
                continue
            self.files.append(path)
            self.listbox.insert(tk.END, path)
            added += 1

        if added:
            self.select_all()

        if blocked:
            messagebox.showwarning(
                "Skipped files",
                "Elements are on the excluded list:\n\n"
                + "\n".join(blocked[:10])
                + ("\n..." if len(blocked) > 10 else ""),
                parent=self.root,
            )
        elif added:
            messagebox.showinfo("Files added", f"Added: {added}", parent=self.root)

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        selected.reverse()
        for index in selected:
            self.listbox.delete(index)
            del self.files[index]
        self.update_estimation_info()

    def remove_all(self):
        if not self.files:
            return
        if messagebox.askyesno("Confirmation", "Clear all files from the list?", parent=self.root):
            self.files.clear()
            self.listbox.delete(0, tk.END)
            self.update_estimation_info()

    def select_all(self):
        if self.listbox.size() == 0:
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(0, tk.END)
        self.listbox.activate(0)
        self.update_estimation_info()

    def unselect_all(self):
        self.listbox.selection_clear(0, tk.END)
        self.update_estimation_info()

    def open_filters(self):
        if hasattr(self, "filter_window_inst") and self.filter_window_inst.window.winfo_exists():
            self.filter_window_inst.window.lift()
            return
        self.filter_window_inst = FilterWindow(self)

    def open_output_folder(self):
        os.makedirs(self.output_dir, exist_ok=True)
        import sys

        if sys.platform.startswith("win"):
            os.startfile(self.output_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", self.output_dir])
        else:
            subprocess.run(["xdg-open", self.output_dir])

    def clear_output(self):
        if not os.path.exists(self.output_dir):
            return
        confirm = messagebox.askyesno(
            "Empty output",
            "Are you sure you want to clear output?\nThis operation cannot be undone.",
            parent=self.root,
        )
        if not confirm:
            return
        for item in os.listdir(self.output_dir):
            path = os.path.join(self.output_dir, item)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def generate(self):
        selected_indexes = self.listbox.curselection()
        if not selected_indexes:
            messagebox.showwarning("No selection", "Select files to generate.", parent=self.root)
            return

        files_to_generate = [self.files[i] for i in selected_indexes]

        if files_to_generate:
            try:
                cpath = os.path.commonpath(files_to_generate)
                if os.path.isfile(cpath):
                    prefix = os.path.basename(os.path.dirname(cpath))
                    if not prefix:
                        prefix = os.path.basename(cpath).split(".")[0]
                else:
                    prefix = os.path.basename(cpath)
            except ValueError:
                prefix = "repo"
            prefix = "".join(c for c in prefix if c.isalnum() or c in ("_", "-")).strip()
            if not prefix:
                prefix = "repo"
        else:
            prefix = "repo"

        output_file = os.path.join(self.output_dir, f"{prefix}_full_repo.txt")

        with open(output_file, "w", encoding="utf-8") as out:
            for full_path in files_to_generate:
                if not self.is_extension_allowed(full_path):
                    continue
                relative = os.path.basename(full_path)
                out.write(f"#~~~~~~[FILE START: {relative} ]~~~~~~#\n")
                try:
                    with open(full_path, encoding="utf-8", errors="ignore") as source:
                        out.write(source.read())
                except Exception as e:
                    out.write("\nREAD ERROR:\n")
                    out.write(str(e))
                out.write(f"\n#~~~~~~[FILE END: {relative} ]~~~~~~#\n\n")

        if self.split_enabled.get():
            try:
                limit_bytes = self.split_size.get() * 1024
                if os.path.getsize(output_file) > limit_bytes:
                    with open(output_file, encoding="utf-8") as source:
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
                        part_file = os.path.join(
                            self.output_dir, f"{prefix}_part_{idx}_from_{total_chunks}.txt"
                        )
                        with open(part_file, "w", encoding="utf-8") as pf:
                            pf.writelines(chunk_lines)
            except Exception:
                pass

        messagebox.showinfo("Done", "Repository generated:\n\n" + output_file, parent=self.root)


def run_repo_generator(parent=None):
    if parent:
        root = tk.Toplevel(parent)
    else:
        root = tk.Tk()

    state = load_state()
    generator_pos = state.get("generator_pos", "")
    if generator_pos:
        root.geometry(generator_pos)
    root.minsize(800, 600)

    # Styles are registered on the interpreter, so a Toplevel already
    # inherits them; this only paints the new window's own background
    # and keeps the active mode.
    apply_theme(root)
    theme.retint(root)

    app = RepoGenerator(root)

    def on_closing():
        import re

        geom = root.geometry()
        m = re.match(r"^(\d+x\d+)([+-]?\d+)([+-]?\d+)$", geom.replace("+-", "-"))
        if m:
            size = m.group(1)
            x, y = max(0, int(m.group(2))), max(0, int(m.group(3)))
            pos = f"{size}+{x}+{y}"
        else:
            pos = ""

        save_state(
            generator_pos=pos,
            repo_gui_files=app.files,
            repo_gui_selected=list(app.listbox.curselection()),
            repo_gui_skip_exts=list(app.skip_exts),
            repo_gui_skip_dirs=list(app.skip_dirs),
            repo_gui_current_preset=app.current_preset,
            repo_gui_split_enabled=app.split_enabled.get(),
            repo_gui_split_size=app.split_size.get(),
        )
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    if parent is None:
        root.mainloop()
    return root


if __name__ == "__main__":
    run_repo_generator()
