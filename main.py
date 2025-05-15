import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from threading import Thread
import glob
import sys

class VideoConverter:
    """Gère la conversion des vidéos avec FFmpeg"""
    def __init__(self, ffmpeg_path):
        self.ffmpeg_path = ffmpeg_path
        self.compression_levels = {
            "low": {'crf': '28', 'preset': 'fast'},
            "medium": {'crf': '23', 'preset': 'medium'},
            "high": {'crf': '18', 'preset': 'slow'}
        }

    def get_compression_params(self, level):
        return self.compression_levels.get(level, self.compression_levels["medium"])

    def convert(self, input_file, output_file, compression_level):
        """Convertit un fichier vidéo avec les paramètres de compression spécifiés"""
        compression = self.get_compression_params(compression_level)
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            cmd = [
                self.ffmpeg_path, '-y', '-i', input_file,
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
            raise Exception(f"Erreur lors de la conversion: {str(e)}")


class FileManager:
    """Gère les opérations sur les fichiers"""
    @staticmethod
    def get_video_files(folder):
        """Retourne la liste des fichiers MP4 dans le dossier"""
        return sorted([
            f for f in glob.glob(os.path.join(folder, '*.mp4'))
            if os.path.isfile(f)
        ])

    @staticmethod
    def create_output_folder(path):
        """Crée le dossier de sortie si nécessaire"""
        os.makedirs(path, exist_ok=True)


class ConversionTask:
    """Gère une tâche de conversion avec suivi de progression"""
    def __init__(self, converter, file_manager):
        self.converter = converter
        self.file_manager = file_manager
        self.running = False
        self.total_files = 0
        self.processed_files = 0

    def process(self, input_folder, output_folder, compression_level, progress_callback, log_callback):
        """Exécute la conversion des fichiers"""
        self.running = True
        try:
            if not input_folder or not output_folder:
                raise ValueError("Les dossiers source et destination doivent être spécifiés")

            self.file_manager.create_output_folder(output_folder)
            video_files = self.file_manager.get_video_files(input_folder)
            
            if not video_files:
                raise ValueError("Aucun fichier MP4 trouvé dans le dossier source")

            self.total_files = len(video_files)
            self.processed_files = 0
            
            log_callback(f"Début de conversion ({compression_level}) - {self.total_files} fichiers")

            for i, input_file in enumerate(video_files, 1):
                if not self.running:
                    break

                self.processed_files = i
                filename = os.path.basename(input_file)
                output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_comp.mp4")
                
                progress_callback((i-1)/self.total_files*100, filename)
                log_callback(f"Traitement: {filename}")

                try:
                    success = self.converter.convert(input_file, output_file, compression_level)
                    if success:
                        log_callback("✓ Succès")
                    else:
                        log_callback("✗ Échec")
                        raise Exception(f"Échec de la conversion de {filename}")
                except Exception as e:
                    log_callback(f"Erreur: {str(e)}")
                    raise

                progress_callback(i/self.total_files*100)

            if self.running:
                log_callback("✅ Conversion terminée")
                return True
            else:
                log_callback("⛔ Conversion interrompue")
                return False
        finally:
            self.running = False

    def stop(self):
        """Arrête la conversion en cours"""
        self.running = False


class MainApplication(tk.Tk):
    """Interface graphique principale"""
    def __init__(self):
        super().__init__()
        self.title("Convertisseur Vidéo par Lots")
        
        # Initialisation des composants
        self.converter = VideoConverter(self._get_ffmpeg_path())
        self.file_manager = FileManager()
        self.conversion_task = ConversionTask(self.converter, self.file_manager)
        
        # Variables d'interface
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.current_file = tk.StringVar(value="")
        self.compression_level = tk.StringVar(value="medium")
        self.progress = tk.DoubleVar()
        
        # Configuration de l'interface
        self._setup_ui()
        
    def _get_ffmpeg_path(self):
        """Retourne le chemin de ffmpeg selon l'environnement"""
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Dossier source
        ttk.Label(main_frame, text="Dossier source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self._select_input_folder).grid(row=0, column=2, padx=5)
        
        # Dossier de sortie
        ttk.Label(main_frame, text="Dossier de sortie:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self._select_output_folder).grid(row=1, column=2, padx=5)
        
        # Niveau de compression
        ttk.Label(main_frame, text="Niveau de compression:").grid(row=2, column=0, sticky=tk.W, pady=5)
        compression_combo = ttk.Combobox(main_frame, textvariable=self.compression_level, 
                                       values=["low", "medium", "high"], state="readonly")
        compression_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        compression_combo.current(1)
        
        # Fichier en cours
        ttk.Label(main_frame, text="Fichier en cours:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.current_file).grid(row=3, column=1, columnspan=2, sticky=tk.W)
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E, pady=10)
        
        # Compteur fichiers
        self.file_counter = ttk.Label(main_frame, text="0/0 fichiers traités")
        self.file_counter.grid(row=5, column=0, columnspan=3, sticky=tk.W)
        
        # Journal d'activité
        ttk.Label(main_frame, text="Journal d'activité:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.log_widget = scrolledtext.ScrolledText(main_frame, height=10, state='disabled')
        self.log_widget.grid(row=7, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=10)
        
        self.convert_btn = ttk.Button(btn_frame, text="Convertir", command=self._start_conversion)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Arrêter", command=self._stop_conversion, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Prêt")
        self.status_label.grid(row=9, column=0, columnspan=3, sticky=tk.W+tk.E)

        # Configuration du redimensionnement
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def _select_input_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier source")
        if folder:
            self.input_folder.set(folder)
            self.output_folder.set(os.path.join(folder, "mp4_comp"))
            self._update_file_count()

    def _select_output_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if folder:
            self.output_folder.set(folder)

    def _update_file_count(self):
        """Met à jour le compteur de fichiers"""
        input_folder = self.input_folder.get()
        if input_folder:
            video_files = self.file_manager.get_video_files(input_folder)
            self.total_files = len(video_files)
            self.file_counter.config(text=f"0/{self.total_files} fichiers traités")
            self.status_label.config(text=f"Prêt - {self.total_files} vidéos à convertir")
            self.progress.set(0)

    def _log_message(self, message):
        """Ajoute un message au journal"""
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.configure(state='disabled')
        self.log_widget.see(tk.END)
        self.update_idletasks()

    def _update_progress(self, percent=None, current_file=""):
        """Met à jour la progression"""
        if percent is not None:
            self.progress.set(percent)
        if current_file:
            self.current_file.set(os.path.basename(current_file))
        if hasattr(self, 'total_files') and self.total_files > 0:
            self.file_counter.config(text=f"{self.conversion_task.processed_files}/{self.total_files} fichiers traités")
        self.update_idletasks()

    def _start_conversion(self):
        """Démarre la conversion"""
        if self.conversion_task.running:
            return

        self.convert_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Conversion en cours...")
        
        def run_conversion():
            try:
                success = self.conversion_task.process(
                    input_folder=self.input_folder.get(),
                    output_folder=self.output_folder.get(),
                    compression_level=self.compression_level.get(),
                    progress_callback=self._update_progress,
                    log_callback=self._log_message
                )
                
                if success:
                    messagebox.showinfo("Terminé", "Conversion terminée avec succès!")
                    self.status_label.config(text="Prêt - Conversion terminée")
                else:
                    messagebox.showwarning("Interrompu", "Conversion interrompue")
                    self.status_label.config(text="Prêt - Conversion interrompue")
                    
            except Exception as e:
                self._log_message(f"❌ Erreur: {str(e)}")
                messagebox.showerror("Erreur", str(e))
                self.status_label.config(text="Prêt - Erreur de conversion")
            finally:
                self.convert_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.progress.set(0)

        Thread(target=run_conversion, daemon=True).start()

    def _stop_conversion(self):
        """Arrête la conversion"""
        self.conversion_task.stop()
        self._log_message("⛔ Conversion arrêtée par l'utilisateur")
        self.status_label.config(text="Prêt - Conversion arrêtée")
        self.stop_btn.config(state=tk.DISABLED)
        self.convert_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
