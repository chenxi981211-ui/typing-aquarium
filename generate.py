# generate_thumbnails.py - Run this script once
import os
from PIL import Image

THUMBNAIL_SIZE = (64, 64)
ASSETS_DIR = "assets"
THUMBNAIL_DIR = "assets/thumbnails"

# Create thumbnails directory if it doesn't exist
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

for filename in os.listdir(ASSETS_DIR):
    if filename.endswith("_swim.png") and not filename.startswith("."):
        fish_id = filename.replace("_swim.png", "")
        sprite_path = os.path.join(ASSETS_DIR, filename)
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{fish_id}.png")

        # Load sprite sheet and extract first frame
        sprite = Image.open(sprite_path)
        first_frame = sprite.crop((0, 0, 256, 256))
        thumbnail = first_frame.resize(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        thumbnail.save(thumbnail_path)
        print(f"Generated: {thumbnail_path}")