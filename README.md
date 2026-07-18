# Geo Project

Scanne un dossier de photos, extrait leur position GPS depuis les métadonnées EXIF, et génère une carte HTML interactive. Les photos sans position sont listées à part avec la raison de l'échec.

## Fonctionnalités

- Scan récursif d'un dossier (`.jpg`, `.jpeg`, `.png`)
- Extraction des coordonnées GPS et de la date de prise de vue via `exiftool`
- Carte interactive (Leaflet) avec un marqueur par photo localisée, popup avec vignette de la photo
- Liste des photos non localisées avec la raison précise (appareil sans GPS, pas de métadonnées, erreur de lecture...)
- Filtre par date : un sélecteur de calendrier filtre à la fois la carte et la liste des échecs sur une date donnée
- Page HTML unique, autonome (images encodées en base64, pas de fichiers externes à part les CDN Leaflet)

## Prérequis

- Python 3
- [exiftool](https://exiftool.org/) installé sur le système :
  ```
  brew install exiftool
  ```
- Le module Python Pillow :
  ```
  pip install pillow
  ```

## Utilisation

```
python3 main.py
```

Le script demande :
1. Le chemin du dossier à scanner
2. Le chemin du fichier HTML de sortie (par défaut `carte.html` si laissé vide)

Ouvrez ensuite le fichier généré dans un navigateur.

## Pourquoi certaines photos ne sont pas localisées ?

- **Appareil sans GPS** : certains appareils photo (compacts, reflex) n'ont pas de module GPS et n'enregistrent jamais de position, même s'ils écrivent un bloc GPS vide dans l'EXIF.
- **Pas de métadonnées** : les captures d'écran ou fichiers PNG ne contiennent généralement aucune métadonnée EXIF exploitable.
- **Erreur de lecture** : le fichier est corrompu ou illisible par `exiftool`.

Dans tous ces cas, la donnée GPS n'existe pas dans le fichier — ce n'est pas un problème d'extraction.
