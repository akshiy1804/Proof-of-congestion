import csv
import statistics
from collections import defaultdict

path = "results/range_calibration_final.csv"
groups = defaultdict(list)

with open(path, newline="") as f:
    for row in csv.DictReader(f):
        groups[row["condition"]].append({
            "score": int(row["score"]),
            "latency": float(row["latency_ms"]),
            "loss": float(row["packet_loss_pct"]),
            "tier": int(row["current_tier"]),
        })

print(f"{'Condition':<15} {'N':>3} {'Mean':>9} {'Median':>9} "
      f"{'Std dev':>9} {'Min':>7} {'Max':>7} {'Mean loss':>11}")
print("-" * 78)

for condition, data in groups.items():
    scores = [r["score"] for r in data]
    losses = [r["loss"] for r in data]
    sd = statistics.stdev(scores) if len(scores) > 1 else 0.0

    print(f"{condition:<15} {len(scores):>3} "
          f"{statistics.mean(scores):>9.1f} "
          f"{statistics.median(scores):>9.1f} "
          f"{sd:>9.1f} {min(scores):>7} {max(scores):>7} "
          f"{statistics.mean(losses):>10.1f}%")
