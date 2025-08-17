from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Rate limiting and error handling
@app.before_request
def limit_requests():
    time.sleep(0.5)  # Add delay to prevent rate limiting

@app.route('/check')
def check_username():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400
    
    try:
        # Make request to Roblox API with proper headers
        headers = {
            "User-Agent": "Findify/1.0 (+https://findify-psef.onrender.com)"
        }
        
        response = requests.get(
            f"https://api.roblox.com/users/get-by-username?username={username}",
            headers=headers,
            timeout=5
        )
        
        # Handle different response scenarios
        if response.status_code == 404:
            return jsonify({
                "username": username,
                "available": True,
                "status": "success"
            })
        
        response.raise_for_status()  # Raises exception for 4XX/5XX
        
        data = response.json()
        
        return jsonify({
            "username": username,
            "available": False,
            "status": "success",
            "robloxData": data
        })
        
    except requests.exceptions.RequestException as e:
        # Detailed error logging
        error_msg = f"Roblox API error: {str(e)}"
        if hasattr(e, 'response') and e.response:
            error_msg += f" | Status: {e.response.status_code}"
        print(error_msg)
        
        return jsonify({
            "error": True,
            "message": "Failed to check username",
            "status": "error",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
