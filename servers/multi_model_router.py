# servers/multi_model_router.py
import requests
import time
import random
from flask import Flask, request, jsonify

app = Flask(__name__)

# Model registry: (name, endpoint, cost_per_1k_tokens, avg_quality)
models = [
    {"name": "llama3.2:3b", "endpoint": "http://localhost:11434/api/generate", "cost": 0.001, "quality": 70},
    {"name": "gemini-flash-free", "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_API_KEY", "cost": 0.0, "quality": 65},
    {"name": "groq-mixtral-free", "endpoint": "https://api.groq.com/openai/v1/chat/completions", "cost": 0.0, "quality": 68},
]

def call_ollama(prompt, model_name):
    url = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except:
        pass
    return None

def call_gemini(prompt):
    # mock – replace with real API key
    return f"[Gemini mock] {prompt[:50]}..."

def call_groq(prompt):
    # mock – replace with real API key
    return f"[Groq mock] {prompt[:50]}..."

def route_request(prompt, min_quality=50):
    # filter models that meet min quality
    candidates = [m for m in models if m["quality"] >= min_quality]
    if not candidates:
        candidates = models  # fallback
    # pick cheapest (lowest cost)
    best = min(candidates, key=lambda m: m["cost"])
    # call the selected model
    if best["name"].startswith("llama"):
        response = call_ollama(prompt, best["name"])
    elif "gemini" in best["name"]:
        response = call_gemini(prompt)
    else:
        response = call_groq(prompt)
    return response, best["name"], best["cost"]

@app.route('/infer', methods=['POST'])
def infer():
    data = request.get_json()
    if not data or 'payment_id' not in data:
        return jsonify({"error": "payment required"}), 402
    prompt = data.get("prompt", "")
    min_quality = data.get("min_quality", 50)
    response, model_used, cost = route_request(prompt, min_quality)
    return jsonify({
        "response": response,
        "model": model_used,
        "cost_cents": cost * 100  # convert to cents
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013)
