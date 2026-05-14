# oframe/servers/multi_model_router.py
import requests, random
from flask import Flask, request, jsonify

app = Flask(__name__)
models = [
    {"name":"llama3.2:3b","endpoint":"http://localhost:11434/api/generate","cost":0.001,"quality":70},
    {"name":"gemini-flash","endpoint":"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent","cost":0.0,"quality":65},
    {"name":"groq-mixtral","endpoint":"https://api.groq.com/openai/v1/chat/completions","cost":0.0,"quality":68},
]

def call_local(prompt):
    r = requests.post("http://localhost:11434/api/generate", json={"model":"llama3.2:3b","prompt":prompt,"stream":False})
    return r.json().get("response","") if r.ok else ""

def route(prompt, min_quality=50):
    candidates = [m for m in models if m["quality"] >= min_quality] or models
    best = min(candidates, key=lambda m: m["cost"])
    if best["name"].startswith("llama"):
        resp = call_local(prompt)
    else:
        resp = f"[Mock {best['name']}] {prompt[:100]}"
    return resp, best["name"], best["cost"]

@app.route('/infer', methods=['POST'])
def infer():
    data = request.json
    if not data.get("payment_id"):
        return jsonify({"error":"payment required"}),402
    prompt = data.get("prompt","")
    min_q = data.get("min_quality",50)
    resp, model, cost = route(prompt, min_q)
    return jsonify({"response":resp,"model":model,"cost_cents":cost*100})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013)