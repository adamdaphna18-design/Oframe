# oframe/servers/marketplace.py
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "agent_economy.db"

def init():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY, seller_agent TEXT, strategy_text TEXT, price_cents INTEGER, success_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, buyer_agent TEXT, listing_id INTEGER, paid_cents INTEGER, purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

@app.route('/listings', methods=['GET'])
def list_listings():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT id, seller_agent, strategy_text, price_cents, success_count FROM listings ORDER BY success_count DESC").fetchall()
    return jsonify([{"id":r[0],"seller":r[1],"strategy":r[2],"price":r[3],"successes":r[4]} for r in rows])

@app.route('/list', methods=['POST'])
def create_listing():
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO listings (seller_agent, strategy_text, price_cents) VALUES (?,?,?)", (data["seller_agent"], data["strategy_text"], data.get("price_cents",1)))
        conn.commit()
        return jsonify({"listing_id": cur.lastrowid})

@app.route('/buy/<int:listing_id>', methods=['POST'])
def buy_listing(listing_id):
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT price_cents, strategy_text FROM listings WHERE id = ?", (listing_id,)).fetchone()
        if not row: return jsonify({"error":"not found"}),404
        price, strategy = row
        conn.execute("INSERT INTO purchases (buyer_agent, listing_id, paid_cents) VALUES (?,?,?)", (data["buyer_agent"], listing_id, price))
        conn.execute("UPDATE listings SET success_count = success_count + 1 WHERE id = ?", (listing_id,))
        conn.commit()
    return jsonify({"strategy": strategy})

if __name__ == '__main__':
    init()
    app.run(host='0.0.0.0', port=5012)