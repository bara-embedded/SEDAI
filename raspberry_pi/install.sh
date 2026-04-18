#!/bin/bash
# install.sh - Script d'installation automatique pour le projet SEDAI
# Adapté pour Raspberry Pi OS (Debian)

echo "=========================================================="
echo "   Installation de SEDAI - Système Embarqué de Diagnostic "
echo "=========================================================="

# Requis pour éviter que les prompt interactifs bloquent l'installation
export DEBIAN_FRONTEND=noninteractive

echo "-> [1/5] Mise à jour et installation des prérequis système..."
sudo apt-get update
# portaudio19-dev/libportaudio2 -> PyAudio & Sounddevice
# espeak-ng -> Essentiel pour faire fonctionner Piper-TTS
sudo apt-get install -y python3-venv python3-pip portaudio19-dev alsa-utils libportaudio2 espeak-ng git curl

echo "-> [2/5] Création de l'environnement virtuel (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "[!] Environnement virtuel créé avec succès."
else
    echo "[i] L'environnement virtuel existe déjà."
fi

echo "-> [3/5] Activation et installation des paquets Python..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "-> [4/5] Vérification de l'installation d'Ollama (Serveur IA)..."
if ! command -v ollama &> /dev/null
then
    echo "[!] Ollama introuvable. Installation d'Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "[i] Ollama est déjà installé sur ce système."
fi

echo "-> [5/5] Préparation de la structure des dossiers IA locaux..."
# Ces dossiers correspondent aux chemins fixes de "/home/sedai/models/" dans config.py
mkdir -p /home/sedai/models/piper
mkdir -p /home/sedai/models/vosk

echo "=========================================================="
echo "✅ Installation complètement achevée !"
echo " "
echo "💡 POUR DÉMARRER SEDAI, exécutez la commande suivante :"
echo "   source .venv/bin/activate && python3 src/main.py"
echo "=========================================================="
