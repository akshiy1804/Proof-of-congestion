# Proof-of-Congestion: Demo Runbook

## 1. Purpose

This demonstration shows how the device-side commitment mechanism and router-side verification work together.

It demonstrates:

- Generation of SHA-256 commitments.
- Verification of a valid reveal.
- Detection of a tampered reveal.
- Cross-checking against simulated router-observed congestion metrics.
- Temporary priority allocation and expiry.
- Automated testing and result visualization.

**Scope:** This is a local Python simulation. It does not communicate with a physical router or measure live network traffic.

## 2. Prerequisites

- Python 3 installed.
- The project repository cloned locally.
- `commitment_engine.py`, `device.py`, `router.py`, `simulation.py`, and test files present.
- Matplotlib installed for generating charts.

Install Matplotlib if needed:

```bash
python -m pip install matplotlib
```

Open a terminal in the project root.

## 3. Demonstration Sequence

### Step 1: Run the device simulation

```bash
python device.py --value 250
```

Expected behavior:

- The device identifies the score as Tier 2.
- A COMMIT message containing three hashes is printed.
- A separate REVEAL message containing the actual score, nonce, and tier ID is printed.

Explain that the demonstration prints both messages for learning. A real protocol would control when the reveal is sent.

### Step 2: Demonstrate cryptographic verification

Run:

```bash
python -c "from device import build_messages; from router import validate_commit, verify_reveal; c, r = build_messages(250); s = validate_commit(c); print('Commit accepted:', len(s) == 3); print('Valid reveal:', verify_reveal(s, r)); r['value'] = 251; print('Tampered reveal rejected:', not verify_reveal(s, r))"
```

Expected output:

```text
Commit accepted: True
Valid reveal: True
Tampered reveal rejected: True
```

Explain that changing the revealed value causes verification to fail because the recalculated hash no longer matches the stored commitment.

### Step 3: Run the multi-device simulation

```bash
python simulation.py
```

The simulation uses four synthetic devices.

Expected outcomes:

| Device | Claim | Observed score | Outcome |
|---|---:|---:|---|
| Device 1 | 45 | 45 | Accepted |
| Device 2 | 250 | 250 | Accepted |
| Device 3 | 750 | 750 | Accepted |
| Device 4 | 900 | 100 | Rejected |

Explain that Device 4's claim conflicts with the router's simulated observed metric and exceeds the configured tolerance.

### Step 4: Run the automated tests

```bash
python -m unittest -v
```

Expected behavior: all tests pass, including cryptographic validation, router verification, metric mismatch, and priority expiry tests.

Use the actual test summary from the terminal when reporting the number of passing tests.

### Step 5: Generate result files and charts

```bash
python generate_results.py
```

Expected output files:

```text
results/
├── simulation_results.csv
├── congestion_comparison.png
└── verification_outcomes.png
```

Open the two PNG files in VS Code to show the comparison of claimed versus observed scores and the number of accepted versus rejected claims.

## 4. Presentation Script

1. Introduce the problem of devices making dishonest congestion claims.
2. Explain SHA-256 commitments and random nonces.
3. Run the device simulation and show the COMMIT and REVEAL messages.
4. Run the cryptographic verification example and show the tampering test.
5. Run the multi-device simulation and explain why Device 4 is rejected.
6. Show the unit-test results and generated charts.
7. Explain the security limitations and future improvements.

## 5. Troubleshooting

### Python command not found

On Windows, try:

```powershell
py -m unittest -v
```

### Matplotlib is missing

Run:

```powershell
python -m pip install matplotlib
```

### A test fails

Read the first failing test and traceback. Do not claim the test suite passes until the failure is fixed and the tests are rerun.

### Results directory is missing

Run `python generate_results.py` from the project root. The script should create the directory.

### Git push is rejected

Run `git status` and inspect the error. Do not force-push over the shared branch.

## 6. Security Notes

- Commitment verification confirms consistency with the original hash, not genuine congestion.
- The router-observed metrics in this demonstration are synthetic.
- Priority tracking is simulated in memory.
- Device authentication, robust replay protection, real network communication, and actual traffic scheduling remain future work.

## 7. Successful Demonstration Checklist

- [ ] Device simulation runs.
- [ ] Original reveal verifies.
- [ ] Tampered reveal is rejected.
- [ ] Multi-device simulation rejects the inconsistent claim.
- [ ] All automated tests pass.
- [ ] CSV and chart files are generated.
- [ ] The limitations are clearly explained.
