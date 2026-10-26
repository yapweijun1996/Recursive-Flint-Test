from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, clock):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.clock = clock
        self.data = OrderedDict()

    def get(self, key, default=None):
        now = self.clock()
        if key not in self.data:
            return default

        value, expiry = self.data[key]
        if now >= expiry:
            del self.data[key]
            return default

        self.data.move_to_end(key)
        return value

    def put(self, key, value, ttl):
        now = self.clock()
        if ttl <= 0:
            self.data.pop(key, None)
            return

        expired = [stored_key for stored_key, (_, expiry) in self.data.items() if now >= expiry]
        for expired_key in expired:
            del self.data[expired_key]

        self.data[key] = (value, now + ttl)
        self.data.move_to_end(key)

        if len(self.data) > self.capacity:
            self.data.popitem(last=False)