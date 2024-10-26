import random
import time
from typing import Dict

class CodeGenerator:
    def __init__(self, code_length: int = 4):
        self.code_length = code_length
        self.active_codes: Dict[str, float] = {}
    
    def generate_code(self, expiry_seconds: int = 300) -> str:
        """Generate a random 4-digit numeric code."""
        code = ''.join(random.choices('0123456789', k=4))
        self.active_codes[code] = time.time() + expiry_seconds
        return code
    
    def verify_code(self, code: str) -> bool:
        """Verify if a code is valid and not expired."""
        expiry_time = self.active_codes.get(code)
        if expiry_time is None:
            return False
        
        if time.time() > expiry_time:
            self.active_codes.pop(code, None)
            return False
            
        return True
    
    def invalidate_code(self, code: str) -> None:
        """Invalidate a code immediately."""
        self.active_codes.pop(code, None)
    
    def cleanup_expired_codes(self) -> None:
        """Remove all expired codes."""
        current_time = time.time()
        self.active_codes = {
            code: expiry
            for code, expiry in self.active_codes.items()
            if expiry > current_time
        }