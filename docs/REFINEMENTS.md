# Refinement validation — September 14, 2026

Two correctness refinements were tested with synthetic inputs:

1. Evaluation no longer coerces string or boolean probabilities into numbers. Ten malformed inputs were rejected, including nonfinite and out-of-range numbers. Numeric zero and one retain their correct binary Brier scores.
2. Interface actions now ignore overlapping calls and disable evidence, label and receipt mutation controls until completion. A Node.js VM with a minimal DOM stub verified locking, overlap rejection, and release on success and error.

The existing nine integration checks, 92 policy contracts and ten HTTP checks passed. All 13 canonical synthetic records still match their frozen probabilities and decisions exactly, and repeated inference remains equal.

No new throughput gain is claimed. These changes improve input correctness and state consistency. Browser visual QA and independent external-label validation remain incomplete. The DOM stub does not measure rendering, accessibility or actual browser event behavior.
