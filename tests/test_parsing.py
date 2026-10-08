import unittest

from profi_order_monitor.parsing import extract_ids, find_matching_ids, has_board_payload


def board(*ids):
    return {"data": {"boSearchBoardItems": {"items": [{"id": value} for value in ids]}}}


class ParsingTests(unittest.TestCase):
    def test_direct_ids_are_normalized_and_deduplicated(self):
        self.assertEqual(extract_ids(board(" demo-order-001 ", 42, 42)), {"demo-order-001", "42"})

    def test_batch_and_wrapped_responses_are_combined(self):
        data = [board("demo-order-001"), {"wrapper": [board("demo-order-002"), board("demo-order-003")]}]
        self.assertEqual(find_matching_ids(data), {"demo-order-001", "demo-order-002", "demo-order-003"})

    def test_unrelated_ids_are_ignored(self):
        data = {"items": [{"id": "unrelated"}], "wrapper": board("demo-order-001")}
        self.assertEqual(find_matching_ids(data), {"demo-order-001"})

    def test_invalid_id_types_and_blank_strings_are_ignored(self):
        self.assertEqual(extract_ids(board(None, True, False, [], {}, 1.5, "", " ", "demo-order-001")), {"demo-order-001"})

    def test_empty_board_is_a_valid_payload(self):
        self.assertTrue(has_board_payload(board()))
        self.assertEqual(find_matching_ids(board()), set())

    def test_wrong_shapes_do_not_raise(self):
        for value in [None, 1, "text", {}, [], {"data": None}, {"data": {"boSearchBoardItems": {"items": {}}}}]:
            with self.subTest(value=value):
                self.assertFalse(has_board_payload(value))
                self.assertEqual(extract_ids(value), set())


if __name__ == "__main__":
    unittest.main()
