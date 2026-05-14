import time
import random
import threading
import logging
from collections import defaultdict
from datetime import datetime
from croniter import croniter

from .skill_graph import SkillGraph
from .rl_optimizer import TimedBandit
from .cooperative_vote import CooperativeSlotAllocator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

        # Track runtime constraints
        self.hourly_runs = defaultdict(int)
        self.last_hour = datetime.now().hour

    def start(self):
        self.running = True
        logger.info("AdaptiveScheduler started.")
        while self.running:
            now = datetime.now()
            if now.hour != self.last_hour:
                self.hourly_runs.clear()
                self.last_hour = now.hour

            for skill in self.graph.skills:
                if self._should_run(skill, now):
                    self._run_skill(skill, now)
            time.sleep(60)

    def _evaluate_condition(self, condition_str):
        if not condition_str:
            return True
        # For security, a real system would parse the expression safely.
        # As a mock, we use a very restricted environment or just return True.
        # The prompt says: "add a check_condition(condition_str) method that can evaluate simple expressions (e.g. via eval with safe globals or calling external API)"
        safe_globals = {
            "market_volatility": 0.6,
            "gas_price": 15
        }
        try:
            return eval(condition_str, {"__builtins__": None}, safe_globals)
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition_str}': {e}")
            return False

    def trigger_event(self, event_name, payload=None):
        logger.info(f"Received event: {event_name}")
        now = datetime.now()
        for skill in self.graph.skills:
            if skill.get("trigger") == "on_event" and skill.get("event") == event_name:
                condition = skill.get("condition")
                if not condition or self._evaluate_condition(condition):
                    logger.info(f"Triggering skill {skill.name} from event {event_name}")
                    self._run_skill(skill, now)

    def _should_run(self, skill, now):
        # Only evaluate non-event triggers in the main loop
        trigger = skill.get("trigger")
        if trigger == "on_event":
            return False

        stats = self.graph.stats(skill.name)

        # 1. Check max runs per hour
        max_runs = skill.get("max_runs_per_hour", float('inf'))
        if self.hourly_runs[skill.name] >= max_runs:
            return False

        # 2. Check cooldown
        last_run = stats.get("last_run")
        if last_run:
            cooldown = skill.get("cooldown", 0)
            if (now - last_run).total_seconds() < cooldown:
                return False

        # 3. Check Condition
        condition = skill.get("condition")
        if condition and not self._evaluate_condition(condition):
            return False

        # 4. Trigger logic
        if trigger == "probabilistic":
            prob = skill.get("probability", 0.3)
            return random.random() <= prob

        elif trigger == "cron":
            cron_expr = skill.get("cron")
            if cron_expr:
                # We want to check if it's supposed to run in this minute
                # We compare the previous minute's next run with now
                try:
                    minute_ago = now.timestamp() - 60
                    cron = croniter(cron_expr, minute_ago)
                    next_run = cron.get_next()
                    if next_run <= now.timestamp():
                        return True
                except Exception as e:
                    logger.error(f"Invalid cron expression for {skill.name}: {e}")
            return False

        elif trigger == "interval":
            interval = skill.get("interval", 3600)
            if not last_run:
                return True
            return (now - last_run).total_seconds() >= interval

        else:
            # Fallback to bandit
            bandit = self.bandits[skill.name]
            suggested_hour = bandit.select_hour()
            if now.hour == suggested_hour:
                return True

        return False

    def _run_skill(self, skill, now):
        logger.info(f"Attempting to run skill: {skill.name}")
        # resolve dependencies first
        for dep_name in skill.dependencies:
            if not self.graph.is_satisfied(dep_name):
                dep_skill = self.graph.get_skill(dep_name)
                if dep_skill:
                    logger.info(f"Running dependency {dep_name} for {skill.name}")
                    success = self._run_skill(dep_skill, now)
                    if not success:
                        logger.warning(f"Dependency {dep_name} failed. Cannot run {skill.name}")
                        return False
                else:
                    logger.warning(f"Dependency {dep_name} not found.")
                    return False

        # execute via plugin
        handler = skill.get("handler")
        success = False
        if handler:
            try:
                plugin_name, method = handler.split(":")
                plugin = next((p for p in self.pm.plugins if p.name == plugin_name), None)
                if plugin and hasattr(plugin, method):
                    result = getattr(plugin, method)(skill.payload)
                    success = result.get("success", False)
                else:
                    logger.error(f"Handler {handler} not found.")
            except Exception as e:
                logger.error(f"Error running skill {skill.name}: {e}")
        else:
            # Mock success if no handler
            success = True

        self.graph.record_outcome(skill.name, success)
        self.bandits[skill.name].update(now.hour, success)
        self.hourly_runs[skill.name] += 1

        status_msg = "Succeeded" if success else "Failed"
        logger.info(f"Skill {skill.name} {status_msg}")
        return success

if __name__ == "__main__":
    import yaml
    logger.info("Starting standalone AdaptiveScheduler testing...")

    class DummyPluginManager(PluginManager):
        plugins = []

    sg = SkillGraph()
    try:
        with open("schedules.yaml", "r") as f:
            data = yaml.safe_load(f)
            for name, skill_data in data.get("skills", {}).items():
                sg.add_skill(name, skill_data)
            # Apply schedule specific config like max_runs, priority, cooldown back to skill data
            for schedule_data in data.get("schedules", []):
                s_name = schedule_data.get("skill")
                skill = sg.get_skill(s_name)
                if skill:
                    for k, v in schedule_data.items():
                        if k != "skill":
                            skill.data[k] = v
    except FileNotFoundError:
        logger.warning("schedules.yaml not found, starting with empty graph.")

    scheduler = AdaptiveScheduler(sg, DummyPluginManager())

    def run_loop():
        scheduler.start()

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.running = False
        logger.info("Scheduler stopped.")
