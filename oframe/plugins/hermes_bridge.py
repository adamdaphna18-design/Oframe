try:
    from oframe.plugin_interface import OFramePlugin
except ImportError:
    class OFramePlugin:
        pass

import requests
import logging

logger = logging.getLogger(__name__)

class HermesBridge(OFramePlugin):
    @property
    def name(self):
        return "hermes_bridge"

    def on_golden_idea(self, idea, score):
        if score > 70:
            logger.info(f"Emitting golden_idea event for idea with score {score}")
            try:
                requests.post(
                    "http://localhost:5014/event",
                    json={"event": "golden_idea", "data": {"idea": idea, "score": score}},
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to emit golden_idea event: {e}")
