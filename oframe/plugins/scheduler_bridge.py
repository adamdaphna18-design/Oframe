# oframe/plugins/scheduler_bridge.py
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
        # delegate to revenue_stream_bridge if available
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
