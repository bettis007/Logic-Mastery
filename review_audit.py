"""Compare supplied reviewer worksheets without creating or adjudicating labels."""
import argparse
import hashlib
import json
from pathlib import Path

from dataset_intake import parse_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def indexed(items):
    require(isinstance(items, list) and bool(items), 'Missing review items')
    require(all(isinstance(r, dict) and text(r.get('id')) for r in items), 'Invalid review item')
    result = {r['id']: r for r in items}
    require(len(result) == len(items), 'Duplicate review ID')
    return result


def audit(template, reviews, rubric):
    result = {'scope': 'Worksheet consistency and declared reviewer agreement only',
              'technical_review_complete': False, 'independence_verified': False,
              'external_accuracy': None, 'protocol_approved': False,
              'blockers': [], 'agreements': [], 'disagreements': [],
              'joint_exclusions': [], 'incomplete': [], 'jointly_annotated': 0,
              'joint_label_agreement_rate': None}
    try:
        require(isinstance(rubric, dict), 'Invalid rubric')
        require(rubric.get('target') in ('waveform_context', 'claim_evidence'), 'Unsupported review target')
        for name in ('reference_labels', 'evidence_categories', 'handling_actions'):
            values = rubric.get(name)
            require(isinstance(values, list) and values and all(text(v) for v in values)
                    and len(set(values)) == len(values), 'Invalid rubric vocabulary')
        require(rubric.get('status') in ('draft', 'approved'), 'Invalid rubric status')
        result['protocol_approved'] = rubric['status'] == 'approved'
        if result['protocol_approved']:
            require(text(rubric.get('approval_reference')), 'Missing rubric approval record reference')
        if not result['protocol_approved']:
            result['blockers'].append('Rubric remains a draft; agreement is not an evaluation approval')
        digest = hashlib.sha256(json.dumps(rubric, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result['rubric_sha256'] = digest
        require(isinstance(template, dict) and template.get('status') == 'unannotated', 'Expected frozen blank template')
        expected = indexed(template.get('items'))
        for row in expected.values():
            require(all(row.get(k) is None for k in ('reference_label', 'evidence_category', 'handling_action')), 'Template must not contain reference answers')
            sha = row.get('source_sha256')
            require(isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha)
                    and text(row.get('source_family')), 'Invalid template source identity')
        require(isinstance(reviews, list) and len(reviews) == 2, 'Two reviewer worksheets required')
        ids, tables = [], []
        for role, review in zip(('reviewer_a', 'reviewer_b'), reviews):
            require(isinstance(review, dict) and review.get('role') == role, 'Reviewer role mismatch')
            reviewer = review.get('reviewer_id')
            require(text(reviewer), 'Missing reviewer identity declaration')
            ids.append(reviewer.strip())
            require(review.get('status') == 'complete', 'Worksheet is not marked complete')
            require(review.get('protocol_reference') == digest, 'Worksheet rubric hash mismatch')
            table = indexed(review.get('items'))
            require(set(table) == set(expected), 'Review IDs do not match frozen template')
            tables.append(table)
        require(ids[0] != ids[1], 'Reviewer identities must be distinct declarations')
        for key, original in expected.items():
            decisions = []
            for table in tables:
                row = table[key]
                require(row.get('source_sha256') == original['source_sha256']
                        and row.get('source_family') == original['source_family'], 'Review source binding mismatch')
                excluded = text(row.get('exclusion_reason'))
                values = tuple(row.get(k) for k in ('reference_label', 'evidence_category', 'handling_action'))
                if excluded:
                    require(all(v is None for v in values), 'Excluded item cannot also have reference answers')
                    decisions.append(('excluded',))
                else:
                    refs = row.get('evidence_references')
                    valid = (values[0] in rubric['reference_labels'] and values[1] in rubric['evidence_categories']
                             and values[2] in rubric['handling_actions'] and text(row.get('rationale'))
                             and text(row.get('uncertainty')) and isinstance(refs, list)
                             and bool(refs) and all(text(ref) for ref in refs))
                    decisions.append(('annotated', *values) if valid else ('incomplete',))
            if any(d[0] == 'incomplete' for d in decisions):
                result['incomplete'].append(key)
            elif all(d[0] == 'excluded' for d in decisions):
                result['joint_exclusions'].append(key)
            else:
                if all(d[0] == 'annotated' for d in decisions):
                    result['jointly_annotated'] += 1
                result['agreements' if decisions[0] == decisions[1] else 'disagreements'].append(key)
        if result['incomplete']:
            result['blockers'].append('Incomplete item reviews remain')
        result['technical_review_complete'] = not result['incomplete']
        if result['jointly_annotated']:
            result['joint_label_agreement_rate'] = len(result['agreements']) / result['jointly_annotated']
        if result['disagreements']:
            result['blockers'].append('Disagreements need separate adjudication; no tie-breaking label was generated')
        if not result['jointly_annotated']:
            result['blockers'].append('No jointly annotated examples; exclusions do not establish agreement or accuracy')
    except (ValueError, TypeError, KeyError) as exc:
        result['technical_review_complete'] = False
        result['joint_label_agreement_rate'] = None
        result['blockers'].append(str(exc))
    result['ready_for_adjudication'] = (result['technical_review_complete'] and result['protocol_approved']
                                       and bool(result['jointly_annotated'] or result['disagreements']))
    result['warning'] = 'Declared identities, references and approval are not authenticated. Agreement is not correctness.'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('template', 'reviewer_a', 'reviewer_b', 'rubric', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = [args.template, args.reviewer_a, args.reviewer_b, args.rubric]
    raw = [p.read_bytes() for p in paths]
    template, a, b, rubric = [parse_json(blob.decode()) for blob in raw]
    result = audit(template, [a, b], rubric)
    result['input_sha256'] = dict(zip(('template', 'reviewer_a', 'reviewer_b', 'rubric'),
                                    [hashlib.sha256(blob).hexdigest() for blob in raw]))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    raise SystemExit(0 if result['ready_for_adjudication'] else 1)
