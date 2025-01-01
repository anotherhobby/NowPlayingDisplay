import time
import upnpclient
import xmltodict
import requests
import unicodedata
import re
from npstate import NowPlayingState
try:
    from npsettings_local import npapi_address, npapi_port, wiim_address
except ImportError:
    from npsettings import npapi_address, npapi_port, wiim_address

np_client = "wiim"
np = NowPlayingState()
wiim = upnpclient.Device(f"http://{wiim_address}:49152/description.xml")

#list of exceptions of artists that should not be split despite containing a comma
exceptions = ["Tyler, The Creator", 
              "Earth, Wind & Fire", 
              "10,000 Maniacs", 
              "Crosby, Stills & Nash",
              "Crosby, Stills, Nash & Young", 
              "The Good, The Bad and The Queen",
              "Emerson, Lake & Palmer",
              "Faith, Hope & Charity",
              "Now, Now",
              "Blood, Sweat & Tears"]


def now_playing():
    '''
    main loop function.
    Collects now playing information by polling the WiiM player, and then sends it to the NowPlayingDisplay server.
    '''

    info = poll_wiim_info()

    send_update = False
    if info["title"] != np.get_title() or info["state"] != np.get_player_state() or info["album"] != np.get_album():
        np.set_player_state(info["state"])
        np.set_title(info["title"])
        np.set_artist(info["artist"])
        np.set_album(info["album"])
        np.set_duration(info["duration"])
        np.set_art_url(info["art_url"])
        np.set_elapsed(increment_time(info["elapsed"]))
        np.set_quality(info["quality"])
        send_update = True
    else:
        if time.time() - int(np.last_update_time) >= 10:
            np.set_elapsed(increment_time(info["elapsed"]))
            np.set_duration(info["duration"])
            send_update = True

    #if it is determined that we should send an update to the now_playing server, do so
    if send_update:
        status = post_now_playing(np.get_data())
    else:
        status = True

    return status


def increment_time(time, seconds=1):
    """
    Increment time by the specified number of seconds.

    Args:
        time (str): Time in the format "hh:mm:ss" or "mm:ss".
        seconds (int, optional): The number of seconds to increment. Defaults to 1.

    Returns:
        str: The updated time in the format "hh:mm:ss".
    """
    if time is not None:
        parts = list(map(int, time.split(':')))
        if len(parts) == 3:  # "hh:mm:ss" format
            h, m, s = parts
        elif len(parts) == 2:  # "mm:ss" format
            h, m, s = 0, *parts
        else:
            h, m, s = 0, 0, 0
    else:
        h, m, s = 0, 0, 0

    # Increment seconds and adjust minutes and hours
    s += seconds
    m += s // 60
    s = s % 60
    h += m // 60
    m = m % 60
    
    return f"{h:02}:{m:02}:{s:02}"

def poll_wiim_info():
    # Get the current state of the WiiM player
    # always returns a valid dictionary

    old_title = ""
    duration = "0:00"  # Initialize duration to a default value


    try:
        WiimInfo = wiim.AVTransport.GetInfoEx(InstanceID="0")
    except Exception as e:
        print(e)
        WiimInfo = {}

    PlayerState = WiimInfo.get("CurrentTransportState", "stopped").lower()

    if PlayerState == "paused_playback" or PlayerState == "no_media_present":
        PlayerState = "paused"

    try:
        TrackMetaData = xmltodict.parse(WiimInfo["TrackMetaData"])["DIDL-Lite"]["item"]
    except:
        TrackMetaData = {}
        
    title = TrackMetaData.get("dc:title", "")

    #extract track elapsed and duration
    try:
        elapsed = WiimInfo.get("RelTime", "0:00")
    except:
        elapsed = ""

    #if the title has changed, update the whole dictionary
    if title != old_title:

        duration = WiimInfo.get("TrackDuration", "0:00")
        artist = TrackMetaData.get("upnp:artist", "")
        album = TrackMetaData.get("upnp:album", "")

        if artist is not None:
            artist_list = split_artists(artist, exceptions)
        else:
            artist_list = None


        try: #song sample rate
            SampleRate = int(TrackMetaData['song:rate_hz'])/1000.0
        except:
            SampleRate = 0

        try: #song bitrate
            br = int(TrackMetaData['song:bitrate']) 
            bitrate = f"{br} kbps"
        except Exception as e:
            print(e)
            bitrate = ""

        try: #song bit depth
            depth = int(TrackMetaData['song:format_s'])
            if depth > 24:
                depth = 24
        except:
            depth = 0

        #try to get album art url
        try:
            arttmp = TrackMetaData["upnp:albumArtURI"]
            if isinstance(arttmp, dict):
                arturl = arttmp["#text"]
            else:
                arturl = arttmp
        except:
            arturl = ""

        old_title = title

    return {
        "state": PlayerState,
        "title": title,
        "duration": duration,
        "elapsed": elapsed,
        "artist": artist_list,
        "album": album,
        "art_url": arturl,
        "quality": f"{depth} bits / {SampleRate} kHz {bitrate}"
    }

def split_artists(artist_string, exceptions):
    # Dictionary to store placeholders and corresponding exception artist names
    placeholders = {}

    # Replace exceptions with placeholders
    for i, artist in enumerate(exceptions):
        placeholder = f"__ARTIST_{i}__"
        placeholders[placeholder] = artist
        artist_string = artist_string.replace(artist, placeholder)
    
    # Split the string on commas
    artist_list = [artist.strip() for artist in artist_string.split(',')]
        
    # Replace placeholders back with the original artist names
    for placeholder, artist in placeholders.items():
        artist_list = [a.replace(placeholder, artist) for a in artist_list]
        
    return artist_list


def post_now_playing(now_playing):
    url = f'http://{npapi_address}:{npapi_port}/update-now-playing'
    headers = {'Content-Type': 'application/json'}
    data = {
        "album": now_playing.get("album", ""),
        "artist": now_playing.get("artist", ""),
        "title": now_playing.get("title", ""),
        "state": now_playing.get("state", ""),
        "elapsed": now_playing.get("elapsed", ""),
        "duration": now_playing.get("duration", ""),
        "quality": now_playing.get("quality", ""),
        "art_url": now_playing.get("art_url", ""),
        "npclient": np_client,
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        np.set_last_update_time()
        return True
    except requests.exceptions.RequestException as e:
        print("Failed to send now playing update", e)
        return False
    

def main():
    while True:
        try:
            now_playing()
        except Exception as e:
            print(e)
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()