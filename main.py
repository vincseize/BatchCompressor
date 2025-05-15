import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from threading import Thread
import glob
import sys

class BatchVideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Convertisseur Vidéo par Lots")
        
        # Variables
        self.progress = tk.DoubleVar()
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.current_file = tk.StringVar(value="")
        self.compression_level = tk.StringVar(value="medium")  # Niveau par défaut
        self.running = False
        self.total_files = 0
        self.processed_files = 0
        
        # Interface
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(main_frame, text="Dossier source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self.select_input_folder).grid(row=0, column=2, padx=5)
        
        ttk.Label(main_frame, text="Dossier de sortie:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self.select_output_folder).grid(row=1, column=2, padx=5)
        
        ttk.Label(main_frame, text="Niveau de compression:").grid(row=2, column=0, sticky=tk.W, pady=5)
        compression_combo = ttk.Combobox(main_frame, textvariable=self.compression_level, 
                                         values=["low", "medium", "high"], state="readonly")
        compression_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        compression_combo.current(1)
        
        ttk.Label(main_frame, text="Fichier en cours:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.current_file).grid(row=3, column=1, columnspan=2, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E, pady=10)
        
        self.file_counter = ttk.Label(main_frame, text="0/0 fichiers traités")
        self.file_counter.grid(row=5, column=0, columnspan=3, sticky=tk.W)
        
        ttk.Label(main_frame, text="Journal d'activité:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.log_widget = scrolledtext.ScrolledText(main_frame, height=10, state='disabled')
        self.log_widget.grid(row=7, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=10)
        
        self.convert_btn = ttk.Button(btn_frame, text="Convertir", command=self.start_conversion)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Arrêter", command=self.stop_conversion, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(main_frame, text="Prêt")
        self.status_label.grid(row=9, column=0, columnspan=3, sticky=tk.W+tk.E)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier source")
        if folder:
            self.input_folder.set(folder)
            self.output_folder.set(os.path.join(folder, "mp4_comp"))
            self.update_file_count()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if folder:
            self.output_folder.set(folder)

    def update_file_count(self):
        input_folder = self.input_folder.get()
        if input_folder:
            video_files = self.get_video_files(input_folder)
            self.total_files = len(video_files)
            self.file_counter.config(text=f"0/{self.total_files} fichiers traités")
            self.status_label.config(text=f"Prêt - {self.total_files} vidéos à convertir")
            self.progress.set(0)

    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

    def get_compression_params(self):
        level = self.compression_level.get()
        return {
            "low": {'crf': '28', 'preset': 'fast'},
            "medium": {'crf': '23', 'preset': 'medium'},
            "high": {'crf': '18', 'preset': 'slow'}
        }.get(level, {'crf': '23', 'preset': 'medium'})

    def log_message(self, message):
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.configure(state='disabled')
        self.log_widget.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, value=None, current_file=""):
        if value is not None:
            self.progress.set(value)
        if current_file:
            self.current_file.set(os.path.basename(current_file))
        if self.total_files > 0:
            self.file_counter.config(text=f"{self.processed_files}/{self.total_files} fichiers traités")
        self.root.update_idletasks()

    def get_video_files(self, folder):
        return sorted([
            f for f in glob.glob(os.path.join(folder, '*.mp4'))
            if os.path.isfile(f)
        ])

    def convert_video(self, input_file, output_file):
        ffmpeg_path = self.get_ffmpeg_path()
        compression = self.get_compression_params()
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = [
                ffmpeg_path, '-y', '-i', input_file,
                '-c:v', 'libx264',
                '-crf', compression['crf'],
                '-preset', compression['preset'],
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-strict', 'experimental',
                '-hide_banner',
                '-loglevel', 'error',
                output_file
            ]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW
            )
            process.wait()
            return process.returncode == 0 and os.path.exists(output_file)
        except Exception as e:
            self.log_message(f"Erreur: {e}")
            return False

    def process_folder(self):
        input_folder = self.input_folder.get()
        output_folder = self.output_folder.get()
        if not input_folder or not output_folder:
            messagebox.showwarning("Attention", "Veuillez sélectionner les dossiers source et destination")
            self.running = False
            return

        os.makedirs(output_folder, exist_ok=True)
        video_files = self.get_video_files(input_folder)
        if not video_files:
            messagebox.showinfo("Information", "Aucun fichier MP4 trouvé dans le dossier source")
            self.running = False
            return

        self.total_files = len(video_files)
        self.processed_files = 0
        self.progress.set(0)
        self.update_progress()
        self.log_message(f"Conversion de {self.total_files} fichiers avec compression '{self.compression_level.get()}'")

        for i, input_file in enumerate(video_files, 1):
            if not self.running:
                break
            self.processed_files = i
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_comp.mp4")
            self.update_progress(((i - 1) / self.total_files) * 100, filename)
            self.log_message(f"→ {filename}")
            success = self.convert_video(input_file, output_file)
            self.update_progress((i / self.total_files) * 100)
            if success:
                self.log_message("✓ Succès")
            else:
                self.log_message("✗ Échec")
                messagebox.showerror("Erreur", f"Échec de la conversion: {filename}")

        if self.running:
            self.status_label.config(text="Conversion terminée")
            self.log_message("✅ Conversion terminée")
            messagebox.showinfo("Terminé", "Conversion des fichiers terminée")

        self.running = False
        self.convert_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def start_conversion(self):
        if self.running:
            return
        self.running = True
        self.convert_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        thread = Thread(target=self.process_folder)
        thread.start()

    def stop_conversion(self):
        self.running = False
        self.convert_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Arrêté")
        self.log_message("⛔ Conversion arrêtée")

# Lancement de l'application
if __name__ == "__main__":
    root = tk.Tk()
    app = BatchVideoConverterApp(root)
    root.mainloop()
