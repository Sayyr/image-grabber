import logging

from icrawler.builtin import BaiduImageCrawler

from .abstract_grabber import AbstractGrabber
from .grab_settings import GrabSourceType
from utils.utils import FileUtil


class BaiduGrabber(AbstractGrabber):
    """Récupère des images depuis Baidu Images via icrawler.

    Source supplémentaire utile pour grossir un dataset : son catalogue diffère
    de Bing, ce qui réduit le recouvrement (donc plus d'images uniques)."""

    source = GrabSourceType.BAIDU.value
    full_image = True

    def grab(self, keyword: str, nb_images: int, root_dir: str,
             min_size=None, max_size=None) -> int:
        crawler = BaiduImageCrawler(
            downloader_threads=4,
            log_level=logging.WARNING,
            storage={'root_dir': root_dir},
        )

        before = FileUtil.nb_file_images_in_folder(root_dir)
        crawler.crawl(
            keyword=keyword,
            max_num=nb_images,
            min_size=min_size,
            max_size=max_size,
            file_idx_offset='auto',
        )
        return FileUtil.nb_file_images_in_folder(root_dir) - before
