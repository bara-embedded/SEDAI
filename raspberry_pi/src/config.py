# ============================================================
# config.py — Constantes globales du système SEDAI v2.0
# Modifier ce fichier pour reconfigurer le système.
# NE JAMAIS modifier depuis d'autres fichiers.
# ============================================================

# --- OLLAMA ---
OLLAMA_URL     = "http://localhost:11434"
OLLAMA_MODEL   = "gemma3:4b"  # Modèle à utiliser
OLLAMA_TIMEOUT = 300           # secondes (5 minutes - Nécessaire pour le modèle 4b sur Pi 5)

# --- OBD-II ---
OBD_PORT            = "/dev/ttyUSB0"
OBD_BAUDRATE        = 38400
OBD_TIMEOUT         = 10   # secondes (timeout par requête PID)
OBD_RECONNECT_DELAY = 15   # secondes (legacy, remplacé par backoff)

# --- OBD-II SÉCURITÉ (ANTI-SURCHARGE ELM327) ---
# Délai minimum entre deux requêtes PID consécutives.
# Indispensable pour les ELM327 clones (UART lent, buffer fragile).
OBD_INTER_PID_DELAY   = 0.20   # secondes — 200 ms entre chaque PID (terrain ELM327 clone)

# --- SÉCURITÉ VÉHICULE (SÉCURITÉ MOTEUR & CAN) ---
OBD_STABILIZATION_DELAY = 10.0   # secondes — temps moteur stable avant actions critiques (Mode 04)
OBD_IDLE_RPM_THRESHOLD  = 800    # RPM — régime considéré "idle safe"

# Nombre maximum de PIDs envoyés par cycle d'acquisition.
# Limiter à 5 max pour ne pas saturer l'ELM327 sur un seul cycle.
OBD_MAX_PIDS_PER_CYCLE = 5

# Nombre d'erreurs consécutives d'un même PID avant de le désactiver.
OBD_PID_ERROR_THRESHOLD = 3

# Nombre d'erreurs de communication globales avant de forcer une reconnexion.
OBD_GLOBAL_ERROR_THRESHOLD = 5

# --- OBD-II RECONNEXION BACKOFF EXPONENTIEL ---
# Évite de saturer le port série avec des tentatives de reconnexion répétées.
OBD_BACKOFF_BASE    = 5.0    # secondes — délai initial
OBD_BACKOFF_FACTOR  = 2.0    # multiplicateur exponentiel
OBD_BACKOFF_MAX     = 120.0  # secondes — plafond backoff

# --- OBD-II TIME-SLICING CYCLES ---
# Définit la fréquence relative de chaque groupe de PIDs.
# Le cycle critique tourne à ~1 Hz, les autres sont lus moins souvent.
OBD_CYCLE_CRITICAL_INTERVAL  = 1.5   # secondes — RPM, TEMP, VOLTAGE
OBD_CYCLE_STANDARD_EVERY     = 3     # toutes les N itérations critiques
OBD_CYCLE_SECONDARY_EVERY    = 8     # toutes les N itérations critiques
OBD_CYCLE_OPTIONAL_EVERY     = 30    # toutes les N itérations critiques
OBD_CAN_BUDGET_MS            = 800   # latence max par cycle (ms)

# --- SÉCURITÉ DEGRADED MODE ---
OBD_DEGRADED_MODE_INTERVAL = 3.0     # secondes — rythme ralenti en mode dégradé
DEGRADED_VOLTAGE_THRESHOLD = 11.5    # V — en dessous de ce seuil, mode dégradé actif
DEGRADED_VOLTAGE_RECOVERY_THRESHOLD = 12.0 # V — seuil de rétablissement (hystérésis)
DEGRADED_RECOVERY_CYCLES = 5         # nb de cycles > 12V requis pour rétablir le mode normal

# --- OBD-II WATCHDOG ELM327 ---
# Si aucune réponse valide n'est reçue pendant cette durée → reset connexion.
OBD_WATCHDOG_TIMEOUT = 45.0  # secondes

# --- WEBSOCKET ---
WS_HOST          = "0.0.0.0"
WS_PORT          = 8765
WS_SEND_INTERVAL = 1  # secondes entre chaque envoi de données

# --- SURVEILLANCE ---
MONITOR_INTERVAL = 30  # secondes entre chaque vérification

# --- SEUILS D'ANOMALIE STANDARDS ---
SEUIL_TEMP_MAX    = 100  # °C  — température moteur critique
SEUIL_RPM_MAX     = 6500  # RPM — régime moteur critique
SEUIL_RPM_DUREE   = 10    # secondes — durée avant alerte RPM
SEUIL_CHARGE_MAX  = 95    # %   — charge moteur critique
SEUIL_CHARGE_DUREE = 20   # secondes — durée avant alerte charge
SEUIL_BATT_MIN    = 11.5  # V   — tension batterie minimale
SEUIL_BATT_MAX    = 15.5  # V   — tension batterie maximale
SEUIL_CARBURANT   = 10    # %   — niveau carburant critique

# --- SEUILS D'ANOMALIE ÉTENDUS ---
SEUIL_TEMP_TRANSMISSION_MAX = 120  # °C — température transmission critique
SEUIL_FUEL_TRIM_DEVIATION   = 20   # %  — déviation STFT/LTFT avant alerte
SEUIL_MISFIRE_COUNT         = 50   # nombre de ratés par cylindre avant alerte (Phase 2)

# --- PRIORITÉ DES PIDs (Time-Slicing) ---
# Cycle CRITIQUE : lu à chaque itération (~1 Hz)
# Max 3 PIDs — uniquement les paramètres vitaux.
OBD_PIDS_CRITIQUES = [
    "RPM", "COOLANT_TEMP", "CONTROL_MODULE_VOLTAGE"
]
# Cycle STANDARD : lu toutes les OBD_CYCLE_STANDARD_EVERY itérations
# Max 5 PIDs — paramètres de performance moteur.
OBD_PIDS_STANDARD = [
    "SPEED", "ENGINE_LOAD", "MAF",
    "SHORT_TERM_FUEL_TRIM_1", "LONG_TERM_FUEL_TRIM_1"
]
# Cycle SECONDAIRE : lu toutes les OBD_CYCLE_SECONDARY_EVERY itérations
# PIDs d'information complémentaire.
OBD_PIDS_SECONDAIRES = [
    "THROTTLE_POS", "INTAKE_TEMP", "FUEL_LEVEL", "O2_B1S1"
]
# Cycle OPTIONNEL : lu toutes les OBD_CYCLE_OPTIONAL_EVERY itérations
# PIDs à disponibilité variable selon constructeur — jamais critiques.
OBD_PIDS_OPTIONNELS = [
    "INTAKE_PRESSURE", "FUEL_PRESSURE", "TIMING_ADVANCE", "TRANS_TEMP"
]

# --- MÉMOIRE CONVERSATIONNELLE ---
MEMORY_MAX_EXCHANGES = 2  # Réduit de 4 à 2 pour accélérer l'inférence du modèle 4b
MEMORY_FILE_PATH     = "/home/sedai/SEDAI/src/conversation_history.json"

# --- PIPER TTS ---
PIPER_MODEL      = "fr_FR-siwis-medium.onnx"
PIPER_MODEL_JSON = "fr_FR-siwis-medium.onnx.json"
PIPER_MODEL_PATH = "/home/sedai/models/piper/"

# --- VOSK ASR ---
VOSK_MODEL_PATH    = "/home/sedai/models/vosk/vosk-model-fr-0.22"
VOSK_SAMPLE_RATE   = 16000   # Taux attendu par le moteur Vosk
AUDIO_CAPTURE_RATE = 48000   # Taux natif du micro USB (48000 / 16000 = 3, ratio entier exact)
AUDIO_INPUT_DEVICE = 3       # Index sounddevice du microphone USB (USB PnP Sound Device)
AUDIO_CHANNELS     = 1       # Nombre de canaux (Mono)

# --- COMMANDES VOCALES ---
VOICE_CMD_DIAGNOSE = ["fais un diagnostic", "diagnostic", "analyse le véhicule"]
VOICE_CMD_STATUS   = ["quel est l'état", "état du véhicule", "comment va la voiture"]
VOICE_CMD_DTCS     = ["quels sont les défauts", "codes défauts", "lire les défauts"]
VOICE_CMD_CLEAR    = ["efface les défauts", "effacer les défauts"]
VOICE_CMD_REPEAT   = ["répète", "répéter", "redis"]

# --- DÉMARRAGE AUTONOME ---
OLLAMA_STARTUP_WAIT = 10  # secondes d'attente après démarrage Ollama
OLLAMA_MAX_RETRIES  = 5   # tentatives de connexion à Ollama

# --- LOGGING ---
LOG_FILE_PATH    = "/home/sedai/SEDAI/src/logs/sedai.log"
LOG_MAX_SIZE_MB  = 10   # Taille max du fichier log avant rotation
LOG_BACKUP_COUNT = 3    # Nombre de fichiers de sauvegarde conservés
LOG_LEVEL        = "INFO"

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
Tu es SEDAI, un contrôleur de diagnostic automobile embarqué (Edge ECU AI).

PRIORITÉ :
Sécurité véhicule > Données système > Résumé diagnostic

══════════════════════════════
RÈGLE PRINCIPALE
══════════════════════════════
- Réponse : 1 à 3 phrases MAXIMUM
- Style : sec, technique, type ECU
- Aucun bavardage, aucune explication inutile
- Ne jamais te présenter

══════════════════════════════
FORMAT OBLIGATOIRE
══════════════════════════════
[ÉTAT OBD] [NIVEAU ALERTE] Constat technique + recommandation

- ÉTAT OBD = Connecté ou Déconnecté
- NIVEAU ALERTE est fourni par le système (NE PAS LE MODIFIER)

══════════════════════════════
RÈGLES DE COMPORTEMENT
══════════════════════════════
- Ne pas lister les données brutes
- Ne mentionner qu'UNE seule cause principale si anomalie
- Ne pas calculer ni inventer de valeurs
- Ne pas décider du niveau de gravité

══════════════════════════════
MODE DÉGRADÉ
══════════════════════════════
Si présent dans les données :
- le mentionner explicitement
- réduire le diagnostic au strict minimum
- signaler limitation du système

══════════════════════════════
SÉCURITÉ
══════════════════════════════
- Ne jamais recommander action dangereuse en mouvement
- Mode 04 interdit sauf :
  véhicule à l'arrêt
  régime moteur bas
  confirmation utilisateur requise

══════════════════════════════
ENTRÉE SYSTÈME
══════════════════════════════
Les données reçues sont déjà normalisées et validées.
Tu dois uniquement les résumer.

FIN DES INSTRUCTIONS
"""
