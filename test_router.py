
import unittest

from device import build_messages
from router import validate_commit, verify_reveal


class RouterTests(unittest.TestCase):
    def test_valid_reveal(self):
        commit, reveal_message = build_messages(45)
        stored = validate_commit(commit)
        self.assertTrue(verify_reveal(stored, reveal_message))

    def test_tampered_reveal(self):
        commit, reveal_message = build_messages(45)
        stored = validate_commit(commit)
        reveal_message["value"] = 46
        self.assertFalse(verify_reveal(stored, reveal_message))

    def test_missing_commitment_rejected(self):
        commit, _ = build_messages(45)
        commit["commitments"].pop()
        with self.assertRaises(ValueError):
            validate_commit(commit)


if __name__ == "__main__":
    unittest.main()
