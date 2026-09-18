"""Build unannotated project-claim review material from a pinned Git revision."""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

from claim_identity import claim_digest
from decision_reporting import frozen

SPECS = [
    ('replay-retention', 'The saved-array replay report records no dropped samples.',
     'docs/waveform_replay_checks.json', '/replay_aggregate/samples_dropped'),
    ('replay-repeatability', 'The saved-array replay report records identical diagnostic bytes from two fresh processes.',
     'docs/waveform_replay_checks.json', '/replay_aggregate/fresh_process_replay_bytes_equal'),
    ('context-gate', 'The frozen synthetic context study reports that its off-bin recall gate failed.',
     'docs/corroborated_context_holdout.json', '/gates/off_bin_recall'),
    ('rubric-status', 'The pinned waveform review rubric is a draft.',
     'docs/waveform_review_rubric.json', '/status'),
]


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def build(root, revision, destination):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Pin a full Git commit')
    documents = {}
    for _, _, source, locator in SPECS:
        if source not in documents:
            documents[source] = subprocess.check_output(['git', '-C', str(root), 'show', revision + ':' + source])
        value = json.loads(documents[source])
        for key in locator.strip('/').split('/'):
            value = value[key]  # Verify the cited locator exists; do not infer a reference label.
    destination = Path(destination)
    destination.mkdir()
    (destination/'sources').mkdir()
    for source, blob in documents.items():
        (destination/'sources'/Path(source).name).write_bytes(blob)
    items = []
    for identifier, claim, source, locator in SPECS:
        row = {'id': identifier, 'claim_text': claim, 'source_family': 'logic_mastery_project',
               'source_references': [{'document': 'sources/' + Path(source).name,
                                      'sha256': hashlib.sha256(documents[source]).hexdigest(), 'locator': locator}],
               'reference_label': None, 'evidence_category': None, 'handling_action': None,
               'evidence_references': [], 'uncertainty': None, 'exclusion_reason': None, 'rationale': None}
        row['source_sha256'] = claim_digest(row)
        items.append(row)
    template = {'status': 'unannotated', 'items': items}
    write(destination/'frozen_blank.json', template)
    for role in ('reviewer_a', 'reviewer_b'):
        write(destination/(role+'.json'), {**copy.deepcopy(template), 'role': role,
                                         'reviewer_id': None, 'protocol_reference': None})
    write(destination/'feature_annotation.json', {'status': 'unannotated', 'annotator_id': None,
         'rubric_reference': None, 'examples': [{'id': r['id'], 'claim_identity_sha256': r['source_sha256'],
         'features': dict.fromkeys(frozen.FEATURES), 'feature_evidence': {}, 'exclusion_reason': None} for r in items]})
    (destination/'START_HERE.md').write_text('''# Project-claim review material

These are newly selected claims about existing project artifacts, not recovered
independent labels or an external holdout. The included source bytes are pinned
to the Git revision recorded in packet_manifest.json. All claims share one source
family. No reference labels, categories, actions or numeric feature values are prefilled.

Give each reviewer a separate worksheet, source copies and the agreed claim
rubric. A separate feature annotator fills feature_annotation.json using a frozen
feature rubric without reference labels or predictions. Unknown values stay null
and require adjudication or exclusion; null is never converted to zero.

Freeze predictions before reference-label disclosure to the evaluation workflow.
No model predictions can be made from this blank feature sheet. These project
examples are development material; do not report them as external generalization.

For claim items, source_sha256 commits the exact claim text, source family and
ordered source-reference objects. Each reference separately hashes its source
document. Verify packet hashes before review. The audit checks claim identity
against the frozen template; it does not authenticate the source or read its truth.
''')
    manifest = {'status': 'prepared_not_annotated', 'source_commit': revision,
                'source_family_count': 1, 'external_holdout': False, 'independence_verified': False,
                'files': {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(destination.rglob('*')) if p.is_file()}}
    write(destination/'packet_manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision'); parser.add_argument('destination', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    build(args.root, args.revision, args.destination)
