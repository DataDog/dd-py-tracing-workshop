# Datadog Distributed Tracing Workshop

Content for a workshop on Distributed Tracing sponsored by [Datadog](http://www.datadoghq.com)

## Prerequisites

* Install ``docker`` and ``docker-compose`` on your system. Please, follow the instructions available
  in the [Docker website](https://www.docker.com/community-edition)
  For Linux environment, it should go like 
  ```bash
  $ sudo curl -sSL https://get.docker.com/ | sh
  $ sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose``
  $ sudo chmod +x /usr/local/bin/docker-compose
  ```
* Get the workshop material ready to play with
  ```bash
  $ git clone https://github.com/DataDog/dd-py-tracing-workshop.git
  $ cd dd-py-tracing-workshop
  ```
* Create a [Datadog Account](https://app.datadoghq.com/signup) and get an ``API_KEY`` for that account (you can create from the [Datadog API page](https://app.datadoghq.com/account/settings#api)). Remember to not share this key with anyone.

## Flask Application

Here's an app that does a simple thing. It tells you what donut to pair with your craft brew. While it is contrived in its purpose,
it probably has something in common with the apps you work on:
* It's a web application that exposes HTTP endpoints.
* To do its job, it must talk to datastores and external services.
* It may need performance improvements.

## Get Started

The application runs in many Docker containers that you can launch using the following command:

```bash
$ sudo DD_API_KEY=<add_your_API_KEY_here> docker-compose up
```

Each Python application runs a Flask server with live-reload so you can update your code without restarting any container.
After executing the command above, you should have running:
* A Flask app ``cafe``, accepting HTTP requests
* A micro-service implemented by a smaller Flask app ``taster``, also accepting HTTP requests
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
ddpytracingworkshop_cafe_1      python cafe.py                   Up      0.0.0.0:5000->5000/tcp
```

Now, let's poke through the app and see how it works.

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


## Step 1 - Instrumenting one single function

In this first step, we'll use basic manual instrumentation to trace one single function from our application. 

First, we configure the agent to make it can receive traces. 
```yaml
# docker-compose.yaml

  agent:
    image: "datadog/agent:latest"
    environment:
      - DD_API_KEY
      - DD_APM_ENABLED=true
      - DD_APM_NON_LOCAL_TRAFFIC=TRUE
    ports: 
      - "8126:8126"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
```

Then, let's instrument the code. The first thing to do is to import and configure tracing capabilities:

```python
# cafe.py

from ddtrace import tracer, config, patch_all;
tracer.configure(hostname='agent', port=8126)
```

After what, we instrument the `beers()` function by adding the tracer decorator.
```python
# cafe.py

@app.route('/beers')
@tracer.wrap(service='beers')
def beers():
```

Now, when you call your webapp for beers `curl -XGET "localhost:5000/beers"`, you see the traces of the underlying `beers()` function in Datadog Trace List [Datadog Trace List](https://app.datadoghq.com/apm/traces) 

When you click (View Trace ->) on your newly tracked service, you see the "details" of the trace. For now, the details are limited to the single span of the `beers` method you just instrumented. One valuable information you find here is the duration of the span.

If you access the [Beer Service Statistics](https://app.datadoghq.com/apm/service/beers/app.beers) page, you also find statistics about all the occurences of calls to that service (try `curl -XGET "localhost:5000/beers"` ten times in a row to populate that statistics. 

This is useful, but you'll need more to observe what's happening in your application and eventually fix or optimize things.

## Step 2 - Access full trace (Automatic Instrumentation)

A good tracing client will unpack, for instance, some of the layers of indirection in ORMs, and give
you a true view of the SQL being executed. This lets us marry the the nice APIs of ORMS with visibility
into what exactly is being executed and how performant it is.

We'll use Datadog's monkey patcher, a tool for safely adding tracing to packages in the import space for both apps `cafe.py` and `taster.py`. This monkey patcher enables OOTB instrumentation for Flask applications, along with other common frameworks in Python.

```python
# cafe.py

from ddtrace import patch_all; 
patch_all(flask=True)
```

```python
# taster.py

from ddtrace import tracer, config, patch_all
tracer.configure(hostname='agent', port=8126) 
config.flask['service_name'] = 'taster' 

patch_all(flask=True)
from flask import Flask, request, jsonify
```

Don't forget to remove the `tracer.wrap()` decorator from `beers()` function, which we added in Step 1 but which is useless now.

The middleware is operating by monkey patching the flask integration to ensure it is:
- Timing requests
- Collecting request-scoped metadata
- Pinning some information to the global request context to allow causal relationships to be registered

Now, if we hit our app, we can see that Datadog has begun to display some information for us. Meaning,
you should be able to see some data in the APM portion of the Datadog application.


## Step 3 - Access full trace (Distributed Tracing)

At the moment I'm writing this workshop, the `requests` [package](http://docs.python-requests.org/en/master/) is not yet auto-instrumented by the monkey patcher (but it's about to come :) ). As a consequence, the traces from `cafe` web application and `taster` micro-service are not associated with each other.

Good pretext to explore what's happening behind the scene with distributed tracing by doing it manually. Indeed, traces can cross boundaries thanks to trace context transiting through HTTP calls headers. 

Here is the corresponding code in the `cafe.py` to inject the trace context in the call to `taster` micro-service:

```python
# cafe.py

from ddtrace.propagation.http import HTTPPropagator

def best_match(beer):
  
    with tracer.trace("best_match") as span:
        
        # [...]

        for candidate in candidates:
            headers = {}
            propagator = HTTPPropagator()
            propagator.inject(span.context,headers)
            try:
                 resp = requests.get("http://taster:5001/taste",
                                     params={"beer": beer.name, "donut": candidate},
                                     timeout=2,headers=headers)
        # [...]
```

The reverse operation of getting the context back from the header in the HTTP call received by `taster` micro-service is done automatically, since the `Flask.request` package is patched along with any other `flask` component.


## Step 4 - Correlate Traces and Logs

Traces are useful material, but sometimes troubleshoot starts with a line of log. Datadog magically enables correlation of traces and logs thanks to a `trace_id`. It's a unique identifier of every single trace, that you can easily report in any log written in that trace.

Let's append our logger format to inherit metadata from trace: `trace_id` and `span_id`.

```python
# cafe.py

patch_all(logging=True)
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
```

```python
# taster.py

patch_all(logging=True)
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
```

We need to configure the agent to collect logs from the docker socket - refer to [agent documentation](https://docs.datadoghq.com/logs/log_collection/docker/?tab=dockercompose)
  
```yaml
# docker-compose.yml

  agent:
    environment:
      - DD_LOGS_ENABLED=true
      - DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true
      - DD_AC_EXCLUDE=name:agent
    volumes:
      - /opt/datadog-agent/run:/opt/datadog-agent/run:rw
  web:
    labels:
      com.datadoghq.ad.logs: '[{"source": "custom_python", "service": "web"}]'
  taster:
    labels:
      com.datadoghq.ad.logs: '[{"source": "custom_python", "service": "taster"}]'

```

And finally update the [Log pipelines](https://app.datadoghq.com/logs/pipelines/) to process these custom-format python logs. Note that there is no need to do it for Agent and Redis Logs, they are automatically recongnized and processes as such.

Create a new pipeline whose custom filter is `source:custotm_python`. Within that pipeline:

* Create a Grok Parser witht the following parsing rule `custom_python_trace %{date("yyyy-MM-dd HH:mm:ss,SSS"):timestamp} %{word:levelname} \[%{word}\] \[%{word}.%{word}:%{integer}] \[dd.trace_id=%{numberStr:dd.trace_id} dd.span_id=%{numberStr:dd.span_id}\] - %{data:message}`,

* Create a Date Remapper with the `timestamp` attribute,

* Create a Status remapper with the `levelname` attribute,

* Ceatet a Trace ID with the `dd.trace_id` attribute.


With that setup, you should now be able: 

* to access logs from a trace - see the Log Panel in the Trace Panel. [See Documentation](https://docs.datadoghq.com/tracing/visualization/trace/?tab=logs)

* to access a trace from a log - see the "Go to Trace" buttom in the Log Panel. [See Documentation](https://docs.datadoghq.com/logs/explorer/?tab=logstream#log-panel)  

## Step 5 - Trace Search

Trace search deactivated by default in Datadog. You should explictely enable it, service by service. 

Adding this environment variable in the datadog agent docker configures the agent to send trace events for the flask service.

```
# docker-compose.yml

  agent:
    image: "datadog/agent:latest"
    environment:
      - DD_APM_ANALYZED_SPANS=cafe|flask.request=1,taster|flask.request=1 
```

After this, you can now search for specific traces in the [Trace Search](https://app.datadoghq.com/apm/search), and access advanced [Analytics](https://app.datadoghq.com/apm/search/analytics) capabilities as well.


## Step 6  - Optimize Endpoint

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
        resp = requests.get(
            "http://taster:5001/taste",
            params={"beer": beer.name, "donuts": candidates},
            timeout=2,
            headers=headers,
        )
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
