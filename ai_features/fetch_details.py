import pytesseract
from typing import Tuple, Dict, Optional
import cv2
import numpy as np
from pdf2image import convert_from_path
import re

class OCRDetailsExtractor:
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
        
    def clean_text(self, text: str) -> str:
        """Clean text by removing non-ASCII characters and normalizing whitespace."""
        # Remove non-ASCII characters but keep basic punctuation
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def normalize_address(self, address: str) -> str:
        """Normalize address by removing noise and standardizing format."""
        if not address:
            return None
            
        # Remove common OCR artifacts and noise
        noise_patterns = [
            r'pears\s+Paha\s*\d*',  # Remove "pears Paha" and any following numbers
            r'PUR\s+coven\s+wae\s+keg\s+\d*',  # Remove "PUR coven wae keg" and numbers
            r'Mau\s+eheret\s+nna\s+Ce\s*:*\s*\d*',  # Remove "Mau eheret nna Ce" and numbers
            r'\s+:\s+',  # Remove colons with spaces
            r'\s+,\s+',  # Normalize commas
            r'\s+-\s+',  # Normalize hyphens
        ]
        
        # Apply noise removal patterns
        for pattern in noise_patterns:
            address = re.sub(pattern, ', ', address)
        
        # Split address into components
        components = [comp.strip() for comp in address.split(',') if comp.strip()]
        
        # Remove duplicate components
        seen = set()
        unique_components = []
        for comp in components:
            comp_normalized = comp.upper()
            if comp_normalized not in seen:
                seen.add(comp_normalized)
                unique_components.append(comp)
        
        # Reconstruct address
        clean_address = ', '.join(unique_components)
        
        # Final cleanup
        clean_address = re.sub(r'\s+', ' ', clean_address)  # Normalize spaces
        clean_address = re.sub(r',\s*,', ',', clean_address)  # Remove double commas
        clean_address = re.sub(r'[\s,]+-[\s,]', ' - ', clean_address)  # Clean up around hyphens
        clean_address = re.sub(r',\s*$', '', clean_address)  # Remove trailing comma
        
        return clean_address
        
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess the image for better OCR results."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        denoised = cv2.fastNlMeansDenoising(threshold)
        return denoised

    def extract_text_from_image(self, image: np.ndarray) -> str:
        """Extract text from a preprocessed image using OCR."""
        try:
            custom_config = '--psm 6 --oem 3 -l eng'
            return pytesseract.image_to_string(image, config=custom_config)
        except Exception as e:
            print(f"OCR extraction error: {str(e)}")
            return ""

    def extract_name_from_aadhar(self, text: str) -> Optional[str]:
        """Extract name from Aadhar card format."""
        # Clean the text first
        text = self.clean_text(text)
        
        # Look for the name after "Government of India" and before "DOB" or "MALE"
        name_pattern = r'Government of India\s+([A-Z][a-z]+ [A-Z][a-z]+)'
        match = re.search(name_pattern, text)
        if match:
            return match.group(1).strip()
            
        # Alternative pattern looking for name in standard format
        alt_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        matches = re.findall(alt_pattern, text)
        if matches:
            # Return the first match that's not part of the address
            for match in matches:
                if 'S/O' not in match and 'D/O' not in match:
                    return match.strip()
        
        return None

    def extract_address_from_aadhar(self, text: str) -> Optional[str]:
        """Extract address from Aadhar card format."""
        # Clean the text first
        text = self.clean_text(text)
        
        # Look for address pattern after "Address:" or "ADDRESS:"
        address_pattern = r'(?:Address|ADDRESS)\s*:\s*(S/O.*?(?:\d{6}|-\s*\d{6}))'
        match = re.search(address_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            address = match.group(1).strip()
        else:
            # Alternative pattern if "Address:" is not found
            alt_pattern = r'S/O.*?(?:\d{6}|-\s*\d{6})'
            match = re.search(alt_pattern, text, re.DOTALL)
            if match:
                address = match.group(0).strip()
            else:
                return None
        
        # Normalize and clean the address
        return self.normalize_address(address)

    def detect_document_type(self, text: str) -> str:
        """Detect the type of document based on content."""
        text = self.clean_text(text)
        if any(keyword in text.upper() for keyword in ['HDFC BANK', 'ACCOUNT NO', 'STATEMENT OF ACCOUNT']):
            return 'bank_statement'
        elif any(keyword in text.upper() for keyword in ['UIDAI', 'AADHAR', 'VID', 'GOV.IN', 'GOVERNMENT OF INDIA']):
            return 'aadhar'
        return 'unknown'

    def extract_details_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extract full name and address from OCR text output."""
        if not text:
            return {"full_name": None, "address": None}

        # Clean the text
        text = self.clean_text(text)
        
        # Detect document type
        doc_type = self.detect_document_type(text)
        
        # Extract details based on document type
        if doc_type == 'aadhar':
            name = self.extract_name_from_aadhar(text)
            address = self.extract_address_from_aadhar(text)
        else:
            name, address = None, None

        return {"full_name": name, "address": address}

    def process_file(self, file_path: str) -> Tuple[Dict[str, Optional[str]], Optional[str]]:
        """Process file and extract details."""
        try:
            text = ""
            
            if file_path.lower().endswith(".pdf"):
                pages = convert_from_path(file_path)
                for page in pages:
                    image = np.array(page)
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    preprocessed_image = self.preprocess_image(image)
                    page_text = self.extract_text_from_image(preprocessed_image)
                    text += page_text + "\n"
            else:
                image = cv2.imread(file_path)
                if image is None:
                    return {}, "Error: Could not open image file."
                
                preprocessed_image = self.preprocess_image(image)
                text = self.extract_text_from_image(preprocessed_image)

            # Extract details
            details = self.extract_details_from_text(text)
            return details, None

        except Exception as e:
            return {}, f"OCR extraction failed: {str(e)}"

# Example usage
if __name__ == "__main__":
    extractor = OCRDetailsExtractor()
    file_path = "harsh-aadhar.pdf"  # Replace with your file path
    
    details, error = extractor.process_file(file_path)
    
    if error:
        print(f"Error: {error}")
    else:
        print("\nExtracted Details:")
        print(f"Full Name: {details['full_name']}")
        print(f"Address: {details['address']}")