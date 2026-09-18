# Dataset intake and recovery review

## Recovery outcome

A targeted saved-file search located an earlier background-label table and all
twenty array files it names. The saved arrays were loaded offline with pickle
disabled. Each contained finite complex-valued samples. Recomputed RMS agreed
with the associated table to within a very small floating-point difference.
The private recovery audit retains exact file hashes, shapes and differences;
raw records and private source identifiers are not included in this repository.

That establishes readable saved bytes and a consistency check, not independently
verified collection history. The accompanying notes explicitly assume acquisition
settings and recommend provisional background/rejection labels. They do not
establish independent adjudication. These files are candidates for a separately
designed offline replay study, not a recovered external holdout for this model.

Other inspected feature-table headers describe symbolic glyph classes, with a
different input representation and target. The original logic-mastery report and
code describe synthetic fixtures. Neither can be relabeled as an independently
annotated claim-evidence dataset. This was a targeted search and compatibility
review, not an exhaustive proof that no suitable records exist elsewhere.

## New executable preflight

`dataset_intake.py` checks a supplied claim-feature file, separate labels and a
split manifest. It never creates missing annotations, trains a model, predicts,
scores accuracy or converts a waveform/glyph dataset into claim evidence.

Checks include exact feature names; finite bounded numeric values; separate labels;
unique matching IDs; recognized target labels; source-family agreement; heldout
feature hashes; and declared source-family/exact-feature separation across build,
calibration, selection and heldout splits. Hashing normalizes integer/float zero
spellings so those spellings cannot hide an exact duplicate. JSON duplicate keys
and nonfinite constants are rejected. Reports are created exclusively, preserving
earlier output files.

The split manifest has this shape (placeholders, not a recovered dataset):

```json
{
  "schema_version": "1",
  "development_inventory_complete": false,
  "ontology_review_ref": "",
  "records": [
    {
      "id": "example-id",
      "source_family": "source-family-id",
      "split": "heldout",
      "feature_sha256": "REPLACE_WITH_COMPUTED_FEATURE_DIGEST"
    }
  ]
}
```

This incomplete template intentionally fails. Supply the actual inventory and a
reviewed category/action mapping reference; do not mark them complete to obtain a
pass. `feature_sha256` is computed with `dataset_intake.feature_digest` from the
feature dictionary. Include development/calibration/selection records as well as
heldout records. Other-split hashes and family membership remain declarations;
the checker cannot verify omitted training data or authenticate reviewer identity.

Preserve the existing inference-only features format and separate labels format
shown in `demo/`. Their contents are synthetic schema examples. The scorer's
legacy `epistemic_category` tag does not resolve its mixed category/action ontology.

## Workflow

Freeze the procedure and source-family inventory before final evaluation. Produce
and preserve prediction receipts before revealing heldout reference labels. Then
run intake as part of evaluation preparation:

```bash
python dataset_intake.py features.json labels.json split_manifest.json intake_report.json
```

The command exits successfully only when its technical checks pass. It is a
standalone preflight, not yet enforced by the browser or existing scorer. Inspect
the report before using the separate scoring workflow. A technical pass always
retains `independent_provenance_verified: false` and
`external_validation_status: "not_established"`. It does not certify label quality,
semantic near-duplicate separation, blinding, trusted timestamps, sample power,
class coverage or scientific validity of the category mapping.

## Validation and next work

The synthetic intake contract tests passed, including rejection of incompatible
schemas, overlapping source families, renamed exact feature duplicates, mismatched
hashes, incomplete inventory, malformed values and attempts to overwrite reports.
Raw test output and source hashes are in `dataset_intake_checks.json`.

Next options are (a) a separate offline adapter study for recovered complex
waveform records, retaining provisional labels and explicit acquisition assumptions,
or (b) independent annotation of compatible claim-evidence examples using
ANNOTATION_PROTOCOL.md. Neither option authorizes hardware acquisition or allows
provisional labels to become independent ground truth automatically. The existing
off-bin and jointly wrong-context detector gates remain failed and unretuned.
