import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Video Settings
MAX_VIDEO_LENGTH = 600  # 10 minutes in seconds
REEL_DURATION = 30  # 30 seconds per reel
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 9:16 aspect ratio for reels

# Paths
TEMP_DIR = 'temp'
OUTPUT_DIR = 'output'

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)