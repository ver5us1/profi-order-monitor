import json
import tempfile
import unittest
from pathlib import Path

from profi_order_monitor.storage.files import load_state, read_json, save_snapshot, save_state, write_json


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "nested" / "state.json"

    def test_missing_state_has_no_known_ids(self):
        self.assertEqual(load_state(self.path), set())

    def test_state_round_trip_is_sorted(self):
        save_state(self.path, {"demo-order-002", "demo-order-001"})
        self.assertEqual(load_state(self.path), {"demo-order-001", "demo-order-002"})
        self.assertEqual(read_json(self.path)["known_ids"], ["demo-order-001", "demo-order-002"])

    def test_bad_state_structure_is_rejected(self):
        for value in [[], {}, {"known_ids": None}, {"known_ids": [True]}, {"known_ids": [""]}]:
            with self.subTest(value=value):
                write_json(self.path, value)
                with self.assertRaises(ValueError):
                    load_state(self.path)

    def test_corrupt_json_is_not_silently_reset(self):
        self.path.parent.mkdir()
        self.path.touch()
        with self.assertRaises(json.JSONDecodeError):
            load_state(self.path)

    def test_serialization_error_preserves_previous_file_and_cleans_temp(self):
        save_state(self.path, {"demo-order-001"})
        previous = self.path.read_bytes()
        with self.assertRaises(TypeError):
            write_json(self.path, {"unsupported": object()})
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_snapshot_is_complete_json_without_temporary_files(self):
        directory = self.path.parent / "downloads"
        data = {"data": {"boSearchBoardItems": {"items": []}}}
        path = save_snapshot(directory, data)
        self.assertTrue(path.name.startswith("response_"))
        self.assertEqual(read_json(path), data)
        self.assertEqual(list(directory.iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
