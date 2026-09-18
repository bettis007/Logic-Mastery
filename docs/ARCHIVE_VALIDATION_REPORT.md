# Ledger archive and migration validation — September 18, 2026

## Outcome

A new offline maintenance API makes validated snapshots of the synthetic delivery
ledger. Supported older ledgers can be migrated in the copy, with explicitly
declared policy limits. Source records are not pruned or replaced. Tests use
disposable local databases and fresh ephemeral keys.

All targeted archive and affected regression checks passed. This does not certify
an operational deployment, power-loss durability, external context truth or
protection from physical signals. Existing detector failures remain open; no
detector thresholds, classification rules or browser code changed in this work.

## What is checked

The source opens read-only. SQLite's backup API includes committed WAL contents
in a consistent snapshot. Before publishing a destination, the utility checks
SQLite integrity, an exact supported schema, state/receipt/policy authentication,
configuration binding, sequence/time consistency, allowed-receipt/outbox
correspondence, queue statuses, retry counts and capacity. Unknown tables,
triggers, views and schemas are rejected.

Current signed policy limits cannot be overridden. For the supported legacy
schema, an operator must supply the historical retry budget and a new capacity.
The old schema did not store those limits; supplying them is a declaration, not
independent recovery of history. Spent attempts, pending schedules, delivered and
exhausted rows, and receipt bytes are retained. Limits that conflict with existing
attempt counts or row counts are rejected.

The snapshot is written to a private temporary file in the destination directory.
After validation and file synchronization, a same-filesystem hard link publishes
it without overwriting an existing destination. The containing directory is
synchronized. Normal errors remove the temporary copy. An abrupt process exit
may leave a temporary file; it does not replace the source. If directory sync
fails after publication, the function raises and a valid destination may already
exist; inspect it before retrying. These are Linux filesystem assumptions.

## Measured checks

| Suite | Result |
|---|---|
| New archive/migration tests | All passed |
| Queue/context boundary regression tests | All passed |
| Transactional delivery and injected process-crash checks | All passed |
| Receipt recovery, concurrency and mutation checks | All passed |

Full commands, raw outputs, test counts, runtime version and source SHA-256 hashes
are in [archive_validation_results.json](archive_validation_results.json).

New checks cover a current ledger containing delivered, exhausted and pending
work; unchanged source bytes for quiescent fixtures; exact preserved logical rows;
duplicate receipt recovery; continued pending delivery; retained retry exhaustion;
committed WAL data; review/rate-rejection receipts without effects; explicit legacy
migration; existing destination preservation; wrong keys; changed receipt/policy
bytes; missing queue/receipt rows; invalid status; unexpected triggers; unreadable
databases; incompatible limits; and an injected publication error. The publication
error is a simulated exception, not a power interruption.

## API usage

Python callers supply the original receipt key through their existing trusted key
handling. Do not place keys in source control, command-line arguments or reports.

```python
from ledger_archive import copy_ledger

# Current schema: preserves its authenticated policy.
summary = copy_ledger(source_path, new_snapshot_path, receipt_key)

# Supported pre-policy schema only: limits must be known/approved by the operator.
summary = copy_ledger(
    legacy_source_path, new_migrated_path, receipt_key,
    legacy_limits=(historical_retry_budget, new_capacity),
)
```

These calls produce separate copies. They do not switch the active worker or
initialize a fresh sink. Before any manually reviewed cutover, stop writers,
retain the matching existing sink and compatible source/key/configuration, and
choose one active ledger. Running both copies could duplicate authorization
across different sinks. A snapshot taken while writes continue is an archive
of one instant, not a coordinated ledger-and-sink migration.

## Remaining limits

Archiving does **not** reclaim capacity. Safe compaction would need a separate
design that preserves duplicate-request history, spent retries, idempotency and
the relationship to retained sink effects. No automatic deletion or retry reset
is provided. The capacity gate still stops new allowed effects when full.

Mutable queue attempts, schedules and statuses remain unauthenticated; structural
checks cannot detect every plausible alteration. Receipt MACs do not prove a
ledger is the latest complete version, identify an attacker or authenticate
incoming messages with the experiment's public fixture key. A matching sink is
not inspected or copied by this utility. No key rotation or distributed-worker
protocol is added.

Independent operational evaluation remains blocked by missing compatible records
and annotations. The collection requirements are in
[INDEPENDENT_CONTEXT_EVALUATION.md](INDEPENDENT_CONTEXT_EVALUATION.md).

## Reproduce

```bash
python -m unittest -v test_ledger_archive test_runtime_refinements
python test_transactional_delivery.py
python test_receipt_guard.py
```
