import requests
from flask import Flask, request, jsonify
import time
import logging
from datetime import datetime
from threading import Lock

app = Flask(__name__)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration with optimal defaults
CONFIG = {
    'api_url': "https://auth.roblox.com/v1/usernames/validate",
    'min_delay': 1.5,  # More conservative default delay
    'max_attempts': 3,
    'timeout': 8,
    'user_agent': "RobloxUsernameChecker/1.0 (+https://github.com/username)"
}

# Thread-safe rate limiting
request_lock = Lock()
last_request_time = 0

def make_roblox_request(username):
    """Thread-safe request maker with precise rate limiting"""
    global last_request_time
    
    with request_lock:
        current_time = time.time()
        elapsed = current_time - last_request_time
        sleep_needed = max(0, CONFIG['min_delay'] - elapsed)
        
        if sleep_needed > 0:
            logger.debug(f"Rate limiting: Sleeping {sleep_needed:.3f}s")
            time.sleep(sleep_needed)
        
        try:
            response = requests.get(
                CONFIG['api_url'],
                params={
                    "request.username": username,
                    "request.birthday": "2000-01-01",
                    "request.context": "Signup"
                },
                headers={
                    "User-Agent": CONFIG['user_agent'],
                    "Accept": "application/json",
                },
                timeout=CONFIG['timeout']
            )
            
            last_request_time = time.time()
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {type(e).__name__}: {str(e)}")
            return None

@app.route('/check', methods=['GET'])
def check_username():
    start_time = time.time()
    username = request.args.get('username', '').strip()
    
    if not username or len(username) < 3 or len(username) > 20:
        logger.warning(f"Invalid username: '{username}'")
        return jsonify({
            "error": "Username must be 3-20 characters",
            "status": 400
        }), 400
    
    logger.info(f"Processing username: {username}")
    
    result = None
    for attempt in range(1, CONFIG['max_attempts'] + 1):
        result = make_roblox_request(username)
        
        if result is not None:
            status = "available" if result.get("code", 1) == 0 else "taken"
            logger.info(f"Success on attempt {attempt}: {username} -> {status}")
            break
            
        if attempt < CONFIG['max_attempts']:
            retry_delay = attempt * 1.5  # Linear backoff
            logger.info(f"Retry #{attempt} in {retry_delay}s...")
            time.sleep(retry_delay)
    
    processing_time = time.time() - start_time
    
    if result is None:
        logger.error(f"Failed after {CONFIG['max_attempts']} attempts")
        return jsonify({
            "username": username,
            "status": "error",
            "message": "Service unavailable",
            "attempts": CONFIG['max_attempts'],
            "time_sec": round(processing_time, 3)
        }), 503
    
    return jsonify({
        "username": username,
        "available": result.get("code", 1) == 0,
        "status": "available" if result.get("code", 1) == 0 else "taken",
        "message": result.get("message", ""),
        "code": result.get("code", -1),
        "attempts": attempt,
        "time_sec": round(processing_time, 3)
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "time": datetime.now().isoformat(),
        "config": {
            "min_delay": CONFIG['min_delay'],
            "max_attempts": CONFIG['max_attempts'],
            "timeout": CONFIG['timeout']
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
