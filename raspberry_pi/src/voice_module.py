"""
voice_module.py — Reconnaissance vocale (Vosk ASR)
Capture le son du microphone USB et le convertit en texte via Vosk hors ligne.
Fonctionne sur le principe du "Push-to-talk" : l'enregistrement est actif uniquement
lorsque le flag "voice_activate" est déclenché par Flutter.
"""

import logging
import threading
import json
import queue
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    Model, KaldiRecognizer = None, None

from config import *

logger = logging.getLogger("VOICE")

class VoiceModule(threading.Thread):
    """
    Module gérant l'écoute du microphone et sa transcription par le modèle Vosk.
    """
    
    def __init__(self, action_queue: queue.Queue, event_voice_active: threading.Event, event_stop: threading.Event):
        super().__init__(daemon=True)
        self.action_queue = action_queue
        self.event_voice_active = event_voice_active
        self.event_stop = event_stop
        
        self.model = None
        self.recognizer = None
        self._init_vosk()

    def _init_vosk(self) -> None:
        """Charge le modèle de reconnaissance vocale hors ligne Vosk en RAM."""
        if Model is None:
            logger.warning("[VOICE] AVERTISSEMENT : Bibliothèque Vosk non installée.")
            return
            
        try:
            logger.info(f"[VOICE] Chargement du modèle ASR depuis {VOSK_MODEL_PATH}...")
            self.model = Model(VOSK_MODEL_PATH)
            self.recognizer = KaldiRecognizer(self.model, VOSK_SAMPLE_RATE)
            logger.info("[VOICE] Modèle Vosk chargé avec succès.")
        except Exception as e:
            logger.error(f"[VOICE] Erreur lors du chargement du modèle Vosk : {e}")

    def _handle_command(self, text: str) -> None:
        """Analyse le texte transcrit et déclenche l'action correspondante."""
        text = text.lower().strip()

        if any(kw in text for kw in VOICE_CMD_DIAGNOSE + VOICE_CMD_STATUS):
            self.action_queue.put({
                "type": "diagnostic_request",
                "source": "voice",
                "text": "Demande vocale du conducteur."
            })

        elif any(kw in text for kw in VOICE_CMD_DTCS):
            self.action_queue.put({
                "type": "get_dtcs",
                "source": "voice",
                "text": text
            })

        elif any(kw in text for kw in VOICE_CMD_CLEAR):
            self.action_queue.put({
                "type": "clear_dtcs",
                "source": "voice",
                "text": text
            })

        elif any(kw in text for kw in VOICE_CMD_REPEAT):
            self.action_queue.put({
                "type": "repeat_last",
                "source": "voice",
                "text": text
            })

        else:
            # Mode conversation libre — toute autre phrase
            self.action_queue.put({
                "type": "free_chat",
                "source": "voice",
                "text": text
            })

    def run(self) -> None:
        """Boucle du thread qui interroge continuellement le microphone quand activé."""
        logger.info("[VOICE] Démarrage du thread de reconnaissance vocale (Vosk).")
        
        if self.model is None or sd is None:
            logger.error("[VOICE] Module vocal inopérant ou désactivé.")
            while not self.event_stop.is_set():
                self.event_stop.wait(1.0)
            return

        try:
            # Recherche dynamique du périphérique USB pour le microphone
            device_idx = None
            try:
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    # Cherche un périphérique avec "USB" et supportant la capture
                    if "USB" in dev['name'] and dev['max_input_channels'] > 0:
                        device_idx = i
                        break
            except Exception as e:
                logger.warning(f"[VOICE] Erreur query_devices: {e}")
                
            if device_idx is not None:
                logger.info(f"[VOICE] Microphone USB détecté automatiquement : Index {device_idx}")
            else:
                logger.warning("[VOICE] Aucun micro USB identifié spécifiquement, utilisation de l'index par défaut du système.")

            RESAMPLE_RATIO = AUDIO_CAPTURE_RATE // VOSK_SAMPLE_RATE  # = 3
            with sd.RawInputStream(samplerate=AUDIO_CAPTURE_RATE, blocksize=4000 * RESAMPLE_RATIO,
                                   dtype='int16', channels=AUDIO_CHANNELS,
                                   device=device_idx) as stream:
                logger.info("[VOICE] Microphone initialisé et en attente.")
                
                while not self.event_stop.is_set():
                    # Enregistrement déclenché uniquement quand PTT est actif
                    if self.event_voice_active.is_set():
                        data, overflowed = stream.read(4000 * RESAMPLE_RATIO)
                        
                        # Décimation : on prend 1 échantillon sur RESAMPLE_RATIO (48000→16000 Hz)
                        pcm = np.frombuffer(bytes(data), dtype=np.int16)
                        pcm_16k = pcm[::RESAMPLE_RATIO].tobytes()
                        
                        # Transmission des frames rééchantillonnées à Vosk
                        if self.recognizer.AcceptWaveform(pcm_16k):
                            result = json.loads(self.recognizer.Result())
                            text = result.get("text", "")
                            
                            if text:
                                logger.info(f"[VOICE] Phrase reconnue : '{text}'")
                                self._handle_command(text)
                                
                    else:
                        # Moins de charge CPU quand inactif
                        self.event_voice_active.wait(timeout=0.2)
                        
        except Exception as e:
            logger.error(f"[VOICE] Exception matérielle ou logicielle (Micro) : {e}")
            
        logger.info("[VOICE] Arrêt du thread de reconnaissance vocale.")
