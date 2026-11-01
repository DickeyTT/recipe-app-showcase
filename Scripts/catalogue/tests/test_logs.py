import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('logs', Path(__file__).parents[1] / 'catalogue_logs.py')
logs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logs)


class LogTests(unittest.TestCase):
    def test_boundaries_preserve_all_text_and_no_guessed_values(self):
        text = '# 2023 diary\nUndated intro\n28 September 2023 Cabbage\n1250g cabbage, 25g salt\n2023-11-05 Sauce\npH 3.6\n'
        rows = logs.candidates(text, 'Diary.md')
        self.assertEqual(''.join(r['text'] for r in rows), text)
        self.assertEqual([r['startDate'] for r in rows], [None, '2023-09-28', '2023-11-05'])
        self.assertEqual(rows[1]['saltGrams'], 25)
        self.assertEqual(rows[2]['pH'], 3.6)
        self.assertIsNone(rows[1]['ingredientWeightGrams'])
        self.assertTrue(all(r['needsReview'] and r['recipeSuggestion'] is None for r in rows))
        self.assertEqual(rows, logs.candidates(text, 'Diary.md'))
        self.assertIsNone(logs.candidates('03/04/23 ambiguous date\n', 'x')[0]['startDate'])

    def test_prepare_never_modifies_source_or_overwrites_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            file = source / 'log.md'
            file.write_text('2023-09-28 First batch\n')
            original = file.read_bytes()
            output = root / 'review.json'
            self.assertEqual(logs.prepare(source, output), 1)
            self.assertEqual(file.read_bytes(), original)
            self.assertEqual(json.loads(output.read_text())['version'], 1)
            with self.assertRaises(ValueError):
                logs.prepare(source, output)
            with self.assertRaises(ValueError):
                logs.prepare(source, source / 'review.json')
