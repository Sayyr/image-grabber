import os
import unicodedata
from typing import List

from PIL import Image

from image_grabber.grab_settings import DEBUG_MODE


class StringUtil:
    def __init__(self):
        """Constructor for StringUtil"""

    @staticmethod
    def underscore_and_lowercase(words: str) -> str:
        return words.lower().replace(" ", "_")

    @staticmethod
    def is_http_url(src) -> bool:
        result = unicodedata.normalize('NFKD', src).encode('ascii', 'ignore')
        return result[:4].decode() == "http"


class ExceptionUtil:

    @staticmethod
    def print(e):
        if DEBUG_MODE:
            print(e)


class ProgressBarUtil:

    @staticmethod
    def update(progress: int, total: int):
        workdone = progress / total
        print("\rProgress: [{0:50s}] {1:.1f}%".format(
            '#' * int(workdone * 50), workdone * 100), end="", flush=True)


class FileUtil:
    image_extensions = ['.bmp', '.gif', '.jpeg', '.jpg', '.png', '.raw', '.tiff', '.webp']

    def __init__(self):
        """Constructor for FileUtil"""

    @staticmethod
    def folder_total_size(folder_path: str) -> float:
        return sum([os.path.getsize(os.path.join(folder_path, f))
                    for f in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, f))
                    and FileUtil.is_image(os.path.join(folder_path, f))])

    @staticmethod
    def mean_folder_file_size(folder_path: str) -> float:
        nb = FileUtil.nb_file_images_in_folder(folder_path)
        return FileUtil.folder_total_size(folder_path) / nb if nb else 0.0

    @staticmethod
    def nb_file_images_in_folder(folder_path: str) -> int:
        if not os.path.isdir(folder_path):
            return 0
        return len(FileUtil.get_images_file_path_array(folder_path))

    @staticmethod
    def get_file_extension(path: str) -> str:
        return os.path.splitext(path)[1]

    @staticmethod
    def is_image(path: str) -> bool:
        return FileUtil.get_file_extension(path).lower() in FileUtil.image_extensions

    @staticmethod
    def get_images_file_path_array(folder_path) -> List[str]:
        return [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
                and FileUtil.is_image(os.path.join(folder_path, f))]

    @staticmethod
    def open(path: str) -> Image.Image:
        return Image.open(path)

    @staticmethod
    def create_folder(folder_path: str):
        os.makedirs(folder_path, exist_ok=True)

    @staticmethod
    def generate_next_file_path(folder_path: str, file_prefix: str):
        counter = len([i for i in os.listdir(folder_path) if file_prefix in i]) + 1
        extension = ".jpg"
        file_name = file_prefix + "_" + str(counter) + extension
        return os.path.join(folder_path, file_name)

    @staticmethod
    def dedup_folder(folder_path: str) -> int:
        """Supprime les doublons exacts (même contenu) d'un dossier d'images.
        Retourne le nombre de fichiers supprimés."""
        import hashlib
        seen = set()
        removed = 0
        for path in FileUtil.get_images_file_path_array(folder_path):
            try:
                with open(path, 'rb') as f:
                    h = hashlib.md5(f.read()).hexdigest()
            except OSError:
                continue
            if h in seen:
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    pass
            else:
                seen.add(h)
        return removed

    @staticmethod
    def save_file(image: Image.Image, folder_path: str, file_prefix: str):
        FileUtil.create_folder(folder_path)
        full_destination = FileUtil.generate_next_file_path(folder_path, file_prefix)
        image.convert('RGB').save(full_destination)


class NoImageFoundException(Exception):
    pass
