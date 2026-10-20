
import unittest

from measure import parse_ping_output, score_from_metrics


class MeasurementTests(unittest.TestCase):
    def test_score_formula(self):
        self.assertEqual(score_from_metrics(25, 0), 50)
        self.assertEqual(score_from_metrics(50, 5), 200)

    def test_score_is_clamped(self):
        self.assertEqual(score_from_metrics(0, 0), 1)
        self.assertEqual(score_from_metrics(1000, 100), 1000)

    def test_invalid_metrics_rejected(self):
        with self.assertRaises(ValueError):
            score_from_metrics(-1, 0)
        with self.assertRaises(ValueError):
            score_from_metrics(10, 101)

    def test_parse_linux_ping_output(self):
        output = (
            "4 packets transmitted, 4 received, 0% packet loss\n"
            "rtt min/avg/max/mdev = 1.0/2.5/4.0/1.0 ms"
        )
        self.assertEqual(parse_ping_output(output, system="linux"), (2.5, 0.0))

    def test_parse_windows_ping_output(self):
        output = (
            "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),\n"
            "Minimum = 1ms, Maximum = 4ms, Average = 2ms"
        )
        self.assertEqual(parse_ping_output(output, system="windows"), (2.0, 0.0))


if __name__ == "__main__":
    unittest.main()

