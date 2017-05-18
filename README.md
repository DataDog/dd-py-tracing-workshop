# Pycon 2017 Distributed Tracing Workshop

Content for a workshop on Distributed Tracing sponsored by [Datadog](http://www.datadoghq.com) at Pycon 2017

## Prerequisites
- `docker`
- `docker-compose`
- `python`
- [A Datadog Account](https://app.datadoghq.com/signup)


## A sample app in Flask begging to be traced
Here's an app that does a simple thing. It tells you what donut to pair with your craft brew. While it is contrived in its purpose, it probably has something in common with the apps you work on:

- It speaks HTTP
- To do its job, it must talk to datastores and external services.
- It has performance issues

## Get started
**Set your [Datadog API key](https://app.datadoghq.com/account/settings#api) in the docker-compose.yml file**

Now start up the sample app
```
$ docker-compose up
```

Now you should have running:
- A Flask app `web`, accepting HTTP requests
- A smaller Flask app `taster`, also accepting HTTP requests
- Redis, the backing datastore
- Datadog agent, a process that listens for, samples and aggregates traces

You can run the following command to verify these are running properly.

```
$ docker-compose ps
```

If all containers are running properly, you should see the following:

```
            Name                           Command               State                          Ports
-----------------------------------------------------------------------------------------------------------------------------
pycontracingworkshop_agent_1    /entrypoint.sh supervisord ...   Up      7777/tcp, 8125/udp, 0.0.0.0:8126->8126/tcp, 9001/tcp
pycontracingworkshop_redis_1    docker-entrypoint.sh redis ...   Up      6379/tcp
pycontracingworkshop_taster_1   python taster.py                 Up      0.0.0.0:5001->5001/tcp
pycontracingworkshop_web_1      python app.py                    Up      0.0.0.0:5000->5000/tcp
```

## Debugging
A few useful commands for debugging. You'll want these handy:

```
# Tail the logs for the trace-agent
docker exec -it pycontracingworkshop_agent_1 tail -f /var/log/datadog/trace-agent.log
```

```
# Tail the logs for web container
docker-compose logs -f web
```

## Step 1

Let's poke through the app and see how it works.

Vital Business Info about Beers and Donuts live in a SQL database.

Some information about Donuts changes rapidly, with the waves of baker opinion.
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
    @wraps(func)
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

This code lives for you in `timing.py` and logs to `timing.log`. Let's wire these into the app, `app.py`.
```python
from timing import timing_decorator, TimingContextManager
...

@app.route('/pair/beer')
@timing_decorator
def pair():
    ...
```
Now, when our slow route gets hit, it dumps some helpful debug information to the log, `timing.log`.

You can start to see log lines such as:

```
function pair took 0.053 seconds
```

## Step 3 - Drill Down into subfunctions

The information about our bad route is still rather one-dimensional. The pair route does some fairly
complex things and i'm still not entirely sure _where_ it spends its time.

Let me use the timing context manager to drill down further.
```python
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


## Step 4 - Request-scoped Metadata
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
        req_id = uuid.uuid1().int>>64 # a random 64-bit int
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
req: 10743597937325899402, operation beer.query took 0.023 seconds
req: 10743597937325899402, operation donuts.query took 0.006 seconds
req: 10743597937325899402, operation match took 0.013 seconds
req: 10743597937325899402, function pair took 0.047 seconds
```


## Step 5 - A Step back
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


## Step 6 - Datadog's python tracing client
Datadog's tracing client integrates with several commonly used python libraries.

Instrumentation can be explicit or implicit, and uses any library standards for telemetry that exist.
For most web frameworks this means Middleware. Let's add trace middleware to our flask integration

```python
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

Now that Datadog is doing the work for us at the middleware layer, lets drop out `@timing_decorator` and each `with TimingContextManager` in our `app.py` file.

If we hit our app a few more times, we can see that datadog has begun to display some information for us.
Let's walk through what you're seeing: _segue to demo

## Step 7 - Services, Names, and Resources
Datadog's tracing client configures your application to emit _Spans_ .
A span is a chunk of computation time. It is an operation that you care about, that takes some amount of time in the process of serving a request

Let's look at what a span consists of.
```
name flask.request
id 7245111199352082055
trace_id 1044159332829592407
parent_id None
service matchmaker
resource ping
type http
start 1495094155.75
end 1495094155.92
duration 0.17s
error 0
tags
    http.status_code: 200
```

`name` is the name of the operation being traced

A `service` is the name of a set of processes that work together to provide a feature set.

A `resource` is a particular query to a service. For web apps this is usually the route or handler function

`id` is the unique ID of the current span

`trace_id` is the unique ID of the request containing this span

`parent_id` is the unique ID of the span that was the immediate causal predecessor of this span.

Remember the significance of `trace_id` and `parent_id`. We'll need them later as we wire up
tracing across service boundaries.

## Step 8 - Nested spans
While expressive, a Span by itself is not incredibly useful. Let's add some context around it.

Our app involves multiple services.
You'll notice our service list is a little bare. That's because right now, Datadog only knows about the
one high-level flask service. Let's do some work so that it knows about the other services and datastores we communicate with.

Datadog's tracing client provides a version of the TimingContextManager that produces well-formatted _spans_.
It also accepts as parameters the service, name and resource identifiers we just talked about.

Let's do a subtle rewrite of our context managers
```python
# app.py

@app.route('/pair/beer')
def pair():
    name = request.args.get('name')

    with tracer.trace("beer.query", service="db"):
        beer = Beer.query.filter_by(name=name).first()
    with tracer.trace("donuts.query", service="db"):
        donuts = Donut.query.all()

    # leaving the service blank implies that we inherit the service from our parent
    # i.e. the active span at the time `tracer.trace` is invoked
    with tracer.trace("donuts.query"):
        match = best_match(beer)

    return jsonify(match=match)
```

If we hit the `/pair/beer` route a few more times, we should see a trace like this one:
https://cl.ly/11010t3H2g3N

## Step 9 - Tracing the ORM
A good tracing client will unpack some of the layers of indirection in ORMs , and give you a
true view of the sql being executed. This lets us marry the the nice APIs of ORMS with visibility
into what exactly is being executed and how performant it is

Let's see what Datadog's `sqlalchemy` and `redis` integrations can do to help
de-mystify some of the abstractions we've built in our app. We'll use Datadog's monkey patcher, a tool for safely adding tracing to packages in the import space

```python
# app.py
from ddtrace import monkey; monkey.patch(sqlalchemy=True, redis=True)
```
Ping our favorite route a few more times, and Datadog should show you a trace like this:
https://cl.ly/0U2z3E2X2V07

## Step 10 - Distributed!
Most of the hard problems we have to solve in our systems won't involve just one application. Even in our toy app the `best_match` function crosses a distinct service
boundary, making an HTTP call to the "taster" service.

For traditional metrics and logging crossing a service boundary is often a full stop for whatever telemetry you have in place. But traces can cross these boundaries, which is what makes them so useful.

Here's how to make this happen in the Datadog client.
First we configure the service that behaves as the client, to propagate information about the
active trace via HTTP headers

```python
# app.py

def best_match(beer):
    ...

    for candidate in candidates:
        try:
            # Propagate context between the two services
            headers = {
                "X-Datadog-Trace-Id": str(g.flask_datadog_span.trace_id), # Here's what transaction I am a part of
                "X-Datadog-Parent-Span-Id": str(g.flask_datadog_span.span_id) # Here's the span that is the immediate parent of the server-side span
            }
            resp = requests.get("http://taster:5001/taste", params={"beer": beer.name, "donut": candidate}, timeout=2, headers=headers)
            ...
```

We set up tracing on the server-side app ( "taster" ):

```python
# taster,py

from ddtrace import tracer; tracer.debug_logging = True
tracer.configure(hostname="agent") # point to agent container

from ddtrace.contrib.flask import TraceMiddleware

app = Flask(__name__)
traced_app = TraceMiddleware(app, tracer, service="taster")
```

Then we configure the server side of this equation to extract this information from the http headers and continue the trace
```python
# taster.py

@app.route("/taste")
def taste():
    tid = request.headers.get("X-Datadog-Trace-Id")
    pid = request.headers.get("X-Datadog-Parent-Span-Id")
    if tid and pid:
        g.flask_datadog_span.trace_id = int(tid)
        g.flask_datadog_span.parent_id = int(pid)

    beer = request.args.get("beer")
    ...
```

Let's hit our pairing route a few more times now, and see what Datadog turns up:
`curl -XGET localhost:5000/pair/beer?name=ipa`

If everything went well we should see a distributed trace! 
https://cl.ly/3J2E092U2w2b


## In conclusion
Datadog's tracing client gives you a lot of tools to extract meaningful insights from your Python apps.

We support an explicit approach, with tracing constructs embedded in your code,
as well as more implicit ones, with tracing auto-patched into common libraries or even triggered via our command line entrypoint like so:

```ddtrace-run python my_app.py```

We hope you can find an approach that fits for your app. More details at:
https://pypi.datadoghq.com/trace/docs
https://github.com/DataDog/dd-trace-py

Happy Tracing!
