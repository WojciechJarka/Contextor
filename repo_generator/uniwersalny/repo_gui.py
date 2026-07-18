import tkinter as tk
from tkinter import filedialog, messagebox
import os

# --- KONFIGURACJA ---
# Rozszerzenia, które mają być dodawane do repozytorium
FILE_EXTENSIONS = {".py", ".bat", ".vbs", ".js", ".sh", ".md", ".txt", ".json"}
# Katalogi/pliki, które zawsze pomijamy
SKIP_DIRS = {".git", "venv", "__pycache__"}

class RepoGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Generator Repozytorium")
        self.root.geometry("400x250")
        
        self.path_var = tk.StringVar()
        self.filter_md = tk.BooleanVar(value=True)

        tk.Label(root, text="Wybierz katalog do zindeksowania:").pack(pady=10)
        
        frame = tk.Frame(root)
        frame.pack(pady=5)
        tk.Entry(frame, textvariable=self.path_var, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="...", command=self.browse).pack(side=tk.LEFT)
        
        tk.Checkbutton(root, text="Filtruj (usuń) pliki .md", variable=self.filter_md).pack(pady=10)
        tk.Button(root, text="GENERUJ REPOZYTORIUM", command=self.generate, 
                  bg="green", fg="white", height=2).pack(pady=10)

    def browse(self):
        path = filedialog.askdirectory()
        if path: self.path_var.set(path)

    def generate(self):
        repo_folder = self.path_var.get()
        if not os.path.exists(repo_folder):
            messagebox.showerror("Błąd", "Nieprawidłowa ścieżka!")
            return

        folder_name = os.path.basename(repo_folder)
        output_filename = f"repozytorium_{folder_name}.txt"
        output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)

        try:
            with open(output_file, "w", encoding="utf-8") as out:
                for root, dirs, files in os.walk(repo_folder):
                    # Filtrowanie folderów (usuwanie z listy dirs modyfikuje zachowanie os.walk)
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    
                    for file in files:
                        # Pomijanie samego pliku wynikowego
                        if file == output_filename: continue
                        
                        ext = os.path.splitext(file)[1].lower()
                        if ext not in FILE_EXTENSIONS: continue
                        
                        # Filtrowanie plików .md
                        if self.filter_md.get() and ext == ".md": continue
                        
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, repo_folder)

                        out.write(f"#~~~~~~[START PLIKU: {rel_path} ]~~~~~~#\n")
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                out.write(f.read())
                        except Exception as e:
                            out.write(f"BŁĄD ODCZYTU: {e}")
                        out.write(f"\n#~~~~~~[KONIEC PLIKU: {rel_path} ]~~~~~~#\n\n")
            
            messagebox.showinfo("Sukces", f"Gotowe! Plik zapisano:\n{output_file}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoGenerator(root)
    root.mainloop()