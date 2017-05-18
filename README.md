# Pycon 2017 Distributed Tracing Workshop

Content for a workshop on Distributed Tracing sponsored by Datadog at Pycon 2017

## Prerequisites
- `docker`
- `docker-compose`
- `python`


## A sample app in Flask begging to be traced
Here's an app that does a simple thing. It tells you what donut to pair with your craft brew. While its contrived in its purpose, it probably has something in common with the apps you work on:

- It speaks HTTP
- To do its job, it must talk to datastores and external services.
- It _fails_

## Get started
**Set your Datadog API key in the docker-compose.yml file**

Now start up the sample app
```
$ docker-compose up
```

Now you should have running:
- A Flask app, accepting HTTP requests
- Redis, the backing datastore
- Datadog agent, a process that listens for, samples and aggregates traces

## Step 1

Let's poke through the app and see how it works.

Vital Business Info about Beers and Donuts live in a SQL database.

Some information about Donuts changes rapidly, with the waves of public opinion.
We store this time-sensitive information in a Redis-backed datastore called DonutDB.

The `DonutDB` class abstracts away some of the gory details and provides a simple API

Now let's look at the HTTP interface.

We can list the beers we have available
`curl -XGET localhost:5000/beers`

And the donuts we have available
`curl -XGET localhost:5000/donuts`

We can grab a beer by name
`curl -XGET localhost:5000/beers/ipa`

and a donut by name
`curl -XGET localhost:5000/donuts/jelly`

So far so good.


Things feel pretty speedy. But what happens when we try to find a donut that pairs well with our favorite beer?

`curl -XGET localhost:5000/pair/beer?name=ipa`

It feels slow! Slow enough that people might complain about it. Let's try to understand why

## Step 2 - Timing a Route

Anyone ever had to time a python function before?
There are several ways to do it, and they all involve some kind of timestamp math

With a decorator:
```python
def timing_decorator(func):
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            ret = func(*args, **kwargs)
        finally:
            end = time.time()
        print("function %s took %.2f seconds" % (func.__name__, end-start))
        return ret
    return wrapped
```

With a context manager:
```python
class TimingContextManager(object):

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, traceback):
        end = time.time()
        log.info("operation %s took %.2f seconds", self.name, end-self.:start)
```

This code lives for you in `timing.py` and logs to `timing.log`. Let's wire these into the app.
```python
from timing import timing_decorator, TimingContextManager
...

@app.route('/pair/beer')
@timing_decorator
def pair():
    ...
```
Now, when our slow route gets hit, it dumps some helpful debug information to the log.

## Step 3 - Drill Down into subfunctions

The information about our bad route is still rather one-dimensional. The pair route does some fairly
complex things and i'm still not entirely sure _where_ it spends its time.

Let me use the timing context manager to drill down further.
```
@app.route('/pair/beer')
@timing_decorator
def pair():
    name = request.args.get('name')

    with TimingContextManager("beer.query"):
        beer = Beer.query.filter_by(name=name).first()
    with TimingContextManager("donuts.query"):
        donuts = Donut.query.all()
    with TimingContextManager("match"):
        match = best_match(beer)

    return jsonify(match=match)
```


We now have a more granular view of where time is being spent
```
operation beer.query took 0.020 seconds
operation donuts.query took 0.005 seconds
operation match took 0.011 seconds
function pair took 0.041 seconds
```

But after several requests, this log becomes increasingly hard to scan! Let's add an identifier
to make sure we can trace the path of a request in its entirety.


## Step 3 - Request-scoped Metadata
You may have the notion of a "correlation ID" in your infrastructure already. The goal of this
identifier is almost always to inspect the lifecycle of a single request, especially one that moves
through several parts of code and several services.

Let's put a correlation ID into our timed routes! Hopefully this will make the log easier to parse


Add it to our decorator
```python
# timing.py

import uuid
...

def timing_decorator(func):
    def wrapped(*args, **kwargs):
        req_id = uuid.uuid1().int>>64 # a random 64-bit int, ask me why later
        from flask import g
        g.req_id = req_id
        ...
        log.info("req: %s, function %s took %.3f seconds", req_id, func.__name__, end-start)
```

... and to our context manager
```
# timing.py
class TimingContextManager(object):

    def __init__(self, name, req_id):
        self.name = name
        self.req_id = req_id

    def __exit__(...):
        ....
        log.info("req: %s, operation %s took %.3f seconds", self.req_id, self.name, end-self.start)
```

```
# app.py
with TimingContextManager('beer.query', g.req_id):
   ...
```

Now we see output like

```
req: 27c2fd1a-98db-4767-bb93-b7582cf9c776, operation beer.query took 0.023 seconds
req: 27c2fd1a-98db-4767-bb93-b7582cf9c776, operation donuts.query took 0.006 seconds
req: 27c2fd1a-98db-4767-bb93-b7582cf9c776, operation match took 0.013 seconds
req: 27c2fd1a-98db-4767-bb93-b7582cf9c776, function pair took 0.047 seconds
```


## Step 4 - A Step back
Let's think about what we've done so far. We've taken an app that was not particularly observable
and made it incrementally more so.

Our app now generates events
   - that are request-scoped.
   - and suggest a causal relationship

Remember our glossary - we're well on our way to having real traces!

One thing to note, this didn't come for free:
 - instrumentation is a non-zero overhead
 - instrumentation logic can leak into business logic in unsavory ways

What a good tracing client does for you is minimize the impact of both of these, while still emitting
rich, structured information.


## Step 5 - Datadog's python tracing client
Datadog's tracing client integrates with several commonly used python libraries.

Instrumentation can be explicit or implicit, and uses any library standards for telemetry that exist.
For most web frameworks this means Middleware. Let's add trace middleware to our flask integration

```
# app.py

from ddtrace import tracer; tracer.debug_logging = True
tracer.configure(hostname="agent") # point to agent container

from ddtrace.contrib.flask import TraceMiddleware

app = Flask(__name__)
traced_app = TraceMiddleware(app, tracer, service="matchmaker")
```
The middleware is doing something very similar to the code you just wrote. It is:
- Timing requests
- Collecting request-scoped metadata
- Pinning some information to the global request context to allow causal relationships to be registered

If we hit our app a few more times, we can see that datadog has begun to display some information for us.
Let's walk through what you're seeing -

Now that Datadog is doing the work for us at the middleware layer, we can drop our `@timing_decorator`

## Step 6 - Services, Names, and Resources
Datadog's tracing client configures your application to emit _Spans_ .
A span is a chunk of computation time, an operation that you care about that is part of serving a request

Let's look at what a span consists. In the previous step, you turned debug_logging on, which instructs
the tracer do dump spans to the console as they're emitted. (Don't do this in production!)
```
TODO Span dump
```

Looks cool but how useful is that by itself. Let's add some context around it.

Our app involves multiple services.
You'll notice our service list is a little bare. That's because right now, Datadog only knows about the
one high-level flask service. Let's do some work so that it knows about the other services and datastores we communicate with.

Datadog's tracing client provides a version of the TimingContextManager that produces well-formatted _spans_.
It also accepts as parameters the service, name and resource identifiers we just talked about.

Let's do a subtle rewrite of our context managers
```
@app.route('/pair/beer')
def pair():
    name = request.args.get('name')

    with tracer.trace("beer.query", service="db"):
        beer = Beer.query.filter_by(name=name).first()
    with tracer.trace("donuts.query", service="db"):
        donuts = Donut.query.all()

    # leaving the service back implies that we inherit the service from our parent
    # i.e. the active span at the time `tracer.trace` is invoked
    with tracer.trace("donuts.query"):
        match = best_match(beer)

    return jsonify(match=match)
```


## Step 7 - Tracing the ORM
A good tracing client will unpack some of the layers of indirection in ORMs , and give you a
true view of the sql being executed. This lets us marry the the nice APIs of ORMS with visibility
into what exactly is being executed and how performant it is

Let's see what Datadog's `sqlalchemy` and `redis` integrations can do to help
de-mystify some of the abstractions we've built
```from ddtrace import monkey; monkey.patch(sqlalchemy=True, redis=True)```

## Step 8 - Distributed!
Most of the hard problems we have to solve in our systems won't involve just one application. Even in our toy app the `best_match` function crosses a distinct service
boundary, making an HTTP call to the "taster" service.


For traditional metrics and logging this is a full-stop in practice. But _traces_
can cross host-boundaries.

Here's how to make this happen in the datadog client


```
def best_match(beer):
    ...

    for candidate in candidates:
        try:
            # Propagate context between the two services
            headers = {
                "X-Datadog-Trace-Id": g.flask_datadog_span.trace_id,
                "X-Datadog-Parent-Span-Id": g.flask_datadog_span.id
            }
            resp = requests.get("http://taster:5001/taste", params={"beer": beer.name, "donut": candidate}, timeout=2, headers=headers)
            ...
```

```
# taster.py

@app.route("/taste")
def pair():
    tid = request.headers.get("X-Datadog-Trace-Id")
    pid = request.headers.get("X-Datadog-Parent-Span-Id")
    if tid and pid:
        g.flask_datadog_span.trace_id = tid
        g.flask_datadog_span.parent_id = pid

    beer = request.args.get("beer")
    ...
```

Let's hit our pairing route a few more times now, and see what Datadog turns up
`curl -XGET localhost:5000/pair/beer?name=ipa`

## Step 9 - Investigate
As datadog shows us we seem to be doing a bucket load of SQL queries for finding
good beer-donut pairings!

A single beer can pair with many donuts! But do we need to issue a query for each of those donuts?

This is a variant of the N+1 problem that most of you will come across at one point or another in your experience with ORMs.
SQLAlchemy's lazy-loading makes this a very easy trap to fall into

Let's see how we can make this query better

## Step 10 - Rearchitect pair route to do fewer DB calls
Rather than lazy-loading donuts that pair can with Beer X. Let's just eagerly load all of them!

with some custom sql
```
SELECT 'donuts'.* FROM 'donuts' WHERE 'donuts'.'id' IN (1,2,3,4,5)
```

How does our route look now? Faster?

## Step 11 - Rearchitect pair route to use a cache
Our pairing request consistently takes about 200ms. Can we do better?
Our list of beers and donuts probably won't change frequently. So for a popular beer
it makes sense to cache its donut pairing so other users will benefit. Let's give that a shot, using a redis cache (part of the same docker compose setup)

How do our traces look now?
