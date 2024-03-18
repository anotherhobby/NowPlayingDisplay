import time

class NowPlayingState:
    """
    Class to represent and manage the current state of the music player.
    """
    def __init__(self):
        self.update = False
        self.album = ""
        self.artist = []
        self.title = ""
        self.tracks = []
        self.duration = ""
        self.elapsed = ""
        self.npclient = ""
        self.previous_state = "startup"
        self.player_state = "stopped"
        self.displayed_album = ""
        self.state_lock = False
        self.art_url = ""
        self.debug = False
        self.last_update_time = time.time()-60 # clients
        self.api_payloads = [self.get_empty_payload()]
        self.last_payload = self.get_empty_payload()
        self.epoc_start = time.time()  # Track the time the album started

    def set_last_update_time(self):
        self.last_update_time = time.time()
    
    def get_last_update_time(self):
        return self.last_update_time

    def set_album(self, album):
        self.album = album

    def set_art_url(self, art_url):
        self.art_url = art_url

    def get_art_url(self):
        return self.art_url

    def get_album(self):
        return self.album

    def set_artist(self, artist):
        self.artist = artist

    def get_artist(self):
        return self.artist

    def set_title(self, title):
        self.title = title

    def get_title(self):
        return self.title
    
    def set_npclient(self, npclient):
        self.npclient = npclient
    
    def get_npclient(self):
        return self.npclient

    def set_tracks(self, tracks: list):
        print(f"Setting tracks: {tracks}")
        self.tracks = tracks

    def set_elapsed(self, elapsed):
        current_time = int(time.time())
        # get the time the album started
        self.epoc_start = current_time - self._time_to_seconds(elapsed)
        self.elapsed = elapsed
        return

    def get_elapsed(self):
        return self.elapsed

    def set_duration(self, duration):
        self.duration = duration

    def get_duration(self):
        return self.duration

    def set_debug(self, debug):
        self.debug = debug

    def set_last_payload(self, payload):
        self.last_payload = payload

    def get_last_payload(self):
        return self.last_payload

    def get_empty_payload(self):
        return {
            "album": "",
            "artist": "",
            "title": "",
            "duration": "",
            "elapsed": "",
            "state": "",
            "npclient": ""
        }

    def get_tracks(self):
        return self.tracks

    def add_api_payload(self, payload):
        self.api_payloads.append(payload)

    def get_api_payload(self):
        # Get the most recent payload, remove it from the list, and return it
        try:
            payload = self.api_payloads.pop(0)
        except:
            payload = self.get_empty_payload()
        return payload

    def _time_to_seconds(self, time_str):
        # Convert time string in mm:ss format to seconds
        try:
            minutes, seconds = map(int, str(time_str).split(':'))
        except:
            minutes, seconds = 0, 0
        return minutes * 60 + seconds

    def get_epoc_elapsed(self):
        # Get the elapsed time using epoc and add 2 seconds of delay
        try:
            total_elapsed_seconds = int(time.time() - self.get_epoc_start())
        except:
            total_elapsed_seconds = 0
        elapsed_minutes = total_elapsed_seconds // 60
        elapsed_seconds = total_elapsed_seconds % 60
        elapsed = f"{elapsed_minutes}:{elapsed_seconds:02d}"
        # if elapsed time is greater than the duration, set the elapsed time to the duration
        if total_elapsed_seconds > self._time_to_seconds(self.get_duration()):
            elapsed = self.get_duration()
            # we want to set the display to go inactive here!
        return elapsed

    def get_epoc_start(self):
        return self.epoc_start

    def set_previous_state(self, previous_state):
        self.previous_state = previous_state

    def set_player_state(self, state):
        state_updates = ["playing", "paused", "stopped", "completed", "idle", "startup"]
        if state.lower() not in state_updates:
            print(f"Invalid state: set_player_state({state})")
            return
        self.set_previous_state(self.player_state)
        self.player_state = state.lower()

    def get_player_state(self):
        return self.player_state

    def update_state(self):
        # use a lock to prevent multiple threads from updating the state at the same time
        while self.state_lock:
            time.sleep(0.1)
        self.state_lock = True
        result = self._update_state()
        self.state_lock = False
        return result

    def _update_state(self):
        # if the contents of the last api payload are different from the current state,
        # then update the state from the payload and return True, else return False
        payload = self.get_api_payload()
        if payload == self.get_empty_payload():
            return False
        elif payload != self.get_last_payload():
            self.set_last_payload(payload)
            self.set_title(payload["title"])
            self.set_artist(payload["artist"])
            self.set_album(payload["album"])
            self.set_npclient(payload["npclient"])
            if payload["state"] == "playing":
                # only update the elapsed time if the player is active or playing
                self.set_duration(payload["duration"])
                self.set_elapsed(payload["elapsed"])
            self.set_player_state(payload["state"])
            if "art_url" in payload:
                self.set_art_url(payload["art_url"])
            else:
                self.set_art_url("")
            self.set_last_update_time()
            return True
        else:
            return False

    def get_data(self):
        data = {
            "album": self.get_album(),
            "artist": self.get_artist(),
            "title": self.get_title(),
            "duration": self.get_duration(),
            "elapsed": self.get_elapsed(),
            "state": self.get_player_state(),
            "art_url": self.get_art_url(),
            "npclient": self.npclient
        }
        return data

    def get_artist_multi_line(self):
        if len(self.artist) > 1:
            if len(self.artist) < 5:
                return "\n".join(self.artist)
            else:
                # too many lines for the display space, use commas
                return ", ".join(self.artist)
        else:
            return self.artist[0]

    def get_displayed_album(self):
        return self.displayed_album
    
    def set_displayed_album(self, album):
        self.displayed_album = album

    def get_artist_str(self):
        if len(self.artist) > 1:
            return ", ".join(self.artist)
        else:
            return self.artist[0]

    def get_previous_state(self):
        return self.previous_state
