
import unittest

from device import build_messages
from router import Router


class RouterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.router = Router(
            observed_metrics={"device_1": 250, "device_2": 100},
            priority_seconds=10,
            max_metric_difference=100,
        )
        self.now = 1_000_000.0

    def prepare_device(self, device_id, value):
        commit, reveal = build_messages(value)
        ack = self.router.receive_commit(device_id, commit)

        # Use a consistent simulated clock for this test.
        self.router.sessions[device_id]["commit_time"] = self.now
        self.assertTrue(ack["accepted"])
        return reveal

    def test_valid_claim_grants_priority(self):
        reveal = self.prepare_device("device_1", 250)
        result = self.router.receive_reveal(
            "device_1", reveal, now=self.now + 1
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(
            self.router.has_priority("device_1", now=self.now + 5)
        )

    def test_metric_mismatch_rejected(self):
        reveal = self.prepare_device("device_2", 900)
        result = self.router.receive_reveal(
            "device_2", reveal, now=self.now + 1
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(
            self.router.has_priority("device_2", now=self.now + 1)
        )

    def test_missing_commit_rejected(self):
        _, reveal = build_messages(250)
        result = self.router.receive_reveal(
            "device_1", reveal, now=self.now + 1
        )
        self.assertFalse(result["accepted"])

    def test_priority_expires(self):
        reveal = self.prepare_device("device_1", 250)
        self.router.receive_reveal(
            "device_1", reveal, now=self.now + 1
        )
        self.assertTrue(
            self.router.has_priority("device_1", now=self.now + 9)
        )
        self.assertFalse(
            self.router.has_priority("device_1", now=self.now + 11)
        )

    def test_tampered_reveal_rejected(self):
        reveal = self.prepare_device("device_1", 250)
        reveal["value"] = 251
        result = self.router.receive_reveal(
            "device_1", reveal, now=self.now + 1
        )
        self.assertFalse(result["accepted"])


if __name__ == "__main__":
    unittest.main()
