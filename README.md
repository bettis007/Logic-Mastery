# Logic Mastery

Offline-first evidence workbench for claim triage, explicit confidence reporting,
deterministic replay, and reproducible validation.

**Research prototype · Local development · Synthetic reference data**

Logic Mastery makes a classifier's output and the final policy decision visible
side by side. It helps a reviewer inspect overrides, compare receipts and score
separately supplied labels. It does not establish real-world truth, interpret
raw documents, or change hidden model weights.

## Start the workbench

Use Python 3.12. Install dependencies into a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:8765** on the same machine. The server binds only to
loopback and is a development prototype, not a production web server.

1. Load the synthetic demo or import feature JSON.
2. Run the review and inspect classifier-to-policy changes.
3. Import a previous receipt to compare matching IDs.
4. Load reference labels separately, evaluate, and export the audit JSON.

The browser keeps the current run in memory; closing or reloading loses it
unless exported. The server does not save uploaded datasets. The first
prediction initializes the canonical model; subsequent requests reuse it.
The interface accepts up to 1,000 examples and a 2 MB request body.

## What the probabilities mean

| Field | Meaning |
|---|---|
| `classifier_top_label` | Classifier's most likely category |
| `classifier_top_label_probability` | Probability assigned to that category |
| `final_policy_label` | Category selected after the policy gates |
| `classifier_probability_for_final_label` | Classifier support for the final category |
| `policy_override` | Whether the policy changed the top label |
| `post_policy_correctness_probability` | Null: no such correctness model is fitted |

A high probability for ACCEPT is not a high probability for QUALIFY after a
policy override. A deliberate quarantine is not automatically a classifier
error or proof that the underlying claim is false.

## Command-line interface

```bash
python claim_app.py demo/features.json results/predictions.json
python evaluate_labels.py results/predictions.json demo/labels.json results/evaluation.json
```

Use new output filenames for each run; these commands refuse overwrites.
Prediction accepts only example IDs and all 17 numeric features, in the named
schema demonstrated by `demo/features.json`. Labels never enter prediction.
This is feature-based inference, not an automatic text-to-evidence system.

## Verification

```bash
python test_integration.py
python test_policy_contracts.py
python test_server.py
python test_refinements.py
python test_integrity_audit.py
node test_ui_state.cjs  # Optional Node.js state-coordination check
python benchmark_app.py
```

Measured in the development environment:

- 9 integration checks passed; all 13 canonical synthetic records reproduced.
- 92 separately authored synthetic policy-contract cases passed.
- 10 local HTTP-boundary checks passed.
- 10 malformed probability inputs were rejected; numeric endpoints remained valid.
- A Node.js DOM-stub test verifies action locking and recovery after errors.
  This is not a browser visual or interaction review.
- Cached and rebuilt requests produced exactly equal records for benchmark
  batches of 13, 100 and 1,000 examples.
- For 1,000 examples, median request computation fell from **154.15 ms to
  7.14 ms**, about **21.6×**, by avoiding model rebuilding on each request.

This is a warm-process optimization relative to an inefficient rebuild-per-call
baseline. It is not a faster classification algorithm, an HTTP round-trip
benchmark or a Google Cloud performance result. See docs/PERFORMANCE.md.

The browser in the development environment could not access the loopback URL.
HTTP behavior and JavaScript syntax were checked; visual browser QA and a full
interactive browser walkthrough remain unverified.

## Validation limits

The shipped labels are synthetic, not independently annotated external data.
Policy-contract testing checks known requirements, not the scientific validity
of those requirements. No external-validation score is claimed.

The public numerical reference omits private documentary fixtures and source
manifests. Numeric baseline comparisons do not certify the private corpus.
See docs/REFERENCE_PROVENANCE.md and docs/EXTERNAL_VALIDATION.md.

See [browser review](docs/BROWSER_REVIEW.md) for accessibility changes and
remaining live checks, and [annotation protocol](docs/ANNOTATION_PROTOCOL.md)
for the proposed independent evaluation process and dataset compatibility review.

## Simulation-first roadmap

1. Review the local import → inspect → compare → export workflow.
2. Complete visual/user QA and measure representative batch/memory workloads.
3. Evaluate an independently labeled, source-separated dataset.
4. Define identity, storage, access, retention and restart/retry requirements.
5. Deploy private staging in Google Cloud only after those design gates pass.

GitHub versions the design and implementation now. Cloud resources and costs
are not configured by this repository. No production authentication, persistent
multi-user storage, natural-language extraction or cloud deployment is claimed.
See docs/ARCHITECTURE.md for the implemented and planned boundaries.

## Integrity and evidence reporting

See [integrity and preview security](docs/INTEGRITY_SECURITY.md) for the read-only
Git-reference audit tool, its scope and controlled mutation tests. Records expose
`handling_action` separately from `evidence_category` (currently unassessed/null).
Legacy decisions and probabilities remain available for replay comparisons.

## Synthetic signal/message guard experiment

[Simulation report](docs/SIGNAL_GUARD_REPORT.md) and [measured results](docs/guard_simulation_results.json)
document the standalone `signal_guard_sim.py` experiment, including false alarms,
missed weak signals and authenticated false-content controls. It is not a deployed
firewall or RF/biological detector. Run `python test_signal_guard.py` for boundary tests.

## Restart and signal refinement study

[Restart/refinement report](docs/RESTART_REFINEMENT_REPORT.md) records 11 passing
SQLite restart/concurrency checks and a frozen 28,000-example signal comparison.
The experimental detector fails the expanded false-alarm gate and is not enabled
in the original guard. `durable_guard.py` is a standalone persistence prototype.

## Receipt recovery and context study

[Recovery/context report](docs/RECEIPT_CONTEXT_REPORT.md) documents 12 passing
authenticated-receipt tests and a 40,000-example frozen synthetic comparison.
Correct context reduced periodic-change false alarms, but weak recall and
signed-wrong-context gates failed. Both prototypes remain separate from the app.

## Transactional delivery and corroboration

[Delivery/corroboration report](docs/DELIVERY_CORROBORATION_REPORT.md) documents
a synthetic local outbox with bounded retries and an extended context study.
Delivery fixtures pass; off-bin and both-wrong-context gates remain failed.
No live service integration or automatic blocking is enabled.

## Current runtime refinements

[Runtime refinement audit](docs/RUNTIME_REFINEMENT_REPORT.md) covers queue progress
past delayed/exhausted work, authenticated retry/capacity policies, stricter context
validation and safer receipt imports. Records are retained; no auto-migration or
automatic archival is provided for earlier prototype ledgers. Later independent
effects may overtake deferred effects, so strict global ordering is not guaranteed.
Frozen detector failures remain open.

## Validated snapshots and legacy migration

`ledger_archive.copy_ledger` creates a new validated delivery-ledger snapshot
without replacing or pruning its source. It includes committed WAL records,
checks authenticated state/receipts/policy, and preserves queue progress and
spent retries. Supported pre-policy ledgers require an explicit historical retry
budget and new capacity; those declarations cannot be recovered from old bytes.

[Archive validation report](docs/ARCHIVE_VALIDATION_REPORT.md) explains usage,
failure handling and the measured checks. A snapshot does not free capacity,
copy the sink or authorize running two active workers. No automatic cutover or
production retention policy is implemented.

[Independent context evaluation preparation](docs/INDEPENDENT_CONTEXT_EVALUATION.md)
specifies the missing evidence needed for an external test. Independent accuracy
and live browser QA remain unverified; the detector's failed gates remain open.

## Dataset intake

Dataset recovery and intake now have a [compatibility preflight](docs/DATASET_INTAKE.md).
Related saved waveform records were located, but compatible independent reference
annotations remain unavailable. The standalone checker rejects schema mismatches,
source-family leakage and declared cross-split exact duplicates before scoring;
technical acceptance does not certify provenance or label quality.

## Offline waveform replay and review preparation

[Saved-waveform replay](docs/WAVEFORM_REPLAY.md) preserves complex IQ and partial
windows, leaves unknown acquisition settings unset, and produces diagnostics
without applying the synthetic detector. Recovered-record replay was identical
across two fresh processes. The packet generator creates neutral item names,
separate empty reviewer worksheets, a coordinator mapping and a blank claim
annotation template. Independent reference labels remain unavailable.

## Repository description

Suggested GitHub About text (also in `.github/description.txt`):

> Offline-first evidence workbench for claim triage, explicit confidence reporting, deterministic replay, and reproducible validation.

The About metadata must be set separately; a file does not update that field.

## License

MIT, preserving the repository owner's existing LICENSE.
