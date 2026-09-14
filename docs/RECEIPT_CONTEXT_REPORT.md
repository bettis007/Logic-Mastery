# Recovery receipts and context review study

## Disposition

Keep the context rule experimental. It fails two frozen gates. The receipt prototype is a standalone developer component and is not installed into the app server. No hardware, RF measurements, biological model or external service is involved.

## Receipt recovery

12/12 tests passed with disposable SQLite ledgers and fresh random receipt keys. No keys are written to test results.

- after commit atomic recovery
- altered receipt rejected
- altered state rejected
- before commit atomic recovery
- concurrent duplicate same receipt
- duplicate does not add receipt
- duplicate returns original receipt
- invalid message cannot recover receipt
- rate rejection receipt is stable
- restart recovers receipt
- sequence payload conflict rejected
- wrong receipt key rejected

Replay state and receipt are committed in one SQLite transaction. After a process exit following commit, retry returns the original authenticated receipt. Before commit, retry performs the uncommitted decision. Duplicate calls never imply new authorization to execute a downstream effect. Downstream effects and exactly-once delivery are outside this prototype.

Receipt and state HMACs use separate domain prefixes and a caller-supplied key of at least 32 bytes. Message authentication still uses the public synthetic fixture key. This is not sender enrollment or a production authentication deployment. Anyone holding a shared receipt key can forge receipts; no nonrepudiation is claimed.

Authentication detects the tested byte alterations, not rollback of an entire earlier valid database. There is no external monotonic witness, key rotation, ledger retention limit, or power-loss durability test. A same-sequence request with a different authenticated payload is rejected. A rate-rejected request returns the same original rejection on retry; a new request requires a new sequence. Duplicate receipt recovery does not consume a new quota slot and is not independently rate-limited, so request flooding needs a separate boundary.

## Context experiment

Development: 9,000 benign synthetic examples, seed 730127. Before holdout access, select the maximum per-slice 99.5th percentile of standardized known-phase amplitude/mean residual. Frozen threshold: 3.1766241653501774.

Holdout: seed 830129, 40,000 new synthetic examples, 4,000 in each of ten slices. Compare the frozen previous experimental detector (spectral threshold 0.485 plus mean rule) on the same samples. This is not a comparison against the older 0.6/RMS baseline or independent external data.

Context supplies expected amplitude, DFT bin/phase and noise scale. Those values are exact synthetic metadata, not estimated from real operational records. No physical sample rate or RF frequency is inferred. Invalid or missing context routes to review. A public fixture HMAC distinguishes planted invalid signatures from valid ones; it does not authenticate real-world truth.

| Slice | Without context: review rate | Context: review rate |
|---|---:|---:|
| clean | 1.175% | 0.300% |
| dc_shift | 100.000% | 100.000% |
| forged_context | 62.375% | 100.000% |
| legitimate_periodic_change | 61.475% | 0.300% |
| legitimate_stress | 0.000% | 0.150% |
| missing_context | 61.250% | 100.000% |
| off_bin_weak | 0.925% | 0.225% |
| signed_wrong_context | 62.775% | 0.250% |
| strong_tone | 100.000% | 100.000% |
| weak_tone | 62.075% | 49.875% |

| Frozen gate | Outcome |
|---|---|
| clean_false_alarm | PASS |
| forged_context_review | PASS |
| legitimate_periodic_change_false_alarm | PASS |
| legitimate_stress_false_alarm | PASS |
| missing_context_review | PASS |
| signed_wrong_context_recall | FAIL |
| strong_recall | PASS |
| weak_recall | FAIL |

Gate bounds: each benign slice <=1% review; weak-tone recall >=50%; strong-tone recall >=99%; invalid/missing context review 100%; signed-wrong context recall >=50%. Off-bin and DC slices are diagnostics without a predeclared threshold. Weak recall 49.875% fails even though it is near the cutoff. No tuning followed holdout inspection.

The legitimate periodic-change and signed-wrong-context slices deliberately present statistically equivalent observations/context with different evaluator labels. The near-zero review of signed-wrong context is an expected information limit, not evidence that signatures detect truth. The off-bin weak-tone review rate also fell from 0.925% to 0.225%; this known-phase detector provides little coverage there.

A second fresh process reproduced the full held-out result object exactly. Receipt tests use fresh random keys, so receipt bytes across separate test campaigns are intentionally not claimed to match. Within duplicate/recovery tests, original receipt bodies and MACs match exactly.

## Next bounded work

- Define durable effect IDs and transactional delivery before integrating receipt recovery with real actions; add bounded retention and retry-rate limits.
- Treat missing context as review, and verify expected-operation declarations against independently controlled records. A signature alone cannot address a compromised or mistaken context producer.
- Develop a new context estimator and wider-bin diagnostic on a separate development set, then reserve new held-out data. Do not optimize on this failed holdout.

## Reproduce

`python test_receipt_guard.py`

`python context_guard_study.py develop --config results/new_context_config.json`

`python context_guard_study.py evaluate --config results/new_context_config.json --output results/new_context_holdout.json`

These commands perform local software simulations only. Use new output paths.

## Hashes

- receipt_guard.py: `e96fd24854cd87a4a217699309e53656f9e9744e5b996cc035cb633589607962`
- test_receipt_guard.py: `adc948f261514a2de529b0d07583b4bcb1102033347e33cbb06f9065e749c396`
- context_guard_study.py: `142ec977ac252d8d3a7c946ad7b83e5c86155ea3970ead52c65f506f34b1cfb2`
- docs/context_guard_config.json: `ac88febd4475f68510219d7b6ebfd288b0093c74d5fd0829123eee23e2be2ca4`
- docs/context_guard_holdout.json: `198e6db2c32a3e26af60ed8604f86a13f46edcef3e68d1536cb417612a1a4e1a`
- docs/receipt_guard_checks.json: `7d4c290f196d4a2c619a1a66cb545bfffd60fcca2906c1b9367d91ac69051542`
- Decision trace: `aa2f4d936839ad9f47c40ea2ea6560ce382dbd37b742c3e44d60693b9ff1ab42`
