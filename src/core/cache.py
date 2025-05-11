import json
import redis

class RedisCache:
    def __init__(self, host, port):
        self.client = redis.StrictRedis(host=host, port=port, decode_responses=True)

    def get(self, key):
        data = self.client.get(key)
        return json.loads(data) if data else None

    def set(self, key, value):
        self.client.set(key, json.dumps(value))