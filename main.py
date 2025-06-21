from math import ceil
import pygame
import subprocess
import time
import random
import threading
from pathlib import Path
from tile_logic import draw_tile_grid #, get_pressed_tile
from video_player import play_fullscreen_video
from tile_comm import initialize_arduino, light_tile, turn_off_all_tiles

pygame.init()

# Set up paths for cross-platform compatibility
ASSETS_DIR = Path(__file__).parent / "assets"
VIDEOS_DIR = ASSETS_DIR / "videos"
INTRO_VIDEO = VIDEOS_DIR / "intro.mp4"
WIN_VIDEO = VIDEOS_DIR / "win.mp4"
LOSE_VIDEO = VIDEOS_DIR / "lose.mp4"
BACKGROUND_VIDEO = VIDEOS_DIR / "background.mp4"  # Add background video path

# Set up 16:9 aspect ratio screen
screen_width = 1920
screen_height = 1080
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# Calculate areas: Grid covers full width and top 80% height, UI in bottom 20%
grid_width = screen_width
grid_height = int(screen_height * 0.8)
ui_width = screen_width
ui_height = screen_height - grid_height

# Game states
WAITING_FOR_START = "waiting_for_start"
PLAYING_INTRO = "playing_intro"
PLAYING_GAME = "playing_game"
GAME_OVER = "game_over"
SHOWING_FINAL_SCORE = "showing_final_score"  # New state for final score display

# Game variables
game_state = WAITING_FOR_START
last_stump_pos = None
total_patterns_played = 0
active_tiles = {(2, 2): "stump"}  # Initialize with center tile as stump
pattern_timer = 0
pattern_interval = 3000  # 3 seconds in milliseconds
difficulty_timer = 0
difficulty_interval = 12000  # 12 seconds in milliseconds
current_difficulty = 1
max_difficulty = 5
score = 0
game_over_timer = 0
game_over_duration = 4000  # 4 seconds for score display
game_start_time = 0
game_duration = 120000  # 2 minute in milliseconds
video_playing = False
video_text = ""
pattern_scored = False  # Flag to track if current pattern has been scored
hits = 0  # Track number of hits
misses = 0  # Track number of misses
intro_duration = 7000  # 7 seconds for intro video
win_lose_duration = 5000  # 5 seconds for win/lose videos

# Tile types for different difficulties
tile_types = ["green", "red", "blue", "yellow", "purple", "orange"]

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
    """Play intro video in fullscreen using mpv, with fallback text"""
    global video_playing, video_text
    video_playing = True
    video_text = "Playing intro..."
    
    try:
        # Use mpv to play video in fullscreen
        subprocess.run([
            "mpv", 
            "--fs",           # Fullscreen
            "--no-audio",     # Disable sound
            "--really-quiet", # Suppress terminal messages
            str(INTRO_VIDEO)
        ], timeout=7.5)  # Slightly longer timeout than video duration
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: display text for 7 seconds
        time.sleep(7)
    finally:
        video_playing = False

def play_win_video():
    """Play win video in fullscreen using mpv, with fallback text"""
    global video_playing, video_text
    video_playing = True
    video_text = "Playing win video..."
    
    try:
        # Use mpv to play video in fullscreen
        subprocess.run([
            "mpv", 
            "--fs",           # Fullscreen
            "--no-audio",     # Disable sound
            "--really-quiet", # Suppress terminal messages
            str(WIN_VIDEO)
        ], timeout=4.0)  # Slightly longer timeout than video duration
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: display text for 3.5 seconds
        time.sleep(3.5)
    finally:
        video_playing = False

def play_lose_video():
    """Play lose video in fullscreen using mpv, with fallback text"""
    global video_playing, video_text
    video_playing = True
    video_text = "Playing lose video..."
    
    try:
        # Use mpv to play video in fullscreen
        subprocess.run([
            "mpv", 
            "--fs",           # Fullscreen
            "--no-audio",     # Disable sound
            "--really-quiet", # Suppress terminal messages
            str(LOSE_VIDEO)
        ], timeout=4.0)  # Slightly longer timeout than video duration
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: display text for 3.5 seconds
        time.sleep(3.5)
    finally:
        video_playing = False

def generate_pattern(difficulty, last_stump_pos=None, total_patterns_played=0):
    """
    Generate a tile pattern for a 3x5 grid based on difficulty.
    - Always at least one "stump" and one "rock"
    - Total number of tiles is 2 to 4
    - At low difficulty, more stumps than rocks
    - At high difficulty, more rocks than stumps
    - Never place two types on the same tile
    - Never exceed 4 lit tiles total
    - Valid positions: (row, col) with row in 0-2, col in 0-4
    - New stump must be different from last stump position
    - New stump must be at least 2 Manhattan distance away (except in last 3 patterns)
    - Allow 1-step diagonals (Manhattan distance = 2)
    - In last 3 patterns, drop distance restriction entirely
    """
    rows, cols = 3, 5
    all_positions = [(r, c) for r in range(rows) for c in range(cols)]

    # Determine total number of tiles (2 to 4)
    # At low difficulty, fewer tiles; at high, more
    min_tiles = 2
    max_tiles = 4
    # Scale number of tiles with difficulty (1 = easy, max_difficulty = hard)
    num_tiles = min_tiles + (max_tiles - min_tiles) * (difficulty - 1) // (max_difficulty - 1)
    num_tiles = max(min(num_tiles, max_tiles), min_tiles)

    # Always at least one stump and one rock
    # Decide how many of each
    if difficulty <= (max_difficulty // 2):
        # Low difficulty: more stumps
        num_stumps = max(1, num_tiles - 1)
        num_rocks = num_tiles - num_stumps
    else:
        # High difficulty: more rocks
        num_rocks = max(1, num_tiles - 1)
        num_stumps = num_tiles - num_rocks

    # Filter available positions for stump based on last stump position
    available_positions = all_positions.copy()
    
    if last_stump_pos is not None:
        # Remove the last stump position to avoid reusing it
        if last_stump_pos in available_positions:
            available_positions.remove(last_stump_pos)
        
        # Check if we're in the last 3 patterns (drop distance restriction)
        # Assuming game duration is 60 seconds and pattern interval is 3-1.5 seconds
        # Roughly 20-40 patterns per game, so last 3 patterns would be around patterns 17+
        is_last_3_patterns = total_patterns_played >= 17
        
        if not is_last_3_patterns:
            # Filter positions to only those with Manhattan distance >= 2
            # This allows 1-step diagonals (distance = 2) but prevents adjacent moves
            reachable_positions = []
            for pos in available_positions:
                # Calculate Manhattan distance
                distance = abs(pos[0] - last_stump_pos[0]) + abs(pos[1] - last_stump_pos[1])
                
                if distance <= 2:  # At most 2 Manhattan distance away
                    reachable_positions.append(pos)
            
            # If no reachable positions, fall back to all available positions
            if reachable_positions:
                available_positions = reachable_positions

    # Randomly select unique positions for stumps and rocks
    positions = random.sample(available_positions, num_tiles)
    stump_positions = positions[:num_stumps]
    rock_positions = positions[num_stumps:]

    pattern = {}
    for pos in stump_positions:
        pattern[pos] = "stump"
    for pos in rock_positions:
        pattern[pos] = "rock"

    return pattern

def handle_mouse_click(pos):
    """Handle mouse clicks and return True if tile (2, 2) was clicked"""
    # Convert screen position to grid position (only within grid area)
    if pos[0] >= grid_width:  # Click is in UI area
        return False
    
    # Calculate tile size based on grid dimensions
    tile_width = grid_width // 5
    tile_height = grid_height // 3
    
    grid_x = pos[0] // tile_width
    grid_y = pos[1] // tile_height
    
    # Check if tile (2, 2) was clicked (3rd column, 3rd row based on zero index)
    if grid_x == 2 and grid_y == 2:
        return True
    return False

def check_tile_press():
    """Check for tile presses and update score accordingly - only once per pattern"""
    global score, active_tiles, pattern_scored, hits, misses
    
    # If this pattern has already been scored, don't score again
    if pattern_scored:
        return
    
    pressed_tile = get_pressed_tile()
    if pressed_tile is not None:
        # Check if the pressed tile is in active_tiles and is a stump
        if pressed_tile in active_tiles:
            if active_tiles[pressed_tile] == "stump":
                score += 2  # Correct tile
                hits += 1
                pattern_scored = True  # Mark this pattern as scored
            else:
                score -= 1  # Wrong tile (rock)
                misses += 1
                pattern_scored = True  # Mark this pattern as scored
        else:
            score -= 1  # Pressed empty tile
            misses += 1
            pattern_scored = True  # Mark this pattern as scored

def draw_ui_area():
    """Draw the UI area on the right side of the screen"""
    # Fill UI area with dark background
    ui_surface = pygame.Surface((ui_width, ui_height))
    ui_surface.fill((20, 20, 20))
    
    if game_state == WAITING_FOR_START:
        # Show start instructions
        font = pygame.font.Font(None, 36)
        text = font.render("Step on the center tile", True, (255, 255, 255))
        text2 = font.render("to start the game!", True, (255, 255, 255))
        
        text_rect = text.get_rect(center=(ui_width // 2, ui_height // 2 - 30))
        text2_rect = text2.get_rect(center=(ui_width // 2, ui_height // 2 + 10))
        
        ui_surface.blit(text, text_rect)
        ui_surface.blit(text2, text2_rect)
        
    elif game_state == PLAYING_INTRO:
        print('video playing')
        # Show intro video text
        font = pygame.font.Font(None, 36)
        text = font.render(video_text, True, (255, 255, 255))
        text_rect = text.get_rect(center=(ui_width // 2, ui_height // 2))
        ui_surface.blit(text, text_rect)
        
    elif game_state == PLAYING_GAME:
        # Show game info
        font = pygame.font.Font(None, 32)
        difficulty_text = font.render(f"Level: {current_difficulty}", True, (255, 255, 255))
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        hits_text = font.render(f"Hits: {hits}", True, (255, 255, 255))
        misses_text = font.render(f"Misses: {misses}", True, (255, 255, 255))
        
        # Calculate remaining time
        remaining_time = max(0, game_duration - (pygame.time.get_ticks() - game_start_time))
        minutes = remaining_time // 60000
        seconds = (remaining_time % 60000) // 1000
        time_text = font.render(f"Time: {minutes:02d}:{seconds:02d}", True, (255, 255, 255))
        
        ui_surface.blit(difficulty_text, (20, 50))
        ui_surface.blit(score_text, (20, 100))
        ui_surface.blit(hits_text, (20, 150))
        ui_surface.blit(misses_text, (20, 200))
        ui_surface.blit(time_text, (20, 250))
        
        # Show instructions
        instruction_font = pygame.font.Font(None, 28)
        instruction1 = instruction_font.render("Step on the stumps!", True, (200, 200, 200))
        instruction2 = instruction_font.render("Avoid the rocks!", True, (200, 200, 200))
        
        ui_surface.blit(instruction1, (20, ui_height - 100))
        ui_surface.blit(instruction2, (20, ui_height - 70))
        
    elif game_state == GAME_OVER:
        # Show video playing text or final score
        if video_playing:
            font = pygame.font.Font(None, 36)
            text = font.render(video_text, True, (255, 255, 255))
            text_rect = text.get_rect(center=(ui_width // 2, ui_height // 2))
            ui_surface.blit(text, text_rect)
        else:
            # Show final score and stats
            font = pygame.font.Font(None, 48)
            score_text = font.render(f"Final Score: {score}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(ui_width // 2, ui_height // 2 - 60))
            ui_surface.blit(score_text, score_rect)
            
            stats_font = pygame.font.Font(None, 32)
            hits_text = stats_font.render(f"Hits: {hits}", True, (0, 255, 0))
            misses_text = stats_font.render(f"Misses: {misses}", True, (255, 0, 0))
            hits_rect = hits_text.get_rect(center=(ui_width // 2, ui_height // 2 + 20))
            misses_rect = misses_text.get_rect(center=(ui_width // 2, ui_height // 2 + 60))
            ui_surface.blit(hits_text, hits_rect)
            ui_surface.blit(misses_text, misses_rect)
    
    # Draw UI area on main screen
    screen.blit(ui_surface, (0, grid_height))

def draw_grid_area():
    """Draw the tile grid in the left area maintaining aspect ratio"""
    # Create a surface for the grid area
    grid_surface = pygame.Surface((grid_width, grid_height))
    grid_surface.fill((0, 0, 0))  # Black background
    
    # Draw the tile grid on the grid surface
    draw_tile_grid(grid_surface, active_tiles)
    
    # Draw grid area on main screen
    screen.blit(grid_surface, (0, 0))

def play_looping_background_video():
    """Play background video in a loop using mpv in a non-blocking thread"""
    try:
        subprocess.Popen([
            "mpv",
            "--loop",
            "--fs",
            "--no-border",
            "--ontop",
            "--no-terminal",
            "--really-quiet",
            "--geometry=0x0+0+0",
            str(BACKGROUND_VIDEO)
        ])
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: just continue without background video
        pass

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
    
    score_text = font_large.render(f"Final Score: {score}", True, (255, 255, 255))
    hits_text = font_medium.render(f"Hits: {hits}", True, (0, 255, 0))
    misses_text = font_medium.render(f"Misses: {misses}", True, (255, 0, 0))
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

def draw_mini_grid():
    """Draw a small version of the tile grid in the bottom 20% of screen"""
    # Calculate mini grid dimensions
    mini_grid_width = screen_width // 3  # Make it smaller
    mini_grid_height = ui_height // 2
    mini_tile_width = mini_grid_width // 5
    mini_tile_height = mini_grid_height // 3
    
    # Position mini grid in center of bottom area
    mini_grid_x = (screen_width - mini_grid_width) // 2
    mini_grid_y = grid_height + (ui_height - mini_grid_height) // 2
    
    # Draw mini grid background
    mini_surface = pygame.Surface((mini_grid_width, mini_grid_height))
    mini_surface.fill((40, 40, 40))
    
    # Draw mini tiles
    for row in range(3):
        for col in range(5):
            tile_x = col * mini_tile_width
            tile_y = row * mini_tile_height
            
            if (row, col) in active_tiles:
                if active_tiles[(row, col)] == "stump":
                    color = (0, 255, 0)  # Green for stumps
                else:
                    color = (255, 0, 0)  # Red for rocks
            else:
                color = (80, 80, 80)  # Gray for empty tiles
            
            pygame.draw.rect(mini_surface, color, 
                           (tile_x, tile_y, mini_tile_width - 2, mini_tile_height - 2))
    
    # Draw mini grid on main screen
    screen.blit(mini_surface, (mini_grid_x, mini_grid_y))

def run_desktop_game():
    """Main game loop for desktop gameplay"""
    global game_state, active_tiles, pattern_timer, difficulty_timer, game_start_time
    global score, hits, misses, current_difficulty, pattern_scored, video_playing
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
                    # play_intro_video()
                    # Wait 2 seconds for intro text
                    pygame.time.wait(3000)
                    game_state = PLAYING_GAME
                    pattern_timer = current_time
                    difficulty_timer = current_time
                    game_start_time = current_time
                    score = 0
                    hits = 0
                    misses = 0
                    current_difficulty = 1
                    active_tiles = {}  # Clear the center tile
                    pattern_scored = False
                    video_playing = False
                    last_stump_pos = None  # Initialize last_stump_pos

        # Handle game over timer
        if game_state == GAME_OVER:
            if video_playing:
                # Wait 2 seconds for video text
                if current_time - game_over_timer > 3500:
                    video_playing = False
                    game_over_timer = current_time  # Reset timer for score display
            elif current_time - game_over_timer > game_over_duration:
                game_state = WAITING_FOR_START
                active_tiles = {(2, 2): "stump"}  # Highlight center tile
                video_playing = False
        
        # Update game logic
        if game_state == PLAYING_GAME:
            # Check for tile presses
            check_tile_press()
            
            # Check if game time is up (1 minute)
            if current_time - game_start_time >= game_duration:
                won = score > 0
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
                pattern_scored = False  # Reset the scoring flag for the new pattern
        
        # Draw everything
        screen.fill((0, 0, 0))  # Black background
        
        draw_grid_area()
        draw_ui_area()
        
        pygame.display.flip()
        clock.tick(30)

def run_arduino_game():
    """Main game loop for Arduino-based gameplay"""
    global game_state, active_tiles, pattern_timer, difficulty_timer, game_start_time
    global score, hits, misses, current_difficulty, pattern_scored, video_playing
    global pattern_interval, game_over_timer
    
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
                active_tiles = {(2, 2): "stump"}  # Highlight center tile
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
                score = 0
                hits = 0
                misses = 0
                current_difficulty = 1
                active_tiles = {}  # Clear the center tile
                pattern_scored = False
                video_playing = False
                
                # Start background video in a non-blocking thread
                video_thread = threading.Thread(target=play_looping_background_video, daemon=True)
                video_thread.start()
        
        elif game_state == PLAYING_GAME:
            # Check for tile presses using Arduino
            check_tile_press()
            
            # Check if game time is up (1 minute)
            if current_time - game_start_time >= game_duration:
                won = score > 0
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
                # Turn off all tiles first
                turn_off_all_tiles()
                
                # Generate new pattern
                active_tiles = generate_pattern(current_difficulty, last_stump_pos)
                
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
                pattern_scored = False  # Reset the scoring flag for the new pattern
            
            # Draw gameplay screen
            screen.fill((0, 0, 0))  # Black background
            
            # Draw mini grid in bottom 20%
            draw_mini_grid()
            
            # Draw UI info in bottom area
            draw_ui_area()
            
            pygame.display.flip()
        
        elif game_state == GAME_OVER:
            if video_playing:
                # Wait for video to finish
                if current_time - game_over_timer > 3500:
                    video_playing = False
                    game_over_timer = current_time
            else:
                # Show final score fullscreen
                game_state = SHOWING_FINAL_SCORE
                show_final_score_fullscreen()
        
        elif game_state == SHOWING_FINAL_SCORE:
            # Final score is already displayed, wait for key press
            pass
        
        clock.tick(30)

# Start the desktop game
run_desktop_game()

# Start the Arduino game
# run_arduino_game()

pygame.quit()
