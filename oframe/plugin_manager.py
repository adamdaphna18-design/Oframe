"""Dynamic plugin discovery, loading, and lifecycle forwarding."""
import importlib.util
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .plugin_interface import OFramePlugin

logger = logging.getLogger(__name__)

class PluginManager:
    """Loads and manages plugins from given directories."""

    def __init__(self, plugin_dirs: List[Path]):
        self.dirs = plugin_dirs
        self.plugins: List[OFramePlugin] = []

    def discover_and_load(self) -> None:
        """Scan plugin directories, import each Python file, and instantiate plugins."""
        for d in self.dirs:
            if not d.exists():
                logger.debug(f"Plugin dir not found: {d}")
                continue
            logger.info(f"Scanning plugins in: {d}")
            for pyfile in d.glob("*.py"):
                if pyfile.name.startswith("_"):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)
                    if not spec or not spec.loader:
                        logger.warning(f"Could not load spec for {pyfile}")
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Find classes that are subclasses of OFramePlugin (not the base itself)
                    for attr_name in dir(module):
                        obj = getattr(module, attr_name)
                        if (isinstance(obj, type) and
                            issubclass(obj, OFramePlugin) and
                            obj != OFramePlugin):
                            plugin = obj()
                            plugin.on_load({})
                            self.plugins.append(plugin)
                            logger.info(f"✅ Loaded plugin: {plugin.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {pyfile}: {e}")

    # ----- Scout -----
    def scout_all(self, context: Dict[str, Any]) -> List[str]:
        """Collect signals from all plugins' scout() methods."""
        signals = []
        for p in self.plugins:
            try:
                result = p.scout(context)
                if result:
                    signals.extend(result)
            except Exception as e:
                logger.warning(f"Scout plugin {p.name} failed: {e}")
        return signals

    # ----- Filter -----
    def filter_all(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all filter plugins. If any plugin returns accept=False,
        stop and return that verdict.
        """
        for p in self.plugins:
            try:
                result = p.filter(idea)
                if result and not result.get('accept', True):
                    return {
                        'accepted': False,
                        'reason': result.get('reason', 'Filtered by plugin'),
                        'plugin': p.name,
                        'risk_score': result.get('risk_score', 10)
                    }
            except Exception as e:
                logger.warning(f"Filter plugin {p.name} failed: {e}")
        return {'accepted': True}

    # ----- Builder -----
    def build_all(self, idea: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all builder plugins on a golden idea and collect results."""
        results = []
        for p in self.plugins:
            try:
                res = p.build(idea)
                if res:
                    results.append(res)
            except Exception as e:
                logger.warning(f"Builder plugin {p.name} failed: {e}")
        return results

    # ----- Lifecycle forwarding -----
    def on_iteration_all(self, iter_num: int, question: str, answer: str, score: int, next_q: str) -> None:
        for p in self.plugins:
            try:
                p.on_iteration(iter_num, question, answer, score, next_q)
            except Exception as e:
                logger.warning(f"on_iteration plugin {p.name} failed: {e}")

    def on_golden_idea_all(self, idea: Dict[str, Any]) -> None:
        for p in self.plugins:
            try:
                p.on_golden_idea(idea)
            except Exception as e:
                logger.warning(f"on_golden_idea plugin {p.name} failed: {e}")

    def on_shutdown_all(self) -> None:
        for p in self.plugins:
            try:
                p.on_shutdown()
            except Exception as e:
                logger.warning(f"on_shutdown plugin {p.name} failed: {e}")

    # ----- Helper: get matched answer from any plugin -----
    def get_matched_answer(self, question: str) -> Optional[str]:
        for p in self.plugins:
            if hasattr(p, 'get_matched_answer'):
                answer = p.get_matched_answer(question)
                if answer:
                    return answer
        return None
