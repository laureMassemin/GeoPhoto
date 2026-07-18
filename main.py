import json
import subprocess
import os
import folium
formatImage = ('.jpg', '.jpeg', '.png')

def scanner_dossier(dossier):
    list_points = []
    for fichier in os.listdir(dossier):
        chemin_ficher = os.path.join(dossier, fichier)
        if os.path.isfile(chemin_ficher) and fichier.lower().endswith(formatImage):
            resultat_scan = scanner_image(chemin_ficher)
            if resultat_scan is not None:
                list_points.append(resultat_scan)
        elif os.path.isdir(chemin_ficher):
            resultat_dossier = scanner_dossier(chemin_ficher)
            if resultat_dossier:
                list_points.extend(resultat_dossier)

    return list_points

def scanner_image(chemin_image):
    resultat = subprocess.run(
        ["exiftool", "-gps:all", "-n", "-json", chemin_image],
        capture_output=True,
        text=True
    )
    if resultat.returncode != 0:
        print(f"Erreur exiftool sur {chemin_image}: {resultat.stderr}")
        return None

    donnees = json.loads(resultat.stdout)[0] 

    if "GPSLatitude" not in donnees or "GPSLongitude" not in donnees:
        return None  

    return {
        "nom_fichier": os.path.basename(chemin_image),
        "latitude": donnees["GPSLatitude"],
        "longitude": donnees["GPSLongitude"],
    }

def generer_carte(points, chemin_sortie):
    if not points:
        print("Aucune coordonnée GPS trouvée. Aucune carte générée.")
        return
    carte = folium.Map(location=[0, 0], zoom_start=2)
    for point in points:
        folium.Marker(location=[point["latitude"], point["longitude"]]).add_to(carte)
    carte.save(chemin_sortie)

def main():
    dossier = input("Entrez le chemin du dossier à scanner : ")
    points = scanner_dossier(dossier)
    chemin_sortie = input("Entrez le chemin du fichier de sortie pour la carte : ")
    if not chemin_sortie:
        chemin_sortie = "carte.html"
    generer_carte(points, chemin_sortie)

main()
