
"""Generate reproducible simulation results and charts."""

import csv
from pathlib import Path

from device import build_messages
from router import Router

OUTPUT_DIR = Path("results")
DEVICES = {
    "device_1": 45,
    "device_2": 250,
    "device_3": 750,
    "device_4": 900,
}
OBSERVED = {
    "device_1": 45,
    "device_2": 250,
    "device_3": 750,
    "device_4": 100,
}


def generate():
    OUTPUT_DIR.mkdir(exist_ok=True)
    router = Router(
        observed_metrics=OBSERVED,
        priority_seconds=10,
        max_metric_difference=100,
    )
    rows = []

    for device_id, private_score in DEVICES.items():
        commit, reveal = build_messages(private_score)
        ack = router.receive_commit(device_id, commit)

        if ack.get("accepted"):
            result = router.receive_reveal(
                device_id,
                reveal,
                session_id=ack.get("session_id"),
            )
        else:
            result = {
                "accepted": False,
                "reason": ack.get("reason", "Commit rejected"),
                "tier_id": None,
            }

        rows.append({
            "device_id": device_id,
            "private_score": private_score,
            "router_observed_score": OBSERVED[device_id],
            "claimed_tier": reveal.get("tier_id"),
            "accepted": result.get("accepted", False),
            "priority": router.has_priority(device_id),
            "reason": result.get("reason", ""),
        })

    csv_path = OUTPUT_DIR / "simulation_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; CSV generated, charts skipped.")
        print(f"CSV: {csv_path}")
        return rows

    # Chart 1: router-observed score versus the device's local score.
    labels = [row["device_id"] for row in rows]
    x = list(range(len(rows)))
    width = 0.36

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(
        [i - width / 2 for i in x],
        [row["private_score"] for row in rows],
        width,
        label="Device-local score",
    )
    ax.bar(
        [i + width / 2 for i in x],
        [row["router_observed_score"] for row in rows],
        width,
        label="Router-observed score",
    )
    ax.set_xticks(x, labels)
    ax.set_ylabel("Congestion score")
    ax.set_ylim(0, 1100)
    ax.set_title("Device Claims vs Router Measurements")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "congestion_comparison.png", dpi=150)
    plt.close(fig)

    # Chart 2: verification outcome.
    accepted_count = sum(row["accepted"] for row in rows)
    rejected_count = len(rows) - accepted_count

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(["Accepted", "Rejected"], [accepted_count, rejected_count])
    ax.set_ylabel("Number of devices")
    ax.set_title("Proof-of-Congestion Verification Outcomes")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "verification_outcomes.png", dpi=150)
    plt.close(fig)

    print(f"CSV generated: {csv_path}")
    print(f"Charts generated in: {OUTPUT_DIR.resolve()}")
    print(f"Accepted: {accepted_count}; rejected: {rejected_count}")
    return rows


if __name__ == "__main__":
    generate()
