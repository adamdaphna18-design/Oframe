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
