
"""Offline Proof-of-Congestion protocol simulation."""

import json

from device import build_messages
from router import Router


def main():
    devices = {
        "device_1": 45,
        "device_2": 250,
        "device_3": 750,
        "device_4": 900,
    }

    # Independent router-side measurements.
    # device_4 claims severe congestion but the router observes a low score.
    observed_metrics = {
        "device_1": 45,
        "device_2": 250,
        "device_3": 750,
        "device_4": 100,
    }

    router = Router(
        observed_metrics=observed_metrics,
        priority_seconds=10,
        max_metric_difference=100,
    )

    print("PROOF-OF-CONGESTION: OFFLINE PROTOCOL DEMO\n")

    for device_id, local_score in devices.items():
        print(f"\n--- {device_id} ---")
        print(f"Device's private score: {local_score}")

        commit_message, reveal_message = build_messages(local_score)

        print("1. Device sends COMMIT.")
        ack = router.receive_commit(device_id, commit_message)
        print(json.dumps(ack, indent=2))

        if not ack.get("accepted"):
            print("Commit rejected; skipping reveal.")
            continue

        print("2. Router requests reveal; device sends tier and nonce only.")
        result = router.receive_reveal(
            device_id,
            reveal_message,
            session_id=ack.get("session_id"),
        )
        print("REVEAL:", json.dumps(reveal_message, indent=2))
        print("3. Router RESULT:", json.dumps(result, indent=2))

    print("\n--- FINAL PRIORITY STATUS ---")
    for device_id in devices:
        print(f"{device_id}: priority={router.has_priority(device_id)}")


if __name__ == "__main__":
    main()
