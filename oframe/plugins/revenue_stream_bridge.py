try:
    from oframe.plugin_interface import OFramePlugin
except ImportError:
    class OFramePlugin:
        pass

class RevenueStreamBridge(OFramePlugin):
    @property
    def name(self):
        return "revenue_stream_bridge"

    def _call_stream(self, stream_type, payload):
        if stream_type == "spectrum":
            return {"frequencies": ["2.4GHz", "5GHz"]}
        return {"status": "unknown"}
