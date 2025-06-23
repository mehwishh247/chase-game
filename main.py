from math import ceil
import pygame
import subprocess
import time
import sys
from pathlib import Path

from pattern_logic import generate_pattern
from score_tracker import ScoreTracker
from tile_logic import draw_tile_grid #, get_pressed_tile
# from video_player import play_fullscreen_video
from tile_comm import initialize_arduino, light_tile, turn_off_all_tiles

pygame.init()

# Set up paths for cross-platform compatibility
ASSETS_DIR = Path(__file__).parent / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LOGO_IMAGE = IMAGES_DIR / "logo.png"
VIDEOS_DIR = ASSETS_DIR / "videos"
INTRO_VIDEO = VIDEOS_DIR / "intro.mp4"
WIN_VIDEO = VIDEOS_DIR / "win.mp4"
LOSE_VIDEO = VIDEOS_DIR / "lose.mp4"

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
video_height = int(screen_height * 0.17)  # Changed from 0.33 to 0.17
game_area_height = screen_height - video_height
game_area_y_start = video_height

# Layout within the bottom 83% game area
logo_height = int(game_area_height * 0.20)  # Made logo bigger
ui_height = int(game_area_height * 0.30)    # Made scoreboard taller
grid_height = game_area_height - logo_height - ui_height

# Y positions
logo_y_start = game_area_y_start
grid_y_start = logo_y_start + logo_height # Grid starts right after logo
ui_y_start = grid_y_start + grid_height - 150 # Move scoreboard up more

# Padding
side_padding = 75 # Increased to make scoreboard less wide
bottom_padding = int(side_padding * 1.5)

# Game states
WAITING_FOR_START = "waiting_for_start"
PLAYING_INTRO = "playing_intro"
PLAYING_GAME = "playing_game"
GAME_OVER = "game_over"
SHOWING_FINAL_SCORE = "showing_final_score"  # New state for final score display
SHOWING_WIN_LOSE_TEXT = "showing_win_lose_text"  # New state for win/lose text display

# Game variables
game_state = WAITING_FOR_START
last_stump_pos = None
total_patterns_played = 0
active_tiles = {(2, 2): "cue"}  # Initialize with center tile as cue
pattern_timer = 0
pattern_interval = 3000  # 3 seconds in milliseconds
difficulty_timer = 0
difficulty_interval = 12000  # 12 seconds in milliseconds
current_difficulty = 1
max_difficulty = 5
game_over_timer = 0
game_over_duration = 4000  # 4 seconds for score display
win_lose_text_timer = 0
win_lose_text_duration = 3000  # 6 seconds for win/lose text display
game_start_time = 0
game_duration = 120000  # 2 minute in milliseconds
video_playing = False
video_text = ""
tracker = ScoreTracker()
intro_duration = 7000  # 7 seconds for intro video
win_lose_duration = 5000  # 5 seconds for win/lose videos

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

def play_intro_video():
    """Play intro video in fullscreen without stretching"""
    global video_playing, video_text
    video_playing = True
    video_text = "Playing intro..."
    
    try:
        # Use mpv for fullscreen video playback
        subprocess.Popen([
            "mpv", 
            "--fullscreen",
            "--no-border",
            "--ontop",
            "--no-terminal",
            "--keep-open=no",
            str(INTRO_VIDEO),
        ])
    except FileNotFoundError:
        # Fallback if mpv is not installed
        video_text = ""

def play_win_video():
    """Play win video in fullscreen without stretching"""
    global video_playing, video_text
    video_playing = True
    video_text = "You won! Playing win video..."
    
    try:
        subprocess.Popen([
            "mpv", 
            "--fullscreen",
            "--no-border",
            "--ontop",
            "--no-terminal",
            "--keep-open=no",
            str(WIN_VIDEO),
        ])
    except FileNotFoundError:
        video_text = ""

def play_lose_video():
    """Play lose video in fullscreen without stretching"""
    global video_playing, video_text
    video_playing = True
    video_text = "You lost. Playing lose video..."
    
    try:
        subprocess.Popen([
            "mpv", 
            "--fullscreen",
            "--no-border",
            "--ontop",
            "--no-terminal",
            "--keep-open=no",
            str(LOSE_VIDEO),
        ])
    except FileNotFoundError:
        video_text = ""



def handle_mouse_click(pos):
    """Handle mouse clicks and return True if tile (2, 2) was clicked"""
    # Check if click is within the grid area
    if pos[1] < grid_y_start or pos[1] >= grid_y_start + grid_height:
        return False
    
    # Account for side padding
    adjusted_x = pos[0] - side_padding
    if adjusted_x < 0 or adjusted_x >= screen_width - (2 * side_padding):
        return False
    
    # Calculate tile size based on grid dimensions (matching tile_logic.py)
    grid_surface_width = screen_width - (2 * side_padding)
    padding = 15  # Same as in tile_logic.py
    
    # Calculate tile dimensions
    available_width = grid_surface_width - (padding * 2)
    available_height = grid_height - (padding * 2)
    
    cols, rows = 5, 3
    h_from_width = (available_width - (cols - 1) * padding) / (cols * 1.5)
    h_from_height = (available_height - (rows - 1) * padding) / rows
    
    tile_height = min(h_from_width, h_from_height)
    if tile_height < 0: tile_height = 0
    tile_width = tile_height * 1.5
    
    # Calculate grid content dimensions
    grid_content_width = cols * tile_width + (cols - 1) * padding
    grid_content_height = rows * tile_height + (rows - 1) * padding
    start_x = (grid_surface_width - grid_content_width) / 2
    start_y = padding
    
    # Convert click position to grid coordinates
    click_x = adjusted_x - start_x
    click_y = pos[1] - grid_y_start - start_y
    
    # Calculate grid position
    if click_x < 0 or click_y < 0:
        return False
    
    col = int(click_x // (tile_width + padding))
    row = int(click_y // (tile_height + padding))
    
    # Check if click is within tile bounds
    tile_x = col * (tile_width + padding)
    tile_y = row * (tile_height + padding)
    
    if (click_x >= tile_x and click_x < tile_x + tile_width and 
        click_y >= tile_y and click_y < tile_y + tile_height):
        # Check if tile (2, 2) was clicked (center tile)
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
        # Display score, hits, and misses during gameplay
        font_large = pygame.font.Font(None, 50)
        font_medium = pygame.font.Font(None, 36)
        
        # Score at the top
        score_text = font_large.render(f"Score: {tracker.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(ui_surface_width // 2, ui_surface_height // 2 - 30))
        ui_surface.blit(score_text, score_rect)
        
        # Hits and misses below
        hits_text = font_medium.render(f"Hits: {tracker.hits}", True, (0, 255, 0))
        misses_text = font_medium.render(f"Misses: {tracker.misses}", True, (255, 0, 0))
        
        hits_rect = hits_text.get_rect(center=(ui_surface_width // 2 - 80, ui_surface_height // 2 + 20))
        misses_rect = misses_text.get_rect(center=(ui_surface_width // 2 + 80, ui_surface_height // 2 + 20))
        
        ui_surface.blit(hits_text, hits_rect)
        ui_surface.blit(misses_text, misses_rect)

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

def end_game(won):
    """End the game and show appropriate video"""
    global game_state, game_over_timer, video_playing
    game_state = GAME_OVER
    game_over_timer = pygame.time.get_ticks()
    
    # Stop background video
    subprocess.run(["pkill", "mpv"])
    time.sleep(0.2)  # Optional short delay
    
    if won:
        play_win_video()
    else:
        play_lose_video()


def show_splash_screen():
    """Show splash screen in fullscreen"""
    # Fill screen with dark background
    screen.fill((20, 20, 20))
    
    # Draw splash text
    font_large = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 36)
    
    title = font_large.render("TILE GAME", True, (255, 255, 255))
    subtitle = font_small.render("Step on the center tile to begin", True, (200, 200, 200))
    
    title_rect = title.get_rect(center=(screen_width // 2, screen_height // 2 - 50))
    subtitle_rect = subtitle.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
    
    screen.blit(title, title_rect)
    screen.blit(subtitle, subtitle_rect)
    
    pygame.display.flip()

def show_final_score_fullscreen():
    """Show final score in fullscreen"""
    # Fill screen with dark background
    screen.fill((20, 20, 20))
    
    # Draw final score
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)
    
    score_text = font_large.render(f"Final Score: {tracker.score}", True, (255, 255, 255))
    hits_text = font_medium.render(f"Hits: {tracker.hits}", True, (0, 255, 0))
    misses_text = font_medium.render(f"Misses: {tracker.misses}", True, (255, 0, 0))
    instruction = font_small.render("Press any key to play again", True, (200, 200, 200))
    
    score_rect = score_text.get_rect(center=(screen_width // 2, screen_height // 2 - 100))
    hits_rect = hits_text.get_rect(center=(screen_width // 2, screen_height // 2 - 20))
    misses_rect = misses_text.get_rect(center=(screen_width // 2, screen_height // 2 + 20))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height // 2 + 100))
    
    screen.blit(score_text, score_rect)
    screen.blit(hits_text, hits_rect)
    screen.blit(misses_text, misses_rect)
    screen.blit(instruction, instruction_rect)
    
    pygame.display.flip()

def show_win_lose_text_fullscreen(won):
    """Show win/lose text in fullscreen for 2 seconds after outro video"""
    # Fill screen with dark background
    screen.fill((20, 20, 20))
    
    # Draw win/lose message
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 48)
    
    if won:
        message_text = font_large.render("YOU WIN!", True, (0, 255, 0))
        score_text = font_medium.render(f"Final Score: {tracker.score}", True, (255, 255, 255))
    else:
        message_text = font_large.render("GAME OVER", True, (255, 0, 0))
        score_text = font_medium.render(f"Final Score: {tracker.score}", True, (255, 255, 255))
    
    message_rect = message_text.get_rect(center=(screen_width // 2, screen_height // 2 - 50))
    score_rect = score_text.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
    
    screen.blit(message_text, message_rect)
    screen.blit(score_text, score_rect)
    
    pygame.display.flip()

def run_desktop_game():
    """Main game loop for desktop gameplay"""
    global game_state, active_tiles, pattern_timer, difficulty_timer, game_start_time
    global current_difficulty, video_playing
    global pattern_interval, game_over_timer, last_stump_pos, total_patterns_played
    
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
                    # Wait 2 seconds for intro text
                    pygame.time.wait(3000)
                    game_state = PLAYING_GAME
                    pattern_timer = current_time
                    difficulty_timer = current_time
                    game_start_time = current_time
                    tracker.reset()
                    current_difficulty = 1
                    active_tiles = {}  # Clear the center tile
                    video_playing = False
                    last_stump_pos = None  # Initialize last_stump_pos

        # Handle game over timer
        if game_state == GAME_OVER:
            if video_playing:
                # Wait for video to finish (outro video duration)
                if current_time - game_over_timer > 5000:  # 5 seconds for win/lose video
                    video_playing = False
                    game_over_timer = current_time
            else:
                # Show win/lose text in fullscreen for 2 seconds after video
                won = tracker.score > 0
                show_win_lose_text_fullscreen(won)
                game_state = SHOWING_WIN_LOSE_TEXT
                win_lose_text_timer = current_time
        
        elif game_state == SHOWING_WIN_LOSE_TEXT:
            # Show win/lose text for 2 seconds after video, then reset
            if current_time - win_lose_text_timer > win_lose_text_duration:
                game_state = WAITING_FOR_START
                active_tiles = {(2, 2): "cue"}  # Highlight center tile
                video_playing = False
            else:
                # Keep showing the win/lose text
                won = tracker.score > 0
                show_win_lose_text_fullscreen(won)
        
        # Update game logic
        if game_state == PLAYING_GAME:
            # Check for tile presses
            pressed_tile = get_pressed_tile()
            tracker.check_tile_press(pressed_tile, active_tiles)
            
            # Check if game time is up (1 minute)
            if current_time - game_start_time >= game_duration:
                won = tracker.score > 0
                end_game(won)
                continue
            
            # Update difficulty every 10 seconds
            if current_time - difficulty_timer > difficulty_interval:
                current_difficulty = min(current_difficulty + 1, max_difficulty)
                difficulty_timer = current_time
                # Decrease pattern interval (faster patterns)
                pattern_interval = max(1500, 3000 - (current_difficulty - 1) * 300)  # 3s to 1.5s
            
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

def run_arduino_game():
    """Main game loop for Arduino-based gameplay"""
    global game_state, active_tiles, pattern_timer, difficulty_timer, game_start_time
    global current_difficulty, video_playing
    global pattern_interval, game_over_timer, win_lose_text_timer, last_stump_pos, total_patterns_played
    
    # Initialize Arduino connection
    initialize_arduino()
    
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            
            elif event.type == pygame.KEYDOWN and game_state == SHOWING_FINAL_SCORE:
                # Any key press returns to splash screen
                game_state = WAITING_FOR_START
                active_tiles = {(2, 2): "cue"}  # Highlight center tile
                video_playing = False

        # Handle different game states
        if game_state == WAITING_FOR_START:
            # Show splash screen
            show_splash_screen()
            
            # Light center tile with brightness 100
            turn_off_all_tiles()
            light_tile(2, 2, "bright")  # Use string color instead of number
            
            # Check if center tile is pressed
            pressed_tile = get_pressed_tile()
            if pressed_tile == (2, 2):
                game_state = PLAYING_INTRO
                play_intro_video()
                game_state = PLAYING_GAME
                pattern_timer = current_time
                difficulty_timer = current_time
                game_start_time = current_time
                tracker.reset()
                current_difficulty = 1
                active_tiles = {}  # Clear the center tile
                video_playing = False
                last_stump_pos = None  # Initialize last_stump_pos
                total_patterns_played = 0  # Initialize total_patterns_played
                
        elif game_state == PLAYING_GAME:
            # Check for tile presses using Arduino
            pressed_tile = get_pressed_tile()
            tracker.check_tile_press(pressed_tile, active_tiles)
            
            # Check if game time is up (1 minute)
            if current_time - game_start_time >= game_duration:
                won = tracker.score > 0
                end_game(won)
                continue
            
            # Update difficulty every 10 seconds
            if current_time - difficulty_timer > difficulty_interval:
                current_difficulty = min(current_difficulty + 1, max_difficulty)
                difficulty_timer = current_time
                # Decrease pattern interval (faster patterns)
                pattern_interval = max(1500, 3000 - (current_difficulty - 1) * 300)  # 3s to 1.5s
            
            # Update pattern every pattern_interval
            if current_time - pattern_timer > pattern_interval:
                total_patterns_played += 1
                
                # Turn off all tiles first
                turn_off_all_tiles()
                
                # Generate new pattern
                active_tiles = generate_pattern(current_difficulty, last_stump_pos, total_patterns_played)
                
                # Update last_stump_pos with the new stump position
                stump_positions = [pos for pos, t in active_tiles.items() if t == "stump"]
                if stump_positions:
                    last_stump_pos = stump_positions[0]
                
                # Light up tiles according to pattern
                for (row, col), tile_type in active_tiles.items():
                    if tile_type == "stump":
                        light_tile(row, col, "bright")  # Bright for stumps
                    elif tile_type == "rock":
                        light_tile(row, col, "medium")   # Medium for rocks
                
                # Light up background tiles
                for row in range(3):
                    for col in range(5):
                        if (row, col) not in active_tiles:
                            light_tile(row, col, "dim")  # Dim for background
                
                pattern_timer = current_time
                tracker.pattern_scored = False  # Reset the scoring flag for the new pattern
            
            # Draw gameplay screen
            screen.fill((0, 0, 0))  # Black background
            
            draw_logo_area()
            # Draw grid
            draw_grid_area()
            
            # Draw UI info in bottom area
            draw_ui_area()
            
            pygame.display.flip()
        
        elif game_state == GAME_OVER:
            if video_playing:
                # Wait for video to finish (outro video duration)
                if current_time - game_over_timer > 5000:  # 5 seconds for win/lose video
                    video_playing = False
                    game_over_timer = current_time
            else:
                # Show win/lose text in fullscreen for 2 seconds after video
                won = tracker.score > 0
                show_win_lose_text_fullscreen(won)
                game_state = SHOWING_WIN_LOSE_TEXT
                win_lose_text_timer = current_time
        
        elif game_state == SHOWING_WIN_LOSE_TEXT:
            # Show win/lose text for 2 seconds after video, then reset
            if current_time - win_lose_text_timer > win_lose_text_duration:
                game_state = WAITING_FOR_START
                active_tiles = {(2, 2): "cue"}  # Highlight center tile
                video_playing = False
            else:
                # Keep showing the win/lose text
                won = tracker.score > 0
                show_win_lose_text_fullscreen(won)
        
        clock.tick(30)

def main():
    """Determine whether to run desktop or Arduino game"""
    if "--arduino" in sys.argv:
        run_arduino_game()
    else:
        run_desktop_game()

if __name__ == "__main__":
    main()
    pygame.quit()