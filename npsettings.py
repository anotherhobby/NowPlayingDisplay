# This file contains the common settings that need to be configured
# This file is a template, with an explanation of what the config values do

# Copy this file into a new one called npsettings_local.py
# Put the IP address, location, font, etc that you want to use in there
# The values in this file serve as a fallback

npapi_port = 5432
npapi_address = "192.168.1.xxx" #this should be the IP address of the computer running the main now_playing.py program
wiim_address = "192.168.1.xxx" #this should be the IP address of your WiiM, if you are using one
tidal_client = "my-tidal"

screensaver_delay = 200 #the number of seconds before the screensaver starts

MAX_STORED_ALBUM_IMAGES = 10000

FAST_LOOP_TIME = 0.05 #how fast to run the main loop when there is no new data.
# Reduces the amount of latency when starting music or skipping songs
# Increase if you have performance issues

# Set main display colors
BACKGROUND_COLOR = "#000000"
HEADER_BACKGROUND_COLOR = "#000000"
HEADER_FOREGROUND_COLOR = "#CCCCCC"

# Set the color of text and progress bar while playing music at daytime
ACTIVE_TEXT_HEX = "#DCDCDC"
ACTIVE_PROGRESS_BAR_COLOR = "#424242"

# Set the level of dimming when paused.
# The mask will be applied to the album art (255 is fully black)
# The dimming fraction will be applied to the text and progress bar
INACTIVE_ART_MASK = 200
INACTIVE_DISPLAY_DIMMING_FRACTION = 0.35

#### DIMMING AFTER DUSK
# If configured, the display will dim the album art and screensaver after your local dusk time
# This feature can also be disabled if not desired - set MAX_DUSK_DIMMING_MASK to 0
# After the moment of sunset, the display will dim the album art and screensaver 
# to the MAX_DUSK_DIMMING_MASK over a duration of DIMMING_TIME_MINS
MAX_DUSK_DIMMING_MASK = 105 #The maximum mask that will be applied. Set to 0 to disable dimming. Set to 256 for maximum dimming (blackness)
MAX_SCREENSAVER_DUSK_DIMMING_MASK = 180
DIMMING_TIME_MINS = 60 # The number of minutes dimming will take. Dimming starts at dusk and linearly ramps over this duration to the final NIGHT_DIMMED values
NIGHT_DIMMED_TEXT_HEX = "#686868"
NIGHT_DIMMED_PBAR_HEX = "#424242"

# if you want to use sunset dimming, put your local latitude and longitude here
# use a site like latlong.net
# sample values are for Mexico City
LOCAL_LATITUDE = 19.4326
LOCAL_LONGITUDE = -99.1332


# whether to enable debug logging... it's quite verbose
DEBUG = True
USE_APPLE_DOWNLOADER = False
USE_SCREENSAVER = True

# these are the fonts that are used in the UI, they need to be installed on the system
# and can also be changed to other fonts if desired
primary_fontname = "Merriweather"
header_fontname = "Lato"
mono_fontname = "Noto Mono"