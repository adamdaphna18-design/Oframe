import time
import random
import threading
from collections import defaultdict
from datetime import datetime
from .skill_graph import SkillGraph
from .rl_optimizer import TimedBandit
from .cooperative_vote import CooperativeSlotAllocator

# Mocking missing modules based on the snippet provided.
# If they exist in a larger repo we wouldn't need this, but for now we avoid ImportError.
try:
    from oframe.core import ask_ollama
except ImportError:
    def ask_ollama(prompt):
        return {"response": "Mock response"}

try:
    from oframe.plugin_manager import PluginManager
except ImportError:
    class PluginManager:
        plugins = []

class AdaptiveScheduler:
    def __init__(self, skill_graph: SkillGraph, plugin_manager: PluginManager):
        self.graph = skill_graph
        self.pm = plugin_manager
        self.bandits = defaultdict(TimedBandit)
        self.allocator = CooperativeSlotAllocator()
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            now = datetime.now()
            for skill in self.graph.skills:
                if self._should_run(skill, now):
                    self._run_skill(skill, now)
            time.sleep(60)  # check every minute

    def _should_run(self, skill, now):
        stats = self.graph.stats(skill.name)
        if not stats:
            return True
        # probabilistic trigger
        if skill.get("trigger") == "probabilistic":
            prob = skill.get("probability", 0.3)
            if random.random() > prob:
                return False
        # check cooldown
        last_run = stats.get("last_run")
        if last_run:
            cooldown = skill.get("cooldown", 0)
            if (now - last_run).total_seconds() < cooldown:
                return False

        # bandit‑selected time
        bandit = self.bandits[skill.name]
        suggested_hour = bandit.select_hour()

        # ensure we don't run repeatedly in the same hour unless configured
        if now.hour == suggested_hour:
            # check if max runs per hour is respected
            # this is a basic implementation, we can just enforce a minimum cooldown if running
            return True
        return False

    def _run_skill(self, skill, now):
        # resolve dependencies first
        for dep_name in skill.dependencies:
            if not self.graph.is_satisfied(dep_name):
                dep_skill = self.graph.get_skill(dep_name)
                if dep_skill:
                    self._run_skill(dep_skill, now)
                # Check again if it's satisfied after attempting to run
                if not self.graph.is_satisfied(dep_name):
                    return False
        # execute via plugin
        handler = skill.get("handler")
        if handler:
            plugin_name, method = handler.split(":")
            plugin = next((p for p in self.pm.plugins if p.name == plugin_name), None)
            if plugin and hasattr(plugin, method):
                result = getattr(plugin, method)(skill.payload)
                success = result.get("success", False)
                self.graph.record_outcome(skill.name, success)
                # update bandit
                self.bandits[skill.name].update(now.hour, success)
                return success
        return False

if __name__ == "__main__":
    import yaml
    print("Starting AdaptiveScheduler...")
    # Basic standalone run block if run as a script
    class DummyPluginManager(PluginManager):
        plugins = []

    sg = SkillGraph()
    try:
        with open("schedules.yaml", "r") as f:
            data = yaml.safe_load(f)
            for name, skill_data in data.get("skills", {}).items():
                sg.add_skill(name, skill_data)
    except FileNotFoundError:
        print("schedules.yaml not found, starting with empty graph.")

    scheduler = AdaptiveScheduler(sg, DummyPluginManager())

    # Run loop in background or a limited number of iterations for test
    def run_loop():
        scheduler.start()

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.running = False
        print("Scheduler stopped.")
