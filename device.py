
"""Device-side COMMIT and tier-only REVEAL demonstration."""

import argparse
import json
import random

from commitment_engine import generate_commitments, reveal


def build_messages(congestion_value):
    """Keep the score local; reveal only the selected tier and nonce."""
    generated = generate_commitments(congestion_value)

    commit_message = {
        "type": "commit",
        "commitments": generated["commitments"],
    }

    tier_id = generated["real_tier_id"]
    nonce = generated["private_reveals"][tier_id]["nonce"]
    reveal_message = reveal(nonce, tier_id)

    return commit_message, reveal_message


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Congestion device protocol demo"
    )
    parser.add_argument(
        "--value",
        type=int,
        help="Local congestion score (1-1000); never sent in REVEAL",
    )
    args = parser.parse_args()

    value = args.value if args.value is not None else random.randint(1, 1000)

    try:
        commit_message, reveal_message = build_messages(value)
    except ValueError as exc:
        parser.error(str(exc))

    print("Local congestion score (device only):", value)
    print("\nCOMMIT message (sent first):")
    print(json.dumps(commit_message, indent=2))
    print("\nREVEAL message (no exact score):")
    print(json.dumps(reveal_message, indent=2))


if __name__ == "__main__":
    main()
