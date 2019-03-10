
# STEP 01 - Import Tracing Solution
from ddtrace import tracer 
tracer.configure(hostname='agent', port=8126)  

# STEP 02 - Inject traces in logs
from ddtrace import patch_all;
patch_all(logging=True)
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          # STEP 02 - Define custom log format
          '[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)
log.level = logging.INFO


# STEP 03 - Automatically Instrument Flask
from ddtrace import patch_all;
patch_all(Flask=True)

from flask import request, jsonify
from bootstrap import create_app

import requests

from models import Beer, Donut
from stats import DonutStats


# initialize Flask application
app = create_app()

# some simple routes
@app.route('/ping')
def ping():
    """
    A health check
    """
    log.info('health check OK')
    return "200 OK"

@app.route('/beers')
# STEP 01 - Basic Tracing 
# @tracer.wrap() command to be commented in step 03 and after
# @tracer.wrap(service='beers')
def beers():
    """
    List all beers
    """
    log.info('List all Beers')
    # Get beers from the database
    return jsonify(beers=[b.serialize() for b in Beer.query.all()])


@app.route('/donuts')
def donuts():
    """
    List all donuts
    """
    log.info('List all Donuts')
    return jsonify(donuts=[d.serialize() for d in Donut.query.all()])


@app.route('/beers/<name>')
def beer(name):
    """
    Get a beer by name
    """
    return jsonify(Beer.query.filter_by(name=name).first().serialize())


@app.route('/donuts/<name>')
def donut(name):
    """
    Get a donut by name
    """
    return jsonify(Donut.query.filter_by(name=name).first().serialize())


@app.route('/pair/beer')
def pair():
    """A complex endpoint that makes a request to another Python service"""
    name = request.args.get('name')
    beer = Beer.query.filter_by(name=name).first()

    # force a query
    Donut.query.all()

    match = best_match(beer)
    return jsonify(match=match)


def get_candidates(beer):
    """
    returns a list of donuts based on hops level of beer
    """
    db = DonutStats.instance()

    # find our optimal sugar level Donuts above or below this level
    # will certainly not be a good match
    optimal_sugar_level = db.get_optimal_sugar_level(beer.hops)
    return db.get_by_sugar_level(optimal_sugar_level, limit=10)


def best_match(beer):
    """
    returns a single donut matched to the hops level of a beer
    """
    # get a list of donuts that match sugar content for beer
    candidates = get_candidates(beer)

    # send the remaining candidates to our taster and pick the best
    max_score = -1
    best_match = None

    for candidate in candidates:
        try:
            resp = requests.get(
                "http://taster:5001/taste",
                params={"beer": beer.name, "donut": candidate},
                timeout=2,
            )
        except requests.exceptions.Timeout:
            continue

        score = resp.json()["score"]
        if score > max_score:
            max_score = score
            best_match = candidate

    return best_match
