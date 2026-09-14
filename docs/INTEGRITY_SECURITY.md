# Local integrity and preview security

The integrity tool is a read-only developer utility, not an RF/frequency detector. It is not installed in OpenAI systems and does not modify hidden model memory. The GitHub repository is the durable project source; users may clone or pull it to their own computers.

Run `python integrity_audit.py --reference FULL_TRUSTED_COMMIT_SHA` from a reviewed checkout. Supply a full 40-character commit identifier obtained through a trusted review process. Exit zero means covered file bytes match and no additional nonignored files were found. Exit one means differences need review. Operational errors also require investigation and must not be interpreted as an integrity pass.

The report includes per-file expected and actual SHA-256 values, changed/missing/unsupported paths and additional nonignored files. It checks both staged additions and untracked additions. It refuses to follow working-tree symlinks. Authorized edits produce differences too: do not label them as attacks automatically.

Ignored files, Python dependencies, file permissions, browser extensions, running process memory, kernel state and RF signals are outside scope. A compromised Git executable, baseline or host can invalidate the audit. This tool does not establish baseline authorship, time of alteration or attacker attribution. Review a quiet checkout to avoid races with concurrent writes.

## Controlled checks

Seven disposable-repository checks cover clean bytes, modified bytes, deletion, symlink substitution, untracked addition, staged addition and rejection of an unpinned reference.

The local HTTP tests compare all three served assets byte-for-byte with disk and check CSP, no-sniff and no-store headers. They also check host/origin/token restrictions, traversal rejection, allowlisted assets and input boundaries. They are not a browser-engine or penetration-test certification.

The cloud preview returned an explicit URL-policy block for the loopback app. No workaround was attempted. This is evidence of restricted browser access, not evidence of RF interference or tampering. No RF measurement or transmission occurred.

## Evidence and handling separation

Decision records version 2.1 retain legacy labels and their probabilities for replay. `handling_action` makes the operational choice explicit; `evidence_category` is null with an unassessed status. It is not inferred from quarantine, acceptance or the legacy classifier's most likely label. Independent category annotation and a revised classifier remain future work. Legacy evaluator scores still assess its original mixed-label target and do not validate the new unassessed evidence field.
