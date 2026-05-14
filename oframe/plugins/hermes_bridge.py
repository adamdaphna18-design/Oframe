"""Hermes Bridge Plugin – Self‑improving learning loop for O‑Frame."""
import json
import hashlib
import logging
import requests
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
        self.memory_dir.mkdir(exist_ok=True, parents=True)
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
            json.dump(self.episodes[-100:], f, indent=2)  # keep last 100

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def on_iteration(self, iter_num, question, answer, score, next_q):
        # Optional: check if question matches a learned skill
        best_match = None
        best_ratio = 0.6  # threshold
        for skill_key, skill_data in self.skills.items():
            ratio = self._similarity(question, skill_data["original_question"])
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = skill_data
        if best_match:
            logger.info(f"📚 Hermes skill match ({best_ratio:.2f}): using template from '{best_match['original_question'][:50]}'")
            # The main loop could use best_match['answer'] as a starting point,
            # but we'll just log for now – you can extend to pre‑fill.

    def on_golden_idea(self, idea: dict):
        # 1. Store episode
        episode = {
            "timestamp": datetime.now().isoformat(),
            "question": idea.get("question", ""),
            "answer": idea.get("answer", ""),
            "score": idea.get("score", 0),
            "next_question": idea.get("next_question", ""),
            "plan_path": idea.get("plan_path", "")
        }
        self.episodes.append(episode)
        self._save_episodes()

        # Emit event for scheduler
        try:
            requests.post("http://localhost:5015/event", json={
                "event": "golden_idea",
                "score": idea.get("score", 0),
                "question": idea.get("question", ""),
                "answer": idea.get("answer", "")
            }, timeout=1)
        except:
            pass

        # 2. Reflect and create/update a skill
        reflection_prompt = f"""
You are Hermes, the learning engine. Reflect on this successful golden idea:

Question: {episode['question']}
Answer: {episode['answer']}
Profit score: {episode['score']}

Write a short, reusable “skill” that captures the pattern that made this idea profitable.
The skill should be a 2‑3 sentence heuristic that can be applied to similar future questions.
Only output the skill text, nothing else.
"""
        new_skill = ask_ollama(reflection_prompt)

        # Use a key based on question keywords (e.g., first 50 chars as hash)
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
        for skill_key, skill_data in self.skills.items():
            ratio = self._similarity(question, skill_data["original_question"])
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = skill_data
        if best_match:
            return f"[Based on a previous successful idea] {best_match['skill']}\n\nWould you like me to elaborate?"
        return None
