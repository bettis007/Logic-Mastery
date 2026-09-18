"""Create unfilled review packets from saved IQ; never generate reference labels."""
import argparse
import hashlib
import json
from pathlib import Path

from waveform_replay import read_bounded, replay_bytes


GUIDE = '''# Independent review preparation

This packet contains saved numeric arrays and diagnostics, not verified acquisition
metadata or ground truth. Original filenames and prior provisional labels are
withheld from reviewer worksheets. This reduces one source of bias; it does not
prove blinding, independence or truthful acquisition history.

The coordinator must agree a target definition, evidence requirements, handling
of missing metadata and sampling plan before review. The current fixed real-valued
synthetic detector is incompatible with these complex arrays; do not score it by
silently discarding Q, inventing context or guessing sample rate.

Give each reviewer only their worksheet, this guide, samples and diagnostics.
Do not distribute the coordinator mapping or the other reviewer's answers.
Review independently without predictions or earlier provisional labels. Leave
reference_label null where evidence is insufficient, and record a reason. Use
separate evidence_category and handling_action fields; quarantine is not a truth
label. Record the rubric, source references, uncertainties and reviewer identity.
A separate adjudicator must resolve disagreements after both reviews are frozen.

All recovered records initially share one conservative source-family assignment.
Do not split windows from the same source across development and heldout data.
Do not use this entire collection both to develop an adapter and to claim a final
holdout result. Hashes identify bytes, not trusted timestamps or reviewer identity.

The claim-evidence template is also blank. It needs supplied claims, source
material, a reviewed feature rubric and independent category/action annotations.
Waveform measurements must not be substituted for the claim model's evidence
features. No accuracy or reviewer agreement exists until actual reviews occur.
'''


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def prepare(paths, destination):
    # Validate every source before creating a packet. Bound batch memory as well.
    if not 1 <= len(paths) <= 100:
        raise ValueError('Supply a bounded nonempty source list')
    prepared, hashes, total_bytes = [], set(), 0
    for path in paths:
        blob = read_bounded(path)
        total_bytes += len(blob)
        if total_bytes > 100 * 1024 * 1024:
            raise ValueError('Packet exceeds batch byte limit')
        result = replay_bytes(blob)
        digest = result['source_sha256']
        if digest in hashes:
            raise ValueError('Duplicate source bytes')
        hashes.add(digest)
        prepared.append((Path(path).name, blob, result))
    destination = Path(destination)
    destination.mkdir()  # Exclusive; existing packets remain untouched.
    (destination / 'samples').mkdir()
    (destination / 'diagnostics').mkdir()
    items, mapping = [], []
    for index, (name, blob, diagnostics) in enumerate(sorted(prepared, key=lambda r: r[2]['source_sha256'])):
        item = 'item_' + str(index + 1).zfill(4)
        (destination / 'samples' / (item + '.npy')).write_bytes(blob)
        write_json(destination / 'diagnostics' / (item + '.json'), diagnostics)
        items.append({'id': item, 'source_sha256': diagnostics['source_sha256'],
                      'source_family': 'recovered_collection_unverified',
                      'reference_label': None, 'evidence_category': None,
                      'handling_action': None, 'evidence_references': [],
                      'uncertainty': None, 'exclusion_reason': None, 'rationale': None})
        mapping.append({'id': item, 'original_filename': name,
                        'source_sha256': diagnostics['source_sha256']})
    for role in ('reviewer_a', 'reviewer_b'):
        write_json(destination / (role + '.json'), {'status': 'unannotated',
                   'reviewer_id': None, 'protocol_reference': None, 'role': role, 'items': items})
    write_json(destination / 'coordinator_only.json', {'scope': 'Do not distribute this filename mapping to blinded reviewers',
               'independence_verified': False, 'mapping': mapping})
    write_json(destination / 'claim_annotation_template.json', {
        'status': 'unannotated_template_not_recovered_labels',
        'rubric_reference': None, 'ontology_mapping_reference': None,
        'feature_annotator': None, 'reviewer_a': None, 'reviewer_b': None,
        'adjudicator': None, 'claims': [],
        'required_claim_fields': ['id', 'claim_text', 'source_references', 'source_family',
                                  'source_sha256', 'feature_values', 'evidence_category',
                                  'handling_action', 'reviewer_rationale', 'adjudication']})
    (destination / 'REVIEW_GUIDE.md').write_text(GUIDE)
    # Written last: absence means incomplete packet; never treat it as ready.
    manifest = {'status': 'prepared_for_review_not_annotated', 'source_count': len(items),
                'independence_verified': False,
                'files': {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(destination.rglob('*')) if p.is_file()}}
    write_json(destination / 'packet_manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('sources', nargs='+', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.sources, args.destination), indent=2))
