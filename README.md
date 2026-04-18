# SEDAI — Système Embarqué de Diagnostic Automobile Intelligent

![Project Status](https://img.shields.io/badge/status-active-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg?logo=flutter)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-C51A4A.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

SEDAI (Système Embarqué de Diagnostic Automobile Intelligent) est un système innovant combinant matériel embarqué et une application mobile pour fournir un diagnostic automobile avancé, compréhensible et vocal, propulsé par l'Intelligence Artificielle.

## 🎯 Objectif du système

L'objectif de SEDAI est de démocratiser le diagnostic automobile. Au lieu de fournir de simples codes d'erreur (DTC) difficiles à interpréter pour le grand public, SEDAI lit les données via un boîtier OBD-II, les normalise, puis utilise une IA de pointe pour fournir :
- Un diagnostic clair et vulgarisé.
- Des recommandations de réparation.
- Une interaction vocale fluide pendant la conduite pour informer l'utilisateur de l'état de son véhicule en temps réel.

## ✨ Fonctionnalités Principales

- **Lecture OBD-II en temps réel** : Extraction des PID (Régime moteur, Vitesse, Température, etc.) et des codes défauts.
- **Agent IA embarqué** : Compréhension contextuelle du problème via analyse LLM (Gemini).
- **Assistant Vocal** : Synthèse et reconnaissance vocale optimisées pour un usage au volant ("mains libres").
- **Application Mobile Companion** : Interface utilisateur riche construite avec Flutter, offrant la visualisation des données et l'interaction avec le véhicule.

## 🛠 Technologies utilisées

*   **Application Mobile** : Flutter, Dart
*   **Système Embarqué** : Python 3.11+, Raspberry Pi (Zero 2 W / 4 / 5)
*   **Connectivité Véhicule** : OBD-II (ELM327 Bluetooth/USB), python-OBD
*   **Intelligence Artificielle** : API Google Gemini (LLM)
*   **Audio/Vocal** : PyAudio, Edge-TTS
*   **Communication** : WebSockets pour la liaison en temps réel entre le Raspberry Pi et l'application mobile.

## 🏗 Architecture du système

Le système DAI repose sur deux composants principaux communicant via WebSockets :

```
┌─────────────────────────────────────────────────────────┐
│                 🚗 VÉHICULE OBD-II                       │
│         Données PID + Codes défauts (DTC)               │
└────────────────────────┬────────────────────────────────┘
                         │ ELM327 (USB / Bluetooth)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              🖥  RASPBERRY PI (Backend Python)           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  obd_module │→ │obd_normalizer│→ │diagnostic_mod │  │
│  │ (ELM327 raw)│  │(AI-ready data)│ │(Gemini LLM)   │  │
│  └─────────────┘  └──────────────┘  └───────┬───────┘  │
│                                             │           │
│  ┌───────────────┐  ┌──────────────┐        │           │
│  │  voice_module │  │  tts_module  │◄───────┘           │
│  │  (STT/micro)  │  │  (Edge-TTS)  │                    │
│  └───────────────┘  └──────────────┘                    │
│                   WebSocket (ws_module)                  │
└────────────────────────┬────────────────────────────────┘
                         │ Wi-Fi / Hotspot
                         ▼
┌─────────────────────────────────────────────────────────┐
│              📱 APPLICATION MOBILE (Flutter)             │
│  • Tableau de bord en temps réel (PID)                  │
│  • Affichage des codes défauts (DTC)                    │
│  • Historique des diagnostics                           │
│  • Interface chat IA                                    │
└─────────────────────────────────────────────────────────┘
```

### Structure du dépôt

```
sedai_GitHub_Export/
│
├── mobile_app/              # Application Flutter
│   ├── lib/                 #   Code source Dart
│   ├── android/             #   Config Android
│   ├── ios/                 #   Config iOS
│   └── pubspec.yaml         #   Dépendances
│
├── raspberry_pi/            # Système embarqué Python
│   ├── src/
│   │   ├── main.py          #   Point d'entrée principal
│   │   ├── obd_module.py    #   Communication ELM327 / OBD-II
│   │   ├── obd_normalizer.py#   Normalisation des données pour l'IA
│   │   ├── obd_safety.py    #   Sécurité et rate-limiting
│   │   ├── diagnostic_module.py # Moteur de diagnostic (Gemini)
│   │   ├── voice_module.py  #   Reconnaissance vocale
│   │   ├── tts_module.py    #   Synthèse vocale (Edge-TTS)
│   │   ├── ws_module.py     #   Serveur WebSocket
│   │   └── config.py        #   Configuration globale
│   ├── requirements.txt     #   Dépendances Python
│   └── install.sh           #   Script d'installation automatique
│
├── ai_engine/               # Modules IA (à venir)
├── docs/                    # Documentation, rapports, schémas
├── hardware/                # Câblage, OBD-II specs, BOM
└── tests/                   # Tests unitaires et d'intégration
```


## 🚀 Instructions d'installation et d'utilisation

### 1. Préparation du Raspberry Pi (Backend)
1. Flashez Raspberry Pi OS (Bookworm) sur une carte SD.
2. Clonez ce dépôt.
3. Configurez les dépendances audio et OBD :
   ```bash
   cd raspberry_pi
   chmod +x install.sh
   ./install.sh
   ```
4. Configurez vos clés API en créant un fichier `raspberry_pi/src/.env` (ajoutez la variable `GEMINI_API_KEY`).
5. Lancez le système :
   ```bash
   python src/main.py
   ```

### 2. Application Mobile (Frontend)
1. Installez le SDK [Flutter](https://flutter.dev/docs/get-started/install).
2. Accédez au répertoire mobile :
   ```bash
   cd mobile_app
   flutter pub get
   ```
3. Connectez un appareil physique ou lancez un émulateur, puis déployez l'application :
   ```bash
   flutter run
   ```
4. Dans l'application, configurez l'adresse IP du Raspberry Pi pour initier la connexion WebSocket.

## 📄 Licence

Ce projet est distribué sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

**YankeMall** - [GitHub](https://github.com/YankeMall)
*Créateur et développeur principal du système SEDAI.*

---

*SEDAI - Rendre la technologie automobile accessible à tous.* 🚗🤖
