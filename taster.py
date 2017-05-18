from __future__ import print_function

import random
from flask import Flask, request, jsonify, g

app = Flask(__name__)


@app.route("/taste")
def taste():
    beer = request.args.get("beer")
    donut = request.args.get("donut")
    
    # TODO: Insert awesome scoring algo here
    score = random.randint(1, 10)
    return jsonify(score=score)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
