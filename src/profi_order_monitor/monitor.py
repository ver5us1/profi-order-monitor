"""File polling and confirmed delivery of previously unknown order IDs."""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from profi_order_monitor.config import Settings, initialize
from profi_order_monitor.notifications.messages import notification_batches
from profi_order_monitor.notifications.telegram import TelegramClient
from profi_order_monitor.parsing import find_matching_ids, has_board_payload
from profi_order_monitor.storage.files import load_state, read_json, save_state

logger = logging.getLogger(__name__)


def process_snapshot(
    data: object,
    known_ids: set[str],
    state_file: Path,
    send_message: Callable[[str], bool],
) -> bool:
    if not has_board_payload(data):
        return True
    ids = find_matching_ids(data)
    new_ids = ids - known_ids
    for batch_ids, text in notification_batches(new_ids):
        if not send_message(text):
            return False
        # Save only IDs from a confirmed notification. Commit each batch separately.
        updated = known_ids | batch_ids
        save_state(state_file, updated)
        known_ids.update(batch_ids)
    return True


def run_monitor(settings: Settings) -> None:
    if not settings.telegram_token or settings.telegram_token in {"replace_me", "ВСТАВЬ_ТОКЕН_СЮДА"}:
        raise ValueError("Не задан TELEGRAM_BOT_TOKEN в .env")
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    known_ids = load_state(settings.state_file)
    client = TelegramClient(settings)
    processed = set()
    retry_after = {}
    logger.info("Монитор запущен; известных ID: %s", len(known_ids))
    while True:
        files = []
        for path in settings.downloads_dir.glob("*.json"):
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            files.append((stat.st_mtime_ns, path, stat.st_size))
        for modified, path, size in sorted(files):
            fingerprint = (path.name, modified, size)
            if fingerprint in processed or time.monotonic() < retry_after.get(fingerprint, 0):
                continue
            try:
                data = read_json(path)
                completed = process_snapshot(data, known_ids, settings.state_file, client.send_message)
                if completed:
                    processed.add(fingerprint)
                    retry_after.pop(fingerprint, None)
                else:
                    retry_after[fingerprint] = time.monotonic() + settings.retry_seconds
                    logger.warning("Доставка не подтверждена; файл будет проверен повторно")
            except Exception as error:
                retry_after[fingerprint] = time.monotonic() + settings.retry_seconds
                logger.warning("Обработка %s: %s", path.name, type(error).__name__)
        time.sleep(settings.poll_seconds)


def main() -> None:
    settings = initialize()
    try:
        run_monitor(settings)
    except KeyboardInterrupt:
        logger.info("Монитор остановлен")


if __name__ == "__main__":
    main()
