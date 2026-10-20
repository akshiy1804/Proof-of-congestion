
"""Commitments for the tier-only Proof-of-Congestion protocol."""

import hashlib
import json
import secrets
from typing import Any, Mapping

PROTOCOL_CONTEXT = "proof-of-congestion-v1"

TIERS: dict[int, dict[str, Any]] = {
    1: {"min": 1, "max": 100, "description": "Mild congestion"},
    2: {"min": 101, "max": 300, "description": "Moderate congestion"},
    3: {"min": 301, "max": 1000, "description": "Severe congestion"},
}


def _valid_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _tier_bounds(tier: Any) -> tuple[int, int]:
    if isinstance(tier, Mapping):
        low, high = tier.get("min"), tier.get("max")
    elif isinstance(tier, (tuple, list)) and len(tier) == 2:
        low, high = tier
    else:
        raise ValueError("Invalid tier configuration")
    if not _valid_integer(low) or not _valid_integer(high) or low > high:
        raise ValueError("Invalid tier bounds")
    return low, high


def get_tier(value: int, tiers: Mapping[int, Any] = TIERS) -> int:
    if not _valid_integer(value):
        raise ValueError("Congestion value must be an integer")
    for tier_id, tier in tiers.items():
        low, high = _tier_bounds(tier)
        if low <= value <= high:
            return int(tier_id)
    raise ValueError(f"Congestion value {value} is outside all tiers")


def create_commitment(
    nonce: str,
    tier_id: int,
    context: str = PROTOCOL_CONTEXT,
) -> str:
    """Commit to context, tier, and nonce before the router decides.

    Every tier has a commitment, so commitments alone do not prove honesty.
    The router's independent measurement provides the cross-check.
    """
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("Nonce must be a non-empty string")
    if not _valid_integer(tier_id) or tier_id not in TIERS:
        raise ValueError("Unknown tier")
    if not isinstance(context, str) or not context:
        raise ValueError("Context must be a non-empty string")

    payload = {"context": context, "tier_id": tier_id, "nonce": nonce}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_commitments(
    real_value: int,
    tiers: Mapping[int, Any] = TIERS,
    context: str = PROTOCOL_CONTEXT,
) -> dict[str, Any]:
    """Create equal-format commitments; retain nonces locally."""
    real_tier_id = get_tier(real_value, tiers)
    commitments = []
    private_reveals = {}

    for raw_tier_id in tiers:
        tier_id = int(raw_tier_id)
        nonce = secrets.token_hex(32)
        commitments.append({
            "tier_id": tier_id,
            "commitment": create_commitment(nonce, tier_id, context),
        })
        private_reveals[tier_id] = {"nonce": nonce}

    return {
        "commitments": commitments,
        "private_reveals": private_reveals,
        "real_tier_id": real_tier_id,
    }


def reveal(nonce: str, tier_id: int) -> dict[str, Any]:
    """Reveal the selected tier and nonce, never the exact score."""
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("Nonce must be a non-empty string")
    if not _valid_integer(tier_id) or tier_id not in TIERS:
        raise ValueError("Unknown tier")
    return {"type": "reveal", "tier_id": tier_id, "nonce": nonce}


def verify(
    commitment: str,
    nonce: str,
    tier_id: int,
    context: str = PROTOCOL_CONTEXT,
) -> bool:
    """Verify the tier-only commitment."""
    try:
        if not isinstance(commitment, str) or len(commitment) != 64:
            return False
        if any(c not in "0123456789abcdef" for c in commitment):
            return False
        expected = create_commitment(nonce, tier_id, context)
        return secrets.compare_digest(expected, commitment)
    except (TypeError, ValueError):
        return False
