try:
    from flask import Flask, jsonify, request
except ImportError:
    Flask = None

def create_scheduler_api(scheduler):
    if not Flask:
        return None

    app = Flask(__name__)

    @app.route('/schedules', methods=['GET'])
    def get_schedules():
        skills_info = []
        for skill in scheduler.graph.skills:
            st = scheduler.graph.stats(skill.name)
            skills_info.append({
                "name": skill.name,
                "dependencies": skill.dependencies,
                "stats": st
            })
        return jsonify({"skills": skills_info})

    @app.route('/stats/<skill_name>', methods=['GET'])
    def get_skill_stats(skill_name):
        st = scheduler.graph.stats(skill_name)
        if st:
            return jsonify(st)
        return jsonify({"error": "Skill not found"}), 404

    @app.route('/vote', methods=['POST'])
    def vote_for_slot():
        data = request.json
        skill_name = data.get("skill")
        requested_slots = data.get("slots", [])
        winner = scheduler.allocator.allocate(skill_name, requested_slots)
        return jsonify({"winner": winner})

    @app.route('/event', methods=['POST'])
    def trigger_event():
        data = request.json
        if not data or "event" not in data:
            return jsonify({"error": "Missing event name"}), 400

        event_name = data["event"]
        payload = data.get("data", {})

        # Trigger the event asynchronously so we don't block the API response
        import threading
        t = threading.Thread(target=scheduler.trigger_event, args=(event_name, payload), daemon=True)
        t.start()

        return jsonify({"status": "Event triggered", "event": event_name})

    return app

if __name__ == "__main__":
    # Test API
    from .skill_graph import SkillGraph
    from .adaptive_scheduler import AdaptiveScheduler
    class MockPM:
        plugins = []

    sg = SkillGraph()
    scheduler = AdaptiveScheduler(sg, MockPM())
    app = create_scheduler_api(scheduler)
    if app:
        app.run(port=5014)
