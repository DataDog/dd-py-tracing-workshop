import random

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/taste")
def taste():
    beer = request.args.get("beer")
    score = 10 if beer == 'stout' else random.randint(1, 10)
    return jsonify(score=score)
