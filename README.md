## A sample app in Flask begging to be traced


## Prerequisites
- `docker`


## Get started
Start up the sample app along with the trace-agent
```
$ docker-compose up
```

## Step 1

We have an app that lets us find good pairings of beer and donuts.
Let's look at all the beers we have available
`curl -XGET localhost:8080/beers`

And now let's look at all the flavors of donuts we have available
`curl -XGET localhost:8080/donuts`

We can grab a beer by name
`curl -XGET localhost:8080/beer/ipa`

and a donut by name
`curl -XGET localhost:8080/donut/jelly`

Things feel pretty speedy. But happens when we try to find a donut that pairs well with our favorite beer?

`curl -XGET localhost:8080/pair/beer?name=ipa`

It feels slow !! How much slower? Good q

## Step 2 - add timing to individual routes

Anyone ever had to time a python function before? There are several ways to do it

With a decorator:
TODO Code sample

With a context manager:
TODO Code sample

Let's choose our favorite one of these and wire these into the app.
Every time a route gets hit, let's have it dump helpful debug information to the log.

This seems like useful information to have enabled by default. How do we do that?

## Step 3 - Middleware
Python web frameworks all support the concept of middleware. Arbitrary code that
is run at the beginning and end of every HTTP request loop. This is an ideal place
to plugin telemetry

## Step 4 - ddtrace patch Flask
We've done the hard work of adding Middleware for you let's look at what it does.
And here's how we can patch it
```from ddtrace import monkey; monkey.patch(flask=True)```

Now let's restart our app, and pull up datadog. Ping your app a few times. And there you go.

## Step 5 - ddtrace patch sqlalchemy
Our spans look a bit sparse without real info about DB calls, let's add in some custom wrappers around the db

```
with tracer.trace("db.query", service="db") as span:
    span.Resource = "Beer.query.all"
    Beer.query.all()
```

Seem onerous to do this everywhere - luckily ddtrace will patch all calls for you
```from ddtrace import monkey; monkey.patch(sqlalchemy=True)```

## Step 6 - Autopatch

## Step 7 - Rearchitect pair route to use a cache

## Step 8 - Identify cache query in a for loop

## Step 9 - Nearly Done!
