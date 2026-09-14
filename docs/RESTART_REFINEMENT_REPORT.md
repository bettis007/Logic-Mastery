# Restart and signal refinement report

## Decision

Keep the original signal guard unchanged. The experimental replacement fails the expanded benign-periodic false-alarm gate and must not become an automatic blocking policy. The SQLite wrapper is a separately tested prototype for retaining the original guard's state across process restarts; it is not connected to the app HTTP server.

## Restart results

11/11 checks passed.

- after commit recovery
- altered binding refused
- before commit recovery
- clock rollback rejected
- concurrent duplicate serialized
- corrupt ledger refused
- existing ledger reset refused
- missing ledger refused
- quota expires
- restart quota preserved
- restart replay rejected

The process-crash tests terminate actual subprocesses before and after SQLite commit. Before commit, retry is allowed; after commit, retry is rejected. Two concurrent subprocesses submitting the same sequence produced one allowance and one replay rejection. These are at-most-once guard decisions: downstream effects and lost-response receipt recovery are not implemented, so exactly-once delivery is not claimed.

A configuration/key/source binding prevents accidental reuse of a different guard's ledger. It is not authentication of the database. A knowledgeable adversary able to rewrite or roll back the ledger can defeat it. The test key remains public and nonsecret. There is no production key enrollment, key rotation or trusted storage. Tests cover process exit, not OS crash or power loss. Clock rollback rejects requests; production clock and legitimate reordering semantics remain open.

## Signal study

Development: 8,000 synthetic examples, seed 610201. Select among 81 spectral thresholds with <=1% false alarms separately on clean and legitimate-stress slices; maximize weak-tone recall. Selected threshold 0.485; retain absolute-mean threshold 0.5; remove RMS rejection. Freeze configuration before evaluating test seed 910301.

Held-out: 28,000 fresh synthetic examples, 4,000 per slice, evaluated by both baseline and experimental rules. Different random seeds do not constitute external validation. Legitimate periodic changes and weak injected tones intentionally overlap in distribution; the test exposes a coverage limit of waveform-only judgments.

| Slice | Baseline flag rate | Experimental flag rate |
|---|---:|---:|
| clean | 0.000% | 0.825% |
| dc_shift | 100.000% | 100.000% |
| legitimate_periodic_change | 3.350% | 62.700% |
| legitimate_stress | 9.700% | 0.000% |
| off_bin_weak | 0.000% | 0.950% |
| strong_tone | 100.000% | 100.000% |
| weak_tone | 3.550% | 61.875% |

| Gate | Baseline | Experimental |
|---|---|---|
| core_clean_false_alarm | PASS | PASS |
| core_stress_false_alarm | FAIL | PASS |
| expanded_periodic_false_alarm | FAIL | FAIL |
| strong_recall | PASS | PASS |
| weak_recall | FAIL | PASS |

Gate bounds: each benign slice <=1% false alarms; strong-tone recall >=99%; weak-tone recall >=50%. Gates were written into the configuration before holdout scoring; this is not external preregistration. Off-bin detection and DC-shift detection are diagnostic slices without a predeclared pass threshold.

Baseline: accuracy 70.071%; precision 93.975%; recall 50.887%; aggregate benign false alarms 4.350%.

Experimental: accuracy 71.329%; precision 80.535%; recall 65.706%; aggregate benign false alarms 21.175%.

A second fresh process reproduced the entire held-out result object exactly. Sixty separate numeric examples confirmed the comparison's baseline rule agrees with the original Guard. No threshold was revised after inspecting the test results. No throughput improvement is measured here.

## Next design work

Preserve this failed candidate as evidence. Add independently obtained context and a review action for ambiguous periodic changes, rather than lowering thresholds again on this holdout. Any new detector needs a newly frozen test set. For the message layer, design authenticated receipt recovery, sender-specific key management and rollback-resistant state before deployment.

## Reproduce

- `python test_durable_guard.py`
- `python refine_signal_guard.py develop --config results/new_config.json`
- `python refine_signal_guard.py evaluate --config results/new_config.json --output results/new_holdout.json`

Output files are exclusive-create. No physical hardware, RF sensing, biological effects or network scanning is involved.

## Hashes

- durable_guard.py: `b9e45225a28752215bd90ebc073775bf2178778d7bd547e3954c50aafce94f46`
- test_durable_guard.py: `ae833dc0a553a6fcabcbe049f19fbaa67f9db6e178d3ecb8097fc74cdee1e208`
- refine_signal_guard.py: `cd710eec97333163a99f011c4455c037446c502b50088c225592b833c0870217`
- docs/guard_refined_config.json: `49e978faa681d59c4ba72d73b95d633418c6122b92aa717fa4062c0ce6fb1a3a`
- docs/guard_refined_holdout.json: `3c8332ef4a2c68665bbd8da60bc090bbf413ca3e88aa39b7eef81468654decb4`
- Canonical decision trace: `5457b01fe728c286cd24e828acb1af02df408efb9b950d5d289f27a2c51f4d19`
