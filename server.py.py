import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # enable CORS so browser can call this API

@app.route("/check", methods=["GET"])
def check_username():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"ok": False, "message": "Missing ?username"}), 400

    url = "https://auth.roblox.com/v1/usernames/validate"
    params = {
        "request.username": username,
        "request.birthday": "2000-01-01",
        "request.context": "Signup"
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        available = data.get("code") == 0
        return jsonify({"ok": True, "available": available, "roblox": data})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
