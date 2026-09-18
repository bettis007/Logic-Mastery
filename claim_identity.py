"""Commit the exact claim, source family and references; not a truth certificate."""
import hashlib
import json
import re


def claim_digest(row):
    if not isinstance(row.get('claim_text'), str) or not row['claim_text'].strip():
        raise ValueError('Missing claim text')
    if not isinstance(row.get('source_family'), str) or not row['source_family'].strip():
        raise ValueError('Missing claim source family')
    refs = row.get('source_references')
    if not isinstance(refs, list) or not refs:
        raise ValueError('Missing claim source references')
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'document', 'sha256', 'locator'}:
            raise ValueError('Invalid claim source reference')
        if not all(isinstance(ref[k], str) and ref[k].strip() for k in ref):
            raise ValueError('Invalid source reference values')
        if not re.fullmatch('[0-9a-f]{64}', ref['sha256']):
            raise ValueError('Invalid source reference hash')
        key = (ref['document'], ref['locator'])
        if key in seen:
            raise ValueError('Duplicate claim source reference')
        seen.add(key)
    committed = {k: row[k] for k in ('claim_text', 'source_family', 'source_references')}
    return hashlib.sha256(json.dumps(committed, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
