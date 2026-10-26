def paginate(items, page, size):
    if isinstance(page, bool) or not isinstance(page, int):
        raise TypeError("page must be an integer")
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an integer")
    if page < 1:
        raise ValueError("page must be at least 1")
    if size < 1:
        raise ValueError("size must be at least 1")

    total = len(items)
    pages = (total + size - 1) // size
    start = (page - 1) * size
    return {
        "items": items[start:start + size],
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
    }
