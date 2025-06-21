
class ScoreTracker:
    def __init__(self):
        self.score = 0
        self.hits = 0
        self.misses = 0
        self.pattern_scored = False  # only score once per pattern

    def reset(self):
        self.score = 0
        self.hits = 0
        self.misses = 0
        self.pattern_scored = False

    def check_tile_press(self, pressed_tile, active_tiles):
        """
        Updates score and flags based on tile press.
        Returns True if scored, False if already scored or no press.
        """
        if self.pattern_scored or pressed_tile is None:
            return False

        if pressed_tile in active_tiles:
            if active_tiles[pressed_tile] == "stump":
                self.score += 2
                self.hits += 1
            else:
                self.score -= 1
                self.misses += 1
        else:
            self.score -= 1
            self.misses += 1

        self.pattern_scored = True
        return True
