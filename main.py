from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import math
from pymongo import MongoClient
from bson.json_util import dumps
import openai

# Import services
from authentication_system.config import Config
from authentication_system.services.video_processor import VideoProcessor
from authentication_system.services.face_recognition import FaceVerifier
from authentication_system.services.ocr import OCRVerifier
from authentication_system.services.speech_recognition import SpeechVerifier
from authentication_system.services.code_generator import CodeGenerator
from authentication_system.utils.error_handling import handle_errors, create_success_response, create_error_response, AuthenticationError, CustomFileNotFoundError, ContentTooLarge
from ai_features.fetch_details import OCRDetailsExtractor
from ai_features.exchange_recommendation import ExchangeRateService
from utils import parse_address, haversine_distance

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size

# Initialize services
video_processor = VideoProcessor()
face_verifier = FaceVerifier(confidence_threshold=Config.FACE_CONFIDENCE_THRESHOLD)
ocr_verifier = OCRVerifier(confidence_threshold=Config.OCR_CONFIDENCE_THRESHOLD)
speech_verifier = SpeechVerifier(confidence_threshold=Config.SPEECH_CONFIDENCE_THRESHOLD)
code_generator = CodeGenerator(code_length=Config.CODE_LENGTH)
ocr_details_extractor = OCRDetailsExtractor(confidence_threshold=Config.OCR_CONFIDENCE_THRESHOLD)
exchange_service = ExchangeRateService()

# MongoDB client setup (replace with your connection string)
client = MongoClient('mongodb://localhost:27017/')
db = client['currency_exchange_db']  # Replace with your database name
users_collection = db['users']  # Replace with your users collection name

def save_uploaded_video(file) -> str:
    """Save uploaded video file and return its path."""
    filename = secure_filename(f"video_{datetime.now().timestamp()}.mp4")
    filepath = os.path.join(Config.TEMP_DIR, filename)
    file.save(filepath)
    return filepath

# App route for video and audio authentication
@app.route('/api/verify', methods=['POST'])
@handle_errors
def verify_video():
    """
    Verify user authentication through video stream analysis.
    The video should contain:
    1. User's face
    2. User showing the verification code
    3. User speaking the verification code
    """
    # Check if video file is provided
    if 'video' not in request.files:
        raise AuthenticationError('No video file provided')
    
    # Check if verification code is provided
    if 'code' not in request.form:
        raise AuthenticationError('No verification code provided')
    
    code = request.form['code']
    if not code_generator.verify_code(code):
        raise AuthenticationError('Invalid or expired verification code')

    video_file = request.files['video']
    video_path = save_uploaded_video(video_file)
    
    try:
        # Process video to extract frames and audio
        frame_paths, audio_path, error = video_processor.extract_frames_and_audio(video_path)
        if error:
            raise AuthenticationError(f"Video processing failed: {error}")

        # Verify face using the best face frames
        face_frames = video_processor.get_best_frames(
            frame_paths, 
            0, 
            Config.FACE_FRAME_COUNT
        )
        face_verified = False
        for frame in face_frames:
            success, error_message = face_verifier.verify_face(frame)
            if success:
                face_verified = True
                break
        
        if not face_verified:
            raise AuthenticationError("Face verification failed")

        # Verify code using OCR on the best code frames
        code_frames = video_processor.get_best_frames(
            frame_paths, 
            Config.FACE_FRAME_COUNT, 
            Config.CODE_FRAME_COUNT
        )
        code_verified = False
        for frame in code_frames:
            success, error_message = ocr_verifier.verify_code(frame, code)
            if success:
                code_verified = True
                break
        
        if not code_verified:
            raise AuthenticationError("Code verification through OCR failed")

        # Verify spoken code
        speech_success, speech_error = speech_verifier.verify_speech(audio_path, code)
        if not speech_success:
            raise AuthenticationError(f"Speech verification failed: {speech_error}")

        # If all verifications passed, invalidate the code and return success
        code_generator.invalidate_code(code)
        
        return create_success_response({
            'message': 'Authentication successful',
            'verifications': {
                'face': True,
                'ocr': True,
                'speech': True
            }
        })

    finally:
        # Cleanup temporary files
        if os.path.exists(video_path):
            os.remove(video_path)
        if 'frame_paths' in locals():
            video_processor.cleanup_files(frame_paths, audio_path)

# App route to fetch details from documents or images and compare addresses for verification and return the name and address
@app.route('/api/fetchDetails', methods=['POST'])
@handle_errors
def fetchDetails():
    """
    Extract and compare details from two uploaded files (images or PDFs).
    Returns extracted details if they match, raises error if they don't.
    """
    # Validate file presence with custom exception
    if 'file1' not in request.files:
        raise CustomFileNotFoundError(
            message="First file (file1) is missing from the request",
            status_code=404
        )
    
    if 'file2' not in request.files:
        raise CustomFileNotFoundError(
            message="Second file (file2) is missing from the request",
            status_code=404
        )

    file1 = request.files['file1']
    file2 = request.files['file2']

    # Validate file contents
    if file1.filename == '':
        raise CustomFileNotFoundError(
            message="First file is empty or no file was selected",
            status_code=404
        )
    
    if file2.filename == '':
        raise CustomFileNotFoundError(
            message="Second file is empty or no file was selected",
            status_code=404
        )

    # Save uploaded files temporarily
    timestamp = datetime.now().timestamp()
    file1_path = os.path.join(Config.TEMP_DIR, secure_filename(f"file1_{timestamp}"))
    file2_path = os.path.join(Config.TEMP_DIR, secure_filename(f"file2_{timestamp}"))
    
    try:
        # Handle file saving errors
        try:
            file1.save(file1_path)
        except Exception as e:
            raise CustomFileNotFoundError(
                message=f"Error saving first file: {str(e)}",
                status_code=404
            )

        try:
            file2.save(file2_path)
        except Exception as e:
            raise CustomFileNotFoundError(
                message=f"Error saving second file: {str(e)}",
                status_code=404
            )

        # Extract details from both files
        details1, error1 = ocr_details_extractor.process_file(file1_path)
        if error1:
            raise AuthenticationError(f"Error processing first file: {error1}")

        details2, error2 = ocr_details_extractor.process_file(file2_path)
        if error2:
            raise AuthenticationError(f"Error processing second file: {error2}")

        # Validate that required fields were extracted
        if not details1.get('full_name') or not details1.get('address'):
            raise AuthenticationError("Could not extract required details from first file")
        if not details2.get('full_name') or not details2.get('address'):
            raise AuthenticationError("Could not extract required details from second file")

        # Parse addresses into structured format for storage
        parsed_address1 = parse_address(details1['address'])
        parsed_address2 = parse_address(details2['address'])

        # Compare details
        name_match = details1['full_name'].lower().strip() == details2['full_name'].lower().strip()
        
        # Normalize addresses for comparison by removing extra spaces and converting to lowercase
        def normalize_address(address_str):
            return ' '.join(address_str.lower().split())

        # Compare complete addresses as strings
        address1_normalized = normalize_address(details1['address'])
        address2_normalized = normalize_address(details2['address'])
        address_match = address1_normalized == address2_normalized

        if not (name_match and address_match):
            raise AuthenticationError("Details from the two files do not match")

        # Return success response with matched details
        return create_success_response({
            'message': 'Details matched successfully',
            'details': {
                'full_name': details1['full_name'],
                'address': parsed_address1,  # Return structured address for storage/display
            },
            'verification': {
                'name_match': True,
                'address_match': True
            }
        })

    finally:
        # Cleanup temporary files
        for filepath in [file1_path, file2_path]:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing temporary file {filepath}: {str(e)}")

# App Route for best time to exchange currency
@app.route('/api/get_exchange_recommendation', methods=['POST'])
def get_exchange_recommendation():
    """
    API route to get exchange rate recommendations.
    Expects 'from_currency', 'to_currency', and 'amount' in the request body.
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        amount = data.get('amount')
        
        if not from_currency or not to_currency or not amount:
            return jsonify({"error": "Please provide 'from_currency', 'to_currency', and 'amount'"}), 400

        # Get recommended exchange rates
        rates = exchange_service.get_best_rates(from_currency, to_currency, float(amount))
        
        return jsonify({
            "message": "Exchange rate recommendations retrieved successfully",
            "recommendations": rates
        })

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to retrieve exchange rates"}), 500

# App route to find best matches for currency P2P exchange
@app.route('/api/get_best_matches', methods=['POST'])
def get_best_matches():
    """
    API route to get the best matches for currency exchange.
    Expects 'userID', 'latitude', 'longitude', 'amount', 'currency', 'price' and 'distance' in the request body.
    """
    try:
        data = request.get_json()

        # Extract parameters from the request
        user_id = data.get('userID')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        amount = data.get('amount')
        currency = data.get('currency')
        price = data.get('price')
        distance = data.get('distance')

        if not all([user_id, latitude, longitude, amount, currency, price, distance]):
            return jsonify({"error": "Please provide 'userID', 'latitude', 'longitude', 'amount', 'currency', 'price' and 'distance'"}), 400

        # Calculate the distance threshold for matching (in kilometers)
        distance_threshold = 50  # Value is in km
        if distance > distance_threshold:
            raise ContentTooLarge(message=f"Distance value is greater than {distance_threshold}km")

        # Find matches based on criteria
        matches = []

        # Query to find potential matches
        potential_matches = users_collection.find({
            "currency": currency,
            "price": {"$lte": price},  # Find users with a price less than or equal to the user's price
        })

        for user in potential_matches:
            # Calculate the distance using Haversine formula
            user_latitude = user['latitude']
            user_longitude = user['longitude']

            # Haversine formula to calculate the distance between two points on the earth
            distance = haversine_distance.haversine(latitude, longitude, user_latitude, user_longitude)

            if distance <= distance_threshold and user['userID'] != user_id:  # Exclude the requesting user
                matches.append({
                    "userID": user['userID'],
                    "latitude": user['latitude'],
                    "longitude": user['longitude'],
                    "currency": user['currency'],
                    "price": user['price'],
                    "distance": distance
                })

        return jsonify({
            "message": "Best matches retrieved successfully",
            "matches": matches
        })

    except ContentTooLarge as e:
        return jsonify({"error": str(e)}), 413  # 413 Payload Too Large
    except Exception as e:
        return jsonify({"error": "An error occurred while retrieving matches", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
