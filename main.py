import os
import re
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
        self.running = False
        self.total_files = 0
        self.processed_files = 0
        
        # Interface
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Sélection dossier d'entrée
        ttk.Label(main_frame, text="Dossier source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        input_entry = ttk.Entry(main_frame, textvariable=self.input_folder, width=50)
        input_entry.grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self.select_input_folder).grid(row=0, column=2, padx=5)
        
        # Sélection dossier de sortie
        ttk.Label(main_frame, text="Dossier de sortie:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_entry = ttk.Entry(main_frame, textvariable=self.output_folder, width=50)
        output_entry.grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Parcourir...", command=self.select_output_folder).grid(row=1, column=2, padx=5)
        
        # Fichier en cours
        ttk.Label(main_frame, text="Fichier en cours:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.current_file).grid(row=2, column=1, columnspan=2, sticky=tk.W)
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, pady=10)
        
        # Compteur fichiers
        self.file_counter = ttk.Label(main_frame, text="0/0 fichiers traités")
        self.file_counter.grid(row=4, column=0, columnspan=3, sticky=tk.W)
        
        # Widget de log
        ttk.Label(main_frame, text="Journal d'activité:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.log_widget = scrolledtext.ScrolledText(main_frame, height=10, state='disabled')
        self.log_widget.grid(row=6, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        self.convert_btn = ttk.Button(btn_frame, text="Convertir", command=self.start_conversion)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Arrêter", command=self.stop_conversion, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Prêt")
        self.status_label.grid(row=8, column=0, columnspan=3, sticky=tk.W+tk.E)
        
        # Configuration du redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier source")
        if folder:
            self.input_folder.set(folder)
            self.output_folder.set(os.path.join(folder, "mp4_comp"))
    
    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if folder:
            self.output_folder.set(folder)
    
    def get_ffmpeg_path(self):
        """Retourne le chemin de ffmpeg selon l'environnement"""
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')
    
    def log_message(self, message):
        """Ajoute un message au widget de log"""
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.configure(state='disabled')
        self.log_widget.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, value=None, current_file=""):
        """Met à jour l'interface"""
        if value is not None:
            self.progress.set(value)
        
        if current_file:
            self.current_file.set(os.path.basename(current_file))
        
        if self.total_files > 0:
            self.file_counter.config(text=f"{self.processed_files}/{self.total_files} fichiers traités")
        
        self.root.update_idletasks()
    
    def get_video_files(self, folder):
        """Retourne la liste des fichiers MP4 dans le dossier (sans sous-dossiers) sans doublons"""
        video_files = set()  # Utilisation d'un set pour éviter les doublons
        for f in glob.glob(os.path.join(folder, '*')):
            if os.path.isfile(f) and os.path.dirname(f) == folder:
                filename_lower = f.lower()
                if filename_lower.endswith('.mp4'):
                    video_files.add(f)  # Ajoute le fichier avec sa casse originale
        return sorted(video_files)  # Retourne une liste triée
    
    def convert_video(self, input_file, output_file):
        """Convertit un fichier vidéo avec suivi de progression réel"""
        ffmpeg_path = self.get_ffmpeg_path()
        
        try:
            # Configuration pour masquer la console
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Construction de la commande FFmpeg
            cmd = [
                ffmpeg_path,
                '-y',
                '-i', input_file,
                '-c:v', 'libx264',
                '-crf', '23',
                '-preset', 'medium',
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-strict', 'experimental',
                '-hide_banner',
                '-loglevel', 'error',
                output_file
            ]

            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                bufsize=1
            )

            # Lecture de la progression en temps réel
            duration = None
            while True:
                if process.poll() is not None:
                    break
                    
                line = process.stderr.readline()
                if not line:
                    continue
                    
                # Détection de la durée totale
                if "Duration:" in line:
                    try:
                        time_str = line.split("Duration:")[1].split(",")[0].strip()
                        h, m, s = time_str.split(':')
                        duration = float(h) * 3600 + float(m) * 60 + float(s)
                    except:
                        pass
                
                # Détection du temps écoulé
                elif "time=" in line:
                    try:
                        time_str = line.split("time=")[1].split(" ")[0]
                        h, m, s = time_str.split(':')
                        current_time = float(h) * 3600 + float(m) * 60 + float(s)
                        if duration:
                            progress_percent = (current_time / duration) * 100
                            self.progress.set(progress_percent)
                            self.root.update_idletasks()
                    except:
                        pass

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, 
                    cmd, 
                    process.stderr.read()
                )

            return os.path.exists(output_file)

        except Exception as e:
            self.log_message(f"Erreur lors de la conversion de {input_file}: {str(e)}")
            return False
    
    def process_folder(self):
        """Traite tous les fichiers vidéo du dossier"""
        input_folder = self.input_folder.get()
        output_folder = self.output_folder.get()
        
        if not input_folder or not output_folder:
            messagebox.showwarning("Attention", "Veuillez sélectionner les dossiers source et destination")
            self.running = False
            return
        
        # Création du dossier de sortie si nécessaire
        os.makedirs(output_folder, exist_ok=True)
        
        # Recherche des fichiers MP4 (uniquement dans le dossier racine)
        video_files = self.get_video_files(input_folder)
        
        if not video_files:
            messagebox.showinfo("Information", "Aucun fichier MP4 trouvé dans le dossier source")
            self.running = False
            return
        
        # Initialisation des compteurs
        self.total_files = len(video_files)
        self.processed_files = 0
        self.progress.set(0)
        self.update_progress()
        self.log_message(f"Début de la conversion de {self.total_files} fichiers")
        
        # Conversion des fichiers
        for i, input_file in enumerate(video_files, 1):
            if not self.running:
                break
            
            self.processed_files = i
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_comp.mp4")
            
            self.current_file.set(filename)
            self.progress.set(0)
            self.update_progress()
            self.log_message(f"Traitement du fichier {i}/{self.total_files}: {filename}")
            
            success = self.convert_video(input_file, output_file)
            
            if success:
                self.log_message(f"✓ Conversion réussie: {filename}")
            elif self.running:
                self.log_message(f"✗ Échec de la conversion: {filename}")
                messagebox.showerror("Erreur", f"Échec de la conversion de {filename}")
            
            # Mise à jour de la progression globale
            global_progress = (i / self.total_files) * 100
            self.progress.set(global_progress)
            self.update_progress()
        
        # Fin du traitement
        if self.running:
            self.status_label.config(text=f"Terminé - {self.processed_files} fichiers traités")
            self.log_message(f"Conversion terminée - {self.processed_files} fichiers traités")
            messagebox.showinfo("Terminé", "Conversion des fichiers terminée!")
        
        self.running = False
        self.toggle_buttons()
    
    def start_conversion(self):
        """Démarre la conversion"""
        if not self.running:
            self.running = True
            self.toggle_buttons()
            Thread(target=self.process_folder, daemon=True).start()
    
    def stop_conversion(self):
        """Arrête la conversion"""
        self.running = False
        self.status_label.config(text="Conversion arrêtée")
        self.log_message("Conversion arrêtée par l'utilisateur")
    
    def toggle_buttons(self):
        """Active/désactive les boutons"""
        state = tk.DISABLED if self.running else tk.NORMAL
        self.convert_btn.config(state=state)
        self.stop_btn.config(state=tk.DISABLED if not self.running else tk.NORMAL)
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchVideoConverterApp(root)
    root.mainloop()