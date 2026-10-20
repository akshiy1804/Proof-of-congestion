
"""Threaded TCP server with independent router-side measurements."""

import argparse
import json
import socketserver

from measure import measure_host
from router import Router


def send_json(sock, message):
    payload = json.dumps(message, separators=(",", ":")) + "\n"
    sock.sendall(payload.encode("utf-8"))


def receive_json(reader):
    line = reader.readline()
    if not line:
        raise ConnectionError("Peer disconnected")

    message = json.loads(line)
    if not isinstance(message, dict):
        raise ValueError("JSON message must be an object")
    return message


class ProtocolHandler(socketserver.StreamRequestHandler):
    def handle(self):
        router = self.server.router
        self.request.settimeout(15)

        try:
            network_commit = receive_json(self.rfile)
            if network_commit.get("type") != "COMMIT":
                send_json(self.request, {
                    "type": "RESULT",
                    "accepted": False,
                    "reason": "Expected COMMIT",
                })
                return

            device_id = network_commit.get("device_id")
            if not isinstance(device_id, str) or not device_id:
                raise ValueError("Invalid device ID")

            internal_commit = dict(network_commit)
            internal_commit["type"] = "commit"

            ack = router.receive_commit(device_id, internal_commit)
            send_json(self.request, ack)

            if not ack.get("accepted"):
                return

            session_id = ack.get("session_id")
            if not isinstance(session_id, str):
                raise ValueError("Router did not create a session ID")

            send_json(self.request, {
                "type": "REVEAL_REQUEST",
                "session_id": session_id,
            })

            network_reveal = receive_json(self.rfile)
            received_session = network_reveal.pop("session_id", None)

            if network_reveal.get("type") != "REVEAL":
                send_json(self.request, {
                    "type": "RESULT",
                    "device_id": device_id,
                    "accepted": False,
                    "priority": False,
                    "reason": "Expected REVEAL",
                })
                return

            # Use the configured device IP, or the TCP peer address.
            target_ip = self.server.device_ips.get(device_id)
            if not target_ip:
                target_ip = self.client_address[0]

            # Independently measure the device from the router.
            try:
                measurement = measure_host(target_ip)
            except RuntimeError as exc:
                send_json(self.request, {
                    "type": "RESULT",
                    "device_id": device_id,
                    "accepted": False,
                    "priority": False,
                    "reason": f"Router measurement failed: {exc}",
                })
                return

            router.observed_metrics[device_id] = measurement["score"]

            
            print(
                f"[MEASUREMENT] device={device_id} ip={target_ip} "
                f"latency={measurement['latency_ms']}ms "
                f"loss={measurement['packet_loss_pct']}% "
                f"score={measurement['score']}",
                flush=True,
            )


            internal_reveal = dict(network_reveal)
            internal_reveal["type"] = "reveal"

            try:
                result = router.receive_reveal(
                    device_id,
                    internal_reveal,
                    session_id=received_session,
                )
            except Exception as exc:
                print(f"[ERROR] receive_reveal failed for {device_id}: {exc!r}")
                result = {
                    "type": "RESULT",
                    "device_id": device_id,
                    "accepted": False,
                    "priority": False,
                    "reason": f"Reveal processing error: {exc}",
                }

           
            send_json(self.request, result)
            print(f"[RESULT] device={device_id} result={result}", flush=True)

        except (
            OSError,
            ConnectionError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            try:
                send_json(self.request, {
                    "type": "RESULT",
                    "accepted": False,
                    "priority": False,
                    "reason": f"Protocol error: {exc}",
                })
            except OSError:
                pass


class ProtocolServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, router, device_ips):
        self.router = router
        self.device_ips = device_ips
        super().__init__(address, ProtocolHandler)


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Congestion TCP router with ping measurements"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--device-ip",
        action="append",
        default=[],
        metavar="DEVICE_ID=IP",
        help="IP address to independently probe; repeat for each device",
    )
    args = parser.parse_args()

    device_ips = {}
    for item in args.device_ip:
        try:
            device_id, ip = item.split("=", 1)
            if not device_id or not ip:
                raise ValueError
            device_ips[device_id] = ip
        except ValueError:
            parser.error(f"Invalid --device-ip value: {item!r}")

    router = Router(observed_metrics={})

    with ProtocolServer(
        (args.host, args.port), router, device_ips
    ) as server:
        print(
            f"Proof-of-Congestion router listening on "
            f"{args.host}:{args.port}"
        )
        print("Router-side device IP mappings:", device_ips)
        print("Measurements are collected independently using ping.")
        print("Press Ctrl+C to stop.")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping router server.")
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
