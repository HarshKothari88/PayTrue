from flask import Flask, request, jsonify # type: ignore
from flask_cors import cross_origin,CORS # type: ignore


from contollers.auth.Authentication import addUser,loginUser,verifyUser

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
        if "userData" in response and "_id" in response["userData"]:
            response["userData"]["_id"] = str(response["userData"]["_id"])
    
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


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=8080)