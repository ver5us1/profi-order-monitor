"""The original notification format, with bounded batches."""


def build_message(new_ids: set[str]) -> str:
    lines = ["🔔 НОВЫЕ ЗАКАЗЫ", "", f"Найдено новых: {len(new_ids)}", ""]
    lines.extend(f"🆔 {item_id}" for item_id in sorted(new_ids))
    return "\n".join(lines)


def notification_batches(new_ids: set[str]):
    batch = set()
    for item_id in sorted(new_ids):
        candidate = batch | {item_id}
        units = len(build_message(candidate).encode("utf-16-le")) // 2
        if units > 4000:
            if not batch:
                raise ValueError("ID слишком длинный для Telegram-уведомления")
            yield batch, build_message(batch)
            batch = {item_id}
            if len(build_message(batch).encode("utf-16-le")) // 2 > 4000:
                raise ValueError("ID слишком длинный для Telegram-уведомления")
        else:
            batch = candidate
    if batch:
        yield batch, build_message(batch)
