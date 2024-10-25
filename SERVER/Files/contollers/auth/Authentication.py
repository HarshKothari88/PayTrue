from pymongo import MongoClient #type: ignore
from bson import ObjectId #type: ignore
from dotenv import load_dotenv #type: ignore
import os,requests

load_dotenv()

JASWANTH_BACKEND_URL = os.getenv("JASWANTH_BACKEND")
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION_USERS")

client = MongoClient(mongo_uri)
db = client[mongo_db]
userCollection = db[mongo_collection]



PHOTOGRAPH_UPLOAD_FOLDER = 'uploads/photographs'
if not os.path.exists(PHOTOGRAPH_UPLOAD_FOLDER):
    os.makedirs(PHOTOGRAPH_UPLOAD_FOLDER)

IDPROOF_UPLOAD_FOLDER = 'uploads/idproofs'
if not os.path.exists(IDPROOF_UPLOAD_FOLDER):
    os.makedirs(IDPROOF_UPLOAD_FOLDER)

ADDRESSPROOF_UPLOAD_FOLDER = 'uploads/addressproofs'
if not os.path.exists(ADDRESSPROOF_UPLOAD_FOLDER):
    os.makedirs(ADDRESSPROOF_UPLOAD_FOLDER)


def addUser(user_data):
    userFormData = user_data.form
    try:
        if not userFormData:
            return {"message": "No data provided"}, 400
        
        required_fields = ["name", "email", "phone", "gender", "dateOfBirth", "occupation", "country", "idProofType", "addressProofType", "password"]
        missing_fields = [field for field in required_fields if field not in userFormData]
        
        if missing_fields:
            return {"message": f"Missing required data: {', '.join(missing_fields)}"}, 400
        
        photograph = user_data.files['photograph']
        if photograph.filename == '':
            return {"error": "No photograph selected"}, 400
        photographfilename = photograph.filename
        photograph_file_path = os.path.join(PHOTOGRAPH_UPLOAD_FOLDER, photographfilename)
        photograph.save(photograph_file_path)

        idProof = user_data.files['idProof']
        if idProof.filename == '':
            return {"error": "No ID Proof selected"}, 400
        idProoffilename = idProof.filename
        idProof_file_path = os.path.join(IDPROOF_UPLOAD_FOLDER, idProoffilename)
        idProof.save(idProof_file_path)
        
        addressProof = user_data.files['addressProof']
        if addressProof.filename == '':
            return {"error": "No Address Proof selected"}, 400
        addressProoffilename = addressProof.filename
        addressProof_file_path = os.path.join(ADDRESSPROOF_UPLOAD_FOLDER, addressProoffilename)
        addressProof.save(addressProof_file_path)

        # Check if user already exists
        alreadyExists = userCollection.find_one({'email': userFormData['email']})
        if alreadyExists:
            return {"message": "User already exists","success":False}, 400
        
        # Prepare the user data for insertion
        finalUserData = {
            "name": userFormData["name"],
            "email": userFormData["email"],
            "phone": userFormData["phone"],
            "gender": userFormData["gender"],
            "dateOfBirth": userFormData["dateOfBirth"],
            "occupation": userFormData["occupation"],
            "country": userFormData["country"],
            "idProofType": userFormData["idProofType"],
            "idProofPath": idProoffilename,
            "addressProofType": userFormData["addressProofType"],
            "addressProofPath": addressProoffilename,
            "password": userFormData["password"],
            "photographPath": photographfilename,
            "address1": None,
            "address2": None,
            "city": None,
            "state": None,
            "pincode": None,
            "verified": False,
            "kyc": False, 
        }        
        # Insert user data into the database
        result = userCollection.insert_one(finalUserData)
        
        # Prepare the response with the user ID as a string
        returnData = {
            "success": True,
            "message": "User added successfully",
            "uid": str(result.inserted_id),
            "data": finalUserData
        }
        return returnData, 201
    
    except Exception as e:
        print(e)
        return {"error": str(e)}, 500


def loginUser(email,password):
    if email is None or password is None:
        return {"message": "Missing email or password"}, 400

    user = userCollection.find_one({'email': email})
    if not user:
        return {"message": "User not found","success":False}, 404
    
    if user['password']!= password:
        return {"message": "Incorrect password","success":False}, 401
    
    user_data = {
        "success":True,
        "uid": str(user['_id']), 
        "Message": "Successfully Login!",
    }
    return user_data, 200

def verifyUser(id):
    try:
        object_id = ObjectId(id)
    except:
        return {"message": "Invalid user ID format"}, 400
    
    user = userCollection.find_one({'_id': object_id})
    if not user:
        return {"message": "User not found"}, 404
    user_data ={
        "uid": str(user['_id']),
        "Message": "User verified successfully",
        "success": True,
        "fullName": user['name']
    }
    return user_data, 200


def parseUser(id):
    try:
        object_id = ObjectId(id)
        user = userCollection.find_one({'_id': object_id})
        if not user:
            return {"message": "User not found"}, 404
        
        addressProof_file_path = "uploads/addressproofs/" + user['addressProofPath']
        idProof_file_path = "uploads/idproofs/" + user['idProofPath']
        

        user_data = {
            "uid": str(user['_id'])
        }

        # Open the files in binary mode
        with open(addressProof_file_path, 'rb') as address_proof_file, open(idProof_file_path, 'rb') as id_proof_file:
            files = {
                'file1': address_proof_file,
                'file2': id_proof_file
            }
            response = requests.post(JASWANTH_BACKEND_URL+'/api/fetchDetails', data=user_data, files=files)
            print(response.json())

        # Return the response from the API
        if response.ok:
            return response.json(), response.status_code
        else:
            return {"message": "Failed to send files"}, response.status_code

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "Invalid user ID format"}, 400


