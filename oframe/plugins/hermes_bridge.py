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
