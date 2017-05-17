from __future__ import print_function

import random
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/taste")
def pair(name):
    # tid = request.headers.get("X-Trace-Id")
    # pid = request.headers.get("X-Parent-Span-Id")
    beer = request.params.get("beer")
    donut = request.params.get("donut")
    
    # TODO: Insert awesome scoring algo here
    score = random.randint(1, 10)
    return jsonify(score=score)
