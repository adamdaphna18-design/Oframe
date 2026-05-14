# oframe/servers/failure_recovery.py
import sqlite3, time, logging, requests

logging.basicConfig(level=logging.INFO)
DB_PATH = "agent_economy.db"
REPUTATION_API = "http://localhost:5010"

def recover():
    with sqlite3.connect(DB_PATH) as conn:
        stuck = conn.execute("SELECT id, assigned_agent FROM task_queue WHERE status = 'processing' AND (strftime('%s','now') - strftime('%s',started_at)) > 30").fetchall()
        for task_id, agent_id in stuck:
            logging.info(f"Recovering task {task_id} from agent {agent_id}")
            conn.execute("UPDATE task_queue SET status = 'pending', assigned_agent = NULL, started_at = NULL, retries = retries + 1 WHERE id = ?", (task_id,))
            conn.commit()
            # penalize agent
            try:
                requests.post(f"{REPUTATION_API}/reputation/{agent_id}/update", json={"task_success": False})
            except: pass

if __name__ == '__main__':
    logging.info("Failure recovery daemon started")
    while True:
        recover()
        time.sleep(15)