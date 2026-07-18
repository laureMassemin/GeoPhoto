import base64
import json
import subprocess
import os
from io import BytesIO

import folium
from PIL import Image

formatImage = ('.jpg', '.jpeg', '.png')

def scanner_dossier(dossier):
    list_points = []
    list_echecs = []
    for fichier in os.listdir(dossier):
        chemin_ficher = os.path.join(dossier, fichier)
        if os.path.isfile(chemin_ficher) and fichier.lower().endswith(formatImage):
            resultat_scan, raison_echec = scanner_image(chemin_ficher)
            if resultat_scan is not None:
                list_points.append(resultat_scan)
            else:
                list_echecs.append({
                    "nom_fichier": os.path.basename(chemin_ficher),
                    "chemin": chemin_ficher,
                    "raison": raison_echec,
                })
        elif os.path.isdir(chemin_ficher):
            points_dossier, echecs_dossier = scanner_dossier(chemin_ficher)
            list_points.extend(points_dossier)
            list_echecs.extend(echecs_dossier)

    return list_points, list_echecs

def scanner_image(chemin_image):
    resultat = subprocess.run(
        ["exiftool", "-gps:all", "-Make", "-Model", "-n", "-json", chemin_image],
        capture_output=True,
        text=True
    )
    if resultat.returncode != 0:
        return None, f"Erreur exiftool : {resultat.stderr.strip()}"

    try:
        donnees = json.loads(resultat.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return None, "Impossible de lire les métadonnées de l'image"

    if "GPSLatitude" not in donnees or "GPSLongitude" not in donnees:
        marque, modele = donnees.get("Make"), donnees.get("Model")
        if modele and marque and modele.lower().startswith(marque.lower()):
            appareil = modele
        else:
            appareil = " ".join(part for part in [marque, modele] if part).strip()
        if appareil:
            return None, f"Photo prise avec {appareil} — pas de GPS"
        return None, "Aucune donnée GPS dans les métadonnées EXIF"

    return {
        "nom_fichier": os.path.basename(chemin_image),
        "chemin": chemin_image,
        "latitude": donnees["GPSLatitude"],
        "longitude": donnees["GPSLongitude"],
    }, None

def image_vers_base64(chemin_image, largeur_max=400):
    try:
        with Image.open(chemin_image) as img:
            img = img.convert("RGB")
            if img.width > largeur_max:
                ratio = largeur_max / img.width
                img = img.resize((largeur_max, int(img.height * ratio)))
            tampon = BytesIO()
            img.save(tampon, format="JPEG", quality=70)
            return base64.b64encode(tampon.getvalue()).decode("utf-8")
    except Exception:
        return None

def generer_carte(points):
    lat_moyenne = sum(p["latitude"] for p in points) / len(points)
    lon_moyenne = sum(p["longitude"] for p in points) / len(points)
    carte = folium.Map(location=[lat_moyenne, lon_moyenne], zoom_start=6, tiles="CartoDB positron")

    for point in points:
        b64 = image_vers_base64(point["chemin"])
        if b64:
            popup_html = f'''
                <div style="text-align:center;font-family:-apple-system,sans-serif">
                    <img src="data:image/jpeg;base64,{b64}" style="max-width:250px;border-radius:10px"><br>
                    <span style="font-size:13px;font-weight:600">{point["nom_fichier"]}</span>
                </div>'''
            popup = folium.Popup(popup_html, max_width=300)
        else:
            popup = point["nom_fichier"]
        folium.Marker(
            location=[point["latitude"], point["longitude"]],
            popup=popup,
            tooltip=point["nom_fichier"],
            icon=folium.Icon(color="cadetblue", icon="camera", prefix="fa"),
        ).add_to(carte)

    return carte

def generer_carte_html(points):
    if not points:
        return '<div class="vide">Aucune coordonnée GPS trouvée parmi les photos scannées.</div>'
    carte_html = generer_carte(points).get_root().render()
    b64_carte = base64.b64encode(carte_html.encode("utf-8")).decode("utf-8")
    return f'<iframe class="carte-frame" src="data:text/html;charset=utf-8;base64,{b64_carte}"></iframe>'

def generer_html_echecs(echecs):
    if not echecs:
        return '<div class="vide">Toutes les photos ont été localisées.</div>'

    lignes = ""
    for echec in echecs:
        b64 = image_vers_base64(echec["chemin"], largeur_max=120)
        if b64:
            img_html = f'<img src="data:image/jpeg;base64,{b64}" class="miniature">'
        else:
            img_html = '<div class="miniature miniature-vide"></div>'
        lignes += f'''
            <li class="ligne-echec">
                {img_html}
                <div class="ligne-echec-texte">
                    <div class="nom-fichier">{echec["nom_fichier"]}</div>
                    <div class="raison">{echec["raison"]}</div>
                </div>
            </li>'''

    return f'<ul class="liste-echecs">{lignes}</ul>'

def generer_page(points, echecs, chemin_sortie):
    page_html = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carte des photos</title>
<style>
    :root {{
        --bg: #ffffff;
        --text: #1a1a1a;
        --text-muted: #6b7280;
        --border: #e5e7eb;
    }}
    @media (prefers-color-scheme: dark) {{
        :root {{
            --bg: #1e1e1e;
            --text: #e5e5e5;
            --text-muted: #9ca3af;
            --border: #3a3a3a;
        }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
    }}
    header {{
        padding: 16px 20px;
        border-bottom: 1px solid var(--border);
    }}
    header h1 {{
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }}
    header p {{
        margin: 4px 0 0;
        font-size: 13px;
        color: var(--text-muted);
    }}
    .layout {{
        display: flex;
        align-items: stretch;
        height: calc(100vh - 65px);
    }}
    .colonne-carte {{
        flex: 1 1 65%;
        padding: 16px;
    }}
    .colonne-echecs {{
        flex: 0 0 340px;
        border-left: 1px solid var(--border);
        padding: 16px;
        overflow-y: auto;
    }}
    .colonne-echecs h2 {{
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 12px;
    }}
    .carte-frame {{
        width: 100%;
        height: 100%;
        border: 1px solid var(--border);
        border-radius: 6px;
        display: block;
    }}
    .vide {{
        color: var(--text-muted);
        font-size: 13px;
        padding: 20px 0;
    }}
    .liste-echecs {{
        list-style: none;
        margin: 0;
        padding: 0;
    }}
    .ligne-echec {{
        display: flex;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid var(--border);
    }}
    .ligne-echec:last-child {{ border-bottom: none; }}
    .miniature {{
        width: 52px;
        height: 52px;
        object-fit: cover;
        border-radius: 4px;
        flex-shrink: 0;
    }}
    .miniature-vide {{ background: var(--border); }}
    .ligne-echec-texte {{ min-width: 0; }}
    .nom-fichier {{
        font-size: 13px;
        font-weight: 500;
        word-break: break-all;
    }}
    .raison {{
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 2px;
    }}
    @media (max-width: 720px) {{
        .layout {{ flex-direction: column; height: auto; }}
        .colonne-echecs {{ flex: none; border-left: none; border-top: 1px solid var(--border); }}
        .carte-frame {{ height: 400px; }}
    }}
</style>
</head>
<body>
    <header>
        <h1>Carte des photos</h1>
        <p>{len(points)} localisée{'s' if len(points) != 1 else ''} · {len(echecs)} non localisée{'s' if len(echecs) != 1 else ''}</p>
    </header>
    <div class="layout">
        <div class="colonne-carte">
            {generer_carte_html(points)}
        </div>
        <div class="colonne-echecs">
            <h2>Photos non localisées ({len(echecs)})</h2>
            {generer_html_echecs(echecs)}
        </div>
    </div>
</body>
</html>'''

    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(page_html)

def main():
    dossier = input("Entrez le chemin du dossier à scanner : ")
    points, echecs = scanner_dossier(dossier)
    chemin_sortie = input("Entrez le chemin du fichier de sortie pour la carte : ")
    if not chemin_sortie:
        chemin_sortie = "carte.html"
    generer_page(points, echecs, chemin_sortie)

main()
