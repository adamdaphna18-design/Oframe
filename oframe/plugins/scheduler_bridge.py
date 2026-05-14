try:
    from oframe.plugin_interface import OFramePlugin
except ImportError:
    # Fallback mock for isolated environments
    class OFramePlugin:
        pass

class SchedulerBridge(OFramePlugin):
    @property
    def name(self):
        return "scheduler_bridge"

    def on_load(self, config):
        self.skills = {
            "spectrum_scan": self.spectrum_scan,
            "arbitrage_check": self.arbitrage_check,
        }

    def spectrum_scan(self, payload):
        try:
            # call revenue_stream_bridge or directly
            from oframe.plugins.revenue_stream_bridge import RevenueStreamBridge
            bridge = RevenueStreamBridge()
            result = bridge._call_stream("spectrum", payload)
            return {"success": "frequencies" in result, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def arbitrage_check(self, payload):
        # mock arbitrage check
        return {"success": True, "data": {"status": "checked"}}
