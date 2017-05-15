if __name__ == '__main__':
    from app import db, Beer, Donut
    db.create_all()

    # create beers
    db.session.add(Beer("ipa"))
    db.session.add(Beer("pilsner"))
    db.session.add(Beer("lager"))
    db.session.add(Beer("stout"))
    db.session.commit()

    # create donuts
    db.session.add(Donut("jelly"))
    db.session.add(Donut("glazed"))
    db.session.add(Donut("chocolate"))
    db.session.add(Donut("bavarian"))
    db.session.commit()
