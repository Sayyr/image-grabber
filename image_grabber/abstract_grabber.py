from abc import ABCMeta, abstractmethod


class AbstractGrabber(metaclass=ABCMeta):
    """Base class for all image sources.

    Note: the contract changed from the original `get_images_url` (which returned
    a list of URLs to download separately) to `grab`, because the icrawler
    engine crawls and downloads in one step. Each grabber writes files directly
    into `root_dir` and returns how many it downloaded.
    """

    # If True grab the full-size image, if False the thumbnail (when supported).
    # With icrawler the original image is always fetched, so this is informational.
    full_image = True

    @abstractmethod
    def grab(self, keyword: str, nb_images: int, root_dir: str,
             min_size=None, max_size=None) -> int:
        """Download up to `nb_images` images for `keyword` into `root_dir`.

        Returns the number of images actually downloaded.
        """
        raise NotImplementedError
