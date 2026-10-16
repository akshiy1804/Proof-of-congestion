"""Device-side cryptographic helpers for the Proof-of-Congestion prototype."""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any, Mapping

PROTOCOL_CONTEXT = "proof-of-congestion-v1"

# Keep this configuration identical on the device and router.
TIERS: dict[int, dict[str, Any]] = {
    1: {"min": 1, "max": 100, "description": "Mild congestion"},
    2: {"min": 101, "max": 300, "description": "Moderate congestion"},
    3: {"min": 301, "max": 1000, "description": "Severe congestion"},
}


def _valid_integer(value: Any) -> bool:
    """True for integers, but not booleans (bool is an int subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _tier_bounds(tier: Any) -> tuple[int, int]:
    """Read bounds from a tier config dict or a (minimum, maximum) pair."""
    if isinstance(tier, Mapping):
        low, high = tier.get("min"), tier.get("max")
    elif isinstance(tier, (tuple, list)) and len(tier) == 2:
        low, high = tier
    else:
        raise ValueError("Each tier must contain 'min'/'max' or be a (min, max) pair")
    if not _valid_integer(low) or not _valid_integer(high) or low > high:
        raise ValueError("Tier bounds must be valid integers with min <= max")
    return low, high


def get_tier(value: int, tiers: Mapping[int, Any] = TIERS) -> int:
    """Return the ID of the tier containing value, or raise ValueError."""
    if not _valid_integer(value):
        raise ValueError("Congestion value must be an integer")
    for tier_id, tier in tiers.items():
        low, high = _tier_bounds(tier)
        if low <= value <= high:
            return int(tier_id)
    raise ValueError(f"Congestion value {value} is outside all configured tiers")


def create_commitment(
    value: int,
    nonce: str,
    tier_id: int | None = None,
    context: str = PROTOCOL_CONTEXT,
) -> str:
    """Create a SHA-256 commitment to the value, nonce, tier, and protocol context."""
    if not _valid_integer(value):
        raise ValueError("Congestion value must be an integer")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("Nonce must be a non-empty string")
    if tier_id is not None and not _valid_integer(tier_id):
        raise ValueError("tier_id must be an integer when provided")
    if not isinstance(context, str) or not context:
        raise ValueError("Context must be a non-empty string")

    payload = {
        "context": context,
        "tier_id": tier_id,
        "value": value,
        "nonce": nonce,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_commitments(
    real_value: int,
    tiers: Mapping[int, Any] = TIERS,
    context: str = PROTOCOL_CONTEXT,
) -> dict[str, Any]:
    """Create one commitment per tier; keep reveal data in a separate local field.

    Return value shape:
      {
        "commitments": [{"tier_id": 1, "commitment": "..."}, ...],
        "private_reveals": {1: {"value": ..., "nonce": ...}, ...},
        "real_tier_id": 1
      }

    Only the ``commitments`` list should be sent in the COMMIT message. The
    private_reveals mapping must stay on the device until reveal time.
    """
    real_tier_id = get_tier(real_value, tiers)
    commitments: list[dict[str, Any]] = []
    private_reveals: dict[int, dict[str, Any]] = {}

    for raw_tier_id, tier in tiers.items():
        tier_id = int(raw_tier_id)
        low, high = _tier_bounds(tier)
        if tier_id == real_tier_id:
            value = real_value
        else:
            value = secrets.randbelow(high - low + 1) + low
        nonce = secrets.token_hex(32)
        commitment = create_commitment(value, nonce, tier_id=tier_id, context=context)
        commitments.append({"tier_id": tier_id, "commitment": commitment})
        private_reveals[tier_id] = {"value": value, "nonce": nonce}

    return {
        "commitments": commitments,
        "private_reveals": private_reveals,
        "real_tier_id": real_tier_id,
    }


def reveal(real_value: int, nonce: str, tier_id: int | None = None) -> dict[str, Any]:
    """Prepare the REVEAL message for the actual value and its original nonce."""
    if not _valid_integer(real_value):
        raise ValueError("Congestion value must be an integer")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("Nonce must be a non-empty string")
    if tier_id is not None and not _valid_integer(tier_id):
        raise ValueError("tier_id must be an integer when provided")
    message: dict[str, Any] = {"type": "reveal", "value": real_value, "nonce": nonce}
    if tier_id is not None:
        message["tier_id"] = tier_id
    return message


def verify(
    commitment: str,
    value: int,
    nonce: str,
    tier_range: Any,
    tier_id: int | None = None,
    context: str = PROTOCOL_CONTEXT,
) -> bool:
    """Verify that a reveal is in range and matches the stored commitment."""
    try:
        low, high = _tier_bounds(tier_range)
        if not _valid_integer(value) or not low <= value <= high:
            return False
        if not isinstance(nonce, str) or not nonce:
            return False
        if not isinstance(commitment, str) or len(commitment) != 64:
            return False
        expected = create_commitment(value, nonce, tier_id=tier_id, context=context)
        return secrets.compare_digest(expected, commitment)
    except (TypeError, ValueError):
        return False
