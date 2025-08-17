from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/check')
def check_username():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400
    
    try:
        # Check Roblox username availability
        response = requests.get(
            f"https://api.roblox.com/users/get-by-username?username={username}",
            timeout=5
        )
        data = response.json()
        available = data.get("error") or not data.get("Id")
        
        return jsonify({
            "username": username,
            "available": available,
            "robloxData": data
        })
    except Exception as e:
        return jsonify({
            "error": True,
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Critical change: Bind to 0.0.0.0 instead of 127.0.0.1
    app.run(host='0.0.0.0', port=5000)
