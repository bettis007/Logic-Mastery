"""Synthetic input-contract tests; never evidence of external accuracy."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dataset_intake import assess, feature_digest, parse_json


class IntakeTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent
        self.features = json.loads((root / 'demo/features.json').read_text())
        self.labels = json.loads((root / 'demo/labels.json').read_text())
        self.manifest = {'schema_version': '1', 'development_inventory_complete': True,
                         'ontology_review_ref': 'synthetic contract fixture only',
                         'records': [{'id': r['id'], 'split': 'heldout',
                                      'source_family': 'synthetic_reference',
                                      'feature_sha256': feature_digest(r['features'])}
                                     for r in self.features['examples']]}

    def result(self):
        return assess(self.features, self.labels, self.manifest)

    def rejected(self, fragment):
        result = self.result()
        self.assertFalse(result['technical_compatibility_passed'])
        self.assertIn(fragment, result['blockers'][0])
        self.assertEqual(result['external_validation_status'], 'not_established')

    def test_compatible_synthetic_inputs_do_not_become_independent_evidence(self):
        result = self.result()
        self.assertTrue(result['technical_compatibility_passed'])
        self.assertFalse(result['independent_provenance_verified'])
        self.assertEqual(result['external_validation_status'], 'not_established')
        self.assertNotIn('accuracy', result)

    def test_incompatible_feature_schema_and_label_target_rejected(self):
        self.features['examples'][0]['features']['rms'] = .2
        self.rejected('feature schema')
        self.setUp()
        self.labels['provenance']['label_target'] = 'glyph_class'
        self.rejected('label target')

    def test_missing_mismatched_and_duplicate_ids_rejected(self):
        self.labels['labels'].pop()
        self.rejected('IDs must match')
        self.setUp()
        self.features['examples'].append(copy.deepcopy(self.features['examples'][0]))
        self.rejected('duplicate ID')

    def test_reference_labels_cannot_enter_inference_features(self):
        self.features['examples'][0]['expected'] = 'ACCEPT'
        self.rejected('labels must be separate')

    def test_nonfinite_boolean_and_out_of_range_features_rejected(self):
        for value in (True, float('nan'), float('inf'), -1, 2, 10**1000, '0.5'):
            self.features['examples'][0]['features']['source_authority'] = value
            self.rejected('finite numbers')

    def test_source_family_leakage_rejected(self):
        old = copy.deepcopy(self.manifest['records'][0])
        old.update(id='old-development', split='build', feature_sha256='a'*64)
        self.manifest['records'].append(old)
        self.rejected('family crosses splits')

    def test_identical_features_with_different_id_and_family_rejected(self):
        old = copy.deepcopy(self.manifest['records'][0])
        old.update(id='old-development', split='selection', source_family='another-family')
        self.manifest['records'].append(old)
        self.rejected('duplicate crosses splits')

    def test_integer_float_and_negative_zero_hashes_match(self):
        first = dict.fromkeys(self.features['examples'][0]['features'], 0)
        second = dict.fromkeys(first, -0.0)
        self.assertEqual(feature_digest(first), feature_digest(second))

    def test_digest_family_and_inventory_mismatch_rejected(self):
        self.manifest['records'][0]['feature_sha256'] = '0'*64
        self.rejected('digest mismatch')
        self.setUp()
        self.labels['labels'][0]['source_family'] = 'other'
        self.rejected('family mismatch')
        self.setUp()
        self.manifest['development_inventory_complete'] = False
        self.rejected('incomplete')
        self.setUp()
        self.manifest['ontology_review_ref'] = ''
        self.rejected('mapping reference')

    def test_strict_json_and_exclusive_cli_output(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError):
                parse_json(text)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [root / name for name in ('features.json', 'labels.json', 'manifest.json')]
            for path, content in zip(files, (self.features, self.labels, self.manifest)):
                path.write_text(json.dumps(content))
            output = root / 'result.json'
            command = [sys.executable, str(Path(__file__).with_name('dataset_intake.py')), *map(str, files), str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            old = output.read_bytes()
            self.assertEqual(len(json.loads(old)['input_file_sha256']), 3)
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
