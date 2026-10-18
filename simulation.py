
from device import build_messages
from router import Router

devices = {
    "device_1": 45,
    "device_2": 250,
    "device_3": 750,
    "device_4": 900,
}

# Synthetic router-observed metrics for demonstration.
router = Router(
    observed_metrics={
        "device_1": 45,
        "device_2": 250,
        "device_3": 750,
        "device_4": 100,
    },
    priority_seconds=10,
    max_metric_difference=100,
)

for device_id, value in devices.items():
    commit, reveal = build_messages(value)
    ack = router.receive_commit(device_id, commit)
    result = (
        router.receive_reveal(device_id, reveal)
        if ack["accepted"]
        else {"accepted": False, "reason": "Commit rejected"}
    )

    print(
        device_id,
        "claim =", value,
        "| result =", result["accepted"],
        "| reason =", result["reason"],
    )

print("\nPriority allocation:")
for device_id in devices:
    print(device_id, router.has_priority(device_id))
