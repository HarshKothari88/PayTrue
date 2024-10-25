import speech_recognition as sr
from typing import Tuple, Optional
from authentication_system.config import Config

class SpeechVerifier:
    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold
        self.recognizer = sr.Recognizer()
    
    def verify_speech(self, audio_path: str, expected_code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify if the spoken code matches the expected code.
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            with sr.AudioFile(audio_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source)
                
                # Record the audio
                audio = self.recognizer.record(source)
                
                # Perform speech recognition
                text = self.recognizer.recognize_google(
                    audio,
                    language=Config.SPEECH_LANGUAGE
                )
                
                # Clean and format the recognized text
                recognized_code = ''.join(text.strip().split())
                
                # Compare with expected code
                if recognized_code.upper() == expected_code.upper():
                    return True, None
                else:
                    return False, f"Code mismatch: expected {expected_code}, found {recognized_code}"
                    
        except sr.UnknownValueError:
            return False, "Speech could not be understood"
        except sr.RequestError as e:
            return False, f"Could not request results from speech recognition service: {str(e)}"
        except Exception as e:
            return False, f"Speech verification failed: {str(e)}"