import random

from flask import Flask, request, jsonify


app = Flask(__name__)


@app.route("/taste")
def taste():
    request.args.get("beer")
    request.args.get("donut")

    # TODO: insert a crash here
    score = random.randint(1, 10)
    return jsonify(score=score)
