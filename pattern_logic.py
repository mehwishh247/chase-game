import random

def generate_tile_pattern(difficulty_level):
    """
    Generate a tile pattern for a 3x5 grid based on difficulty level.
    Returns a dictionary with keys (row, col) and values as color strings.
    - At least one green (safe) tile.
    - Number of red (rock) tiles increases with difficulty.
    - Optionally one blue (stump) tile.
    - No overlapping colors on the same tile.
    """
    rows, cols = 3, 5
    all_tiles = [(r, c) for r in range(rows) for c in range(cols)]
    pattern = {}

    # Always at least one green (safe) tile
    green_tile = random.choice(all_tiles)
    pattern[green_tile] = "green"

    # Determine number of red (rock) tiles based on difficulty
    # For example: 1 at level 1, up to 8 at level 5
    min_rocks = 1
    max_rocks = 8
    num_rocks = min_rocks + (max_rocks - min_rocks) * (difficulty_level - 1) // 4
    num_rocks = min(max(num_rocks, min_rocks), max_rocks)

    # Choose red tiles, avoiding overlap with green
    available_for_red = [tile for tile in all_tiles if tile != green_tile]
    red_tiles = set(random.sample(available_for_red, min(num_rocks, len(available_for_red))))
    for tile in red_tiles:
        pattern[tile] = "red"

    # Optionally add a blue (stump) tile, 50% chance
    if len(pattern) < len(all_tiles):
        if random.random() < 0.5:
            available_for_blue = [tile for tile in all_tiles if tile not in pattern]
            if available_for_blue:
                blue_tile = random.choice(available_for_blue)
                pattern[blue_tile] = "blue"

    return pattern
