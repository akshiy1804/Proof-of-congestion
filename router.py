
"""Router-side verification for Proof-of-Congestion."""

from typing import Any
from commitment_engine import TIERS, PROTOCOL_CONTEXT, verify


def validate_commit(message: dict[str, Any]) -> dict[int, str]:
    """Validate and store public commitments."""
    if not isinstance(message, dict) or message.get("type") != "commit":
        raise ValueError("Invalid message type")

    entries = message.get("commitments")
    if not isinstance(entries, list):
        raise ValueError("Commitments must be a list")

    stored: dict[int, str] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid commitment entry")

        tier_id = entry.get("tier_id")
        commitment = entry.get("commitment")

        if type(tier_id) is not int or tier_id not in TIERS:
            raise ValueError("Unknown tier")

        if tier_id in stored:
            raise ValueError("Duplicate tier")

        if (
            not isinstance(commitment, str)
            or len(commitment) != 64
            or any(c not in "0123456789abcdef" for c in commitment)
        ):
            raise ValueError("Invalid commitment hash")

        stored[tier_id] = commitment

    if set(stored) != set(TIERS):
        raise ValueError("A commitment for every tier is required")

    return stored


def verify_reveal(
    commitments: dict[int, str],
    message: dict[str, Any],
) -> bool:
    """Check a reveal against the stored commitment."""
    if not isinstance(message, dict) or message.get("type") != "reveal":
        return False

    tier_id = message.get("tier_id")
    value = message.get("value")
    nonce = message.get("nonce")

    if type(tier_id) is not int or tier_id not in TIERS:
        return False

    if not isinstance(nonce, str) or not nonce:
        return False

    return verify(
        commitment=commitments.get(tier_id, ""),
        value=value,
        nonce=nonce,
        tier_range=TIERS[tier_id],
        tier_id=tier_id,
        context=PROTOCOL_CONTEXT,
    )
