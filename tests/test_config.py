import os
import unittest
from unittest.mock import patch

from profi_order_monitor.config import Settings


class ConfigurationTests(unittest.TestCase):
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
        self.assertEqual((settings.min_interval, settings.max_interval), (10, 50))
        self.assertEqual(settings.poll_seconds, 1)
        self.assertEqual(settings.site_url, "https://profi.ru/backoffice/n.php")

    def test_environment_overrides(self):
        values = {"MIN_REFRESH_SECONDS": "20", "MAX_REFRESH_SECONDS": "40", "POLL_SECONDS": "2.5", "TELEGRAM_CHAT_ID": " demo-chat "}
        with patch.dict(os.environ, values, clear=True):
            settings = Settings.from_environment()
        self.assertEqual((settings.min_interval, settings.max_interval), (20, 40))
        self.assertEqual(settings.poll_seconds, 2.5)
        self.assertEqual(settings.telegram_chat_id, "demo-chat")

    def test_invalid_intervals_and_urls_are_rejected(self):
        cases = [
            {"MIN_REFRESH_SECONDS": "0"},
            {"MAX_REFRESH_SECONDS": "9"},
            {"POLL_SECONDS": "nan"},
            {"RETRY_SECONDS": "inf"},
            {"POLL_SECONDS": "-1"},
            {"TELEGRAM_TIMEOUT_SECONDS": "oops"},
            {"SITE_URL": " "},
            {"MATCH_URL": ""},
        ]
        for values in cases:
            with self.subTest(values=values), patch.dict(os.environ, values, clear=True):
                with self.assertRaises(ValueError):
                    Settings.from_environment()

    def test_repr_excludes_credentials(self):
        settings = Settings(telegram_token="fictional-token-for-test", telegram_chat_id="fictional-chat-for-test")
        self.assertNotIn(settings.telegram_token, repr(settings))
        self.assertNotIn(settings.telegram_chat_id, repr(settings))


if __name__ == "__main__":
    unittest.main()
