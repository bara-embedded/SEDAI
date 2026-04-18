"""
ws_module.py — Serveur WebSocket bidirectionnel
Assure la communication avec l'application Flutter sans utiliser asyncio.
- Envoie les paramètres en temps réel à la fréquence WS_SEND_INTERVAL.
- Reçoit les actions (voice_activate, infos véhicule, commandes OBD).
"""

import threading
import json
import time
import queue
from typing import Dict, Any

try:
    from websockets.sync.server import serve, ServerConnection
    import websockets.exceptions
except ImportError:
    serve, ServerConnection = None, None

from config import *

class WebSocketModule(threading.Thread):
    """
    Module réseau synchrone (threadé) gérant un port bidirectionnel pour Flutter.
    """
    
    def __init__(self, shared_state: Dict[str, Any], state_lock: threading.Lock,
                 action_queue: queue.Queue, event_voice_active: threading.Event,
                 event_stop: threading.Event, obd_module: Any = None):
        """
        Initialise le serveur.
        """
        super().__init__(daemon=True)
        self.shared_state = shared_state
        self.state_lock = state_lock
        self.action_queue = action_queue
        self.event_voice_active = event_voice_active
        self.event_stop = event_stop
        self.obd_module = obd_module
        
        self.clients_lock = threading.Lock()
        self.clients = set()
        self._server = None

    def broadcast_loop(self) -> None:
        """
        Boucle d'arrière-plan : envoie l'état OBD et le snapshot IA au client Flutter.

        Le payload contient :
          - statut_obd, dtcs       : état de connexion et codes défauts
          - données OBD brutes     : valeurs clés (régime, temp, vitesse...)
          - snapshot_ia (optionnel): snapshot normalisé complet avec features IA
          - rapport (optionnel)    : dernier rapport vocal généré
        """
        print("[WEBSOCKET] Démarrage du sous-thread d'envoi en continu.")

        while not self.event_stop.is_set():
            if self.event_stop.wait(WS_SEND_INTERVAL):
                break

            with self.clients_lock:
                if not self.clients:
                    continue

            with self.state_lock:
                obd_status      = self.shared_state.get("statut_obd", "déconnecté")
                obd_data        = dict(self.shared_state.get("obd_data", {}))
                dtcs            = list(self.shared_state.get("dtcs", []))
                dernier_rapport = self.shared_state.get("dernier_rapport")
                # Snapshot IA normalisé (disponible dès le 1er cycle critique)
                ai_snapshot     = self.shared_state.get("obd_snapshot_ia")

            payload = {
                "statut_obd": obd_status,
                "dtcs": dtcs,
            }

            # Données OBD brutes (rétro-compatibilité Flutter)
            if obd_data:
                payload.update(obd_data)

            # Snapshot IA enrichi (features + score de risque)
            if ai_snapshot:
                payload["snapshot_ia"] = {
                    "features":     ai_snapshot.get("features_ia", {}),
                    "meta":         ai_snapshot.get("meta", {}),
                    "timestamp":    ai_snapshot.get("timestamp", ""),
                }

            if dernier_rapport:
                payload["rapport"] = dernier_rapport.get("texte", "")
                
            message_str = json.dumps(payload, ensure_ascii=False)
            
            dead_clients = set()
            with self.clients_lock:
                for client in self.clients:
                    try:
                        client.send(message_str)
                    except Exception:
                        dead_clients.add(client)
                        
                for dc in dead_clients:
                    self.clients.discard(dc)

    def handle_client(self, websocket: Any) -> None:
        """
        Gère la réception des commandes pour un client Flutter.
        """
        print(f"[WEBSOCKET] Client connecté : {websocket.remote_address}")
        
        with self.clients_lock:
            self.clients.add(websocket)
            
        try:
            for message in websocket:
                if self.event_stop.is_set():
                    break
                    
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                    
                cmd = data.get("command") or data.get("action")
                
                if cmd == "voice_activate":
                    print("[WEBSOCKET] Action : Activation du Push-To-Talk auto.")
                    self.event_voice_active.set()
                    
                elif cmd == "voice_deactivate":
                    print("[WEBSOCKET] Action : Désactivation du Push-To-Talk.")
                    self.event_voice_active.clear()
                    
                elif cmd == "diagnose":
                    print("[WEBSOCKET] Demande manuel d'un diagnostic système complet.")
                    self.action_queue.put({
                        "type": "diagnostic_request",
                        "source": "smartphone (Flutter)",
                        "text": "Le conducteur a demandé un rapport complet de l'état actuel de la mécanique via son téléphone."
                    })
                    
                elif cmd == "vehicle_info":
                    infos = data.get("data", {})
                    if infos:
                        with self.state_lock:
                            self.shared_state["vehicle_info"] = infos
                        print(f"[WEBSOCKET] Informations véhicule réceptionnées : {infos.get('marque')} {infos.get('modele')}")
                        
                elif cmd == "get_dtcs":
                    print("[WEBSOCKET] Vérification à la volée des DTC en cours...")
                    if self.obd_module:
                        # On lit la liste (la boucle de obd_module stockera le résultat automatiquement)
                        self.obd_module.get_dtc()
                        
                elif cmd == "clear_dtcs":
                    user_confirmed = data.get("user_confirmed", False)
                    if not user_confirmed:
                        print("[WEBSOCKET] REFUSÉ : Effacement des DTC demandé sans confirmation explicite (user_confirmed=False).")
                    else:
                        print("[WEBSOCKET] Ordre d'effacement mémoire des DTC (confirmé par l'utilisateur).")
                        if self.obd_module:
                            self.obd_module.clear_dtc(confirmed=True)
                        
                elif cmd == "set_volume":
                    level = data.get("level", 60)
                    print(f"[WEBSOCKET] Changement de volume global demandé: {level}%")
                    try:
                        import subprocess
                        # On récupère tous les sous-contrôles de la carte USB
                        result = subprocess.check_output(["amixer", "-c", "2", "scontrols"], stderr=subprocess.STDOUT)
                        controls = result.decode().splitlines()
                        for line in controls:
                            if "'" in line:
                                control_name = line.split("'")[1]
                                subprocess.run(["amixer", "-c", "2", "sset", control_name, f"{int(level)}%", "unmute"], 
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # Sauvegarde physique pour le prochain démarrage
                        import os
                        volume_file = os.path.join(os.path.dirname(__file__), "volume_state.txt")
                        with open(volume_file, "w") as f:
                            f.write(str(int(level)))
                            
                        print(f"[WEBSOCKET] Volume matériel ajusté et sauvegardé localement à {level}%.")
                    except Exception as e:
                        print(f"[WEBSOCKET] Erreur lors du changement de volume : {e}")
                        
        except Exception:
            pass # Les fermetures de connexion génèrent logiquement une exception standard
        finally:
            print(f"[WEBSOCKET] Disparition d'un client de la socket.")
            with self.clients_lock:
                self.clients.discard(websocket)

    def run(self) -> None:
        """Démarre le serveur et son Broadcaster associé."""
        if serve is None:
            print("[WEBSOCKET] ERREUR : API synchrones (websockets >= 10.0) requises non trouvées.")
            print("[WEBSOCKET] Lancez 'pip install websockets'")
            return
            
        print(f"[WEBSOCKET] Lancement du serveur sur {WS_HOST}:{WS_PORT}")
        broadcaster = threading.Thread(target=self.broadcast_loop, daemon=True)
        broadcaster.start()
        
        try:
            with serve(self.handle_client, WS_HOST, WS_PORT) as server:
                self._server = server
                # serve_forever bloque l'exécution jusqu'à server.shutdown()
                server.serve_forever()
        except Exception as e:
            print(f"[WEBSOCKET] Erreur critique serveur WebSockets : {e}")
        finally:
            print("[WEBSOCKET] Fin du thread Serveur bidirectionnel.")
