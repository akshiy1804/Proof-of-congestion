
"""Latency and packet-loss measurements for Proof-of-Congestion."""

import platform
import re
import subprocess
from typing import Callable, Optional


def score_from_metrics(latency_ms: float, loss_pct: float) -> int:
    """Map latency and packet loss to a score in the range 1..1000."""
    if latency_ms < 0 or not 0 <= loss_pct <= 100:
        raise ValueError("Invalid latency or packet-loss measurement")

    score = round(latency_ms * 2 + loss_pct * 20)
    return max(1, min(1000, score))


def parse_ping_output(output: str, system: Optional[str] = None) -> tuple[float, float]:
    """Extract average RTT in ms and packet loss percentage from ping output."""
    system = (system or platform.system()).lower()

    loss_match = re.search(
        r"(\d+(?:\.\d+)?)%\s*packet loss",
        output,
        re.IGNORECASE,
    )
    if not loss_match:
        loss_match = re.search(
            r"Lost\s*=\s*\d+\s*\((\d+(?:\.\d+)?)%\s*loss\)",
            output,
            re.IGNORECASE,
        )

    if not loss_match:
        raise ValueError("Could not parse packet loss from ping output")

    loss_pct = float(loss_match.group(1))

    if system == "windows":
        rtt_match = re.search(
            r"Average\s*=\s*(\d+)\s*ms",
            output,
            re.IGNORECASE,
        )
    else:
        rtt_match = re.search(
            r"(?:rtt|round-trip).*?=\s*"
            r"[\d.]+/([\d.]+)/[\d.]+",
            output,
            re.IGNORECASE,
        )

    # If every packet was lost, use a conservative high latency.
    if not rtt_match and loss_pct == 100:
        return 500.0, loss_pct

    if not rtt_match:
        raise ValueError("Could not parse average latency from ping output")

    latency_ms = float(rtt_match.group(1))
    return latency_ms, loss_pct


def measure_host(
    host: str,
    *,
    runner: Callable = subprocess.run,
    count: int = 4,
    timeout_seconds: int = 8,
) -> dict:
    """Ping a host and return measured latency, loss, and score.

    The runner argument is injectable so tests can provide fake ping output.
    """
    if not host or count < 1:
        raise ValueError("A host and positive ping count are required")

    system = platform.system().lower()
    if system == "windows":
        command = ["ping", "-n", str(count), "-w", str(timeout_seconds * 1000), host]
    else:
        command = ["ping", "-c", str(count), "-W", str(timeout_seconds), host]

    try:
        result = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds * count + 2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Ping measurement failed for {host}: {exc}") from exc

    output = (result.stdout or "") + "\n" + (result.stderr or "")

    try:
        latency_ms, loss_pct = parse_ping_output(output, system=system)
    except ValueError as exc:
        raise RuntimeError(
            f"Could not measure {host}; ping output was: {output.strip()!r}"
        ) from exc

    return {
        "host": host,
        "latency_ms": latency_ms,
        "packet_loss_pct": loss_pct,
        "score": score_from_metrics(latency_ms, loss_pct),
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Measure congestion metrics")
    parser.add_argument("host", help="Host/IP address to ping")
    args = parser.parse_args()

    try:
        print(json.dumps(measure_host(args.host), indent=2))
    except RuntimeError as exc:
        parser.error(str(exc))

