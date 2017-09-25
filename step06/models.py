from flask_sqlalchemy import SQLAlchemy


# don't initialize the SQLAlchemy immediately
db = SQLAlchemy()


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
            'id': self.id,
            'name': self.name,
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
            'id': self.id,
            'name': self.name,
        }
