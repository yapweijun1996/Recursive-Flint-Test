"""Frozen repair tasks and independent behavioral checks for the Pi benchmark."""

import copy
import random

TASKS = {
    'merge_intervals': {
        'contract': 'Implement merge_intervals(intervals). Input is a list of valid closed intervals [start,end] on the real number line, with integer endpoints and start<=end. Merge exactly when next_start<=current_end; touching means a shared endpoint, not adjacent integers. For example [[1,2],[2,4]] becomes [[1,4]], but [[1,2],[3,4]] stays separate. Return sorted fresh lists and never mutate the input. Empty input returns [].',
        'buggy': '''def merge_intervals(intervals):
    intervals.sort()
    merged = []
    for interval in intervals:
        if merged and interval[0] < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], interval[1])
        else:
            merged.append(interval)
    return merged
''',
        'reference': '''def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged
''',
    },
    'pagination': {
        'contract': 'Implement paginate(items,page,size). page and size must be integers (booleans are invalid), both >=1. Invalid types raise TypeError; nonpositive integers raise ValueError. Return a dict with keys items,page,size,total,pages,has_next. Pages are 1-based; pages is ceil(total/size), including zero for empty input. Pages beyond the end return items=[],has_next=False. Do not mutate items. Retain all existing return keys.',
        'buggy': '''def paginate(items, page, size):
    start = page * size
    total = len(items)
    return {"items": items[start:start + size], "page": page,
            "size": size, "total": total, "pages": total // size,
            "has_next": page <= total // size}
''',
        'reference': '''def paginate(items, page, size):
    if type(page) is not int or type(size) is not int:
        raise TypeError("page and size must be integers")
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive")
    total = len(items)
    start = (page - 1) * size
    return {"items": list(items[start:start + size]), "page": page,
            "size": size, "total": total, "pages": (total + size - 1) // size,
            "has_next": page * size < total}
''',
    },
    'ttl_lru': {
        'contract': 'Repair TTLCache(capacity,clock), preserving put(key,value,ttl) and get(key,default=None). capacity is a positive integer; clock is an injected callable returning numeric time. A key is expired when now>=its expiry. get returns default for absent/expired keys and makes a live hit most recently used. put updates expiry and makes key most recent. ttl<=0 deletes that key and stores nothing. Before enforcing capacity on put, purge ALL expired entries so live entries are not evicted unnecessarily. Evict the least recently used LIVE key if still over capacity. Do not add dependencies beyond the Python standard library.',
        'buggy': '''from collections import OrderedDict

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
''',
        'reference': '''from collections import OrderedDict

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
''',
    },
}


def check_candidate(task, namespace):
    checks = []

    def check(label, action):
        try:
            action()
            checks.append({'name': label, 'passed': True})
        except Exception as error:
            checks.append({'name': label, 'passed': False, 'error': type(error).__name__ + ': ' + str(error)[:240]})

    def equal(actual, expected):
        assert actual == expected, f'Expected {expected!r}, got {actual!r}'

    if task == 'merge_intervals':
        function = namespace['merge_intervals']
        fixed = [([], []), ([[1, 2]], [[1, 2]]),
                 ([[4, 8], [1, 4]], [[1, 8]]),
                 ([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
                 ([[1, 9], [2, 4], [9, 10]], [[1, 10]]),
                 ([[0, 0], [0, 0], [-2, 0]], [[-2, 0]])]
        for index, (intervals, expected) in enumerate(fixed):
            check(f'fixed-{index}', lambda a=intervals, b=expected: equal(function(copy.deepcopy(a)), b))

        def mutation_check():
            original = [[4, 6], [1, 5]]
            saved = copy.deepcopy(original)
            result = function(original)
            equal(original, saved)
            result[0][0] = -999
            equal(original, saved)
        check('input-and-output-aliasing', mutation_check)

        def random_check(seed):
            rng = random.Random(seed)
            original = []
            for _ in range(rng.randrange(15)):
                start = rng.randrange(-10, 11)
                original.append([start, start + rng.randrange(6)])
            saved = copy.deepcopy(original)
            result = function(original)
            equal(original, saved)
            # Half-integer coverage detects real gaps between closed intervals.
            coverage = lambda values: {point for start, end in values for point in range(start * 2, end * 2 + 1)}
            equal(coverage(result), coverage(saved))
            assert all(result[i][1] < result[i + 1][0] for i in range(len(result) - 1))
            equal(function(copy.deepcopy(result)), result)
        for seed in range(30):
            check(f'generated-{seed}', lambda seed=seed: random_check(seed))

    elif task == 'pagination':
        function = namespace['paginate']
        for total in [0, 1, 2, 7, 10, 11]:
            for size in [1, 2, 4, 10]:
                for page in [1, 2, 4, 20]:
                    def page_check(total=total, size=size, page=page):
                        items = list(range(total))
                        saved = items[:]
                        result = function(items, page, size)
                        expected_items = [value for index, value in enumerate(items) if (page - 1) * size <= index < page * size]
                        pages = len([index for index in range(total) if index % size == 0])
                        equal(result, {'items': expected_items, 'page': page, 'size': size,
                                       'total': total, 'pages': pages, 'has_next': page < pages})
                        equal(items, saved)
                    check(f'page-{total}-{size}-{page}', page_check)
        for page, size, expected_error in [(True, 2, TypeError), (1, False, TypeError),
                                            ('1', 2, TypeError), (1, 1.5, TypeError),
                                            (None, 2, TypeError), (0, 2, ValueError),
                                            (-1, 2, ValueError), (1, 0, ValueError)]:
            def invalid_check(page=page, size=size, expected_error=expected_error):
                try:
                    function([1, 2], page, size)
                except expected_error:
                    return
                raise AssertionError('Required validation exception was not raised')
            check(f'invalid-{page!r}-{size!r}', invalid_check)

    elif task == 'ttl_lru':
        cache_class = namespace['TTLCache']

        def boundary():
            now = [0]
            cache = cache_class(2, lambda: now[0])
            cache.put('a', 7, 2)
            now[0] = 2
            equal(cache.get('a', 'missing'), 'missing')
        check('expiry-boundary', boundary)

        def lru_hit():
            cache = cache_class(2, lambda: 0)
            cache.put('a', 1, 10)
            cache.put('b', 2, 10)
            equal(cache.get('a'), 1)
            cache.put('c', 3, 10)
            equal(cache.get('b'), None)
            equal(cache.get('a'), 1)
            equal(cache.get('c'), 3)
        check('live-hit-refreshes-lru', lru_hit)

        def expired_before_eviction():
            now = [0]
            cache = cache_class(2, lambda: now[0])
            cache.put('a', 1, 100)
            cache.put('b', 2, 1)
            now[0] = 2
            cache.put('c', 3, 100)
            equal(cache.get('a'), 1)
            equal(cache.get('c'), 3)
        check('purge-expired-before-eviction', expired_before_eviction)

        def nonpositive_ttl():
            cache = cache_class(2, lambda: 0)
            cache.put('a', 1, 10)
            cache.put('a', 2, 0)
            equal(cache.get('a'), None)
            cache.put('b', 3, -1)
            equal(cache.get('b', 'x'), 'x')
        check('nonpositive-ttl-deletes', nonpositive_ttl)

        def simulation(seed):
            rng = random.Random(seed)
            now = [0]
            capacity = 1 + seed % 4
            cache = cache_class(capacity, lambda: now[0])
            oracle, sequence = {}, 0
            for _ in range(150):
                sequence += 1
                now[0] += rng.choice([0, 0, 1, 2])
                key = rng.choice('abcde')
                if rng.randrange(2):
                    ttl = rng.randrange(-1, 8)
                    value = rng.randrange(100)
                    cache.put(key, value, ttl)
                    oracle = {k: v for k, v in oracle.items() if now[0] < v[1]}
                    if ttl <= 0:
                        oracle.pop(key, None)
                    else:
                        oracle[key] = (value, now[0] + ttl, sequence)
                        if len(oracle) > capacity:
                            del oracle[min(oracle, key=lambda k: oracle[k][2])]
                else:
                    if key in oracle and now[0] >= oracle[key][1]:
                        del oracle[key]
                    expected = oracle[key][0] if key in oracle else 'missing'
                    equal(cache.get(key, 'missing'), expected)
                    if key in oracle:
                        value, expiry, _ = oracle[key]
                        oracle[key] = (value, expiry, sequence)
        for seed in range(15):
            check(f'stateful-{seed}', lambda seed=seed: simulation(seed))
    else:
        raise ValueError('Unknown repair task')
    return {'passed': all(item['passed'] for item in checks), 'checks': len(checks),
            'passed_checks': sum(item['passed'] for item in checks),
            'failures': [item for item in checks if not item['passed']]}
