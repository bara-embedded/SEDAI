"""
tts_module.py — Synthèse vocale Text-To-Speech (Piper)
Gère une file d'attente de messages à lire à voix haute via le haut-parleur USB.
Utilise Piper TTS pour la génération vocale locale et aplay (ALSA) pour la lecture.
Fonctionne dans un thread dédié (daemon).
"""

import threading
import queue
import subprocess
import os
import logging
import time

from config import *

# Configuration du logger pour le module TTS
logger = logging.getLogger("TTS")

class TTSModule(threading.Thread):
    """
    Module générant et lisant la voix à partir de texte en utilisant Piper TTS.
    Gère une file d'attente pour ne pas bloquer les autres modules.
    """
    
    def __init__(self, event_stop: threading.Event):
        """
        Initialise le module TTS.
        
        Args:
            event_stop (threading.Event): Événement pour stopper proprement le thread.
        """
        super().__init__(daemon=True)
        self.message_queue: queue.Queue[str] = queue.Queue()
        self.event_stop = event_stop

        # Initialisation automatique du volume de la carte USB en lisant la dernière sauvegarde
        try:
            logger.info("[TTS] Restauration du volume matériel (Carte 2)...")
            
            # Lecture du volume sauvegardé
            saved_volume = 75 # Défaut si pas de fichier
            volume_file = os.path.join(os.path.dirname(__file__), "volume_state.txt")
            if os.path.exists(volume_file):
                with open(volume_file, "r") as f:
                    try:
                        saved_volume = int(f.read().strip())
                    except ValueError:
                        pass
            
            # Récupération de la liste des contrôles (PCM, Speaker, etc.)
            result = subprocess.check_output(["amixer", "-c", "2", "scontrols"], stderr=subprocess.STDOUT)
            controls = result.decode().splitlines()
            
            for line in controls:
                if "'" in line:
                    control_name = line.split("'")[1]
                    # On applique le volume restauré
                    subprocess.run(["amixer", "-c", "2", "sset", control_name, f"{saved_volume}%", "unmute"], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.warning(f"[TTS] Échec de la restauration du volume : {e}")

    def speak(self, text: str) -> None:
        """
        Ajoute un message à la file d'attente vocale.
        
        Args:
            text (str): Le texte à lire à voix haute.
        """
        if text and str(text).strip():
            self.message_queue.put(str(text).strip())

    def clear_queue(self) -> None:
        """
        Vide la file d'attente vocale (utile pour interrompre les lectures en attente
        et donner priorité à une alerte d'urgence).
        """
        with self.message_queue.mutex:
            self.message_queue.queue.clear()

    def play_text(self, text: str) -> None:
        """
        Génère l'audio avec Piper et le lit immédiatement via ALSA (aplay).
        Inclut un mécanisme de retry automatique pour stabiliser le matériel USB.
        """
        logger.info(f"[TTS] Synthèse et lecture : {text}")
        model_file = os.path.join(PIPER_MODEL_PATH, PIPER_MODEL)
        
        if not os.path.exists(model_file):
            logger.error(f"[TTS] ERREUR : Le modèle vocal Piper est introuvable à {model_file}")
            return

        for attempt in range(2):
            try:
                wav_path = "/tmp/sedai_tts.wav"
                
                # ÉTAPE 1 : Génération du fichier WAV avec Piper (fini les problèmes de pipe direct)
                piper_cmd = ["piper", "--model", model_file, "--output_file", wav_path]
                try:
                    subprocess.run(piper_cmd, input=f"{text}\n".encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                except FileNotFoundError:
                    piper_cmd[0] = "piper-tts"
                    subprocess.run(piper_cmd, input=f"{text}\n".encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                
                # ÉTAPE 2 : Lecture propre du fichier WAV par l'ALSA
                aplay_cmd = ["aplay", "-D", "plughw:CARD=UACDemoV10,DEV=0", wav_path]
                p_aplay = subprocess.Popen(aplay_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                
                stderr_aplay = b""
                try:
                    _, stderr_aplay = p_aplay.communicate(timeout=120)
                except subprocess.TimeoutExpired:
                    logger.warning("[TTS] Timeout aplay, kill du processus...")
                    p_aplay.kill()
                    _, stderr_aplay = p_aplay.communicate()

                err_aplay = stderr_aplay.decode().strip() if stderr_aplay else ""
                
                # Si le périphérique est occupé ou n'est pas prêt, on va réessayer de le lire
                if ("No such device" in err_aplay or "busy" in err_aplay.lower()) and attempt == 0:
                    logger.warning(f"[TTS] Matériel occupé ou non prêt ({err_aplay}). Retry dans 3s...")
                    time.sleep(3)
                    continue
                
                if p_aplay.returncode != 0 and err_aplay:
                    logger.error(f"[TTS] Erreur aplay (code {p_aplay.returncode}) : {err_aplay}")
                
                break # Succès
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"[TTS] Erreur de génération Piper : {e.stderr.decode().strip()}")
                break
            except Exception as e:
                logger.error(f"[TTS] Erreur critique dans la chaîne audio : {e}")
                break
                
        # Nettoyage
        try:
            if os.path.exists("/tmp/sedai_tts.wav"):
                os.remove("/tmp/sedai_tts.wav")
        except:
            pass

    def run(self) -> None:
        """Boucle du thread traitant la file d'attente de messages."""
        logger.info("[TTS] Démarrage du thread de synthèse vocale.")
        
        while not self.event_stop.is_set():
            try:
                # Attente bloquante mais avec timeout pour pouvoir vérifier event_stop
                text = self.message_queue.get(timeout=0.5)
                self.play_text(text)
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TTS] Erreur inattendue dans la boucle TTS : {e}")
                
        logger.info("[TTS] Arrêt du thread TTS.")
