from pymongo import MongoClient #type: ignore
from bson import ObjectId #type: ignore
from dotenv import load_dotenv #type: ignore
import os,requests #type: ignore
from datetime import datetime #type: ignore

load_dotenv()

JASWANTH_BACKEND_URL = os.getenv("JASWANTH_BACKEND")
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION_USERS")
mongo_collection_wallet = os.getenv("MONGO_COLLECTION_WALLETS")
MONGO_COLLECTION_GLOBALWALLETS = os.getenv("MONGO_COLLECTION_GLOBALWALLETS")
MONGO_COLLECTION_MONEYWITHDRAWLTRANSACTIONS = os.getenv("MONGO_COLLECTION_MONEYWITHDRAWLTRANSACTIONS")

client = MongoClient(mongo_uri)
db = client[mongo_db]
userCollection = db[mongo_collection]
walletCollection = db[mongo_collection_wallet]
globalWalletCollection = db[MONGO_COLLECTION_GLOBALWALLETS]
moneyWithdrawlTransactionsCollection = db[MONGO_COLLECTION_MONEYWITHDRAWLTRANSACTIONS]



PHOTOGRAPH_UPLOAD_FOLDER = 'uploads/photographs'
if not os.path.exists(PHOTOGRAPH_UPLOAD_FOLDER):
    os.makedirs(PHOTOGRAPH_UPLOAD_FOLDER)

IDPROOF_UPLOAD_FOLDER = 'uploads/idproofs'
if not os.path.exists(IDPROOF_UPLOAD_FOLDER):
    os.makedirs(IDPROOF_UPLOAD_FOLDER)

ADDRESSPROOF_UPLOAD_FOLDER = 'uploads/addressproofs'
if not os.path.exists(ADDRESSPROOF_UPLOAD_FOLDER):
    os.makedirs(ADDRESSPROOF_UPLOAD_FOLDER)


def get_exchange_rate(from_currency, to_currency):
    try:
        # Replace with your API key
        api_key = "b60a8af8d0f11331471da969"
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"

        # Make the API call
        response = requests.get(url)
        data = response.json()

        # Check if the response is successful
        if response.status_code == 200 and data.get("result") == "success":
            return data["conversion_rate"]
        else:
            raise ValueError(f"Failed to fetch exchange rate: {data.get('error-type', 'Unknown error')}")
    except Exception as e:
        print(f"Error fetching exchange rate: {str(e)}")
        # Fallback to a default exchange rate or raise an error
        raise ValueError("Could not retrieve exchange rate. Please try again later.")

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
            "verified": False,
            "kyc": False, 
            "homeBank":[],
            "balance": 0,
        }        


        # Insert user data into the database
        result = userCollection.insert_one(finalUserData)

        walletResult = walletCollection.insert_one({"uid": str(result.inserted_id), "balance": [{"amount": 0, "currency": "INR"}, {"amount": 0, "currency": "USD"}, {"amount": 0, "currency": "EUR"}, {"amount": 0, "currency": "GBP"}, {"amount": 0, "currency": "JPY"}, {"amount": 0, "currency": "CNY"}]})

        finalUserData['id'] = str(result.inserted_id)
        finalUserData['walletId'] = str(walletResult.inserted_id)
        
        # Prepare the response with the user ID as a string
        returnData = {
            "success": True,
            "message": "User added successfully",
            "data": finalUserData,
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


def parseUserData(id):
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
            FILE_UPLOAD_URL = JASWANTH_BACKEND_URL + "/api/fetchDetails"
            response = requests.post(FILE_UPLOAD_URL, data=user_data, files=files)

        # Check if the response is successful
        if response.ok:
            response_data = response.json()
            if response_data.get("status") == "success":
                # Extract the new address from the response
                new_address = response_data.get("details", {}).get("address")
                
                if new_address:
                    # Update the user's address in the database
                    userCollection.update_one(
                        {'_id': object_id},
                        {'$set': {'address': new_address,"verified":True}}
                    )
                    print(f"User address updated to: {new_address}")

                # Return the updated data
                return {
                    "message": "User data updated successfully",
                    "data": response_data
                }, 200
            else:
                return {
                    "message": "Verification failed",
                    "details": response_data.get("message", "Unknown error")
                }, 400
        else:
            return {"message": "Failed to send files"}, response.status_code

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "Invalid user ID format"}, 400


def addHomeBranch(data):
    try:
        user_data = data.json
        if not user_data:
            return {"message": "No data provided"}, 400
        
        required_fields = ["uid", "bankName", "accountNo", "accountHolderName"]
        missing_fields = [field for field in required_fields if field not in user_data]
        
        if missing_fields:
            return {"message": f"Missing required data: {', '.join(missing_fields)}"}, 400
        
        object_id = ObjectId(user_data['uid'])
        user = userCollection.find_one({'_id': object_id})
        if not user:
            return {"message": "User not found"}, 404
        
        homeBank = {
            "bankName": user_data['bankName'],
            "accountNo": user_data['accountNo'],
            "accountHolderName": user_data['accountHolderName'],
            "balance": 9000,
        }
        userCollection.update_one({'_id': object_id}, {'$push': {'homeBank': homeBank}})
        
        return {"message": "Home branch added successfully","success":True}, 200
    
    except Exception as e:
        print(e)
        return {"error": str(e),"success":False}, 500
    
def getBanks(uid):
    try:
        object_id = ObjectId(uid)
        user = userCollection.find_one({'_id': object_id})
        if not user:
            return {"message": "User not found"}, 400
        
        return {"data": user['homeBank'],"success":True}, 200
    
    except Exception as e:
        print(e)
        return {"error": str(e),"success":False}, 500


def globalWallet():
    try:
        count = globalWalletCollection.count_documents({})
        if count > 0:
            return {"message": "Global Wallet already exists","success":False}, 400
        else:
            globalWallet = globalWalletCollection.insert_one({"balance": [{"amount": 100000000000000, "currency": "INR"}, {"amount": 100000000000000, "currency": "USD"}, {"amount": 100000000000000, "currency": "EUR"}, {"amount": 100000000000000, "currency": "GBP"}, {"amount": 100000000000000, "currency": "JPY"}, {"amount": 100000000000000, "currency": "CNY"}]})
            return {"message": "Global Wallet created successfully","success":True}, 200
    except Exception as e:
        print(e)
        return {"error": str(e),"success":False}, 500

def homeDelivery(request):
    try:
        user_data = request.json
        if not user_data:
            print("No data provided")
            return {"message": "No data provided"}, 400

        required_fields = ["uid", "fromCurrency", "toCurrency", "amount", "toDigital"]
        missing_fields = [field for field in required_fields if field not in user_data]

        if missing_fields:
            print(f"Missing required data: {', '.join(missing_fields)}")
            return {"message": f"Missing required data: {', '.join(missing_fields)}"}, 400

        # Parse the input data
        uid = user_data["uid"]
        from_currency = user_data["fromCurrency"]
        to_currency = user_data["toCurrency"]
        amount = user_data["amount"]
        delivery_address = user_data.get("delivery", None)  # Optional parameter for delivery address
        to_digital = user_data["toDigital"]
        confirm = user_data.get("confirm", False)  # Optional parameter for confirmation

        if amount <= 0:
            print("Amount must be greater than 0")
            return {"message": "Amount must be greater than 0"}, 400

        object_id = ObjectId(uid)
        user = userCollection.find_one({'_id': object_id})
        if not user:
            print("User not found")
            return {"message": "User not found"}, 404

        wallet = walletCollection.find_one({'uid': str(user['_id'])})
        if not wallet:
            print("Wallet not found")
            return {"message": "Wallet not found"}, 404

        # Find the balance object for the fromCurrency
        from_currency_balance = next((b for b in wallet['balance'] if b['currency'] == from_currency), None)
        if not from_currency_balance:
            print(f"{from_currency} balance not found in wallet")
            return {"message": f"{from_currency} balance not found in wallet"}, 400

        # Check if there is sufficient balance
        if from_currency_balance['amount'] < amount:
            print(f"Insufficient balance in {from_currency}")
            return {"message": f"Insufficient balance in {from_currency}"}, 400

        # Fetch the exchange rate (mocked or from an external API)
        exchange_rate = get_exchange_rate(from_currency, to_currency)  # Assume this function exists
        to_amount = amount * exchange_rate

        # If `confirm` is False, return the exchange rate details without processing the transaction
        if not confirm:
            return {
                "data": {
                    "exchangeRate": exchange_rate,
                    "fromCurrency": from_currency,
                    "fromAmount": amount,
                    "toCurrency": to_currency,
                    "toAmount": round(to_amount, 2),
                    "delivery": delivery_address,
                    "toDigital": to_digital
                },
                "success": True
            }, 200

        # If `confirm` is True, proceed with the transaction
        # Deduct the amount from the user's wallet
        from_currency_balance['amount'] -= amount

        # Update the wallet with the new balance
        walletCollection.update_one(
            {'_id': wallet['_id']},
            {'$set': {'balance': wallet['balance']}}
        )

        # If the delivery is None, update the user's wallet with the converted amount
        if delivery_address is None:
            # Find or create the balance object for the toCurrency in the user's wallet
            to_currency_balance = next(
                (b for b in wallet['balance'] if b['currency'] == to_currency),
                None
            )
            if not to_currency_balance:
                to_currency_balance = {"currency": to_currency, "amount": 0}
                wallet['balance'].append(to_currency_balance)

            # Add the converted amount to the user's wallet's toCurrency balance
            to_currency_balance['amount'] += to_amount

            # Update the wallet with the new balance
            walletCollection.update_one(
                {'_id': wallet['_id']},
                {'$set': {'balance': wallet['balance']}}
            )

            # Log the transaction in the moneyWithdrawlTransactionsCollection
            transaction_id = moneyWithdrawlTransactionsCollection.insert_one({
                "uid": str(user['_id']),
                "fromCurrency": from_currency,
                "toCurrency": to_currency,
                "fromAmount": amount,
                "toAmount": round(to_amount, 2),
                "exchangeRate": exchange_rate,
                "delivery": delivery_address,
                "toDigital": to_digital,
                "message": f"{amount} {from_currency} converted to {round(to_amount, 2)} {to_currency} in user's wallet",
                "status": "success",
                "createdat": datetime.now(),
                "type": "homeDelivery",
                "delivered": True if delivery_address else False,
                "confirmed": True
            }).inserted_id

            return {
                "message": f"{amount} {from_currency} converted to {round(to_amount, 2)} {to_currency} in user's wallet",
                "transactionId": str(transaction_id),
                "success": True
            }, 200

        # If delivery is provided, proceed with updating the global wallet
        # Find the global wallet
        global_wallet = globalWalletCollection.find_one({})
        if not global_wallet:
            print("Global Wallet not found")
            return {"message": "Global Wallet not found"}, 500

        # Find the balance object for the fromCurrency in the global wallet
        global_from_currency_balance = next(
            (b for b in global_wallet['balance'] if b['currency'] == from_currency),
            None
        )
        
        if not global_from_currency_balance:
            print(f"{from_currency} balance not found in global wallet")
            return {"message": f"{from_currency} balance not found in global wallet"}, 500

        # Add the amount to the global wallet's corresponding fromCurrency balance
        global_from_currency_balance['amount'] += amount

        # Find the balance object for the toCurrency in the global wallet
        global_to_currency_balance = next(
            (b for b in global_wallet['balance'] if b['currency'] == to_currency),
            None
        )

        if not global_to_currency_balance:
            print(f"{to_currency} balance not found in global wallet")
            return {"message": f"{to_currency} balance not found in global wallet"}, 500

        # Subtract the converted amount from the global wallet's corresponding toCurrency balance
        if global_to_currency_balance['amount'] < to_amount:
            print(f"Insufficient balance in {to_currency} in global wallet")
            return {"message": f"Insufficient balance in {to_currency} in global wallet"}, 400

        global_to_currency_balance['amount'] -= to_amount

        # Update the global wallet with the new balances
        globalWalletCollection.update_one(
            {'_id': global_wallet['_id']},
            {'$set': {'balance': global_wallet['balance']}}
        )

        # Log the transaction in the moneyWithdrawlTransactionsCollection
        transaction_id = moneyWithdrawlTransactionsCollection.insert_one({
            "uid": str(user['_id']),
            "fromCurrency": from_currency,
            "toCurrency": to_currency,
            "fromAmount": amount,
            "toAmount": round(to_amount, 2),
            "exchangeRate": exchange_rate,
            "delivery": delivery_address,
            "toDigital": to_digital,
            "message": f"{amount} {from_currency} deducted successfully and converted to {round(to_amount, 2)} {to_currency}",
            "status": "success",
            "createdat": datetime.now(),
            "type": "homeDelivery",
            "delivered": True,
            "confirmed": True
        }).inserted_id

        return {
            "message": f"{amount} {from_currency} deducted successfully and added to the global wallet. {round(to_amount, 2)} {to_currency} deducted from the global wallet",
            "transactionId": str(transaction_id),
            "success": True
        }, 200

    except Exception as e:
        print(e)
        return {"error": str(e), "success": False}, 500


def getWallet(uid):
    try:
        wallet = walletCollection.find_one({'uid': uid})
        if not wallet:
            return {"message": "Wallet not found"}, 404
        
        return {"data": wallet["balance"],"success":True}, 200
    
    except Exception as e:
        print(e)
        return {"error": str(e),"success":False}, 500


def returnMoney(request):
    try:
        user_data = request.json
        if not user_data:
            return {"message": "No data provided"}, 400

        uid = user_data.get("uid")
        bank_name = user_data.get("bankName")
        currency = user_data.get("currency")

        if not uid or not bank_name or not currency:
            return {"message": "User ID, bank name, and currency are required"}, 400

        # Convert the UID to ObjectId and find the user
        object_id = ObjectId(uid)
        user = userCollection.find_one({'_id': object_id})
        if not user:
            return {"message": "User not found"}, 404

        # Find the user's wallet
        wallet = walletCollection.find_one({'uid': str(user['_id'])})
        if not wallet:
            return {"message": "Wallet not found"}, 404

        total_inr_amount = 0

        # Loop through each currency in the wallet and convert to INR if it matches the specified currency
        for balance_entry in wallet.get('balance', []):
            if balance_entry['currency'].upper() == currency.upper():
                amount = balance_entry['amount']

                # Fetch the exchange rate for conversion to INR (assume this function exists)
                exchange_rate = get_exchange_rate(currency, "INR")
                inr_amount = amount * exchange_rate

                # Add the converted INR amount to the total
                total_inr_amount += inr_amount

                # Set the converted currency's balance to zero in the wallet after conversion
                balance_entry['amount'] = 0

                break

        if total_inr_amount <= 0:
            return {"message": f"No convertible balance available for {currency}"}, 400

        # Find the user's bank account from homeBank using bank_name
        home_bank_accounts = user.get('homeBank', [])
        selected_bank = next((bank for bank in home_bank_accounts if bank['bankName'].lower() == bank_name.lower()), None)

        if not selected_bank:
            return {"message": f"Bank '{bank_name}' not found in user's home banks"}, 404

        # Update the bank balance with the converted amount
        selected_bank['balance'] += total_inr_amount

        # Update the user's bank information in the database
        userCollection.update_one(
            {'_id': object_id},
            {'$set': {'homeBank': home_bank_accounts}}
        )

        # Update the user's wallet balance in the database
        walletCollection.update_one(
            {'_id': wallet['_id']},
            {'$set': {'balance': wallet['balance']}}
        )

        return {
            "message": f"{currency} balance converted to INR and added to {bank_name}. Total INR added: {round(total_inr_amount, 2)}",
            "convertedAmount": round(total_inr_amount, 2),
            "success": True
        }, 200

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "An error occurred while processing the transaction", "error": str(e)}, 500


def doKYC(request):
    try:
        URL =  JASWANTH_BACKEND_URL + "/api/generate_code"
        response = requests.get(URL)
        if response.status_code!= 200:
            return {"message": "Failed to generate KYC code"}, 500
        code = response.json()['data']['verification_code']
        return {
            "success": True,
            "data":{
                "code": code
            }
        }, 200

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "An error occurred while updating KYC status", "error": str(e)}, 500



def transactionHistory(uid):
    try:
        # Fetch transactions for the given user ID
        transactions = moneyWithdrawlTransactionsCollection.find({'uid': uid})

        # Convert cursor to a list
        transactions_list = list(transactions)

        # Check if there are no transactions
        if not transactions_list:
            return {"message": "No transactions found"}, 404
        
        # Convert ObjectId fields to string
        for transaction in transactions_list:
            transaction['_id'] = str(transaction['_id'])  # Convert ObjectId to string
            # If there are other ObjectId fields, convert them as well
            # transaction['some_other_id'] = str(transaction['some_other_id'])

        return {"data": transactions_list, "success": True}, 200
    
    except Exception as e:
        print(e)
        return {"error": str(e), "success": False}, 500