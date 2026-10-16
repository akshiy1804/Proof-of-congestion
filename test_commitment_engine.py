"""Unit tests for the device-side cryptographic engine (stdlib unittest)."""

import unittest

from commitment_engine import (
    TIERS,
    create_commitment,
    generate_commitments,
    get_tier,
    reveal,
    verify,
)


class TierTests(unittest.TestCase):
    def test_tier_boundaries(self):
        self.assertEqual(get_tier(1), 1)
        self.assertEqual(get_tier(100), 1)
        self.assertEqual(get_tier(101), 2)
        self.assertEqual(get_tier(300), 2)
        self.assertEqual(get_tier(301), 3)
        self.assertEqual(get_tier(1000), 3)

    def test_out_of_range_values_rejected(self):
        for value in (0, 1001, -5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                get_tier(value)

    def test_non_integer_values_rejected(self):
        for value in (True, 45.0, "45"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                get_tier(value)


class CommitmentTests(unittest.TestCase):
    def test_valid_commitment_verifies(self):
        nonce = "example-secret-nonce"
        commitment = create_commitment(45, nonce, tier_id=1)
        self.assertTrue(verify(commitment, 45, nonce, TIERS[1], tier_id=1))

    def test_modified_value_fails(self):
        nonce = "example-secret-nonce"
        commitment = create_commitment(45, nonce, tier_id=1)
        self.assertFalse(verify(commitment, 46, nonce, TIERS[1], tier_id=1))

    def test_modified_nonce_fails(self):
        commitment = create_commitment(45, "original", tier_id=1)
        self.assertFalse(verify(commitment, 45, "modified", TIERS[1], tier_id=1))

    def test_modified_commitment_fails(self):
        commitment = create_commitment(45, "original", tier_id=1)
        tampered = ("0" if commitment[0] != "0" else "1") + commitment[1:]
        self.assertFalse(verify(tampered, 45, "original", TIERS[1], tier_id=1))

    def test_wrong_tier_fails(self):
        commitment = create_commitment(45, "original", tier_id=1)
        self.assertFalse(verify(commitment, 45, "original", TIERS[1], tier_id=2))

    def test_value_outside_claimed_tier_fails(self):
        commitment = create_commitment(45, "original", tier_id=1)
        self.assertFalse(verify(commitment, 101, "original", TIERS[1], tier_id=1))

    def test_generate_one_commitment_per_tier(self):
        result = generate_commitments(45)
        self.assertEqual(len(result["commitments"]), 3)
        self.assertEqual(result["real_tier_id"], 1)
        self.assertEqual([item["tier_id"] for item in result["commitments"]], [1, 2, 3])
        self.assertEqual(result["private_reveals"][1]["value"], 45)
        self.assertTrue(101 <= result["private_reveals"][2]["value"] <= 300)
        self.assertTrue(301 <= result["private_reveals"][3]["value"] <= 1000)

    def test_reveal_message_uses_original_nonce(self):
        generated = generate_commitments(45)
        secret = generated["private_reveals"][1]
        message = reveal(45, secret["nonce"], tier_id=1)
        self.assertEqual(message["type"], "reveal")
        self.assertEqual(message["value"], 45)
        self.assertEqual(message["nonce"], secret["nonce"])
        self.assertEqual(message["tier_id"], 1)


if __name__ == "__main__":
    unittest.main()
