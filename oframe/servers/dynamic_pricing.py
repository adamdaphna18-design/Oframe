# oframe/servers/dynamic_pricing.py
import sqlite3, time
from collections import deque
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "agent_economy.db"
request_history = deque(maxlen=100)
min_bid = {"spectrum":1, "robot":1, "inference":0.5, "trading":2, "threat":5}

def update_pricing():
    now = time.time()
    recent = [ts for ts, _ in request_history if now-ts < 60]
    demand_factor = len(recent) / 10.0
    for stream in min_bid:
        new = min_bid[stream] * (1 + demand_factor*0.2)
        min_bid[stream] = round(min(new, min_bid[stream]*5), 2)

@app.route('/price/<stream>', methods=['GET'])
def get_price(stream):
    agent_id = request.headers.get("X-Agent-Id")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT reputation FROM agents WHERE agent_id = ?", (agent_id,))
        rep = cur.fetchone()[0] if cur.fetchone() else 50
    multiplier = 1.0 + max(0, (50-rep))/100.0
    return jsonify({"min_bid_cents": round(min_bid.get(stream,1)*multiplier,2)})

@app.route('/bid/<stream>', methods=['POST'])
def accept_bid(stream):
    data = request.json
    bid, agent_id = data.get("bid_cents"), data.get("agent_id")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT reputation FROM agents WHERE agent_id = ?", (agent_id,))
        rep = cur.fetchone()[0] if cur.fetchone() else 50
    required = min_bid.get(stream,1) * (1.0 + max(0, (50-rep))/100.0)
    if bid >= required:
        return jsonify({"accepted": True})
    else:
        return jsonify({"accepted": False, "required": required}), 402

@app.route('/report_demand', methods=['POST'])
def report_demand():
    stream = request.json.get("stream")
    if stream:
        request_history.append((time.time(), stream))
        update_pricing()
    return jsonify({"status":"ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011)