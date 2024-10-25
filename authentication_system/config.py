import os
from pathlib import Path

class Config:
    # Base directory
    BASE_DIR = Path(__file__).parent.absolute()
    
    # Authentication settings
    CODE_LENGTH = 6
    CODE_EXPIRY_SECONDS = 300  # 5 minutes
    
    # Video processing settings
    REQUIRED_FRAMES = 30  # Number of frames to analyze
    FRAME_INTERVAL = 5   # Analyze every 5th frame
    
    # Face recognition settings
    FACE_CONFIDENCE_THRESHOLD = 0.85
    FACE_DETECTION_MODEL = "hog"  # or "cnn" for GPU
    
    # OCR settings
    OCR_CONFIDENCE_THRESHOLD = 0.75
    
    # Speech recognition settings
    SPEECH_CONFIDENCE_THRESHOLD = 0.8
    SPEECH_LANGUAGE = "en-US"
    
    # Storage settings
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Frame extraction settings
    FACE_FRAME_COUNT = 5    # Number of frames to use for face verification
    CODE_FRAME_COUNT = 10   # Number of frames to use for OCR
    AUDIO_DURATION = 5      # Duration in seconds to extract for audio analysis