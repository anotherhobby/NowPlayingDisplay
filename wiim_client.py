import time
import upnpclient
import xmltodict
import requests
from npstate import NowPlayingState
try:
    from npsettings_local import npapi_address, npapi_port, wiim_address
except ImportError:
    from npsettings import npapi_address, npapi_port, wiim_address

np_client = "wiim"
np = NowPlayingState()
wiim = upnpclient.Device(f"http://{wiim_address}:49152/description.xml")


def now_playing():
    '''
    main loop function.
    Collects now playing information by polling the WiiM player, and then sends it to the NowPlayingDisplay server.
    '''

    info = poll_wiim_info()

    send_update = False
    if info["title"] != np.get_title() or info["state"] != np.get_player_state():
        np.set_player_state(info["state"])
        np.set_title(info["title"])
        np.set_artist(info["artist"])
        np.set_album(info["album"])
        np.set_duration(info["duration"])
        np.set_art_url(info["art_url"])
        np.set_elapsed(increment_time(info["elapsed"]))
        send_update = True
    else:
        if time.time() - int(np.last_update_time) >= 10:
            np.set_elapsed(increment_time(info["elapsed"]))
            np.set_duration(info["duration"])
            send_update = True

    if send_update:
        status = post_now_playing(np.get_data())
    else:
        status = True

    return status


def increment_time(time, seconds=1):
    """
    Increment  time by the specified number of seconds.

    Args:
        time_elapsed (str): Time in the format "mm:ss".
        seconds (int, optional): The number of seconds to increment. Defaults to 1.

    Returns:
        str: The updated time in the format "mm:ss".
    """
    m, s = map(int, time.split(':'))
    return f"{m + (s + seconds) // 60}:{(s + seconds) % 60:02d}"


def poll_wiim_info():
    # Get the current state of the WiiM player
    # always returns a valid dictionary
    try:
        info = wiim.AVTransport.GetInfoEx(InstanceID="0")
    except Exception as e:
        print(e)
        info = {}

    try:
        meta = xmltodict.parse(info["TrackMetaData"])["DIDL-Lite"]["item"]
    except:
        meta = {}
    state = info.get("CurrentTransportState", "stopped").lower()
    if state == "paused_playback":
        state = "paused"
    elapsed = strip_lead_zeros(info.get("RelTime", "0:00")[3:])
    duration = strip_lead_zeros(info.get("TrackDuration", "0:00")[3:])
    title = meta.get("dc:title", "")
    artist = meta.get("upnp:artist", "")
    album = meta.get("upnp:album", "")
    art = meta.get("upnp:albumArtURI", "")
    art_url = art.get("#text") if isinstance(art, dict) else art

    return {
        "state": state,
        "title": title,
        "duration": duration,
        "elapsed": elapsed,
        "artist": artist.split(","),
        "album": album,
        "art_url": art_url
    }


def strip_lead_zeros(time_str):
    if time_str[0] == "0":
        return time_str[1:]

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