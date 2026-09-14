# Logic Mastery

Offline-first evidence workbench for claim triage, explicit confidence reporting, deterministic replay, and reproducible validation.

## Project status

Research prototype under development. This repository currently documents the design and validation status; the tested application files have **not yet been uploaded**. The development workspace disconnected before publication. There is no hosted application or runnable installation in this repository yet.

Development follows a simulation-first workflow: implement bounded behavior, test it against explicit expectations, preserve evidence, and refine the design before cloud deployment.

## Application design

The local prototype includes:

- Numeric evidence input, synthetic demo cases, and input validation.
- A decision ledger with filtering and per-case inspection.
- Separate reference-label import and evaluation.
- Comparison with previous prediction receipts and JSON audit export.
- A Python loopback HTTP server with session-token and origin checks.
- In-memory model reuse to avoid rebuilding the same reference model on every request.

Inputs are numeric features, not an automatic document-understanding or fact-verification system. A policy acceptance means that the encoded evidence meets the simulator's rules; it does not establish external truth.

## Confidence and evidence boundaries

The interface distinguishes the classifier's most probable label from the final policy label.

| Field | Meaning |
|---|---|
| Classifier top-label probability | Model probability for its preferred label |
| Final-label model probability | Model probability for the label ultimately selected by policy |
| Policy override | Whether policy changed the classifier's preferred label |
| Post-policy correctness probability | Unknown; no independently calibrated value is claimed |

Simulated, narrative, conceptual, and unverified claims must retain their evidence category. Synthetic test success does not promote them to real-world facts. No hidden model-weight changes are claimed.

## Development validation recorded on September 14, 2026

These are local development measurements. Their source files and raw receipts remain pending upload, so they are not yet reproducible from this repository.

| Check | Observed result |
|---|---:|
| Integration checks | 9 passed |
| Synthetic policy-contract checks | 92 passed |
| Local HTTP checks | 10 passed |
| JavaScript syntax and Python compilation | Passed |
| Model-cache comparison | Identical prediction records for tested batches |
| Browser visual and interaction review | Incomplete: local preview access blocked |
| Independent external labeled evaluation | Incomplete: no suitable independent labels supplied |

The policy cases are authored synthetic contracts, not a blind external benchmark.

For a 1,000-case batch, median local prediction time was approximately **154.15 ms with model rebuilding versus 7.14 ms with a warm cached model** (about 21.6 times faster). This measures avoided model construction on the development host. It is not a cloud-latency, hardware-acceleration, or general intelligence result.

## Publication and release gates

1. Reconnect the development workspace and publish the reviewed public-safe source, tests, and reproducibility instructions.
2. Complete browser visual, interaction, and accessibility checks.
3. Evaluate against independently labeled examples with documented provenance and category definitions.
4. Preserve deterministic replay and distinguish classifier calibration from final-policy calibration.
5. Define production identity, storage, retention, and deployment requirements.
6. Select and validate a Google Cloud deployment after the application design stabilizes.

Private source documents, recovered attachments, credentials, and private working history are excluded from the public release. The public numerical reference is intended to omit documentary narratives; this changes its source bytes and requires explicit provenance documentation.

## Repository description

Suggested GitHub About text:

> Offline-first evidence workbench for claim triage, explicit confidence reporting, deterministic replay, and reproducible validation.

This README does not change GitHub's About metadata.

## License

MIT. See [LICENSE](LICENSE).
