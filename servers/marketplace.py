# servers/marketplace.py
import sqlite3
import json
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "agent_economy.db"

def init_marketplace():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_agent TEXT,
                strategy_text TEXT,
                price_cents INTEGER,
                success_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_agent TEXT,
                listing_id INTEGER,
                paid_cents INTEGER,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@app.route('/listings', methods=['GET'])
def list_listings():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT id, seller_agent, strategy_text, price_cents, success_count FROM listings ORDER BY success_count DESC")
        rows = cur.fetchall()
    return jsonify([{"id": r[0], "seller": r[1], "strategy": r[2], "price": r[3], "successes": r[4]} for r in rows])

@app.route('/list', methods=['POST'])
def create_listing():
    data = request.get_json()
    seller = data.get("seller_agent")
    strategy = data.get("strategy_text")
    price = data.get("price_cents", 1)
    if not seller or not strategy:
        return jsonify({"error": "missing seller or strategy"}), 400
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO listings (seller_agent, strategy_text, price_cents) VALUES (?, ?, ?)", (seller, strategy, price))
        listing_id = cur.lastrowid
        conn.commit()
    return jsonify({"listing_id": listing_id, "status": "active"})

@app.route('/buy/<int:listing_id>', methods=['POST'])
def buy_listing(listing_id):
    data = request.get_json()
    buyer = data.get("buyer_agent")
    # In mock mode, just accept. In real mode, verify payment via x402.
    with sqlite3.connect(DB_PATH) as conn:
        # get listing details
        cur = conn.execute("SELECT price_cents, strategy_text FROM listings WHERE id = ?", (listing_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "listing not found"}), 404
        price, strategy = row
        # record purchase
        conn.execute("INSERT INTO purchases (buyer_agent, listing_id, paid_cents) VALUES (?, ?, ?)", (buyer, listing_id, price))
        # increment success count (optional)
        conn.execute("UPDATE listings SET success_count = success_count + 1 WHERE id = ?", (listing_id,))
        conn.commit()
    # Return the strategy text so agent can use it
    return jsonify({"strategy": strategy, "paid_cents": price})

if __name__ == '__main__':
    init_marketplace()
    app.run(host='0.0.0.0', port=5012)
