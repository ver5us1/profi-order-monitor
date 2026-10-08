"""Read order IDs only from the expected board structure."""

from collections.abc import Iterator


def board_lists(data: object) -> Iterator[list]:
    if isinstance(data, dict):
        inner = data.get("data")
        board = inner.get("boSearchBoardItems") if isinstance(inner, dict) else None
        items = board.get("items") if isinstance(board, dict) else None
        if isinstance(items, list):
            yield items
        for value in data.values():
            if isinstance(value, (dict, list)):
                yield from board_lists(value)
    elif isinstance(data, list):
        for value in data:
            if isinstance(value, (dict, list)):
                yield from board_lists(value)


def extract_ids(data: object) -> set[str]:
    if not isinstance(data, dict):
        return set()
    inner = data.get("data")
    board = inner.get("boSearchBoardItems") if isinstance(inner, dict) else None
    items = board.get("items") if isinstance(board, dict) else None
    if not isinstance(items, list):
        return set()
    return item_ids(items)


def item_ids(items: list) -> set[str]:
    result = set()
    for item in items:
        value = item.get("id") if isinstance(item, dict) else None
        if type(value) not in {str, int}:
            continue
        value = str(value).strip()
        if value:
            result.add(value)
    return result


def find_matching_ids(data: object) -> set[str]:
    result = set()
    for items in board_lists(data):
        result.update(item_ids(items))
    return result


def has_board_payload(data: object) -> bool:
    return next(board_lists(data), None) is not None
