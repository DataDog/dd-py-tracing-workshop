from __future__ import print_function
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import  SQLAlchemy

import random
import requests
import redis

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Our data model
class Beer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    brewer = db.Column(db.String(80))

    # A hoppy rating from 1-10
    hops = db.Column(db.Integer)

    def __init__(self, name, hops):
        self.name = name
        self.hops = hops

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }

class Donut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))

    # A sugar rating from 1-10
    sugar = db.Column(db.Integer)

    def __init__(self, name):
        self.name = name

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }


# Some simple routes

@app.route('/ping')
def ping():
    """
    A health check
    """
    return "200 OK"

@app.route('/beers')
def beers():
    """
    List all beers
    """
    # Get beers from the database
    return jsonify(beers=[b.serialize() for b in Beer.query.all()])

@app.route('/donuts')
def donuts():
    """
    List all donuts
    """
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

# And some complex ones

@app.route('/pair/beer')
def pair():
    name = request.args.get('name')
    beer = Beer.query.filter_by(name=name).first()
    donuts = Donut.query.all()
    match = best_match(beer)

    return jsonify(match=match)


class DonutDB(object):
    """
    >>> db = DonutDB.instance()
    >>> db.get_optimal_sugar_level(7)
    >>> db.get_by_sugar_level(7, limit=4)
    """
    _instance = None

    def __init__(self):
        self.redis = redis.StrictRedis(host="redis")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_optimal_sugar_level(self, hops):
        opt = self.redis.get("optimal_sugar_level_for_hops_%s" % hops)
        if not opt:
            opt = random.randint(1,10)
        return opt

    def get_by_sugar_level(self, sugar, limit=10):
        opt = self.redis.get("donuts_by_sugar_level_%s" % sugar)
        if not opt:
            opt = ["jelly", "glazed", "chocolate", "bavarian"]
        return opt

def best_match(beer):
    db = DonutDB.instance()

    # Find our optimal sugar level
    # Donuts above or below this level will certainly not
    # be a good match.
    optimal_sugar_level = db.get_optimal_sugar_level(beer.hops)
    candidates = db.get_by_sugar_level(optimal_sugar_level, limit=10)

    # Send the remaining candidates to our taster
    # and pick the best
    max_score = -1
    best_match = None

    for candidate in candidates:
        try:
            resp = requests.get("http://taster:5001/taste", params={"beer": beer.name, "donut": candidate}, timeout=2)
        except requests.exceptions.Timeout:
            continue

        score = resp.json()["score"]
        if score > max_score:
            max_score = score
            best_match = candidate

    return best_match

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
