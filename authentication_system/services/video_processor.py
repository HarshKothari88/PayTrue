import cv2
import numpy as np
from typing import Tuple, List, Optional
import os
import tempfile
from moviepy.editor import VideoFileClip
from authentication_system.config import Config

class VideoProcessor:
    def __init__(self):
        self.temp_dir = Config.TEMP_DIR

    def extract_frames_and_audio(self, video_path: str) -> Tuple[List[str], str, Optional[str]]:
        """
        Extract frames and audio from video file.
        Returns: (frame_paths: List[str], audio_path: str, error_message: Optional[str])
        """
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return [], "", "Failed to open video file"

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            # Extract audio using moviepy
            video = VideoFileClip(video_path)
            audio_path = os.path.join(self.temp_dir, "temp_audio.wav")
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)

            frame_paths = []
            frame_count = 0
            saved_count = 0

            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % Config.FRAME_INTERVAL == 0:
                    frame_path = os.path.join(
                        self.temp_dir, 
                        f"frame_{saved_count}.jpg"
                    )
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    saved_count += 1

                frame_count += 1

                if saved_count >= Config.REQUIRED_FRAMES:
                    break

            cap.release()
            return frame_paths, audio_path, None

        except Exception as e:
            return [], "", f"Error processing video: {str(e)}"

    def cleanup_files(self, frame_paths: List[str], audio_path: str):
        """Clean up temporary files."""
        for frame_path in frame_paths:
            if os.path.exists(frame_path):
                os.remove(frame_path)
        
        if os.path.exists(audio_path):
            os.remove(audio_path)

    def get_best_frames(self, frame_paths: List[str], start_idx: int, count: int) -> List[str]:
        """Get the best frames for analysis based on image quality."""
        if len(frame_paths) <= count:
            return frame_paths

        # Calculate image quality scores (using variance of Laplacian as a measure of focus)
        def get_focus_measure(image_path: str) -> float:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return cv2.Laplacian(gray, cv2.CV_64F).var()

        scores = [(path, get_focus_measure(path)) for path in frame_paths[start_idx:]]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return [score[0] for score in scores[:count]]