"""Check supplied claim-feature datasets and declared split separation, without scoring.

This checks structure and declared relationships, not provenance or human blinding.
It never generates missing labels, maps incompatible targets or trains a model.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from decision_reporting import frozen
from evaluate_labels import LABELS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 200


def feature_digest(features):
    # Normalize JSON numeric spelling, so 0 and 0.0 cannot hide exact duplicates.
    values = [float(features[name]) for name in frozen.FEATURES]
    values = [0.0 if v == 0 else v for v in values]
    return hashlib.sha256(json.dumps(values, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def rows_by_id(rows, context):
    require(isinstance(rows, list) and bool(rows), context + ': expected nonempty list')
    require(all(isinstance(r, dict) and identifier(r.get('id')) for r in rows), context + ': invalid ID')
    result = {r['id']: r for r in rows}
    require(len(result) == len(rows), context + ': duplicate ID')
    return result


def assess(features, labels, manifest):
    result = {'technical_compatibility_passed': False,
              'external_validation_status': 'not_established',
              'independent_provenance_verified': False,
              'scope': 'Claim-feature schema and declared split checks only; no accuracy score',
              'blockers': [],
              'limitations': ['Source identity, human blinding and completeness are not authenticated',
                              'Exact feature duplicates are checked; semantic near-duplicates are not',
                              'Other-split digests and family memberships are supplied declarations',
                              'A reference to an ontology review does not validate its conclusions']}
    try:
        require(isinstance(features, dict) and set(features) == {'examples'}, 'Expected inference-only examples object')
        examples = rows_by_id(features['examples'], 'features')
        for row in examples.values():
            require(set(row) == {'id', 'features'}, 'Unexpected feature row fields; labels must be separate')
            values = row['features']
            require(isinstance(values, dict) and set(values) == set(frozen.FEATURES), 'Incompatible feature schema')
            require(all(type(v) in (int, float) and 0 <= v <= 1 and math.isfinite(v) for v in values.values()),
                    'Features must be finite numbers in range; booleans are not numbers')
        require(isinstance(labels, dict) and set(labels) == {'provenance', 'labels'}, 'Expected separate reference labels')
        meta = labels['provenance']
        require(isinstance(meta, dict), 'Invalid annotation provenance')
        for field in ('dataset_kind', 'annotation_author', 'annotation_protocol', 'label_target'):
            require(isinstance(meta.get(field), str) and bool(meta[field].strip()), 'Missing annotation declaration: ' + field)
        require(meta['label_target'] == 'epistemic_category', 'Incompatible label target; no automatic mapping')
        reference = rows_by_id(labels['labels'], 'labels')
        require(set(reference) == set(examples), 'Feature and label IDs must match exactly')
        for row in reference.values():
            require(set(row) == {'id', 'expected', 'source_family'}, 'Invalid reference fields')
            require(row['expected'] in LABELS and identifier(row['source_family']), 'Invalid label or source family')
        require(isinstance(manifest, dict) and set(manifest) ==
                {'schema_version', 'development_inventory_complete', 'ontology_review_ref', 'records'}, 'Invalid split manifest')
        require(manifest['schema_version'] == '1', 'Unsupported split schema')
        require(manifest['development_inventory_complete'] is True, 'Development inventory declared incomplete')
        require(identifier(manifest['ontology_review_ref']), 'Missing reviewed category/action mapping reference')
        records = rows_by_id(manifest['records'], 'split manifest')
        families, hashes, heldout = {}, {}, set()
        for key, row in records.items():
            require(set(row) == {'id', 'source_family', 'split', 'feature_sha256'}, 'Invalid split row fields')
            family, split, digest = row['source_family'], row['split'], row['feature_sha256']
            require(identifier(family) and split in ('build', 'calibration', 'selection', 'heldout'), 'Invalid family or split')
            require(isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'Invalid feature digest')
            require(family not in families or families[family] == split, 'Source family crosses splits')
            require(digest not in hashes or hashes[digest] == split, 'Exact feature duplicate crosses splits')
            families[family], hashes[digest] = split, split
            if split == 'heldout':
                heldout.add(key)
        require(heldout == set(examples), 'Heldout inventory must match supplied examples exactly')
        for key, row in examples.items():
            require(records[key]['source_family'] == reference[key]['source_family'], 'Label/manifest source-family mismatch')
            require(records[key]['feature_sha256'] == feature_digest(row['features']), 'Heldout feature digest mismatch')
        result.update(technical_compatibility_passed=True, examples=len(examples),
                      heldout_source_families=len({r['source_family'] for r in reference.values()}),
                      exact_feature_groups=len({feature_digest(r['features']) for r in examples.values()}),
                      declared_dataset_kind=meta['dataset_kind'],
                      class_support={label: sum(r['expected'] == label for r in reference.values()) for label in LABELS})
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        result['blockers'].append(str(exc))
    return result


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('features', 'labels', 'manifest', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = [args.features, args.labels, args.manifest]
    raw = []
    try:
        raw = [path.read_bytes() for path in paths]
        result = assess(*(parse_json(blob.decode('utf-8')) for blob in raw))
    except (ValueError, OSError) as exc:
        result = {'technical_compatibility_passed': False, 'external_validation_status': 'not_established',
                  'independent_provenance_verified': False, 'blockers': [str(exc)]}
    # Private report: input digests are written only to the caller-chosen output.
    result['input_file_sha256'] = {name: hashlib.sha256(blob).hexdigest()
                                  for name, blob in zip(('features', 'labels', 'manifest'), raw)}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return 0 if result['technical_compatibility_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
