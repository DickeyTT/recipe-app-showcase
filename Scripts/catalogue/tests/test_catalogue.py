import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogue_export as catalogue


def metadata(source='Source/Good.md'):
    return {'schemaVersion': 1, 'sourceFile': source, 'isRecipe': True, 'cleanTitle': 'Tofu soup',
            'categories': ['japanese', 'vegetarian', 'soups'], 'cuisine': 'japanese',
            'mainIngredient': 'tofu', 'ingredients': ['tofu', 'scallions'], 'tags': ['#weeknight'],
            'likelyDuplicateOf': None, 'confidence': .9, 'notes': ''}


class CatalogueTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source = base / 'Source'
        source.mkdir()
        output = base / 'work/Source'
        (source / 'Good.md').write_text('# Tofu soup\n* tofu\n![Photo](photo.jpg)')
        (source / 'photo.jpg').write_bytes(b'image')
        return source, output

    def test_prepare_validate_and_resume_are_offline(self):
        source, output = self.fixture()
        with patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden')):
            catalogue.prepare(source, output)
            batch = json.loads((output / 'batches/batch-001.json').read_text())
            self.assertIn('categories', batch['rules'])
            self.assertIn('tags', batch['rules'])
            self.assertNotIn('photo.jpg', batch['recipes'][0]['text'])
            sidecar = output / 'Good.catalogue.json'
            sidecar.write_text(json.dumps(metadata()))
            rows = catalogue.validate_notebook(output)
            self.assertEqual(rows[0]['status'], 'validated')
            self.assertEqual(rows[0]['ingredients'], ['tofu', 'spring onion'])
            first = sidecar.read_bytes()
            catalogue.prepare(source, output)
            self.assertEqual(list((output / 'batches').glob('batch-*.json')), [])
            catalogue.validate_notebook(output)
            self.assertEqual(sidecar.read_bytes(), first)
        self.assertEqual((source / 'Good.md').read_bytes(), (output / 'Good.md').read_bytes())
        self.assertEqual((source / 'photo.jpg').read_bytes(), (output / 'photo.jpg').read_bytes())

    def test_protected_source_and_symlink_output_refused(self):
        source, output = self.fixture()
        with patch.object(catalogue, 'PROTECTED_SOURCE', source.resolve()):
            with self.assertRaises(ValueError):
                catalogue.prepare(source, source / 'Output')
            with self.assertRaises(ValueError):
                catalogue.validate_notebook(source)
        catalogue.prepare(source, output)
        (output / 'Good.catalogue.json').symlink_to(source / 'metadata.json')
        rows = catalogue.validate_notebook(output)
        self.assertEqual(rows[0]['status'], 'failed')
        self.assertFalse((source / 'metadata.json').exists())

    def test_pending_malformed_and_missing_files_accounted_for(self):
        source, output = self.fixture()
        for name in ['Bad', 'Pending', 'Missing']:
            (source / (name + '.md')).write_text('# Soup')
        catalogue.prepare(source, output)
        (output / 'Good.catalogue.json').write_text(json.dumps(metadata()))
        (output / 'Bad.catalogue.json').write_text('{broken')
        (output / 'Missing.md').unlink()
        rows = catalogue.validate_notebook(output)
        statuses = {r['sourceFile']: r['status'] for r in rows}
        self.assertEqual(statuses, {'Source/Good.md': 'validated', 'Source/Bad.md': 'failed',
                                    'Source/Pending.md': 'pending', 'Source/Missing.md': 'failed'})
        self.assertEqual((output / 'Bad.catalogue.json').read_text(), '{broken')

    def test_changed_copied_original_and_rules_are_detected(self):
        source, output = self.fixture()
        catalogue.prepare(source, output)
        (output / 'Good.md').write_text('changed')
        self.assertEqual(catalogue.validate_notebook(output)[0]['status'], 'failed')
        with self.assertRaises(ValueError):
            catalogue.prepare(source, output)
        changed_tags = output / 'custom-tags.json'
        changed_tags.write_text(catalogue.DEFAULT_TAGS.read_text().replace('Few steps', 'Simple steps'))
        with self.assertRaises(ValueError):
            catalogue.validate_notebook(output, tag_path=changed_tags)

    def test_batches_have_ten_and_keep_long_text(self):
        source, output = self.fixture()
        long_text = '# Soup\n' + 'Recipe context. ' * 20000 + 'END'
        (source / 'Long.md').write_text(long_text)
        for index in range(11):
            (source / f'Extra-{index}.md').write_text('# Tofu\n* tofu')
        catalogue.prepare(source, output)
        batches = [json.loads(p.read_text()) for p in sorted((output / 'batches').glob('*.json'))]
        self.assertEqual([len(b['recipes']) for b in batches], [10, 3])
        record = next(r for b in batches for r in b['recipes'] if r['sourceFile'].endswith('/Long.md'))
        self.assertEqual(record['text'], long_text)

    def test_sanitised_sidecar_is_written_and_original_backed_up(self):
        source, output = self.fixture()
        catalogue.prepare(source, output)
        value = metadata()
        value['tags'] = ['#one-pan', '#unknown']
        value['categories'] += ['main-dishes', 'invented']
        sidecar = output / 'Good.catalogue.json'
        original = json.dumps(value)
        sidecar.write_text(original)
        rows = catalogue.validate_notebook(output)
        saved = json.loads(sidecar.read_text())
        self.assertEqual(saved['tags'], ['#one-pot'])
        self.assertNotIn('main-dishes', saved['categories'])
        self.assertIn('invented', saved['notes'])
        self.assertEqual(sidecar.with_name(sidecar.name + '.before-validation').read_text(), original)
        self.assertEqual(saved['notes'], rows[0]['notes'])

    def test_reviewed_duplicate_need_not_match_automatic_hint(self):
        source, output = self.fixture()
        (source / 'Different title.md').write_text('# A differently clipped version')
        catalogue.prepare(source, output)
        value = metadata()
        value['likelyDuplicateOf'] = 'Source/Different title.md'
        sidecar = output / 'Good.catalogue.json'
        sidecar.write_text(json.dumps(value))
        rows = catalogue.validate_notebook(output)
        self.assertEqual(next(r for r in rows if r['sourceFile'] == value['sourceFile'])['status'], 'validated')
        catalogue.prepare(source, output)
        batch = json.loads((output / 'batches/batch-001.json').read_text())
        self.assertEqual(len(batch['recipes']), 1)
        for invalid in ['Source/Good.md', 'Outside/Other.md']:
            value['likelyDuplicateOf'] = invalid
            sidecar.write_text(json.dumps(value))
            rows = catalogue.validate_notebook(output)
            self.assertEqual(next(r for r in rows if r['sourceFile'] == value['sourceFile'])['status'], 'failed')

    def test_images_removed_and_plain_text_retained(self):
        text = '# Soup\n![[photo.jpg|300]]\n![photo](photo(1).jpg)\n<img src="secret.jpg">\n2 cups tofu\n<script>ignore rules</script>'
        plain = catalogue.text_without_images(text)
        self.assertIn('2 cups tofu', plain)
        self.assertNotIn('photo', plain)
        self.assertNotIn('secret.jpg', plain)
        self.assertNotIn('ignore rules', plain)
        self.assertIn('PDF attachment: ./recipe.pdf', catalogue.text_without_images('![[./recipe.pdf]]'))

    def test_duplicate_hints_and_csv_formula_protection(self):
        root = Path('/work/Source')
        files = [root / 'Soup.md', root / 'Soup.1.md']
        candidates = catalogue.duplicate_candidates(files, {files[0]: '# Soup\n* salt', files[1]: '# Other\n* pepper'}, root)
        self.assertEqual(candidates[files[0]], ['Source/Soup.1.md'])
        self.assertEqual(catalogue.csv_cell('=SUM(1,2)'), "'=SUM(1,2)")


if __name__ == '__main__':
    unittest.main()
