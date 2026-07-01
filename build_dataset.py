import argparse
import warnings

from image_grabber import image_downloader
from image_grabber.grab_settings import *

warnings.filterwarnings("ignore")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Construit un dataset d'images volumineux (10k+) en éclatant "
                    "un thème sur plusieurs mots-clés et plusieurs moteurs, "
                    "puis en dédupliquant. Tout atterrit dans un seul dossier.",
        epilog="Source Openverse (-src Openverse) : images sous licence ouverte "
               "(CC / domaine public), avec attributions.csv généré. Token gratuit "
               "optionnel via la variable d'env OPENVERSE_TOKEN (lève le plafond de "
               "20 résultats/page et le ~1 req/s de l'accès anonyme). Filtre de "
               "licence via OPENVERSE_LICENSE, ex. \"cc0,by\".")

    def resize_arg(s):
        try:
            x, y = map(int, s.lower().split('x'))
            return x, y
        except Exception:
            raise argparse.ArgumentTypeError(
                "Format attendu : LARGEURxHAUTEUR, ex. --resize=32x32")

    parser.add_argument('keyword', nargs=1,
                        help='Mot-clé principal (donne aussi le nom du dossier).')
    parser.add_argument('-variations', '-v', nargs='+', default=[], dest='variations',
                        help='Variantes à ajouter, ex. -v chaton "chat noir" "chat persan". '
                             'Chacune relance ~1000 images par moteur.')
    parser.add_argument('-limit', '-l', type=int, default=10000,
                        help='Nombre TOTAL d\'images visé (défaut : 10000), '
                             'réparti sur tous les mots-clés.')
    parser.add_argument('-dest', '-d', help='Dossier de destination (défaut : %s/).'
                        % DEFAULT_DESTINATION_FOLDER)
    parser.add_argument('-source', '-src', action='append', dest='sources',
                        help='Source(s) : %s. Répéter pour cumuler. '
                             'Défaut : toutes les sources fiables.'
                             % ', '.join(e.value for e in GrabSourceType))
    parser.add_argument('-allsources', '-as', action='store_true', default=False,
                        help='Utiliser toutes les sources disponibles.')
    parser.add_argument('-resize', dest='resize', default=None, type=resize_arg,
                        help='Redimensionner toutes les images, ex. -resize 64x64.')
    parser.add_argument('-nodedup', action='store_true', default=False,
                        help='Désactiver la déduplication finale.')

    args = parser.parse_args()

    downloader = image_downloader.ImageDownloader()
    downloader.limit = args.limit
    if args.dest is not None:
        downloader.destination = args.dest
    if args.resize is not None:
        downloader.resize = args.resize

    # Par défaut on cumule les sources fiables (Bing + Baidu) pour maximiser le volume.
    if args.allsources:
        downloader.sources = [ALL_SOURCE]
    elif args.sources:
        downloader.sources = args.sources
    else:
        downloader.sources = [GrabSourceType.BING.value, GrabSourceType.BAIDU.value]

    keywords = args.keyword + args.variations
    downloader.download_dataset(keywords, dedup=not args.nodedup)
