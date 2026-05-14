#!/bin/bash
# restore_o_frame.sh - Recreates the full O‑Frame framework

set -e

echo "🔧 Recreating O‑Frame directory structure..."

# Create directories
mkdir -p bin oframe oframe/plugins templates tests ideas assets .github/workflows

# ---------- bin/ executables ----------
cat > bin/o << 'EOF2'
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from oframe.core import ask_ollama

if len(sys.argv) < 2:
    print("Usage: o ask <question>")
    sys.exit(1)
if sys.argv[1] == "ask":
    answer = ask_ollama(" ".join(sys.argv[2:]))
    print(answer)
else:
    print("Unknown command")
EOF2
chmod +x bin/o

cat > bin/o-loop << 'EOF2'
#!/usr/bin/env python3
"""Autonomous loop with plugin system and skill injection."""
import sys
import time
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from oframe.core import ask_ollama, profit_score
from oframe.plugin_manager import PluginManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("o-loop")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--iterations", type=int, default=5, help="Number of iterations")
    parser.add_argument("--continuous", action="store_true", help="Run forever")
    args = parser.parse_args()

    # Load plugins
    plugin_dirs = [Path.home() / ".oframe" / "plugins", Path("oframe/plugins")]
    pm = PluginManager(plugin_dirs)
    pm.discover_and_load()
    logger.info(f"Loaded {len(pm.plugins)} plugins")

    question = "What's the fastest way to make \$100 today using only local tools?"
    iteration = 0
    try:
        while args.continuous or iteration < args.iterations:
            iteration += 1
            logger.info(f"Iteration {iteration}")

            # Skill injection (shortcut LLM if plugin has answer)
            skill_answer = pm.get_matched_answer(question)
            if skill_answer:
                answer = skill_answer
                logger.info("⚡ Used skill shortcut")
            else:
                answer = ask_ollama(question)
            score = profit_score(answer)
            next_q = ask_ollama(f"Based on '{answer}', what should I ask next?")
            logger.info(f"Score: {score}")

            # Forward to plugins
            pm.on_iteration_all(iteration, question, answer, score, next_q)

            # If golden idea (score >= 70), trigger golden idea hook
            if score >= 70:
                idea = {"question": question, "answer": answer, "score": score, "next_question": next_q}
                pm.on_golden_idea_all(idea)

            question = next_q
            if not args.continuous:
                time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        pm.on_shutdown_all()

if __name__ == "__main__":
    main()
EOF2
chmod +x bin/o-loop

# ---------- oframe/ core files ----------
cat > oframe/__init__.py << 'EOF2'
from .core import ask_ollama, profit_score, search_web
from .state import load_state, save_state
EOF2

cat > oframe/core.py << 'EOF2'
import subprocess
import random
from ddgs import DDGS

def ask_ollama(prompt: str, model: str = "llama3.2:3b", use_cache: bool = True) -> str:
    """Send prompt to local Ollama model."""
    # Simple cache (optional)
    result = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True)
    return result.stdout.strip()

def profit_score(text: str) -> int:
    """Heuristic profit score (0-100)."""
    keywords = ["money", "sell", "product", "service", "automate", "arbitrage", "inference", "spectrum"]
    score = sum(10 for k in keywords if k in text.lower())
    return min(score, 100)

def search_web(query: str):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=3))
EOF2

cat > oframe/state.py << 'EOF2'
import json
from pathlib import Path

STATE_FILE = Path.home() / ".oframe" / "state.json"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"golden_ideas": [], "iterations": 0}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
EOF2

cat > oframe/plugin_interface.py << 'EOF2'
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

class OFramePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def on_load(self, config: Dict[str, Any]) -> None:
        pass

    def scout(self, context: Dict[str, Any]) -> Optional[List[str]]:
        return None

    def filter(self, idea: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    def build(self, idea: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    def on_iteration(self, iter_num: int, question: str, answer: str, score: int, next_q: str) -> None:
        pass

    def on_golden_idea(self, idea: Dict[str, Any]) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def get_matched_answer(self, question: str) -> Optional[str]:
        return None
EOF2

cat > oframe/plugin_manager.py << 'EOF2'
import importlib.util
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .plugin_interface import OFramePlugin

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self, plugin_dirs: List[Path]):
        self.dirs = plugin_dirs
        self.plugins: List[OFramePlugin] = []

    def discover_and_load(self) -> None:
        for d in self.dirs:
            if not d.exists():
                continue
            for pyfile in d.glob("*.py"):
                if pyfile.name.startswith("_"):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)
                    if not spec or not spec.loader:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for attr_name in dir(module):
                        obj = getattr(module, attr_name)
                        if isinstance(obj, type) and issubclass(obj, OFramePlugin) and obj != OFramePlugin:
                            plugin = obj()
                            plugin.on_load({})
                            self.plugins.append(plugin)
                            logger.info(f"Loaded plugin: {plugin.name}")
                except Exception as e:
                    logger.error(f"Failed to load {pyfile}: {e}")

    def get_matched_answer(self, question: str) -> Optional[str]:
        for p in self.plugins:
            ans = p.get_matched_answer(question)
            if ans:
                return ans
        return None

    def on_iteration_all(self, iter_num: int, question: str, answer: str, score: int, next_q: str) -> None:
        for p in self.plugins:
            try:
                p.on_iteration(iter_num, question, answer, score, next_q)
            except Exception as e:
                logger.warning(f"Plugin {p.name} on_iteration failed: {e}")

    def on_golden_idea_all(self, idea: Dict[str, Any]) -> None:
        for p in self.plugins:
            try:
                p.on_golden_idea(idea)
            except Exception as e:
                logger.warning(f"Plugin {p.name} on_golden_idea failed: {e}")

    def on_shutdown_all(self) -> None:
        for p in self.plugins:
            try:
                p.on_shutdown()
            except Exception as e:
                logger.warning(f"Plugin {p.name} on_shutdown failed: {e}")
EOF2

# ---------- Other stubs (optional but expected) ----------
cat > oframe/golden_goose.py << 'EOF2'
# Stub – orchestrates idea → MVP plan (future expansion)
pass
EOF2
cat > oframe/market_analysis.py << 'EOF2'
# Stub – competitor/segment analysis
pass
EOF2
cat > oframe/mvp_builder.py << 'EOF2'
# Stub – generates 6‑step plan via Jinja2
pass
EOF2
cat > oframe/news_agent.py << 'EOF2'
# Stub – scans web for opportunities
pass
EOF2
cat > oframe/api_server.py << 'EOF2'
# Stub – optional FastAPI server
pass
EOF2

# ---------- Plugin: hermes_bridge (self‑improving) ----------
mkdir -p oframe/plugins
cat > oframe/plugins/hermes_bridge.py << 'EOF2'
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from oframe.plugin_interface import OFramePlugin
from oframe.core import ask_ollama

logger = logging.getLogger(__name__)

class HermesBridge(OFramePlugin):
    @property
    def name(self) -> str:
        return "hermes_bridge"

    def on_load(self, config):
        self.memory_dir = Path.home() / ".oframe" / "hermes"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.skills_file = self.memory_dir / "learned_skills.json"
        self.episodes_file = self.memory_dir / "episodes.json"
        self._load_skills()

    def _load_skills(self):
        if self.skills_file.exists():
            with open(self.skills_file) as f:
                self.skills = json.load(f)
        else:
            self.skills = {}
        if self.episodes_file.exists():
            with open(self.episodes_file) as f:
                self.episodes = json.load(f)
        else:
            self.episodes = []

    def _save_skills(self):
        with open(self.skills_file, "w") as f:
            json.dump(self.skills, f, indent=2)

    def _save_episodes(self):
        with open(self.episodes_file, "w") as f:
            json.dump(self.episodes[-100:], f, indent=2)

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def on_iteration(self, iter_num, question, answer, score, next_q):
        best_match = None
        best_ratio = 0.6
        for skill_data in self.skills.values():
            orig_q = skill_data.get("original_question", "")
            ratio = self._similarity(question, orig_q)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = skill_data
        if best_match:
            logger.info(f"📚 Hermes skill match ({best_ratio:.2f}): {best_match['skill'][:50]}")

    def on_golden_idea(self, idea: dict):
        # Store episode
        episode = {
            "timestamp": datetime.now().isoformat(),
            "question": idea.get("question", ""),
            "answer": idea.get("answer", ""),
            "score": idea.get("score", 0),
            "next_question": idea.get("next_question", "")
        }
        self.episodes.append(episode)
        self._save_episodes()
        # Reflect and create skill
        reflection_prompt = f"""
Reflect on this successful golden idea:
Question: {episode['question']}
Answer: {episode['answer']}
Score: {episode['score']}
Write a short reusable skill (2‑3 sentences) capturing the pattern.
"""
        new_skill = ask_ollama(reflection_prompt)
        key = hashlib.md5(episode['question'].encode()).hexdigest()[:8]
        self.skills[key] = {
            "original_question": episode['question'],
            "skill": new_skill,
            "score": episode['score'],
            "created": episode['timestamp']
        }
        self._save_skills()
        logger.info(f"🧠 Hermes learned new skill from golden idea (key: {key})")

    def get_matched_answer(self, question: str) -> str | None:
        best_match = None
        best_ratio = 0.6
        for skill_data in self.skills.values():
            orig_q = skill_data.get("original_question", "")
            ratio = self._similarity(question, orig_q)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = skill_data
        if best_match:
            return f"[Based on previous success] {best_match['skill']}\n\nWould you like me to apply this?"
        return None
EOF2

# ---------- Plugin: revenue_stream_bridge (executor) ----------
cat > oframe/plugins/revenue_stream_bridge.py << 'EOF2'
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
EOF2

# ---------- requirements.txt ----------
cat > requirements.txt << 'EOF2'
ddgs
flask
requests
jinja2
EOF2

# ---------- setup.sh ----------
cat > setup.sh << 'EOF2'
#!/bin/bash
pip install -r requirements.txt
mkdir -p ~/.oframe/plugins
cp -r oframe/plugins/* ~/.oframe/plugins/ 2>/dev/null || true
echo "O‑Frame setup complete."
EOF2
chmod +x setup.sh

# ---------- .gitignore ----------
cat > .gitignore << 'EOF2'
__pycache__/
*.pyc
*.pyo
.env
.venv
venv/
~/.oframe/
*.db
*.log
EOF2

# ---------- README.md (minimum) ----------
cat > README.md << 'EOF2'
# O‑Frame + AI Agent Economy

Autonomous idea generation and execution with self‑improving skills and revenue streams.

## Quick Start
1. Install Ollama and pull `llama3.2:3b`
2. Run `bash setup.sh`
3. Start any revenue stream servers (spectrum, robot, etc.)
4. Run `bin/o-loop -n 5`
EOF2

echo "✅ All O‑Frame files restored. Run 'bash setup.sh' then 'bin/o-loop' to test."
