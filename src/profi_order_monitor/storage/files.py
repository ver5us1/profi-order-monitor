"""Atomic JSON writes prevent readers from seeing incomplete snapshots."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("known_ids"), list):
        raise ValueError("state.json должен содержать список known_ids")
    values = data["known_ids"]
    if any(type(value) not in {str, int} or not str(value).strip() for value in values):
        raise ValueError("known_ids содержит некорректный ID")
    return {str(value).strip() for value in values}


def save_state(path: Path, ids: set[str]) -> None:
    write_json(path, {"known_ids": sorted(ids)})


def save_snapshot(directory: Path, data: object) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    path = directory / f"response_{stamp}.json"
    write_json(path, data)
    return path
