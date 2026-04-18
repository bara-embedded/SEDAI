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
    
    for node in nodes:
        idx, text, shape, x, y = node
        
        if shape == "ellipse":
            style = "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;"
            width, height = 80, 40
            x_offset = x + 50 
        elif shape == "rhombus":
            style = "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1;"
            width, height = 160, 80
            x_offset = x + 10 
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;strokeColor=#666666;arcSize=20;fontStyle=1;"
            width, height = 180, 60
            x_offset = x
            
        text_encoded = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&#xa;")
        
        node_xml = f'        <mxCell id="{idx}" value="{text_encoded}" style="{style}" vertex="1" parent="1">'
        node_xml += f'<mxGeometry x="{x_offset}" y="{y}" width="{width}" height="{height}" as="geometry" /></mxCell>'
        xml_out.append(node_xml)
        
    edge_idx = 1000
    for edge in edges:
        if len(edge) == 3:
            src, tgt, label = edge
            edge_style = ""
        else:
            src, tgt, label, edge_style = edge
            
        base_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;"
        style = base_style + edge_style
        
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
    X_CENTER = 300
    X_RIGHT = 550
    X_FAR_RIGHT = 800

    # ==========================================
    # SEDAI COMPACT (AVEC RESTITUTION VOCALE CLAIRE)
    # ==========================================
    sedai_nodes = [
        ("A", "DÉBUT", "ellipse", X_CENTER, 30),
        ("B", "Init. Système\n(IA & OBD-II)", "rect", X_CENTER, 110),
        ("C", "Véhicule\nConnecté ?", "rhombus", X_CENTER, 210),
        
        ("D", "Alerte : Connexion Fail\n(Nouvelle tentative)", "rect", X_RIGHT, 220),
        
        ("F", "Connexion Réussie\n(WiFi ON)", "rect", X_CENTER, 330),
        ("G", "Monitoring Temps Réel\n(Lecture Capteurs)", "rect", X_CENTER, 430),
        
        ("H", "Détection\nAnomalie ?", "rhombus", X_CENTER, 530),
        ("I", "Diagnostic IA", "rect", X_RIGHT, 540), # Align with H
        ("I2", "Restitution Vocale\n(Alerte Danger)", "rect", X_RIGHT, 630),
        
        ("J", "Commande\nVocale ?", "rhombus", X_CENTER, 720),
        ("K", "Interprétation IA", "rect", X_RIGHT, 730), # Align with J
        ("K2", "Restitution Vocale\n(Réponse TTS)", "rect", X_RIGHT, 820),
        
        ("L", "Envoi Flux Data\n(WebSocket)", "rect", X_CENTER, 880),
        
        ("M", "Moteur\nCoupé ?", "rhombus", X_CENTER, 980),
        ("N", "Générer Rapport Final", "rect", X_CENTER, 1080),
        ("O", "FIN", "ellipse", X_CENTER, 1180),
    ]

    sedai_edges = [
        ("A", "B", ""),
        ("B", "C", ""),
        
        ("C", "D", "Non", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("D", "C", "Attente 3s", "exitX=0.5;exitY=0;entryX=1;entryY=0.25;"),
        
        ("C", "F", "Oui"),
        ("F", "G", ""),
        ("G", "H", ""),
        
        ("H", "I", "Oui", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("I", "I2", ""),
        ("I2", "J", "", "exitX=0.5;exitY=1;entryX=1;entryY=0.25;"), 
        
        ("H", "J", "Non"),
        
        ("J", "K", "Oui", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("K", "K2", ""),
        ("K2", "L", "", "exitX=0.5;exitY=1;entryX=1;entryY=0.25;"),
        
        ("J", "L", "Non"),
        ("L", "M", ""),
        
        ("M", "G", "Non", "exitX=0;exitY=0.5;entryX=0;entryY=0.5;"),
        
        ("M", "N", "Oui"),
        ("N", "O", ""),
    ]

    build_drawio(sedai_nodes, sedai_edges, "C:/Projects/SEDAI/diagrams/SEDAI_Architecture.drawio")

    build_drawio(sedai_nodes, sedai_edges, "C:/Projects/SEDAI/diagrams/SEDAI_Architecture.drawio")

    # ==========================================
    # APP MOBILE COMPACT (SANS LIGNES QUI SE CROISENT)
    # ==========================================
    app_nodes = [
        ("A", "DÉBUT", "ellipse", X_CENTER, 30),
        ("B", "Lancement de l'App", "rect", X_CENTER, 110),
        ("C", "Premier\nLancement ?", "rhombus", X_CENTER, 210),

        ("D", "Écran Configuration\n(IP, Véhicule...)", "rect", X_RIGHT, 220),

        ("E", "Tableau de Bord HUD", "rect", X_CENTER, 340),
        ("F", "Connexion\nau SEDAI ?", "rhombus", X_CENTER, 440),

        ("G", "Badge Hors Ligne\n(Nouvelle tentative)", "rect", X_RIGHT, 450),

        ("H", "Réception Data Temps Réel\n(Jauges actives)", "rect", X_CENTER, 560),

        ("I", "Action Conducteur ?\n(Diagnostic IA / Micro PTT)", "rhombus", X_CENTER, 660),
        ("I2", "Envoi Commande\nau SEDAI", "rect", X_RIGHT, 670),

        ("J", "Diagnostic reçu\ndu SEDAI ?", "rhombus", X_CENTER, 790),
        ("K", "Ouvrir Écran Analyse IA\n& Sauvegarder Historique", "rect", X_RIGHT, 800),

        ("L", "App\nFermée ?", "rhombus", X_CENTER, 920),

        ("M", "Clôture Connexion", "ellipse", X_CENTER, 1020),
    ]

    app_edges = [
        ("A", "B", ""),
        ("B", "C", ""),

        ("C", "D", "Oui", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("D", "E", "", "exitX=0.5;exitY=1;entryX=1;entryY=0.5;"),

        ("C", "E", "Non"),
        ("E", "F", ""),

        ("F", "G", "Non", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("G", "F", "Attente 3s", "exitX=0.5;exitY=0;entryX=1;entryY=0.25;"),

        ("F", "H", "Oui (Connecté)"),
        ("H", "I", ""),

        ("I", "I2", "Oui", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("I2", "J", "", "exitX=0.5;exitY=1;entryX=1;entryY=0.5;"),

        ("I", "J", "Non"),

        ("J", "K", "Oui", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
        ("K", "L", "", "exitX=0.5;exitY=1;entryX=1;entryY=0.5;"),

        ("J", "L", "Non"),

        ("L", "H", "Non", "exitX=0;exitY=0.5;entryX=0;entryY=0.5;"),

        ("L", "M", "Oui (Fermeture)"),
    ]

    build_drawio(app_nodes, app_edges, "C:/Projects/auto_japan_app/diagrams/Application_Mobile_Architecture.drawio")

    print("Drawio COMPACT files successfully generated!")
