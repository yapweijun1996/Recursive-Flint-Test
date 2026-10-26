def paginate(items, page, size):
    if isinstance(page, bool) or not isinstance(page, int) or isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("page and size must be integers")
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive integers")
    total = len(items)
    pages = (total + size - 1) // size
    start = (page - 1) * size
    end = start + size
    return {
        "items": items[start:end],
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
    }