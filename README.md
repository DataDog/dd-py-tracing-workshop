# Datadog Distributed Tracing Workshop

Content for a workshop on Distributed Tracing sponsored by [Datadog](http://www.datadoghq.com)

## Prerequisites

* Install ``docker`` and ``docker-compose`` on your system. Please, follow the instructions available
  in the [Docker website](https://www.docker.com/community-edition)
* A [Datadog Account](https://app.datadoghq.com/signup)
* A Datadog ``API_KEY`` that you can create from the [Datadog API page](https://app.datadoghq.com/account/settings#api).
  Remember to not share this key with anyone.

## Flask Application

Here's an app that does a simple thing. It tells you what donut to pair with your craft brew. While it is contrived in its purpose,
it probably has something in common with the apps you work on:
* It's a web application that exposes HTTP endpoints.
* To do its job, it must talk to datastores and external services.
* It may need performance improvements.

## Get Started

The application runs in many Docker containers that you can launch using the following command:

```bash
$ DD_API_KEY=<add_your_API_KEY_here> docker-compose up
```

Each Python application runs a Flask server with live-reload so you can update your code without restarting any container.
After executing the command above, you should have running:
* A Flask app ``web``, accepting HTTP requests
* A smaller Flask app ``taster``, also accepting HTTP requests
* Redis, the backing datastore
* Datadog agent, a process that listens for, samples and aggregates traces

You can run the following command to verify these are running properly.

```bash
$ docker-compose ps
```

If all containers are running properly, you should see the following:

```
            Name                           Command               State                          Ports
-----------------------------------------------------------------------------------------------------------------------------
ddpytracingworkshop_agent_1     /entrypoint.sh supervisord ...   Up      7777/tcp, 8125/udp, 0.0.0.0:8126->8126/tcp, 9001/tcp
ddpytracingworkshop_redis_1     docker-entrypoint.sh redis ...   Up      6379/tcp
ddpytracingworkshop_taster_1    python taster.py                 Up      0.0.0.0:5001->5001/tcp
ddpytracingworkshop_web_1       python app.py                    Up      0.0.0.0:5000->5000/tcp
```


## Step 0

Let's poke through the app and see how it works.

### Architecture

* Vital Business Info about Beers and Donuts lives in a SQL database.

* Some information about Donuts changes rapidly, with the waves of baker opinion, so
we store this time-sensitive information in a Redis-backed datastore called DonutStats.

* The `DonutStats` class abstracts away some of the gory details and provides a simple API

### HTTP Interface

* We can list the beers we have available
`curl -XGET "localhost:5000/beers"`

* The donuts we have available
`curl -XGET "localhost:5000/donuts"`

* We can grab a beer by name
`curl -XGET "localhost:5000/beers/ipa"`

* We can grab a donut by name
`curl -XGET "localhost:5000/donuts/jelly"`

So far so good.

Things feel pretty speedy. But what happens when we try to find a donut that pairs well with our favorite beer?

* `curl -XGET "localhost:5000/pair/beer?name=ipa"`

It feels slow! Slow enough that people might complain about it. Let's try to understand why




## Step 1 - Import Tracing Solution

In this first step, we'll use basic manual instrumentation to trace one single function from our application. Let's edit the `app.py` to do that.

Import and configure tracing capabilities.

```python
# app.py

from ddtrace import tracer
tracer.configure(hostname='agent', port=8126)
```

Add the datadog tracer decorator to beer function.
```python
# app.py

@app.route('/beers')
@tracer.wrap(service='beers')
def beers():
```

## Step 2 - Correlate Traces and Logs

```python
# app.py

patch_all(logging=True)
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)
log.level = logging.INFO
```


## Step 1 - Datadog's Python Tracing Client

Datadog's tracing client integrates with several commonly used python libraries.

Instrumentation can be explicit or implicit, and uses any library standards for telemetry that exist.
For most web frameworks this means Middleware. Let's add trace middleware for our Flask integration:

```python
# app.py
from ddtrace import tracer
from ddtrace.contrib.flask import TraceMiddleware

app = create_app()
TraceMiddleware(app, tracer, service="match-maker")
```

The middleware is operating by monkey patching the flask integration to ensure it is:
- Timing requests
- Collecting request-scoped metadata
- Pinning some information to the global request context to allow causal relationships to be registered

Now, if we hit our app, we can see that Datadog has begun to display some information for us. Meaning,
you should be able to see some data in the APM portion of the Datadog application. Ultimately,
this code will produce a flame graph that looks like this:

![https://cl.ly/1U0v3M0t0W2Z](https://d1ax1i5f2y3x71.cloudfront.net/items/0E3t1V1J31020y0G0L3u/Image%202017-09-23%20at%201.23.42%20PM.png?X-CloudApp-Visitor-Id=2639901 "Basic trace")

### Services, Names, and Resources

Datadog's tracing client configures your application to emit _Spans_.
A span is a chunk of computation time. It is an operation that you care about, that takes some amount of time in the process of serving a request
Let's look at what a span consists of:

```
name flask.request
id 7245111199352082055
trace_id 1044159332829592407
parent_id None
service match-maker
resource ping
type http
start 1495094155.75
end 1495094155.92
duration 0.17s
error 0
tags [
    http.status_code: 200
]
```

* `name` is the name of the operation being traced
* `service` is the name of a set of processes that work together to provide a feature set.
* `resource` is a particular query to a service. For web apps this is usually the route or handler function
* `id` is the unique ID of the current span
* `trace_id` is the unique ID of the request containing this span
* `parent_id` is the unique ID of the span that was the immediate causal predecessor of this span.

Remember the significance of `trace_id` and `parent_id`. We'll need them later as we wire up
tracing across service boundaries.

## Step 2 - Manual Instrumentation

While expressive, a ``Span`` by itself is not incredibly useful. Let's add some context around it.

Our app involves multiple services.
You'll notice our service list is a little bare. That's because right now, Datadog only knows about the
one high-level flask service. Let's do some work so that it knows about the other services and datastores we communicate with.

```python
# app.py

@app.route('/pair/beer')
def pair():
    """A complex endpoint that makes a request to another Python service"""
    name = request.args.get('name')

    with tracer.trace("beer.query", service="beer-database"):
        beer = Beer.query.filter_by(name=name).first()

    # force a query
    with tracer.trace("donuts.query", service="beer-database"):
        Donut.query.all()

    with tracer.trace("donuts.query") as span:
        span.set_tag('beer.name', name)
        match = best_match(beer)
    return jsonify(match=match)
```

If we hit the ``/pair/beer`` route a few more times, we should see a trace like this one:

![https://cl.ly/1u0l1v3b1I46](https://d1ax1i5f2y3x71.cloudfront.net/items/2n2I3G3r320b082X0k1q/Image%202017-09-23%20at%201.50.43%20PM.png?X-CloudApp-Visitor-Id=2639901) 

It's also worth noting that we now are able to see the tag
we have set as well. If you select the appropriate span, you will see it in the metadata
below:

![https://cl.ly/163F000D0t2O](https://d1ax1i5f2y3x71.cloudfront.net/items/1Q1c0I1I3H2E0m0v2N0g/%5B4025b9ed7be33e3697c568703b3e2cf8%5D_Image%25202017-09-23%2520at%25201.52.08%2520PM.png?X-CloudApp-Visitor-Id=2639901)

## Step 3 - Trace Application Libraries

A good tracing client will unpack, for instance, some of the layers of indirection in ORMs, and give
you a true view of the SQL being executed. This lets us marry the the nice APIs of ORMS with visibility
into what exactly is being executed and how performant it is.

Let's see what Datadog's ``sqlalchemy``, ``redis`` and ``requests`` integrations can do to help
de-mystify some of the abstractions we've built in our app. We'll use Datadog's monkey patcher, a tool
for safely adding tracing to packages in the import space:

```python
# bootstrap.py

from ddtrace import tracer, patch
patch(sqlalchemy=True, redis=True, requests=True)
```

Ping our favorite route a few more times, and Datadog should show you a trace like this:

![https://cl.ly/0l2Y2x1w0i37](https://d1ax1i5f2y3x71.cloudfront.net/items/24022k1k1N3G0Q0r3z3p/Image%202017-09-23%20at%202.07.44%20PM.png?X-CloudApp-Visitor-Id=2639901)

## Step 4 - Distributed!

Most of the hard problems we have to solve in our systems won't involve just one application. Even in our
toy app the ``best_match`` function crosses a distinct service boundary, making an HTTP call to the "taster" service.

For traditional metrics and logging crossing a service boundary is often a full stop for whatever telemetry you have
in place. But traces can cross these boundaries, which is what makes them so useful.

Here's how to make this happen in the Datadog client. First we configure the service that behaves as the client,
to propagate information about the active trace via HTTP headers:

```python
# app.py

def best_match(beer):
    # ...
    for candidate in candidates:
        try:
            # propagate the trace context between the two services
            span = tracer.current_span()
            headers = {
                "X-Datadog-Trace-Id": str(span.trace_id),
                "X-Datadog-Parent-Id": str(span.span_id),
            }

            resp = requests.get(
                "http://taster:5001/taste",
                params={"beer": beer.name, "donut": candidate},
                timeout=2,
                headers=headers,
            )
        except requests.exceptions.Timeout:
            continue
    # ...
```

We set up tracing on the server-side app (``taster``):

```python
# taster.py

import random

# import tracing functions
from ddtrace import tracer
from ddtrace.contrib.flask import TraceMiddleware

from flask import Flask, request, jsonify


app = create_app()

# trace the Flask application
tracer.configure(hostname='agent')
TraceMiddleware(app, tracer, service="taster")
```

Then we configure the server side of this equation to extract this information from the HTTP headers and continue the trace:
```python
# taster.py

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
    # ...
```

Let's hit our pairing route a few more times now, and see what Datadog turns up:
``curl -XGET "localhost:5000/pair/beer?name=ipa"``

If everything went well we should see a distributed trace: 

![alt text](https://d1ax1i5f2y3x71.cloudfront.net/items/2C130u1S143T1f3p2H33/Image%202017-09-23%20at%202.20.42%20PM.png?X-CloudApp-Visitor-Id=2639901 "Distributed Trace")

## Step 5 - Optimize Endpoint

As we can see from that trace, we're spending a lot of time in the requests library,
especially relative to the amount of work being done in the taster application. This
looks like a place we can optimize.

If we look at the work being done in the ``best_match()`` and ``taste()``, we see
that we can probably move work from ``best_match()`` to ``taste()`` and eliminate
the number of requests we are making.

Let's do this and see if we can cut down the average latency of this code!

First, we'll refactor ``best_match`` to include all of the candidates in its request,
rather than making multiple requests.

```python
# app.py

def best_match(beer):
    # ...
    try:
        # propagate the trace context between the two services
        span = tracer.current_span()
        headers = {
            "X-Datadog-Trace-Id": str(span.trace_id),
            "X-Datadog-Parent-Id": str(span.span_id),
        }

        resp = requests.get(
            "http://taster:5001/taste",
            params={"beer": beer.name, "donuts": candidates},
            timeout=2,
            headers=headers,
        )
    except requests.exceptions.Timeout:
        # log the error
        return "not available"
    # ...
```

Then, we'll refactor the ``taste()`` function to accept this and return the donut
with the highest taste score.

```python
# taster.py

@app.route("/taste")
def taste():
    # ...
    # send the remaining candidates to our taster and pick the best
    matches = []
    beer = request.args.get("beer")
    candidates = request.args.getlist("donuts")

    for candidate in candidates:
        score = random.randint(1, 10)
        matches.append((score, candidate))

    best_match = max(matches)
    return jsonify(candidate=best_match[1], score=best_match[0])
```

Once we've done this, we can take a look at another trace and notice that we've
cut down the total time significantly, or about ~60 ms to ~20 ms: 

![https://cl.ly/3J3Y0B330p1P](https://d1ax1i5f2y3x71.cloudfront.net/items/1k02400O1X331A123036/Image%202017-09-23%20at%202.47.53%20PM.png?X-CloudApp-Visitor-Id=2639901)

## In conclusion

Datadog's tracing client gives you a lot of tools to extract meaningful insights from your Python apps.

We support an explicit approach, with tracing constructs embedded in your code, as well as more implicit ones,
with tracing auto-patched into common libraries or even triggered via our command line entrypoint like so:

```bash
$ ddtrace-run python my_app.py
```

We hope you can find an approach that fits for your app. More details at:
* https://pypi.datadoghq.com/trace/docs
* https://github.com/DataDog/dd-trace-py

Happy Tracing!
