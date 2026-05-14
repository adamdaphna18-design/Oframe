# oframe/servers/reputation_queue.py
import sqlite3, json, time
from contextlib import contextmanager
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "agent_economy.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY, reputation INTEGER DEFAULT 50, tasks_completed INTEGER DEFAULT 0, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS task_queue (id INTEGER PRIMARY KEY, task_type TEXT, payload TEXT, status TEXT DEFAULT 'pending', assigned_agent TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP, result TEXT, retries INTEGER DEFAULT 0)")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

@app.route('/reputation/<agent_id>', methods=['GET'])
def get_reputation(agent_id):
    with get_db() as conn:
        row = conn.execute("SELECT reputation, tasks_completed FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
        if row: return jsonify({"agent_id": agent_id, "reputation": row["reputation"], "tasks_completed": row["tasks_completed"]})
        return jsonify({"agent_id": agent_id, "reputation": 50, "tasks_completed": 0})

@app.route('/reputation/<agent_id>/update', methods=['POST'])
def update_reputation(agent_id):
    data = request.get_json()
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO agents (agent_id) VALUES (?)", (agent_id,))
        if data.get("task_success"):
            conn.execute("UPDATE agents SET reputation = reputation + 1, tasks_completed = tasks_completed + 1, last_seen = CURRENT_TIMESTAMP WHERE agent_id = ?", (agent_id,))
        else:
            conn.execute("UPDATE agents SET reputation = reputation - 2, last_seen = CURRENT_TIMESTAMP WHERE agent_id = ?", (agent_id,))
        conn.execute("UPDATE agents SET reputation = MAX(0, MIN(100, reputation)) WHERE agent_id = ?", (agent_id,))
        conn.commit()
        new_rep = conn.execute("SELECT reputation FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()["reputation"]
    return jsonify({"new_reputation": new_rep})

@app.route('/task', methods=['POST'])
def enqueue_task():
    data = request.get_json()
    with get_db() as conn:
        cur = conn.execute("INSERT INTO task_queue (task_type, payload) VALUES (?, ?)", (data.get("task_type"), json.dumps(data.get("payload", {}))))
        conn.commit()
        return jsonify({"task_id": cur.lastrowid})

@app.route('/task/next', methods=['GET'])
def dequeue_task():
    agent_id = request.headers.get("X-Agent-Id")
    if not agent_id: return jsonify({"error": "missing X-Agent-Id"}), 400
    with get_db() as conn:
        row = conn.execute("SELECT id, task_type, payload FROM task_queue WHERE status = 'pending' ORDER BY created_at LIMIT 1").fetchone()
        if not row: return jsonify({"task": None})
        conn.execute("UPDATE task_queue SET status = 'processing', assigned_agent = ?, started_at = CURRENT_TIMESTAMP WHERE id = ?", (agent_id, row["id"]))
        conn.commit()
        return jsonify({"task_id": row["id"], "task_type": row["task_type"], "payload": json.loads(row["payload"])})

@app.route('/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    agent_id = request.headers.get("X-Agent-Id")
    with get_db() as conn:
        conn.execute("UPDATE task_queue SET status = 'done', completed_at = CURRENT_TIMESTAMP, result = ? WHERE id = ? AND assigned_agent = ?", (json.dumps(request.json.get("result", {})), task_id, agent_id))
        conn.commit()
    return jsonify({"status": "completed"})

@app.route('/task/<int:task_id>/fail', methods=['POST'])
def fail_task(task_id):
    agent_id = request.headers.get("X-Agent-Id")
    with get_db() as conn:
        conn.execute("UPDATE task_queue SET retries = retries + 1, status = 'pending', assigned_agent = NULL, started_at = NULL WHERE id = ? AND assigned_agent = ?", (task_id, agent_id))
        conn.commit()
    return jsonify({"status": "requeued"})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5010)