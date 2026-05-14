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
