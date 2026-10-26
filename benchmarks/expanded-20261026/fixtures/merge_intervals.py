def merge_intervals(intervals):
    intervals.sort()
    merged = []
    for interval in intervals:
        if merged and interval[0] < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], interval[1])
        else:
            merged.append(interval)
    return merged
