from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import socket
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

app = Flask(__name__)
CORS(app)

# Configure retry strategy with DNS cache
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

# Custom DNS resolver with caching
class DNSCachingAdapter(HTTPAdapter):
    def __init__(self):
        super().__init__()
        self.dns_cache = {}

    def resolve(self, hostname):
        if hostname not in self.dns_cache:
            try:
                self.dns_cache[hostname] = socket.gethostbyname(hostname)
            except socket.gaierror:
                return None
        return self.dns_cache[hostname]

    def send(self, request, **kwargs):
        resolved_ip = self.resolve(request.url.hostname)
        if resolved_ip:
            request.url = request.url.replace(
                f"//{request.url.hostname}",
                f"//{resolved_ip}"
            )
        return super().send(request, **kwargs)

# Configure session
session = requests.Session()
adapter = DNSCachingAdapter()
adapter.max_retries = retry_strategy
session.mount("https://", adapter)

@app.route('/check')
def check_username():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username required"}), 400

    try:
        headers = {
            "User-Agent": "Findify/1.0",
            "Accept": "application/json"
        }
        
        response = session.get(
            f"https://api.roblox.com/users/get-by-username?username={username}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 404:
            return jsonify({
                "username": username,
                "available": True,
                "status": "success"
            })
        
        response.raise_for_status()
        data = response.json()
        
        return jsonify({
            "username": username,
            "available": False,
            "status": "success",
            "robloxData": data
        })
        
    except Exception as e:
        return jsonify({
            "error": True,
            "message": "Service unavailable",
            "status": "error",
            "details": str(e)
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
