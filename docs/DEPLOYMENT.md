# 🚀 Guide de Déploiement SEDAI

Bienvenue dans le guide d'installation étape par étape du **Système Embarqué de Diagnostic Automobile Intelligent (SEDAI)** sur Raspberry Pi 5. Ce guide est conçu pour être accessible à tout le monde.

---

## 1. 🔌 Pré-requis matériels

Avant de commencer, assurez-vous de disposer du matériel suivant :
- **Raspberry Pi 5** (version 8 Go de RAM vivement recommandée pour faire tourner intelligemment l'IA locale).
- **Carte SD** (capacité de 64 Go minimum, Classe 10 / A2 pour la vitesse d'écriture et de l'OS).
- **Alimentation USB-C** officielle Raspberry Pi (27W / 5.1V 5A). Crucial pour l’inférence du modèle IA sans pertes de performance.
- **Interface OBD-II vers USB** (base ELM327 ou compatible).
- **Microphone et Haut-parleur USB** (ou hub audio combiné USB).

---

## 2. 💿 Installation du système

### Installation de Raspberry Pi OS
1. Téléchargez et installez **Raspberry Pi Imager** sur votre ordinateur (Windows/Mac/Linux).
2. Insérez la carte SD (ou lecteur microSD) dans votre ordinateur.
3. Dans Raspberry Pi Imager :
   - Choisissez le système d'exploitation : `Raspberry Pi OS (64-bit) Bookworm`.
   - Appliquez les réglages OS (la "roue d'engrenage") : configurez votre Wi-Fi pour l'installation, activez **SSH**, et créez un utilisateur nommé `pi`.
   - Sélectionnez votre carte SD et cliquez sur **Écrire**.
4. Insérez la carte microSD flashée dans le Raspberry Pi 5 puis mettez-le sous tension.

### Configuration initiale
Connectez-vous au Raspberry Pi via SSH depuis le terminal (ou PowerShell) de votre ordinateur PC :
```bash
ssh pi@<adresse_ip_du_raspberry>
```
Une fois l'accès établi, mettez à jour votre système Debian :
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

---

## 3. 📦 Installation des dépendances

Le projet utilise un script prêt à l'emploi qui automatise l'installation, gère l'environnement asynchrone (venv) et les packages apt.

1. Transférez le code source du projet SEDAI dans votre dossier `/home/sedai/SEDAI`.
2. Allez à la racine :
```bash
cd /home/sedai/SEDAI
```
3. Rendez le script exécutable et installez le projet :
```bash
chmod +x install.sh
./install.sh
```
>*Note : Patientez durant cette phase. Le script va créer votre l'environnement (`.venv`), compiler les librairies audio (PyAudio) et vérifier Ollama.*

---

## 4. ⚙️ Configuration du projet

### Structure des dossiers
Vérifiez que la racine se présente comme tel :
```text
/home/sedai/SEDAI/
├── src/                # Cœur logique
│   ├── config.py       # Configuration constante (ports, PIDs, seuils)
│   ├── main.py         # Point d'entrée
│   └── ...
├── install.sh          # Script Bash
├── requirements.txt    # Libraires pip
└── .venv/              # Environnement Python (Généré automatiquement)
```

Placez impérativement vos modèles audio dans les répertoires attitrés créés par le `install.sh` :
- Extrayez le **Vosk Model** (ASR) dans : `/home/sedai/models/vosk/vosk-model-fr-0.22`
- Placez vos fichiers **Piper** (.onnx et .json) dans : `/home/sedai/models/piper/`

### Fichier config.py
Aucune variable d'environnement complexe n'est exigée en niveau système. Pour paramétrer un port OBD spécifique ou modifier l'URL Websocket, il suffit d'éditer `src/config.py`.

---

## 5. 🟢 Lancement du système (Manuel)

Commencez toujours par tester de lancer le système manuellement afin de traquer l'affichage dans le prompt SSH :

```bash
cd /home/sedai/SEDAI

# Activation du venv vital
source .venv/bin/activate

# Lancement classique
python3 src/main.py
```
Tôt un flot d'informations indiquera les démarrages. Vous devriez pouvoir identifier `[SEDAI] Système Opérationnel` à la fin.

---

## 6. 🔄 Démarrage automatique (Daemon Tâche de Fond)

Pour un produit embarqué authentique, il faut que SEDAI s'allume au moment même du démarrage logiciel du Raspberry, sans ordinateur !

1. Créez un "fichier de service" Linux systemd :
```bash
sudo nano /etc/systemd/system/sedai.service
```

2. Y coller la logique suivante (Adapter `/home/sedai` au besoin) :
```ini
[Unit]
Description=SEDAI - Serveur de Diagnostic Automobile Intelligent
After=network.target sound.target

[Service]
ExecStart=/home/sedai/SEDAI/.venv/bin/python /home/sedai/SEDAI/src/main.py
WorkingDirectory=/home/sedai/SEDAI
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=sedai
User=pi
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
*Appuyez sur `CTRL+X`, `Y` puis `O` (ou Entrée) pour sauvegarder sous nano.*

3. Activez le nouveau service en l'injectant dans la séquence de boot :
```bash
sudo systemctl daemon-reload
sudo systemctl enable sedai.service
sudo systemctl start sedai.service
```

---

## 7. 🧪 Tests et Validation

Une fois SEDAI auto-hébergé, validez tous les ponts matériels :
- **OBD-II** : Mettez le contact de la voiture et allumez-la. Un log de `[OBD] Connecté` doit survenir.
- **WebSocket** : Démarrez l'application Flutter et entrez l'IP et le port 8765 du RPi (si via point d'accès interne). Observez les KPI (RPM, T°, Vitesse) frétiller à l'écran. 
- **Synthèse Vocale (Piper)** : Une phrase d'accueil est diffusée dès que le démon d'orchestration a démarré avec succès.
- **LLM/Gemma3** : Utilisez le micro Flutter ou bouton pour envoyer l'ordre. L'IA compilera le prompt depuis le thread local silencieux et prononcera l'explication après environ 2/3 secondes.

---

## 8. 🛠️ Dépannage (Troubleshooting)

En cas de comportements muets ou illogiques, sortez une inspection de fond :

- **Check rapide de santé d'arrière-plan** :
```bash
sudo systemctl status sedai.service
```

- **Observateur des journaux et des erreurs Pythons (Directes)** :
```bash
journalctl -u sedai.service -f
```

- **Je veux stopper le script temporairement** :
```bash
sudo systemctl stop sedai.service
```

### ❌ Erreurs Courantes
- **Le port OBD n'accroche pas** : Souvent attribué à `/dev/ttyUSB1` au lieu de `0` suivant l'appareil branché en premier. Modifiez `config.py` ou tapez `dmesg | grep tty` pour identifier le bon identifiant Linux du contrôleur ELM327 USB.
- **Module Vosk/Piper plante ("Segmentation Fault")** : La RAM explose. Assurez-vous d'avoir pris le modèle "gemma3:4b", et pas supérieur, il doit tenir dans le cadre de 8 Go incluant Pi OS et le traitement des autres threads.
- **La voix de Piper-TTS refuse de démarrer (Silence radio / Erreur Python)** : Assurez-vous que la librairie système C++ (`espeak-ng`) a bien été installée. Si vous n'avez pas utilisé le script automatique d'installation de la v2.0, forcez l'installation avec `sudo apt-get install espeak-ng`.
- **SEDAI ne remonte aucune donnée Mode 06 (Ratés d'allumage cylindre par cylindre)** : L'extraction des ratés d'allumage (Misfires) utilise les adresses Hexadécimales modernes CAN (MID $A2 à $A7). Sur des véhicules d'ancienne norme (KWP2000 ou datant d'avant 2004), la voiture ne retournera rien. SEDAI ignorera cette requête sans que cela ne plante le système !
- **Ollama Error API Connection** : Ollama est engorgé. N'hésitez pas à relancer Ollama de force `sudo systemctl restart ollama`.
