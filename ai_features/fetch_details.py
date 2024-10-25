import pytesseract
from PIL import Image
from typing import Tuple, Dict, Optional, Union
import cv2
import numpy as np
from pdf2image import convert_from_path
import os

class OCRDetailsExtractor:
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess the image for better OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Noise removal
        denoised = cv2.fastNlMeansDenoising(threshold)
        
        return denoised
    
    def extract_text_from_image(self, image: np.ndarray) -> str:
        """Extract text from a preprocessed image using OCR."""
        return pytesseract.image_to_string(
            image,
            config='--psm 6 --oem 3'
        )
    
    def extract_details_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extract full name and address from OCR text output."""
        cleaned_text = text.strip().split('\n')
        
        full_name = cleaned_text[0] if len(cleaned_text) > 0 else None
        address = cleaned_text[1] if len(cleaned_text) > 1 else None
        
        return {
            "full_name": full_name,
            "address": address
        }
    
    def process_file(self, file_path: str) -> Tuple[Dict[str, Optional[str]], Optional[str]]:
        """Detect file type, process and extract details accordingly."""
        try:
            # Check if the file is a PDF
            if file_path.lower().endswith(".pdf"):
                # Convert PDF to images (one image per page)
                pages = convert_from_path(file_path)
                
                # Perform OCR on each page
                text = ""
                for page in pages:
                    # Convert PIL image to OpenCV format
                    image = np.array(page)
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    
                    # Preprocess and extract text
                    preprocessed_image = self.preprocess_image(image)
                    text += self.extract_text_from_image(preprocessed_image) + "\n"
            else:
                # Process as an image
                image = cv2.imread(file_path)
                if image is None:
                    return {}, "Error: Could not open image file."
                
                preprocessed_image = self.preprocess_image(image)
                text = self.extract_text_from_image(preprocessed_image)
            
            # Extract details (full name and address) from text
            details = self.extract_details_from_text(text)
            return details, None
            
        except Exception as e:
            return {}, f"OCR extraction failed: {str(e)}"

# Example usage
if __name__ == "__main__":
    extractor = OCRDetailsExtractor()
    file_path = "path/to/your/file.pdf"  # Replace with your file path
    details, error = extractor.process_file(file_path)
    
    if error:
        print(error)
    else:
        print("Extracted Details:")
        print(f"Full Name: {details['full_name']}")
        print(f"Address: {details['address']}")
