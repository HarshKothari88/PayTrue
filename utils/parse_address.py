from typing import Dict, Optional
import re

def parse_address(address_text: str) -> Dict[str, Optional[str]]:
    """
    Parse a raw address string into structured components.
    
    Args:
        address_text (str): Raw address string from OCR
        
    Returns:
        Dict containing parsed address fields
    """
    # Initialize address components
    address_components = {
        'line1': None,
        'line2': None,
        'city': None,
        'state': None,
        'country': None,
        'pincode': None
    }
    
    try:
        # Split address into lines and clean them
        lines = [line.strip() for line in address_text.split('\n') if line.strip()]
        
        # Extract pincode using regex (assuming 6-digit Indian pincode)
        pincode_pattern = r'\b\d{6}\b'
        pincode_match = re.search(pincode_pattern, address_text)
        if pincode_match:
            address_components['pincode'] = pincode_match.group(0)
            # Remove pincode from the address text for further processing
            address_text = re.sub(pincode_pattern, '', address_text)
        
        # Process remaining lines
        if lines:
            # First line is typically street address
            address_components['line1'] = lines[0].strip()
            
            # Second line might contain additional street info
            if len(lines) > 1:
                address_components['line2'] = lines[1].strip()
            
            # Look for state and country in the last lines
            remaining_lines = lines[2:] if len(lines) > 2 else []
            for line in remaining_lines:
                # Common Indian states_and_union_territories
                states_and_union_territories = [
                                        # states_and_union_territories
                                        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
                                        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
                                        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 
                                        'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 
                                        'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 
                                        'West Bengal',

                                        # Union Territories
                                        'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 
                                        'Lakshadweep', 'Delhi', 'Puducherry', 'Ladakh', 'Jammu and Kashmir']
                line = line.strip()
                # Check if line contains a state name
                for state in states_and_union_territories:
                    if state.lower() in line.lower():
                        address_components['state'] = state
                        # The city might be before the state in the same line
                        city_part = line.lower().split(state.lower())[0].strip()
                        if city_part:
                            address_components['city'] = city_part.title()
                
                # Check for country
                if 'india' in line.lower():
                    address_components['country'] = 'India'
            
            # If city wasn't found in state line, check previous lines
            if not address_components['city'] and len(lines) > 2:
                address_components['city'] = lines[2].strip()

    except Exception as e:
        print(f"Error parsing address: {str(e)}")
        # Return original address as line1 if parsing fails
        address_components['line1'] = address_text
    
    return address_components