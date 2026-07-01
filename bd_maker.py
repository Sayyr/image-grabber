import argparse
import warnings

from image_grabber import image_downloader
from image_grabber.grab_settings import *

warnings.filterwarnings("ignore")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Télécharge un jeu d'images à partir d'un mot-clé "
                    "(scraping Google/Bing via icrawler).")

    def resize_arg(s):
        try:
            x, y = map(int, s.lower().split('x'))
            return x, y
        except Exception:
            raise argparse.ArgumentTypeError(
                "Paramètre '-resize' invalide. Format attendu : LARGEURxHAUTEUR. "
                "Exemple : --resize=32x32 produit des images de 32px x 32px.")

    parser.add_argument('image_keyword',
                        nargs=1,
                        help='Mot-clé à rechercher')

    parser.add_argument('-dest', '-d',
                        help='Dossier de destination (défaut : %s/). '
                             'Un sous-dossier est créé par mot-clé.'
                             % DEFAULT_DESTINATION_FOLDER)

    parser.add_argument('-limit', '-l',
                        type=int,
                        help='Nombre d\'images à télécharger (défaut : %s)'
                             % DEFAULT_DOWNLOAD_LIMIT)

    parser.add_argument('-thumbnail', '-thumb',
                        action="store_true",
                        default=False,
                        help='Récupérer la vignette plutôt que l\'image originale')

    parser.add_argument('-resize',
                        dest="resize",
                        default=None,
                        type=resize_arg,
                        help='Redimensionner les images. '
                             'Exemple : -resize 32x32 produit du 32px x 32px.')

    possible_datasources = ', '.join([e.value for e in GrabSourceType])
    parser.add_argument('-source', '-src',
                        action='append',
                        dest='sources',
                        help='Source de téléchargement : %s (défaut : %s). '
                             'Répéter l\'option pour cumuler plusieurs sources.'
                             % (possible_datasources, DEFAULT_GRAB_SOURCE_TYPE))

    parser.add_argument('-allsources', '-as',
                        action="store_true",
                        default=False,
                        help='Mélanger les images de toutes les sources : %s'
                             % possible_datasources)

    args = parser.parse_args()

    downloader = image_downloader.ImageDownloader()

    if args.dest is not None:
        downloader.destination = args.dest

    if args.limit is not None:
        downloader.limit = int(args.limit)

    if args.allsources is True:
        downloader.sources = [ALL_SOURCE]
    elif args.sources is not None:
        downloader.sources = args.sources

    if args.resize is not None:
        downloader.resize = args.resize

    if args.thumbnail is True:
        downloader.full_image = False

    keyword = args.image_keyword[0]
    downloader.download_images(keyword)
