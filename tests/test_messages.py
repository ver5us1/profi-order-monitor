import unittest

from profi_order_monitor.notifications.messages import build_message, notification_batches


class MessageTests(unittest.TestCase):
    def test_message_is_sorted_and_has_count(self):
        text = build_message({"demo-order-002", "demo-order-001"})
        self.assertIn("Найдено новых: 2", text)
        self.assertLess(text.index("demo-order-001"), text.index("demo-order-002"))

    def test_empty_set_produces_no_batches(self):
        self.assertEqual(list(notification_batches(set())), [])

    def test_long_unicode_ids_are_batched_without_loss(self):
        ids = {f"demo-{index:03d}-" + "😀" * 70 for index in range(50)}
        batches = list(notification_batches(ids))
        self.assertGreater(len(batches), 1)
        self.assertEqual(set().union(*(batch for batch, _ in batches)), ids)
        self.assertEqual(sum(len(batch) for batch, _ in batches), len(ids))
        for batch, text in batches:
            self.assertLessEqual(len(text.encode("utf-16-le")) // 2, 4000)
            self.assertEqual(text, build_message(batch))

    def test_single_overlong_id_is_rejected(self):
        with self.assertRaises(ValueError):
            list(notification_batches({"demo-" + "x" * 5000}))


if __name__ == "__main__":
    unittest.main()
