import face_recognition
import numpy as np
from typing import Tuple, Optional
import cv2
from pathlib import Path
import os
from authentication_system.config import Config

class FaceVerifier:
    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
    
    def verify_face(self, image_path: str) -> Tuple[bool, Optional[str]]:
        """
        Verify a face in an image.
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            # Load the image
            image = face_recognition.load_image_file(image_path)
            
            # Find faces in the image
            face_locations = face_recognition.face_locations(
                image, 
                model=Config.FACE_DETECTION_MODEL
            )
            
            if not face_locations:
                return False, "No face detected in the image"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected in the image"
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return False, "Could not encode face features"
            
            # Here you would typically compare against a stored face encoding
            # For this example, we'll just return success if a face is found
            return True, None
            
        except Exception as e:
            return False, f"Face verification failed: {str(e)}"
    
    def store_face_encoding(self, image_path: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Store a face encoding for future verification.
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(
                image,
                model=Config.FACE_DETECTION_MODEL
            )
            
            if not face_locations:
                return False, "No face detected in the image"
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                return False, "Could not encode face features"
            
            # Save encoding to a file or database
            encoding_path = os.path.join(Config.TEMP_DIR, f"{user_id}_face_encoding.npy")
            np.save(encoding_path, face_encodings[0])
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to store face encoding: {str(e)}"