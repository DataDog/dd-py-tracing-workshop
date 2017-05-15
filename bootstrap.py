if __name__ == '__main__':
    from app import db, Beer, Donut
    db.create_all()

    # create beers
    db.session.add(Beer("IPA"))
    db.session.add(Beer("Pilsner"))
    db.session.add(Beer("Lager"))
    db.session.add(Beer("Stout"))
    db.session.commit()

    # create donuts
    db.session.add(Donut("Jelly"))
    db.session.add(Donut("Glazed"))
    db.session.add(Donut("Chocolate"))
    db.session.add(Donut("Bavarian"))
    db.session.commit()
