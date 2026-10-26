from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, clock):
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("capacity must be a positive integer")
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.clock = clock
        self.data = OrderedDict()

    def get(self, key, default=None):
        if key not in self.data:
            return default

        now = self.clock()
        value, expiry = self.data[key]
        if now >= expiry:
            del self.data[key]
            return default

        self.data.move_to_end(key)
        return value

    def put(self, key, value, ttl):
        if ttl <= 0:
            self.data.pop(key, None)
            return

        now = self.clock()
        expired = [stored_key for stored_key, (_, expiry) in self.data.items() if now >= expiry]
        for stored_key in expired:
            del self.data[stored_key]

        self.data[key] = (value, now + ttl)
        self.data.move_to_end(key)

        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
