import os

from .grab_settings import (
    ALL_SOURCE,
    DEFAULT_DESTINATION_FOLDER,
    DEFAULT_DOWNLOAD_LIMIT,
    DEFAULT_GRAB_SOURCE_TYPE,
    GrabSourceType,
)
from .google_grabber import GoogleGrabber
from .bing_grabber import BingGrabber
from .baidu_grabber import BaiduGrabber
from .openverse_grabber import OpenverseGrabber
from utils.utils import StringUtil, FileUtil, ExceptionUtil

# Map a source name (the Enum *value*, e.g. "Google") to its grabber class.
GRABBERS = {
    GrabSourceType.GOOGLE.value: GoogleGrabber,
    GrabSourceType.BING.value: BingGrabber,
    GrabSourceType.BAIDU.value: BaiduGrabber,
    GrabSourceType.OPENVERSE.value: OpenverseGrabber,
}


class ImageDownloader:
    """Orchestre le téléchargement : choisit les sources, répartit le quota
    entre elles, télécharge dans un sous-dossier par mot-clé, puis redimensionne.
    En cas d'échec total d'une source (ex. Google cassé), bascule automatiquement
    sur les autres sources disponibles."""

    def __init__(self):
        self.destination = DEFAULT_DESTINATION_FOLDER
        self.limit = DEFAULT_DOWNLOAD_LIMIT
        self.sources = [DEFAULT_GRAB_SOURCE_TYPE]
        self.resize = None        # (width, height) or None
        self.full_image = True    # kept for CLI compatibility (icrawler fetches originals)
        self.min_size = None      # optional (width, height) minimum filter

    # ------------------------------------------------------------------ #

    def _resolve_sources(self):
        """Turn whatever is in self.sources into a clean list of known sources.
        Accepts 'all', is case-insensitive, and warns on unknown sources."""
        if not self.sources or ALL_SOURCE in self.sources:
            return list(GRABBERS.keys())

        valid, unknown = [], []
        for s in self.sources:
            match = next((k for k in GRABBERS if k.lower() == str(s).lower()), None)
            if match:
                if match not in valid:
                    valid.append(match)
            else:
                unknown.append(s)

        if unknown:
            print('  source(s) inconnue(s) ignorée(s) : %s   (dispo : %s)'
                  % (', '.join(map(str, unknown)), ', '.join(GRABBERS.keys())))

        return valid or [DEFAULT_GRAB_SOURCE_TYPE]

    def download_images(self, keyword: str) -> str:
        requested = self._resolve_sources()

        folder_name = StringUtil.underscore_and_lowercase(keyword)
        dest_dir = os.path.join(self.destination, folder_name)
        os.makedirs(dest_dir, exist_ok=True)

        print('> mot-clé : "%s"  |  sources : %s  |  objectif : %d image(s)'
              % (keyword, ', '.join(requested), self.limit))

        total = self._grab_from_sources(keyword, requested, dest_dir, self.limit)

        # Repli : si les sources demandées n'ont rien ramené, on essaie les autres.
        if total == 0:
            fallback = [s for s in GRABBERS if s not in requested]
            if fallback:
                print('  Erreur ! Aucune image trouvée via %s — repli sur : %s'
                      % (', '.join(requested), ', '.join(fallback)))
                total = self._grab_from_sources(keyword, fallback, dest_dir, self.limit)

        print('✓ %d image(s) téléchargée(s) dans "%s"' % (total, dest_dir))
        if total == 0:
            print('  Erreur ! Aucune image trouvée. Essaie un autre mot-clé, '
                  '--allsources, ou augmente -limit.')

        if self.resize is not None and total:
            self._resize_folder(dest_dir)

        return dest_dir

    # ------------------------------------------------------------------ #

    def _grab_from_sources(self, keyword: str, sources, dest_dir: str, limit: int) -> int:
        """Télécharge en répartissant `limit` sur `sources`. Une source qui
        échoue (exception ou 0 image) n'interrompt pas les suivantes."""
        if not sources or limit <= 0:
            return 0

        per_source = max(1, limit // len(sources))
        total = 0
        for i, source in enumerate(sources):
            # on donne le reste à la dernière source pour viser le quota exact
            target = (limit - total) if i == len(sources) - 1 else per_source
            if target <= 0:
                break
            grabber = GRABBERS[source]()
            grabber.full_image = self.full_image
            print('  → %s : ~%d image(s)…' % (source, target))
            try:
                got = grabber.grab(keyword, target, dest_dir, min_size=self.min_size)
            except Exception as e:
                ExceptionUtil.print(e)
                got = 0
            if got == 0:
                print('     (0 image depuis %s)' % source)
            total += got
        return total

    # ------------------------------------------------------------------ #

    def download_dataset(self, keywords, folder_name: str = None,
                         dedup: bool = True) -> str:
        """Construit un gros dataset : éclate `self.limit` sur plusieurs
        mots-clés (et sur toutes les sources résolues), le tout dans UN seul
        dossier, puis déduplique. Indispensable pour viser 10k+ images, car
        chaque moteur plafonne à ~1000 par mot-clé."""
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords = [k for k in keywords if k and k.strip()]
        if not keywords:
            raise ValueError("Aucun mot-clé fourni.")

        sources = self._resolve_sources()
        folder_name = folder_name or StringUtil.underscore_and_lowercase(keywords[0])
        dest_dir = os.path.join(self.destination, folder_name)
        os.makedirs(dest_dir, exist_ok=True)

        per_keyword = max(1, self.limit // len(keywords))
        print('> dataset "%s" | %d mot(s)-clé | sources : %s | objectif : %d image(s)'
              % (folder_name, len(keywords), ', '.join(sources), self.limit))

        for kw in keywords:
            print('— mot-clé : "%s" (~%d image[s])' % (kw, per_keyword))
            self._grab_from_sources(kw, sources, dest_dir, per_keyword)

        if dedup:
            removed = FileUtil.dedup_folder(dest_dir)
            print('✓ déduplication : %d doublon(s) supprimé(s)' % removed)

        kept = FileUtil.nb_file_images_in_folder(dest_dir)
        print('✓ %d image(s) unique(s) dans "%s"' % (kept, dest_dir))
        if kept < self.limit:
            print('  Erreur ! Sous l\'objectif : ajoute des variantes de mot-clé '
                  '(-v), des sources (--allsources) ou augmente -limit.')

        if self.resize is not None and kept:
            self._resize_folder(dest_dir)

        return dest_dir

    def _resize_folder(self, dest_dir: str):
        from PIL import Image
        width, height = self.resize
        paths = FileUtil.get_images_file_path_array(dest_dir)
        done = 0
        for path in paths:
            try:
                with Image.open(path) as im:
                    im.convert('RGB').resize((width, height)).save(path)
                done += 1
            except Exception as e:
                ExceptionUtil.print(e)
        print('OK ! %d image(s) redimensionnée(s) en %dx%d' % (done, width, height))
