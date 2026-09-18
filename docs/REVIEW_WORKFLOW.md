# Review completion and disagreement workflow

The project now has executable checks for submitted reviewer worksheets and two
explicit draft rubrics. Neither rubric is approved, no independent reviews have
been completed, and no independent accuracy is established.

## Separate targets

| Track | Reference question | Required evidence |
|---|---|---|
| Waveform context | Is the saved array consistent with an agreed documented baseline? | Baseline, acquisition context, allowed-deviation rule and permission |
| Claim evidence | Is the exact claim supported, contradicted or insufficiently evidenced in its supplied context? | Claim text, cited source passages, category/action rubric and permission |

`waveform_review_rubric.json` and `claim_review_rubric.json` contain the draft
vocabularies and requirements. These are review proposals, not previously lost
annotations. An authorized project reviewer must settle the target definitions,
exclusion policy and sampling design before recording an approval reference.
Changing a rubric creates a different protocol hash; do not silently reuse old
reviews. An approval field is a declaration, not authenticated authority.

The claim rubric separates reference support, evidence category and recommended
handling. Quarantine does not mean false. A claim about a synthetic result may be
supported as a statement about the simulation while retaining its simulated
category. No mapping from this draft to the legacy five-class scorer is approved.

## Review procedure

Preserve the original blank worksheet as the frozen template. Supply the same
item IDs, source hashes and source-family assignments to each separate reviewer.
Keep the coordinator filename mapping, provisional labels and predictions out
of reviewer materials. Freeze predictions before reference labels are revealed
to the evaluation workflow; never tune on those final references.

Each reviewer works on a separate copy, declares an identity, sets the role to
`reviewer_a` or `reviewer_b`, and supplies the protocol hash. Compute it from the
exact rubric object using sorted-key compact JSON and SHA-256, as implemented in
`review_audit.py`. The raw rubric-file hash is also recorded by the CLI; it is a
different commitment from the normalized protocol-object hash.

For an annotated item, supply a reference label, evidence category, handling
action, evidence references, rationale and uncertainty statement. For an excluded
item, leave those three answer fields null and give an exclusion reason. Missing
context must not be turned into a negative label. Mark a worksheet `complete`
only when every item has an annotation or documented exclusion.

```bash
python review_audit.py frozen_blank.json reviewer_a.json reviewer_b.json rubric.json review_audit.json
```

The existing waveform packet worksheets already use this item structure. Claim
reviews now require exact claim text and source references committed together;
see SOURCE_EVIDENCE.md and `prepare_claim_evidence.py` for concrete project-source
items. The original empty claim collection template does not contain those items.
Do not substitute waveform rows or synthetic examples just to obtain a passing audit.

## What the checker establishes

The checker requires distinct declared reviewer identities, exact item coverage,
matching source hashes/families and matching protocol hashes. It checks answer
vocabularies and required supporting fields. It reports agreements, disagreements,
joint exclusions and incomplete items separately. Joint label agreement covers
the label/category/action tuple only among jointly annotated items; exclusions
are excluded from that denominator. It is not an accuracy metric.

The CLI returns a failing status for draft protocols, incomplete reviews and
all-excluded batches. Completed reviews with substantive disagreements can be
ready **for adjudication**, but the tool never resolves those disagreements or
exports gold labels. Read all blockers even when the audit is ready for that
next stage. A separate adjudicator needs the frozen reviews, sources, rubric and
a documented rationale; neither majority voting nor model predictions are used
here to manufacture a reference label.

Source hashes establish identity relative to the supplied template, not whether
that template is trustworthy. Distinct identity strings do not prove separate
people. References and rationales are checked for presence, not truth. Human
blinding, independence, collection history and approval remain unverified.

## Tested scope

Synthetic fictional-reviewer tests cover matching answers, disagreements,
incomplete and excluded items, changed source bindings, missing/duplicate IDs,
same reviewer declarations, wrong rubric hashes and draft/blank rejection.
The actual saved blank waveform packet was also audited: it remains blocked.
Raw outputs and source hashes are in `review_workflow_checks.json`.

No detector thresholds changed. Existing detector failures and the external
reference-label gap remain open. The next substantive work needs documented
waveform baselines and completed independent reviews, or sourced claim examples
and separate feature/reference annotation under the agreed claim rubric.
