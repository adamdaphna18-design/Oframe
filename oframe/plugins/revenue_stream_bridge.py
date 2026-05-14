import json
import requests
import logging
from oframe.plugin_interface import OFramePlugin

logger = logging.getLogger(__name__)

class RevenueStreamBridge(OFramePlugin):
    @property
    def name(self) -> str:
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

    def on_golden_idea(self, idea: dict):
        question = idea.get("question", "").lower()
        if "spectrum" in question or "hackrf" in question:
            result = self._call_stream("spectrum", {})
            logger.info(f"📡 Executed spectrum broker: {result}")
        elif "click" in question or "automate" in question:
            result = self._call_stream("robot", {"action": "click", "selector": "#demo"})
            logger.info(f"🤖 Executed robot action: {result}")
        elif "inference" in question or "llm" in question:
            result = self._call_stream("inference", {"prompt": idea.get("answer", "")[:200]})
            logger.info(f"🧠 Ran inference: {result}")
        elif "arbitrage" in question or "trade" in question:
            result = self._call_stream("trading", {})
            logger.info(f"📈 Trading signal: {result}")
        elif "threat" in question or "intel" in question:
            result = self._call_stream("threat", {"ip": "8.8.8.8"})
            logger.info(f"🛡️ Threat intel: {result}")
        else:
            # Auto‑deploy using Ollama
            from oframe.core import ask_ollama
            prompt = f"Given this idea: '{question}', choose best stream: spectrum, robot, inference, trading, threat. Return only the stream name."
            stream = ask_ollama(prompt).strip().lower()
            if stream in self.servers:
                result = self._call_stream(stream, {"idea": question})
                logger.info(f"🤖 Auto‑deployed to {stream}: {result}")

    def get_matched_answer(self, question: str) -> str | None:
        if "spectrum" in question.lower():
            return "I can fetch a spectrum report for you (I've done this before)."
        return None
