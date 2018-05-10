import random

from flask import Flask, request, jsonify


app = Flask(__name__)


@app.route("/taste")
def taste():
    beer = request.args.get("beer")

    if beer == 'stout':
        score = random.randint(10, 0)
    else:
        score = random.randint(1, 10)

    return jsonify(score=score)
