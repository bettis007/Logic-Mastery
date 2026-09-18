"""Known synthetic signals and packet-integrity oracles, not external labels."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from prepare_review_packet import prepare
from waveform_replay import canonical, replay_bytes


def encoded(x):
    stream = io.BytesIO()
    np.save(stream, x)
    return stream.getvalue()


class ReplayTests(unittest.TestCase):
    def test_complex_positive_and_negative_tones_preserve_frequency_sign(self):
        for frequency in (.125, -.125):
            x = 2 * np.exp(2j * np.pi * frequency * np.arange(256))
            result = replay_bytes(encoded(x))
            self.assertEqual(result['sample_count'], 256)
            for row in result['windows']:
                self.assertAlmostEqual(row['rms'], 2)
                self.assertAlmostEqual(row['dominant_ac_cycles_per_sample'], frequency)
                self.assertAlmostEqual(row['dominant_ac_energy_fraction'], 1)
            self.assertIsNone(result['sample_rate_hz'])

    def test_zero_and_dc_do_not_invent_ac_frequency(self):
        for value in (0j, 3+4j):
            result = replay_bytes(encoded(np.full(128, value)))['source_summary']
            self.assertAlmostEqual(result['rms'], abs(value))
            self.assertEqual(result['dominant_ac_energy_fraction'], 0)
            self.assertIsNone(result['dominant_ac_cycles_per_sample'])

    def test_partial_tail_and_q_only_samples_retained(self):
        blob = encoded(np.full(129, 1j, dtype=np.complex64))
        result = replay_bytes(blob)
        self.assertEqual([r['sample_count'] for r in result['windows']], [128, 1])
        self.assertTrue(result['windows'][-1]['partial'])
        self.assertEqual(result['source_summary']['rms'], 1)
        self.assertEqual(result['samples_dropped'], 0)
        self.assertEqual(result['source_sha256'], hashlib.sha256(blob).hexdigest())
        self.assertEqual(canonical(result), canonical(replay_bytes(blob)))

    def test_unsupported_and_malformed_arrays_rejected(self):
        values = [np.ones(128), np.ones((2, 128), complex), np.array([], complex),
                  np.array([complex(float('nan'), 0)]), np.array([{}], dtype=object)]
        for value in values:
            with self.assertRaises(ValueError):
                replay_bytes(encoded(value))
        blob = encoded(np.ones(128, complex))
        for changed in (blob[:-1], blob + b'extra', b'not-npy'):
            with self.assertRaises(ValueError):
                replay_bytes(changed)
        for size in (True, 0, 1, 1.5, 1000000):
            with self.assertRaises(ValueError):
                replay_bytes(blob, size)

    def test_huge_shape_header_rejected_before_allocation(self):
        stream = io.BytesIO()
        np.lib.format.write_array_header_1_0(stream, {'descr': '<c16', 'fortran_order': False, 'shape': (10**12,)})
        with self.assertRaisesRegex(ValueError, 'declared sample count'):
            replay_bytes(stream.getvalue())

    def test_packet_preserves_bytes_and_leaves_reviews_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'old_provisional_positive.npy'
            original = encoded(np.arange(129, dtype=float).astype(complex))
            source.write_bytes(original)
            destination = root / 'packet'
            manifest = prepare([source], destination)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual((destination / 'samples/item_0001.npy').read_bytes(), original)
            for role in ('reviewer_a', 'reviewer_b'):
                text = (destination / (role + '.json')).read_text()
                self.assertNotIn(source.name, text)
                review = json.loads(text)
                self.assertIsNone(review['reviewer_id'])
                self.assertIsNone(review['items'][0]['reference_label'])
                self.assertIsNone(review['items'][0]['evidence_category'])
            for relative, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((destination / relative).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                prepare([source], destination)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                prepare([source, source], root / 'duplicate')
            self.assertFalse((root / 'duplicate').exists())


if __name__ == '__main__':
    unittest.main()
