import random


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
    max_difficulty = 5

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


# def generate_tile_pattern(difficulty_level):
#     """
#     Generate a tile pattern for a 3x5 grid based on difficulty level.
#     Returns a dictionary with keys (row, col) and values as color strings.
#     - At least one green (safe) tile.
#     - Number of red (rock) tiles increases with difficulty.
#     - Optionally one blue (stump) tile.
#     - No overlapping colors on the same tile.
#     """
#     rows, cols = 3, 5
#     all_tiles = [(r, c) for r in range(rows) for c in range(cols)]
#     pattern = {}

#     # Always at least one green (safe) tile
#     green_tile = random.choice(all_tiles)
#     pattern[green_tile] = "green"

#     # Determine number of red (rock) tiles based on difficulty
#     # For example: 1 at level 1, up to 8 at level 5
#     min_rocks = 1
#     max_rocks = 8
#     num_rocks = min_rocks + (max_rocks - min_rocks) * (difficulty_level - 1) // 4
#     num_rocks = min(max(num_rocks, min_rocks), max_rocks)

#     # Choose red tiles, avoiding overlap with green
#     available_for_red = [tile for tile in all_tiles if tile != green_tile]
#     red_tiles = set(random.sample(available_for_red, min(num_rocks, len(available_for_red))))
#     for tile in red_tiles:
#         pattern[tile] = "red"

#     # Optionally add a blue (stump) tile, 50% chance
#     if len(pattern) < len(all_tiles):
#         if random.random() < 0.5:
#             available_for_blue = [tile for tile in all_tiles if tile not in pattern]
#             if available_for_blue:
#                 blue_tile = random.choice(available_for_blue)
#                 pattern[blue_tile] = "blue"

#     return pattern
