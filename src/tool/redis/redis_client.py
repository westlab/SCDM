import redis

class RedisClient:
    def __init__(self):
        self._cli = redis.Redis(host='127.0.0.1', port=6379, db=0)

    def hvals(self, key):
        return self._cli.hvals(key)

