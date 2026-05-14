"""Base plugin interface with lifecycle and role‑based hooks."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

class OFramePlugin(ABC):
    """Base class for all O‑Frame plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        pass

    # Lifecycle hooks
    def on_load(self, config: Dict[str, Any]) -> None:
        """Called once when plugin is loaded. Use to initialise resources."""
        pass

    # ----- Scout (information gathering) -----
    def scout(self, context: Dict[str, Any]) -> Optional[List[str]]:
        """
        Return new raw signals (e.g., URLs, headlines) to feed into the loop.
        Called before each iteration.
        """
        return None

    # ----- Filter (reality check) -----
    def filter(self, idea: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Return a verdict: {'accept': bool, 'reason': str, 'risk_score': int (1-10)}.
        Called after an idea is generated but before it becomes golden.
        """
        return None

    # ----- Builder (execution) -----
    def build(self, idea: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Trigger external action (e.g., call Jules, generate landing page).
        Called after a golden idea is saved.
        """
        return None

    # ----- Logistics (operations) -----
    def on_iteration(self, iter_num: int, question: str, answer: str, score: int, next_q: str) -> None:
        """Called after each loop iteration."""
        pass

    def on_golden_idea(self, idea: Dict[str, Any]) -> None:
        """Called when a golden idea (score >= threshold) is found."""
        pass

    def on_shutdown(self) -> None:
        """Called when the loop exits."""
        pass

    # Optional: add custom CLI commands
    def register_cli(self, subparsers) -> None:
        """Add custom subcommands to the `o` CLI."""
        pass

    # Helper for skill injection (optional)
    def get_matched_answer(self, question: str) -> Optional[str]:
        """
        If the plugin can provide a direct answer from memory/skills,
        return it to shortcut the LLM call.
        """
        return None
