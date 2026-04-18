**PROMPT DE DÉVELOPPEMENT --- SCRIPT PYTHON RASPBERRY PI 5**

**Système embarqué de diagnostic automobile intelligent --- SEDAI**

*Projet de fin d\'études --- INSTI Lokossa --- BARA Ezechiel & BOGNINOU
Armel*

# **1. CONTEXTE ET OBJECTIF DU PROJET**

De nos jours, le véhicule automobile est devenu un système mécatronique
complexe intégrant de nombreux calculateurs électroniques dont les
données et signaux de dysfonctionnement sont souvent mal interprétés par
les conducteurs non spécialisés. Au Bénin, cette situation entraîne des
interventions tardives, des coûts de réparation élevés et une diminution
de la durée de vie des véhicules.

Ce projet porte sur la conception et la réalisation d\'un système
embarqué de diagnostic automobile intelligent, capable d\'analyser les
données du véhicule et de fournir des diagnostics clairs en langage
naturel, sans connexion Internet. Le système repose sur un Raspberry Pi
5 (8 Go RAM) relié au port OBD-II via une interface ELM327 USB.
L\'analyse est assurée par le modèle Gemma3 4B exécuté localement via
Ollama. Les résultats sont restitués vocalement via Piper TTS et
visuellement via une application mobile Flutter.

# **2. FICHIER DE CONSTANTES --- config.py**

Toutes les constantes du système sont regroupées dans un fichier
config.py unique. Ce fichier est le seul à modifier pour reconfigurer le
système sans toucher au code principal. Chaque module importe ses
constantes depuis ce fichier.

> \# ============================================================
>
> \# config.py --- Constantes globales du système SEDAI
>
> \# Modifier ce fichier pour reconfigurer le système
>
> \# ============================================================
>
> \# \-\-- OLLAMA \-\--
>
> OLLAMA_URL = \"http://localhost:11434\"
>
> OLLAMA_MODEL = \"gemma3:4b\"
>
> OLLAMA_TIMEOUT = 120 \# secondes
>
> \# \-\-- OBD-II \-\--
>
> OBD_PORT = \"/dev/ttyUSB0\"
>
> OBD_BAUDRATE = 38400
>
> OBD_TIMEOUT = 10 \# secondes
>
> \# \-\-- WEBSOCKET \-\--
>
> WS_HOST = \"0.0.0.0\"
>
> WS_PORT = 8765
>
> WS_SEND_INTERVAL = 1 \# secondes entre chaque envoi de données
>
> \# \-\-- SURVEILLANCE \-\--
>
> MONITOR_INTERVAL = 30 \# secondes entre chaque vérification
>
> \# \-\-- SEUILS D\'ANOMALIE \-\--
>
> SEUIL_TEMP_MAX = 100 \# °C --- température moteur critique
>
> SEUIL_RPM_MAX = 6500 \# RPM --- régime moteur critique
>
> SEUIL_RPM_DUREE = 10 \# secondes --- durée avant alerte RPM
>
> SEUIL_CHARGE_MAX = 95 \# % --- charge moteur critique
>
> SEUIL_CHARGE_DUREE= 20 \# secondes --- durée avant alerte charge
>
> SEUIL_BATT_MIN = 11.5 \# V --- tension batterie minimale
>
> SEUIL_BATT_MAX = 15.5 \# V --- tension batterie maximale
>
> SEUIL_CARBURANT = 10 \# % --- niveau carburant critique
>
> \# \-\-- MÉMOIRE CONVERSATIONNELLE \-\--
>
> MEMORY_MAX_EXCHANGES = 4 \# Nombre max d\'échanges mémorisés
>
> \# \-\-- PIPER TTS \-\--
>
> PIPER_MODEL = \"fr_FR-upmc-medium.onnx\"
>
> PIPER_MODEL_JSON = \"fr_FR-upmc-medium.onnx.json\"
>
> PIPER_MODEL_PATH = \"/home/sedai/models/piper/\"
>
> \# \-\-- VOSK ASR \-\--
>
> VOSK_MODEL_PATH = \"/home/sedai/models/vosk/vosk-model-fr-0.22\"
>
> VOSK_SAMPLE_RATE = 16000
>
> \# \-\-- DÉMARRAGE AUTONOME \-\--
>
> OLLAMA_STARTUP_WAIT = 10 \# secondes d\'attente après démarrage Ollama
>
> OLLAMA_MAX_RETRIES = 5 \# tentatives de connexion à Ollama

# **3. DÉMARRAGE AUTONOME DU SYSTÈME**

Le script principal doit être totalement autonome. Au démarrage, il
vérifie si Ollama est en cours d\'exécution, le démarre si nécessaire,
attend qu\'il soit prêt, puis démarre tous les modules. Aucune
intervention humaine n\'est requise.

## **3.1 Séquence de démarrage autonome**

> \# startup.py --- Gestionnaire de démarrage autonome
>
> import subprocess, time, requests
>
> from config import \*
>
> def is_ollama_running():
>
> \"\"\"Vérifie si Ollama répond sur son port.\"\"\"
>
> try:
>
> r = requests.get(f\"{OLLAMA_URL}/api/tags\", timeout=3)
>
> return r.status_code == 200
>
> except:
>
> return False
>
> def start_ollama():
>
> \"\"\"Démarre le serveur Ollama en arrière-plan.\"\"\"
>
> subprocess.Popen(
>
> \[\"ollama\", \"serve\"\],
>
> stdout=subprocess.DEVNULL,
>
> stderr=subprocess.DEVNULL
>
> )
>
> print(\"\[SEDAI\] Démarrage d\'Ollama\...\")
>
> time.sleep(OLLAMA_STARTUP_WAIT)
>
> def ensure_ollama_ready():
>
> \"\"\"S\'assure qu\'Ollama est prêt avant de continuer.\"\"\"
>
> for attempt in range(OLLAMA_MAX_RETRIES):
>
> if is_ollama_running():
>
> print(\"\[SEDAI\] Ollama est prêt.\")
>
> return True
>
> print(f\"\[SEDAI\] Tentative {attempt+1}/{OLLAMA_MAX_RETRIES}\...\")
>
> start_ollama()
>
> print(\"\[SEDAI\] ERREUR : Ollama inaccessible après plusieurs
> tentatives.\")
>
> return False
>
> def ensure_model_available():
>
> \"\"\"Vérifie que le modèle Gemma3 est disponible dans Ollama.\"\"\"
>
> try:
>
> r = requests.get(f\"{OLLAMA_URL}/api/tags\")
>
> models = \[m\[\"name\"\] for m in r.json().get(\"models\", \[\])\]
>
> if OLLAMA_MODEL not in models:
>
> print(f\"\[SEDAI\] Téléchargement du modèle {OLLAMA_MODEL}\...\")
>
> subprocess.run(\[\"ollama\", \"pull\", OLLAMA_MODEL\])
>
> return True
>
> except Exception as e:
>
> print(f\"\[SEDAI\] Erreur modèle : {e}\")
>
> return False

## **3.2 Démarrage automatique au démarrage du Raspberry Pi**

Pour que le script démarre automatiquement quand le Raspberry Pi
s\'allume, ajouter la ligne suivante dans /etc/rc.local ou créer un
service systemd :

> \# Option 1 --- /etc/rc.local (simple)
>
> python3 /home/sedai/SEDAI/src/main.py &
>
> \# Option 2 --- Service systemd (recommandé)
>
> \# Créer le fichier : /etc/systemd/system/sedai.service
>
> \[Unit\]
>
> Description=SEDAI Diagnostic Automobile
>
> After=network.target
>
> \[Service\]
>
> ExecStart=/home/sedai/SEDAI/.venv/bin/python /home/sedai/SEDAI/src/main.py
>
> WorkingDirectory=/home/sedai/SEDAI
>
> Restart=always
>
> User=pi
>
> \[Install\]
>
> WantedBy=multi-user.target

# **4. SYSTEM PROMPT --- COMPÉTENCES DE L\'IA (GEMMA3)**

Ce system prompt est envoyé à Gemma3 à chaque requête. Il définit
strictement le comportement et les compétences de l\'IA. Il est stocké
dans config.py comme constante.

> SYSTEM_PROMPT = \"\"\"
>
> Tu es SEDAI, un assistant expert embarqué en diagnostic automobile.
>
> Tu analyses les données OBD-II de véhicules et fournis des diagnostics
>
> clairs et accessibles à tout conducteur non spécialisé.
>
> TES COMPÉTENCES :
>
> \- Tu maîtrises les systèmes mécaniques et électroniques des véhicules
>
> Toyota, Honda, Suzuki, Hyundai, Lexus et autres marques courantes.
>
> \- Tu interprètes les paramètres moteur en temps réel.
>
> \- Tu identifies les systèmes du véhicule probablement affectés.
>
> \- Tu traduis les informations techniques en langage simple et
> naturel.
>
> \- Tu tiens compte des diagnostics précédents grâce à ta mémoire.
>
> TES RÈGLES STRICTES :
>
> 1\. Tu réponds UNIQUEMENT en français.
>
> 2\. Tu n\'utilises JAMAIS les codes techniques P0xxx, P1xxx dans ta
> réponse.
>
> 3\. Tu parles des SYSTÈMES probablement affectés, pas des composants
>
> avec certitude (ex : système d\'alimentation, système d\'allumage).
>
> 4\. Tu utilises des formulations probabilistes :
>
> \"il est probable que\", \"cela pourrait indiquer\", \"il semble
> que\".
>
> 5\. Ton rapport est UN SEUL PARAGRAPHE de 5 à 7 lignes maximum.
>
> Pas de liste, pas de titres, pas de numérotation.
>
> 6\. Tu termines TOUJOURS par recommander une vérification chez un
>
> technicien automobile qualifié.
>
> 7\. Tu n\'exprimes jamais de certitude absolue sur une panne.
>
> 8\. Si les données semblent normales, tu le dis clairement.
>
> 9\. Ton langage est simple, naturel et rassurant.
>
> \"\"\"

# **5. MODULE 1 --- ACQUISITION DES DONNÉES OBD-II**

## **5.1 Données affichées sur le tableau de bord Flutter**

> • Vitesse du véhicule (km/h) --- PID 0x0D
>
> • Régime moteur --- RPM --- PID 0x0C
>
> • Température du liquide de refroidissement (°C) --- PID 0x05
>
> • Débit d\'air MAF (g/s) --- PID 0x10
>
> • Pression absolue collecteur MAP (kPa) --- PID 0x0B
>
> • Tension de la batterie (V) --- PID 0x42
>
> ◇ Pression d\'huile moteur (kPa) --- PID 0x5C *\[si supporté par le
> véhicule\]*
>
> • Sonde lambda --- taux d\'oxygène (V) --- PID 0x14 à 0x1B

## **5.2 Données supplémentaires pour l\'analyse IA**

> • Charge moteur calculée (%) --- PID 0x04
>
> • Position papillon des gaz (%) --- PID 0x11
>
> • Avance à l\'allumage (degrés) --- PID 0x0E
>
> • Température d\'air d\'admission (°C) --- PID 0x0F
>
> ◇ Pression carburant (kPa) --- PID 0x0A *\[si supporté par le
> véhicule\]*
>
> ◇ Niveau de carburant (%) --- PID 0x2F *\[si supporté par le
> véhicule\]*
>
> ◇ Pression des pneus TPMS (kPa) --- PID étendu *\[si supporté par le
> véhicule\]*
>
> *Les PID non supportés par le véhicule sont ignorés silencieusement.
> Le code vérifie si la valeur retournée est None avant de l\'inclure
> dans le prompt.*

## **5.3 Informations véhicule depuis Flutter**

> • Marque du véhicule (ex : Toyota, Honda, Suzuki, Hyundai, Lexus)
>
> • Modèle du véhicule (ex : Corolla, CR-V, Swift, Tucson)
>
> • Modèle du moteur (ex : 1ZZ-FE, K20A, OM651)
>
> • Type de moteur (ex : 1.8L essence, 2.0L diesel turbo)

# **6. MODULE 2 --- SURVEILLANCE SILENCIEUSE EN CONDUITE**

Tourne en arrière-plan toutes les 30 secondes (MONITOR_INTERVAL).
Silence total si tout va bien. Déclenche le diagnostic complet si une
anomalie est détectée.

> • Température moteur \> SEUIL_TEMP_MAX (100°C)
>
> • Régime \> SEUIL_RPM_MAX (6500 RPM) pendant \> SEUIL_RPM_DUREE (10
> sec)
>
> • Tension \< SEUIL_BATT_MIN (11.5V) ou \> SEUIL_BATT_MAX (15.5V)
>
> • Charge moteur \> SEUIL_CHARGE_MAX (95%) pendant \>
> SEUIL_CHARGE_DUREE (20 sec)
>
> ◇ Niveau carburant \< SEUIL_CARBURANT (10%) *\[si supporté par le
> véhicule\]*
>
> ◇ Pression pneu hors plage normale *\[si supporté par le véhicule\]*
>
> • Apparition d\'un nouveau DTC non présent au démarrage
>
> *Le module de surveillance ne génère jamais de son ni de message
> vocal. Seul le rapport final de Gemma3 est lu à voix haute.*

# **7. MODULE 3 --- DIAGNOSTIC COMPLET PAR GEMMA3**

## **7.1 Trois déclencheurs**

> • Démarrage du système (contact mis, connexion OBD-II établie) ---
> automatique
>
> • Anomalie détectée par le module de surveillance --- automatique
>
> • Demande conducteur via Flutter ou commande vocale --- à la demande

## **7.2 Structure du prompt envoyé à Gemma3**

> def build_prompt(vehicle_info, obd_data, dtcs, context, history=\[\]):
>
> user_message = f\"\"\"
>
> VÉHICULE : {vehicle_info\[\"marque\"\]} {vehicle_info\[\"modele\"\]}
>
> MOTEUR : {vehicle_info\[\"modele_moteur\"\]} ---
> {vehicle_info\[\"type_moteur\"\]}
>
> DONNÉES EN TEMPS RÉEL :
>
> Vitesse : {obd_data.get(\"vitesse\", \"N/A\")} km/h
>
> Régime : {obd_data.get(\"regime\", \"N/A\")} RPM
>
> Temp. moteur : {obd_data.get(\"temp_moteur\", \"N/A\")} °C
>
> Charge moteur : {obd_data.get(\"charge\", \"N/A\")} %
>
> MAF : {obd_data.get(\"maf\", \"N/A\")} g/s
>
> MAP : {obd_data.get(\"map\", \"N/A\")} kPa
>
> Papillon : {obd_data.get(\"papillon\", \"N/A\")} %
>
> Avance allumage: {obd_data.get(\"avance\", \"N/A\")} degrés
>
> Temp. admission: {obd_data.get(\"temp_admission\", \"N/A\")} °C
>
> Sonde lambda : {obd_data.get(\"lambda\", \"N/A\")} V
>
> Tension batt. : {obd_data.get(\"tension\", \"N/A\")} V
>
> Pression huile : {obd_data.get(\"pression_huile\", \"N/A\")} kPa
>
> Carburant : {obd_data.get(\"carburant\", \"N/A\")} %
>
> Pression pneus : {obd_data.get(\"pression_pneus\", \"N/A\")} kPa
>
> ANOMALIES DTC : {\", \".join(dtcs) if dtcs else \"Aucun\"}
>
> CONTEXTE : {context}
>
> Génère un rapport en UN SEUL PARAGRAPHE de 5 à 7 lignes.
>
> \"\"\"
>
> messages = \[{\"role\": \"system\", \"content\": SYSTEM_PROMPT}\]
>
> messages += history\[-MEMORY_MAX_EXCHANGES\*2:\]
>
> messages.append({\"role\": \"user\", \"content\": user_message})
>
> return messages

## **7.3 Exemple de rapport attendu**

> *\"L\'état général du véhicule au démarrage semble globalement
> acceptable. La température du moteur est dans la norme et le régime de
> ralenti est stable. Cependant, certains paramètres du système
> d\'alimentation en carburant pourraient mériter d'attention, car les
> valeurs mesurées s\'écartent légèrement de la plage habituelle pour ce
> type de moteur. Il est également possible que le système de
> dépollution soit légèrement sollicité. Ces informations restent
> indicatives et il est conseillé de faire vérifier votre véhicule par
> un technicien automobile qualifié pour un diagnostic complet.\"*

# **8. BIBLIOTHÈQUES PYTHON ET MODÈLES À INSTALLER**

> \# Bibliothèques Python
>
> pip install python-obd vosk websockets requests pyaudio sounddevice
>
> \# Piper TTS
>
> pip install piper-tts
>
> \# Modèle vocal : fr_FR-upmc-medium
>
> \# Télécharger depuis : https://github.com/rhasspy/piper/releases
>
> \# Fichiers requis : fr_FR-upmc-medium.onnx +
> fr_FR-upmc-medium.onnx.json
>
> \# Vosk
>
> pip install vosk
>
> \# Modèle ASR : vosk-model-fr-0.22
>
> \# Télécharger depuis : https://alphacephei.com/vosk/models
>
> \# Décompresser dans : /home/sedai/models/vosk/
>
> \# Ollama --- installation automatique
>
> curl -fsSL https://ollama.com/install.sh \| sh
>
> \# Le script Python démarre Ollama automatiquement si nécessaire
>
> \# et télécharge Gemma3 si le modèle n\'est pas disponible.

# **9. MODULE 7 --- COMMUNICATION WEBSOCKET**

## **Données envoyées en continu à Flutter (chaque seconde)**

> • vitesse, regime, temp_moteur, maf, map, tension
>
> ◇ pression_huile, carburant, pression_pneus *\[si supporté par le
> véhicule\]*
>
> • statut_obd : \"connecté\" / \"déconnecté\"
>
> • rapport (JSON) : rapport lors d\'un diagnostic

## **Commandes reçues depuis Flutter**

> • \"voice_activate\" → activation microphone Vosk
>
> • \"voice_deactivate\" → désactivation microphone
>
> • \"diagnose\" → diagnostic à la demande
>
> • \"get_dtcs\" → lecture des codes défauts
>
> • \"clear_dtcs\" → effacement des codes défauts
>
> • \"vehicle_info\" + JSON → réception infos véhicule

# **10. CONTRAINTES TECHNIQUES**

> • Système 100% hors ligne --- aucune connexion Internet requise
>
> • Ollama démarré automatiquement par le script si nécessaire
>
> • Modèle IA : gemma3:4b --- téléchargé automatiquement si absent
>
> • Modèle vocal Piper : fr_FR-upmc-medium.onnx
>
> • Modèle ASR Vosk : vosk-model-fr-0.22
>
> • Port WebSocket : WS_PORT = 8765
>
> • Port API Ollama : OLLAMA_URL = localhost:11434
>
> • Port OBD-II : OBD_PORT = /dev/ttyUSB0
>
> • Toutes les constantes modifiables dans config.py uniquement
>
> • PID non supportés ignorés silencieusement (valeur None)

**Note :**

*Ce document est le prompt de contexte complet pour le développement du
script Python du Raspberry Pi 5 --- projet SEDAI. Toutes les constantes
sont centralisées dans config.py. Le système est conçu pour être
totalement autonome : il démarre Ollama, charge le modèle Gemma3 et
initialise tous les modules sans intervention humaine.*
