
"""TCP device client for Proof-of-Congestion."""

import argparse
import json
import socket

from device import build_messages


def send_json(sock, message):
    """Send one newline-delimited JSON message."""
    payload = json.dumps(message, separators=(",", ":")) + "\n"
    sock.sendall(payload.encode("utf-8"))


def receive_json(reader):
    """Receive one JSON object from the router."""
    line = reader.readline()
    if not line:
        raise ConnectionError("Router disconnected")

    message = json.loads(line)
    if not isinstance(message, dict):
        raise ValueError("Router response must be a JSON object")

    return message


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Congestion TCP device client"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device-id", default="device_1")
    parser.add_argument(
        "--value",
        type=int,
        default=250,
        help="Device-local congestion score (1-1000)",
    )
    parser.add_argument(
        "--claim-tier",
        type=int,
        choices=[1, 2, 3],
        help="Select a tier to claim for testing against router measurements",
    )
    args = parser.parse_args()

    if not 1 <= args.value <= 1000:
        parser.error("--value must be between 1 and 1000")

    # The exact value remains local to this process.
    commit, reveal = build_messages(args.value)

    if args.claim_tier is not None:
        # Test a different claim. This does not transmit args.value.
        # The router independently checks the resulting tier.
        representative_scores = {1: 50, 2: 200, 3: 750}
        _, reveal = build_messages(representative_scores[args.claim_tier])

        # Use the commitments from the selected test claim as well.
        commit, reveal = build_messages(
            representative_scores[args.claim_tier]
        )

    commit["type"] = "COMMIT"
    commit["device_id"] = args.device_id

    print(f"Connecting to {args.host}:{args.port} ...")
    print("Local score is not included in either protocol message.")

    try:
        with socket.create_connection(
            (args.host, args.port), timeout=10
        ) as sock:
            sock.settimeout(15)

            with sock.makefile(
                "r", encoding="utf-8", newline="\n"
            ) as reader:
                # Stage 1: COMMIT.
                print("1. Sending COMMIT")
                send_json(sock, commit)

                ack = receive_json(reader)
                print("COMMIT_ACK:", json.dumps(ack, indent=2))

                if not ack.get("accepted"):
                    return

                # Stage 2: wait for the router's reveal request.
                request = receive_json(reader)
                print(
                    "Router message:",
                    json.dumps(request, indent=2),
                )

                if request.get("type") != "REVEAL_REQUEST":
                    raise RuntimeError(
                        "Router did not request a reveal"
                    )

                # Stage 3: REVEAL contains tier and nonce only.
                reveal["type"] = "REVEAL"
                reveal["session_id"] = request["session_id"]

                if "value" in reveal:
                    raise ValueError(
                        "Refusing to send a reveal containing value"
                    )

                print("2. Sending tier-only REVEAL")
                send_json(sock, reveal)

                # Stage 4: RESULT.
                result = receive_json(reader)
                print("3. RESULT:", json.dumps(result, indent=2))

    except (
        OSError,
        ConnectionError,
        ValueError,
        json.JSONDecodeError,
        RuntimeError,
    ) as exc:
        print(f"Client protocol failed: {exc}")


if __name__ == "__main__":
    main()
