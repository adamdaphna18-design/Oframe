import subprocess
from duckduckgo_search import DDGS

def ask_ollama(prompt: str) -> str:
    result = subprocess.run(["ollama", "run", "llama3.2", prompt], capture_output=True, text=True)
    return result.stdout.strip()

def profit_score(text: str) -> int:
    # simple heuristic
    return 3

def search_web(query: str):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=3))
