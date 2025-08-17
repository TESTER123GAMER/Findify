import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import time
import random

app = Flask(__name__)

# Configuration
ROBLOX_API_URL = "https://auth.roblox.com/v1/usernames/validate"
DEFAULT_DELAY = 1.0  # seconds between requests
MAX_ATTEMPTS = 3
PROXIES = None  # Can be set to {'http': 'http://proxy:port', 'https': 'https://proxy:port'}

# Rate limiting
last_request_time = 0
request_count = 0
rate_limit_reset = 0

def check_username(username):
    global last_request_time, request_count, rate_limit_reset
    
    # Rate limiting
    current_time = time.time()
    if current_time < last_request_time + DEFAULT_DELAY:
        time.sleep(DEFAULT_DELAY - (current_time - last_request_time))
    
    # Prepare request
    params = {
        "request.username": username,
        "request.birthday": "2000-01-01",  # Default birthday
        "request.context": "Signup"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
    }
    
    # Make request with retries
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(
                ROBLOX_API_URL,
                params=params,
                headers=headers,
                proxies=PROXIES,
                timeout=10
            )
            
            # Update rate limiting tracking
            last_request_time = time.time()
            request_count += 1
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                return {
                    "username": username,
                    "available": data.get("code") == 0,
                    "status": "available" if data.get("code") == 0 else "taken",
                    "message": data.get("message", ""),
                    "code": data.get("code", -1)
                }
            elif response.status_code == 429:
                # Rate limited - implement exponential backoff
                retry_after = int(response.headers.get('Retry-After', 5))
                time.sleep(retry_after + random.uniform(0, 1))
                continue
            else:
                return {
                    "username": username,
                    "available": False,
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "code": -1
                }
                
        except requests.exceptions.RequestException as e:
            if attempt == MAX_ATTEMPTS - 1:
                return {
                    "username": username,
                    "available": False,
                    "status": "error",
                    "message": str(e),
                    "code": -1
                }
            time.sleep(1 + attempt)  # Exponential backoff
    
    return {
        "username": username,
        "available": False,
        "status": "error",
        "message": "Max attempts reached",
        "code": -1
    }

@app.route('/check', methods=['GET', 'POST'])
def check_username_endpoint():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
    else:
        username = request.args.get('username')
    
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400
    
    result = check_username(username)
    return jsonify(result)

@app.route('/batch-check', methods=['POST'])
def batch_check():
    data = request.get_json()
    if not data or 'usernames' not in data:
        return jsonify({"error": "List of usernames is required"}), 400
    
    results = []
    for username in data['usernames']:
        results.append(check_username(username))
        time.sleep(DEFAULT_DELAY)  # Respect rate limits
    
    return jsonify({"results": results})

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "last_request": datetime.fromtimestamp(last_request_time).isoformat() if last_request_time else None,
        "request_count": request_count,
        "rate_limit_reset": rate_limit_reset
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
