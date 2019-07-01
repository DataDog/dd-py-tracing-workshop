import redis
import random


class DonutStats(object):
    """
    >>> db = DonutStats.instance()
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
            opt = random.randint(1, 10)
        return opt

    def get_by_sugar_level(self, sugar, limit=10):
        opt = self.redis.get("donuts_by_sugar_level_%s" % sugar)
        if not opt:
            opt = ["jelly", "glazed", "chocolate", "bavarian"]
        return opt
