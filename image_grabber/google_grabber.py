import logging

from icrawler.builtin import GoogleImageCrawler
from icrawler.builtin.google import GoogleParser

from .abstract_grabber import AbstractGrabber
from .grab_settings import GrabSourceType
from utils.utils import FileUtil


class SafeGoogleParser(GoogleParser):
    """Parser Google tolérant aux pannes.

    Le parser d'origine d'icrawler renvoie ``None`` quand il ne trouve aucune
    URL d'image (page de consentement, balisage Google modifié, etc.). icrawler
    fait alors ``for task in self.parse(...)`` -> ``TypeError: 'NoneType' object
    is not iterable`` dans un thread. On normalise le retour en liste vide pour
    que la source dégrade proprement (0 image) au lieu de planter.
    """

    def parse(self, response):
        result = super().parse(response)
        return result if result is not None else []


class GoogleGrabber(AbstractGrabber):
    """Récupère des images depuis Google Images via icrawler.

    Attention : le crawler Google d'icrawler est régulièrement cassé (Google
    change son balisage). Il peut renvoyer 0 image. Bing est plus fiable ;
    ImageDownloader bascule automatiquement dessus en cas d'échec.
    """

    source = GrabSourceType.GOOGLE.value
    full_image = True

    def grab(self, keyword: str, nb_images: int, root_dir: str,
             min_size=None, max_size=None) -> int:
        crawler = GoogleImageCrawler(
            parser_cls=SafeGoogleParser,   # évite le crash 'NoneType is not iterable'
            feeder_threads=1,
            parser_threads=2,
            downloader_threads=4,
            log_level=logging.WARNING,     # moins de bruit dans la console
            storage={'root_dir': root_dir},
        )

        before = FileUtil.nb_file_images_in_folder(root_dir)
        crawler.crawl(
            keyword=keyword,
            max_num=nb_images,
            min_size=min_size,
            max_size=max_size,
            file_idx_offset='auto',   # garde une numérotation continue entre sources
        )
        return FileUtil.nb_file_images_in_folder(root_dir) - before
