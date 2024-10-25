import pytesseract
from PIL import Image
from typing import Tuple, Optional
import cv2
import numpy as np
from authentication_system.config import Config

class OCRVerifier:
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess the image for better OCR results."""
        # Read image
        image = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Noise removal
        denoised = cv2.fastNlMeansDenoising(threshold)
        
        return denoised
    
    def verify_code(self, image_path: str, expected_code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify if the code in the image matches the expected code.
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(
                processed_image,
                config='--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            )
            
            # Clean the extracted text
            extracted_code = ''.join(text.strip().split())
            
            # Check if the extracted code matches the expected code
            if extracted_code.upper() == expected_code.upper():
                return True, None
            else:
                return False, f"Code mismatch: expected {expected_code}, found {extracted_code}"
                
        except Exception as e:
            return False, f"OCR verification failed: {str(e)}"