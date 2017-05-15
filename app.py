from __future__ import print_function

from flask import Flask
from flask_sqlalchemy import  SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/test.db'
db = SQLAlchemy(app)

class Beer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)

    def __init__(self, name):
        self.name = name

class Donut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)

    def __init__(self, name):
        self.name = name

@app.route('/ping')
def fast_route():
    return "200 OK"

@app.route('/beers')
def slow_route():
    # Get beers from the database
    Beer.query.all()
    return "200 OK"

@app.route('/donuts')
def slower_route():
    # Get donuts from the database
    Donut.query.all()
    return "200 OK"

@app.route('/pair/beer')
def pair():
    # Get beer name from params
    beers = Beer.query(name=name)
    donuts = Donut.query.all()

    best_match(donuts, beer)
    return "200 OK"

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
