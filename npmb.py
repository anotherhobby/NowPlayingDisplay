import musicbrainzngs
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

class MusicBrainzSearch:
    def __init__(self, artists, album, title, duration, debug=False):
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        self.search_artists = artists
        self.search_album = album
        self.search_title = title
        self.search_duration = duration
        self.album = ""
        self.artists = ""
        self.title = ""
        self.album_duration = 0
        self.tracks = []
        self.release_id = ""
        self.release_date = None
        self.recording_data = {}
        self.release_data = {}
        self.front_cover = None
        self.back_cover = None
        self.art_path = ""
        self.succeeded = False
        self._setup()
        if self._search_recordings():
            self._get_release_by_id()
            self.succeeded = True

    def _setup(self):
        musicbrainzngs.set_useragent(
            "nowplayingdisplay",
            "0.1.1",
            "https://github.com/anotherhobby/NowPlayingDisplay",
        )
        self.art_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'album_images/')
        if not os.path.exists(self.art_path):
            os.makedirs(self.art_path)

    def _time_to_ms(self, time_str):
        # Convert time string in mm:ss format to seconds
        minutes, seconds = map(int, str(time_str).split(':'))
        total_seconds = minutes * 60 + seconds
        return total_seconds * 1000
    
    def _ms_to_time(self, ms):
        # Convert milliseconds to "mm:ss" format
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"
    
    def _set_album_duration(self, seconds):
        # Convert seconds to "hh hours, mm minutes" (and ignore seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours == 0:
            self.album_duration = f"{minutes} minutes"
        else:
            self.album_duration = f"{hours} hours, {minutes} minutes"

    def _search_recordings(self):
        logger.debug(f"Searching MusicBrainz for {self.search_title} ({self.search_duration}) by {self.search_artists} on {self.search_album}...")
        result = musicbrainzngs.search_recordings(
            artist=self.search_artists,
            release=self.search_album,
            recording=self.search_title,
            dur=self._time_to_ms(self.search_duration),
            format="Digital Media",
            limit=1
        )
        logger.debug(f"Search result: {result}")
        if len(result['recording-list']) == 0:
            logger.error(f"Could not find recording for {self.search_title} by {self.search_artists} on {self.search_album}")
            return False
        else:
            self.recording_data = result['recording-list'][0]
            self.title = self.recording_data['title']
            for release in self.recording_data['release-list']:
                if release['status'] == 'Official':
                    self.release_id = release['id']
                    return True
            logger.error(f"Could not find official release for {self.search_title} by {self.search_artists} on {self.search_album}")
            return False
        
    def _get_release_by_id(self):
        result = musicbrainzngs.get_release_by_id(
            self.release_id,
            includes=["artists", "recordings", "media"]
        )
        self.release_data = result
        self.album = self.release_data['release']['title']
        # release date will always be in "YYYY-MM-DD" format, want date format to to be "Month DD, YYYY"
        release_date = datetime.strptime(self.release_data['release']['date'], "%Y-%m-%d")
        self.release_date = release_date.strftime("%B %d, %Y")
        self.artists = self.release_data['release']['artist-credit-phrase']
        self._set_tracks()
        self._get_covers()

    def _set_tracks(self):
        # set track listing and add up the track lengths to get the album length
        album_length = 0
        for track in self.release_data['release']['medium-list'][0]['track-list']:
            album_length += int(track['length'])
            self.tracks.append(track['recording']['title'])
        self._set_album_duration(int(album_length / 1000))

    def _get_covers(self):
        if 'cover-art-archive' not in self.release_data['release']:
            return
        if self.release_data['release']['cover-art-archive']['front'] == 'true':
            try:
                self.front_cover = musicbrainzngs.get_image_front(self.release_id)
                # save the front cover image to the album_images directory
                logger.debug(f"Saving cover image to {self.art_path}{self.release_id}.jpg")
                with open(f'{self.art_path}{self.release_id}.jpg', 'wb') as file:
                    file.write(self.front_cover)
            except:
                self.front_cover = None
        if self.release_data['release']['cover-art-archive']['back'] == 'true':
            try:
                self.back_cover = musicbrainzngs.get_image_back(self.release_id)
            except:
                self.back_cover = None

    def get_album(self):
        return self.album
    
    def get_artists(self):
        return self.artists
    
    def get_title(self):
        return self.title
    
    def get_album_duration(self):
        return self.album_duration

    def get_tracks(self):
        return self.tracks
    
    def get_front_cover(self):
        return self.front_cover
    
    def get_back_cover(self):
        return self.back_cover
    
    def get_release_date(self):
        return self.release_date
    
    def get_success(self):
        return self.succeeded



# if __name__ == "__main__":
#     payload = {
#         'album': 'TIME TRAVELLERS II',
#         'artist': ['Jenova 7', 'Mr. Moods'],
#         'title': 'Visions (Original Mix)',
#         'duration': '4:42'
#     }
#     search = MusicBrainzSearch(
#         payload['artist'],
#         payload['album'],
#         payload['title'],
#         payload['duration']
#     )
#     print(json.dumps(search.recording_data, indent=4))
#     print(json.dumps(search.release_data, indent=4))

