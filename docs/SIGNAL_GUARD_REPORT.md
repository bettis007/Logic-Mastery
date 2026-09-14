# Software signal-guard simulation — September 14, 2026

This is a standalone developer experiment, not a deployed firewall or an integration into OpenAI infrastructure. It processes numeric arrays and messages in memory. No RF receiver, transmitter, biological model, network endpoint or personal system is accessed.

## Experimental design

Two fresh Python processes used seed 20260914. Each scored 9,000 messages across nine independent slices. Replay fixtures used 1,000 prior accepted messages; rate fixtures used 20 accepted quota-filling messages. These 1,020 setup events are excluded from the metrics.

128 samples per message. Ordinary signals: independent Gaussian noise with standard deviation 0.25 plus a sine of amplitude 0.25 at DFT bin 15. Strong injected tones add amplitude 2.8; weak tones add 0.10. No physical sample rate or frequency is implied. Stress controls use noise standard deviation 0.9 except every tenth example uses 1.7. All sample distributions and thresholds were set before the first scored run, but are not independently preregistered.

The guard checks serialized size (16,384 bytes), schema, HMAC-SHA256, increasing sequence number and a 20-request sliding one-second window. Waveform review triggers at RMS >1.5, absolute mean >0.5 or maximum centered spectral-bin energy fraction >0.6. Protocol failures reject; waveform anomalies request review. A review is not a finding of malicious intent.

HMAC uses a deliberately public test key; anyone knowing that key can forge a valid fixture message. This demonstrates check logic under simulated key separation, not production cryptographic security. It provides no encryption. Serialization occurs before the size check, so the experiment does not model raw-body memory exhaustion defense.

## Results

| Slice | Cases | Flagged | Allowed | Flag rate |
|---|---:|---:|---:|---:|
| clean | 2000 | 0 | 2000 | 0.00% |
| legitimate_stress | 1000 | 98 | 902 | 9.80% |
| modified_payload | 1000 | 1000 | 0 | 100.00% |
| overflow_burst | 500 | 500 | 0 | 100.00% |
| oversize | 500 | 500 | 0 | 100.00% |
| replay | 1000 | 1000 | 0 | 100.00% |
| strong_tone | 1000 | 1000 | 0 | 100.00% |
| validly_signed_false_content | 1000 | 0 | 1000 | 0.00% |
| weak_tone | 1000 | 27 | 973 | 2.70% |

The false-content slice is an explicit indistinguishability control: its waveform and valid authentication look normal, while the evaluator assigns an adverse semantic label. The message contains no independently verifiable truth evidence. Zero flags are therefore an expected coverage limit, not a measurement of real misinformation detection.

For the chosen synthetic mixture: accuracy 76.9889%, flag precision 97.6242%, recall 67.1167%, benign false-alarm rate 3.2667%. TP=4027, FP=98, FN=1973, TN=2902. These rates depend on this artificial class balance and do not estimate real attack prevalence.

Median inspection time 161.17 microseconds; p95 1170.65 microseconds in run 1 on x86_64, Python 3.12.14, NumPy 2.3.5. Timing excludes sample generation, signing and setup; it is not browser/network latency. Full timings from both processes are in guard_simulation_results.json.

The deterministic result objects matched exactly between fresh processes. Timing is expected to vary. Six separately authored boundary tests passed: replay, clock regression, invalid authentication without sequence advancement, quota expiration, malformed shape and numeric overflow.

Source SHA-256: `83d417e8d7b63040d985db26a874defbec5e205a0e16b7e809ee08062cbd29d8`

Decision trace SHA-256 (canonical outcomes): `cd1b1f9798df1efb80ca71ffd45631f9499d8815e9c3e1189fb4975414ee142e`

## Findings and corrective actions

- Strong disturbance sensitivity does not imply weak disturbance sensitivity: 973/1,000 weak-tone cases were missed. Improve only using a separate development set; reserve a new independent test set.
- Legitimate high-energy signals caused 98 false alarms. Retain a review action and acquire representative normal operating distributions before contemplating automatic blocking.
- Authenticated falsehoods cannot be resolved by an HMAC or waveform threshold. Add independent source verification to a separately defined truth-assessment workflow.
- Replay state is process-local and assumes ordered arrival. Durable state, restart recovery, sender enrollment, real key management and legitimate reordering need design and testing before use outside the harness.
- No protection against authorized copying, data theft, biological attacks or RF interference has been demonstrated. No attacker attribution was attempted.

## Reproduce

`python test_signal_guard.py`

`python signal_guard_sim.py --output results/new_guard_run.json`

Use a new output path. Compare the deterministic objects between fresh runs, excluding timings. The script does not change the application classifier or connect itself to the HTTP server.

## What Logic Mastery does today

The main app is a local numeric-evidence review workbench. You provide an ID and 17 feature scores in [0,1], such as direct observation, corroboration, explicit simulation labeling, ambiguity and tamper score. It does not measure those scores itself or extract them from documents.

A logistic-regression classifier is reconstructed from fixed synthetic training examples: 4,200 BUILD, 1,600 calibration and 1,800 policy-selection rows. It produces probabilities over five legacy labels. Explicit policy rules then select a handling outcome. The UI exposes both, the override, classifier support for the final label, and an unassessed evidence-category field.

You can inspect/filter records, import previous receipts, compare matching IDs, load separate reference labels, compute evaluation metrics and export JSON. Source-truth and label independence are not automatically verified. The supplied demo checks known fixtures. The companion integrity audit compares local file bytes with a chosen Git reference.

User examples are inference-only in this app. The Python classifier is part of this project; saving code is not an invocation of OpenAI fine-tuning. OpenAI's documented fine-tuning workflow uses a training dataset and a training job: https://developers.openai.com/api/docs/guides/supervised-fine-tuning . This run did not invoke such a job or verify account-specific training-data settings.
