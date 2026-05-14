# oframe/scheduler/adaptive_scheduler.py
import time
import random
import yaml
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import croniter
from .skill_graph import SkillGraph, SkillNode
from .rl_optimizer import TimedBandit
from .cooperative_vote import CooperativeSlotAllocator
from oframe.plugin_manager import PluginManager

class AdaptiveScheduler:
    def __init__(self, config_path: str = "schedules.yaml", plugin_manager: PluginManager = None):
        self.config_path = Path(config_path)
        self.graph = SkillGraph()
        self.bandits = {}
        self.allocator = CooperativeSlotAllocator()
        self.pm = plugin_manager or PluginManager([Path.home() / ".oframe" / "plugins", Path("oframe/plugins")])
        self.pm.discover_and_load()
        self.running = False
        self.schedule_entries = []  # list of dicts with trigger details
        self._load_config()
        self._start_event_listener()

    def _load_config(self):
        if not self.config_path.exists():
            print(f"Warning: config {self.config_path} not found")
            return
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        # Load skills
        skills_data = data.get("skills", {})
        for name, cfg in skills_data.items():
            node = SkillNode(
                name=name,
                handler=cfg.get("handler", ""),
                dependencies=cfg.get("dependencies", []),
                trigger=cfg.get("trigger", "interval"),
                probability=cfg.get("probability", 1.0),
                event=cfg.get("event"),
                condition=cfg.get("condition", "")
            )
            self.graph.add_skill(node)
            self.bandits[name] = TimedBandit()
        # Load schedules
        for sched in data.get("schedules", []):
            skill_name = sched["skill"]
            node = self.graph.get_skill(skill_name)
            if not node:
                continue
            entry = {
                "skill": node,
                "trigger": sched.get("trigger", "interval"),
                "spec": sched.get("spec"),
                "seconds": sched.get("seconds"),
                "probability": sched.get("probability", 1.0),
                "event": sched.get("event"),
                "condition": sched.get("condition"),
                "priority": sched.get("priority", "medium"),
                "cooldown": sched.get("cooldown", 0),
                "max_runs_per_hour": sched.get("max_runs_per_hour", None),
                "last_run": 0,
                "runs_this_hour": 0,
                "cron": croniter.croniter(sched["spec"]) if sched.get("spec") else None
            }
            self.schedule_entries.append(entry)

    def _check_condition(self, condition_str: str) -> bool:
        """Evaluate simple condition (e.g., 'market_volatility > 0.5').
           Can be extended to call external APIs or use a safe eval context."""
        if not condition_str:
            return True
        # Very simple demo – you can replace with real logic
        try:
            # WARNING: eval is dangerous. Use a custom parser in production.
            # For demo only – we provide a safe context with no builtins.
            safe_dict = {"market_volatility": 0.6}  # mock value
            return eval(condition_str, {"__builtins__": {}}, safe_dict)
        except:
            return True

    def _should_run(self, entry: dict, now: datetime) -> bool:
        skill_node = entry["skill"]
        trigger = entry["trigger"]
        # Cooldown
        if entry["cooldown"] and (time.time() - entry["last_run"]) < entry["cooldown"]:
            return False
        # Max runs per hour
        if entry["max_runs_per_hour"] and entry["runs_this_hour"] >= entry["max_runs_per_hour"]:
            return False
        # Condition
        if not self._check_condition(entry.get("condition", "")):
            return False
        # Trigger specific
        if trigger == "cron":
            next_run = entry["cron"].get_next(datetime)
            return now >= next_run
        elif trigger == "interval":
            if entry["last_run"] == 0:
                return True
            return (time.time() - entry["last_run"]) >= entry["seconds"]
        elif trigger == "probabilistic":
            # bandit can override hour selection if enabled
            bandit = self.bandits.get(skill_node.name)
            if bandit and entry.get("bandit_optimized", False):
                suggested_hour = bandit.select_hour()
                if now.hour != suggested_hour:
                    return False
            return random.random() < entry["probability"]
        elif trigger == "on_event":
            # events handled separately; not triggered by time loop
            return False
        return False

    def _run_skill(self, skill_node: SkillNode):
        # Resolve dependencies recursively
        for dep_name in skill_node.dependencies:
            dep_node = self.graph.get_skill(dep_name)
            if dep_node and not self.graph.is_satisfied(dep_name):
                self._run_skill(dep_node)
        # Execute via plugin
        handler = skill_node.handler
        if handler and ":" in handler:
            plugin_name, method = handler.split(":")
            plugin = next((p for p in self.pm.plugins if p.name == plugin_name), None)
            if plugin and hasattr(plugin, method):
                result = getattr(plugin, method)({})
                success = result.get("success", False)
                self.graph.record_outcome(skill_node.name, success)
                # Update bandit only if probabilistic/bandit_optimized
                if skill_node.trigger == "probabilistic":
                    self.bandits[skill_node.name].update(datetime.now().hour, success)
                # Log
                print(f"[{datetime.now()}] Ran skill '{skill_node.name}' -> success={success}")
            else:
                print(f"⚠️ No handler found for {skill_node.name}")

    def _event_listener(self):
        """Simple HTTP endpoint listener for events (runs in separate thread)."""
        from flask import Flask, request, jsonify
        app = Flask(__name__)

        @app.route('/event', methods=['POST'])
        def receive_event():
            data = request.json
            event_name = data.get("event")
            if not event_name:
                return jsonify({"error": "missing event"}), 400
            # Find all schedule entries that listen to this event
            for entry in self.schedule_entries:
                if entry["trigger"] == "on_event" and entry.get("event") == event_name:
                    # Check filter if present
                    filter_str = entry.get("filter")
                    if filter_str:
                        # simple eval (unsafe) – replace with safe parsing
                        if not eval(filter_str, {"__builtins__": {}}, data):
                            continue
                    # Run the skill in a separate thread to avoid blocking
                    threading.Thread(target=self._run_skill, args=(entry["skill"],)).start()
            return jsonify({"status": "event processed"})

        app.run(host='0.0.0.0', port=5015, debug=False, use_reloader=False)

    def _start_event_listener(self):
        t = threading.Thread(target=self._event_listener, daemon=True)
        t.start()
        print("Event listener started on port 5015")

    def start(self):
        self.running = True
        print("AdaptiveScheduler started")
        while self.running:
            now = datetime.now()
            # Reset hourly counters
            if now.minute == 0 and now.second == 0:
                for entry in self.schedule_entries:
                    entry["runs_this_hour"] = 0
            for entry in self.schedule_entries:
                if self._should_run(entry, now):
                    self._run_skill(entry["skill"])
                    entry["last_run"] = time.time()
                    entry["runs_this_hour"] += 1
            time.sleep(30)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    scheduler = AdaptiveScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.stop()
