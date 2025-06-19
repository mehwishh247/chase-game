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
    Draw a 3x5 grid of square tiles across the screen using forest-themed colors.

    Args:
        screen: Pygame screen surface (fullscreen window)
        active_tiles: Dictionary with keys (row, col) and values as strings:
                      "stump" (safe), "rock" (obstacle)
    """
    # Get screen dimensions
    screen_width, screen_height = screen.get_size()

    # Grid configuration
    rows, cols = 3, 5
    padding = 20  # Padding between tiles

    # Calculate tile size to fit the grid with padding
    available_width = screen_width - (padding * (cols + 1))
    available_height = screen_height - (padding * (rows + 1))
    tile_size = min(available_width // cols, available_height // rows)

    # Forest-themed color mapping
    colors = {
        "default": (1, 50, 32),         # Dark green (floor, unlit)
        "stump": (139, 69, 19),         # Brown (safe)
        "rock": (47, 79, 79),           # Dark gray (obstacle)
    }

    # Draw each tile in the grid
    for row in range(rows):
        for col in range(cols):
            # Calculate tile position
            x = padding + col * (tile_size + padding)
            y = padding + row * (tile_size + padding)

            # Determine tile color
            tile_type = active_tiles.get((row, col), None)
            if tile_type == "stump":
                color = colors["stump"]
            elif tile_type == "rock":
                color = colors["rock"]
            else:
                color = colors["default"]

            # Draw the tile
            tile_rect = pygame.Rect(x, y, tile_size, tile_size)
            pygame.draw.rect(screen, color, tile_rect)



