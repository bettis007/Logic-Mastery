# Transactional delivery and corroborated-context study

Date: September 15, 2026.

## Decision

The delivery prototype passes its bounded fixture tests. The context detector remains experimental: off-bin recall and both-wrong-context recall fail frozen gates. No live server integration or automatic blocking is enabled.

All seeds, measurements and hashes are preserved without number-based filtering. Numerical appearance is not an integrity test. Comparisons use authenticated bytes, exact replay and explicit expected outcomes.

## Local delivery prototype

An allowed decision inserts a queue row inside the same SQLite transaction as replay state and its receipt. Review/rejection decisions create no queued effects. A single delivery worker authenticates the receipt, derives a stable effect ID and inserts it into a separate local SQLite sink with a unique key. After a process exit following sink commit, recovery compares the stored payload and MAC before acknowledging the queue row.

Attempts are bounded and persist across restart, with exponential backoff. Exhausted work stops for review. This is a demonstration with a local database sink; a remote API would need a compatible idempotency contract. No financial transfer, device action or network request is performed.

Delivery tests: 9/9 passed. Existing receipt regression tests also passed.

- after commit crash recovery
- altered receipt blocks delivery
- before commit crash recovery
- delivery once
- duplicate queues once
- persistent bounded retries
- review does not queue effect
- sink crash recovery
- transient failure recovers

Limitations: single delivery worker assumed; attempt settings are caller-controlled, not cryptographically bound; retry metadata is not authenticated; a queued exhausted entry blocks later entries until manual intervention; retention/dead-letter management is unimplemented. Record deletion or rollback by a privileged actor is not prevented. The process-crash tests do not establish power-loss durability or arbitrary external exactly-once effects. Message authentication still uses a publicly disclosed synthetic fixture key; receipt keys are fresh random values kept out of reports.

## Context and wider-spectrum study

Development: 12,000 benign examples, seed 2026091501. Retain the earlier known-component threshold and calibrate a residual-spectrum threshold at the maximum per-slice 99.75th percentile. Freeze configuration before accessing seed 2026091502.

Test: 48,000 new synthetic examples, equal-sized slices. Compare narrow and broader spectral review rules on the same samples. All use two separately keyed simulated attestations. The operational registry and producer declarations are built before samples. This construction is not a real independent witness or a measured operational source.

The check requires both MACs, matching example IDs, valid time intervals and identical declarations. Invalid/missing context requests review; it does not attribute an attack. Separate public fixture keys test role separation but do not provide deployment security. Both sources can agree on an incorrect declaration.

The broader rule reviews excessive residual energy across positive FFT bins, excluding DC and Nyquist. The prior mean check covers DC separately. Sample arrays have no declared physical sampling rate, so this study makes no claim about RF frequency coverage.

| Slice | Narrow review rate | Broader review rate |
|---|---:|---:|
| bad_signature | 100.000% | 100.000% |
| both_wrong | 0.325% | 0.750% |
| clean | 0.275% | 0.600% |
| missing_registry | 100.000% | 100.000% |
| off_bin | 0.275% | 2.750% |
| periodic | 0.200% | 0.525% |
| producer_wrong | 100.000% | 100.000% |
| stale_registry | 100.000% | 100.000% |
| stress | 0.200% | 0.650% |
| strong | 100.000% | 100.000% |
| weak | 51.875% | 51.900% |
| wrong_example_binding | 100.000% | 100.000% |

| Frozen gate | Outcome |
|---|---|
| bad_signature_review | PASS |
| both_wrong_recall | FAIL |
| clean_false_alarm | PASS |
| missing_registry_review | PASS |
| off_bin_recall | FAIL |
| periodic_false_alarm | PASS |
| producer_wrong_review | PASS |
| stale_registry_review | PASS |
| stress_false_alarm | PASS |
| strong_recall | PASS |
| weak_recall | PASS |
| wrong_example_binding_review | PASS |

Gate definitions: benign false alarms <=1%; weak, off-bin and both-wrong recall >=50%; strong recall >=99%; invalid/missing/mismatched context review 100%. The test configuration records these bounds before holdout scoring. There was no tuning after reading holdout results and no number-based rerun selection.

A second fresh process reproduced the entire heldout result object exactly. Additional declaration checks exercised both validity endpoints, expiry, role swapping, example binding and disagreement. Raw output and configuration are saved beside this report. These are internal synthetic tests, not independent real-world validation.

## Remaining work

Add explicit dead-letter handling and bounded retention before deploying an outbox. Independently controlled operational evidence is needed to evaluate context truth. Improve off-bin modeling using new development data and another untouched test set; preserve this failed test set as a regression fixture.

## Reproduce

- `python test_transactional_delivery.py`
- `python test_receipt_guard.py`
- `python corroborated_context_study.py develop --config results/new_context_config.json`
- `python corroborated_context_study.py evaluate --config results/new_context_config.json --output results/new_context_results.json`

Use fresh output filenames. Scripts do not access RF hardware, user networks or external systems.

## Hashes

- receipt_guard.py: `407c5261e6f9dd526966b26c35a2928678c1e0e0067362fb247e5cfa2ad104cb`
- transactional_delivery.py: `478d5f19e7bfaaa44f72718dec5399870a988013fa7230529484d07450c19ec7`
- test_transactional_delivery.py: `e9f353cc8fa00b5a5239c09612d56630a839747e6d5e3bb4d93c95265ed59f28`
- corroborated_context_study.py: `7c8bcdbb246bcfa05ddc58a04a1e4fd5c0b12f13bb5b49b5073da3d220d446b2`
- docs/corroborated_context_config.json: `046ddef3997555b8aaec0731b7a2e59e67198a1c6ae444205f7799c794d53d18`
- docs/corroborated_context_holdout.json: `737826725896ab55df18bfcc60a1b1fe0ab57dd743d8c8f5a2717912b1edcb3a`
- docs/transactional_delivery_checks.json: `2a60f19e80f72aa55f15201ec1707c732721cb73bd270fdacbe7cad7bdb9810a`
- Canonical decision trace: `02c0c6f5a7b977ceff6cd393031b44f8bc7f0bb89b8c46e34b349435d8fbbf1d`
