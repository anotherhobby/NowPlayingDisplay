import os
import time
import random
import pygame
import math
from threading import Thread
import logging

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

class AlbumArtScreensaver:
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("setting up AlbumArtScreensaver to run")
        self.update_interval = 5  # how often to update grid squares (in seconds)
        self.update_time = time.time()
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.lockfile_path = f"{self.dir}/screensaver.lock"
        self.image_map = {}
        self.used_images = set()
        self.screensaver_thread = None
        pygame.init()

    def stop(self):
        if os.path.exists(self.lockfile_path):
            os.remove(self.lockfile_path)

    def running(self):
        return os.path.exists(self.lockfile_path)

    def start(self):
        logger.debug("Starting screensaver...")
        with open(self.lockfile_path, "w") as f:
            f.write("1")
        Thread(target=self._screensaver).start()

    def _load_images(self, folder_path):
        image_files = [f for f in os.listdir(folder_path) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        image_files.sort()
        return [pygame.image.load(os.path.join(folder_path, image_file)) for image_file in image_files]

    def _select_random_image(self, images):
        remaining_images = [image for image in images if image not in self.used_images]
        if remaining_images:
            return random.choice(remaining_images)
        else:
            return random.choice(images)

    def _simplify_ratio(self, a, b):
        # Calculate the greatest common divisor (GCD) and simplify the ratio
        gcd = math.gcd(a, b)    
        a_prime = a // gcd
        b_prime = b // gcd
        return a_prime, b_prime

    def _update_grid(self, window, image_map, grid, images, image_size):
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                if random.random() < 0.05:  # 10% chance of updating each cell
                    image = self._select_random_image(images)
                    self.used_images.add(image)
                    grid[i][j] = pygame.transform.smoothscale(image, (image_size, image_size))
                    self.used_images.remove(image_map.get(f"{i}/{j}"))
                    image_map[f"{i}/{j}"] = image
        # Draw the updated grid
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                window.blit(grid[i][j], (j * image_size, i * image_size))
        pygame.display.update()
        return image_map

    def _screensaver(self):
        # build the grid based on the screen size and aspect ratio
        logger.debug("Building screensaver grid...")
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h
        grid_size = self._simplify_ratio(screen_width, screen_height)
        logger.debug(f"grid size: {grid_size} from {screen_width}x{screen_height}")

        # Load images
        logger.debug("Loading album art...")
        art_path = f'{self.dir}/album_images/'
        images = self._load_images(art_path)

        # Create the grid
        logger.debug("Creating grid...")
        grid = [[None] * grid_size[0] for _ in range(grid_size[1])]
        image_size = min(screen_width // grid_size[0], screen_height // grid_size[1])
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                image = self._select_random_image(images)
                self.used_images.add(image)
                resized_image = pygame.transform.smoothscale(image, (image_size, image_size))
                grid[i][j] = resized_image
                self.image_map[f"{i}/{j}"] = image

        # Set up the display
        logger.debug("Setting up display...")
        window = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
        pygame.display.set_caption("Dynamic Grid Slideshow")
        pygame.mouse.set_visible(False)  # Hide the mouse
        
        # Main loop
        logger.debug("Starting main loop...")
        clock = pygame.time.Clock()
        while self.running():
            if time.time() - self.update_time > self.update_interval:
                self.update_time = time.time()
                new_image_map = self._update_grid(window, self.image_map.copy(), grid, images, image_size)
                self.image_map = new_image_map.copy()
            clock.tick(10)
        logger.debug("Quitting screensaver...")
        pygame.quit()
        logger.debug("Screensaver done.")


if __name__ == "__main__":
    screensaver = AlbumArtScreensaver()
    screensaver.start()
