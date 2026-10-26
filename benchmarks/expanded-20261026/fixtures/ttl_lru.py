from collections import OrderedDict

class TTLCache:
    def __init__(self, capacity, clock):
        self.capacity = capacity
        self.clock = clock
        self.data = OrderedDict()

    def get(self, key, default=None):
        if key not in self.data:
            return default
        value, expiry = self.data[key]
        if expiry < self.clock():
            del self.data[key]
            return default
        return value

    def put(self, key, value, ttl):
        self.data[key] = (value, self.clock() + ttl)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
