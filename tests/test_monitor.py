import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from profi_order_monitor.config import Settings
from profi_order_monitor.monitor import process_snapshot, run_monitor
from profi_order_monitor.notifications.messages import notification_batches
from profi_order_monitor.storage.files import load_state, save_state, write_json


def board(ids):
    return {"data": {"boSearchBoardItems": {"items": [{"id": value} for value in ids]}}}


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "state.json"

    def test_known_ids_do_not_trigger_send(self):
        known = {"demo-order-001"}
        sender = Mock()
        self.assertTrue(process_snapshot(board(known), known, self.path, sender))
        sender.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_empty_and_unrelated_payloads_do_not_trigger_send(self):
        sender = Mock()
        for data in [board([]), {"unrelated": {"id": "demo-order-001"}}]:
            self.assertTrue(process_snapshot(data, set(), self.path, sender))
        sender.assert_not_called()

    def test_failed_send_does_not_change_known_ids_or_state(self):
        known = {"demo-order-001"}
        save_state(self.path, known)
        self.assertFalse(process_snapshot(board(["demo-order-002"]), known, self.path, Mock(return_value=False)))
        self.assertEqual(known, {"demo-order-001"})
        self.assertEqual(load_state(self.path), known)

    def test_successful_send_persists_new_ids(self):
        known = {"demo-order-001"}
        sender = Mock(return_value=True)
        self.assertTrue(process_snapshot(board(["demo-order-001", "demo-order-002"]), known, self.path, sender))
        sender.assert_called_once()
        self.assertIn("demo-order-002", sender.call_args.args[0])
        self.assertEqual(load_state(self.path), {"demo-order-001", "demo-order-002"})
        self.assertEqual(known, load_state(self.path))

    def test_retry_after_failed_send_is_still_new(self):
        known = set()
        sender = Mock(side_effect=[False, True])
        data = board(["demo-order-001"])
        self.assertFalse(process_snapshot(data, known, self.path, sender))
        self.assertTrue(process_snapshot(data, known, self.path, sender))
        self.assertEqual(sender.call_count, 2)
        self.assertEqual(known, {"demo-order-001"})

    def test_only_confirmed_batch_is_persisted_on_partial_failure(self):
        ids = {f"demo-{index:03d}-" + "x" * 200 for index in range(50)}
        first_batch = list(notification_batches(ids))[0][0]
        known = set()
        sender = Mock(side_effect=[True, False])
        self.assertFalse(process_snapshot(board(ids), known, self.path, sender))
        self.assertEqual(known, first_batch)
        self.assertEqual(load_state(self.path), first_batch)
        successful_retry = Mock(return_value=True)
        self.assertTrue(process_snapshot(board(ids), known, self.path, successful_retry))
        self.assertEqual(known, ids)
        sent_text = "\n".join(call.args[0] for call in successful_retry.call_args_list)
        for item_id in first_batch:
            self.assertNotIn(item_id, sent_text)

    def test_state_write_failure_does_not_mark_id_in_memory(self):
        known = set()
        with patch("profi_order_monitor.monitor.save_state", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                process_snapshot(board(["demo-order-001"]), known, self.path, Mock(return_value=True))
        self.assertEqual(known, set())

    def test_polling_retries_failed_file_and_stops_without_real_wait(self):
        downloads = self.root / "downloads"
        write_json(downloads / "response_demo.json", board(["demo-order-001"]))
        settings = Settings(downloads_dir=downloads, state_file=self.path, telegram_token="fictional-test-token", retry_seconds=30)
        with patch("profi_order_monitor.monitor.TelegramClient") as adapter, patch(
            "profi_order_monitor.monitor.time.sleep", side_effect=[None, KeyboardInterrupt]
        ), patch("profi_order_monitor.monitor.time.monotonic", side_effect=[0, 0, 31]):
            adapter.return_value.send_message.side_effect = [False, True]
            with self.assertRaises(KeyboardInterrupt):
                run_monitor(settings)
        self.assertEqual(adapter.return_value.send_message.call_count, 2)
        self.assertEqual(load_state(self.path), {"demo-order-001"})


if __name__ == "__main__":
    unittest.main()
