"""
startup.py — Gestionnaire de démarrage autonome pour le système SEDAI
Assure le démarrage d'Ollama et le téléchargement du modèle nécessaire.
"""
import subprocess
import time
import requests
from config import *

def is_ollama_running() -> bool:
    """
    Vérifie si Ollama répond sur son port.
    
    Returns:
        bool: True si Ollama est en cours d'exécution, False sinon.
    """
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False

def start_ollama() -> None:
    """Démarre le serveur Ollama en arrière-plan."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[STARTUP] Démarrage d'Ollama...")
        time.sleep(OLLAMA_STARTUP_WAIT)
    except Exception as e:
        print(f"[STARTUP] Erreur inattendue au démarrage d'Ollama: {e}")

def ensure_ollama_ready() -> bool:
    """
    S'assure qu'Ollama est prêt avant de continuer.
    Fait plusieurs tentatives de démarrage configurées dans config.py.
    
    Returns:
        bool: True si Ollama est prêt, False si l'échec persiste.
    """
    for attempt in range(OLLAMA_MAX_RETRIES):
        if is_ollama_running():
            print("[STARTUP] Ollama est prêt.")
            return True
        print(f"[STARTUP] Tentative {attempt+1}/{OLLAMA_MAX_RETRIES}...")
        start_ollama()
    
    print("[STARTUP] ERREUR : Ollama inaccessible après plusieurs tentatives.")
    return False

def ensure_model_available() -> bool:
    """
    Vérifie que le modèle Gemma3 (OLLAMA_MODEL) est disponible dans Ollama.
    Si non, télécharge le modèle automatiquement.
    
    Returns:
        bool: True si le modèle est disponible, False en cas d'erreur.
    """
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        
        if OLLAMA_MODEL not in models:
            print(f"[STARTUP] Le modèle {OLLAMA_MODEL} n'est pas présent.")
            print(f"[STARTUP] Téléchargement du modèle {OLLAMA_MODEL}...")
            subprocess.run(["ollama", "pull", OLLAMA_MODEL], check=True)
            print(f"[STARTUP] Modèle {OLLAMA_MODEL} téléchargé avec succès.")
        else:
            print(f"[STARTUP] Modèle {OLLAMA_MODEL} déjà disponible.")
        return True
    except Exception as e:
        print(f"[STARTUP] Erreur lors de la vérification ou du téléchargement du modèle : {e}")
        return False

def initialize_ai_subsystem() -> bool:
    """
    Point d'entrée pour le démarrage autonome de l'IA.
    
    Returns:
        bool: True si l'IA est prête à l'emploi.
    """
    if not ensure_ollama_ready():
        return False
    
    if not ensure_model_available():
        return False
        
    print("[STARTUP] Sous-système IA initialisé avec succès.")
    return True
