# servers/failure_recovery.py
import sqlite3
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)
DB_PATH = "agent_economy.db"
TASK_QUEUE_API = "http://localhost:5010"  # reputation_queue server

def recover_stuck_tasks():
    """Find tasks in 'processing' for > 30 seconds and reset to pending."""
    with sqlite3.connect(DB_PATH) as conn:
        now = time.time()
        stuck = conn.execute("""
            SELECT id, assigned_agent, started_at
            FROM task_queue
            WHERE status = 'processing' AND (strftime('%s', 'now') - strftime('%s', started_at)) > 30
        """).fetchall()
        for task_id, agent_id, started_at in stuck:
            logging.info(f"Recovering stuck task {task_id} (agent {agent_id})")
            conn.execute("UPDATE task_queue SET status = 'pending', assigned_agent = NULL, started_at = NULL, retries = retries + 1 WHERE id = ?", (task_id,))
            conn.commit()
            # Optionally penalize the agent
            requests.post(f"{TASK_QUEUE_API}/reputation/{agent_id}/update", json={"task_success": False})

def run_forever():
    logging.info("Failure Recovery Swarm started")
    while True:
        recover_stuck_tasks()
        time.sleep(15)

if __name__ == '__main__':
    run_forever()
