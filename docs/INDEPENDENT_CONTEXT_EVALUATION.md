# Independent context evaluation: preparation, not results

Status on September 18, 2026: blocked for a measured external score. No new
independently collected, permissioned operational records or reference annotations
were supplied. The existing corroboration study draws development and holdout
examples from the same synthetic generator. Different seeds and two fixture
signatures do not establish independent collection or factual correctness.

## Two evaluation targets

The workbench evaluates supplied numeric evidence features against reviewed
reference labels. Its annotation process is in ANNOTATION_PROTOCOL.md. Its mixed
category/action label set needs a reviewed mapping before external scoring.

The standalone context study evaluates numeric waveform anomalies given supplied
expected amplitude, noise and frequency context. It cannot score document truth,
attribute an anomaly to an attacker or detect biological effects. A document
fact-checking dataset is not a replacement for compatible waveform records.

## Required collection package

Keep private records outside the public repository. For each permitted example,
record:

| Component | Required evidence |
|---|---|
| Identity | Stable example ID, source-family ID and acquisition/session ID |
| Input | Sample array, units, sample rate, processing history and bytes hash |
| Context | Expected amplitude, noise definition, expected bin and validity interval, with units |
| Provenance | Source references, acquisition method, permission and known dependencies between sources |
| Reference | Independently assigned anomaly label, anomaly type, reviewer IDs and adjudication record |
| Separation | Development/calibration/holdout assignment by source family; duplicate and leakage review |
| Frozen procedure | Code/configuration hashes, target definition, metric denominators, thresholds and exclusion rules |

The current detector accepts a fixed-length, fixed-bin synthetic representation.
Do not silently resample external data or invent missing noise/amplitude values
to fit that representation. Specify and test any adapter separately, with units,
losses and exclusions reported. Keep unsupported inputs unscored.

Before examining final labels, agree the application domain, source sampling,
sample-size rationale, required slice support and confidence-interval method.
Retain clean, legitimate-change, weak-anomaly, off-bin and wrong-context cases.
Context agreement must be tested against references that were not generated
from those same context declarations. Freeze predictions before label access.
Hashes provide byte identity; they do not verify collection date, reviewer
independence, human blinding, signing-key ownership or truth.

## Report when inputs are available

Report missing/excluded examples, class and source-family support, false-alarm
rates, recall by anomaly/context slice and confidence intervals. Keep software
integrity checks separate from detection performance. Do not combine the result
with the workbench's category accuracy or present it as real-world protection.

No new external metric, performance improvement or detector pass is claimed by
this preparation. The frozen synthetic off-bin and jointly wrong-context gates
remain failed. Further tuning needs a new held-out source collection; reusing the
failed holdout to choose thresholds would make it development data.
