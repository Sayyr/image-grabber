# image-grabber

Boîte à outils Python pour **télécharger des images par mot-clé** depuis plusieurs
sources (Bing, Baidu, Google, Openverse) et **construire des datasets de
classification d'images** propres, étiquetés et prêts à l'entraînement.

Conçu au départ pour un projet de reconnaissance de motos (type → marque → modèle),
mais utilisable pour n'importe quel thème.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [Démarrage rapide](#démarrage-rapide)
- [Les sources](#les-sources)
- [Les scripts en détail](#les-scripts-en-détail)
- [Workflow complet : un dataset de classification](#workflow-complet--un-dataset-de-classification)
- [Fichiers de sortie](#fichiers-de-sortie)
- [Limites connues et pièges](#limites-connues-et-pièges)
- [Licences](#licences)

---

## Fonctionnalités

- Téléchargement par mot-clé depuis **Bing, Baidu, Google** (via `icrawler`) et **Openverse** (API REST).
- **Repli automatique** : si une source ne renvoie rien, les autres prennent le relais.
- **Déduplication** des images identiques (hash de contenu).
- Construction de **gros datasets** en éclatant un thème sur plusieurs mots-clés et plusieurs moteurs.
- Construction de **datasets hiérarchiques** pilotés par un fichier CSV (`type/marque/modèle`), avec génération d'un `labels.csv`.
- **Nettoyage sémantique** des images hors-sujet via CLIP (zero-shot).
- **Découpage train/val/test anti-fuite** : regroupement des quasi-doublons (hash perceptuel) + stratification par classe.
- Filtres au téléchargement : `type=photo` (Bing), taille minimale, redimensionnement.
- Pour Openverse : **filtrage par licence** et génération d'un fichier d'**attribution**.

---

## Installation

Python 3.9+ recommandé.

```bash
# Dépendances de base (téléchargement)
pip install icrawler pillow
# requests est installé avec icrawler

# Dépendances du filtre sémantique (filter_dataset.py)
pip install open_clip_torch torch

# Dépendance du découpage train/val/test (split_dataset.py)
pip install imagehash
```

Lance toujours les scripts **depuis la racine du projet** (le dossier qui contient
`image_grabber/` et `utils/`), sinon Python ne trouvera pas les packages.

---

## Structure du projet

```
image-grabber/                   (racine — lance les scripts depuis ici)
├── image_grabber/
│   ├── __init__.py              (vide — requis pour le package)
│   ├── abstract_grabber.py      contrat commun des sources (grab → nb téléchargé)
│   ├── grab_settings.py         enum des sources + valeurs par défaut
│   ├── google_grabber.py        Google via icrawler + parser sécurisé (anti-crash)
│   ├── bing_grabber.py          Bing via icrawler (filtre type=photo)
│   ├── baidu_grabber.py         Baidu via icrawler
│   ├── openverse_grabber.py     API Openverse (licence ouverte + attributions.csv)
│   ├── image_downloader.py      orchestration : sources, repli, dédup, datasets
│   └── grabbed_image.py         ancien data-holder (hérité, optionnel)
├── utils/
│   ├── __init__.py              (vide — requis pour le package)
│   └── utils.py                 FileUtil (images, dédup), StringUtil, etc.
├── download.py                  CLI : un mot-clé
├── bd_maker.py                  variante française de download.py
├── build_dataset.py             gros dataset : multi-mots-clés + multi-sources + dédup
├── build_moto_dataset.py        dataset hiérarchique piloté par CSV (type/marque/modèle)
├── filter_dataset.py            nettoyage sémantique (CLIP) : garde les vraies images
├── split_dataset.py             audit + découpage train/val/test anti-fuite
├── moto_taxonomy.csv            taxonomie de départ (15 modèles, 3 types)
└── README.md
```

Les dossiers de sortie (`images/`, `dataset_moto/`, …) sont créés à l'exécution.

---

## Démarrage rapide

```bash
# Quelques images sur un mot-clé (Bing par défaut)
python download.py "chat" -l 20

# Un gros dataset autour d'un thème (Bing + Baidu, dédupliqué)
python build_dataset.py "chat" -v chaton "chat noir" "chat persan" -l 5000

# Un dataset hiérarchique de motos depuis le CSV de taxonomie
python build_moto_dataset.py moto_taxonomy.csv -l 1000

# Nettoyer les images hors-sujet
python filter_dataset.py dataset_moto

# Découper en train/val/test (sans fuite)
python split_dataset.py dataset_moto
```

---

## Les sources

| Source     | Moteur        | Fiabilité | Notes |
|------------|---------------|-----------|-------|
| `Bing`     | icrawler      | ✅ bonne  | Source par défaut. Filtre `type=photo` actif. |
| `Baidu`    | icrawler      | ✅ bonne  | Catalogue différent → utile pour grossir un dataset. |
| `Openverse`| API REST      | ✅ bonne  | Licence ouverte uniquement, attribution fournie. Couverture plus mince. |
| `Google`   | icrawler      | ⚠️ instable | Le parser d'icrawler casse souvent → 0 image. Repli auto sur les autres. |

- **`all`** comme source utilise toutes les sources disponibles.
- Chaque moteur **plafonne à ~1000 images par mot-clé** : pour aller au-delà, il faut multiplier les mots-clés (voir `build_dataset.py`).

### Openverse — authentification (optionnelle mais recommandée)

Sans authentification : **20 résultats/page** et **~1 requête/seconde**.
Avec authentification : `page_size` jusqu'à 500 et quota bien supérieur.

**1. Enregistrer une application** (une seule fois) pour obtenir un `client_id` / `client_secret` :

```python
import requests
r = requests.post(
    "https://api.openverse.org/v1/auth_tokens/register/",
    json={"name": "mon-projet",
          "description": "Dataset pour classification d'images",
          "email": "toi@example.com"},
)
print(r.json())   # -> {'client_id': '...', 'client_secret': '...', 'name': '...'}
```

Puis **valide l'email de confirmation** reçu (les identifiants ne marchent qu'après).
Garde le `client_secret` confidentiel.

**2. Poser les variables d'environnement.** Le grabber récupère alors le token
automatiquement (et le renouvelle à chaque exécution, puisqu'un token expire) :

```bash
export OPENVERSE_CLIENT_ID="ton_client_id"
export OPENVERSE_CLIENT_SECRET="ton_client_secret"
export OPENVERSE_LICENSE="cc0,by"        # optionnel : ne garder que ces licences
# Alternative : coller directement un token (il a la priorité, mais expire) :
# export OPENVERSE_TOKEN="ton_bearer_token"
```

Sous Windows (PowerShell), utilise `setx OPENVERSE_CLIENT_ID "..."` (effet dans un
terminal neuf) ou `$env:OPENVERSE_CLIENT_ID="..."` (session courante).

Vérification :

```bash
python -c "from image_grabber.openverse_grabber import OpenverseGrabber; print(OpenverseGrabber().token)"
# doit afficher un token, pas None
```

---

## Les scripts en détail

### `download.py` — un mot-clé

```bash
python download.py MOT_CLE [options]
```

| Option | Description |
|--------|-------------|
| `-dest`, `-d` | Dossier de destination (défaut : `images/`). Un sous-dossier par mot-clé. |
| `-limit`, `-l` | Nombre d'images visé (défaut : 50). |
| `-source`, `-src` | Source. Répéter pour en cumuler plusieurs. |
| `-allsources`, `-as` | Mélanger toutes les sources. |
| `-thumbnail`, `-thumb` | Récupérer la vignette plutôt que l'original. |
| `-resize` | Redimensionner, ex. `-resize 64x64`. |

`bd_maker.py` est une variante équivalente avec messages en français.

### `build_dataset.py` — gros dataset multi-mots-clés

```bash
python build_dataset.py MOT_CLE [-v VARIANTE ...] [options]
```

| Option | Description |
|--------|-------------|
| `-variations`, `-v` | Mots-clés supplémentaires (ex. `-v chaton "chat noir"`). |
| `-limit`, `-l` | Nombre TOTAL d'images visé (défaut : 10000), réparti sur tous les mots-clés. |
| `-dest`, `-d` | Dossier de destination. |
| `-source`, `-src` | Source(s). Défaut : Bing + Baidu. |
| `-allsources`, `-as` | Toutes les sources. |
| `-resize` | Redimensionner toutes les images. |
| `-nodedup` | Désactiver la déduplication finale. |

Tous les mots-clés atterrissent dans **un seul dossier**, puis la déduplication retire les doublons.

### `build_moto_dataset.py` — dataset hiérarchique (CSV)

```bash
python build_moto_dataset.py [TAXONOMIE.csv] [options]
```

Lit un CSV de colonnes `type,brand,model,query[,limit]` et range les images dans
`<dest>/<type>/<marque>/<modèle>/`, puis écrit un `labels.csv`.

| Option | Description |
|--------|-------------|
| `-dest`, `-d` | Dossier racine (défaut : `dataset_moto`). |
| `-limit`, `-l` | Images par modèle (défaut : 300 ; la colonne `limit` du CSV est prioritaire). |
| `-source`, `-src` | Source(s). Défaut : Bing + Baidu. |
| `-allsources`, `-as` | Toutes les sources. |
| `-minsize` | Taille minimale `LARGEURxHAUTEUR` (défaut : `256x256`). `0x0` pour désactiver. |

Format du CSV (`moto_taxonomy.csv`) :

```csv
type,brand,model,query,limit
sport,Yamaha,YZF-R1,Yamaha YZF-R1 motorcycle,
cruiser,Honda,Rebel 500,Honda Rebel 500 motorcycle,500
```

> **Principe clé** : on requête des **modèles précis** (pas le type générique), ce qui
> donne les trois niveaux d'étiquette d'un coup et limite le bruit. Prévois plusieurs
> marques par type pour éviter que le classifieur « type » n'apprenne en fait la marque.

### `filter_dataset.py` — nettoyage sémantique (CLIP)

```bash
python filter_dataset.py [DATASET] [options]
```

Pour chaque image, CLIP compare « est-ce une moto ? » à des descriptions négatives
(personne, pièce, voiture, logo, texte…). Tout ce qui n'est pas une moto est
**déplacé** dans `<dataset>/_rejected/` (jamais supprimé), puis `labels.csv` est régénéré.

| Option | Description |
|--------|-------------|
| `dataset` | Dossier racine (défaut : `dataset_moto`). |
| `-threshold` | Score minimal pour garder une image (défaut : 0.30 ; plus haut = plus strict). |
| `-device` | `cpu` / `cuda` (auto-détecté). |

Les listes `POSITIVE_PROMPTS` / `NEGATIVE_PROMPTS` en haut du fichier sont éditables
pour cibler ton bruit récurrent. Le premier lancement télécharge les poids de CLIP (~600 Mo).

### `split_dataset.py` — audit + découpage train/val/test (anti-fuite)

```bash
python split_dataset.py [DATASET] [options]
```

Deux garde-fous avant l'entraînement : les **quasi-doublons** (même photo ré-encodée /
redimensionnée / watermarkée) sont regroupés via un hash perceptuel (dHash) et placés
**entièrement dans le même split** (pas de fuite train/test), et chaque **classe** est
répartie proportionnellement (stratification). Ne déplace ni ne copie rien : écrit un
manifeste `<dataset>/dataset_split.csv` (`file,type,brand,model,split`) et affiche un
audit (comptes par type, équilibre des splits, classes les plus pauvres).

| Option | Description |
|--------|-------------|
| `dataset` | Dossier racine (défaut : `dataset_moto`). |
| `-val` | Proportion validation (défaut : 0.15). |
| `-test` | Proportion test (défaut : 0.15). |
| `-seed` | Graine aléatoire (défaut : 42). |
| `-o`, `--out` | CSV de sortie (défaut : `<dataset>/dataset_split.csv`). |

---

## Workflow complet : un dataset de classification

```bash
# 1) Définir la taxonomie (étendre moto_taxonomy.csv : viser 8–12 modèles par type)

# 2) Télécharger (filtres type=photo + taille min déjà actifs)
python build_moto_dataset.py moto_taxonomy.csv -l 1000

# 3) Nettoyer les images hors-sujet
pip install open_clip_torch torch
python filter_dataset.py dataset_moto -threshold 0.35
#    -> vérifier dataset_moto/_rejected/ pour ajuster le seuil

# 4) Découper en train/val/test (anti-fuite + audit)
pip install imagehash
python split_dataset.py dataset_moto -val 0.15 -test 0.15

# 5) Entraîner à partir de dataset_moto/dataset_split.csv
```

Les trois tâches de classification se lisent directement dans le manifeste
(`type`, `brand`, `model`), l'image restant la même. Pour l'entraînement, l'approche
recommandée est le **transfert learning** (backbone pré-entraîné ImageNet), traité
**tâche par tâche du plus simple au plus dur** : type (3 classes) → marque → modèle.
Pense à l'augmentation de données (flip, recadrage, couleur) et à la pondération des
classes pour compenser le déséquilibre ; ne regarde le **test** qu'une seule fois, à la fin.

---

## Fichiers de sortie

- **Images** : `<dest>/<...>/`, nommées par source (`000001.jpg`, …) ou par identifiant Openverse (`ov_<id>.jpg`).
- **`labels.csv`** (datasets hiérarchiques) : `file,type,brand,model` — une ligne par image.
- **`attributions.csv`** (Openverse) : `file,title,creator,license,license_version,license_url,source,foreign_landing_url`.
- **`_rejected/`** (après filtrage CLIP) : images écartées, arborescence d'origine conservée.
- **`dataset_split.csv`** (après découpage) : `file,type,brand,model,split` (`split` ∈ train/val/test).

---

## Limites connues et pièges

- **Plafond ~1000 images par moteur et par mot-clé** : multiplier les mots-clés est indispensable pour les gros volumes.
- **Google instable** : le crawler d'icrawler casse régulièrement (0 image) ; le repli automatique compense, garde Bing/Baidu comme sources principales.
- **`min_size` ne s'applique qu'aux moteurs icrawler** (Bing/Baidu/Google), pas à Openverse.
- **Déduplication : exacte au téléchargement, perceptuelle au découpage.** Les doublons exacts sont retirés dès le téléchargement ; les quasi-doublons (ré-encodage, recadrage, watermark) ne sont pas supprimés, mais `split_dataset.py` les regroupe pour éviter les fuites train/test. Pour les *supprimer* réellement, il faudrait une passe de dédup perceptuelle dédiée.
- **Le filtre CLIP répond à « moto / pas moto »**, il ne vérifie pas que le *modèle exact* est correct.
- **Biais de dataset** à surveiller : déséquilibre entre classes, fond blanc des photos studio (raccourci d'apprentissage), fuite marque→type. La fuite entre splits est gérée par `split_dataset.py`.

---

## Licences

c'est là pour la forme parce que le code est largement récupérer de différents endroits sur plusieurs forum/subreddit
et les photos ne m'appartiennent pas (sinon j'aurais pas fait ce dataset maker)

README généré par claude.
Refactoring et commentaire généré par Claude également pour rendre le code plus lisible pour mes "collégues" (🤡)
Au moins ça m'apprendra à ne jamais essayer de rendre la tâche plus simple pour des gens qui ne se mettent pas à la tâche..
