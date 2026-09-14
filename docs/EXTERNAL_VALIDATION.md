# External validation remains an open gate

The examples in demo/ are original synthetic feature fixtures with numeric
expectations. The contract suite is separately authored against the known policy
specification, not a blind independent assessor. Do not report either as real-world
generalization or external-validation accuracy.

To run a genuine external evaluation, provide inference-only feature examples
and a separate labels file with documented source families, label definitions,
annotation authorship and adjudication. Keep development/calibration source
families out of the final test and freeze predictions before exposing labels.
The current tool records declarations but cannot authenticate provenance or
enforce human blinding. Feature extraction may itself leak reference labels.

Use the demo JSON files as schema examples. Labels must target epistemic category
(ACCEPT, QUALIFY, SIMULATED, NARRATIVE, QUARANTINE), not policy-action
appropriateness. Those targets require separate assessment. Missing/duplicate IDs
and incompatible target types are rejected rather than silently dropped.

The scorer reports supports, fixed-five-class F1, confusion matrix, source-family
accuracy, category-to-fact violations, false factual promotion and chosen-label
probability calibration diagnostics. Absent category slices return null.
No threshold tuning on final evaluation labels is implemented or authorized by
running the evaluator. No independent dataset was identified in this task.
