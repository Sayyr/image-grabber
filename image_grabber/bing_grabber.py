import logging

from icrawler.builtin import BingImageCrawler

from .abstract_grabber import AbstractGrabber
from .grab_settings import GrabSourceType
from utils.utils import FileUtil


class BingGrabber(AbstractGrabber):
    """Récupère des images depuis Bing Images via icrawler (source fiable)."""

    source = GrabSourceType.BING.value
    full_image = True

    def grab(self, keyword: str, nb_images: int, root_dir: str,
             min_size=None, max_size=None) -> int:
        crawler = BingImageCrawler(
            downloader_threads=4,
            log_level=logging.WARNING,   # moins de bruit dans la console
            storage={'root_dir': root_dir},
        )

        before = FileUtil.nb_file_images_in_folder(root_dir)
        crawler.crawl(
            keyword=keyword,
            max_num=nb_images,
            min_size=min_size,
            max_size=max_size,
            filters={'type': 'photo'},   # écarte clipart / dessins / logos / animés
            file_idx_offset='auto',
        )
        return FileUtil.nb_file_images_in_folder(root_dir) - before
