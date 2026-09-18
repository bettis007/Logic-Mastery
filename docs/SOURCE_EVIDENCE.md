# Concrete source-evidence preparation

The claim-review track now has selected claims, exact source copies, blank review
worksheets and a separate unfilled feature sheet. The statements concern existing
project reports: retained replay samples, repeatability, a failed synthetic gate
and a draft rubric. These are newly authored development claims, not recovered
independent annotations. All belong to one project source family; they do not
constitute an external holdout or establish generalization accuracy.

## Pinned claim packet

`prepare_claim_evidence.py` reads documented source JSON files from an explicit
full Git commit, checks each cited JSON location and copies exact source bytes
into a new directory. It does not choose reference labels, evidence categories,
handling actions or feature values. Unknown features remain null; the current
classifier cannot use that unfilled sheet and null is never converted to zero.

```bash
python prepare_claim_evidence.py FULL_COMMIT_SHA new_claim_review_directory
```

The packet includes `START_HERE.md`, `frozen_blank.json`, separate reviewer
worksheets, `feature_annotation.json`, source snapshots and a hash manifest.
Reviewers need the claims, source copies and an agreed claim rubric. A separate
feature annotator needs an approved feature-encoding rubric; one has not been
approved. No reviewers were contacted or identities invented. Freeze predictions
before reference-label disclosure to the evaluation workflow.

## Claim identity correction

Previously the review checker compared item IDs, source hashes and source
families. Those fields alone did not bind claim wording. Claim reviews now
require a commitment to the exact claim text, source family and ordered reference
objects. References include source-document hashes and cited JSON locations.
Editing claim wording, source document, source hash or locator causes rejection
against the frozen template.

For claim items, `source_sha256` holds this combined commitment; individual source
hashes remain in `source_references`. Waveform items still use the original
array-file hash. Older claim worksheets without text/reference bindings are
intentionally rejected and require preparation again. No answers are carried
forward automatically.

This checks identity, not factual truth. The audit does not load source documents;
verify the packet manifest before review. Replacing the entire untrusted template
and its matching reviews would not be detected without a separately trusted
commitment. Source copies and labels from this project are not independent merely
because their hashes match.

## Waveform evidence status

Recovered notes explicitly treat acquisition settings as assumptions and supply
provisional background/rejection labels. They do not establish a verified baseline
distribution, independently adjudicated anomaly reference or agreed deviation
rule. A private context-gap record separates those assumptions from verified
metadata. No assumed setting was promoted to a measured fact or used to run a
detector.

Advancing that track requires acquisition/session records tied to saved-file
hashes, a documented baseline, an agreed target/rule and separate completed
reviews. Keep unresolved cases unscored. Repeated searches or generated labels
cannot substitute for those missing inputs.

## Verification and remaining gates

Affected reviewer and packet tests passed, covering altered claim/reference
fields, source-byte equality with the pinned revision, preserved null annotation
fields, manifest hashes, malformed references and overwrite prevention. Raw
results and source hashes are in `source_evidence_checks.json`.

Both rubrics remain drafts; the legacy category mapping is unapproved; independent
reviews are absent; existing detector failures remain open. The next substantive
inputs are independent claim reviews with feature coding, or verified waveform
context plus waveform reviews. No new model accuracy or hardware validation is
claimed.
