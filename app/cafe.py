# from ddtrace import tracer, config, patch_all; # STEP 01
# tracer.configure(hostname='agent', port=8126) # STEP 01 
# config.flask['service_name'] = 'cafe' # STEP 01

# patch_all(flask=True) # STEP 02
from flask import request, jsonify

# from ddtrace.propagation.http import HTTPPropagator # STEP 03

# patch_all(logging=True) # STEP 04
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          #'[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] ' # STEP 04
          '- %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)
log.level = logging.INFO

import requests

from models import Beer, Donut
from stats import DonutStats
from bootstrap import create_app

#---------------------------------------#

# initialize Flask application
app = create_app()

# some simple routes

@app.route('/ping')
# @tracer.wrap('ping',service='cafe') # STEP 01 (to be re-commented in STEP 02)
def ping():
    log.info('ping!')
    return "200 OK"

@app.route('/beers')
def beers():
    log.info('List all beers')
    # Get beers from the database
    return jsonify(beers=[b.serialize() for b in Beer.query.all()])


@app.route('/donuts')
def donuts():
    log.info('List all donuts')
    return jsonify(donuts=[d.serialize() for d in Donut.query.all()])


@app.route('/beers/<name>')
def beer(name):
    log.info('Get a beer by name')
    return jsonify(Beer.query.filter_by(name=name).first().serialize())


@app.route('/donuts/<name>')
def donut(name):
    log.info('Get a donutt by name')
    return jsonify(Donut.query.filter_by(name=name).first().serialize())


@app.route('/pair/beer')
def pair():

    name = request.args.get('name')
    beer = Beer.query.filter_by(name=name).first()

    log.info('Finding the best donut for '+beer.name)

    # force a query
    Donut.query.all()

    match = best_match(beer)
    log.info('And the best donut for '+beer.name+' is ...'+match+'!!')
    return jsonify(match=match)


def get_candidates(beer):
    
    db = DonutStats.instance()

    # find our optimal sugar level Donuts above or below this level
    # will certainly not be a good match
    optimal_sugar_level = db.get_optimal_sugar_level(beer.hops)
    return db.get_by_sugar_level(optimal_sugar_level, limit=10)


def best_match(beer):
   
    # with tracer.trace("best_match") as span: # STEP 03
   
        # get a list of donuts that match sugar content for beer
        candidates = get_candidates(beer)

        # send the remaining candidates to our taster and pick the best
        max_score = -1
        best_match = None

        for candidate in candidates:
            # headers = {} # STEP 03
            # propagator = HTTPPropagator() # STEP 03
            # propagator.inject(span.context,headers) # STEP 03
            try:
                 log.info('Trying '+beer.name+' with '+candidate)
                 resp = requests.get(
                     "http://taster:5001/taste",
                     params={"beer": beer.name, "donut": candidate},
                     timeout=2,
                     # headers=headers # STEP 03
                 )
            except requests.exceptions.Timeout:
                continue

            score = resp.json()["score"]
            if score > max_score:
                max_score = score
                best_match = candidate

        return best_match # to be reindented along with "with" statement in STEP 03

