import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1]))
from apply_tidy_additions import apply
from catalogue_export import categories_from
from catalogue_rules import apply_rules, load_tags


class TidyAdditionsTests(unittest.TestCase):
    def test_all_authored_decisions_follow_catalogue_rules(self):
        root = Path(__file__).parents[1]
        entries = json.loads((root / 'tidy-catalogue-additions.json').read_text())
        self.assertEqual(len(entries), 103)
        self.assertEqual(sum(not e['catalogue']['isRecipe'] for e in entries), 3)
        categories, _ = categories_from(root / 'categories.json')
        tags = load_tags(root / 'tags.json')
        for entry in entries:
            data = entry['catalogue']
            self.assertNotIn('cleanTitle', data)
            self.assertIsNone(data['likelyDuplicateOf'])
            self.assertIsNone(data['duplicateStatus'])
            self.assertTrue(0 <= data['confidence'] <= 1)
            # Validation is idempotent; nothing invalid remains to prune.
            checked = apply_rules(json.loads(json.dumps(data)), categories, tags,
                                  {'vegetarianStatus': 'not-vegetarian'} if 'meat' in data['categories'] or 'fish' in data['categories'] else {})
            self.assertEqual(checked, data, data['sourceFile'])
            self.assertTrue(all(i == i.lower() for i in data['ingredients']))

    def test_hash_guard_and_repeat_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / 'Note.md'
            file.write_text('# A note')
            manifest = root / 'decisions.json'
            manifest.write_text(json.dumps([{'markdownSHA256': hashlib.sha256(file.read_bytes()).hexdigest(), 'catalogue': {'sourceFile': 'Note.md'}}]))
            self.assertEqual(apply(manifest, root), 1)
            self.assertEqual(apply(manifest, root), 0)
            file.write_text('# Changed')
            with self.assertRaises(ValueError):
                apply(manifest, root)
