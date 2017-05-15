## A sample app in Flask begging to be traced


## Prerequisites
- `docker`
- `docker-compose`
- `python`

[Docker install for Mac](https://www.docker.com/docker-mac)
[Docker install for Windows](TODO)


## Get started
Set your Datadog API key in the docker-compose.yml file

Now start up the sample app
```
$ docker-compose up

# bootstrap our database
$ python bootstrap.py
```

## Step 1

We have an app that lets us find good pairings of beer and donuts.
Let's look at all the beers we have available
`curl -XGET localhost:5000/beers`

And now let's look at all the flavors of donuts we have available
`curl -XGET localhost:5000/donuts`

We can grab a beer by name
`curl -XGET localhost:5000/beer/ipa`

and a donut by name
`curl -XGET localhost:5000/donut/jelly`

Things feel pretty speedy. But happens when we try to find a donut that pairs well with our favorite beer?

`curl -XGET localhost:5000/pair/beer?name=ipa`

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
In fact we have tracing for a ton of useful libraries right out of the box. Let's enable these via autopatching

As datadog shows us we seem to be doing a bucket load of SQL queries for finding
good beer-donut pairings!

A single beer can pair with many donuts! But do we need to issue a query for each of those donuts?

This is a variant of the N+1 problem that most of you will come across at one point or another in your experience with ORMs.
SQLAlchemy's lazy-loading makes this a very easy trap to fall into

Let's see how we can make this query better

## Step 7 - Rearchitect pair route to do fewer DB calls
Rather than lazy-loading donuts that pair can with Beer X. Let's just eagerly load all of them!

with some custom sql
```
SELECT 'donuts'.* FROM 'donuts' WHERE 'donuts'.'id' IN (1,2,3,4,5)
```

How does our route look now? Faster?

## Step 8 - Rearchitect pair route to use a cache
Our pairing request consistently takes about 200ms. Can we do better?
Our list of beers and donuts probably won't change frequently. So for a popular beer
it makes sense to cache its donut pairing so other users will benefit. Let's give that a shot, using a redis cache (part of the same docker compose setup)

How do our traces look now?

## Step 9 - Nearly Done!
