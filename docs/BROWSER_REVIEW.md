# Browser and accessibility review

September 14, 2026: live navigation to the loopback app returned `net::ERR_BLOCKED_BY_CLIENT`. No rendered browser workflow, keyboard walkthrough, screen-reader or full accessibility pass is claimed.

Source-level improvements: skip-to-workbench link; inspection dialog named by its heading; focusable, named scrolling ledger region; explicit column-header scope. These changes need a real browser check.

## Outstanding acceptance steps

- At desktop and narrow/mobile widths: load demo, run, filter, inspect and close a record; verify no page-level horizontal clipping.
- Use keyboard alone: skip link, file inputs, action buttons, filter, scroll region and dialog. Verify visible focus, Escape close and focus return.
- Load labels, evaluate and export. Import the receipt and verify unchanged-ID comparison. Confirm failed imports leave prior state clearly identified.
- Verify screen-reader names, live status announcements, column associations and dialog title.
- Inspect contrast, 200% zoom, long IDs, empty filters and the 1,000-case limit.

Static tests check markup relationships only. They cannot certify the above behavior.
