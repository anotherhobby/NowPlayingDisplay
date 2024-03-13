import logging
import time
import re
from typing import Tuple
from urllib.parse import quote, urlparse
from urllib.request import HTTPError, Request, urlopen

from get_cover_art.deromanizer import DeRomanizer
from get_cover_art.meta import Meta
from get_cover_art.normalizer import AlbumNormalizer, ArtistNormalizer

# https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/Searching.html
# https://itunes.apple.com/search?term=Lambert&entity=song&attribute=artistTerm&term=OPEN&entity=album&attribute=albumTerm&term=I've+Never+Been+to+China&entity=song&attribute=songTerm
# https://itunes.apple.com/search?term=The%20Open&entity=musicTrack&attribute=artistTerm&term=The%20Open&attribute=albumTerm&term=ive%20never%20been%20to%20china&attribute=songTerm&The%20Open

QUERY_TEMPLATE = "https://itunes.apple.com/search?term=%s&media=music&entity=%s"
ATTRIBUTE_QUERY_TEMPLATE = "https://itunes.apple.com/search?term=%s&entity=musicTrack&attribute=artistTerm&term=%s&attribute=albumTerm&term=%s&attribute=songTerm=%s"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36"
THROTTLED_HTTP_CODES = [403, 429]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppleDownloader(object):
    def __init__(self, debug: bool, throttle: float, art_size: int, art_quality: int):
        quality_suffix = "bb" if art_quality == 0 else f"-{art_quality}"
        self.file_suffix = f"{art_size}x{art_size}{quality_suffix}"
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("debug logging enabled for AppleDownloader")
        else:
            print("debug logging disabled for AppleDownloader")
        self.throttle = throttle
        self.artist_normalizer = ArtistNormalizer()
        self.album_normalizer = AlbumNormalizer()
        self.deromanizer = DeRomanizer()
        
    def _urlopen_safe(self, url: str) -> str:
        while True:
            try:
                q = Request(url)
                q.add_header("User-Agent", USER_AGENT)
                response = urlopen(q)
                return response.read()
            except HTTPError as e:
                if e.code in THROTTLED_HTTP_CODES:
                    # we've been throttled, time to sleep
                    domain = urlparse(url).netloc
                    logger.warning(f"Request limit exceeded from {domain}, trying again in {self.throttle} seconds...")
                    time.sleep(self.throttle)
                else:
                    raise e

    def _urlopen_text(self, url: str) -> str:
        try:
            return self._urlopen_safe(url).decode("utf8")
        except Exception as error:
            if ("certificate verify failed" in str(error)):
                logger.error(f"Python doesn't have SSL certificates installed, can't access {url}")
                logger.error("Please run 'Install Certificates.command' from your Python installation directory.")
            else:
                logger.error(f"Error reading URL ({url}): {str(error)})")
            return ""

    def _download_from_url(self, image_url: str, dest_path: str):
        image_data = self._urlopen_safe(image_url)
        if self.debug:
            logger.debug(f"Downloading from: {image_url}")
        with open(dest_path,'wb') as file:
            file.write(image_data)
        logger.debug(f"Downloaded cover art: {dest_path}")

    def _query(self, artist: str, album: str, title: str, attr_search: bool = False) -> dict:
        query_term = f"{artist} {title} {album}"
        logger.debug(f"Query term: {query_term}")
        if attr_search:
            url = ATTRIBUTE_QUERY_TEMPLATE % (quote(title), quote(artist), quote(album), quote(title))
        else:
            url = QUERY_TEMPLATE % (quote(query_term), "musicTrack")
        logger.debug(f"URL: {url}")
        json = self._urlopen_text(url)
        if json:
            try:
                safe_json = json.replace('true', 'True').replace('false', 'False')
                return eval(safe_json)
            except Exception as error:
                logger.error(f"Error parsing JSON from {url}: {str(error)}")
                pass
        return {}

    def _match_strings(self, value1: str, value2: str) -> bool:
        '''Sometimes artists are not in the same order or one might be missing. 
        Check if two artist strings are similar enough to be considered the same artist.'''
        # Split the artist strings into sets of lower case individual elements
        set1 = set(value1.lower().split())
        set2 = set(value2.lower().split())
        # Calculate the number of common elements
        common_elements = len(set1.intersection(set2))
        # Calculate the percentage overlap
        try:
            percentage_overlap = (common_elements / min(len(set1), len(set2))) * 100
        except ZeroDivisionError:
            return False
        # Check if the percentage overlap is greater than 75%
        # tune this value to be higher if matches are not accurate enough
        return percentage_overlap > 75

    def _strip_paren_words(self, value: str) -> str:
        '''Remove words in parentesis from the string'''
        return re.sub(r'\([^)]*\)', '', value)

    def _get_data(self, meta: Meta) -> Tuple[str, str, dict, bool]:
        norm_artist = self.artist_normalizer.normalize(meta.artist)
        norm_album = self.album_normalizer.normalize(meta.album)
        norm_title = self.album_normalizer.normalize(meta.title)

        # # 0th search, using attributes
        # info = self._query(norm_artist, norm_album, norm_title, True)
        # logger.debug(f"Attribute search query: {norm_artist}, {norm_album}, {norm_title}")
        # if info.get('resultCount') > 0:
        #     logger.debug(f"0st search info: {info}")
        #     return (norm_artist, norm_album, info, len(norm_album) == 0)

        # 1st search, with all artists
        info = self._query(norm_artist, norm_album, norm_title)
        logger.debug(f"Search query: {norm_artist}, {norm_album}, {norm_title}")
        if info.get('resultCount') > 0:
            logger.debug(f"1st search info: {info}")
            return (norm_artist, norm_album, info, len(norm_album) == 0)

        # 2nd search, if any (parenthesis words) in the TITLE, try again without those words
        if "(" in meta.title:
            s_norm_title = self.artist_normalizer.normalize(self._strip_paren_words(meta.title))
            info = self._query(norm_artist, norm_album, s_norm_title)
            logger.debug(f"Search query: {norm_artist}, {norm_album}, {s_norm_title}")
        if info.get('resultCount') > 0:
                logger.debug(f"2nd search info: {info}")
                return (norm_artist, norm_album, info, len(norm_album) == 0)

        # 3rd search, try a search with each individual artist
        album_artists = meta.artist.split(",")
        for a_artist in album_artists:
            norm_a_artist = self.artist_normalizer.normalize(a_artist)
            info = self._query(norm_a_artist, norm_album, norm_title)
            if info.get('resultCount') > 0:
                logger.debug(f"3rd search info: {info}")
                return (norm_a_artist, norm_album, info, len(norm_album) == 0)
            
        # 4nd search, if any (parenthesis words) in the ALBUM, try again without those words
        if "(" in meta.album:
            s_norm_album = self.artist_normalizer.normalize(self._strip_paren_words(meta.album))
            info = self._query(norm_artist, s_norm_album, norm_title)
            logger.debug(f"Search query: {norm_artist}, {s_norm_album}, {norm_title}")
            if info.get('resultCount') > 0:
                logger.debug(f"4th search info: {info}")
                return (norm_artist, s_norm_album, info, len(s_norm_album) == 0)

        # 5th search, if no results found yet, try deromanizer
        logger.debug("No results found yet, trying deromanizer")
        artist = self.deromanizer.convert_all(norm_artist)
        album = self.deromanizer.convert_all(norm_album)
        info = self._query(artist, album, norm_title)
        return (artist, album, info, len(album) == 0)

    def download(self, meta: Meta, art_path: str) -> bool:
        (meta_artist, meta_album, info, title_only) = self._get_data(meta)
        logger.debug(f"Meta artist: {meta_artist}, Meta album: {meta_album}, Info: {info}, Title only: {title_only}")
        if info:
            try:
                art = ""
                # go through albums, use exact match or first contains match if no exacts found
                results = reversed(info.get('results'))
                if title_only:
                    # if no album name provided, use earliest matching release
                    results = reversed(sorted(results, key=lambda x: x.get('releaseDate')))
                for album_info in results:
                    artist = self.artist_normalizer.normalize(album_info.get('artistName'))
                    album = self.album_normalizer.normalize(album_info.get('collectionName'))
                    if not self._match_strings(artist, self.artist_normalizer.normalize(meta_artist)):
                        logger.debug(f"Skipping album {album} by {artist} - {meta_artist} - artist mismatch")
                        continue
                    if not self._match_strings(album, self.album_normalizer.normalize(meta_album)):
                        logger.debug(f"Skipping album by {artist} - {album} - album mismatch")
                        continue
                    art = album_info.get('artworkUrl100').replace('100x100bb', self.file_suffix)
                    if not title_only and meta_album == album:
                        logger.debug(f"Exact album match found: {meta_album} - {album}: {album_info}")
                        break # exact match found
                if art:
                    logger.debug(f"Downloading album art for {meta_artist} - {meta_album} - {meta.title}")
                    image_data = self._urlopen_safe(art)
                    with open(f'{art_path}{album_info["collectionId"]}.jpg', 'wb') as file:
                        file.write(image_data)
                    return image_data, album_info

            except Exception as error:
                logger.error(f"Error encountered when downloading for artist ({meta_artist}) and album ({meta_album})")
                logger.error(album_info)
                logger.error(error)

        logger.debug(f"Failed to find matching artist ({meta_artist}) and album ({meta_album})")
        return False

