import requests
from flask import Flask, request, jsonify
import time
import logging
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ROBLOX_API_URL = "https://auth.roblox.com/v1/usernames/validate"
REQUEST_DELAY = 1.2  # seconds between requests to avoid rate limiting
MAX_ATTEMPTS = 3
TIMEOUT = 10  # seconds

# Rate limiting tracking
last_request_time = 0

def make_roblox_request(username):
    """Make request to Roblox API with proper rate limiting"""
    global last_request_time
    
    # Enforce rate limiting
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_DELAY:
        sleep_time = REQUEST_DELAY - elapsed
        logger.info(f"Rate limiting: Sleeping {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
    
    params = {
        "request.username": username,
        "request.birthday": "2000-01-01",
        "request.context": "Signup"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
    }
    
    last_request_time = time.time()
    
    try:
        response = requests.get(
            ROBLOX_API_URL,
            params=params,
            headers=headers,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {username}: {str(e)}")
        return None

@app.route('/check', methods=['GET'])
def check_username():
    username = request.args.get('username')
    
    if not username:
        logger.warning("Missing username parameter")
        return jsonify({"error": "Username parameter is required"}), 400
    
    logger.info(f"Checking username: {username}")
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = make_roblox_request(username)
        
        if result is not None:
            available = result.get("code", 1) == 0
            return jsonify({
                "username": username,
                "available": available,
                "status": "available" if available else "taken",
                "message": result.get("message", ""),
                "code": result.get("code", -1),
                "attempts": attempt
            })
        
        if attempt < MAX_ATTEMPTS:
            retry_delay = attempt * 2  # Exponential backoff
            logger.info(f"Retry {attempt} in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    logger.error(f"Max attempts reached for {username}")
    return jsonify({
        "username": username,
        "available": False,
        "status": "error",
        "message": "Max attempts reached",
        "code": -1
    }), 503

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.1"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
