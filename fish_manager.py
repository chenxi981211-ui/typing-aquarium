# fish_manager.py
import random

class SwimmingFish:
    def __init__(self, fish_id, label, sprite_path, x, y, width, height):
        self.fish_id = fish_id  # NEW: Store the ID
        self.label = label
        self.sprite_path = sprite_path
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.dx = random.choice([-1.5, -1, -0.5, 0.5, 1, 1.5])
        self.dy = random.choice([-1, -0.5, 0, 0.5, 1])