from enum import Enum

DEBUG_MODE = False

USER_AGENT_HEADER = {
    'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"
}


class GrabSourceType(Enum):
    GOOGLE = 'Google'
    BING = 'Bing'
    BAIDU = 'Baidu'
    OPENVERSE = 'Openverse'


ALL_SOURCE = 'all'

# Bing par défaut : le crawler Google d'icrawler est régulièrement cassé et
# renvoie 0 image. On peut toujours forcer Google avec -src Google.
DEFAULT_GRAB_SOURCE_TYPE = GrabSourceType.BING.value
DEFAULT_DOWNLOAD_LIMIT = 50
DEFAULT_DESTINATION_FOLDER = "images"
