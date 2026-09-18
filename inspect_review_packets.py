"""Read-only inspection of prepared packets; never create reference annotations."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from claim_identity import claim_digest
from dataset_intake import parse_json
from waveform_replay import canonical, replay_bytes


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load_packet(root):
    """Check supplied commitments, rejecting paths outside the packet and symlinks."""
    root = Path(root).resolve()
    manifest_path = root / 'packet_manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Symlink manifest is unsupported')
    raw = manifest_path.read_bytes()
    manifest = parse_json(raw.decode())
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Missing packet files')
    blobs = {}
    for name, expected in files.items():
        rel = PurePosixPath(name)
        if (rel.is_absolute() or not rel.parts or '..' in rel.parts
                or str(rel) != name or '\\' in name):
            raise ValueError('Unsafe packet path')
        path = root
        for part in rel.parts:
            path = path / part
            if path.is_symlink():
                raise ValueError('Symlink packet member is unsupported')
        if not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError('Missing or oversized packet member: ' + name)
        blob = path.read_bytes()
        if sha(blob) != expected:
            raise ValueError('Packet hash mismatch: ' + name)
        blobs[name] = blob
    return blobs, {'manifest_sha256': sha(raw), 'matched_files': len(blobs),
                   'commitment_scope': 'Supplied manifest only; not authenticated provenance'}


def pointer(document, locator):
    if not isinstance(locator, str) or (locator and not locator.startswith('/')):
        raise ValueError('Invalid JSON pointer')
    value = document
    for token in locator.split('/')[1:] if locator else []:
        if re.search(r'~(?![01])', token):
            raise ValueError('Invalid JSON pointer escape')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict):
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
            value = value[int(token)]
        else:
            raise ValueError('Unresolvable JSON pointer')
    return value


def inspect_claims(blobs):
    template = parse_json(blobs['frozen_blank.json'].decode())
    if template.get('status') != 'unannotated' or not template.get('items'):
        raise ValueError('Expected prepared blank claim packet')
    observations = []
    seen = set()
    for item in template['items']:
        if item['id'] in seen or claim_digest(item) != item['source_sha256']:
            raise ValueError('Duplicate or changed claim identity')
        seen.add(item['id'])
        if any(item.get(k) is not None for k in ('reference_label', 'evidence_category', 'handling_action')):
            raise ValueError('Frozen template contains answers')
        refs = []
        for ref in item['source_references']:
            blob = blobs[ref['document']]
            if sha(blob) != ref['sha256']:
                raise ValueError('Cited source hash mismatch')
            refs.append({**ref, 'observed_value': pointer(parse_json(blob.decode()), ref['locator'])})
        observations.append({'id': item['id'], 'claim_text': item['claim_text'],
                             'source_passages': refs, 'reference_label': None})
    features = parse_json(blobs['feature_annotation.json'].decode())
    return {'claims_checked': len(observations), 'observations': observations,
            'missing_feature_values': sum(v is None for row in features['examples']
                                          for v in row['features'].values()),
            'scope': 'Exact source values, not an independent truth review or feature validation'}


def inspect_waveforms(blobs):
    samples = sorted(name for name in blobs if name.startswith('samples/') and name.endswith('.npy'))
    if not samples:
        raise ValueError('No saved arrays')
    aggregate = {'records_checked': len(samples), 'samples': 0, 'samples_dropped': 0,
                 'partial_windows': 0, 'diagnostics_match_saved': True, 'records': []}
    for name in samples:
        saved = parse_json(blobs['diagnostics/' + PurePosixPath(name).stem + '.json'].decode())
        actual = replay_bytes(blobs[name], saved['window_size'])
        matches = canonical(actual) == canonical(saved)
        aggregate['diagnostics_match_saved'] &= matches
        aggregate['samples'] += actual['sample_count']
        aggregate['samples_dropped'] += actual['samples_dropped']
        aggregate['partial_windows'] += sum(w['partial'] for w in actual['windows'])
        aggregate['records'].append({'item': PurePosixPath(name).stem,
                                     'source_sha256': actual['source_sha256'],
                                     'diagnostic_sha256': actual['diagnostic_sha256'],
                                     'matches_saved': matches})
    aggregate['scope'] = 'Local saved-array replay; no acquisition or anomaly attribution'
    return aggregate


def inspect(claim_root, waveform_root):
    claims, claim_manifest = load_packet(claim_root)
    waves, wave_manifest = load_packet(waveform_root)
    result = {'scope': 'Evidence preparation inspection; no labels or classifier predictions generated',
              'claim_manifest': claim_manifest, 'waveform_manifest': wave_manifest,
              'claims': inspect_claims(claims), 'waveforms': inspect_waveforms(waves),
              'reviewer_declarations': {}, 'independent_accuracy': None,
              'independence_verified': False}
    for track, blobs in (('claims', claims), ('waveforms', waves)):
        result['reviewer_declarations'][track] = [
            {key: row.get(key) for key in ('role', 'reviewer_id', 'status', 'protocol_reference')}
            for row in (parse_json(blobs[name].decode()) for name in ('reviewer_a.json', 'reviewer_b.json'))]
    result['inspection_passed'] = result['waveforms']['diagnostics_match_saved']
    result['evaluation_requirements'] = {
        'claims': ['Agreed claim and feature rubrics', 'Separate completed reviews and feature coding',
                   'Documented adjudication and source-separated evaluation design'],
        'waveforms': ['Hash-linked acquisition metadata', 'Documented baseline and deviation rule',
                      'Separate completed reviews and adjudication']}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('claims', type=Path)
    parser.add_argument('waveforms', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = inspect(args.claims, args.waveforms)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    raise SystemExit(0 if result['inspection_passed'] else 1)
