from math import ceil
import pygame
import subprocess
import time
import random
import threading
from pathlib import Path
import sys

from pattern_logic import generate_pattern
from score_tracker import ScoreTracker
from tile_logic import draw_tile_grid
from tile_comm import initialize_arduino, light_tile, turn_off_all_tiles

pygame.init()

# Set up paths for cross-platform compatibility
ASSETS_DIR = Path(__file__).parent / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LOGO_IMAGE = IMAGES_DIR / "logo.png"
VIDEOS_DIR = ASSETS_DIR / "videos"
INTRO_VIDEO = VIDEOS_DIR / "intro.mp4"

# Get display info to set game window size
info = pygame.display.Info()
display_width = info.current_w
display_height = info.current_h

# Maintain a 9:16 portrait aspect ratio
aspect_ratio = 9 / 16

# Calculate screen dimensions to fit display while maintaining aspect ratio
if (display_height * aspect_ratio) <= display_width:
    # Fit to display height
    screen_height = display_height
    screen_width = int(display_height * aspect_ratio)
else:
    # Fit to display width
    screen_width = display_width
    screen_height = int(display_width / aspect_ratio)

screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# Calculate areas for portrait mode
video_height = int(screen_height * 0.17)  # Reduced from 0.33 to 0.17
game_area_height = screen_height - video_height
game_area_y_start = video_height

# Layout within the bottom 66% game area
logo_height = int(game_area_height * 0.20)
ui_height = int(game_area_height * 0.35)  # Make scoreboard taller
side_padding = 75
grid_surface_width = screen_width - (2 * side_padding)

# Calculate spacing based on an estimate of grid height
height_for_grid_and_spacing = game_area_height - logo_height - ui_height
spacing = 20  # Fallback spacing
grid_height = height_for_grid_and_spacing - spacing

# Y positions
logo_y_start = game_area_y_start
grid_y_start = logo_y_start + logo_height
ui_y_start = grid_y_start + (grid_height // 1.5) + spacing

# Padding
bottom_padding = int(side_padding * 1.5)

# Game states
WAITING_FOR_START = "waiting_for_start"
PLAYING_INTRO = "playing_intro"
PLAYING_GAME = "playing_game"
GAME_OVER = "game_over"
SHOWING_FINAL_SCORE = "showing_final_score"

# Game variables
game_state = WAITING_FOR_START
active_tiles = {(2, 2): "cue"}  # Center tile as cue
pattern_timer = 0
pattern_interval = 3000
current_difficulty = 1
max_difficulty = 5
last_stump_pos = None
total_patterns_played = 0
tracker = ScoreTracker()

def get_pressed_tile():
    """
    Map keyboard keys to tile positions:
    - Q W E R T → (0,0) to (0,4)
    - A S D F G → (1,0) to (1,4)
    - Z X C V B → (2,0) to (2,4)
    Returns (row, col) for the key being pressed, or None if no relevant key is pressed
    """
    keys = pygame.key.get_pressed()
    
    # First row: Q W E R T → (0,0) to (0,4)
    if keys[pygame.K_q]: return (0, 0)
    if keys[pygame.K_w]: return (0, 1)
    if keys[pygame.K_e]: return (0, 2)
    if keys[pygame.K_r]: return (0, 3)
    if keys[pygame.K_t]: return (0, 4)
    
    # Second row: A S D F G → (1,0) to (1,4)
    if keys[pygame.K_a]: return (1, 0)
    if keys[pygame.K_s]: return (1, 1)
    if keys[pygame.K_d]: return (1, 2)
    if keys[pygame.K_f]: return (1, 3)
    if keys[pygame.K_g]: return (1, 4)
    
    # Third row: Z X C V B → (2,0) to (2,4)
    if keys[pygame.K_z]: return (2, 0)
    if keys[pygame.K_x]: return (2, 1)
    if keys[pygame.K_c]: return (2, 2)
    if keys[pygame.K_v]: return (2, 3)
    if keys[pygame.K_b]: return (2, 4)
    
    return None

def handle_mouse_click(pos):
    """Handle mouse clicks and return True if tile (2, 2) was clicked"""
    # Define grid properties
    grid_surface_width = screen_width - (2 * side_padding)
    rows, cols = 3, 5
    tile_padding = 15

    # Calculate the space taken by tiles and padding
    total_padding_x = (cols - 1) * tile_padding
    total_padding_y = (rows - 1) * tile_padding

    # Calculate tile dimensions based on a 3:2 aspect ratio
    h_from_width = (grid_surface_width - total_padding_x) / (cols * 1.5)
    h_from_height = (grid_height - total_padding_y) / rows
    tile_height = min(h_from_width, h_from_height)
    if tile_height < 0: tile_height = 0
    tile_width = tile_height * 1.5
    
    # Calculate grid content dimensions
    grid_content_width = cols * tile_width + total_padding_x
    grid_content_height = rows * tile_height + total_padding_y
    
    # Calculate grid's top-left corner on the screen
    grid_start_x_on_screen = side_padding + (grid_surface_width - grid_content_width) / 2
    grid_start_y_on_screen = grid_y_start + tile_padding

    # Get mouse position relative to the grid
    relative_x = pos[0] - grid_start_x_on_screen
    relative_y = pos[1] - grid_start_y_on_screen

    # Determine which tile was clicked
    if relative_x > 0 and relative_y > 0:
        col = int(relative_x // (tile_width + tile_padding))
        row = int(relative_y // (tile_height + tile_padding))
        
        if row == 2 and col == 2:
            return True

    return False

def draw_logo_area():
    """Draws the logo from an image file."""
    try:
        logo_img = pygame.image.load(LOGO_IMAGE)
        logo_img = pygame.transform.scale(logo_img, (logo_height, logo_height)) # Assuming square logo for scaling
        logo_rect = logo_img.get_rect(center=(screen_width // 2, logo_y_start + logo_height // 2))
        screen.blit(logo_img, logo_rect)
    except pygame.error:
        # Fallback to text if image fails to load
        logo_font = pygame.font.Font(None, 40)
        logo_text = logo_font.render("Logo Image Not Found", True, (255, 0, 0))
        logo_rect = logo_text.get_rect(center=(screen_width // 2, logo_y_start + logo_height // 2))
        screen.blit(logo_text, logo_rect)

def draw_ui_area():
    """Draw the UI area at the bottom of the screen"""
    ui_surface_width = screen_width - (2 * side_padding)
    ui_surface_height = ui_height - bottom_padding
    ui_surface = pygame.Surface((ui_surface_width, ui_surface_height), pygame.SRCALPHA)
    
    # Draw the rounded background
    corner_radius = 15
    pygame.draw.rect(ui_surface, (169, 169, 169), ui_surface.get_rect(), border_radius=corner_radius)
    
    if game_state == WAITING_FOR_START:
        # Show start instructions
        font = pygame.font.Font(None, 36)
        text1 = font.render("Press the center tile", True, (255, 255, 255))
        text2 = font.render("to start the game!", True, (255, 255, 255))
        text1_rect = text1.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 - 20))
        text2_rect = text2.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 + 20))
        ui_surface.blit(text1, text1_rect)
        ui_surface.blit(text2, text2_rect)
        
    elif game_state == PLAYING_GAME:
        # Display score and timer
        font = pygame.font.Font(None, 50)
        score_text = font.render(f"Score: {tracker.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2))
        ui_surface.blit(score_text, score_rect)

    elif game_state == SHOWING_FINAL_SCORE:
        # Draw final score, hits, and misses
            font = pygame.font.Font(None, 48)
            score_text = font.render(f"Final Score: {tracker.score}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 - 60))
            ui_surface.blit(score_text, score_rect)
            
            stats_font = pygame.font.Font(None, 32)
            hits_text = stats_font.render(f"Hits: {tracker.hits}", True, (0, 255, 0))
            misses_text = stats_font.render(f"Misses: {tracker.misses}", True, (255, 0, 0))
            hits_rect = hits_text.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 + 20))
            misses_rect = misses_text.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 + 60))
            ui_surface.blit(hits_text, hits_rect)
            ui_surface.blit(misses_text, misses_rect)

    # Draw UI area on main screen
    screen.blit(ui_surface, (side_padding, ui_y_start))

def draw_grid_area():
    """Draw the main tile grid in its designated area"""
    grid_surface_width = screen_width - (2 * side_padding)
    grid_surface = pygame.Surface((grid_surface_width, grid_height))
    draw_tile_grid(grid_surface, active_tiles)
    screen.blit(grid_surface, (side_padding, grid_y_start))

def run_desktop_game():
    """Main game loop for desktop gameplay"""
    global game_state, active_tiles, pattern_timer, current_difficulty, last_stump_pos, total_patterns_played
    
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN and game_state == WAITING_FOR_START:
                if handle_mouse_click(event.pos):
                    game_state = PLAYING_INTRO
                    play_intro_video()
                    # Wait for intro video to finish (approximately 7 seconds)
                    pygame.time.wait(7000)
                    game_state = PLAYING_GAME
                    pattern_timer = current_time
                    tracker.reset()
                    current_difficulty = 1
                    active_tiles = {}
                    last_stump_pos = None
                    total_patterns_played = 0

        # Update game logic
        if game_state == PLAYING_GAME:
            # Check for tile presses
            pressed_tile = get_pressed_tile()
            tracker.check_tile_press(pressed_tile, active_tiles)
            
            # Update pattern every pattern_interval
            if current_time - pattern_timer > pattern_interval:
                total_patterns_played += 1
                active_tiles = generate_pattern(current_difficulty, last_stump_pos, total_patterns_played)
                # Update last_stump_pos with the new stump position
                stump_positions = [pos for pos, t in active_tiles.items() if t == "stump"]
                if stump_positions:
                    last_stump_pos = stump_positions[0]

                pattern_timer = current_time
                tracker.pattern_scored = False  # Reset the scoring flag for the new pattern
        
        # Draw everything
        screen.fill((0, 0, 0))  # Black background
        
        draw_logo_area()
        draw_grid_area()
        draw_ui_area()
        
        pygame.display.flip()
        clock.tick(30)

def play_intro_video():
    """Play intro video using mpv in fullscreen with aspect ratio preservation"""
    try:
        subprocess.Popen([
            "mpv", 
            "--fullscreen",
            "--no-border",
            "--ontop",
            "--no-terminal",
            "--keepaspect",
            str(INTRO_VIDEO),
        ])
    except FileNotFoundError:
        print("mpv not found. Cannot play intro video.")

def main():
    """Run the desktop game"""
    run_desktop_game()

if __name__ == "__main__":
    main()
    pygame.quit()