# 📊 Rapport d'État d'Avancement : Projet SEDAI v2.0
**Date** : 12 Avril 2026  
**Objet** : Synthèse technique et fiabilisation du système de diagnostic intelligent local.

---

## 1. 🎯 Objectif du Projet
Le projet **SEDAI** (Système Embarqué de Diagnostic Automobile Intelligent) vise à fournir un assistant vocal local, autonome et performant, capable de diagnostiquer les véhicules via l'interface OBD-II. Le système est optimisé pour un usage au Bénin, avec un accent sur la concision des rapports et la robustesse matérielle (Raspberry Pi 5).

---

## 2. 🏗️ Architecture du Système

### 2.1. Matériel (Hardware)
- **Cœur** : Raspberry Pi 5 (8 Go RAM vivement conseillé).
- **Interface Véhicule** : Adaptateur USB OBD-II (ELM327).
- **Interface Audio** : Microphone et Haut-parleur USB (Carte ALSA index 2).

### 2.2. Logiciel (Software)
- **Backend (Python 3.11+)** : Orchestration asynchrone des modules.
- **IA (Ollama/Gemma3:4b)** : Modèle de langage local pour l'analyse des pannes.
- **ASR (Vosk)** : Reconnaissance vocale hors-ligne (Modèle FR 0.22).
- **TTS (Piper)** : Synthèse vocale ultra-rapide et naturelle.
- **Frontend (Flutter)** : Interface de contrôle HUD (Head-Up Display) temps réel.

---

## 3. ✅ Travaux Réalisés (Détails Techniques)

### 3.1. Intelligence Artificielle & Diagnostic
- **Optimisation du Prompt** : Nouveau `SYSTEM_PROMPT` imposant une concision extrême.
    - *Véhicule sain* : Réponse de 1 à 2 phrases maximum, interdiction de conseils génériques.
    - *Anomalie* : Raisonnement par "Systèmes" (ex: injection, allumage) sans citer de pièces précises pour éviter les faux diagnostics.
- **Mode 06 (Misfires)** : Implémentation du suivi des ratés d'allumage cylindre par cylindre via les adresses CAN modernes ($A2-$A7).
- **Priorisation des PIDs** : Tri des données OBD en trois catégories (Critique: 1Hz, Important: 0.5Hz, Secondaire: 0.2Hz) pour maximiser la réactivité.

### 3.2. Système Vocal (Audio)
- **Chaîne TTS Fiabilisée** : Utilisation de `Piper` en flux "raw" dirigé vers `aplay` sur la carte USB spécifique (`plughw:2,0`).
- **Initialisation Automatique** : Script intégrant le débogage ALSA et le "unmute" automatique du volume au démarrage.
- **Reconnaissance Contextuelle** : Support de commandes spécifiques (Diagnostic, État, Effacement des codes, Répétition).

### 3.3. Infrastructure & Stabilité
- **Gestion des Logs** : Rotation automatique des journaux (`sedai.log`) limitée à 10 Mo pour éviter la saturation de la carte SD.
- **Service Systemd** : Déploiement d'un démon `sedai.service` gérant le redémarrage automatique en cas de crash.

---

## 4. ⚠️ Points de Blocage Actuels (Connectivité)

Le système rencontre actuellement une erreur de communication entre l'application mobile et le Raspberry Pi.

> [!WARNING]
> **Erreur détectée** : `SocketException: Connection refused (errno = 1225)`  
> **Diagnostic** : L'application tente de se connecter à l'IP `10.95.195.84` sur des ports variables (ex: `59249`, `62601`), alors que le backend est configuré pour écouter sur le port fixe **`8765`**.

**Actions requises** :
1. Vérifier que l'IP du Raspberry Pi est bien fixe ou réservée sur votre routeur/point d'accès.
2. S'assurer que le port `8765` est autorisé dans le pare-feu (`sudo ufw allow 8765`).
3. Mettre à jour les réglages de l'application Flutter pour pointer explicitement sur le port `8765`.

---

## 5. 🛠️ Guide de Maintenance (SSH)

Voici les commandes essentielles pour piloter SEDAI à distance :

| Action | Commande |
| :--- | :--- |
| **Vérifier l'état** | `sudo systemctl status sedai.service` |
| **Voir les logs en direct** | `journalctl -u sedai.service -f` |
| **Redémarrer le backend** | `sudo systemctl restart sedai.service` |
| **Redémarrer l'IA** | `sudo systemctl restart ollama` |
| **Vérifier les ports** | `sudo netstat -tulpn | grep 8765` |

---

## 6. 🚀 Prochaines Étapes
1.  **Correction de la communication** WebSocket (Alignement des ports).
2.  **Test en conditions réelles** sur route pour valider l'inférence de Gemma3 en roulant.
3.  **Finalisation du Dashboard** Flutter (Lissage des jauges et alertes visuelles).

---
*Fin du rapport.* 🚗💨
