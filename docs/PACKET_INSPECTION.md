# Inspect both prepared evidence tracks

`inspect_review_packets.py` verifies packet members against their supplied
manifests, binds claim text to cited source bytes, resolves exact JSON passages,
and recomputes saved-array diagnostics. It refuses outside paths, symlinks,
missing files and changed file commitments. A recomputed diagnostic mismatch
produces an unsuccessful inspection status. The originals are opened read-only;
the output path must be new.

```bash
python inspect_review_packets.py /path/to/claim_packet /path/to/waveform_packet new_inspection.json
python -m unittest test_packet_inspection test_claim_packet test_waveform_replay
```

The output contains observed source values, missing-feature counts and declared
reviewer status. It never supplies reference labels, feature values or predictions.
Use `review_audit.py` separately for completed worksheet validation: this inspector
does not validate submitted answers or establish evaluation readiness.

The manifests are supplied commitments, not authenticated provenance. Replacing
an entire packet and its manifest is outside this check's assurance. Preserve a
separately trusted copy or digest. Resolved passages establish what a source says;
they do not establish the truth of the source or independence of its reviewers.

Current source claims concern project development reports. They are not external
holdout data. Saved waveforms retain unverified acquisition metadata, and local
replay cannot infer a documented baseline, label an attacker or establish physical
causes. Original provisional labels must not be promoted into independent answers.

To advance claim evaluation, obtain agreed claim/feature rubrics and separately
completed reviews and feature annotations. To advance waveform evaluation, obtain
hash-linked acquisition metadata, a documented baseline/deviation rule and
separately completed reviews. Adjudication and a frozen source-separated evaluation
design remain required. Existing synthetic detector gate failures remain open.
