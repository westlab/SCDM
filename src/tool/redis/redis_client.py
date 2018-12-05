import redis

class RedisClient:
    # assume key:   int
    # assume field: str
    # assume value: int
    def __init__(self):
        self._cli = redis.Redis(host='127.0.0.1', port=6379, db=0)

    def hvals(self, key):
        return self._cli.hvals(key)

    def hgetall(self, key):
        return {k.decode(): int(v) for k,v in self._cli.hgetall(key).items()}

