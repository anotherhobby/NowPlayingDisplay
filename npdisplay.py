from tkinter import Label, ttk
from PIL import Image, ImageEnhance, ImageTk
import logging
from screensaver import AlbumArtScreensaver
from nputils import *

try:
    from npsettings_local import *
except ImportError:
    from npsettings import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if DEBUG:
    logger.setLevel(logging.DEBUG)


class NowPlayingDisplay:
    """This class is for creating and updating the objects of the Now Playing screen."""
    def __init__(self, tk_instance, sw, sh):
        self.tk_instance = tk_instance
        self.fontsize = sh // 20
        self.header_fontsize = int(self.fontsize * 0.5)
        self.fontname = primary_fontname
        self.header_fontname = header_fontname
        self.mono_fontname = mono_fontname
        self.current_text_color = ACTIVE_TEXT_HEX
        self.current_pgbar_color = ACTIVE_PROGRESS_BAR_COLOR
        self.active_artwork = None
        self.screensaver_lock = False
        self.screensaver_after = None
        self.screensaver = None
        self.DEBUG = False

        # Row Configuration
        tk_instance.rowconfigure(0, weight=0) 
        tk_instance.rowconfigure(1, weight=3)  # title
        tk_instance.rowconfigure(2, weight=0)  # artist header
        tk_instance.rowconfigure(3, weight=3)  # artists
        tk_instance.rowconfigure(4, weight=0)  # album header
        tk_instance.rowconfigure(5, weight=3)  # album text
        tk_instance.rowconfigure(6, weight=0)  # track #/#
        tk_instance.rowconfigure(7, weight=0)  # elapsed and duration
        tk_instance.rowconfigure(8, weight=0)  # progress bar
        # Title (remove header for now)
        # self.title_header_lbl = Label(
        #     tk_instance,
        #     text="Title",
        #     anchor="sw",
        #     wraplength=sw-sh,
        #     justify="left",
        #     padx=0,
        #     pady=0,
        #     font=(self.header_fontname, self.header_fontsize),
        #     bg=HEADER_BACKGROUND_COLOR,
        #     fg=HEADER_FOREGROUND_COLOR
        # )
        # self.title_header_lbl.grid(row=1, column=1, columnspan=3, sticky="sew")

        self.title_lbl = Label(
            tk_instance,
            text="",
            anchor="nw",
            wraplength=(sw - sh) - ((sw - sh) * 0.1),
            justify="left",
            padx=50,
            pady=30,
            font=(self.fontname, self.fontsize, "bold"),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.title_lbl.grid(row=1, column=1, columnspan=3, sticky="new")

        # Artists
        self.artist_header_lbl = Label(
            tk_instance,
            text="Artists",
            anchor="sw",
            wraplength=sw-sh,
            justify="center",
            padx=50,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=BACKGROUND_COLOR,
            fg=HEADER_FOREGROUND_COLOR
        )
        self.artist_header_lbl.grid(row=2, column=1, columnspan=3, sticky="sew")

        self.artist_lbl = Label(
            tk_instance,
            text="",
            anchor="nw",
            wraplength=(sw - sh) - ((sw - sh) * 0.1),
            justify="left",
            padx=50,
            pady=0,
            font=(self.fontname, self.fontsize),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.artist_lbl.grid(row=3, column=1, columnspan=3, sticky="new")

        # Album
        self.album_header_lbl = Label(
            tk_instance,
            text="Album",
            anchor="w",
            wraplength=sw-sh,
            justify="left",
            padx=50,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=BACKGROUND_COLOR,
            fg=HEADER_FOREGROUND_COLOR
        )
        self.album_header_lbl.grid(row=4, column=1, columnspan=3, sticky="sew")

        #released date
        self.album_released_lbl = Label(
            tk_instance,
            text="",
            anchor="ne",
            wraplength=sw-sh,
            justify="right",
            padx=50,
            pady=0,
            font=(self.mono_fontname, self.header_fontsize),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.album_released_lbl.grid(row=5, column=1, columnspan=3, sticky="se")

        #album duration
        self.album_duration_lbl = Label(
            tk_instance,
            text="",
            anchor="sw",
            wraplength=sw-sh,
            justify="left",
            padx=50,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.album_duration_lbl.grid(row=5, column=1, columnspan=3, sticky="sw")

        #album name
        self.album_lbl = Label(
            tk_instance,
            text="",
            anchor="nw",
            wraplength=(sw - sh) - ((sw - sh) * 0.1),
            justify="left",
            padx=50,
            pady=0,
            font=(self.fontname, self.fontsize),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.album_lbl.grid(row=5, column=1, columnspan=3, sticky="new")

        # Track
        #track x of y
        self.track_lbl = Label(
            tk_instance,
            text="",
            anchor="nw",
            wraplength=(sw - sh) - ((sw - sh) * 0.1),
            justify="left",
            padx=50,
            pady=0,
            font=(self.mono_fontname, self.header_fontsize),
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.track_lbl.grid(row=6, column=1, columnspan=3, sticky="new")

        # Elapsed and Duration
        self.elapsed_lbl = Label(
            tk_instance,
            text="0:00",
            anchor="sw",
            font=(self.mono_fontname, self.header_fontsize),
            padx=50,
            pady=0,
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.elapsed_lbl.grid(row=7, column=1, columnspan=3, sticky="sw")

        #Duration of the track
        self.duration_lbl = Label(
            tk_instance,
            text="0:00",
            anchor="se",
            font=(self.mono_fontname, self.header_fontsize),
            padx=50,
            pady=0,
            bg=BACKGROUND_COLOR,
            fg=ACTIVE_TEXT_HEX
        )
        self.duration_lbl.grid(row=7, column=1, columnspan=3, sticky="se")

        # Progress Bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.Horizontal.TProgressbar",
            foreground="black",
            background=self.current_pgbar_color,
            troughcolor=BACKGROUND_COLOR,
            borderwidth=0
        )
        self.progress_bar = ttk.Progressbar(
            tk_instance,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.config(length=sw, value=0, maximum=100)
        self.progress_bar.grid(row=8, column=1, columnspan=3, sticky="es", ipady=sh//300)

        # Full Screen Album Art goes here!
        self.art_lbl = Label(
            tk_instance,
            image=None,
            bg=BACKGROUND_COLOR
        )
        self.art_lbl.grid(row=1, column=0, rowspan=8, sticky="nswe", padx=0, pady=0)

    def _time_to_seconds(self, time_str):
        try:
            parts = list(map(int, str(time_str).split(':')))
            if len(parts) == 3:
                hours, minutes, seconds = parts
            elif len(parts) == 2:
                hours = 0
                minutes, seconds = parts
            else:
                return 0
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0

    def _update_progress_bar(self, elapsed):
        # Convert elapsed and duration to seconds
        elapsed_seconds = self._time_to_seconds(elapsed)
        duration_seconds = self._time_to_seconds(self.get_duration())

        if duration_seconds == 0:
            self.progress_bar["value"] = 0
            return
        else:
            percentage_elapsed = (elapsed_seconds / duration_seconds) * 100
            self.progress_bar["value"] = percentage_elapsed

    def get_duration(self):
        return self.duration_lbl.cget("text")

    def set_debug(self, debug):
        self.DEBUG = debug

    def set_duration_and_elapsed(self, duration, new_elapsed):
        if duration is not None: #split duration into hh mm ss
            parts = duration.split(':')
            if len(parts) == 3:  # "hh:mm:ss" format
                dur_h, dur_m, dur_s = parts
            elif len(parts) == 2:  # "mm:ss" format
                dur_h, dur_m, dur_s = 0, *parts
            else:
                dur_h, dur_m, dur_s = 0, 0, 0
        else:
            dur_h, dur_m, dur_s = 0, 0, 0

        if new_elapsed is not None: #split elapsed into hh mm ss
            parts =  new_elapsed.split(':')
            if len(parts) == 3:  # "hh:mm:ss" format
                elap_h, elap_m, elap_s = parts
            elif len(parts) == 2:  # "mm:ss" format
                elap_h, elap_m, elap_s = 0, *parts
            else:
                elap_h, elap_m, elap_s = 0, 0, 0
        else:
            elap_h, elap_m, elap_s = 0, 0, 0

        #want to make sure that duration and elapsed have the same format
        #m:ss - m:ss
        #mm:ss - mm:ss
        #h:mm:ss - mm:ss
        #hh:mm:ss - hh:mm:ss

        if len(str(dur_h).lstrip('0')) == 2: #10+ hours long
            dur_label_text = f"{int(dur_h):02}:{int(dur_m):02}:{int(dur_s):02}"
            elap_label_text = f"{int(elap_h):02}:{int(elap_m):02}:{int(elap_s):02}"
        elif len(str(dur_h).lstrip('0')) == 1: #1-9 hours long
            dur_label_text = f"{int(dur_h):1}:{int(dur_m):02}:{int(dur_s):02}"
            elap_label_text = f"{int(elap_h):1}:{int(elap_m):02}:{int(elap_s):02}"
        elif len(str(dur_m).lstrip('0')) == 2: #10-59 minutes long")
            dur_label_text = f"{int(dur_m):02}:{int(dur_s):02}"
            elap_label_text = f"{int(elap_m):02}:{int(elap_s):02}"
        else: #less than 10 minutes long
            dur_label_text = f"{int(dur_m):1}:{int(dur_s):02}"
            elap_label_text = f"{int(elap_m):1}:{int(elap_s):02}"

        self.elapsed_lbl.config(text=elap_label_text)
        self.duration_lbl.config(text=dur_label_text)

        # update progress bar with new elapsed time
        self._update_progress_bar(new_elapsed)
    
    def set_title(self, new_title):
        self.fade_text(self.title_lbl, new_title)

    def set_artist(self, new_artist):
        self.fade_text(self.artist_lbl, new_artist)
        if "\n" in new_artist:
            self.fade_text(self.artist_header_lbl, "Artists")
        else:
            self.fade_text(self.artist_header_lbl, "Artist")

    def set_album(self, new_album):
        self.fade_text(self.album_lbl, new_album)
        self.fade_text(self.album_header_lbl, "Album")

    def set_album_released(self, new_album_released):
        self.album_released_lbl.config(text=new_album_released)
    
    def set_album_duration(self, new_album_duration):
        self.album_duration_lbl.config(text=new_album_duration)

    def set_artwork(self, active_artwork):
        if active_artwork is not None:
            self.active_artwork = active_artwork
            self.set_active_art_with_mask(calculate_dimming_mask())

    def set_track(self, track_text):
        self.track_lbl.config(text=track_text)

    def _update_foreground(self):
        # Update the text color of the labels
        self.album_header_lbl.config(fg=self.current_text_color)
        self.album_lbl.config(fg=self.current_text_color)
        self.album_released_lbl.config(fg=self.current_text_color)
        self.album_duration_lbl.config(fg=self.current_text_color)
        self.artist_header_lbl.config(fg=self.current_text_color)
        self.artist_lbl.config(fg=self.current_text_color)
        self.title_lbl.config(fg=self.current_text_color)
        self.track_lbl.config(fg=self.current_text_color)
        self.elapsed_lbl.config(fg=self.current_text_color)
        self.duration_lbl.config(fg=self.current_text_color)
        # Update the progress bar style's background color
        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar", background=self.current_pgbar_color)

    def start_screensaver(self, delay):
        self.screensaver_lock = True
        self.screensaver = AlbumArtScreensaver(debug=self.DEBUG)
        self.screensaver_after = self.tk_instance.after(delay*1000, self.screensaver.start)

    def _stop_screensaver(self):
        if self.screensaver:
            self.screensaver.stop()  # Ensure screensaver stops all background tasks
            self.screensaver = None
        self.tk_instance.after_cancel(self.screensaver_after)
        self.screensaver_lock = False

    def set_inactive(self):
        # dim the text color of the labels when the player is inactive
        if not self.screensaver_lock:
            self.current_text_color = set_hex_brightness(self.current_text_color, INACTIVE_DISPLAY_DIMMING_FRACTION)
            self.current_pgbar_color = set_hex_brightness(self.current_pgbar_color, INACTIVE_DISPLAY_DIMMING_FRACTION)
            self.set_active_art_with_mask(INACTIVE_ART_MASK)
            self._update_foreground()
            if USE_SCREENSAVER:
                self.start_screensaver(screensaver_delay)

    def set_active(self):
        # lighten the text color of the labels when the player is active
        self.set_current_text_color(calculate_dimmed_hex(ACTIVE_TEXT_HEX, NIGHT_DIMMED_TEXT_HEX))
        self.set_current_pbar_color(calculate_dimmed_hex(ACTIVE_PROGRESS_BAR_COLOR, NIGHT_DIMMED_PBAR_HEX))

        # use the active artwork if it is available
        if self.active_artwork:
            self.set_active_art_with_mask(calculate_dimming_mask()) 

        self._update_foreground()

        #stop the screensaver after 5 seconds, to give time for the main display to update
        #so as not to show a flash of incorrect data before updating
        if self.screensaver:
            self.tk_instance.after(5000, self._stop_screensaver)

        # Force the window to be in the foreground
        self.tk_instance.after(5000, self.tk_instance.focus_force)
        self.tk_instance.after(5000, self.tk_instance.lift)  # Lift the window to the top

    def set_current_text_color(self, color):
        self.current_text_color = color

    def set_current_pbar_color(self, color):
        self.current_pgbar_color = color

    def set_active_art_with_mask(self, mask):
        """
        Dim the image by applying a semi-transparent black overlay.
        dim_percentage: float between 0 (no dimming) and 100 (full dimming)
        """
        if self.active_artwork is not None:
            # Convert the Tkinter PhotoImage back to a PIL Image
            pil_image = ImageTk.getimage(self.active_artwork)
            
            # Create a black overlay with the desired opacity
            overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, mask))
            
            # Apply the overlay on top of the original image
            dimmed_image = Image.alpha_composite(pil_image, overlay)
            
            # Convert back to a PhotoImage for Tkinter
            dimmed_tkimage = ImageTk.PhotoImage(dimmed_image)

            # Update the label's image in place
            self.art_lbl.config(image=dimmed_tkimage)
            self.art_lbl.image = dimmed_tkimage  # Keep a reference to avoid garbage collection

    def fade_text(self, label, new_text, duration=200, steps=10):
        delay = duration // steps  # Delay between each step in milliseconds
        initial_color = label.cget("fg")  # Get the current foreground color
        faded_out_color = BACKGROUND_COLOR # Match background for fading out effect

        def fade_step(step):
            if step < steps:
                # Fade out
                color = self.interpolate_color(initial_color, faded_out_color, step / steps)
                label.config(fg=color)
                self.tk_instance.after(delay, fade_step, step + 1)
            elif step == steps:
                # Change text when fully faded out
                label.config(text=new_text)
                self.tk_instance.after(delay, fade_step, step + 1)
            elif step < 2 * steps:
                # Fade in
                color = self.interpolate_color(faded_out_color, initial_color, (step - steps) / steps)
                label.config(fg=color)
                self.tk_instance.after(delay, fade_step, step + 1)

        # Start the fade
        fade_step(0)

    def interpolate_color(self, color1, color2, t):
        """ Linearly interpolate between two colors. t goes from 0 to 1. """
        color1_rgb = hex_to_rgb(color1)
        color2_rgb = hex_to_rgb(color2)
        interp_rgb = tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1_rgb, color2_rgb))
        return rgb_to_hex(interp_rgb)