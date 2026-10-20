# Proof-of-Congestion (PoC)

A Cryptographic Prototype for Verifying Network Congestion Claims

## 1. Project Overview

Proof-of-Congestion (PoC) is a prototype designed to explore how a shared network can verify a device's congestion claim before considering it for preferential treatment.

In networks such as campus Wi-Fi, office networks, and public hotspots, devices compete for limited bandwidth. A device may claim that it is experiencing congestion and request additional network resources.

If a router trusts every claim, a dishonest device could falsely claim severe congestion to gain an unfair advantage over other devices. If the router rejects every claim, legitimate devices experiencing congestion may not receive appropriate treatment.

Proof-of-Congestion explores a cryptographic commitment-and-reveal mechanism that allows a device to commit to information before revealing it later. The router can then verify that the revealed information matches the original commitment.

**Important:** This repository implements a software prototype of the device-side cryptographic mechanism and router-side verification. It does not yet implement a complete production networking protocol or independently prove that a device's reported congestion measurement is genuine.

## 2. Problem Statement

Consider a shared network containing several devices.

- Device A experiences congestion and requests priority.
- Device B makes the same request despite having no genuine congestion.
- The router must distinguish valid, consistent claims from invalid or manipulated claims.

Simply trusting a device's reported congestion score creates an opportunity for abuse. A cryptographic commitment can prevent a device from changing the committed value without detection, assuming the commitment and its associated secret are generated and handled correctly.

However, commitment verification alone cannot establish that the original measurement was honest. Additional measurement validation and protocol safeguards are required for a complete solution.

## 3. Project Objectives

The prototype aims to:

1. Represent congestion using configurable severity tiers.
2. Generate cryptographic commitments using SHA-256.
3. Use random nonces to conceal committed values until reveal time.
4. Separate public commitment messages from private reveal information.
5. Validate incoming commitment messages at the router.
6. Verify revealed values against previously stored commitments.
7. Detect modified values, incorrect nonces, incorrect tiers, and malformed messages.
8. Provide automated tests for the core cryptographic and verification functions.

## 4. System Architecture

The current implementation contains two main components.

### 4.1 Device-side component

The device-side component prepares the congestion claim and generates the cryptographic commitments.

It is implemented in:

- `commitment_engine.py`
- `device.py`

The commitment engine validates congestion values, identifies the corresponding tier, generates nonces, calculates hashes, and prepares reveal data.

The device simulator packages the public commitments into a COMMIT message and prepares a separate REVEAL message.

### 4.2 Router-side component

The router-side component receives and validates the public commitments, stores the commitment hashes, and verifies a later reveal.

It is implemented in:

- `router.py`

The router checks the structure of the COMMIT message, verifies that all configured tiers are represented, rejects malformed hashes and duplicate tier entries, and validates the revealed value against the stored commitment.

### 4.3 Testing component

Automated tests verify the behavior of the cryptographic engine and router verification.

- `test_commitment_engine.py`
- `test_router.py`

The tests cover tier boundaries, invalid inputs, valid commitments, modified reveals, and malformed commitment messages.

## 5. Repository Structure

```text
Proof-of-congestion/
├── commitment_engine.py
├── device.py
├── router.py
├── test_commitment_engine.py
├── test_router.py
├── README.md
└── .gitignore
```

### File descriptions

| File | Responsibility |
|---|---|
| `commitment_engine.py` | Tier configuration, SHA-256 commitments, nonce generation, reveal preparation, and commitment verification |
| `device.py` | Command-line simulation of device-side COMMIT and REVEAL messages |
| `router.py` | Validation of public commitments and verification of reveal messages |
| `test_commitment_engine.py` | Unit tests for tier handling, commitments, and reveal behavior |
| `test_router.py` | Unit tests for router-side commitment and reveal validation |
| `README.md` | Project documentation, setup instructions, architecture, and limitations |
| `.gitignore` | Specifies files and directories Git should not track |

## 6. Technologies Used

- **Python 3:** Implements the prototype and its message-processing logic.
- **SHA-256:** Produces fixed-length cryptographic commitment hashes.
- **Python `hashlib`:** Calculates SHA-256 digests.
- **Python `secrets`:** Generates cryptographically strong random nonces.
- **Python `json`:** Serializes commitment payloads into a consistent representation.
- **Python `unittest`:** Runs automated tests without requiring a third-party testing framework.
- **Git and GitHub:** Support source-code management and team collaboration.

The core implementation uses Python's standard library and does not require third-party packages.

## 7. Congestion Tier Configuration

The prototype defines three congestion tiers in `commitment_engine.py`.

| Tier ID | Congestion score | Description |
|---|---:|---|
| 1 | 1–100 | Mild congestion |
| 2 | 101–300 | Moderate congestion |
| 3 | 301–1000 | Severe congestion |

The `get_tier()` function determines which tier contains a supplied congestion score.

For example:

- A score of `45` belongs to Tier 1.
- A score of `250` belongs to Tier 2.
- A score of `750` belongs to Tier 3.

Scores outside the configured ranges are rejected.

The tier configuration must remain consistent between the device and router because both components use the same tier boundaries during commitment generation and reveal verification.

These values are demonstration settings, not calibrated measurements of real network congestion.

## 8. Cryptographic Commitment Mechanism

The prototype uses a commitment scheme based on SHA-256.

A commitment is calculated from four fields:

- Protocol context
- Tier ID
- Congestion value
- Random nonce

The payload is serialized as canonical JSON using sorted keys and compact separators before being hashed.

Conceptually:

```text
payload = {
    context,
    tier_id,
    value,
    nonce
}

commitment = SHA256(canonical_json(payload))
```

The resulting SHA-256 digest is represented as a 64-character hexadecimal string.

### 8.1 Why use a nonce?

A nonce is a random secret value included in the commitment.

Without a sufficiently unpredictable nonce, an observer who knows the possible congestion scores might try candidate values and compare their hashes. A random nonce makes this guessing strategy substantially harder.

### 8.2 Why include the tier ID?

Including the tier ID binds the commitment to a particular tier. A reveal created for one tier will not verify against a commitment for another tier when the tier ID is included consistently.

### 8.3 Why include the protocol context?

The context identifies the protocol version and separates commitments intended for this protocol from commitments used in other contexts.

The current context string is:

`proof-of-congestion-v1`

### 8.4 What does a commitment guarantee?

Under the intended use of a secure hash and a properly generated nonce, changing the committed value, nonce, tier, or context will cause verification to fail.

A commitment does not prove that the committed value was measured honestly. It also does not, by itself, prevent replay, guarantee message delivery, or establish that the sender is an authenticated device.

## 9. Device-Side Workflow

The device-side workflow is implemented in `commitment_engine.py` and `device.py`.

### Step 1: Obtain a congestion score

The device simulator accepts a congestion score through a command-line argument or generates a random valid score when no argument is provided.

### Step 2: Determine the actual tier

The `get_tier()` function identifies the tier containing the supplied score.

### Step 3: Generate one commitment per tier

The `generate_commitments()` function creates a commitment for each configured tier.

For the actual tier, it uses the supplied congestion value.

For the other tiers, it generates random values within their respective ranges.

Each commitment uses a separately generated random nonce.

### Step 4: Separate public and private information

The function returns three fields:

- `commitments`: the public list of tier IDs and hashes.
- `private_reveals`: locally retained values and nonces associated with each tier.
- `real_tier_id`: the ID of the actual tier.

Only the commitment list belongs in the public COMMIT message. The private reveal mapping should remain on the device.

### Step 5: Prepare the COMMIT message

The device packages the public commitments into a message with the type `commit`.

The router can receive the hashes before the actual congestion value and nonce are revealed.

### Step 6: Prepare the REVEAL message

The simulator prepares a separate message containing the actual congestion value, its original nonce, and its tier ID.

In a real deployment, the device should send this message only at the protocol-defined reveal stage, such as after an authenticated router request.

The current command-line demonstration prints both messages for educational purposes. It does not implement a live request-response exchange.

## 10. Router-Side Workflow

The router-side logic is implemented in `router.py`.

### Step 1: Receive a COMMIT message

The router receives a message that should contain the type `commit` and a list of commitments.

### Step 2: Validate the message structure

The `validate_commit()` function checks:

- The message type is correct.
- The commitments field is a list.
- Each commitment entry has the expected structure.
- Every tier ID is a valid configured integer.
- No tier ID appears more than once.
- Every hash has the expected 64-character hexadecimal format.
- Every configured tier has a commitment.

Invalid commitment messages are rejected with a `ValueError`.

### Step 3: Store the commitment hashes

The function returns a mapping from tier IDs to commitment hashes.

In this prototype, the mapping is held in memory. Persistent storage, expiration policies, and protection against replay have not been implemented.

### Step 4: Receive a REVEAL message

The router receives the revealed value, nonce, and tier ID in a separate message.

### Step 5: Validate the reveal

The `verify_reveal()` function checks the message type, tier ID, and nonce format before calling the cryptographic verification function.

### Step 6: Check the commitment

The underlying `verify()` function checks that:

1. The value is an integer and falls within the claimed tier's configured range.
2. The nonce and commitment have acceptable formats.
3. The commitment recalculated from the reveal matches the stored hash.

If these checks succeed, the reveal is consistent with the stored commitment and tier.

If the value, nonce, tier, or commitment does not match, verification fails.

### Step 7: Decide how to handle the claim

A successful verification means the reveal matches the earlier commitment. It should not automatically be treated as proof of genuine congestion.

A complete system would additionally validate measurements, authenticate devices, apply replay protection, enforce rate limits, and use an explicit network scheduling policy.

## 11. Example: Device-to-Router Exchange

Consider a device reporting a congestion score of `250`.

The score falls within Tier 2.

The device creates three commitments:

- Tier 1: commitment to a randomly generated value in the mild range.
- Tier 2: commitment to the actual value `250`.
- Tier 3: commitment to a randomly generated value in the severe range.

Each commitment has its own nonce.

The device sends the public commitment list to the router. The router validates and stores the three hashes.

Later, the device reveals the value `250`, the corresponding original nonce, and Tier 2.

The router recalculates the hash using the same context, tier, value, and nonce. If the hash matches the stored Tier 2 commitment and the value is within the Tier 2 range, the reveal is accepted.

If the revealed value is changed to `251` without changing the original commitment, verification fails.

This example demonstrates commitment consistency, not independent proof that the network actually experienced the reported congestion.

## 12. Installation and Setup

### Prerequisites

Install Python 3 and Git.

Verify that Python is available:

```bash
python --version
```

On some systems, use:

```bash
python3 --version
```

Clone the repository:

```bash
git clone https://github.com/akshiy1804/Proof-of-congestion.git
```

Move into the project directory:

```bash
cd Proof-of-congestion
```

No additional package installation is required for the current standard-library implementation.

## 13. Running the Device Simulation

To simulate a device reporting a congestion score of `250`:

```bash
python device.py --value 250
```

To generate a random valid congestion score:

```bash
python device.py
```

The program prints the COMMIT message first and the REVEAL message second.

The displayed hashes and nonces will differ between runs because the nonces are generated randomly.

The printed messages are illustrative JSON output, not network packets exchanged with a real router.

## 14. Running the Tests

Run the complete test suite from the project directory:

```bash
python -m unittest -v
```

If your system uses `python3`, run:

```bash
python3 -m unittest -v
```

### Existing cryptographic tests

`test_commitment_engine.py` covers:

- Tier boundary handling.
- Rejection of out-of-range scores.
- Rejection of invalid score types.
- Successful commitment verification.
- Detection of a modified value.
- Detection of a modified nonce.
- Detection of a modified commitment.
- Detection of an incorrect tier.
- Rejection of values outside the claimed tier.
- Generation of one commitment per tier.
- Use of the original nonce in a reveal message.

### Router verification tests

`test_router.py` covers:

- Acceptance of a valid reveal.
- Rejection of a modified reveal.
- Rejection of a commitment message with a missing tier.

A passing test suite confirms the tested behaviors for the implemented prototype. It does not establish the security of a complete production deployment.

## 15. Security Considerations and Limitations

This project is an educational prototype and has several important limitations.

### 15.1 No independent measurement verification

The commitment mechanism verifies consistency between an earlier hash and a later reveal. It does not prove that the original congestion score was measured honestly.

A malicious device may still commit to a fabricated score.

### 15.2 No device authentication

The current code does not establish device identity or authenticate messages using a trusted identity system.

### 15.3 No live network communication

The device and router communicate through simulated Python objects and printed messages. There is no implemented socket protocol, wireless integration, or router firmware integration.

### 15.4 No replay protection

The prototype does not maintain protocol session IDs, timestamps, expiration rules, or replay-detection records.

### 15.5 No persistent commitment storage

Router-side commitments are held in memory. Restarting the process loses the stored mappings.

### 15.6 No complete priority-allocation mechanism

The prototype does not implement bandwidth scheduling, queue management, or a policy for assigning network resources after verification.

### 15.7 Reveal protocol is not fully implemented

The simulator prepares and prints both stages. It does not wait for a router request, enforce protocol timeouts, or manage multiple concurrent sessions.

### 15.8 Hash verification is not a digital signature

A matching commitment establishes consistency with the committed data. It does not authenticate the sender or prove who created the commitment.

### 15.9 Nonce handling is critical

Reveal secrets must remain private until the reveal stage. A production system must protect them against logging, leakage, reuse, and unauthorized access.

These limitations define the boundary between the current prototype and a complete network security system.

## 16. Future Improvements

Possible next steps include:

1. Implement a real router-device message exchange.
2. Add unique session identifiers and protocol state management.
3. Add authenticated device identities and secure message transport.
4. Implement replay protection and commitment expiration.
5. Add independent or trusted validation of congestion measurements.
6. Define a secure reveal-request and response protocol.
7. Add rate limiting and abuse detection.
8. Integrate verification with a network scheduling policy.
9. Add integration tests for malformed messages and repeated sessions.
10. Evaluate performance under concurrent devices and simulated congestion.
11. Improve logging and error handling without exposing secret nonces.
12. Document a threat model and conduct a security review before deployment.

## 17. Team Contribution and Integration

The repository is organized around device-side commitment generation and router-side verification.

The device-side component provides the commitment and reveal data structures. The router-side component validates incoming commitments and checks later reveals using the same cryptographic rules and tier configuration.

The two components are designed to work together while keeping the device's private reveal information separate from the public commitment message.

Individual contributor responsibilities should be documented according to the team's actual division of work.

## 18. Conclusion

Proof-of-Congestion demonstrates how cryptographic commitments can help detect changes to a congestion claim between commitment and reveal.

The prototype combines SHA-256 hashing, random nonces, tier-based value validation, separate message stages, and automated tests.

It provides a foundation for further investigation into fairer handling of congestion claims on shared networks.

However, cryptographic consistency is only one part of the problem. A production-ready solution must also establish measurement credibility, device authenticity, replay protection, reliable protocol execution, and a safe network resource-allocation policy.

**Project status:** Educational prototype. Not intended for direct production deployment.
