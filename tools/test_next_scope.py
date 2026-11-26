import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import next_scope

R = pathlib.Path(__file__).resolve().parents[1]
ORDER = ['Gen.8.%d' % i for i in range(1, 23)] + ['Gen.9.%d' % i for i in range(1, 30)]


class NextScopeTests(unittest.TestCase):
    def test_held_verse_is_skipped_and_batch_continues(self):
        published = {'Gen.8.%d' % i for i in range(1, 6)}
        result = next_scope.next_scope(ORDER, published, {'Gen.8.7'}, 5)
        self.assertEqual(result['scope'], ['Gen.8.6', 'Gen.8.8', 'Gen.8.9', 'Gen.8.10', 'Gen.8.11'])
        self.assertEqual(result['skipped_held'], ['Gen.8.7'])

    def test_batch_does_not_cross_chapter(self):
        published = {'Gen.8.%d' % i for i in range(1, 20)}
        result = next_scope.next_scope(ORDER, published, set(), 5)
        self.assertEqual(result['scope'], ['Gen.8.20', 'Gen.8.21', 'Gen.8.22'])

    def test_held_at_chapter_end_moves_to_next_chapter(self):
        published = {'Gen.8.%d' % i for i in range(1, 22)}
        result = next_scope.next_scope(ORDER, published, {'Gen.8.22'}, 3)
        self.assertEqual(result['scope'], ['Gen.9.1', 'Gen.9.2', 'Gen.9.3'])
        self.assertEqual(result['skipped_held'], [])

    def test_released_entries_are_not_held(self):
        held = {'verses': [{'id': 'Gen.8.7', 'status': 'released'}, {'id': 'Gen.8.9'}]}
        self.assertEqual(next_scope.held_ids(held), {'Gen.8.9'})

    def test_repository_hold_file_is_valid(self):
        held = json.loads((R/'automation/held-verses.json').read_text(encoding='utf-8'))
        for entry in held['verses']:
            self.assertRegex(entry['id'], r'^[A-Za-z0-9]+\.\d+\.\d+$')
            self.assertTrue(entry['reason_ko'] and entry['release_when_ko'])


if __name__ == '__main__':
    unittest.main()
