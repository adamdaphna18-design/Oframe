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
