import random

# import tracing functions
from ddtrace import tracer
from ddtrace.contrib.flask import TraceMiddleware

from flask import Flask, request, jsonify


app = Flask(__name__)

# trace the Flask application
tracer.configure(hostname='agent')
TraceMiddleware(app, tracer, service="taster")


@app.route("/taste")
def taste():
    # continue the trace
    trace_id = request.headers.get("X-Datadog-Trace-Id")
    parent_id = request.headers.get("X-Datadog-Parent-Id")
    if trace_id and parent_id:
        span = tracer.current_span()
        span.trace_id = int(trace_id)
        span.parent_id = int(parent_id)

    # send the remaining candidates to our taster and pick the best
    matches = []
    beer = request.args.get("beer")
    candidates = request.args.getlist("donuts")

    for candidate in candidates:
        score = random.randint(1, 10)
        matches.append((score, candidate))

    best_match = max(matches)

    return jsonify(candidate=best_match[1], score=best_match[0])
