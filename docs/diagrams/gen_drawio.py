import sys

def build_drawio(nodes, edges, filename):
    xml_out = []
    xml_out.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_out.append('<mxfile>')
    xml_out.append('  <diagram id="diagram_id" name="Page-1">')
    xml_out.append('    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">')
    xml_out.append('      <root>')
    xml_out.append('        <mxCell id="0" />')
    xml_out.append('        <mxCell id="1" parent="0" />')
    
    # Process Nodes
    y_starts = {}
    for node in nodes:
        idx, text, shape, x, y = node
        
        style = ""
        width, height = 180, 60
        
        if shape == "ellipse":
            style = "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
            width, height = 80, 40
        elif shape == "rhombus":
            style = "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
            width, height = 160, 80
        else:
            style = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;strokeColor=#666666;"
            
        # Drawio encoding for text
        text_encoded = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&#xa;")
        
        node_xml = f'        <mxCell id="{idx}" value="{text_encoded}" style="{style}" vertex="1" parent="1">'
        node_xml += f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" /></mxCell>'
        xml_out.append(node_xml)
        
    # Process Edges
    edge_idx = 1000
    for edge in edges:
        src, tgt, label = edge
        style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;"
        label_encoded = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        edge_xml = f'        <mxCell id="e{edge_idx}" value="{label_encoded}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
        edge_xml += f'<mxGeometry relative="1" as="geometry" /></mxCell>'
        xml_out.append(edge_xml)
        edge_idx += 1
        
    xml_out.append('      </root>')
    xml_out.append('    </mxGraphModel>')
    xml_out.append('  </diagram>')
    xml_out.append('</mxfile>')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_out))


if __name__ == "__main__":
    # ---------------- SEDAI ----------------
    sedai_nodes = [
        ("A", "Début", "ellipse", 400, 50),
        ("B", "Démarrage du boîtier SEDAI", "rect", 400, 150),
        ("C", "Chargement du moteur\nd'Intelligence Artificielle", "rect", 400, 250),
        ("D", "Tentative de connexion\nà la prise OBD-II", "rect", 400, 350),
        ("E", "Connexion établie ?", "rhombus", 400, 450),
        
        ("F", "Alerte vocale :\nVéhicule non détecté", "rect", 700, 460),
        ("G", "Fin", "ellipse", 740, 580),
        
        ("H", "Alerte vocale :\nSystème opérationnel", "rect", 400, 580),
        ("I", "Création réseau local WiFi", "rect", 400, 680),
        
        ("J", "Véhicule en marche ?", "rhombus", 400, 780),
        
        ("V", "Enregistrement du rapport final", "rect", 700, 790),
        ("W", "Extinction du système SEDAI", "rect", 700, 890),
        ("X", "Fin", "ellipse", 740, 990),
        
        ("K", "Lecture capteurs moteur temps réel", "rect", 400, 910),
        ("L", "Vérification des erreurs", "rect", 400, 1010),
        ("M", "Pannes détectées ?", "rhombus", 400, 1110),
        
        ("N", "L'IA analyse le problème", "rect", 150, 1120),
        ("O", "Alerte vocale de danger", "rect", 150, 1220),
        ("P", "Transmission du danger\nà l'Application", "rect", 150, 1320),
        
        ("Q", "Commande vocale du conducteur ?", "rhombus", 400, 1420),
        
        ("R", "L'IA interprète la requête vocale", "rect", 700, 1430),
        ("S", "Déduction consigne et action", "rect", 700, 1530),
        ("T", "Réponse à haute voix", "rect", 700, 1630),
        
        ("U", "Envoi des données (WebSocket)", "rect", 400, 1750),
    ]

    sedai_edges = [
        ("A", "B", ""),
        ("B", "C", ""),
        ("C", "D", ""),
        ("D", "E", ""),
        
        ("E", "F", "Non"),
        ("F", "G", ""),
        
        ("E", "H", "Oui"),
        ("H", "I", ""),
        ("I", "J", ""),
        
        ("J", "V", "Non"),
        ("V", "W", ""),
        ("W", "X", ""),
        
        ("J", "K", "Oui"),
        ("K", "L", ""),
        ("L", "M", ""),
        
        ("M", "N", "Oui"),
        ("N", "O", ""),
        ("O", "P", ""),
        ("P", "Q", ""),
        
        ("M", "Q", "Non"),
        
        ("Q", "R", "Oui"),
        ("R", "S", ""),
        ("S", "T", ""),
        ("T", "U", ""),
        
        ("Q", "U", "Non"),
        
        ("U", "J", "Boucle"),
    ]

    build_drawio(sedai_nodes, sedai_edges, "C:/Projects/SEDAI/diagrams/SEDAI_Architecture.drawio")

    # ---------------- APP ----------------
    app_nodes = [
        ("A", "Début", "ellipse", 400, 50),
        ("B", "Lancement de l'Application", "rect", 400, 150),
        ("C", "Premier lancement ?", "rhombus", 400, 250),
        
        ("D", "Afficher Configuration", "rect", 150, 260),
        ("E", "Saisie marque, modèle", "rect", 150, 360),
        ("F", "Sauvegarde des préférences", "rect", 150, 460),
        
        ("G", "Affichage Tableau de Bord\nHUD Principal", "rect", 400, 560),
        
        ("H", "Tentative connexion\nau réseau WiFi SEDAI", "rect", 400, 680),
        ("I", "Boîtier introuvable ?", "rhombus", 400, 780),
        
        ("J", "Statut : Connexion échouée", "rect", 700, 790),
        ("K", "Affichage erreur", "rect", 700, 890),
        ("L", "Reconnexion...", "ellipse", 740, 990),
        
        ("M", "Statut : En Ligne", "rect", 400, 910),
        ("N", "Ouverture flux WebSocket", "rect", 400, 1010),
        ("O", "Application ouverte ?", "rhombus", 400, 1110),
        
        ("P", "Réception constante des données", "rect", 400, 1250),
        ("Q", "Mise à jour Jauges HUD", "rect", 400, 1350),
        ("R", "Alerte critique du SEDAI ?", "rhombus", 400, 1450),
        
        ("S", "Notification Urgence Rouge", "rect", 150, 1460),
        ("T", "L'utilisateur ouvre l'écran d'Analyse", "rect", 150, 1560),
        ("U", "Affichage du rapport IA", "rect", 150, 1660),
        
        ("V", "Menu : Navigation ?", "rhombus", 400, 1780),
        
        ("W", "Menu: Historique des pannes", "rect", 700, 1790),
        ("X", "Menu: Paramètres d'apparence", "rect", 700, 1890),
        
        ("Y", "Clôture connexion réseau", "rect", 400, 1950),
        ("Z", "Fin", "ellipse", 440, 2050),
    ]

    app_edges = [
        ("A", "B", ""),
        ("B", "C", ""),
        
        ("C", "D", "Oui"),
        ("D", "E", ""),
        ("E", "F", ""),
        ("F", "G", ""),
        
        ("C", "G", "Non"),
        ("G", "H", ""),
        ("H", "I", ""),
        
        ("I", "J", "Oui"),
        ("J", "K", ""),
        ("K", "L", ""),
        ("L", "H", "Boucle essai"),
        
        ("I", "M", "Non"),
        ("M", "N", ""),
        ("N", "O", ""),
        
        ("O", "P", "Oui"),
        ("P", "Q", ""),
        ("Q", "R", ""),
        
        ("R", "S", "Oui"),
        ("S", "T", ""),
        ("T", "U", ""),
        ("U", "V", ""),
        
        ("R", "V", "Non"),
        
        ("V", "W", "Clic Historique"),
        ("W", "O", ""),
        
        ("V", "X", "Clic Paramètres"),
        ("X", "O", ""),
        
        ("V", "O", "Rien / Reste sur HUD"),
        
        ("O", "Y", "Non (Fermeture)"),
        ("Y", "Z", ""),
    ]

    build_drawio(app_nodes, app_edges, "C:/Projects/auto_japan_app/diagrams/Application_Mobile_Architecture.drawio")

    print("Drawio files successfully generated!")
