import pygame
import subprocess
import time
import random
from tile_logic import draw_tile_grid #, get_pressed_tile

pygame.init()

# Set up 16:9 aspect ratio screen
screen_width = 1920
screen_height = 1080
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# Calculate areas: 60% for grid, 40% for UI
grid_width = int(screen_width * 0.6)
ui_width = screen_width - grid_width
grid_height = screen_height
ui_height = screen_height

# Game states
WAITING_FOR_START = "waiting_for_start"
PLAYING_INTRO = "playing_intro"
PLAYING_GAME = "playing_game"
GAME_OVER = "game_over"

# Game variables
game_state = WAITING_FOR_START
active_tiles = {(2, 2): "stump"}  # Initialize with center tile as stump
pattern_timer = 0
pattern_interval = 3000  # 3 seconds in milliseconds
difficulty_timer = 0
difficulty_interval = 10000  # 10 seconds in milliseconds
current_difficulty = 1
max_difficulty = 5
score = 0
game_over_timer = 0
game_over_duration = 4000  # 4 seconds for score display
game_start_time = 0
game_duration = 60000  # 1 minute in milliseconds
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
    """Show intro video text instead of playing actual video"""
    global video_playing, video_text
    video_playing = True
    video_text = "Intro video playing..."

def play_win_video():
    """Show win video text instead of playing actual video"""
    global video_playing, video_text
    video_playing = True
    video_text = "Win video playing..."

def play_lose_video():
    """Show lose video text instead of playing actual video"""
    global video_playing, video_text
    video_playing = True
    video_text = "Lose video playing..."

def generate_pattern(difficulty):
    """
    Generate a tile pattern for a 3x5 grid based on difficulty.
    - Always at least one "stump" and one "rock"
    - Total number of tiles is 2 to 4
    - At low difficulty, more stumps than rocks
    - At high difficulty, more rocks than stumps
    - Never place two types on the same tile
    - Never exceed 4 lit tiles total
    - Valid positions: (row, col) with row in 0-2, col in 0-4
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

    # Randomly select unique positions for stumps and rocks
    positions = random.sample(all_positions, num_tiles)
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
    screen.blit(ui_surface, (grid_width, 0))

def draw_grid_area():
    """Draw the tile grid in the left area maintaining aspect ratio"""
    # Create a surface for the grid area
    grid_surface = pygame.Surface((grid_width, grid_height))
    grid_surface.fill((0, 0, 0))  # Black background
    
    # Draw the tile grid on the grid surface
    draw_tile_grid(grid_surface, active_tiles)
    
    # Draw grid area on main screen
    screen.blit(grid_surface, (0, 0))

def end_game(won):
    """End the game and show appropriate video"""
    global game_state, game_over_timer, video_playing
    game_state = GAME_OVER
    game_over_timer = pygame.time.get_ticks()
    
    if won:
        play_win_video()
    else:
        play_lose_video()

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
                pygame.time.wait(7000)
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
            active_tiles = generate_pattern(current_difficulty)
            pattern_timer = current_time
            pattern_scored = False  # Reset the scoring flag for the new pattern
    
    # Draw everything
    screen.fill((0, 0, 0))  # Black background
    
    draw_grid_area()
    draw_ui_area()
    
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
