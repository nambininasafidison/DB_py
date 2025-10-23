import json
try:
    import redis
    _REDIS_AVAILABLE = True
except Exception:
    redis = None
    _REDIS_AVAILABLE = False


class RedisCache:
    """Cache wrapper that uses redis if available, otherwise an in-memory dict fallback.

    This allows running the project without installing or running a Redis server during
    development or on systems where the user doesn't want to install packages.
    """
    def __init__(self, host, port):
        self._store = {}
        self.client = None
        if _REDIS_AVAILABLE:
            try:
                self.client = redis.StrictRedis(host=host, port=port, decode_responses=True)
                self.client.ping()
            except Exception:
                self.client = None

    def get(self, key):
        if self.client:
            try:
                data = self.client.get(key)
                return json.loads(data) if data else None
            except Exception:
                return None
        return self._store.get(key)

    def set(self, key, value):
        if self.client:
            try:
                self.client.set(key, json.dumps(value))
                return
            except Exception:
                pass
        self._store[key] = value