"""Controlled source/pointer/path mutation checks; fixtures are synthetic."""
import json
import io
import tempfile
import unittest
from pathlib import Path
import numpy as np
from claim_identity import claim_digest
from inspect_review_packets import inspect_claims, inspect_waveforms, load_packet, pointer, sha
from waveform_replay import replay_bytes


class PacketInspection(unittest.TestCase):
    def test_recomputed_diagnostics_detect_changed_saved_result(self):
        stream = io.BytesIO()
        np.save(stream, np.array([1+2j, 2+1j, 3+0j], dtype=np.complex64))
        raw = stream.getvalue()
        saved = replay_bytes(raw, 2)
        blobs = {'samples/fixture.npy': raw,
                 'diagnostics/fixture.json': json.dumps(saved).encode()}
        actual = inspect_waveforms(blobs)
        self.assertTrue(actual['diagnostics_match_saved'])
        self.assertEqual(actual['samples'], 3)
        self.assertEqual(actual['partial_windows'], 1)
        saved['source_summary']['rms'] += 1
        blobs['diagnostics/fixture.json'] = json.dumps(saved).encode()
        self.assertFalse(inspect_waveforms(blobs)['diagnostics_match_saved'])

    def test_json_pointer_escapes_arrays_and_failures(self):
        doc = {'a/b': {'~key': [False, 0]}}
        self.assertIs(pointer(doc, '/a~1b/~0key/0'), False)
        self.assertEqual(pointer(doc, '/a~1b/~0key/1'), 0)
        for loc in ('missing', '/a~2b', '/a~1b/~0key/01', '/a~1b/~0key/-1'):
            with self.assertRaises((ValueError, KeyError)):
                pointer(doc, loc)

    def test_manifest_changed_bytes_missing_files_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data.json'
            data.write_bytes(b'{}')
            manifest = root / 'packet_manifest.json'
            manifest.write_text(json.dumps({'files': {'data.json': sha(b'{}')}}))
            self.assertEqual(load_packet(root)[1]['matched_files'], 1)
            data.write_bytes(b'[]')
            with self.assertRaises(ValueError): load_packet(root)
            data.unlink()
            with self.assertRaises(ValueError): load_packet(root)
            for name in ('../outside', '/etc/passwd', './data.json'):
                manifest.write_text(json.dumps({'files': {name: sha(b'{}')}}))
                with self.assertRaises(ValueError): load_packet(root)
            data.symlink_to('/etc/passwd')
            manifest.write_text(json.dumps({'files': {'data.json': sha(b'{}')}}))
            with self.assertRaises(ValueError): load_packet(root)

    def test_cited_bytes_and_identity_bound_without_creating_answers(self):
        raw = b'{"gate":false}'
        item = {'id': 'fixture', 'claim_text': 'Fixture report records a failed gate.',
                'source_family': 'synthetic_fixture', 'source_references': [
                    {'document': 'source.json', 'sha256': sha(raw), 'locator': '/gate'}]}
        item['source_sha256'] = claim_digest(item)
        blobs = {'source.json': raw, 'feature_annotation.json': b'{"examples":[]}'}
        def freeze():
            blobs['frozen_blank.json'] = json.dumps({'status': 'unannotated', 'items': [item]}).encode()
        freeze()
        report = inspect_claims(blobs)
        self.assertIs(report['observations'][0]['source_passages'][0]['observed_value'], False)
        self.assertIsNone(report['observations'][0]['reference_label'])
        blobs['source.json'] = b'{"gate":true}'
        with self.assertRaises(ValueError): inspect_claims(blobs)
        blobs['source.json'] = raw
        item['claim_text'] = 'Altered wording'
        freeze()
        with self.assertRaises(ValueError): inspect_claims(blobs)


if __name__ == '__main__':
    unittest.main()
