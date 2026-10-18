
"""Router-side protocol, verification, simulation metrics, and priority expiry."""

from __future__ import annotations

import time
from typing import Any

from commitment_engine import TIERS, PROTOCOL_CONTEXT, verify


def validate_commit(message: dict[str, Any]) -> dict[int, str]:
    """Validate and extract one commitment for every configured tier."""
    if not isinstance(message, dict) or message.get("type") != "commit":
        raise ValueError("Invalid message type")

    entries = message.get("commitments")
    if not isinstance(entries, list):
        raise ValueError("Commitments must be a list")

    stored: dict[int, str] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid commitment entry")

        tier_id = entry.get("tier_id")
        commitment = entry.get("commitment")

        if type(tier_id) is not int or tier_id not in TIERS:
            raise ValueError("Unknown tier")
        if tier_id in stored:
            raise ValueError("Duplicate tier")
        if (
            not isinstance(commitment, str)
            or len(commitment) != 64
            or any(c not in "0123456789abcdef" for c in commitment)
        ):
            raise ValueError("Invalid commitment hash")

        stored[tier_id] = commitment

    if set(stored) != set(TIERS):
        raise ValueError("A commitment for every tier is required")

    return stored


def verify_reveal(
    commitments: dict[int, str],
    message: dict[str, Any],
) -> bool:
    """Verify the reveal against the commitment for its tier."""
    if not isinstance(message, dict) or message.get("type") != "reveal":
        return False

    tier_id = message.get("tier_id")
    value = message.get("value")
    nonce = message.get("nonce")

    if type(tier_id) is not int or tier_id not in TIERS:
        return False
    if not isinstance(nonce, str) or not nonce:
        return False

    return verify(
        commitment=commitments.get(tier_id, ""),
        value=value,
        nonce=nonce,
        tier_range=TIERS[tier_id],
        tier_id=tier_id,
        context=PROTOCOL_CONTEXT,
    )


class Router:
    """In-memory router simulation with metric checks and expiring priority."""

    def __init__(
        self,
        observed_metrics: dict[str, int],
        priority_seconds: float = 10.0,
        max_metric_difference: int = 100,
    ):
        if priority_seconds <= 0:
            raise ValueError("priority_seconds must be positive")
        if max_metric_difference < 0:
            raise ValueError("max_metric_difference cannot be negative")

        self.observed_metrics = observed_metrics
        self.priority_seconds = priority_seconds
        self.max_metric_difference = max_metric_difference
        self.sessions: dict[str, dict[str, Any]] = {}
        self.priority_until: dict[str, float] = {}
        self.logs: list[dict[str, Any]] = []

    def receive_commit(
        self, device_id: str, message: dict[str, Any]
    ) -> dict[str, Any]:
        """Timestamp and store a device's commitments."""
        now = time.time()

        try:
            if not isinstance(device_id, str) or not device_id:
                raise ValueError("Invalid device ID")

            commitments = validate_commit(message)
            self.sessions[device_id] = {
                "commitments": commitments,
                "commit_time": now,
            }
            return {
                "type": "COMMIT_ACK",
                "device_id": device_id,
                "accepted": True,
                "timestamp": now,
            }
        except (ValueError, TypeError) as exc:
            return {
                "type": "COMMIT_ACK",
                "device_id": device_id,
                "accepted": False,
                "reason": str(exc),
                "timestamp": now,
            }

    def receive_reveal(
        self,
        device_id: str,
        message: dict[str, Any],
        now: float | None = None,
    ) -> dict[str, Any]:
        """Verify a reveal, cross-check metrics, and issue a RESULT."""
        now = time.time() if now is None else now
        session = self.sessions.get(device_id)
        reason = "accepted"

        if session is None:
            reason = "No valid commitment session"
        elif now < session["commit_time"]:
            reason = "Reveal timestamp precedes commitment"
        elif not verify_reveal(session["commitments"], message):
            reason = "Cryptographic verification failed"
        elif device_id not in self.observed_metrics:
            reason = "No router-observed metric available"
        else:
            observed = self.observed_metrics[device_id]
            claimed = message.get("value") if isinstance(message, dict) else None

            if (
                type(observed) is not int
                or type(claimed) is not int
                or abs(observed - claimed) > self.max_metric_difference
            ):
                reason = "Claim does not match observed metrics"

        accepted = reason == "accepted"

        if accepted:
            self.priority_until[device_id] = now + self.priority_seconds
        else:
            self.priority_until.pop(device_id, None)

        result = {
            "type": "RESULT",
            "device_id": device_id,
            "accepted": accepted,
            "reason": reason,
            "timestamp": now,
            "priority_until": self.priority_until.get(device_id),
        }
        self.logs.append(result.copy())
        return result

    def has_priority(self, device_id: str, now: float | None = None) -> bool:
        """Return whether a device's temporary priority is still active."""
        now = time.time() if now is None else now
        expiry = self.priority_until.get(device_id)

        if expiry is None:
            return False
        if now >= expiry:
            del self.priority_until[device_id]
            return False
        return True

    def expire_priorities(self, now: float | None = None) -> list[str]:
        """Remove expired grants and return the affected device IDs."""
        now = time.time() if now is None else now
        expired = [
            device_id
            for device_id, expiry in self.priority_until.items()
            if now >= expiry
        ]

        for device_id in expired:
            del self.priority_until[device_id]

        return expired
