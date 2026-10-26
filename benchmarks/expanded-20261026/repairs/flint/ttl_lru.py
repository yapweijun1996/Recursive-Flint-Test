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
        if self.clock() >= expiry:
            del self.data[key]
            return default
        self.data.move_to_end(key)
        return value

    def put(self, key, value, ttl):
        if ttl <= 0:
            self.data.pop(key, None)
            return
        self.data[key] = (value, self.clock() + ttl)
        self.data.move_to_end(key)
        now = self.clock()
        expired = [k for k, (_, e) in self.data.items() if now >= e]
        for k in expired:
            del self.data[k]
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)