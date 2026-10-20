
"""Integration tests for the TCP Proof-of-Congestion protocol."""

import json
import socket
import threading
import unittest
from unittest.mock import patch

from device import build_messages
from router import Router
from router_server import ProtocolServer


class NetworkProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router(
            observed_metrics={},
            priority_seconds=10,
            max_metric_difference=100,
        )
        cls.server = ProtocolServer(
            ("127.0.0.1", 0), cls.router, {}
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def exchange(self, device_id, score, measured_score):
        commit, reveal = build_messages(score)
        commit["type"] = "COMMIT"
        commit["device_id"] = device_id

        # Keep tests deterministic; do not rely on actual ping timing.
        fake_measurement = {
            "host": "127.0.0.1",
            "latency_ms": 10.0,
            "packet_loss_pct": 0.0,
            "score": measured_score,
        }

        with patch("router_server.measure_host", return_value=fake_measurement):
            with socket.create_connection(
                ("127.0.0.1", self.port), timeout=3
            ) as sock:
                sock.settimeout(3)
                with sock.makefile(
                    "r", encoding="utf-8", newline="\n"
                ) as reader:
                    def receive():
                        line = reader.readline()
                        if not line:
                            raise ConnectionError("Server closed connection")
                        return json.loads(line)

                    def send(message):
                        sock.sendall(
                            (json.dumps(message) + "\n").encode("utf-8")
                        )

                    send(commit)
                    ack = receive()
                    self.assertEqual(ack["type"], "COMMIT_ACK")
                    self.assertTrue(ack["accepted"])

                    request = receive()
                    self.assertEqual(request["type"], "REVEAL_REQUEST")

                    reveal["type"] = "REVEAL"
                    reveal["session_id"] = request["session_id"]
                    self.assertNotIn("value", reveal)
                    send(reveal)

                    return receive()

    def test_honest_device_accepted(self):
        result = self.exchange("honest_net", 50, 50)
        self.assertTrue(result["accepted"])
        self.assertTrue(result["priority"])
        self.assertEqual(result["tier_id"], 1)

    def test_lying_high_tier_rejected(self):
        result = self.exchange("cheater_net", 750, 50)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["priority"])
        self.assertEqual(
            result["reason"],
            "Claim does not match observed metrics",
        )

    def test_reveal_never_contains_exact_score(self):
        _, reveal = build_messages(250)
        self.assertNotIn("value", reveal)

    def test_malformed_json_is_handled(self):
        with socket.create_connection(
            ("127.0.0.1", self.port), timeout=3
        ) as sock:
            sock.settimeout(3)
            sock.sendall(b"{invalid json}\n")
            response = sock.makefile(
                "r", encoding="utf-8", newline="\n"
            ).readline()
            self.assertTrue(response)
            message = json.loads(response)
            self.assertFalse(message["accepted"])


if __name__ == "__main__":
    unittest.main()
