from flask import Flask, request, jsonify # type: ignore
from flask_cors import cross_origin,CORS # type: ignore


from contollers.auth.Authentication import addUser,loginUser,verifyUser,parseUserData,addHomeBranch,getBanks,globalWallet,homeDelivery,getWallet,returnMoney,doKYC,transactionHistory

app = Flask(__name__)
CORS(app)

@app.route('/',methods=['GET'])
def home():
    return "<H1>PayTrue Server API - Homepage</H1>"

'''
    USER AUTHENTICATION & VERIFICATION
'''
@app.route('/api/register', methods=['POST'])
def add_user_route():
    try:
        response, status_code = addUser(request)
        if "uid" in response:
            response["uid"] = str(response["uid"])
        if "data" in response and "_id" in response["data"]:
            response["data"]["_id"] = str(response["data"]["_id"])
    
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    
    return jsonify(response), status_code

@app.route('/api/login', methods=['POST'])
def login_route():
    user_data = request.json
    try:
        response, status_code = loginUser(user_data['email'], user_data['password'])
        return jsonify(response), status_code
    except Exception as e:
        response = {"message": str(e),"success":False}
        return jsonify(response), 400
        
@app.route('/api/verify', methods=['GET'])
def verify_route():
    id = request.args.get('uid')
    try:
        response, status_code = verifyUser(id)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/parseaddress', methods=['GET'])
def parse_address():
    id = request.args.get('uid')
    try:
        response, status_code = parseUserData(id)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/addhomebranch', methods=['POST'])
def add_home_branch():
    try:
        response, status_code = addHomeBranch(request)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/getbanks', methods=['GET'])
def get_banks():
    uid = request.args.get('uid')
    try:
        response, status_code = getBanks(uid)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code


@app.route('/api/globalwallet', methods=['GET'])
def global_wallet():
    try:
        response, status_code = globalWallet()
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/getwallet', methods=['GET'])
def get_wallet():
    uid = request.args.get('uid')
    try:
        response, status_code = getWallet(uid)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code


@app.route('/api/homedelivery', methods=['POST'])
def home_delivery():
    try:
        response, status_code = homeDelivery(request)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/returnmoney', methods=['POST'])
def return_money():
    try:
        response, status_code = returnMoney(request)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code


@app.route('/api/getkyccode', methods=['GET'])
def kyc():
    try:
        response, status_code = doKYC(request)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code

@app.route('/api/transactionhistory', methods=['GET'])
def transaction_history():
    uid = request.args.get('uid')
    try:
        response, status_code = transactionHistory(uid)
    except Exception as e:
        response = {"error": str(e)}
        status_code = 500
    return jsonify(response), status_code



if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=8080)