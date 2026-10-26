def paginate(items, page, size):
    start = page * size
    total = len(items)
    return {"items": items[start:start + size], "page": page,
            "size": size, "total": total, "pages": total // size,
            "has_next": page <= total // size}
