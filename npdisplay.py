import tkinter as tk
from tkinter import Label, ttk
from threading import Timer
import time
from screensaver import AlbumArtScreensaver

try:
    from npsettings_local import screensaver_delay, primary_fontname, header_fontname
except ImportError:
    from npsettings import screensaver_delay, primary_fontname, header_fontname


class NowPlayingDisplay:
    """This class is for creating and updating the objects of the Now Playing screen."""
    def __init__(self, tk_instance, screenwidth, screenheight):
        self.fontsize = screenheight // 33
        self.header_fontsize = int(self.fontsize * 0.8)
        self.fontname = primary_fontname
        self.header_fontname = header_fontname
        self.bgcolor = "#000000"
        self.header_bgcolor = "#1F1F1F"
        self.header_fgcolor = "#CCCCCC"
        self.active_foreground = "#FFFFFF"
        self.inactive_foreground = "#666666"
        self.active_pgbar_color = "#7D7D7D"
        self.inactive_pgbar_color = "#5C5C5C"
        self.foreground = self.active_foreground
        self.pgbar_color = self.active_pgbar_color
        self.active_artwork = None
        self.inactive_artwork = None
        self.screensaver_timer = None
        self.screensaver_lock = False
        self.screensaver = None
        self.DEBUG = False

        # Row Configuration
        tk_instance.rowconfigure(0, weight=0) 
        tk_instance.rowconfigure(1, weight=3)  # title header and text
        tk_instance.rowconfigure(2, weight=3)  # album header and text
        tk_instance.rowconfigure(3, weight=3)  # artist header and text
        tk_instance.rowconfigure(4, weight=2)  # track header and text
        tk_instance.rowconfigure(5, weight=0)  # elapsed/duration
        tk_instance.rowconfigure(6, weight=0)  # progress bar

        # Title
        self.title_header_lbl = Label(
            tk_instance,
            text="title",
            anchor="n",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=0,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=self.header_bgcolor,
            fg=self.header_fgcolor
        )
        self.title_header_lbl.grid(row=1, column=1, columnspan=3, sticky="new")

        self.title_lbl = Label(
            tk_instance,
            text="",
            anchor="n",
            wraplength=screenwidth-screenheight-20,
            justify="center",
            padx=0,
            pady=0,
            font=(self.fontname, self.fontsize, "bold"),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.title_lbl.grid(row=1, column=1, columnspan=3, sticky="ew")


        # Album
        self.album_header_lbl = Label(
            tk_instance,
            text="album",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=0,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=self.header_bgcolor,
            fg=self.header_fgcolor
        )
        self.album_header_lbl.grid(row=2, column=1, columnspan=3, sticky="new")

        self.album_released_lbl = Label(
            tk_instance,
            text="",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=0,
            pady=0,
            font=(self.fontname, self.header_fontsize),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.album_released_lbl.grid(row=2, column=1, columnspan=3, sticky="sw")

        self.album_duration_lbl = Label(
            tk_instance,
            text="",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=20,
            pady=0,
            font=(self.fontname, self.header_fontsize),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.album_duration_lbl.grid(row=2, column=1, columnspan=3, sticky="se")

        self.album_lbl = Label(
            tk_instance,
            text="",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=10,
            pady=0,
            font=(self.fontname, self.fontsize),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.album_lbl.grid(row=2, column=1, columnspan=3, sticky="ew")

        # Artist
        self.artist_header_lbl = Label(
            tk_instance,
            text="artists",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=0,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=self.header_bgcolor,
            fg=self.header_fgcolor
        )
        self.artist_header_lbl.grid(row=3, column=1, columnspan=3, sticky="new")

        self.artist_lbl = Label(
            tk_instance,
            text="",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=10,
            pady=0,
            font=(self.fontname, self.fontsize),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.artist_lbl.grid(row=3, column=1, columnspan=3, sticky="ew")

        # Track
        self.track_header_lbl = Label(
            tk_instance,
            text="track",
            anchor="s",
            wraplength=screenwidth-screenheight,
            justify="center",
            padx=0,
            pady=0,
            font=(self.header_fontname, self.header_fontsize),
            bg=self.header_bgcolor,
            fg=self.header_fgcolor
        )
        self.track_header_lbl.grid(row=4, column=1, columnspan=3, sticky="ew")

        self.track_lbl = Label(
            tk_instance,
            text="",
            anchor="s",
            wraplength=screenwidth-screenheight-20,
            justify="center",
            padx=0,
            pady=0,
            font=(self.fontname, self.fontsize),
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.track_lbl.grid(row=4, column=1, columnspan=3, sticky="sew")

        # Elapsed and Duration
        self.elapsed_lbl = Label(
            tk_instance,
            text="0:00",
            anchor="sw",
            font=(self.fontname, self.fontsize),
            padx=5,
            pady=0,
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.elapsed_lbl.grid(row=5, column=1, columnspan=3, sticky="sw")

        self.duration_lbl = Label(
            tk_instance,
            text="0:00",
            anchor="se",
            font=(self.fontname, self.fontsize),
            padx=20,
            pady=0,
            bg=self.bgcolor,
            fg=self.active_foreground
        )
        self.duration_lbl.grid(row=5, column=1, columnspan=3, sticky="se")

        # Progress Bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.Horizontal.TProgressbar",
            foreground="black",
            background=self.pgbar_color,
            troughcolor=self.header_bgcolor,
            borderwidth=0,
            height=6
        )
        self.progress_bar = ttk.Progressbar(
            tk_instance,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.config(length=screenwidth, value=0, maximum=100)       
        self.progress_bar.grid(row=6, column=1, columnspan=3, sticky="es")

        # Full Screen Album Art goes here!
        self.art_lbl = Label(
            tk_instance,
            image=None
        )
        self.art_lbl.grid(row=1, column=0, rowspan=6, sticky="wns", padx=0, pady=0)

        # create vertical progress bars to use as borders for the sides of the screen
        vstyle = ttk.Style()
        vstyle.theme_use('default')
        vstyle.configure(
            "Custom.Vertical.TProgressbar",
            foreground="black",
            background=self.pgbar_color,
            troughcolor=self.header_bgcolor,
            borderwidth=0,
            width=6
        )
        self.left_pgbar = ttk.Progressbar(
            tk_instance,
            orient="vertical",
            mode="determinate",
            style="Custom.Vertical.TProgressbar"
        )
        self.left_pgbar.config(length=screenheight, value=0, maximum=100)
        self.left_pgbar.grid(row=1, column=0, rowspan=6, sticky="ens", padx=0, pady=0)

        self.right_pgbar = ttk.Progressbar(
            tk_instance,
            orient="vertical",
            mode="determinate",
            style="Custom.Vertical.TProgressbar"
        )
        self.right_pgbar.config(length=screenheight, value=0, maximum=100)
        self.right_pgbar.grid(row=1, column=2, rowspan=6, sticky="ens", padx=0, pady=0)
        self.left_pgbar["value"] = 0
        self.right_pgbar["value"] = 0


    def _time_to_seconds(self, time_str):
        # Convert time string in mm:ss format to seconds
        try:
            minutes, seconds = map(int, str(time_str).split(':'))
        except:
            minutes, seconds = 0, 0
        return minutes * 60 + seconds
    
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

    def set_duration(self, duration):
        self.duration_lbl.config(text=duration)

    def set_debug(self, debug):
        self.DEBUG = debug

    def set_elapsed(self, new_elapsed):
        self.elapsed_lbl.config(text=new_elapsed)
        # update progress bar with new elapsed time
        self._update_progress_bar(new_elapsed)

    def set_title(self, new_title):
        self.title_lbl.config(text=new_title)

    def set_artist(self, new_artist):
        self.artist_lbl.config(text=new_artist)

    def set_album(self, new_album):
        self.album_lbl.config(text=new_album)

    def set_album_released(self, new_album_released):
        self.album_released_lbl.config(text=new_album_released)
    
    def set_album_duration(self, new_album_duration):
        self.album_duration_lbl.config(text=new_album_duration)

    def set_artwork(self, active_artwork, inactive_artwork):
        self.active_artwork = active_artwork
        self.inactive_artwork = inactive_artwork
        self.art_lbl.config(image=active_artwork)

    def set_track(self, track_text):
        self.track_lbl.config(text=track_text)

    def _update_foreground(self):
        # Update the text color of the labels
        self.album_lbl.config(fg=self.foreground)
        self.album_released_lbl.config(fg=self.foreground)
        self.album_duration_lbl.config(fg=self.foreground)
        self.artist_lbl.config(fg=self.foreground)
        self.title_lbl.config(fg=self.foreground)
        self.track_lbl.config(fg=self.foreground)
        self.elapsed_lbl.config(fg=self.foreground)
        self.duration_lbl.config(fg=self.foreground)
        # Update the progress bar style's background color
        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar", background=self.pgbar_color)

    def start_screensaver(self, delay):
        if AlbumArtScreensaver.running:
            if AlbumArtScreensaver.display_is_on():
                self._stop_screensaver()
            else:
                return
        self.screensaver_lock = True
        self.screensaver = AlbumArtScreensaver(debug=self.DEBUG)
        self.screensaver_timer = Timer(int(delay), self.screensaver.start)
        self.screensaver_timer.start()  

    def _stop_screensaver(self):
        if self.screensaver:
            self.screensaver.stop()
            self.screensaver_timer.cancel()
            self.screensaver_timer = None
            self.screensaver = None
            self.screensaver_lock = False

    def set_inactive(self):
        # dim the text color of the labels when the player is inactive
        if not self.screensaver_lock:
            self.foreground = self.inactive_foreground
            self.pgbar_color = self.inactive_pgbar_color
            # use the inactive artwork if it is available
            if self.inactive_artwork:
                self.art_lbl.config(image=self.inactive_artwork)
            self._update_foreground()
            self.start_screensaver(screensaver_delay)

    def set_active(self):
        # lighten the text color of the labels when the player is active
        self.foreground = self.active_foreground
        self.pgbar_color = self.active_pgbar_color
        # use the active artwork if it is available
        if self.active_artwork:
            self.art_lbl.config(image=self.active_artwork)
        self._update_foreground()
        if self.screensaver_timer:
            self._stop_screensaver()

    def restart_screensaver(self):
        if self.screensaver:
            self._stop_screensaver()
        while AlbumArtScreensaver.running:
            time.sleep(0.1)
        self.start_screensaver(0)


