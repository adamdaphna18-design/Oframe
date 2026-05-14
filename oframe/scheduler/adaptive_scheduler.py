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
