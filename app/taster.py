# STEP 05 - Distributed Tracing
from ddtrace import tracer 
tracer.configure(hostname='agent', port=8126)  
from ddtrace import config ; config.flask['service_name'] = 'taster'

from ddtrace import patch_all;
patch_all()



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
