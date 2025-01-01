import os
import time
import random
import pygame
import math
from threading import Thread, Lock
import logging
from nputils import *


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from npsettings_local import *
except ImportError:
    logger.error("local config not found, using default")
    from npsettings import *

class AlbumArtScreensaver:
    running = False # only one instance of the screensaver can run at a time
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        self.lock = Lock()
        self.update_interval = 5 #seconds between grid updates
        self.update_time = time.time()
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.lockfile_path = f"{self.dir}/screensaver.lock"
        self.image_map = {}
        self.used_images = set()
        self.screensaver_thread = None
        pygame.init()

    def stop(self):
        logger.debug("Stopping screensaver...")
        self.stop_requested = True  # Set stop flag
        if os.path.exists(self.lockfile_path):
            os.remove(self.lockfile_path)
        self.clear_images()  # Release all images
        if self.screensaver_thread:
            self.screensaver_thread.join()  # Ensure the thread exits
            logger.debug("Screensaver thread joined.")

    def lock_file(self):
        return os.path.exists(self.lockfile_path)
    
    def start(self):
        logger.debug("Starting screensaver thread...")
        self.stop_requested = False  # Reset stop flag
        with open(self.lockfile_path, "w") as f:
            f.write("1")
        self.screensaver_thread = Thread(target=self._screensaver)
        self.screensaver_thread.daemon = True
        self.screensaver_thread.start()

    def _load_images(self, folder_path, target_size):
        image_files = [f for f in os.listdir(folder_path) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        image_files.sort()
        loaded_images = []
        
        for image_file in image_files:
            if self.stop_requested:  # Check if stop is requested during loading
                logger.debug("Screensaver stop requested during image loading.")
                return loaded_images  # Exit early if stopping

            try:
                image = pygame.image.load(os.path.join(folder_path, image_file))
                scaled_image = pygame.transform.smoothscale(image, (target_size, target_size))
                loaded_images.append(scaled_image)
            except pygame.error as e:
                logger.error(f"Error loading image {image_file}: {e}")
        
        return loaded_images

    def _select_random_image(self, images):
        with self.lock:
            remaining_images = [image for image in images if image not in self.used_images]
            if not remaining_images:
                return random.choice(images)
            selected_image = random.choice(remaining_images)
            self.used_images.add(selected_image)
            return selected_image

    def _simplify_ratio(self, a, b):
        # Calculate the greatest common divisor (GCD) and simplify the ratio
        gcd = math.gcd(a, b)    
        return a // gcd, b // gcd
    
    def _update_grid(self, window, image_map, grid, images, image_size, dim_surface, overlay_value):
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                if random.random() < 0.05:  # 5% chance of updating each cell
                    image = self._select_random_image(images)
                    self.used_images.add(image)
                    grid[i][j] = image  # Already resized in _load_images() method
                    self.used_images.remove(image_map.get(f"{i}/{j}"))
                    image_map[f"{i}/{j}"] = image

        # Set the alpha value for the dim surface (0 is fully transparent, 255 is fully opaque)
        dim_surface.set_alpha(int(overlay_value))
        
        # Draw the updated grid
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                window.blit(grid[i][j], (j * image_size, i * image_size))
                # Draw the dimming surface over the window
        window.blit(dim_surface, (0, 0))
        pygame.display.update()
        return image_map
    
    def clear_images(self):
        for key, image in self.image_map.items():
            del image  # Explicitly delete Pygame surfaces
        self.image_map.clear()
        self.used_images.clear()

    def _screensaver(self):
        if AlbumArtScreensaver.running:
            logger.debug("Screensaver already running.")
            return
        AlbumArtScreensaver.running = True
        logger.debug("Building screensaver grid...")
        self.clear_images()
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h
        grid_size = self._simplify_ratio(screen_width, screen_height)
        logger.debug(f"grid size: {grid_size} from {screen_width}x{screen_height}")

        # Load images
        image_size = min(screen_width // grid_size[0], screen_height // grid_size[1])
        art_path = f'{self.dir}/album_images/'
        images = self._load_images(art_path, image_size)

        # Early exit if stop is requested during image loading
        if self.stop_requested:
            logger.debug("Screensaver stop requested before grid setup.")
            AlbumArtScreensaver.running = False
            return

        # Ensure the taskbar is hidden by using FULLSCREEN and NOFRAME flags
        window_flags = pygame.FULLSCREEN | pygame.NOFRAME

        # Create the grid
        logger.debug("Creating grid and resizing images...")
        grid = [[None] * grid_size[0] for _ in range(grid_size[1])]
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                image = self._select_random_image(images)
                with self.lock:
                    self.used_images.add(image)
                    grid[i][j] = image
                    self.image_map[f"{i}/{j}"] = image

        # Create surface that will be used for dimming
        dim_surface = pygame.Surface((screen_width, screen_height))
        dim_surface.fill((0, 0, 0))  # Black color

        # Set up the display (only if stop wasn't requested)
        logger.debug("Setting up window...")
        if not self.stop_requested:
            window = pygame.display.set_mode((screen_width, screen_height), window_flags)
            pygame.display.set_caption("Dynamic Grid Slideshow")
            pygame.mouse.set_visible(False)  # Hide the mouse
        else:
            logger.debug("Screensaver stopped before window setup.")
            AlbumArtScreensaver.running = False
            return

        # Main loop
        logger.debug(f"Starting main screensaver loop at {time.ctime()}...")
        clock = pygame.time.Clock()

        try:
            while self.lock_file() and not self.stop_requested:
                if time.time() - self.update_time > self.update_interval:
                    overlay_value = calculate_screensaver_dimming_mask()
                    self.update_time = time.time()
                    new_image_map = self._update_grid(window, self.image_map.copy(), grid, images, image_size, dim_surface, overlay_value)
                    self.image_map = new_image_map.copy()
                clock.tick(5)
        except Exception as e:
            logger.error(f"Error in main screensaver loop: {e}")
        finally:
            logger.debug(f"Quitting screensaver at {time.ctime()}...")
            pygame.display.quit()  # Quit display
            pygame.quit()  # Ensure Pygame resources are released
            AlbumArtScreensaver.running = False
            logger.debug("Screensaver successfully stopped.")

if __name__ == "__main__":
    screensaver = AlbumArtScreensaver()
    screensaver.start()
