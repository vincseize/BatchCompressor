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

    @staticmethod
    def get_file_size_mb(filepath):
        """Retourne la taille du fichier en Mo, arrondie à 2 décimales"""
        try:
            size_bytes = os.path.getsize(filepath)
            return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            return None


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

                input_size = self.file_manager.get_file_size_mb(input_file)
                if input_size is not None:
                    log_callback(f"Fichier : {filename} ({input_size} Mo)")

                # Met à jour la progression AVANT la conversion, avec nom fichier
                progress_callback((i - 1) / self.total_files * 100, filename)
                log_callback(f"Traitement: {filename}")

                try:
                    success = self.converter.convert(input_file, output_file, compression_level)
                    if success:
                        output_size = self.file_manager.get_file_size_mb(output_file)
                        if output_size is not None:
                            log_callback(f"Compression : {input_size} Mo → {output_size} Mo")
                        log_callback("✓ Succès")
                    else:
                        log_callback("✗ Échec")
                        raise Exception(f"Échec de la conversion de {filename}")

                except Exception as e:
                    log_callback(f"Erreur: {str(e)}")
                    raise

                # Met à jour la progression APRÈS la conversion, avec nom fichier aussi
                progress_callback(i / self.total_files * 100, filename)


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
    
    def _get_total_size_mb(self, folder):
        video_files = self.file_manager.get_video_files(folder)
        total_size = 0.0
        for f in video_files:
            size = self.file_manager.get_file_size_mb(f)
            if size:
                total_size += size
        return round(total_size, 2)


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

            total_size = self._get_total_size_mb(folder)
            self._log_message(f"Taille totale des fichiers MP4 dans le dossier : {total_size} Mo")


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
        """Lance la conversion dans un thread séparé"""
        if self.conversion_task.running:
            return

        self.convert_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.set(0)
        self.current_file.set("")
        self.log_widget.configure(state='normal')
        self.log_widget.delete('1.0', tk.END)
        self.log_widget.configure(state='disabled')
        self._log_message("Préparation de la conversion...")

        self.status_label.config(text="Conversion en cours...")
        self._animate_dots = True
        self._dot_count = 0
        self._update_dots()

        thread = Thread(
            target=self._run_conversion_thread,
            args=(self.input_folder.get(), self.output_folder.get(), self.compression_level.get())
        )
        thread.start()

    def _update_dots(self):
        """Affiche l'animation '...' pendant la conversion"""
        if self._animate_dots:
            self._dot_count = (self._dot_count + 1) % 4
            self.status_label.config(text="Conversion en cours" + "." * self._dot_count)
            self.after(500, self._update_dots)

    def _run_conversion_thread(self, input_folder, output_folder, level):
        try:
            self.conversion_task.process(
                input_folder, output_folder, level,
                self._update_progress,
                self._log_message
            )
        except Exception as e:
            self._log_message(f"Erreur fatale : {str(e)}")
        finally:
            self._on_conversion_finished()

    def _on_conversion_finished(self):
        """Remet l'état initial après conversion"""
        self.convert_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # Ici, conversion terminée = running == False
        if self.conversion_task.running:
            self.status_label.config(text="Conversion en cours")
        else:
            self.status_label.config(text="Conversion terminée")
        self._animate_dots = False
        self.current_file.set("")
        self.progress.set(100)


    def _stop_conversion(self):
        """Demande l'arrêt de la conversion"""
        if self.conversion_task.running:
            self.conversion_task.stop()
            self.status_label.config(text="Arrêt demandé...")
            self._log_message("Arrêt en cours...")
            self._animate_dots = False

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
