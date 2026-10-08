import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from profi_order_monitor.browser.downloader import capture_response
from profi_order_monitor.config import Settings
from profi_order_monitor.notifications.telegram import TelegramClient
from profi_order_monitor.storage.files import read_json


class BrowserAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = Settings(downloads_dir=Path(self.directory.name))

    async def test_matching_empty_board_response_is_saved(self):
        data = {"data": {"boSearchBoardItems": {"items": []}}}
        response = SimpleNamespace(url="https://example.test/graphql", headers={"content-type": "application/json"}, json=AsyncMock(return_value=data))
        path = await capture_response(response, self.settings)
        self.assertIsNotNone(path)
        self.assertEqual(read_json(path), data)

    async def test_unrelated_route_content_type_and_schema_are_not_saved(self):
        cases = [
            ("https://example.test/other", "application/json", {}),
            ("https://example.test/graphql", "text/html", {}),
            ("https://example.test/graphql", "application/json", {"data": {"unrelated": []}}),
        ]
        for url, content_type, data in cases:
            with self.subTest(url=url, content_type=content_type):
                response = SimpleNamespace(url=url, headers={"content-type": content_type}, json=AsyncMock(return_value=data))
                self.assertIsNone(await capture_response(response, self.settings))
        self.assertEqual(list(self.settings.downloads_dir.iterdir()), [])

    async def test_invalid_json_is_logged_without_partial_snapshot(self):
        response = SimpleNamespace(url="https://example.test/graphql", headers={"content-type": "application/json"}, json=AsyncMock(side_effect=ValueError("bad JSON")))
        with self.assertLogs("profi_order_monitor.browser.downloader", level="WARNING"):
            self.assertIsNone(await capture_response(response, self.settings))
        self.assertEqual(list(self.settings.downloads_dir.iterdir()), [])


class TelegramAdapterTests(unittest.TestCase):
    def setUp(self):
        self.token = "fictional-test-token"
        self.client = TelegramClient(Settings(telegram_token=self.token))

    def test_explicit_chat_avoids_auto_discovery(self):
        client = TelegramClient(Settings(telegram_token=self.token, telegram_chat_id="demo-chat"))
        with patch.object(client, "_request") as request:
            self.assertEqual(client.get_chat_id(), "demo-chat")
        request.assert_not_called()

    def test_latest_message_chat_is_selected_and_cached(self):
        data = {"ok": True, "result": [{"message": {"chat": {"id": "demo-first"}}}, {"edited_message": {"chat": {"id": "demo-last"}}}]}
        with patch.object(self.client, "_request", return_value=data) as request:
            self.assertEqual(self.client.get_chat_id(), "demo-last")
            self.assertEqual(self.client.get_chat_id(), "demo-last")
        request.assert_called_once_with("getUpdates")

    def test_no_incoming_message_means_no_send(self):
        with patch.object(self.client, "_request", return_value={"ok": True, "result": []}) as request:
            with self.assertLogs("profi_order_monitor.notifications.telegram", level="WARNING"):
                self.assertFalse(self.client.send_message("demo"))
        request.assert_called_once_with("getUpdates")

    def test_send_failure_returns_false(self):
        self.client.chat_id = "demo-chat"
        with patch.object(self.client, "_request", return_value=None):
            self.assertFalse(self.client.send_message("demo"))

    def test_http_boundary_sends_encoded_message(self):
        response = Mock()
        response.read.return_value = json.dumps({"ok": True, "result": {"message_id": 1}}).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.dict("sys.modules", {"certifi": SimpleNamespace(where=lambda: "fictional-ca-path")}), patch(
            "profi_order_monitor.notifications.telegram.ssl.create_default_context"
        ), patch("profi_order_monitor.notifications.telegram.urllib.request.urlopen", return_value=response) as open_url:
            self.assertIsNotNone(self.client._request("sendMessage", {"chat_id": "demo-chat", "text": "demo text"}))
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(b"text=demo+text", request.data)

    def test_http_errors_do_not_log_token_or_token_bearing_url(self):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        errors = [urllib.error.URLError(url), urllib.error.HTTPError(url, 401, url, {}, io.BytesIO(b""))]
        for error in errors:
            with self.subTest(error_type=type(error).__name__), patch.dict(
                "sys.modules", {"certifi": SimpleNamespace(where=lambda: "fictional-ca-path")}
            ), patch("profi_order_monitor.notifications.telegram.ssl.create_default_context"), patch(
                "profi_order_monitor.notifications.telegram.urllib.request.urlopen", side_effect=error
            ), self.assertLogs("profi_order_monitor.notifications.telegram", level="WARNING") as logs:
                self.assertIsNone(self.client._request("sendMessage", {"text": "demo"}))
            self.assertNotIn(self.token, "\n".join(logs.output))
            self.assertNotIn(url, "\n".join(logs.output))

    def test_placeholder_token_is_rejected_before_network(self):
        client = TelegramClient(Settings(telegram_token="replace_me"))
        with patch("profi_order_monitor.notifications.telegram.urllib.request.urlopen") as open_url:
            with self.assertRaises(ValueError):
                client._request("getUpdates")
        open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
