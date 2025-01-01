import io
import json
import logging
import sys
import os
import re
import signal
import time
import hashlib
from threading import Thread
from tkinter import Tk

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, jsonify, request
from PIL import Image, ImageTk
from thefuzz import process

from get_cover_art.cover_finder import DEFAULTS, CoverFinder, Meta
from npstate import NowPlayingState
from npdisplay import NowPlayingDisplay
from npmusicdata import MusicDataStorage
from nputils import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from npsettings_local import *
except ImportError:
    logger.error("local config not found, using default")
    from npsettings import *

tk = Tk()
npui = NowPlayingDisplay(tk, tk.winfo_screenwidth(), tk.winfo_screenheight())
state = NowPlayingState()
finder = CoverFinder(debug=DEBUG)
npapi = Flask(__name__, template_folder='www')
tk.config(cursor="none")

CODE_PATH = os.path.dirname(os.path.abspath(__file__))
missing_art = Image.open(os.path.join(CODE_PATH, 'images/missing_art.png'))
npui.set_debug(DEBUG)
state.set_debug(DEBUG)
running = True
monitor = True


def display_setup():
    ''' Finish setting up the display for the Now Playing UI '''
    tk.title('NowPlayingDisplay')
    tk.attributes("-fullscreen",True)
    tk.config(bg='#000000')
    tk.columnconfigure(1, weight=2)
    tk.columnconfigure(2, weight=0)
    
    # Force the window to be in the foreground
    tk.focus_force()
    tk.lift()  # Lift the window to the top

    logger.debug(f"Display setup complete. Resolution: {tk.winfo_screenwidth()}x{tk.winfo_screenheight()}")


def fetch_album():
    ''' Get album art and data from Apple Music '''
    DEFAULTS['art_size'] = "1000"
    artist = state.get_artist_str()
    album = state.get_album()
    meta = Meta(artist=artist, album=album, title=state.get_title())
    art_path = os.path.join(CODE_PATH, f'album_images/')
    if not os.path.exists(art_path):
        os.makedirs(art_path)

    result = finder.download(meta, art_path)
    
    if result is not None:
        album_art, data = result
        state.set_album_id(data.get('collectionId', ""))
        album_title = data.get('collectionName', album)
        if "*" in album_title: # apple music uses a * on explicit titles
            if "*" not in album:
                album_title = album

        # use the artist name from the Apple Music album data if available
        apple_artist = data.get('artistName', "")
        if apple_artist != "":
            state.set_artist(apple_artist.split(","))
        album_url = data.get("collectionViewUrl", "")
        return album_art, album_title, album_url
    else:
        return None


def fetch_serialized_server_data(url):
    '''
    Fetches the serialized server data from the given URL
    '''
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'type': 'application/json', 'id': 'serialized-server-data'})
        if script_tag:
            serialized_data = script_tag.string
            return serialized_data
        else:
            logger.error("Serialized server data not found on the page.")
            return None

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching data:", e)
        return None


def apple_album_data(album_url : str) -> dict:
    ''' Get album data from the Apple Music album page '''
    serialized_data = fetch_serialized_server_data(album_url)
    track_data = []
    released = ""
    duration = ""
    if serialized_data is not None:
        sections = json.loads(serialized_data)[0]["data"]["sections"]
        for item in sections:
            if item["itemKind"] == "trackLockup":
                for track in item["items"]:
                    track_data.append(track["title"])
            if item["itemKind"] == "containerDetailTracklistFooterLockup":
                try:
                    description = item['items'][0]['description'].split("\n")
                    released = description[0]
                    duration = description[1].split("Songs, ")[1]
                except Exception as e:
                    logger.error(e)
                    pass
    return {"tracks": track_data, "released": released, "duration": duration}


def current_track():
    ''' Get the current track number out of the list of tracks '''
    if len(state.get_tracks()) == 0:
        return ""

    # use fuzzy to match the current track to the list of tracks
    track = process.extractOne(state.get_title(), state.get_tracks())
    if track is not None:
        # get the index of the track in the list of tracks
        index = state.get_tracks().index(track[0]) + 1
        return f"{index} of {len(state.get_tracks())}"

    # old method of matching tracks, will be removed in the future if fuzzy matching works well
    tracks = state.get_tracks() or []
    if len(tracks) == 0:
        return ""
    for index, name in enumerate(tracks, start=1):
        if name.lower() == state.get_title().lower():
            return f"{index} of {len(tracks)}"
        if name.lower() in state.get_title().lower():
            return f"{index} of {len(tracks)}"
        if strip_paren_words(name.lower()) == strip_paren_words(state.get_title().lower()):
            return f"{index} of {len(tracks)}"

    return f"? of {len(tracks)}"


def split_lines(text):
    # Check if there's a parenthesis with a space before it
    if " (" in text:
        text = text.split(" (", 1)  # Only split on the first occurrence
        return f"{text[0]}\n({text[1]}"
    if ": " in text:
        text = text.split(": ", 1)  # Only split on the first occurrence
        return f"{text[0]}:\n{text[1]}"
    return text


def strip_paren_words(value: str) -> str:
    '''Remove words in parentesis from the string'''
    result = re.sub(r'\([^)]*\)', '', value)
    return result.strip()

def clear_display():
    '''Clear all text fields on the display'''
    logger.debug("clearing display")
    npui.set_title("")
    npui.set_artist("")
    npui.set_album("")
    npui.set_track("")
    npui.set_duration_and_elapsed("", "")
    npui.set_album_released("")
    npui.set_album_duration("")
    npui.set_artwork(mk_album_art(missing_art))
    tk.update()

def np_mainloop():
    ''' Main loop for the Now Playing display, updates the display with new information every second'''
    logger.debug("waiting for the display to be ready...")
    display_setup()
    clear_display()
    old_title = ""
    old_album = ""
    old_album_art_path = ""
    album_for_current_art = ""
    new_art = True #tells the disiplay to refresh the art or not
    
    art_path = os.path.join(CODE_PATH, f'album_images/')
    if not os.path.exists(art_path):
        os.makedirs(art_path)

    loop_time = 1.0
    fast_loop_time = FAST_LOOP_TIME

    #ensure that 0 < fast_loop_time <= loop_time
    if (fast_loop_time > loop_time) or (FAST_LOOP_TIME <= 0):
        fast_loop_time = loop_time

    display_is_active = True

    while running:
        try:
            #sleep for a minimum of fast_loop_time
            time.sleep(fast_loop_time)

            #sleep longer if no update has been published
            if not state.update_state():
                #if no new data is available, sleep for longer
                #fast_loop_time is guaranteed to be between 0 and loop_time
                if display_is_active:
                    npui.set_duration_and_elapsed(state.get_duration(), state.get_epoc_elapsed())
                time.sleep(loop_time - fast_loop_time)
                continue
            
            #determine if the display should be active or inactive
            if state.get_player_state() == "playing" and not display_is_active:
                logger.debug("SETTING ACTIVE")
                npui.set_active()
                display_is_active = True
            elif state.get_player_state() != "playing" and display_is_active:
                logger.debug("SETTING INACTIVE")
                npui.set_inactive() # set the display to inactive (dim)
                keep_recent_files(art_path, MAX_STORED_ALBUM_IMAGES)
                display_is_active = False

            #get the title of the currently playing track
            title = state.get_title()
            album = state.get_album()
            if (title is not None) and ((title != old_title) or (album != old_album)): # the song title or album has changed, update the display
                old_title = title
                old_album = album
                logger.debug(f"Title or Album has changed: {title} {album}")

                if title == "" or (state.get_player_state() != "playing" and display_is_active):
                    npui.set_inactive() # set the display to inactive (dim)
                    display_is_active = False
                    continue
                try:
                    #go through each npclient
                    if state.get_npclient() == "wiim":
                        #get the art url, find the sha, set the filename to be that
                        art_url = state.get_art_url()
                        art_url_hash = hashlib.sha256(art_url.encode('utf-8')).hexdigest()
                        album_art_path = str(art_path) + art_url_hash + ".png" #the filename will be the sha of the art URL

                        album_image_to_show = None

                        if not os.path.exists(album_art_path): #album art doesn't exist for the given URL
                            if "tidal" in art_url: #substitute default resolution 680x680 to 1080x1080, works for tidal
                                pattern = r'\d{3,4}x\d{3,4}'
                                art_url = re.sub(pattern, '1080x1080', art_url)
                            
                            #get the new image
                            with requests.get(art_url, stream=True) as response:
                                if response.status_code == 200:
                                    with Image.open(response.raw) as image:
                                        logger.debug(f"downloading new album art")
                                        # Convert image to RGBA format to ensure 32-bit depth
                                        image = image.convert("RGBA")
                                        album_image_to_show = image
                                        if "tidal" in art_url: #save for tidal (can test for other URLs that are worth saving)
                                            image.save(album_art_path)
                                    new_art = True
                        else:
                            logger.debug(f"already had album art downloaded")
                            if old_album_art_path != album_art_path:
                                with Image.open(album_art_path) as image:
                                    album_image_to_show = image.copy()
                                    old_album_art_path = album_art_path
                                new_art = True
                            else:
                                new_art = False
                    else:
                        pass #put other clients here, if desired
                        # try to get the album art and data from Apple Music

                    if USE_APPLE_DOWNLOADER:
                        result = fetch_album()

                        if result is not None:
                            art, album, album_url = result
                            # set the album art to the new image
                            if not os.path.exists(album_art_path): 
                                npui.set_artwork(mk_album_art(io.BytesIO(art)))
                                logger.debug(f"set fallback apple image for album: {state.get_album()}")
                
                            #album_for_current_art = album
                            album_data = apple_album_data(album_url)
                            state.set_tracks(album_data["tracks"])
                            npui.set_album_released(album_data["released"])
                            #npui.set_album_duration(album_data["duration"])                            
                        else:
                            logger.debug("No album art found")
                            # if album art is provided, use it for the missing art, otherwise use the default missing art
                            if album_for_current_art != "":
                                image_data = finder.downloader._urlopen_safe(state.get_art_url())
                                npui.set_artwork(mk_album_art(io.BytesIO(image_data)))
                            else:
                                logger.debug("No album art found, using default")
                                npui.set_artwork(mk_album_art(missing_art))
                            album_for_current_art = state.get_album()
                            state.set_tracks([])
                            npui.set_album_released("")
                            npui.set_album_duration("") 

                except Exception as e:
                    # generic exception handling, print the exception and continue
                    logger.error(e)
                    pass

                # set song title on the display
                npui.set_title(split_lines(title))
                
                # set the artist on the display
                npui.set_artist(state.get_artist_multi_line())

                # set the album on the display
                npui.set_album(split_lines(state.get_album()))
                
                track = current_track()
                state.set_track(track.split(" ")[0])
                npui.set_track(track)
                
                if new_art:
                    if album_image_to_show:
                        npui.set_artwork(mk_album_art(album_image_to_show))
                    else:
                        npui.set_artwork(mk_album_art(missing_art))

                del album_image_to_show

            if display_is_active: #put any tasks here that should run every time the display updates
                #this will also run when the regular "duration sync" occurs, around 10s by default
                #duration and elapsed are updated, along with the active text colour and art mask (for dimming)
                npui.set_active()
                npui.set_duration_and_elapsed(state.get_duration(), state.get_epoc_elapsed())
            
            tk.update_idletasks() 
            tk.update()

        except Exception as e:
            logger.error(e)

def mk_album_art(image):
    # Resize the original image to the screen height
    original_art = None

    # Create a copy of the resized image
    original_art = ImageTk.PhotoImage(image.resize((tk.winfo_screenheight(), tk.winfo_screenheight())))

    return original_art


def signal_handler(sig, frame):
    # best effort to exit the program
    global running
    print('Exiting...')
    running = False
    tk.quit()
    sys.exit(0)


@npapi.route('/update-now-playing', methods=['POST'])
def update_now_playing():
    '''API endpoint for updating the now playing information on the display.'''
    # if screen is powered off, just return and don't process the request
    if False: #put code here that should block processing the api (such as checking if the display is off)
        logger.debug(f"display is powered off, not processing request")
        return jsonify({"message": "display is powered off"}), 200
    else:
        logger.debug(f"display is powered on, processing request")
    try:
        payload = request.json
        logger.debug(f"api received: {payload}")
    except Exception as e:
        logger.error(e)
        logger.error(request.data)
        return jsonify({"message": "Invalid JSON payload"}), 400
    # require all keys in the payload to be present
    if payload and all(key in payload for key in state.get_empty_payload()):
        # only allow updates from one client at a time
        if payload["npclient"] != state.get_npclient():
            logger.debug(f"client mismatch: {payload['npclient']} != {state.get_npclient()}")
            if state.get_npclient() != None: # no client yet?
                logger.debug(f"last update: {state.get_last_update_time()}")
                if time.time() - state.get_last_update_time() < 60: # 60s of inactivity required to switch clients
                    logger.debug(f"client mismatch, wait 60s")
                    return jsonify({"message": "Client mismatch, wait 60s"}), 400
        state.add_api_payload(payload)
        return jsonify({"message": "Payload received successfully"}), 200
    else:
        logger.debug(f"invalid payload: {payload}")
        return jsonify({"message": "Invalid payload"}), 400

@npapi.route('/')
def index():
    return render_template('index.html')

@npapi.route('/tracks')
def tracks():
    data = MusicDataStorage().retrieve_tracks()
    return render_template('tracks.html', data=data)

@npapi.route('/albums')
def albums():
    data = MusicDataStorage().retrieve_albums()
    return render_template('albums.html', data=data)

def start_api():
    '''Start the Flask API to accept requests to update the now playing information.'''
    flask_log = logging.getLogger('werkzeug')
    flask_log.setLevel(logging.ERROR)
    npapi.run(host='0.0.0.0', port=5432, threaded=True)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    if DEBUG:
        logger.setLevel(logging.DEBUG)

    logger.info("Starting API...")
    api_thread = Thread(target=start_api)
    api_thread.daemon = True  # Daemon threads automatically close when the main program exits
    api_thread.start()

    logger.info("Starting NowPlayingDisplay thread...")
    display_thread = Thread(target=np_mainloop)
    display_thread.daemon = True  # Set as a daemon thread
    display_thread.start()

    logger.info("Starting main display loop...")
    try:
        tk.mainloop()
    finally:
        running = False  # Safely signal threads to exit
        logger.info("Shutting down...")
        display_thread.join()  # Ensure threads finish execution
        api_thread.join()
