"""
diagnostic_module.py — Diagnostic IA avec Gemma3 local (SEDAI v2.0)
Gère l'analyse complète en interrogeant le modèle de langage via l'API locale d'Ollama.
"""

import logging
import threading
import queue
import requests
import json
import time
from typing import Any, Dict, List, Optional

from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, SYSTEM_PROMPT
from memory_module import MemoryModule
from tts_module import TTSModule
from obd_normalizer import OBDNormalizer

# Logger dédié à ce module
logger = logging.getLogger("DIAGNOSTIC")


class DiagnosticModule(threading.Thread):
    def __init__(
        self,
        shared_state: Dict[str, Any],
        state_lock: threading.Lock,
        action_queue: queue.Queue,
        memory: MemoryModule,
        tts: TTSModule,
        event_stop: threading.Event,
    ) -> None:
        super().__init__(daemon=True)
        self.shared_state = shared_state
        self.state_lock = state_lock
        self.action_queue = action_queue
        self.memory = memory
        self.tts = tts
        self.event_stop = event_stop

    # Correspondance clé OBD → libellé lisible + unité
    _OBD_SCHEMA: Dict[str, Dict[str, str]] = {
        "vitesse":            {"label": "Vitesse",                    "unit": "km/h"},
        "regime":             {"label": "Régime moteur",              "unit": "RPM"},
        "temp_moteur":        {"label": "Température moteur",         "unit": "°C"},
        "maf":                {"label": "Débit air (MAF)",            "unit": "g/s"},
        "map":                {"label": "Pression admission (MAP)",   "unit": "kPa"},
        "tension":            {"label": "Tension batterie",           "unit": "V"},
        "charge":             {"label": "Charge moteur",              "unit": "%"},
        "papillon":           {"label": "Position papillon",          "unit": "%"},
        "avance":             {"label": "Avance allumage",            "unit": "°"},
        "temp_admission":     {"label": "Température admission",      "unit": "°C"},
        "pression_huile":     {"label": "Pression huile",             "unit": "kPa"},
        "pression_carburant": {"label": "Pression carburant",         "unit": "kPa"},
        "carburant":          {"label": "Niveau carburant",           "unit": "%"},
        "lambda":             {"label": "Sonde lambda (B1S1)",        "unit": "V"},
        "stft_b1":            {"label": "Correction court terme (STFT B1)", "unit": "%"},
        "ltft_b1":            {"label": "Correction long terme (LTFT B1)", "unit": "%"},
        "temp_transmission":  {"label": "Température transmission",   "unit": "°C"},
    }

    def _build_obd_json(self, obd_data: Dict[str, Any]) -> str:
        """
        Construit un JSON structuré avec valeurs décodées et unités explicites.

        Ollama reçoit uniquement :
          - des valeurs numériques décodées (jamais du HEX brut ni réponses ELM brutes)
          - l'unité physique de chaque paramètre
          - le libellé lisible en français

        Returns:
            Chaîne JSON compacte, prête à être insérée dans le prompt Ollama.
        """
        structured: Dict[str, Any] = {}
        for key, meta in self._OBD_SCHEMA.items():
            value = obd_data.get(key)
            if value is not None:
                structured[meta["label"]] = {
                    "valeur": value,
                    "unite": meta["unit"],
                }
        if not structured:
            return json.dumps({"statut": "Données OBD non disponibles"}, ensure_ascii=False)
        return json.dumps(structured, ensure_ascii=False, indent=2)

    def build_prompt(
        self,
        vehicle_info: Dict[str, str],
        obd_data: Dict[str, Any],
        dtcs: List[str],
        context: str,
        ai_snapshot: Optional[Dict[str, Any]] = None,
        obd_status: str = "déconnecté"
    ) -> List[Dict[str, str]]:
        dernier = self.memory.get_last_report()
        if dernier:
            context_enrichi = f"{context} | Dernier diagnostic : {dernier[:100]}..."
        else:
            context_enrichi = context

        # Schema Lock : Format UNIQUE garanti pour le LLM, qu'on ait le snapshot IA ou non
        if ai_snapshot:
            strict_data = OBDNormalizer.ensure_strict_schema(ai_snapshot, obd_status)
            header_data = "DONNÉES ENRICHIES (SCHEMA LOCK) :"
        else:
            # Fallback déterministe simulant un snapshot à partir des données brutes
            fake_snapshot = {
                "donnees": obd_data,
                "dtcs": dtcs,
                "vehicule": f"{vehicle_info.get('marque', 'Inconnu')} {vehicle_info.get('modele', '')}",
            }
            strict_data = OBDNormalizer.ensure_strict_schema(fake_snapshot, obd_status)
            header_data = "DONNÉES BRUTES (SCHEMA LOCK - Fiabilité réduite) :"

        obd_json = json.dumps(strict_data, ensure_ascii=False, indent=2)

        user_message = f"""
ÉTAT OBD     : {obd_status.upper()}
ÉTAT SYSTÈME : {"MODE DÉGRADÉ ACTIF (Ressources limitées)" if "dégradé" in obd_status.lower() else "NORMAL"}
VÉHICULE     : {vehicle_info.get('marque', 'Inconnu')} {vehicle_info.get('modele', '')}
ANNÉE        : {vehicle_info.get('annee', 'N/A')}

{header_data}
{obd_json}

CODES DÉFAUTS (DTC) : {', '.join(dtcs) if dtcs else 'Aucun défaut détecté'}
CONFIANCE DONNÉES   : {"Haute" if ai_snapshot else "Basse (Données brutes)"}
CONTEXTE            : {context_enrichi}

RAPPEL: 
1. Commence par l'état OBD [Connecté] ou [Déconnecté].
2. Niveau d'alerte [FAIBLE], [MODÉRÉ] ou [CRITIQUE].
3. Reste extremement court et factuel. Pas de bavardage.
"""
        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.memory.get_history())
        messages.append({"role": "user", "content": user_message})
        return messages

    def run_gemma_analysis(self, messages: List[Dict[str, str]]) -> str:
        url = f"{OLLAMA_URL}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.6}
        }
        try:
            logger.info("[DIAGNOSTIC] Génération du rapport via Gemma3...")
            response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            ai_response = response.json().get("message", {}).get("content", "").strip()
            
            # --- LLM FAIL-SAFE (Réponse vide ou incohérente) ---
            if not ai_response or not ("[" in ai_response and "]" in ai_response):
                logger.warning("[DIAGNOSTIC] LLM Fallback déclenché : réponse vide ou format invalide.")
                return "[Connecté] [MODÉRÉ] Inférence limitée. La structure du diagnostic est compromise."
            
            # --- CORRECTION MATÉRIELLE OBLIGATOIRE (ANTI-BROWNOUT) ---
            # Il est VITAL de limiter le temps de parole de l'IA quand tout va bien.
            # L'amplificateur USB tire trop de tension électrique : s'il reste allumé
            # plus de 5 secondes, tout le port USB du système court-circuite et plante.
            if "[FAIBLE]" in ai_response.upper():
                import re
                sentences = re.split(r'(?<=[.!?]) +', ai_response)
                if len(sentences) > 2:
                    ai_response = " ".join(sentences[:2])
                    
            return ai_response
        except requests.RequestException as e:
            logger.error(f"[DIAGNOSTIC] Erreur Ollama : {e}")
            self.tts.speak("Une erreur de communication m'empêche d'établir un diagnostic.")
            
            # --- FAIL-SAFE DÉTERMINISTE ---
            obd_stat = str(self.shared_state.get("statut_obd", "")).lower()
            if "déconnecté" in obd_stat:
                return "[Déconnecté] [MODÉRÉ] Diagnostic indisponible (Timeout API). Vérification matérielle requise."
            else:
                return "[Connecté (Dégradé)] [MODÉRÉ] Analyse IA interrompue (Timeout). Données captées mais non interprétées."

    def run(self) -> None:
        logger.info("[DIAGNOSTIC] Démarrage du thread de diagnostic IA.")
        while not self.event_stop.is_set():
            try:
                action = self.action_queue.get(timeout=1.0)
                type_action = action.get("type")

                if type_action in ["diagnostic_request", "free_chat"]:
                    source = action.get("source", "inconnu")
                    text_context = action.get("text", "")
                    with self.state_lock:
                        obd_status   = self.shared_state.get("statut_obd", "déconnecté")
                        obd_data     = dict(self.shared_state.get("obd_data", {}))
                        dtcs         = list(self.shared_state.get("dtcs", []))
                        vehicle_info = dict(self.shared_state.get("vehicle_info", {}))
                        ai_snapshot  = self.shared_state.get("obd_snapshot_ia")

                    messages = self.build_prompt(
                        vehicle_info, obd_data, dtcs, 
                        context=text_context, 
                        ai_snapshot=ai_snapshot,
                        obd_status=obd_status
                    )
                    report = self.run_gemma_analysis(messages)
                    self.memory.add_exchange(text_context, report)
                    
                    if type_action == "diagnostic_request":
                        with self.state_lock:
                            self.shared_state["dernier_rapport"] = {"texte": report, "source": source}
                    
                    self.tts.speak(report)

                elif type_action == "get_dtcs":
                    with self.state_lock:
                        dtcs = list(self.shared_state.get("dtcs", []))
                    if dtcs:
                        self.tts.speak(f"J'ai détecté les défauts suivants : {', '.join(dtcs)}.")
                    else:
                        self.tts.speak("Aucun code défaut détecté.")

                elif type_action == "clear_dtcs":
                    self.tts.speak("Je demande l'effacement des codes défauts.")

                elif type_action == "speak":
                    texte = action.get("text", "")
                    if texte:
                        self.tts.speak(texte)

                elif type_action == "repeat_last":
                    with self.state_lock:
                        dernier = self.shared_state.get("dernier_rapport", {})
                        texte = dernier.get("texte", "") if dernier else ""
                    if texte:
                        self.tts.speak(texte)
                    else:
                        self.tts.speak("Je n'ai pas de message récent à répéter.")

                self.action_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[DIAGNOSTIC] Erreur inattendue : {e}")
        logger.info("[DIAGNOSTIC] Arrêt du thread de diagnostic.")
