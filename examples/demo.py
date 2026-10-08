"""Two synthetic snapshots: no browser, API calls or Telegram delivery."""

import json
from pathlib import Path

from profi_order_monitor.notifications.messages import build_message
from profi_order_monitor.parsing import find_matching_ids


def main() -> None:
    folder = Path(__file__).resolve().parent
    before = json.loads((folder / "board-before.json").read_text(encoding="utf-8"))
    after = json.loads((folder / "board-after.json").read_text(encoding="utf-8"))
    new_ids = find_matching_ids(after) - find_matching_ids(before)
    print("ДЕМО: вымышленные ID; внешние сервисы не вызываются.\n")
    print(build_message(new_ids))


if __name__ == "__main__":
    main()
