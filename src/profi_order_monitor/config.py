"""Configuration is read on startup, never embedded in source code."""

import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path


def number(name: str, default: float, minimum: float = 0.1) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name}: нужно число") from None
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name}: нужно конечное число не меньше {minimum}")
    return value


def integer(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name}: нужно целое число") from None
    if value < 1:
        raise ValueError(f"{name}: нужно положительное число")
    return value


@dataclass(frozen=True)
class Settings:
    site_url: str = "https://profi.ru/backoffice/n.php"
    match_url: str = "/graphql"
    min_interval: int = 10
    max_interval: int = 50
    downloads_dir: Path = Path("runtime/downloads")
    profile_dir: Path = Path("runtime/browser-profile")
    state_file: Path = Path("runtime/state.json")
    poll_seconds: float = 1
    retry_seconds: float = 30
    telegram_token: str = field(default="", repr=False)
    telegram_chat_id: str = field(default="", repr=False)
    request_timeout: int = 10

    @classmethod
    def from_environment(cls):
        minimum = integer("MIN_REFRESH_SECONDS", 10)
        maximum = integer("MAX_REFRESH_SECONDS", 50)
        if maximum < minimum:
            raise ValueError("MAX_REFRESH_SECONDS не может быть меньше MIN_REFRESH_SECONDS")
        site_url = os.getenv("SITE_URL", cls.site_url).strip()
        match_url = os.getenv("MATCH_URL", cls.match_url).strip()
        if not site_url or not match_url:
            raise ValueError("SITE_URL и MATCH_URL должны быть непустыми")
        return cls(
            site_url=site_url,
            match_url=match_url,
            min_interval=minimum,
            max_interval=maximum,
            downloads_dir=Path(os.getenv("DOWNLOADS_DIR", "runtime/downloads")),
            profile_dir=Path(os.getenv("BROWSER_PROFILE_DIR", "runtime/browser-profile")),
            state_file=Path(os.getenv("STATE_FILE", "runtime/state.json")),
            poll_seconds=number("POLL_SECONDS", 1),
            retry_seconds=number("RETRY_SECONDS", 30),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
            request_timeout=integer("TELEGRAM_TIMEOUT_SECONDS", 10),
        )


def initialize() -> Settings:
    from dotenv import load_dotenv

    load_dotenv(Path.cwd() / ".env", override=False)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("Неизвестный LOG_LEVEL")
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    return Settings.from_environment()
