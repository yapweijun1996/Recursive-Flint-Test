def merge_intervals(intervals):
    merged = []
    for interval in sorted(intervals, key=lambda x: (x[0], x[1])):
        start, end = interval[0], interval[1]
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
