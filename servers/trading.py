from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/')
def index(): return jsonify({"service": "trading", "status": "running"})
if __name__ == '__main__': app.run(port=5004)
