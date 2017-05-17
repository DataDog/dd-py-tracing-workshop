from __future__ import print_function
from flask import Flask, request, jsonify
from flask_sqlalchemy import  SQLAlchemy

import random
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

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
    # Get beer name from params
    name = request.args.get('name')
    beer = Beer.query.filter_by(name=name).first()
    donuts = Donut.query.all()

    match = best_match(beer)
    return jsonify(match=match)


class DonutDB(object):
    """
    >>> db = DonutDB.instance()
    >>> db.get_rank("jelly")
    >>> db.set_rank("jelly", 7.5)
    >>> db.get_tags("jelly")
    >>> db.set_tags("jelly", ["kinda_sweet", "gooey". "best served warm"])
    >>> db.best_match("IPA")
    >>> db._filter("jelly", query_string)

    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_optimal_sugar_level(self, hops):
        return random.randint(1,10)

    def get_by_sugar_level(self, sugar, limit=10):
        return ["jelly"]

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
        resp = requests.get("http://taster:5001/taste", params={"beer": beer, "donut": candidate}) 
        score = resp.json()["score"]
        if score > max_score:
            max_score = score
            best_match = candidate

    return candidate

if __name__ == '__main__':
    db.create_all()
    db.session.add(Beer("ipa", 7))
    db.session.commit()

    app.run(host="0.0.0.0", debug=True)
