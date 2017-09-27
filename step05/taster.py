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

    request.args.get("beer")
    request.args.get("donut")

    # TODO: insert a crash here
    score = random.randint(1, 10)
    return jsonify(score=score)
