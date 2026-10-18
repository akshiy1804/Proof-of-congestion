
"""Run a repeatable multi-device simulation and generate results and charts."""

import csv
import os

import matplotlib.pyplot as plt

from device import build_messages
from router import Router


DEVICES = [
    {"id": "Device 1", "claim": 45, "observed": 45, "type": "Honest"},
    {"id": "Device 2", "claim": 250, "observed": 250, "type": "Honest"},
    {"id": "Device 3", "claim": 750, "observed": 750, "type": "Honest"},
    {"id": "Device 4", "claim": 900, "observed": 100, "type": "Cheating"},
]


def main():
    os.makedirs("results", exist_ok=True)

    router = Router(
        observed_metrics={d["id"]: d["observed"] for d in DEVICES},
        priority_seconds=10,
        max_metric_difference=100,
    )

    rows = []

    for device in DEVICES:
        commit, reveal = build_messages(device["claim"])
        ack = router.receive_commit(device["id"], commit)

        if ack["accepted"]:
            result = router.receive_reveal(device["id"], reveal)
        else:
            result = {"accepted": False, "reason": "Commit rejected"}

        rows.append({
            "device": device["id"],
            "device_type": device["type"],
            "claimed_score": device["claim"],
            "observed_score": device["observed"],
            "accepted": result["accepted"],
            "reason": result["reason"],
            "priority_active": router.has_priority(device["id"]),
        })

    csv_path = "results/simulation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Chart 1: claimed versus router-observed congestion scores.
    labels = [row["device"] for row in rows]
    x = list(range(len(rows)))
    width = 0.35

    plt.figure(figsize=(8, 5))
    plt.bar(
        [i - width / 2 for i in x],
        [row["claimed_score"] for row in rows],
        width,
        label="Claimed score",
    )
    plt.bar(
        [i + width / 2 for i in x],
        [row["observed_score"] for row in rows],
        width,
        label="Observed score",
    )
    plt.xticks(x, labels)
    plt.ylabel("Congestion score")
    plt.title("Device Claims vs Router-Observed Metrics")
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/congestion_comparison.png", dpi=150)
    plt.close()

    # Chart 2: verification outcomes.
    accepted = sum(row["accepted"] for row in rows)
    rejected = len(rows) - accepted

    plt.figure(figsize=(6, 5))
    plt.bar(
        ["Accepted", "Rejected"],
        [accepted, rejected],
    )
    plt.ylabel("Number of devices")
    plt.title("Router Verification Outcomes")
    plt.tight_layout()
    plt.savefig("results/verification_outcomes.png", dpi=150)
    plt.close()

    print("Simulation complete.")
    print(f"CSV: {csv_path}")
    print("Charts: results/congestion_comparison.png")
    print("Charts: results/verification_outcomes.png")
    print(f"Accepted: {accepted}; Rejected: {rejected}")


if __name__ == "__main__":
    main()
