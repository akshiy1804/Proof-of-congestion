# Proof-of-Congestion
## Part 2: Router-Side Verification, Simulation, and Results

### 1. Abstract

Proof-of-Congestion is a prototype that explores how a router can validate congestion claims made by devices sharing a network. Part 2 implements router-side commitment verification, cross-checking against router-observed congestion metrics, temporary priority allocation, multi-device simulation, automated testing, and result visualization.

The prototype uses a commitment-and-reveal mechanism based on SHA-256. The router stores commitment hashes and later checks whether the revealed congestion value and nonce match the original commitment. It also compares the claimed score with a synthetic router-observed score before granting temporary priority.

### 2. Problem Statement

In a shared network, a device might falsely claim severe congestion to request preferential bandwidth allocation. Trusting every claim could allow dishonest devices to obtain an unfair advantage.

The system therefore needs to validate the consistency of congestion claims, compare claims against independent observations, and apply a consistent priority policy.

### 3. Objectives

- Validate COMMIT messages and store their hashes.
- Timestamp commitment receipt.
- Verify later REVEAL messages using the existing commitment engine.
- Cross-check claimed values against router-observed metrics.
- Return a RESULT message indicating acceptance or rejection.
- Grant temporary priority and expire it after a configured time window.
- Simulate multiple devices, including a dishonest device.
- Produce automated tests, result logs, charts, and documentation.

### 4. System Architecture

The device-side component is implemented in `commitment_engine.py` and `device.py`. It creates commitments and prepares reveal messages.

The router-side component is implemented in `router.py`. It validates commitments, verifies reveals, checks observed metrics, records outcomes, and tracks temporary priority grants.

The multi-device simulation is implemented in `simulation.py`. It creates device claims and sends simulated messages to the router.

The results-generation script, `generate_results.py`, writes a CSV file and produces charts using Matplotlib.

### 5. Router Workflow

#### 5.1 COMMIT reception

The router receives a COMMIT message, validates its structure, checks that every configured tier has one valid commitment, and stores the hashes with a receipt timestamp.

Malformed or incomplete messages are rejected.

#### 5.2 REVEAL reception

The router receives the revealed congestion value, nonce, and tier ID. It checks whether a valid commitment session exists and whether the reveal is consistent with the stored commitment.

#### 5.3 Metric cross-check

After cryptographic verification, the router compares the claimed score with its configured observed score for that device.

The current simulation uses an allowed absolute difference of 100 points. Claims outside this tolerance are rejected.

#### 5.4 RESULT message

The router returns a RESULT message containing the device ID, acceptance status, reason, timestamp, and priority expiry timestamp when a grant is issued.

#### 5.5 Temporary priority

An accepted device receives a simulated priority grant for 10 seconds by default. The router checks whether that grant has expired when priority status is queried.

This implementation tracks priority in memory. It does not modify real router queues or bandwidth allocation.

### 6. Multi-Device Simulation

The demonstration uses four synthetic devices.

| Device | Claimed score | Observed score | Expected outcome |
|---|---:|---:|---|
| Device 1 | 45 | 45 | Accepted |
| Device 2 | 250 | 250 | Accepted |
| Device 3 | 750 | 750 | Accepted |
| Device 4 | 900 | 100 | Rejected |

Devices 1–3 submit claims consistent with the configured observed metrics. Device 4 claims a score of 900 while the router's simulated observed score is 100. Its claim exceeds the permitted tolerance and is rejected.

These values are synthetic inputs chosen to demonstrate the decision logic. They are not measurements collected from real network interfaces.

### 7. Testing Methodology

The project uses Python's built-in `unittest` framework.

The cryptographic tests cover tier boundaries, invalid values, commitment generation, reveal consistency, and detection of modified values, nonces, commitments, and tiers.

The router tests cover valid commitment messages, malformed messages, successful reveals, tampered reveals, metric mismatches, missing commitment sessions, and priority expiry.

Run the full suite with:

```bash
python -m unittest -v
```

The test count and results should be taken from the actual terminal output at the time of evaluation.

### 8. Results and Visualization

The results-generation script writes `results/simulation_results.csv`, which records each device's claim, observed score, decision, reason, and priority status.

It also generates:

- `results/congestion_comparison.png`: compares claimed and observed scores.
- `results/verification_outcomes.png`: shows the number of accepted and rejected devices.

For the four-device scenario, the expected result is three accepted claims and one rejected claim.

The charts summarize this particular synthetic scenario. They do not establish performance or accuracy under real network conditions.

### 9. Security Analysis and Limitations

#### Commitment consistency

SHA-256 commitment verification detects changes to committed data when the same payload is reconstructed correctly.

#### Congestion authenticity

A valid commitment does not prove that a device measured its congestion honestly. The router-observed metric cross-check is a separate simulated safeguard.

#### Authentication

The prototype does not implement device authentication or signed messages. A production system would need authenticated identities and protected communications.

#### Replay protection

The current design does not provide a complete replay-protection mechanism using unique session identifiers, nonces tied to sessions, and persistent protocol state.

#### Session and priority expiry

Priority expiration is checked in application logic. The prototype does not implement a background scheduler or actual network traffic shaping.

#### Simulation limitations

The router-observed metrics are supplied as synthetic values. No live network congestion measurements or physical router integration are implemented.

### 10. Future Improvements

- Connect the router to real measurement sources.
- Authenticate devices and protect messages in transit.
- Add session IDs, replay protection, and explicit protocol timeouts.
- Implement a live reveal-request/response exchange.
- Add a real priority queue or network scheduling mechanism.
- Evaluate multiple traffic patterns and larger device populations.
- Persist session state and audit logs securely.
- Conduct a formal security and performance evaluation.

### 11. Conclusion

Part 2 extends the cryptographic commitment mechanism with router-side verification, synthetic metric cross-checking, temporary priority tracking, multi-device simulation, automated tests, and visualization.

The prototype demonstrates how a router can detect a reveal that does not match its original commitment and reject a claim inconsistent with configured observed metrics.

It remains an educational simulation. Further work is required to authenticate devices, validate real congestion measurements, protect against replay, and connect priority decisions to an actual network scheduler.
