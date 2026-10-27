import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

INPUT = Path("results/range_calibration_final.csv")
OUT = Path("results/graphs")
OUT.mkdir(parents=True, exist_ok=True)

with INPUT.open(newline="") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    row["latency_ms"] = float(row["latency_ms"])
    row["packet_loss_pct"] = float(row["packet_loss_pct"])
    row["score"] = int(row["score"])
    row["trial"] = int(row["trial"])
    row["current_tier"] = int(row["current_tier"])

conditions = [
    "baseline", "load_1_8M", "load_1_85M",
    "load_1_9M", "load_1_95M"
]
labels = [
    "Baseline", "1.80 Mbps", "1.85 Mbps",
    "1.90 Mbps", "1.95 Mbps"
]
grouped = {
    c: [r for r in rows if r["condition"] == c]
    for c in conditions
}

if any(not grouped[c] for c in conditions):
    raise ValueError("Missing condition data in calibration CSV")

plt.rcParams.update({"figure.dpi": 140, "font.size": 10})

# 1. Score versus offered traffic load
fig, ax = plt.subplots(figsize=(9, 5.5))
for i, condition in enumerate(conditions):
    scores = [r["score"] for r in grouped[condition]]
    x = np.random.default_rng(42 + i).normal(i, 0.045, len(scores))
    ax.scatter(x, scores, alpha=0.8, label="Individual trials" if i == 0 else None)
    ax.plot([i - 0.16, i + 0.16], [np.median(scores)] * 2,
            linewidth=3, label="Median" if i == 0 else None)
ax.axhline(100, linestyle="--", label="Tier 1 upper bound (100)")
ax.axhline(300, linestyle=":", label="Tier 2 upper bound (300)")
ax.set_xticks(range(len(labels)), labels)
ax.set_ylabel("Congestion score")
ax.set_xlabel("Offered UDP traffic load")
ax.set_title("Congestion Score vs. Offered Load")
ax.legend()
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "01_score_vs_load.png")
plt.close(fig)

# 2. Packet loss versus offered load
fig, ax = plt.subplots(figsize=(9, 5.5))
loss_data = [
    [r["packet_loss_pct"] for r in grouped[c]]
    for c in conditions
]
ax.boxplot(loss_data, tick_labels=labels, showmeans=True)
ax.set_xlabel("Offered UDP traffic load")
ax.set_ylabel("Packet loss (%)")
ax.set_title("Packet Loss vs. Offered Load")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "02_packet_loss_vs_load.png")
plt.close(fig)

# 3. Tier classification distribution
fig, ax = plt.subplots(figsize=(9, 5.5))
bottom = np.zeros(len(conditions))
for tier, name in [(1, "Tier 1"), (2, "Tier 2"), (3, "Tier 3")]:
    counts = [
        sum(r["current_tier"] == tier for r in grouped[c])
        for c in conditions
    ]
    ax.bar(labels, counts, bottom=bottom, label=name)
    bottom += np.array(counts)
ax.set_xlabel("Offered UDP traffic load")
ax.set_ylabel("Number of trials")
ax.set_title("Tier Classification Across 10 Trials")
ax.set_ylim(0, 10)
ax.legend()
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "03_tier_distribution.png")
plt.close(fig)

# 4. Score variability
fig, ax = plt.subplots(figsize=(9, 5.5))
score_data = [
    [r["score"] for r in grouped[c]]
    for c in conditions
]
ax.boxplot(score_data, tick_labels=labels, showmeans=True)
ax.axhline(100, linestyle="--", label="Boundary: 100")
ax.axhline(300, linestyle=":", label="Boundary: 300")
ax.set_xlabel("Offered UDP traffic load")
ax.set_ylabel("Congestion score")
ax.set_title("Score Distribution and Variability")
ax.legend()
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "04_score_variability.png")
plt.close(fig)

print(f"Read {len(rows)} measurements from {INPUT}")
print(f"Saved four graphs in {OUT}/")
for path in sorted(OUT.glob("*.png")):
    print(path)
