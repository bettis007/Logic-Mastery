"""Source-byte binding and blank-annotation preservation checks."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from claim_identity import claim_digest
from prepare_claim_evidence import build


class ClaimPacket(unittest.TestCase):
    def test_pinned_sources_blank_fields_and_exclusive_creation(self):
        root=Path(__file__).parent
        revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'claims';manifest=build(root,revision,out)
            for name,digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),digest)
            blank=json.loads((out/'frozen_blank.json').read_text())
            for row in blank['items']:
                self.assertEqual(claim_digest(row),row['source_sha256'])
                self.assertIsNone(row['reference_label'])
                for ref in row['source_references']:
                    actual=(out/ref['document']).read_bytes()
                    self.assertEqual(hashlib.sha256(actual).hexdigest(),ref['sha256'])
                    source='docs/'+Path(ref['document']).name
                    self.assertEqual(actual,subprocess.check_output(['git','-C',str(root),'show',revision+':'+source]))
            features=json.loads((out/'feature_annotation.json').read_text())
            self.assertTrue(all(v is None for r in features['examples'] for v in r['features'].values()))
            self.assertFalse(manifest['external_holdout'])
            with self.assertRaises(FileExistsError):build(root,revision,out)
            with self.assertRaises(ValueError):build(root,'main',Path(tmp)/'unpinned')

    def test_missing_and_duplicate_references_rejected(self):
        row={'claim_text':'Fixture','source_family':'fixture','source_references':[]}
        with self.assertRaises(ValueError):claim_digest(row)
        ref={'document':'test','sha256':'a'*64,'locator':'/x'}
        row['source_references']=[ref,ref]
        with self.assertRaises(ValueError):claim_digest(row)


if __name__=='__main__':unittest.main()
