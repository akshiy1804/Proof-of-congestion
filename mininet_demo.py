
"""Automated four-host Mininet demo for Proof-of-Congestion.

Linux only. Requires Mininet, iperf (iperf2), ping, and Python 3.
Run from the repository root:
    sudo python3 mininet_demo.py
"""

import os
import time

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import info, setLogLevel


PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
ROUTER_PORT = 8765
IPERF_PORT = 5001


def run_demo():
    net = Mininet(
    controller=None,
    switch=OVSSwitch,
    link=TCLink,
    autoSetMacs=True,
    autoStaticArp=True,
    build=False,
)
    try:
        info("*** Creating four-host bottleneck topology\n")
        switch = net.addSwitch("s1", failMode="standalone")

        h1 = net.addHost("h1", ip="10.0.0.1/24")
        h2 = net.addHost("h2", ip="10.0.0.2/24")
        h3 = net.addHost("h3", ip="10.0.0.3/24")
        h4 = net.addHost("h4", ip="10.0.0.4/24")

        # h1's 2 Mbps link is shared by incoming traffic from h2 and h3.
        net.addLink(h1, switch, cls=TCLink, bw=2, delay="10ms",
                    max_queue_size=10)
        net.addLink(h2, switch, cls=TCLink, bw=5, delay="10ms",
                    max_queue_size=10)
        net.addLink(h3, switch, cls=TCLink, bw=5, delay="10ms",
                    max_queue_size=10)
        net.addLink(h4, switch, cls=TCLink, bw=5, delay="10ms",
                    max_queue_size=10)

        net.start()

        info("*** Checking host connectivity\n")
        loss = net.pingAll()

        if loss is None or loss > 0:
            raise RuntimeError(
                f"Mininet connectivity failed: {loss}% packet loss. "
                "Stopping before starting the protocol clients."
            )

        info("*** Starting iperf server on h1\n")
        h1.cmd(
            f"iperf -s -p {IPERF_PORT} "
            f"> /tmp/poc_iperf_server.log 2>&1 &"
        )
        time.sleep(1)

        info("*** Starting Proof-of-Congestion router on h1\n")
        device_map = (
            "--device-ip device_h2=10.0.0.2 "
            "--device-ip device_h3=10.0.0.3 "
            "--device-ip device_h4=10.0.0.4"
        )
        h1.cmd(
            f"cd {PROJECT_DIR} && "
            f"python3 router_server.py --host 10.0.0.1 "
            f"--port {ROUTER_PORT} {device_map} "
            "> /tmp/poc_router.log 2>&1 &"
        )
        time.sleep(2)

        info("*** Generating competing traffic from h2 and h3\n")
        h2.cmd(
            f"iperf -c 10.0.0.1 -p {IPERF_PORT} "
            "-t 18 -b 5M > /tmp/poc_h2_traffic.log 2>&1 &"
        )
        h3.cmd(
            f"iperf -c 10.0.0.1 -p {IPERF_PORT} "
            "-t 18 -b 5M > /tmp/poc_h3_traffic.log 2>&1 &"
        )
        time.sleep(2)

        info("*** Testing h2 and h3 clients during competing traffic\n")
        # These are declared claims for this demonstration. The router
        # still uses its own ping results to decide whether to accept them.
        h2.cmd(
            f"cd {PROJECT_DIR} && "
            f"python3 device_client.py --host 10.0.0.1 "
            f"--port {ROUTER_PORT} --device-id device_h2 "
            "--value 250 > /tmp/poc_h2_client.log 2>&1"
        )
        h3.cmd(
            f"cd {PROJECT_DIR} && "
            f"python3 device_client.py --host 10.0.0.1 "
            f"--port {ROUTER_PORT} --device-id device_h3 "
            "--value 750 > /tmp/poc_h3_client.log 2>&1"
        )

        info("*** Testing idle h4 with a Tier 3 claim\n")
        h4.cmd(
            f"cd {PROJECT_DIR} && "
            f"python3 device_client.py --host 10.0.0.1 "
            f"--port {ROUTER_PORT} --device-id device_h4 "
            "--claim-tier 3 --value 50 "
            "> /tmp/poc_h4_client.log 2>&1"
        )

        info("\n*** Demo results\n")
        for host, path in (
            (h1, "/tmp/poc_router.log"),
            (h2, "/tmp/poc_h2_client.log"),
            (h3, "/tmp/poc_h3_client.log"),
            (h4, "/tmp/poc_h4_client.log"),
        ):
            info(f"\n--- {host.name}: {path} ---\n")
            info(host.cmd(f"cat {path}"))

        info("\n*** Demo finished. Check RESULT verdicts above.\n")
        info("*** Press Enter to stop the topology.\n")
        input()

    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_demo()
