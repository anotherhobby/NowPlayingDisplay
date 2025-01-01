import subprocess
import logging
from datetime import datetime, timedelta
from astral.sun import sun
from astral import LocationInfo
from datetime import datetime, timezone
from tzlocal import get_localzone, get_localzone_name
import pytz
import heapq
import glob
import os
import re
import unicodedata
import string

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

try:
    from npsettings_local import *
except ImportError:
    logger.error("local config not found, using default")
    from npsettings import *
    
if DEBUG:
    logger.setLevel(logging.DEBUG)

#get local timezone (assume this doesn't change during runtime)
try: 
    local_timezone = get_localzone_name()
except Exception as e:
    local_timezone = None
    logger.error(e)

def keep_recent_files(folder_path, keep=10000):
    # Get a list of all PNG files in the folder with their last access time
    files = [(os.path.getatime(f), f) for f in glob.glob(os.path.join(folder_path, "*.png"))]

    # Sort by access time and keep the most recent files
    if len(files) > keep:
        files_to_delete = heapq.nsmallest(len(files) - keep, files)
    
        # Delete the files that are not among the most recent "keep" (default 10,000)
        for _, file_path in files_to_delete:
            os.remove(file_path)
            print(f"Deleted {file_path}")

def hex_to_rgb(hex_color):
    """Convert a hex color string (e.g., '#F5F5F5') to an RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color):
    """Convert an RGB tuple to a hex color string."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb_color)

def interpolate_color_fraction(color1, color2, fraction):
    """
    Linearly interpolate between two RGB colors.
    
    Args:
        color1 (tuple): The starting RGB color (e.g., (245, 245, 245)).
        color2 (tuple): The ending RGB color (e.g., (98, 98, 98)).
        fraction (float): The fraction between 0 and 1 representing the interpolation percentage.
        
    Returns:
        tuple: The interpolated RGB color.
    """
    return tuple(round(c1 + (c2 - c1) * fraction) for c1, c2 in zip(color1, color2))

def calculate_dimming_mask():
    dimming_fraction = get_dimming_fraction()
    dimming_mask = round(dimming_fraction * MAX_DUSK_DIMMING_MASK)
    #maximum mask to apply - 0 = no dimming, 256 = total blackness
    if dimming_mask < 0:
        dimming_mask = 0
    elif dimming_mask > 255:
        dimming_mask = 255
    return dimming_mask

def calculate_screensaver_dimming_mask():
    dimming_fraction = get_dimming_fraction()
    dimming_mask = round(dimming_fraction * MAX_SCREENSAVER_DUSK_DIMMING_MASK)
    #maximum mask to apply - 0 = no dimming, 256 = total blackness
    if dimming_mask < 0:
        dimming_mask = 0
    elif dimming_mask > 255:
        dimming_mask = 255
    return dimming_mask

def calculate_dimmed_hex(brightest_hex, dimmest_hex):
    dimming_fraction = get_dimming_fraction()

    if dimming_fraction <= 0:
        return brightest_hex
    elif dimming_fraction >= 1:
        return dimmest_hex
    else: #fraction is between 0 and 1
        # Convert hex colors to RGB tuples
        brightest_rgb = hex_to_rgb(brightest_hex)
        dimmest_rgb = hex_to_rgb(dimmest_hex)
        
        return rgb_to_hex(interpolate_color_fraction(brightest_rgb, dimmest_rgb, dimming_fraction))

def get_astral_times():
    if local_timezone is not None:
        local_time = datetime.now(pytz.timezone(local_timezone))
        city = LocationInfo(latitude=LOCAL_LATITUDE, longitude=LOCAL_LONGITUDE)
        sunset_info = sun(city.observer, date=local_time.date(), tzinfo=local_timezone)
        return sunset_info
    else:
        return None

def get_dimming_fraction():
    local_time = datetime.now(pytz.timezone(local_timezone))
    astral_times = get_astral_times()

    if astral_times is None:
        logger.debug(f"No time zone available, dimming is disabled")
        return 0
    elif astral_times['dawn'] < local_time < astral_times['dusk']:
        logger.debug(f"Before dusk, returning 0")
        return 0
    elif astral_times['dusk'] <= local_time or local_time <= astral_times['dawn']:
        # time is after dusk (dusk to midnight)
        #    or before dawn (midnight to dawn).
        # after midnight, dawn and dusk will both be in the future, but we must remain dim
        time_after_dusk = (local_time - astral_times['dusk']).total_seconds() / 60  # minutes
        time_before_dawn = (local_time - astral_times['dawn']).total_seconds() / 60 #minutes

        if time_after_dusk >= DIMMING_TIME_MINS or local_time <= astral_times['dawn']:
            return 1
        else:
            fraction = min((time_after_dusk / DIMMING_TIME_MINS), 1)
            logger.debug(f"Returning fraction {fraction}")
            return fraction
    else:
        #shouldn't get here
        logger.debug(f"Error in get_dimming_fraction, returning defaults")
        return 0

def set_hex_brightness(hex_color, brightness_fraction):
    # Remove the '#' from the beginning if it's there
    hex_color = hex_color.lstrip('#')

    if brightness_fraction > 1:
        brightness_fraction = 1
    elif brightness_fraction < 0:
        brightness_fraction = 0
    
    # Convert hex to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Multiple the brightness of each component by the fraction
    r = max(0, int(r * brightness_fraction))
    g = max(0, int(g * brightness_fraction))
    b = max(0, int(b * brightness_fraction))
    
    # Convert back to hex and return
    return f"#{r:02X}{g:02X}{b:02X}"

def sanitize_filename(album):
    # Normalize the string (decompose accents)
    normalized = unicodedata.normalize('NFD', album)
    
    # Remove accents
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Remove all special characters and spaces
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', without_accents)
    
    return sanitized