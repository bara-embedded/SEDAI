# GEMINI.md — Règles Antigravity pour le projet SEDAI
# Système embarqué de diagnostic automobile intelligent
# Raspberry Pi 5 — Python — OBD-II — IA locale

---

## 🎯 IDENTITÉ DU PROJET

Tu travailles sur **SEDAI** (Système Embarqué de Diagnostic Automobile Intelligent),
un système Python embarqué sur Raspberry Pi 5 (8 Go RAM, Raspberry Pi OS).
Le système fonctionne **100% hors ligne**, sans connexion Internet.

---

## 🔌 PÉRIPHÉRIQUES USB — OBLIGATOIRE

Ces périphériques sont TOUS connectés via USB. Ne jamais supposer Bluetooth ou Wi-Fi.

| Périphérique        | Connexion       | Identifiant Linux         | Bibliothèque       |
|---------------------|-----------------|---------------------------|--------------------|
| Interface OBD-II    | ELM327 **USB**  | /dev/ttyUSB0              | python-obd         |
| Microphone          | Micro **USB**   | Détecté par sounddevice   | sounddevice + vosk |
| Haut-parleur        | HP **USB**      | Détecté par ALSA (aplay)  | subprocess + aplay |

### Règles strictes sur les périphériques
- ❌ Jamais de Bluetooth (pas de `bluetooth`, `BLE`, `rfcomm`)
- ❌ Jamais de Wi-Fi pour l'OBD (pas de socket TCP vers ELM327)
- ❌ Jamais de jack audio (tout passe par USB)
- ✅ ELM327 toujours via port série USB : `OBD_PORT = "/dev/ttyUSB0"`
- ✅ Microphone : détection automatique USB via `sounddevice`
- ✅ Audio sortie : toujours via `aplay` (ALSA) → haut-parleur USB

---

## 📁 STRUCTURE DES FICHIERS À GÉNÉRER

Tu dois créer exactement ces 10 fichiers Python, rien de plus :

```
SEDAI/
├── config.py           ← Toutes les constantes (NE JAMAIS modifier depuis d'autres fichiers)
├── main.py             ← Point d'entrée unique — lance tous les threads
├── startup.py          ← Démarrage autonome Ollama
├── obd_module.py       ← Acquisition données OBD-II + reconnexion automatique
├── monitor_module.py   ← Surveillance silencieuse toutes les 30s
├── diagnostic_module.py← Diagnostic Gemma3 + conversation libre
├── tts_module.py       ← Synthèse vocale Piper TTS avec file d'attente
├── voice_module.py     ← Reconnaissance vocale Vosk push-to-talk
├── memory_module.py    ← Mémoire conversationnelle JSON persistante
└── ws_module.py        ← Serveur WebSocket bidirectionnel Flutter
```

---

## ⚙️ RÈGLES TECHNIQUES STRICTES

### Python
- Version : Python 3.11+ (Raspberry Pi OS Bookworm)
- Style : PEP 8 obligatoire
- Typage : Utiliser les type hints sur toutes les fonctions
- Docstrings : Obligatoires sur chaque classe et méthode (format Google Style)
- Encoding : UTF-8 partout, notamment pour le français
- Logs : Utiliser le format `[MODULE] Message` (ex: `[OBD] Connexion établie`)
- Pas de print() brut — toujours préfixer avec le nom du module

### Threading
- Parallélisme : threading (jamais asyncio, jamais multiprocessing)
- Chaque module = 1 thread daemon
- Communication inter-threads : Queue et Event (jamais de variables globales partagées sans Lock)
- Toujours utiliser try/except dans les boucles de threads pour éviter les crashs silencieux

### Gestion des erreurs
- Toute exception doit être capturée et loggée
- Les erreurs critiques (Ollama inaccessible, OBD déconnecté) déclenchent une alerte vocale
- Jamais de crash sans message explicite
- Les reconnexions se font en boucle automatiquement

### Constantes
- TOUTES les constantes viennent de config.py via `from config import *`
- Jamais de valeur codée en dur dans le code (pas de "8765", "/dev/ttyUSB0", etc.)
- Jamais de modification de config.py depuis un autre module

---

## 🚫 INTERDICTIONS ABSOLUES

- ❌ Pas de connexion Internet (pas de requests vers des serveurs externes)
- ❌ Pas d'asyncio (threading uniquement)
- ❌ Pas de valeurs hardcodées en dehors de config.py
- ❌ Pas de modèle IA en ligne (Ollama local uniquement)
- ❌ Pas de base de données (JSON uniquement pour la mémoire)
- ❌ Pas de dépendances non listées dans la section bibliothèques
- ❌ Pas de code superflu — chaque ligne doit avoir un rôle précis

---

## ✅ COMPORTEMENT ATTENDU DE L'AGENT

1. Lire d'abord le prompt complet dans references/PROMPT_V4.md avant de coder
2. Générer les fichiers dans l'ordre : config.py → startup.py → obd_module.py → memory_module.py → tts_module.py → voice_module.py → monitor_module.py → diagnostic_module.py → ws_module.py → main.py
3. Après chaque fichier généré, vérifier la cohérence avec config.py
4. Ne jamais supposer une valeur — toujours lire config.py
5. Tester la syntaxe Python de chaque fichier avant de passer au suivant
