"""
obd_module.py — Acquisition des données OBD-II (SEDAI v2.1 — Safe Edition)

Changements v2.1 vs v2.0 :
  - Système de time-slicing par cycles (critique / standard / secondaire / optionnel)
  - Délai inter-PID (OBD_INTER_PID_DELAY) appliqué systématiquement
  - Compteur d'erreurs par PID : déconnexion uniquement après N erreurs globales
  - Reconnexion avec backoff exponentiel plafonné
  - Watchdog ELM327 pour détecter les freezes silencieux
  - clear_dtc() protégé : interdit si vitesse > 0 ou RPM actif
  - TRANS_TEMP et PIDs optionnels relégués en cycle lent (toutes les 30 itérations)
  - Intégration obd_safety et obd_normalizer

Comportement "read-only safe" garanti :
  - Uniquement commandes Mode 01 (lecture de données temps réel)
  - Mode 03 pour lecture DTC (passif)
  - Mode 04 (clear_dtc) uniquement sur commande explicite, véhicule arrêté
  - Aucune commande AT custom, aucun mode étendu
"""

import logging
import time
import threading
import queue
from typing import Any, Dict, List, Optional

import obd

from config import (
    OBD_PORT, OBD_BAUDRATE, OBD_TIMEOUT,
    OBD_BACKOFF_BASE, OBD_BACKOFF_FACTOR, OBD_BACKOFF_MAX,
    OBD_CYCLE_CRITICAL_INTERVAL,
    OBD_CYCLE_STANDARD_EVERY,
    OBD_CYCLE_SECONDARY_EVERY,
    OBD_CYCLE_OPTIONAL_EVERY,
    OBD_GLOBAL_ERROR_THRESHOLD,
    OBD_PIDS_CRITIQUES, OBD_PIDS_STANDARD,
    OBD_PIDS_SECONDAIRES, OBD_PIDS_OPTIONNELS,
    SEUIL_TEMP_TRANSMISSION_MAX,
    OBD_STABILIZATION_DELAY, OBD_IDLE_RPM_THRESHOLD,
    OBD_DEGRADED_MODE_INTERVAL, DEGRADED_VOLTAGE_THRESHOLD,
    DEGRADED_VOLTAGE_RECOVERY_THRESHOLD, DEGRADED_RECOVERY_CYCLES,
    OBD_CAN_BUDGET_MS,
)
from obd_safety import RateLimiter, PIDHealthTracker, ELM327Watchdog, BackoffCalculator
from obd_normalizer import OBDNormalizer

logger = logging.getLogger("OBD")

# Supprimer les logs internes de python-obd (très verbeux sur clones ELM)
obd.logger.setLevel(obd.logging.CRITICAL)

# Délai de stabilisation après connexion physique.
# Laisse l'ELM327 terminer son handshake CAN avant le premier PID.
_ELM_INIT_DELAY_S: float = 3.0


# ══════════════════════════════════════════════════════════════════════════════
# Cycle descriptor
# ══════════════════════════════════════════════════════════════════════════════

# Chaque cycle associe un nom de groupe PID à son intervalle (en nombre
# d'itérations critiques). Le cycle critique tourne à chaque itération.
_CYCLES = [
    ("critique",   OBD_PIDS_CRITIQUES,   1),
    ("standard",   OBD_PIDS_STANDARD,    OBD_CYCLE_STANDARD_EVERY),
    ("secondaire", OBD_PIDS_SECONDAIRES, OBD_CYCLE_SECONDARY_EVERY),
    ("optionnel",  OBD_PIDS_OPTIONNELS,  OBD_CYCLE_OPTIONAL_EVERY),
]


def _resolve_command(pid_name: str) -> Optional[obd.OBDCommand]:
    """
    Résout un nom de PID (str) en commande python-obd.

    Retourne None si le PID est inconnu, sans lever d'exception.
    Cela évite tout crash si un nom est mal orthographié en config.
    """
    cmd = getattr(obd.commands, pid_name, None)
    if cmd is None:
        logger.warning(f"[OBD] PID inconnu dans la config : '{pid_name}' — ignoré.")
    return cmd


# ══════════════════════════════════════════════════════════════════════════════
# OBDModule
# ══════════════════════════════════════════════════════════════════════════════

class OBDModule(threading.Thread):
    """
    Thread d'acquisition OBD-II avec time-slicing, rate limiting et watchdog.

    Architecture interne :
      1. RateLimiter      → délai inter-PID (150 ms)
      2. PIDHealthTracker → désactive les PIDs systématiquement en erreur
      3. ELM327Watchdog   → détecte les freezes silencieux de l'adaptateur
      4. BackoffCalculator→ reconnexion progressive
      5. OBDNormalizer    → sortie JSON IA-ready
    """

    def __init__(
        self,
        shared_state: Dict[str, Any],
        state_lock: threading.Lock,
        action_queue: queue.Queue,
        event_stop: threading.Event,
    ) -> None:
        super().__init__(daemon=True)
        self.shared_state = shared_state
        self.state_lock   = state_lock
        self.action_queue = action_queue
        self.event_stop   = event_stop

        # Connexion OBD
        self.connection: Optional[obd.OBD] = None
        self.connected: bool = False

        # Couche sécurité
        self._rate_limiter  = RateLimiter()
        self._pid_tracker   = PIDHealthTracker()
        self._watchdog      = ELM327Watchdog()
        self._backoff       = BackoffCalculator(
            base_s=OBD_BACKOFF_BASE,
            factor=OBD_BACKOFF_FACTOR,
            max_s=OBD_BACKOFF_MAX,
        )

        # Normalisation
        self._normalizer: Optional[OBDNormalizer] = None

        # Compteur d'itérations critiques (référence pour le time-slicing)
        self._iteration: int = 0

        # Compteur d'erreurs globales consécutives (toute requête PID)
        self._global_errors: int = 0

        # Snapshot courant des données (toutes catégories cumulées)
        self._live_snapshot: Dict[str, Any] = {}

        # Suivi de la stabilité moteur pour Mode 04 safety
        self._last_unstable_time: float = 0.0

        # State Machine et Mode dégradé
        self.vehicle_state: str = "STARTING"
        self.is_degraded_mode: bool = False
        self._degraded_recovery_counter: int = 0

    # ──────────────────────────────────────────────────────────────────────────
    # Connexion
    # ──────────────────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Tente d'établir la connexion OBD-II.

        Stratégie :
          1. Port configuré en priorité
          2. Auto-scan si le port configuré échoue
          3. Délai de stabilisation ELM _ELM_INIT_DELAY_S avant la 1ère requête
          4. Vérification de tension (commande légère, sans risque)

        Returns:
            True si connecté et opérationnel.
        """
        try:
            logger.info(
                f"[OBD] Connexion sur {OBD_PORT} "
                f"(baudrate={OBD_BAUDRATE}, fast=False, timeout={OBD_TIMEOUT}s)..."
            )
            conn = obd.OBD(
                OBD_PORT,
                baudrate=OBD_BAUDRATE,
                fast=False,       # Sécurité : désactive les commandes AT rapides
                timeout=OBD_TIMEOUT,
            )

            if not conn.is_connected():
                logger.warning(
                    f"[OBD] Port {OBD_PORT} inaccessible. "
                    "Tentative d'auto-scan..."
                )
                conn = obd.OBD(fast=False, timeout=OBD_TIMEOUT)

            if not conn.is_connected():
                self.connected = False
                logger.error(
                    "[OBD] Aucune interface ELM327 détectée. "
                    "Vérifier le câble USB et l'alimentation du véhicule."
                )
                return False

            self.connection = conn
            port_actuel = self.connection.port_name()
            logger.info(
                f"[OBD] Interface détectée sur {port_actuel}. "
                f"Stabilisation {_ELM_INIT_DELAY_S}s..."
            )

            # Délai de stabilisation : l'ELM327 finalise son handshake CAN
            time.sleep(_ELM_INIT_DELAY_S)

            # Vérification de tension (commande AT RV — sans impact ECU)
            tension = self._check_voltage()
            if tension is not None:
                logger.info(f"[OBD] Tension batterie : {tension:.1f} V")
                if tension < 11.5:
                    logger.warning(
                        "[OBD] Tension faible (< 11.5 V) — "
                        "les lectures peuvent être instables."
                    )
            else:
                logger.info("[OBD] Tension non disponible sur cet adaptateur.")

            # Réinitialisation des compteurs après connexion réussie
            self._pid_tracker.reset()
            self._normalizer = OBDNormalizer(
                self.shared_state.get("vehicle_info", {})
            )
            self._normalizer.reset_history()
            self._iteration = 0
            self._global_errors = 0
            self._live_snapshot.clear()

            self._watchdog.start()
            self._backoff.reset()

            self.connected = True
            with self.state_lock:
                self.shared_state["statut_obd"] = "connecté"
            logger.info(f"[OBD] Connexion pleinement établie sur {port_actuel}.")
            return True

        except Exception as e:
            self.connected = False
            logger.error(f"[OBD] Erreur lors de la connexion : {e}")
            return False

    def _check_voltage(self) -> Optional[float]:
        """
        Lit la tension via AT RV (commande AT sans interaction ECU).
        C'est la commande la moins intrusive possible sur l'ELM327.
        """
        if self.connection is None:
            return None
        try:
            response = self.connection.query(obd.commands.ELM_VOLTAGE)
            if not response.is_null():
                val = response.value
                return float(val.magnitude) if hasattr(val, "magnitude") else float(val)
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Requête PID sécurisée
    # ──────────────────────────────────────────────────────────────────────────

    def _query_pid_safe(self, command: obd.OBDCommand, pid_name: str) -> Optional[Any]:
        """
        Interroge un PID avec protection rate limiter + health tracker.

        Différence v2.1 vs v2.0 :
          - Ne déconnecte PAS immédiatement sur une erreur isolée
          - Incrémente le compteur global d'erreurs consécutives
          - La déconnexion est déclenchée uniquement si ce compteur dépasse
            OBD_GLOBAL_ERROR_THRESHOLD (erreur systémique, pas PID spécifique)

        Args:
            command  : commande python-obd à envoyer
            pid_name : nom string du PID (pour le tracker)

        Returns:
            Valeur numérique propre, ou None si réponse nulle/erreur.
        """
        if not self.connected or self.connection is None:
            return None

        # Vérification health tracker : PID en quarantaine ?
        if not self._pid_tracker.is_active(pid_name):
            return None

        # Respecter le délai inter-PID (rate limiter)
        self._rate_limiter.wait()

        try:
            response = self.connection.query(command)
            self._rate_limiter.record()

            if response.is_null():
                # Réponse vide = PID non supporté par l'ECU (NO DATA)
                # Ce n'est PAS une erreur de communication.
                self._pid_tracker.record_failure(pid_name)
                return None

            # Succès : réinitialiser les compteurs d'erreur
            self._pid_tracker.record_success(pid_name)
            self._watchdog.record_valid_response()
            self._global_errors = 0

            val = response.value
            return float(val.magnitude) if hasattr(val, "magnitude") else val

        except Exception as e:
            self._rate_limiter.record()
            self._pid_tracker.record_failure(pid_name)
            self._global_errors += 1

            logger.warning(
                f"[OBD] Erreur PID '{pid_name}' "
                f"({self._global_errors}/{OBD_GLOBAL_ERROR_THRESHOLD}) : {e}"
            )

            if self._global_errors >= OBD_GLOBAL_ERROR_THRESHOLD:
                logger.error(
                    f"[OBD] {self._global_errors} erreurs consécutives globales — "
                    "problème de communication avec l'ELM327. Reconnexion programmée."
                )
                self.connected = False

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Time-Slicing par cycles
    # ──────────────────────────────────────────────────────────────────────────

    def _read_cycle(self) -> str:
        """
        Exécute les PIDs du cycle courant selon le time-slicing.

        Logique :
          - À chaque itération, le cycle CRITIQUE est toujours exécuté.
          - Si en mode dégradé, ignore les autres cycles.
          - Les autres cycles sont exécutés seulement si `_iteration`
            est un multiple de leur intervalle.
          - Les résultats s'accumulent dans `_live_snapshot`.
        Returns:
            Nom du cycle le plus "avancé" exécuté dans cette itération.
        """
        active_cycle = "critique"
        cycle_start_time = time.time()

        for cycle_name, pid_list, every_n in _CYCLES:
            if self.is_degraded_mode and cycle_name != "critique":
                # En mode dégradé, on ne lit QUE le cycle critique (Max 3 PIDs)
                continue

            if self._iteration % every_n != 0:
                continue

            active_cycle = cycle_name
            for pid_name in pid_list:
                # [BUDGET LATENCE CAN] Ne jamais couper le critique, restreindre le reste
                if cycle_name != "critique":
                    if (time.time() - cycle_start_time) > (OBD_CAN_BUDGET_MS / 1000.0):
                        logger.warning(
                            f"[OBD] Budget latence CAN dépassé (> {OBD_CAN_BUDGET_MS}ms). "
                            "Fin anticipée du cycle."
                        )
                        return active_cycle

                cmd = _resolve_command(pid_name)
                if cmd is None:
                    continue

                key = self._pid_key(pid_name)
                value = self._query_pid_safe(cmd, pid_name)

                if value is not None:
                    self._live_snapshot[key] = (
                        round(value, 2) if isinstance(value, float) else value
                    )

                # Ne pas continuer si déconnexion détectée en cours de cycle
                if not self.connected:
                    return active_cycle

        return active_cycle

    @staticmethod
    def _pid_key(pid_name: str) -> str:
        """Convertit le nom de commande OBD en clé interne SEDAI."""
        _PID_TO_KEY = {
            "RPM":                    "regime",
            "COOLANT_TEMP":           "temp_moteur",
            "CONTROL_MODULE_VOLTAGE": "tension",
            "SPEED":                  "vitesse",
            "ENGINE_LOAD":            "charge",
            "MAF":                    "maf",
            "INTAKE_PRESSURE":        "map",
            "SHORT_TERM_FUEL_TRIM_1": "stft_b1",
            "LONG_TERM_FUEL_TRIM_1":  "ltft_b1",
            "THROTTLE_POS":           "papillon",
            "TIMING_ADVANCE":         "avance",
            "INTAKE_TEMP":            "temp_admission",
            "FUEL_LEVEL":             "carburant",
            "FUEL_PRESSURE":          "pression_carburant",
            "O2_B1S1":                "lambda",
            "ENGINE_OIL_PRESSURE":    "pression_huile",
            "TRANS_TEMP":             "temp_transmission",
        }
        return _PID_TO_KEY.get(pid_name, pid_name.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # DTC
    # ──────────────────────────────────────────────────────────────────────────

    def get_dtc(self) -> List[str]:
        """
        Récupère les codes défauts actifs (Mode 03 — lecture passive).

        Aucune action corrective n'est prise : lecture seule.

        Returns:
            Liste de codes DTC (ex: ['P0104']). Vide si aucun défaut.
        """
        if not self.connected or self.connection is None:
            return []
        try:
            response = self.connection.query(obd.commands.GET_DTC)
            if not response.is_null() and isinstance(response.value, list):
                return [code[0] for code in response.value if code]
        except Exception as e:
            logger.error(f"[OBD] Erreur lecture DTC : {e}")
        return []

    def _update_engine_state(self) -> None:
        """
        Met à jour le chronomètre de stabilité moteur.
        Remet le timer à now() si le véhicule bouge ou n'est pas au ralenti.
        """
        vitesse = self._live_snapshot.get("vitesse", 0)
        regime = self._live_snapshot.get("regime", 0)

        is_moving = isinstance(vitesse, (int, float)) and vitesse > 0
        is_high_rpm = isinstance(regime, (int, float)) and regime > OBD_IDLE_RPM_THRESHOLD

        if is_moving or is_high_rpm:
            self._last_unstable_time = time.time()

    def clear_dtc(self, confirmed: bool = False) -> bool:
        """
        Efface les codes défauts (Mode 04).

        SÉCURITÉ (v2.1) — CONDITIONS STRICTES :
          1. véhicule arrêté (vitesse == 0)
          2. moteur sous la barre de ralenti (RPM < OBD_IDLE_RPM_THRESHOLD)
          3. stabilisé depuis au moins OBD_STABILIZATION_DELAY secondes
          4. L'utilisateur doit explicitement confirmer l'action (confirmed=True)

        Returns:
            True si l'effacement a été envoyé et accepté, False sinon.
        """
        if not confirmed:
            logger.warning("[OBD] clear_dtc() REFUSÉ — confirmation explicite requise (confirmed=False).")
            return False

        if not self.connected or self.connection is None:
            return False

        # Garde de sécurité : vérifier le contexte véhicule
        vitesse = self._live_snapshot.get("vitesse", 0)
        regime  = self._live_snapshot.get("regime", 0)

        if isinstance(vitesse, (int, float)) and vitesse > 0:
            logger.warning(
                "[OBD] clear_dtc() REFUSÉ — véhicule en mouvement "
                f"(vitesse={vitesse} km/h). Arrêtez le véhicule."
            )
            return False

        if isinstance(regime, (int, float)) and regime > OBD_IDLE_RPM_THRESHOLD:
            logger.warning(
                "[OBD] clear_dtc() REFUSÉ — régime moteur trop élevé "
                f"(régime={regime} RPM). Cette action nécessite l'arrêt ou le ralenti."
            )
            return False

        now = time.time()
        # Si on n'a jamais initialisé le chronomètre ou s'il n'est pas stable
        if self.vehicle_state != "STABLE":
            logger.warning(
                "[OBD] clear_dtc() REFUSÉ — Le véhicule n'est pas dans l'état STABLE "
                f"(état actuel : {self.vehicle_state})."
            )
            return False

        if (now - self._last_unstable_time) < OBD_STABILIZATION_DELAY:
            logger.warning(
                "[OBD] clear_dtc() REFUSÉ — véhicule instable récemment. "
                f"Attendez {OBD_STABILIZATION_DELAY}s après arrêt."
            )
            return False

        try:
            logger.warning(
                "[OBD] ATTENTION : Effacement des codes défauts (Mode 04) — "
                "remet à zéro les moniteurs ECU."
            )
            response = self.connection.query(obd.commands.CLEAR_DTC)
            success = not response.is_null()
            if success:
                logger.info("[OBD] DTC effacés avec succès.")
            return success
        except Exception as e:
            logger.error(f"[OBD] Erreur effacement DTC : {e}")
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # State Machine
    # ──────────────────────────────────────────────────────────────────────────

    def _update_vehicle_state_machine(self) -> None:
        """
        Gère la Vehicle Stability State Machine.
        Calcule l'état ECU global.
        États : STARTING -> CRITICAL -> DEGRADED -> TRANSIENT -> STABLE
        """
        tension = self._live_snapshot.get("tension")
        voltage_drop = isinstance(tension, (int, float)) and tension < DEGRADED_VOLTAGE_THRESHOLD
        hardware_faults = self._global_errors > 0

        # Règle d'Entrée (Hystérésis Mode Dégradé)
        if voltage_drop or hardware_faults:
            self._degraded_recovery_counter = 0  # reset compteur de guérison
            if not self.is_degraded_mode:
                logger.warning(
                    "[OBD] ⚠️ PASSAGE EN MODE DÉGRADÉ "
                    f"(tension_basse={voltage_drop}, hw_faults={hardware_faults}) — Limite à 3 PIDs max."
                )
                self.is_degraded_mode = True
                self.action_queue.put({
                    "type": "speak",
                    "text": "Mode dégradé activé. Diagnostic limité."
                })
        else:
            # S'il y a un retour à la normale potentiel (Hystérésis)
            if self.is_degraded_mode:
                voltage_recovered = isinstance(tension, (int, float)) and tension > DEGRADED_VOLTAGE_RECOVERY_THRESHOLD
                if voltage_recovered and not hardware_faults:
                    self._degraded_recovery_counter += 1
                    if self._degraded_recovery_counter >= DEGRADED_RECOVERY_CYCLES:
                        logger.info("[OBD] Rétablissement au Mode Normal confirmé (Hystérésis atteinte).")
                        self.is_degraded_mode = False
                        self._degraded_recovery_counter = 0
                        self.action_queue.put({
                            "type": "speak",
                            "text": "Tension stabilisée. Mode dégradé levé."
                        })
                else:
                    self._degraded_recovery_counter = 0

        # Evaluation State Machine Véhicule Global
        if self._iteration < 5:
            self.vehicle_state = "STARTING"
            return
            
        if hardware_faults:
            self.vehicle_state = "CRITICAL"
            return
            
        if self.is_degraded_mode:
            self.vehicle_state = "DEGRADED"
            return
            
        vitesse = self._live_snapshot.get("vitesse", 0)
        regime = self._live_snapshot.get("regime", 0)
        
        is_moving = isinstance(vitesse, (int, float)) and vitesse > 0
        is_high_rpm = isinstance(regime, (int, float)) and regime > OBD_IDLE_RPM_THRESHOLD
        
        if is_moving or is_high_rpm:
            self.vehicle_state = "TRANSIENT"
        else:
            now = time.time()
            if (now - self._last_unstable_time) >= OBD_STABILIZATION_DELAY:
                self.vehicle_state = "STABLE"
            else:
                self.vehicle_state = "TRANSIENT"

    # ──────────────────────────────────────────────────────────────────────────
    # Boucle principale
    # ──────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Boucle principale du thread d'acquisition OBD-II.

        Comportement :
          1. Si déconnecté → tentative de connexion avec backoff exponentiel
          2. Si connecté   → exécution du cycle de PIDs selon le time-slicing
          3. Vérification watchdog à chaque itération
          4. Mise à jour atomique du shared_state
          5. Attente OBD_CYCLE_CRITICAL_INTERVAL avant la prochaine itération

        Le thread continue à fonctionner même si un PID échoue :
        seul un échec systémique (N erreurs consécutives globales)
        ou un freeze watchdog déclenche une reconnexion.
        """
        logger.info("[OBD] Démarrage du thread d'acquisition (time-slicing v2.1).")

        while not self.event_stop.is_set():

            # ── Reconnexion ──────────────────────────────────────────────────
            if not self.connected:
                with self.state_lock:
                    self.shared_state["statut_obd"] = "déconnecté"

                delay = self._backoff.next_delay()
                logger.info(
                    f"[OBD] Tentative de reconnexion dans {delay:.0f}s "
                    f"(essai #{self._backoff.attempt_count})..."
                )
                # Attente interruptible (respecte event_stop)
                if self.event_stop.wait(timeout=delay):
                    break

                if not self.connect():
                    continue

            # ── Watchdog ─────────────────────────────────────────────────────
            if self._watchdog.is_frozen():
                logger.warning(
                    "[OBD] Watchdog déclenché — ELM327 potentiellement gelé. "
                    "Forçage de la reconnexion."
                )
                self.connected = False
                if self.connection:
                    try:
                        self.connection.close()
                    except Exception:
                        pass
                    self.connection = None
                self._watchdog.stop()
                continue

            # ── State Machine Véhicule ───────────────────────────────────────
            self._update_vehicle_state_machine()

            # ── Cycle de lecture ─────────────────────────────────────────────
            try:
                active_cycle = self._read_cycle()
                self._update_engine_state()

                # DTC : lecture toutes les 30 itérations critiques
                dtcs: List[str] = []
                if self._iteration % OBD_CYCLE_OPTIONAL_EVERY == 0:
                    dtcs = self.get_dtc()
                    # Mémoriser pour les cycles intermédiaires
                    with self.state_lock:
                        self.shared_state["dtcs"] = dtcs
                else:
                    with self.state_lock:
                        dtcs = list(self.shared_state.get("dtcs", []))

                # Normalisation IA (uniquement si des données existent)
                ai_snapshot: Optional[Dict[str, Any]] = None
                if self._normalizer and self._live_snapshot:
                    safety_meta = self._pid_tracker.get_stats()
                    safety_meta["cycle_actuel"] = active_cycle
                    safety_meta["iteration"]    = self._iteration
                    safety_meta["erreurs_consecutives"] = self._global_errors
                    safety_meta["mode_degrade"] = self.is_degraded_mode
                    safety_meta["vehicle_state"] = self.vehicle_state
                    ai_snapshot = self._normalizer.normalize(
                        self._live_snapshot, dtcs, meta=safety_meta
                    )

                # Mise à jour atomique du shared_state
                with self.state_lock:
                    self.shared_state["statut_obd"] = "connecté (dégradé)" if self.is_degraded_mode else "connecté"
                    self.shared_state["obd_data"]   = dict(self._live_snapshot)
                    if ai_snapshot:
                        self.shared_state["obd_snapshot_ia"] = ai_snapshot

                self._iteration += 1

            except Exception as e:
                logger.error(f"[OBD] Erreur inattendue dans la boucle : {e}")
                self._global_errors += 1
                if self._global_errors >= OBD_GLOBAL_ERROR_THRESHOLD:
                    self.connected = False

            # ── Pause inter-cycles ───────────────────────────────────────────
            wait_time = OBD_DEGRADED_MODE_INTERVAL if self.is_degraded_mode else OBD_CYCLE_CRITICAL_INTERVAL
            self.event_stop.wait(timeout=wait_time)

        # ── Nettoyage à l'arrêt ──────────────────────────────────────────────
        self._watchdog.stop()
        if self.connection and self.connection.is_connected():
            try:
                self.connection.close()
            except Exception:
                pass
        logger.info("[OBD] Thread OBD arrêté proprement.")
