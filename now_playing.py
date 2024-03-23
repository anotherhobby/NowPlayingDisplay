import io
import json
import logging
import os
import re
import signal
import time
from threading import Thread
from tkinter import Tk

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from PIL import Image, ImageTk
from thefuzz import process

from get_cover_art.cover_finder import DEFAULTS, CoverFinder, Meta
from npstate import NowPlayingState
from npdisplay import NowPlayingDisplay
from npsettings import DEBUG


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tk = Tk()
npui = NowPlayingDisplay(tk, tk.winfo_screenwidth(), tk.winfo_screenheight())
state = NowPlayingState()
finder = CoverFinder(debug=DEBUG)
npapi = Flask(__name__)

CODE_PATH = os.path.dirname(os.path.abspath(__file__))
missing_art = os.path.join(CODE_PATH, 'images/missing_art.png')
npui.set_debug(DEBUG)
state.set_debug(DEBUG)
running = True


def display_setup():
    ''' Finish setting up the display for the Now Playing UI '''
    tk.title('NowPlayingDisplay')
    tk.attributes("-fullscreen",True)
    tk.config(bg='#000000')
    tk.columnconfigure(1, weight=2)
    tk.columnconfigure(2, weight=0)

    logger.debug("Display setup complete")


def fetch_album():
    ''' Get album art and data from Apple Music '''
    DEFAULTS['art_size'] = "1000"
    artist = state.get_artist_str()
    album = state.get_album()
    meta = Meta(artist=artist, album=album, title=state.get_title())
    art_path = os.path.join(CODE_PATH, f'album_images/')
    if not os.path.exists(art_path):
        os.makedirs(art_path)
    album_art, data = finder.download(meta, art_path)

    if album_art:
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
    tracks = state.get_tracks()
    for index, name in enumerate(tracks, start=1):
        if name.lower() == state.get_title().lower():
            return f"{index} of {len(tracks)}"
        if name.lower() in state.get_title().lower():
            return f"{index} of {len(tracks)}"
        if strip_paren_words(name.lower()) == strip_paren_words(state.get_title().lower()):
            return f"{index} of {len(tracks)}"

    return f"? of {len(tracks)}"


def split_lines(text):
    # if the title has parentheses, split the title into two lines with the parentheses on the second line
    if "(" in text:
        text = text.split(" (")
        return f"{text[0]}\n({text[1]}"
    if ": " in text:
        text = text.split(": ")
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
    npui.set_duration("")
    npui.set_elapsed("")
    npui.set_album_released("")
    npui.set_album_duration("")
    state.set_displayed_album("missing art")
    tk.update()



def np_mainloop():
    ''' Main loop for the Now Playing display, updates the display with new information every second'''
    old_title = ""
    album_for_current_art = ""
    logger.debug("waiting for the display to be ready...")
    display_setup()
    clear_display()
    missing_album, unused = mk_album_art(missing_art)
    npui.set_artwork(missing_album, missing_album)

    while running:
        tk.update()
        time.sleep(1)
        # update_state checks for new API payloads and updates the state if found
        if not state.update_state():
            # if the player is playing and state hasn't changed, only update progress
            if state.get_player_state() == "playing":
                npui.set_duration(state.get_duration())
                npui.set_elapsed(state.get_epoc_elapsed())
            continue

        try: # the player state has changed, update the display
            
            if state.get_player_state() == "playing":
                npui.set_active() # set the display to active (bright)
            else:
                npui.set_inactive() # set the display to inactive (dim)

            # update the elapsed/duration and progress bar
            npui.set_duration(state.get_duration())
            npui.set_elapsed(state.get_epoc_elapsed())

            title = state.get_title()
            if title != old_title:
                # the song title has changed, update the display
                logger.debug(f"Title has changed: {title}")
                old_title = title
                if title == "":
                    clear_display()
                    npui.start_screensaver(10)
                    continue

                # update the artist and duration on the display
                artist_text = state.get_artist_multi_line()
                npui.set_artist(artist_text)
                npui.set_duration(state.get_duration())

                # check if the album is still the same
                if state.get_displayed_album() == state.get_album():
                    logger.debug(f"Album is the same: {state.get_album()}")
                    pass
                else:
                    try:
                        # try to get the album art and data from Apple Music
                        art, album, album_url = fetch_album()
                        if art is not None:
                            # set the album art to the new image
                            active_artwork, inactive_artwork = mk_album_art(io.BytesIO(art))
                            npui.set_artwork(active_artwork, inactive_artwork)
                            state.set_displayed_album(state.get_album())
                            logger.debug(f"set image for album: {state.get_album()}")
                            album_for_current_art = album
                            album_data = apple_album_data(album_url)
                            state.set_tracks(album_data["tracks"])
                            npui.set_album_released(album_data["released"])
                            npui.set_album_duration(album_data["duration"])                            
                        else:
                            logger.debug("No album art found")
                            # if album art is provided, use it for the missing art, otherwise use the default missing art
                            if album_for_current_art != "":
                                image_data = finder.downloader._urlopen_safe(state.get_art_url())
                                active_artwork, inactive_artwork = mk_album_art(io.BytesIO(image_data))
                                npui.set_artwork(active_artwork, inactive_artwork)
                            else:
                                logger.debug("No album art found, using default")
                                state.set_displayed_album("missing art")
                                npui.set_artwork(missing_album, missing_album)
                            album_for_current_art = state.get_album()
                            state.set_tracks([])
                            npui.set_album_released("")
                            npui.set_album_duration("") 

                    except Exception as e:
                        # generic exception handling, print the exception and continue
                        logger.error(e)
                        pass

                    # update the album title on the display
                    npui.set_album(split_lines(album_for_current_art))

            # update the title & track on the display
            npui.set_title(split_lines(title))
            track = current_track()
            state.set_track(track.split(" ")[0])
            npui.set_track(track)

        except Exception as e:
            logger.error(e)


def mk_album_art(path):
    # Resize the original image to the screen height
    original_image = Image.open(path)
    original_image = original_image.resize((tk.winfo_screenheight(), tk.winfo_screenheight()))
    original_art = ImageTk.PhotoImage(original_image)

    # Create a copy of the original image
    dimmed_image = original_image.copy()

    # Apply a semi-transparent black overlay to create a dimmed effect
    overlay = Image.new('RGBA', dimmed_image.size, (0, 0, 0, 128))  # 50% transparent black overlay
    dimmed_image.paste(overlay, (0, 0), overlay)

    # Convert the dimmed image to PhotoImage
    dimmed_art = ImageTk.PhotoImage(dimmed_image)

    return original_art, dimmed_art



def signal_handler(sig, frame):
    # best effort to exit the program
    global running
    print('Exiting...')
    running = False
    tk.quit()
    os._exit(0)


@npapi.route('/update-now-playing', methods=['POST'])
def update_now_playing():
    '''API endpoint for updating the now playing information on the display.'''
    try:
        payload = request.json
        logger.debug(f"api received: {payload}")
    except Exception as e:
        logger.error(e)
        logger.error(request.data)
        return jsonify({"message": "Invalid JSON payload"}), 400

    # require all keys in the payload to be present
    if all(key in payload for key in state.get_empty_payload()):
        # only allow updates from one client at a time
        if payload["npclient"] != state.get_npclient():
            logger.debug(f"client mismatch: {payload['npclient']} != {state.get_npclient()}")
            if state.get_npclient() != None: # no client yet?
                logger.debug(f"last update: {state.get_last_update_time()}")
                if time.time() - state.get_last_update_time() < 60: # 60s of inactivity required to switch clients
                    logger.debug(f"client mismatch, wait 60s")
                    return jsonify({"message": "Client mismatch, wait 60s"}), 400
        state.add_api_payload(payload)
        return jsonify({"message": "Payload received successfully"})
    else:
        logger.debug(f"invalid payload: {payload}")
        return jsonify({"message": "Invalid payload"}), 400
    

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
    Thread(target=start_api).start()

    logger.info("Starting NowPlayingDisplay thread...")
    Thread(target=np_mainloop).start()

    logger.info("Starting main display loop...")
    tk.mainloop()