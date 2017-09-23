from flask import Flask
from ddtrace import tracer
from models import Beer, Donut, db


# configure the tracer so that it reaches the Datadog Agent
# available in another container
tracer.configure(hostname='agent')


def create_app():
    """Create a Flask application"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    initialize_database(app, db)
    return app


def initialize_database(app, db):
    """Drop and restore database in a consistent state"""
    with app.app_context():
        db.drop_all()
        db.create_all()

        # create beers
        db.session.add(Beer('ipa', 10))
        db.session.add(Beer('pilsner', 8))
        db.session.add(Beer('lager', 8))
        db.session.add(Beer('stout', 7))
        db.session.commit()

        # create donuts
        db.session.add(Donut('jelly'))
        db.session.add(Donut('glazed'))
        db.session.add(Donut('chocolate'))
        db.session.add(Donut('bavarian'))
        db.session.commit()
