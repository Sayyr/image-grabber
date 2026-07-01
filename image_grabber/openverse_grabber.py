import csv
import os
import time
from urllib.parse import urlparse

import requests

from .abstract_grabber import AbstractGrabber
from .grab_settings import GrabSourceType
from utils.utils import FileUtil, ExceptionUtil

OPENVERSE_API = "https://api.openverse.org/v1/images/"


class OpenverseGrabber(AbstractGrabber):
    """Récupère des images via l'API Openverse (api.openverse.org).

    Contrairement aux autres sources (scraping via icrawler), c'est une API REST
    stable qui ne renvoie QUE du contenu sous licence ouverte (Creative Commons /
    domaine public) et fournit la licence + l'attribution de chaque image. Idéal
    pour un dataset propre et réutilisable légalement.

    Token optionnel via la variable d'environnement OPENVERSE_TOKEN : sans token,
    l'API limite à 20 résultats/page et ~1 req/s. Avec token (gratuit), page_size
    jusqu'à 500 et quota bien supérieur.

    Filtre de licence optionnel via OPENVERSE_LICENSE, ex. "cc0,by" ou "cc0".
    Une note d'attribution est écrite dans <root_dir>/attributions.csv.
    """

    source = GrabSourceType.OPENVERSE.value
    full_image = True

    def __init__(self):
        self.token = os.environ.get("OPENVERSE_TOKEN")
        self.license = os.environ.get("OPENVERSE_LICENSE")  # ex. "cc0,by"
        self.timeout = 30
        self.request_delay = 0.2 if self.token else 1.1  # respect du ~1 req/s anonyme

    def _headers(self):
        headers = {"User-Agent": "image-grabber/1.0 (+openverse)"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    @staticmethod
    def _ext_from_url(url: str, fallback=".jpg") -> str:
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        return ext if ext in FileUtil.image_extensions else fallback

    def _download(self, session, item, root_dir) -> bool:
        url = item.get("url")
        if not url:
            return False
        # nom de fichier stable basé sur l'id Openverse -> reprise possible / pas de collision
        name = "ov_%s%s" % (item.get("id", str(abs(hash(url)))),
                            self._ext_from_url(url))
        dest = os.path.join(root_dir, name)
        if os.path.exists(dest):
            return False  # déjà téléchargé
        try:
            r = session.get(url, headers={"User-Agent": "image-grabber/1.0"},
                            timeout=self.timeout, stream=True)
            if r.status_code != 200:
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            ExceptionUtil.print(e)
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
            return False

    def grab(self, keyword: str, nb_images: int, root_dir: str,
             min_size=None, max_size=None) -> int:
        FileUtil.create_folder(root_dir)
        before = FileUtil.nb_file_images_in_folder(root_dir)

        page_size = 500 if self.token else 20   # anonyme : plafonné à 20
        manifest = os.path.join(root_dir, "attributions.csv")
        write_header = not os.path.exists(manifest)

        session = requests.Session()
        collected = 0
        page = 1

        with open(manifest, "a", newline="", encoding="utf-8") as mf:
            writer = csv.writer(mf)
            if write_header:
                writer.writerow(["file", "title", "creator", "license",
                                 "license_version", "license_url", "source",
                                 "foreign_landing_url"])

            while collected < nb_images:
                params = {
                    "q": keyword,
                    "page": page,
                    "page_size": min(page_size, nb_images - collected),
                }
                if self.license:
                    params["license"] = self.license
                try:
                    resp = session.get(OPENVERSE_API, params=params,
                                       headers=self._headers(), timeout=self.timeout)
                except Exception as e:
                    ExceptionUtil.print(e)
                    break

                if resp.status_code == 429:        # rate limit -> on patiente
                    time.sleep(5)
                    continue
                if resp.status_code != 200:
                    ExceptionUtil.print("Openverse HTTP %s" % resp.status_code)
                    break

                data = resp.json()
                results = data.get("results") or []
                if not results:
                    break

                for item in results:
                    if collected >= nb_images:
                        break
                    name = "ov_%s%s" % (item.get("id"), self._ext_from_url(item.get("url", "")))
                    if self._download(session, item, root_dir):
                        writer.writerow([
                            name,
                            item.get("title", ""),
                            item.get("creator", ""),
                            item.get("license", ""),
                            item.get("license_version", ""),
                            item.get("license_url", ""),
                            item.get("source", ""),
                            item.get("foreign_landing_url", ""),
                        ])
                        collected += 1

                page_count = data.get("page_count") or page
                if page >= page_count:
                    break
                page += 1
                time.sleep(self.request_delay)

        return FileUtil.nb_file_images_in_folder(root_dir) - before
