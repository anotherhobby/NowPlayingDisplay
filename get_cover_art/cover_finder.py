import os, unicodedata, re
from get_cover_art.apple_downloader import AppleDownloader
from get_cover_art.meta import Meta

DEFAULTS = {
    "art_size": "720",
    "art_quality": "0", # falls back on default quality
    "art_dest_filename": "{artist} - {album_or_title}.jpg",
    "throttle": 3,
}

# anotherhobby: this was sourced and modified from the repository below for NowPlayingDisplay: 
#                     https://github.com/regosen/get_cover_art


class CoverFinder(object):
    def __init__(self, debug: bool = False):
        self.art_size = int(DEFAULTS.get('art_size'))
        self.art_quality = int(DEFAULTS.get('art_quality'))
        self.art_dest_filename = DEFAULTS.get('art_dest_filename')
        self.debug = debug
        self.downloader = None
        self.external_art_mode = None
        self.external_art_filename = None
        throttle = float(DEFAULTS.get('throttle'))
        self.downloader = AppleDownloader(self.debug, throttle, self.art_size, self.art_quality)
        self.force = True
        self.files_to_delete = set([])

    def download(self, meta: Meta, art_path: str) -> bool:
        if self.force or not os.path.exists(art_path):
            return self.downloader.download(meta, art_path)
        elif self.debug:
            print(f"Skipping existing download for {art_path}")
        return True

    def slugify(self, value: str, has_extension=True) -> str:
        """
        Normalizes string, removes non-alpha characters
        based on https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename

        This assumes that a filename being passed in has an
        extension, and preserves the period leading that extension.
        If you have an extensionless filename, specify has_extension=False
        """
        if has_extension:
            value, ext = os.path.splitext(value)
        else:
            ext = ""
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        value = re.sub('[^\w\s-]', '', bytes.decode(value)).strip()
        value += ext
        return value


