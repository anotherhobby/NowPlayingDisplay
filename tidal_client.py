import json
import os
import subprocess
import time
from threading import Timer

import requests
from npstate import NowPlayingState

try:
    from npsettings_local import npapi_address, npapi_port, tidal_client
except ImportError:
    from npsettings import npapi_address, npapi_port, tidal_client

# tidal_watcher.py pushes now playing information to the now playing display API 
# every 10s and any time the TIDAL deskop player changes state. 

np = NowPlayingState()
now_playing_lock = False

parent_dir = os.path.dirname(os.path.realpath(__file__))


def process_log_message(message):
    if type(message) is bool:
        # Received boolean message, skipping...
        return
    if "signal" in message:
        if message["signal"] == "media.state":
            state = message["state"]
            if state == "active":
                state = "playing"
            now_playing()


def now_playing():
    '''
    Primary workflow thread.
    Gets now playing information by scraping the TIDAL user interface with applescript,
    then sends the information to the now playing display API
    '''
    global now_playing_lock
    if now_playing_lock:
        return False
    else:
        # scrape the Tidal user interface to get the current state information
        now_playing_lock = True
        now_playing = read_tidal_ui()
        
        # add state and time information to now_playing data
        if now_playing["state"] == "playing":
            now_playing["elapsed"] = increment_time_elapsed(now_playing["elapsed"])

        if now_playing["state"] in ["completed", "stopped"]:
            now_playing["elapsed"] = now_playing["duration"]
            now_playing["elapsed"] = "0:00"


        # post the now playing information to the now playing display API
        status = post_now_playing(now_playing)
        if not status:
            time.sleep(10)
        now_playing_lock = False
        return True


def increment_time_elapsed(time_elapsed, seconds=1):
    """
    Increment the elapsed time by the specified number of seconds.

    Args:
        time_elapsed (str): The elapsed time in the format "mm:ss".
        seconds (int, optional): The number of seconds to increment. Defaults to 1.

    Returns:
        str: The updated elapsed time in the format "mm:ss".
    """
    m, s = map(int, time_elapsed.split(':'))
    return f"{m + (s + seconds) // 60}:{(s + seconds) % 60:02d}"


def post_now_playing(now_playing):
    url = f'http://{npapi_address}:{npapi_port}/update-now-playing'
    headers = {'Content-Type': 'application/json'}
    data = {
        "album": now_playing["album"],
        "artist": now_playing["artist"],
        "title": now_playing["title"],
        "state": now_playing["state"],
        "elapsed": now_playing["elapsed"],
        "duration": now_playing["duration"],
        "npclient": tidal_client,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        np.set_last_update_time()
        return True
    except requests.exceptions.RequestException as e:
        # display is either off line, or another client is connected
        return False


def read_tidal_ui():
    # run the now-playing.scpt script to get the current title information
    # example JSON output from tidal-now-playing.scpt: 
    # {
    #   'album': 'THE JAZZ JOUSTERS SERIES VOL.1',
    #   'artist': ['Mr. Moods', 'The Jazz Jousters', 'Millennium Jazz Music'],
    #   'duration': '5:02',
    #   'elapsed': '3:34',
    #   'title': 'Love Is A Strange Thing',
    #   'state': 'playing'
    # }
    cmd = ['osascript', f'{parent_dir}/tidal-now-playing.applescript']
    while True:
        try:
            output = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
            now_playing = json.loads(output.stdout)
            if 'error' in now_playing:
                # the applescript failed to get the now playing information, try again
                time.sleep(1)
                continue
            return now_playing
        except Exception as e:
            print("Exception running now-playing.scpt: ", e)
            print("Received output:", output)
            time.sleep(1)
            continue


def check_inactivity():
    # we don't want more than 10 seconds to pass without pushing an update to now playing
    if time.time() - int(np.last_update_time) >= 10:
        now_playing()
    # check for inactivity every second
    Timer(1, check_inactivity).start()


if __name__ == "__main__":
    """
    Player state data is sourced from log messages, and the now playing information is sourced from the TIDAL UI.

    This script watches the TIDAL log file for JSON messages with state updates, and then responds to state changes 
    by running the now-playing.scpt AppleScript to get the current player information from the TIDAL UI.
    """
    try:
        home = os.path.expanduser("~")
        cmd = ['tail', '-f', f'{home}/Library/Logs/TIDAL/app.log']
        print("Starting Tidal Watcher with command: ", cmd)
        # start inactivity timer
        Timer(1, check_inactivity).start()
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            for line in process.stdout:
                # all JSON log messages start with a bracket and end with a bracket
                if line.startswith('['):
                    json_message = line
                    # keep moving the loop to the next line until the rest of the JSON message is captured
                    for line in process.stdout:
                        json_message += line
                        if line.startswith(']'):
                            process_log_message(json.loads(json_message)[0])
                            break
    except KeyboardInterrupt:
        process.terminate()
