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
        now = self.clock()
        for old_key in list(self.data):
            if now >= self.data[old_key][1]:
                del self.data[old_key]
        if ttl <= 0:
            self.data.pop(key, None)
            return
        self.data[key] = (value, now + ttl)
        self.data.move_to_end(key)
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)
