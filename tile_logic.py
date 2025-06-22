'''# Cursor:
# Create a draw_tile_grid(screen, active_tiles) function using Pygame.
# The screen is a fullscreen window.
# Draw a 3x5 grid of square tiles across the screen.
# active_tiles is a dictionary with keys like (row, col) and values as color strings: "green", "red", "blue".
# If a tile is not in the dictionary, draw it as dark gray.
# Draw each tile as a square with padding between them. '''

import pygame

def draw_tile_grid(screen, active_tiles):
    """
    Draw a 3x5 grid of tiles with a 3:2 aspect ratio using light gray colors,
    centered on the provided screen surface.

    Args:
        screen: Pygame screen surface
        active_tiles: Dictionary with keys (row, col) and values as strings:
                      "stump" (safe), "rock" (obstacle)
    """
    screen_width, screen_height = screen.get_size()

    rows, cols = 3, 5
    padding = 15  # Reduced padding to bring tiles closer

    # Calculate total available space for tiles, excluding padding from all sides
    available_width = screen_width - (padding * 2)
    available_height = screen_height - (padding * 2)

    # Calculate tile dimensions based on a 3:2 aspect ratio, considering padding between tiles
    h_from_width = (available_width - (cols - 1) * padding) / (cols * 1.5)
    h_from_height = (available_height - (rows - 1) * padding) / rows
    
    tile_height = min(h_from_width, h_from_height)
    if tile_height < 0: tile_height = 0
    tile_width = tile_height * 1.5
    
    # Darker gray color mapping
    colors = {
        "default": (160, 160, 160),  # Darker gray (unlit)
        "stump": (190, 190, 190),    # Lighter gray (safe)
        "rock": (130, 130, 130),     # Darkest gray (obstacle)
        "cue": (139, 69, 19),       # Brown for the cue tile
    }

    corner_radius = 15

    # Calculate starting position to align grid to the top
    grid_content_width = cols * tile_width + (cols - 1) * padding
    grid_content_height = rows * tile_height + (rows - 1) * padding
    start_x = (screen_width - grid_content_width) / 2
    start_y = padding # Align to top with a small padding

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * (tile_width + padding)
            y = start_y + row * (tile_height + padding)

            tile_type = active_tiles.get((row, col), None)
            if tile_type == "stump":
                color = colors["stump"]
            elif tile_type == "rock":
                color = colors["rock"]
            elif tile_type == "cue":
                color = colors["cue"]
            else:
                color = colors["default"]

            tile_rect = pygame.Rect(x, y, tile_width, tile_height)
            pygame.draw.rect(screen, color, tile_rect, border_radius=corner_radius)



