# Independent evaluation protocol (proposed; not yet executed)

## Target

Assess the evidence category of a claim in its supplied context, not its policy-action appropriateness. ACCEPT, QUALIFY, SIMULATED, NARRATIVE and QUARANTINE currently mix epistemic categories and handling actions. An independent reviewer must resolve this ontology before annotation; in particular, quarantining an item is not proof it is false.

Record category and recommended handling as separate fields during annotation. Only a reviewed, frozen category mapping may populate the existing scorer's `expected` field. Do not derive reference labels from model predictions or feature thresholds.

## Collection and separation

1. Obtain permission to use source material and define the intended application domain.
2. Assign stable example IDs and source-family IDs. Keep related documents and near-duplicates in the same split. Record source references privately when needed.
3. Freeze development, calibration and held-out source-family lists before evaluation; exclude any family used to refine the model from the final held-out set.
4. Have feature annotators encode the 17 inputs using a written rubric, without prediction receipts or reference labels. Do not manufacture unknown evidence values; unresolved coding needs adjudication or exclusion with reasons.
5. Have two separate reviewers annotate evidence category and action appropriateness without seeing model outputs. Record disagreements and adjudicate with a third reviewer. This project has not recruited or contacted reviewers.
6. Freeze the mapping, labels, features, model source, configuration and split files with SHA-256 hashes. Produce predictions before revealing held-out labels. Hashes establish byte identity, not independent authorship or trusted chronology.
7. Score once; report all class supports and source-family results. Do not retune on held-out failures. Use a newly collected holdout for subsequent claims of improvement.

## Reporting

Use the existing evaluator only after schema and target compatibility are established. Report accuracy, fixed-five-class macro F1, category-to-fact violations, false factual promotion, chosen-label Brier/ECE and absent slices. Do not interpret chosen-label model probabilities as calibrated post-policy correctness.

Predeclare sample-size rationale, source sampling, exclusion rules and confidence-interval method. Treat families, not templated rows, as the relevant dependence groups. No powered sample size or confidence bound is claimed here.

## Candidate review on September 14, 2026

The official FEVER dataset describes SUPPORTS, REFUTES and NOT ENOUGH INFO labels and claim/evidence records: https://fever.ai/dataset/fever.html . It does not directly supply the app's five-category labels or 17 numeric features. A direct label conversion would conflate different targets; no FEVER accuracy was calculated. It could support a separately designed factual-verification component after defining and testing an evidence-to-feature pipeline.

Focused saved-file searches did not identify a compatible independent annotation set. This is a search limitation, not proof no such data exists. Existing synthetic fixtures remain useful regression checks only.

Status: BLOCKED for independent accuracy, pending compatible independently annotated data and an agreed category ontology.
