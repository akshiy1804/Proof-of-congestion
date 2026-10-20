
import unittest

from commitment_engine import (
    TIERS,
    create_commitment,
    generate_commitments,
    get_tier,
    reveal,
    verify,
)


class CommitmentTests(unittest.TestCase):
    def test_tier_boundaries(self):
        self.assertEqual(get_tier(45), 1)
        self.assertEqual(get_tier(250), 2)
        self.assertEqual(get_tier(750), 3)

    def test_wrong_nonce_rejected(self):
        digest = create_commitment("nonce-a", 2)
        self.assertFalse(verify(digest, "nonce-b", 2))

    def test_wrong_tier_rejected(self):
        digest = create_commitment("nonce-a", 2)
        self.assertFalse(verify(digest, "nonce-a", 3))

    def test_commitments_have_same_format(self):
        result = generate_commitments(250)
        self.assertEqual(
            {entry["tier_id"] for entry in result["commitments"]},
            set(TIERS),
        )
        self.assertTrue(
            all(len(entry["commitment"]) == 64
                for entry in result["commitments"])
        )

    def test_reveal_does_not_include_value(self):
        message = reveal("nonce-a", 2)
        self.assertNotIn("value", message)
        self.assertEqual(message["tier_id"], 2)


if __name__ == "__main__":
    unittest.main()
