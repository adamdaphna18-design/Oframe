from flask import Flask, jsonify, request
from .adaptive_scheduler import AdaptiveScheduler

app = Flask(__name__)
scheduler = None

def init_scheduler(config_path="schedules.yaml"):
    global scheduler
    scheduler = AdaptiveScheduler(config_path)
    return scheduler

@app.route('/schedules', methods=['GET'])
def list_schedules():
    if not scheduler:
        return jsonify({"error": "scheduler not initialized"}), 500
    skills = {name: vars(node) for name, node in scheduler.graph.skills.items()}
    return jsonify(skills)

@app.route('/schedules/run/<skill_name>', methods=['POST'])
def run_skill(skill_name):
    if not scheduler:
        return jsonify({"error": "scheduler not initialized"}), 500
    node = scheduler.graph.get_skill(skill_name)
    if not node:
        return jsonify({"error": "skill not found"}), 404
    scheduler._run_skill(node)
    return jsonify({"status": "triggered", "skill": skill_name})

@app.route('/schedules/stats', methods=['GET'])
def get_stats():
    if not scheduler:
        return jsonify({"error": "scheduler not initialized"}), 500
    stats = {name: node.stats for name, node in scheduler.graph.skills.items()}
    return jsonify(stats)

if __name__ == '__main__':
    init_scheduler()
    app.run(host='0.0.0.0', port=5014)
