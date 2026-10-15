
import hashlib
import secrets
import json


# Public congestion tiers: (minimum, maximum)
TIERS = {
    1: (1, 100),
    2: (101, 300),
    3: (301, 1000),
}


def get_tier(value, tiers=TIERS):
    """Return the tier containing the congestion value."""
    for tier_id, (minimum, maximum) in tiers.items():
        if minimum <= value <= maximum:
            return tier_id

    raise ValueError("Value does not belong to any tier.")


def create_commitment(value, nonce):
    """Create a SHA-256 commitment to a value and nonce."""
    message = json.dumps(
        {"value": value, "nonce": nonce},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def generate_commitments(real_value, tiers=TIERS):
    """Generate one commitment for each tier."""
    real_tier = get_tier(real_value, tiers)
    commitments = []

    for tier_id, (minimum, maximum) in tiers.items():
        if tier_id == real_tier:
            value = real_value
            nonce = secrets.token_hex(32)
        else:
            value = secrets.randbelow(maximum - minimum + 1) + minimum
            nonce = secrets.token_hex(32)

        commitment = create_commitment(value, nonce)

        commitments.append({
            "tier_id": tier_id,
            "commitment": commitment,
        })

        # The real reveal information stays on the device.
        if tier_id == real_tier:
            real_nonce = nonce

    return commitments, {
        "tier_id": real_tier,
        "value": real_value,
        "nonce": real_nonce,
    }


def reveal(real_value, nonce):
    """Prepare the real value and nonce for reveal."""
    return {
        "value": real_value,
        "nonce": nonce,
    }


def verify(commitment, value, nonce, tier_range):
    """Verify the hash and the tier membership."""
    minimum, maximum = tier_range

    if not isinstance(value, int) or isinstance(value, bool):
        return False

    if not minimum <= value <= maximum:
        return False

    if not isinstance(nonce, str) or not nonce:
        return False

    expected = create_commitment(value, nonce)
    return secrets.compare_digest(commitment, expected)
