import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('tidy_sidecars', Path(__file__).parents[1] / 'tidy_sidecars.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TidySidecarsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tidy/Notes').mkdir(parents=True)
        (self.root / 'catalogue-full/Old').mkdir(parents=True)
        self.markdown = self.root / 'tidy/Notes/Note.md'
        self.markdown.write_text('# A note\n', encoding='utf-8')
        self.original = self.root / 'catalogue-full/Old/Note.catalogue.json'
        self.data = dict(sourceFile='Old/Note.md', cleanTitle='Old title', likelyDuplicateOf='Old/Other.md', duplicateStatus='confirmed', isRecipe=True, categories=['notes-logs'], tags=[], ingredients=['salt'], cuisine=None, mainIngredient=None, confidence=0.7, notes='Keep this.')
        self.original.write_text(json.dumps(self.data), encoding='utf-8')
        self.row = dict(tidy_file='Notes/Note.md', type='note', original_file='Old/Note.md', catalogue_sidecar='catalogue-full/Old/Note.catalogue.json')
        self.mapping = self.root / 'map.csv'

    def run_transfer(self, rows=None):
        with self.mapping.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=self.row.keys())
            writer.writeheader()
            writer.writerows(rows or [self.row])
        return module.transfer(self.mapping, self.root)

    def test_preserves_metadata_sources_and_safe_repeat(self):
        before = self.original.read_bytes(), self.markdown.read_bytes()
        self.assertEqual(self.run_transfer()['created'], 1)
        target = self.markdown.with_suffix('.catalogue.json')
        copied = json.loads(target.read_text())
        self.assertFalse(copied['isRecipe'])
        self.assertNotIn('cleanTitle', copied)
        self.assertIsNone(copied['likelyDuplicateOf'])
        self.assertIsNone(copied['duplicateStatus'])
        self.assertEqual(copied['sourceFile'], 'Notes/Note.md')
        for key in ('categories', 'tags', 'ingredients', 'cuisine', 'mainIngredient', 'confidence', 'notes'):
            self.assertEqual(copied[key], self.data[key])
        self.assertEqual(self.run_transfer()['created'], 0)
        self.assertEqual(before, (self.original.read_bytes(), self.markdown.read_bytes()))
        copied['notes'] = 'User changed'
        target.write_text(json.dumps(copied))
        with self.assertRaises(ValueError):
            self.run_transfer()
        self.assertEqual(json.loads(target.read_text()), copied)

    def test_missing_sidecar_is_reported(self):
        self.row['catalogue_sidecar'] = ''
        self.assertEqual(self.run_transfer(), dict(created=0, mapped=0, missing=['Notes/Note.md']))

    def test_preflight_rejects_escape_before_writing(self):
        bad = dict(self.row, tidy_file='../outside.md')
        with self.assertRaises(ValueError):
            self.run_transfer([self.row, bad])
        self.assertFalse(self.markdown.with_suffix('.catalogue.json').exists())

    def test_rejects_destination_symlink(self):
        self.markdown.with_suffix('.catalogue.json').symlink_to(self.original)
        with self.assertRaises(ValueError):
            self.run_transfer()
