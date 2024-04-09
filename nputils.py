import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)


def display_on():
    try:
        # If the display is physically powered off, pygame will crash when quitting the screensaver.
        # Check if the display is on by running the xrandr command
        output = subprocess.check_output(['xrandr'], universal_newlines=True)
        sizeline = output.split('\n')[1]
        if int(sizeline.split()[-1][:-2]) > 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        logger.error("Error: Unable to execute xrandr command.")
        return True
    except Exception as e:
        logger.error("Error:", e)
        return True

def check_xrandr():
    # on startup, check if xrandr is available
    try:
        output = subprocess.check_output(['xrandr'], universal_newlines=True)
        return True
    except subprocess.CalledProcessError:
        logger.error("Error: Unable to execute xrandr command.")
        return False

