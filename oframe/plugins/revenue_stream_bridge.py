# oframe/plugins/revenue_stream_bridge.py
import requests
import logging
from oframe.plugin_interface import OFramePlugin

logger = logging.getLogger(__name__)

class RevenueStreamBridge(OFramePlugin):
    @property
    def name(self):
        return "revenue_stream_bridge"

    def on_load(self, config):
        self.servers = {
            "spectrum": "http://localhost:5001/spectrum",
            "robot": "http://localhost:5002/execute",
            "inference": "http://localhost:5003/infer",
            "trading": "http://localhost:5004/signal",
            "threat": "http://localhost:5005/intel"
        }
        self.agent_id = config.get("agent_id", "oframe_agent")

    def _call_stream(self, stream_name: str, payload: dict) -> dict:
        if stream_name not in self.servers:
            return {"error": f"Unknown stream: {stream_name}"}
        payload["payment_id"] = f"{self.agent_id}_{stream_name}"
        try:
            resp = requests.post(self.servers[stream_name], json=payload, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def spectrum_scan(self, payload=None):
        return self._call_stream("spectrum", payload or {})

    def arbitrage_check(self, payload=None):
        return self._call_stream("trading", payload or {})

    def threat_update(self, payload=None):
        return self._call_stream("threat", payload or {"ip": "8.8.8.8"})
