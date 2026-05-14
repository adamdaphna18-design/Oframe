#!/bin/bash
# create_scheduler.sh – Installs the novel skill-based scheduler into oframe

set -e  # exit on error

echo "🎨 Creating O-Frame Scheduler components..."

# Create directories
mkdir -p oframe/scheduler
mkdir -p oframe/plugins

# ----------------------------------------------------------------------
# 1. oframe/scheduler/__init__.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/__init__.py << 'EOF'
from .adaptive_scheduler import AdaptiveScheduler
from .skill_graph import SkillGraph
from .rl_optimizer import TimedBandit
from .cooperative_vote import CooperativeSlotAllocator

__all__ = ["AdaptiveScheduler", "SkillGraph", "TimedBandit", "CooperativeSlotAllocator"]
EOF

# ----------------------------------------------------------------------
# 2. oframe/scheduler/skill_graph.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/skill_graph.py << 'EOF'
from typing import Dict, List, Any, Optional
from collections import defaultdict

class SkillNode:
    def __init__(self, name: str, handler: str, dependencies: List[str] = None,
                 trigger: str = "interval", probability: float = 1.0,
                 event: Optional[str] = None, condition: str = ""):
        self.name = name
        self.handler = handler
        self.dependencies = dependencies or []
        self.trigger = trigger
        self.probability = probability
        self.event = event
        self.condition = condition
        self.stats = {"success": 0, "failure": 0, "last_run": None}

class SkillGraph:
    def __init__(self):
        self.skills: Dict[str, SkillNode] = {}
        self.dependency_graph = defaultdict(list)

    def add_skill(self, skill: SkillNode):
        self.skills[skill.name] = skill
        for dep in skill.dependencies:
            self.dependency_graph[dep].append(skill.name)

    def get_skill(self, name: str) -> Optional[SkillNode]:
        return self.skills.get(name)

    def is_satisfied(self, skill_name: str) -> bool:
        node = self.skills.get(skill_name)
        if not node:
            return True
        for dep in node.dependencies:
            if self.skills[dep].stats["last_run"] is None:
                return False
        return True

    def record_outcome(self, skill_name: str, success: bool):
        node = self.skills.get(skill_name)
        if node:
            if success:
                node.stats["success"] += 1
            else:
                node.stats["failure"] += 1
            node.stats["last_run"] = __import__("time").time()
EOF

# ----------------------------------------------------------------------
# 3. oframe/scheduler/rl_optimizer.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/rl_optimizer.py << 'EOF'
import random

class TimedBandit:
    def __init__(self):
        self.alpha = [1] * 24
        self.beta = [1] * 24

    def select_hour(self) -> int:
        samples = [random.betavariate(self.alpha[h], self.beta[h]) for h in range(24)]
        return samples.index(max(samples))

    def update(self, hour: int, success: bool):
        if success:
            self.alpha[hour] += 1
        else:
            self.beta[hour] += 1
EOF

# ----------------------------------------------------------------------
# 4. oframe/scheduler/cooperative_vote.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/cooperative_vote.py << 'EOF'
from typing import List, Tuple, Any

class CooperativeSlotAllocator:
    def allocate(self, skill_name: str, requests: List[Tuple[Any, float, float]]) -> Any:
        if not requests:
            return None
        weighted = [(rep * bid, agent) for agent, bid, rep in requests]
        return max(weighted, key=lambda x: x[0])[1]
EOF

# ----------------------------------------------------------------------
# 5. oframe/scheduler/adaptive_scheduler.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/adaptive_scheduler.py << 'EOF'
import time
import random
import yaml
from datetime import datetime
from pathlib import Path
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
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            print(f"Warning: config {self.config_path} not found")
            return
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
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

    def _should_run(self, skill_node: SkillNode, now: datetime) -> bool:
        if skill_node.trigger == "probabilistic":
            if random.random() > skill_node.probability:
                return False
        if skill_node.trigger not in ("on_event", "cron"):
            bandit = self.bandits.get(skill_node.name)
            if bandit:
                suggested_hour = bandit.select_hour()
                if now.hour != suggested_hour:
                    return False
        return True

    def _run_skill(self, skill_node: SkillNode):
        for dep_name in skill_node.dependencies:
            dep_node = self.graph.get_skill(dep_name)
            if dep_node and not self.graph.is_satisfied(dep_name):
                self._run_skill(dep_node)
        handler = skill_node.handler
        if handler and ":" in handler:
            plugin_name, method = handler.split(":")
            plugin = next((p for p in self.pm.plugins if p.name == plugin_name), None)
            if plugin and hasattr(plugin, method):
                result = getattr(plugin, method)({})
                success = result.get("success", False)
                self.graph.record_outcome(skill_node.name, success)
                self.bandits[skill_node.name].update(datetime.now().hour, success)

    def start(self):
        self.running = True
        print("AdaptiveScheduler started")
        while self.running:
            now = datetime.now()
            for skill_node in self.graph.skills.values():
                if self._should_run(skill_node, now):
                    self._run_skill(skill_node)
            time.sleep(60)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    scheduler = AdaptiveScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.stop()
EOF

# ----------------------------------------------------------------------
# 6. oframe/scheduler/scheduler_api.py
# ----------------------------------------------------------------------
cat > oframe/scheduler/scheduler_api.py << 'EOF'
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
EOF

# ----------------------------------------------------------------------
# 7. oframe/plugins/scheduler_bridge.py
# ----------------------------------------------------------------------
cat > oframe/plugins/scheduler_bridge.py << 'EOF'
import logging
from oframe.plugin_interface import OFramePlugin

logger = logging.getLogger(__name__)

class SchedulerBridge(OFramePlugin):
    @property
    def name(self) -> str:
        return "scheduler_bridge"

    def on_load(self, config):
        self.skills = {
            "spectrum_scan": self.spectrum_scan,
            "arbitrage_check": self.arbitrage_check,
            "threat_update": self.threat_update,
        }
        logger.info("SchedulerBridge loaded")

    def spectrum_scan(self, payload=None):
        try:
            from .revenue_stream_bridge import RevenueStreamBridge
            bridge = RevenueStreamBridge()
            result = bridge._call_stream("spectrum", payload or {})
            return {"success": "frequencies" in result, "data": result}
        except Exception as e:
            logger.error(f"Spectrum scan failed: {e}")
            return {"success": False, "error": str(e)}

    def arbitrage_check(self, payload=None):
        try:
            from .revenue_stream_bridge import RevenueStreamBridge
            bridge = RevenueStreamBridge()
            result = bridge._call_stream("trading", payload or {})
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def threat_update(self, payload=None):
        try:
            from .revenue_stream_bridge import RevenueStreamBridge
            bridge = RevenueStreamBridge()
            result = bridge._call_stream("threat", payload or {"ip": "8.8.8.8"})
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
EOF

# ----------------------------------------------------------------------
# 8. schedules.yaml (example)
# ----------------------------------------------------------------------
cat > schedules.yaml << 'EOF'
skills:
  spectrum_scan:
    handler: "scheduler_bridge:spectrum_scan"
    dependencies: []
    trigger: "probabilistic"
    probability: 0.5
  arbitrage_check:
    handler: "scheduler_bridge:arbitrage_check"
    dependencies: []
    trigger: "interval"
    condition: "market_volatility > 0.5"
  threat_update:
    handler: "scheduler_bridge:threat_update"
    dependencies: []
    trigger: "on_event"
    event: "new_threat_reported"

schedules:
  - skill: spectrum_scan
    priority: medium
    cooldown: 300
  - skill: arbitrage_check
    max_runs_per_hour: 10
EOF

# ----------------------------------------------------------------------
# 9. Update requirements.txt (append if not already present)
# ----------------------------------------------------------------------
echo "croniter" >> requirements.txt
echo "pyyaml" >> requirements.txt
echo "flask" >> requirements.txt
# remove duplicates (optional)
sort -u requirements.txt -o requirements.txt

echo ""
echo "✅ Scheduler installation complete!"
echo ""
echo "To run the scheduler:"
echo "  python -m oframe.scheduler.adaptive_scheduler"
echo ""
echo "To run the API server:"
echo "  python -m oframe.scheduler.scheduler_api"
echo ""
echo "Make sure Ollama and your revenue stream servers are running."
