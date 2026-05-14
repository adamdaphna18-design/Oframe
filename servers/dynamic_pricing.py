# servers/dynamic_pricing.py
import sqlite3
import time
from collections import deque
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "agent_economy.db"

# In‑memory demand tracking
request_history = deque(maxlen=100)  # (timestamp, stream)
min_bid = {
    "spectrum": 1,      # cents
    "robot": 1,
    "inference": 0.5,
    "trading": 2,
    "threat": 5
}

def update_pricing():
    """Recalculate min_bid based on recent demand and reputation feedback."""
    global min_bid
    # Count requests in last 60 seconds
    now = time.time()
    recent = [ts for ts, _ in request_history if now - ts < 60]
    demand_factor = len(recent) / 10.0  # 10 req/min = baseline
    for stream in min_bid:
        # Base price + demand premium (capped at 5x)
        new_bid = min_bid[stream] * (1 + demand_factor * 0.2)
        min_bid[stream] = round(min(new_bid, min_bid[stream] * 5), 2)

@app.route('/price/<stream>', methods=['GET'])
def get_price(stream):
    agent_id = request.headers.get("X-Agent-Id")
    # optional: add reputation multiplier
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT reputation FROM agents WHERE agent_id = ?", (agent_id,))
        row = cur.fetchone()
        rep = row[0] if row else 50
    # lower reputation agents pay more (if reputation < 30, +50% penalty)
    multiplier = 1.0 + max(0, (50 - rep)) / 100.0
    final_price = min_bid.get(stream, 1) * multiplier
    return jsonify({"stream": stream, "min_bid_cents": round(final_price, 2), "reputation_multiplier": multiplier})

@app.route('/bid/<stream>', methods=['POST'])
def accept_bid(stream):
    """Endpoint called by revenue stream servers to validate a bid."""
    data = request.get_json()
    bid = data.get("bid_cents")
    agent_id = data.get("agent_id")
    if not bid or not agent_id:
        return jsonify({"error": "missing bid or agent_id"}), 400
    # get current price
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT reputation FROM agents WHERE agent_id = ?", (agent_id,))
        row = cur.fetchone()
        rep = row[0] if row else 50
    penalty = 1.0 + max(0, (50 - rep)) / 100.0
    required = min_bid.get(stream, 1) * penalty
    if bid >= required:
        return jsonify({"accepted": True, "required": required})
    else:
        return jsonify({"accepted": False, "required": required, "message": "bid too low"}), 402

@app.route('/report_demand', methods=['POST'])
def report_demand():
    data = request.get_json()
    stream = data.get("stream")
    if stream:
        request_history.append((time.time(), stream))
        update_pricing()
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011)
