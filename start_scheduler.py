import threading
import time
import logging
import yaml
from oframe.scheduler.skill_graph import SkillGraph
from oframe.scheduler.adaptive_scheduler import AdaptiveScheduler
from oframe.scheduler.scheduler_api import create_scheduler_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from oframe.plugin_manager import PluginManager
except ImportError:
    class PluginManager:
        plugins = []

def start_scheduler():
    logger.info("Initializing complete scheduler system...")

    # Load configuration
    sg = SkillGraph()
    try:
        with open("schedules.yaml", "r") as f:
            data = yaml.safe_load(f)
            for name, skill_data in data.get("skills", {}).items():
                sg.add_skill(name, skill_data)
            for schedule_data in data.get("schedules", []):
                s_name = schedule_data.get("skill")
                skill = sg.get_skill(s_name)
                if skill:
                    for k, v in schedule_data.items():
                        if k != "skill":
                            skill.data[k] = v
    except FileNotFoundError:
        logger.warning("schedules.yaml not found, starting with empty graph.")

    # Instantiate scheduler
    pm = PluginManager()
    scheduler = AdaptiveScheduler(sg, pm)

    # Start API server in a separate thread
    app = create_scheduler_api(scheduler)
    if app:
        logger.info("Starting scheduler API on port 5014...")
        api_thread = threading.Thread(target=lambda: app.run(port=5014, use_reloader=False, host='0.0.0.0'), daemon=True)
        api_thread.start()

    # Start main scheduler loop
    logger.info("Starting adaptive scheduler loop...")
    scheduler.start()

if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler shutdown requested.")
