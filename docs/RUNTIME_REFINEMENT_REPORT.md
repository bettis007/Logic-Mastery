# Runtime refinement audit — September 17, 2026

## Outcome

Delivery, context-schema and receipt-import refinements passed their targeted checks and affected regression suites. The signal classifier was not retuned: its entire frozen synthetic result object still matches. Off-bin recall and both-wrong-context recall remain failed gates. No live browser or external operational-source verification is claimed.

## Delivery behavior

Ready pending work now takes priority over a deferred entry; exhausted entries remain in the ledger and are excluded from ordinary pending selection. An index supports status-based selection. A caller can inspect counts with `queue_status()`. Changing this order permits later effects to overtake earlier effects: this is suitable only for independent effects, not an application that requires strict global order. Integrity failures still stop the worker for review.

The retry budget and queue capacity are authenticated in a persistent policy record. Reopening with a conflicting policy or overriding the retry budget is rejected. Policy-byte alteration fails authentication. Capacity counts all outbox rows, including completed and exhausted work. When full, insertion rolls back the new receipt, sequence and queue row together; no records are automatically deleted.

The capacity bound covers the outbox, not all receipt storage, the sink or request traffic. Delivered receipt retention and external archival are still unimplemented. Existing pre-policy prototype ledgers are intentionally not auto-migrated or reset. Preserve them with their compatible code version; migrating pending work needs a separately reviewed procedure.

## Progress comparison

The same synthetic workload was run against the pinned prior delivery source and current source. Authentication/receipt fixtures are shared; this isolates queue scheduling behavior. It is a bounded progress comparison, not a throughput benchmark.

Queued effects: 256. Simulated failures applied to the first effect: 3. Subsequent worker calls: 264.

| Outcome | Prior implementation | Refined implementation |
|---|---:|---:|
| delivered | 0 | 255 |
| pending | 255 | 0 |
| exhausted | 1 | 1 |

The exhausted record remains inspectable in both cases. No automatic retry reset or deletion occurred.

## Context boundary

The attestation checker now rejects malformed envelopes and bodies, extra/missing fields, nonfinite values, booleans masquerading as numeric values, nonpositive noise scales, unsupported frequency bins, invalid signature encodings and excessive validity windows. Expected model bin is fixed to the synthetic study's supported bin; the validity window may be at most 300 simulated time units.

Unknown or malformed declarations return false (review required), rather than raising an exception. Validity-window boundaries, expiry, role separation, example binding and disagreement are covered. Agreement between two authenticated declarations is still not independent verification of truth. Public fixture keys are still used in the study.

The complete frozen holdout result exactly matches after this schema change. That replay checks compatibility and determinism; it is not a new generalization experiment. No new external records were supplied in this task, so the independent operational-record validation gate remains open.

## Interface import

Previous-run imports must contain nonempty, bounded, unique example IDs, recognized classifier/policy labels and finite numeric probabilities in range. Empty, oversized, duplicate and malformed receipts are rejected. Failed validation does not replace the last valid imported receipt. This improves comparison reliability without authenticating the imported file's origin.

The JavaScript tests execute source in a minimal DOM stub. They do not validate browser rendering, screen readers, native file choosers or mobile interactions. Live browser QA remains unverified.

## Verification

- Targeted Python tests: 12 passed.
- test_integration.py: PASS.
- test_integrity_audit.py: PASS.
- test_policy_contracts.py: PASS.
- test_receipt_guard.py: PASS.
- test_receipt_import.cjs: PASS.
- test_refinements.py: PASS.
- test_server.py: PASS.
- test_transactional_delivery.py: PASS.
- test_ui_state.cjs: PASS.
- Delivery workload: expected before/after queue states matched.
- Detector replay: full saved result object matched exactly; failed gates retained.

## Limits

Delivery remains a single-worker local SQLite simulation. Policy authentication does not authenticate mutable attempt/status metadata, prevent complete-ledger rollback, enroll real senders, or guarantee arbitrary downstream exactly-once behavior. Process-crash controls do not certify power-loss durability. Operational context truth cannot be inferred from signed agreement alone. No deployment, hardware/RF measurements or attacker attribution occurred.

## Reproduce

- `python test_runtime_refinements.py`
- `python test_transactional_delivery.py`
- `python test_receipt_guard.py`
- `python benchmark_delivery_progress.py` (requires the pinned baseline commit in local Git history)
- `node test_receipt_import.cjs`
- `node test_ui_state.cjs`

Stored raw results are in runtime_refinement_results.json, delivery_progress_results.json and context_schema_replay.json. Earlier reports remain historical results for their original code versions.

## Hashes

- transactional_delivery.py: `f55e64bbe64d29421c65187fa49c8aa91f5fe1380e05c0da67640f6992b840a6`
- corroborated_context_study.py: `d7ba43e1605ec73d2b889d9faac2b2f269d503d419b23c6edd7e1842de718683`
- web/app.js: `4ca745afcaba0746bb944a3038ec68fe1a35f84a674b6e0e5b7166eb9e962740`
- test_runtime_refinements.py: `0a527b8668a42e266c5a1425d8487d5027e5b3df3d9fcc18211df56760b3ae97`
- test_receipt_import.cjs: `986afcdad3ffeebd6720329fae437d507a7ed4bc4b7d6302d0ca942f08eda2da`
- benchmark_delivery_progress.py: `6c7ee1b1e9d355f296a9ffec5ef13c3b0069d8195c66cf17920ee4ae1c1bb82c`
- docs/delivery_progress_results.json: `a99253a5db1f9de7943ba47a62daf31138a839e8074edd91f637e7c7cb300184`
- docs/context_schema_replay.json: `dd69dd3d6a90e49067729e0947ac3e7d0323ed018890a66f4df2f67422ea7f5e`
- docs/runtime_refinement_results.json: `c0e3beae9a35a1aabdef1dc6f9759cba9b3ebe32a34b097c99191e710ff6f64b`
- Frozen detector trace: `02c0c6f5a7b977ceff6cd393031b44f8bc7f0bb89b8c46e34b349435d8fbbf1d`
