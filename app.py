
from flask import Flask, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

try:
    client.admin.command("ping")
    print("MongoDB Connected Successfully!")
except Exception as e:
    print("MongoDB Connection Failed:", e)

db = client["RateLimiterDB"]
collection = db["clients"]

CAPACITY = 5
REFILL_RATE = 1

def allow_request(client_id):
    now = datetime.utcnow()

    data = collection.find_one({"clientId": client_id})

    if data is None:
        collection.insert_one({
            "clientId": client_id,
            "tokens": CAPACITY - 1,
            "lastRefill": now
        })
        return True

    elapsed = (now - data["lastRefill"]).total_seconds()

    new_tokens = min(
        CAPACITY,
        data["tokens"] + elapsed * REFILL_RATE
    )

    if new_tokens >= 1:
        collection.update_one(
            {"clientId": client_id},
            {
                "$set": {
                    "tokens": new_tokens - 1,
                    "lastRefill": now
                }
            }
        )
        return True

    collection.update_one(
        {"clientId": client_id},
        {
            "$set": {
                "tokens": new_tokens,
                "lastRefill": now
            }
        }
    )

    return False


@app.route("/request/<client_id>")
def request_api(client_id):

    if allow_request(client_id):
        return jsonify({
            "status": "allowed",
            "message": "Request accepted"
        }), 200

    return jsonify({
        "status": "blocked",
        "message": "Rate limit exceeded"
    }), 429


@app.route("/")
def home():
    return "Rate Limiter Running"


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
