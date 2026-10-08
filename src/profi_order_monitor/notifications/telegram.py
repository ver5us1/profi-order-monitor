"""Small Telegram Bot API adapter; credentials come from Settings."""

import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request

from profi_order_monitor.config import Settings

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.chat_id = settings.telegram_chat_id or None

    def _request(self, method: str, payload: dict | None = None):
        if not self.settings.telegram_token or self.settings.telegram_token in {
            "replace_me", "ВСТАВЬ_ТОКЕН_СЮДА",
        }:
            raise ValueError("Не задан TELEGRAM_BOT_TOKEN в .env")
        import certifi

        url = f"https://api.telegram.org/bot{self.settings.telegram_token}/{method}"
        body = urllib.parse.urlencode(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET")
        context = ssl.create_default_context(cafile=certifi.where())
        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.request_timeout, context=context,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict) or data.get("ok") is not True:
                code = data.get("error_code") if isinstance(data, dict) else "invalid-response"
                logger.warning("Telegram %s: код %s", method, code)
                return None
            return data
        except urllib.error.HTTPError as error:
            logger.warning("Telegram %s: HTTP %s", method, error.code)
        except Exception as error:
            # Exception messages can include the token-bearing request URL.
            logger.warning("Telegram %s: %s", method, type(error).__name__)
        return None

    def get_chat_id(self) -> str | None:
        if self.chat_id is not None:
            return self.chat_id
        data = self._request("getUpdates")
        if data is None or not isinstance(data.get("result"), list):
            return None
        for update in reversed(data["result"]):
            if not isinstance(update, dict):
                continue
            message = update.get("message") or update.get("edited_message")
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            if isinstance(chat, dict) and type(chat.get("id")) in {str, int}:
                self.chat_id = str(chat["id"])
                return self.chat_id
        return None

    def send_message(self, text: str) -> bool:
        chat_id = self.get_chat_id()
        if chat_id is None:
            logger.warning("Chat ID не найден; нужно сообщение вашему боту или TELEGRAM_CHAT_ID")
            return False
        response = self._request("sendMessage", {
            "chat_id": chat_id, "text": text, "disable_web_page_preview": "true",
        })
        return response is not None
