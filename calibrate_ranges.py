"""Controlled Mininet experiments for investigating congestion score ranges."""

import csv
import time
from pathlib import Path

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel

from measure import parse_ping_output, score_from_metrics
from commitment_engine import get_tier

OUTPUT = Path("results/range_calibration.csv")
IPERF_PORT = 5002
TRIALS = 10

CONDITIONS = [
    {"name": "baseline", "rates": []},
    {"name": "load_1_8M", "rates": [("h2", "1.8M")]},
    {"name": "load_1_85M", "rates": [("h2", "1.85M")]},
    {"name": "load_1_9M", "rates": [("h2", "1.9M")]},
    {"name": "load_1_95M", "rates": [("h2", "1.95M")]},
]


def run_ping(host, target):
    output = host.cmd(
        f"ping -n -i 0.2 -c 50 -W 1 {target}"
    )
    try:
        latency, loss = parse_ping_output(output, system="linux")
        score = score_from_metrics(latency, loss)
        return latency, loss, score, get_tier(score), ""
    except ValueError as exc:
        return None, None, None, None, f"{exc}: {output.strip()}"


def run_demo():
    OUTPUT.parent.mkdir(exist_ok=True)
    rows = []

    net = Mininet(
        controller=None,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
        autoStaticArp=True,
        build=False,
    )

    try:
        switch = net.addSwitch("s1", failMode="standalone")
        hosts = {
            name: net.addHost(name, ip=f"10.0.0.{i}/24")
            for i, name in enumerate(("h1", "h2", "h3", "h4"), start=1)
        }

        net.addLink(hosts["h1"], switch, cls=TCLink,
                    bw=2, delay="10ms", max_queue_size=10)
        for name in ("h2", "h3", "h4"):
            net.addLink(hosts[name], switch, cls=TCLink,
                        bw=5, delay="10ms", max_queue_size=10)

        net.start()

        loss = net.pingAll()
        if loss is None or loss > 0:
            raise RuntimeError("Initial Mininet connectivity check failed")

        h1 = hosts["h1"]
        h1.cmd(
            f"iperf -s -u -p {IPERF_PORT} "
            "> /tmp/poc_calibration_iperf.log 2>&1 &"
        )
        time.sleep(1)

        for condition in CONDITIONS:
            for trial in range(1, TRIALS + 1):
                print(
                    f"\nCondition={condition['name']} "
                    f"trial={trial}/{TRIALS}",
                    flush=True,
                )

                # Start only the load assigned to this condition.
                for host_name, rate in condition["rates"]:
                    hosts[host_name].cmd(
                        f"iperf -c 10.0.0.1 -u -b {rate} "
                        f"-t 12 -p {IPERF_PORT} "
                        f"> /tmp/poc_calibration_{host_name}.log 2>&1 &"
                    )

                if condition["rates"]:
                    time.sleep(1)

                # Measure the same path under every condition.
                latency, packet_loss, score, tier, error = run_ping(
                    h1, "10.0.0.4"
                )

                row = {
                    "condition": condition["name"],
                    "trial": trial,
                    "traffic_rates": ";".join(
                        f"{host}={rate}" for host, rate in condition["rates"]
                    ) or "none",
                    "latency_ms": latency,
                    "packet_loss_pct": packet_loss,
                    "score": score,
                    "current_tier": tier,
                    "error": error,
                }
                rows.append(row)

                print(
                    f"latency={latency} ms, loss={packet_loss}%, "
                    f"score={score}, current_tier={tier}, error={error}",
                    flush=True,
                )

                # Ensure traffic has ended before the next trial.
                if condition["rates"]:
                    time.sleep(12)

                # Allow the queue to drain between trials.
                time.sleep(2)

        with OUTPUT.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nSaved measurements to {OUTPUT.resolve()}")

    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("warning")
    run_demo()
