"""Small command-line simulation of a Proof-of-Congestion device."""

from __future__ import annotations

import argparse
import json
import secrets
from typing import Any

from commitment_engine import TIERS, generate_commitments, reveal


def build_messages(congestion_value: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a public COMMIT message and the later private REVEAL message."""
    generated = generate_commitments(congestion_value, TIERS)
    real_tier_id = generated["real_tier_id"]
    real_secret = generated["private_reveals"][real_tier_id]

    commit_message = {
        "type": "commit",
        "commitments": generated["commitments"],
    }
    reveal_message = reveal(
        real_value=congestion_value,
        nonce=real_secret["nonce"],
        tier_id=real_tier_id,
    )
    return commit_message, reveal_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a device-side congestion claim")
    parser.add_argument(
        "--value",
        type=int,
        help="Congestion score (1-1000). If omitted, a random valid score is used.",
    )
    args = parser.parse_args()
    congestion_value = args.value if args.value is not None else secrets.randbelow(1000) + 1

    try:
        commit_message, reveal_message = build_messages(congestion_value)
    except ValueError as exc:
        parser.error(str(exc))

    print("COMMIT message (sent first; contains hashes only):")
    print(json.dumps(commit_message, indent=2))
    print("\nREVEAL message (sent later in the protocol):")
    print(json.dumps(reveal_message, indent=2))
    print("\nNote: this demo prints both stages for learning. A real device would wait for the router's reveal request.")


if __name__ == "__main__":
    main()
