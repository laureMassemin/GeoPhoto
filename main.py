import base64
import json
import subprocess
import os
from io import BytesIO

from PIL import Image

formatImage = ('.jpg', '.jpeg', '.png')

def scanner_dossier(dossier):
    list_points = []
    list_echecs = []
    for fichier in os.listdir(dossier):
        chemin_ficher = os.path.join(dossier, fichier)
        if os.path.isfile(chemin_ficher) and fichier.lower().endswith(formatImage):
            resultat = scanner_image(chemin_ficher)
            if "raison" in resultat:
                list_echecs.append(resultat)
            else:
                list_points.append(resultat)
        elif os.path.isdir(chemin_ficher):
            points_dossier, echecs_dossier = scanner_dossier(chemin_ficher)
            list_points.extend(points_dossier)
            list_echecs.extend(echecs_dossier)

    return list_points, list_echecs

def extraire_date(valeur_exif):
    if not valeur_exif:
        return None
    try:
        partie_date = valeur_exif.split(" ")[0]
        return partie_date.replace(":", "-")
    except Exception:
        return None

def scanner_image(chemin_image):
    nom_fichier = os.path.basename(chemin_image)
    resultat = subprocess.run(
        ["exiftool", "-gps:all", "-Make", "-Model", "-DateTimeOriginal", "-n", "-json", chemin_image],
        capture_output=True,
        text=True
    )
    if resultat.returncode != 0:
        return {"nom_fichier": nom_fichier, "chemin": chemin_image, "date": None,
                "raison": f"Erreur exiftool : {resultat.stderr.strip()}"}

    try:
        donnees = json.loads(resultat.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return {"nom_fichier": nom_fichier, "chemin": chemin_image, "date": None,
                "raison": "Impossible de lire les métadonnées de l'image"}

    date = extraire_date(donnees.get("DateTimeOriginal"))

    if "GPSLatitude" not in donnees or "GPSLongitude" not in donnees:
        marque, modele = donnees.get("Make"), donnees.get("Model")
        if modele and marque and modele.lower().startswith(marque.lower()):
            appareil = modele
        else:
            appareil = " ".join(part for part in [marque, modele] if part).strip()
        raison = f"Photo prise avec {appareil} — pas de GPS" if appareil else "Aucune donnée GPS dans les métadonnées EXIF"
        return {"nom_fichier": nom_fichier, "chemin": chemin_image, "date": date, "raison": raison}

    return {
        "nom_fichier": nom_fichier,
        "chemin": chemin_image,
        "date": date,
        "latitude": donnees["GPSLatitude"],
        "longitude": donnees["GPSLongitude"],
    }

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
            <li class="ligne-echec" data-date="{echec["date"] or ""}">
                {img_html}
                <div class="ligne-echec-texte">
                    <div class="nom-fichier">{echec["nom_fichier"]}</div>
                    <div class="raison">{echec["raison"]}</div>
                </div>
            </li>'''

    return f'<ul class="liste-echecs">{lignes}</ul>'

def generer_page(points, echecs, chemin_sortie):
    points_js = [{
        "lat": p["latitude"],
        "lon": p["longitude"],
        "nom": p["nom_fichier"],
        "date": p["date"],
        "img": image_vers_base64(p["chemin"]),
    } for p in points]
    points_json = json.dumps(points_js)

    dates_disponibles = sorted({p["date"] for p in points if p["date"]} | {e["date"] for e in echecs if e["date"]})
    date_min, date_max = (dates_disponibles[0], dates_disponibles[-1]) if dates_disponibles else ("", "")
    attrs_filtre = f'min="{date_min}" max="{date_max}"' if date_min else "disabled"

    html_echecs = generer_html_echecs(echecs)

    page_html = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carte des photos</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
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
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
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
    .filtre {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .filtre input[type="date"], .filtre button {{
        font: inherit;
        font-size: 13px;
        padding: 6px 10px;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: var(--bg);
        color: var(--text);
    }}
    .filtre button {{ cursor: pointer; }}
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
    #map {{
        width: 100%;
        height: 100%;
        border: 1px solid var(--border);
        border-radius: 6px;
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
        #map {{ height: 400px; }}
    }}
</style>
</head>
<body>
    <header>
        <div>
            <h1>Carte des photos</h1>
            <p><span id="compte-localisees">{len(points)}</span> localisée(s) · <span id="compte-non-localisees">{len(echecs)}</span> non localisée(s)</p>
        </div>
        <div class="filtre">
            <input type="date" id="filtre-date" {attrs_filtre}>
            <button type="button" id="reset-filtre">Toutes les dates</button>
        </div>
    </header>
    <div class="layout">
        <div class="colonne-carte">
            <div id="map"></div>
        </div>
        <div class="colonne-echecs">
            <h2>Photos non localisées (<span id="compte-non-localisees-liste">{len(echecs)}</span>)</h2>
            {html_echecs}
        </div>
    </div>
    <script>
        const points = {points_json};
        const carte = L.map('map');
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; OpenStreetMap &copy; CARTO',
            maxZoom: 19
        }}).addTo(carte);

        const marqueurs = points.map(p => {{
            const marker = L.marker([p.lat, p.lon]);
            const popupHtml = p.img
                ? `<div style="text-align:center"><img src="data:image/jpeg;base64,${{p.img}}" style="max-width:220px;border-radius:8px"><br><span style="font-size:13px;font-weight:600">${{p.nom}}</span></div>`
                : p.nom;
            marker.bindPopup(popupHtml);
            return {{ marker, date: p.date }};
        }});

        if (marqueurs.length) {{
            carte.fitBounds(L.featureGroup(marqueurs.map(m => m.marker)).getBounds().pad(0.15));
        }} else {{
            carte.setView([20, 0], 2);
        }}

        function appliquerFiltre(dateSelectionnee) {{
            let compteCarte = 0, compteListe = 0;
            marqueurs.forEach(m => {{
                const visible = !dateSelectionnee || !m.date || m.date === dateSelectionnee;
                if (visible) {{
                    if (!carte.hasLayer(m.marker)) m.marker.addTo(carte);
                    compteCarte++;
                }} else if (carte.hasLayer(m.marker)) {{
                    carte.removeLayer(m.marker);
                }}
            }});
            document.querySelectorAll('.ligne-echec').forEach(li => {{
                const d = li.dataset.date || '';
                const visible = !dateSelectionnee || !d || d === dateSelectionnee;
                li.style.display = visible ? '' : 'none';
                if (visible) compteListe++;
            }});
            document.getElementById('compte-localisees').textContent = compteCarte;
            document.getElementById('compte-non-localisees').textContent = compteListe;
            document.getElementById('compte-non-localisees-liste').textContent = compteListe;
        }}

        document.getElementById('filtre-date').addEventListener('change', e => appliquerFiltre(e.target.value));
        document.getElementById('reset-filtre').addEventListener('click', () => {{
            document.getElementById('filtre-date').value = '';
            appliquerFiltre('');
        }});

        appliquerFiltre('');
    </script>
</body>
</html>'''

    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(page_html)

def afficher_echecs(echecs):
    if not echecs:
        return
    print(f"\n{len(echecs)} photo(s) sans localisation :")
    for echec in echecs:
        print(f"  - {echec['nom_fichier']} : {echec['raison']}")

def main():
    dossier = input("Entrez le chemin du dossier à scanner : ")
    points, echecs = scanner_dossier(dossier)
    afficher_echecs(echecs)
    chemin_sortie = input("Entrez le chemin du fichier de sortie pour la carte : ")
    if not chemin_sortie:
        chemin_sortie = "carte.html"
    generer_page(points, echecs, chemin_sortie)

main()
