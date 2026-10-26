def paginate(items, page, size):
    if type(page) is not int or type(size) is not int:
        raise TypeError("page and size must be integers")
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive")
    total = len(items)
    start = (page - 1) * size
    return {"items": list(items[start:start + size]), "page": page,
            "size": size, "total": total, "pages": (total + size - 1) // size,
            "has_next": page * size < total}
