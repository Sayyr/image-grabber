import argparse
import csv
import os
import warnings

from image_grabber import image_downloader
from image_grabber.grab_settings import GrabSourceType, ALL_SOURCE
from utils.utils import StringUtil, FileUtil

warnings.filterwarnings("ignore")


def slug(s: str) -> str:
    return StringUtil.underscore_and_lowercase(s.strip())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Construit un dataset hiérarchique de motos à partir d'un CSV "
                    "taxonomie (colonnes : type,brand,model,query[,limit]). "
                    "Range les images dans <dest>/<type>/<marque>/<modele>/ et "
                    "écrit un labels.csv prêt pour l'entraînement.")
    parser.add_argument('taxonomy', nargs='?', default='moto_taxonomy.csv',
                        help='Fichier CSV de taxonomie (défaut : moto_taxonomy.csv)')
    parser.add_argument('-dest', '-d', default='dataset_moto',
                        help='Dossier racine du dataset (défaut : dataset_moto)')
    parser.add_argument('-limit', '-l', type=int, default=300,
                        help='Images par modèle (défaut : 300 ; '
                             'la colonne "limit" du CSV est prioritaire si présente)')
    parser.add_argument('-source', '-src', action='append', dest='sources',
                        help='Source(s) de téléchargement. Répéter pour cumuler. '
                             'Défaut : Bing + Baidu.')
    parser.add_argument('-allsources', '-as', action='store_true', default=False,
                        help='Utiliser toutes les sources disponibles.')
    parser.add_argument('-minsize', dest='minsize', default='256x256',
                        help='Taille minimale LARGEURxHAUTEUR (défaut : 256x256). '
                             'Écarte logos/icônes/vignettes. "0x0" pour désactiver.')

    args = parser.parse_args()

    try:
        mw, mh = map(int, args.minsize.lower().split('x'))
        min_size = (mw, mh) if (mw > 0 and mh > 0) else None
    except Exception:
        raise SystemExit('-minsize invalide, format attendu LARGEURxHAUTEUR (ex. 256x256)')

    with open(args.taxonomy, newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if (r.get('query') or '').strip()]

    if not rows:
        raise SystemExit('Aucune ligne exploitable dans %s' % args.taxonomy)

    os.makedirs(args.dest, exist_ok=True)
    print('> %d modèle(s) à télécharger depuis "%s"' % (len(rows), args.taxonomy))

    for r in rows:
        t, b, m, q = r['type'].strip(), r['brand'].strip(), r['model'].strip(), r['query'].strip()
        limit = int(r['limit']) if (r.get('limit') or '').strip() else args.limit

        dl = image_downloader.ImageDownloader()
        dl.limit = limit
        dl.min_size = min_size
        dl.destination = os.path.join(args.dest, slug(t), slug(b))
        if args.allsources:
            dl.sources = [ALL_SOURCE]
        elif args.sources:
            dl.sources = args.sources
        else:
            dl.sources = [GrabSourceType.BING.value, GrabSourceType.BAIDU.value]

        print('\n=== %s / %s / %s ===' % (t, b, m))
        dl.download_dataset([q], folder_name=slug(m), dedup=True)

    # ----- labels.csv global (chemin -> type, marque, modèle) -----
    labels_path = os.path.join(args.dest, 'labels.csv')
    n = 0
    with open(labels_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['file', 'type', 'brand', 'model'])
        for r in rows:
            t, b, m = r['type'].strip(), r['brand'].strip(), r['model'].strip()
            folder = os.path.join(args.dest, slug(t), slug(b), slug(m))
            if not os.path.isdir(folder):
                continue
            for fp in FileUtil.get_images_file_path_array(folder):
                w.writerow([fp, t, b, m])
                n += 1

    print('\n✓ %d image(s) étiquetée(s) -> %s' % (n, labels_path))
