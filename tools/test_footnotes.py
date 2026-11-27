"""Alternative readings are shown as verse footnotes with reasons; a hold needs no defensible base text."""
import json
import pathlib
import re
import unittest
from html import escape

R = pathlib.Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((R / name).read_text(encoding='utf-8'))


class FootnoteTests(unittest.TestCase):
    def footnoted(self):
        return [(p, v) for p in read('data/editorial.json')['passages'] for v in p['verses'] if v.get('footnotes')]

    def test_genesis_8_7_text_is_the_hebrew_reading_and_the_greek_reading_is_a_footnote(self):
        verse = next(v for _, v in self.footnoted() if v['source'] == 'Gen.8.7')
        self.assertIn('to and fro', verse['en'])
        self.assertNotIn('did not return', verse['en'])
        note = verse['footnotes'][0]
        self.assertIn('did not return', note['en'])
        self.assertIn('돌아오지 않았다', note['ko'])
        self.assertIn('no volvió', note['es'])
        for lang, reason in (('ko', '때문'), ('en', 'could not'), ('es', 'No se pudo')):
            self.assertIn(reason, note[lang])

    def test_every_footnote_is_visible_under_its_verse_in_all_languages(self):
        self.assertTrue(self.footnoted())
        for passage, verse in self.footnoted():
            for lang in ('ko', 'en', 'es'):
                page = (R / 'dist' / lang / passage['slug'] / 'index.html').read_text(encoding='utf-8')
                article = re.search(r'<article class="verse" id="v%d">.*?</article>' % verse['number'], page, re.S).group(0)
                before_details = article.split('<details', 1)[0]
                for index, note in enumerate(verse['footnotes'], 1):
                    anchor = 'fn-v%d-%d' % (verse['number'], index)
                    self.assertIn('href="#%s"' % anchor, before_details)
                    self.assertIn('id="%s"' % anchor, before_details)
                    self.assertIn(escape(note[lang]), before_details)
                self.assertIn(escape(verse[lang]) + '<sup class="fn-ref">', before_details)
                markdown = (R / 'dist/data' / (passage['slug'] + '.' + lang + '.md')).read_text(encoding='utf-8')
                self.assertIn(verse['footnotes'][0][lang], markdown)

    def test_footnotes_match_the_decision_record_and_public_data(self):
        decisions = {d['id']: d for d in read('data/decisions.json')['verses']}
        records = {r['id']: r for r in read('dist/data/hansam-bible.json')['records']}
        library = read('dist/library/original.json')['records']
        for _, verse in self.footnoted():
            self.assertEqual(verse['footnotes'], decisions[verse['id']]['footnotes'])
            self.assertEqual(verse['footnotes'], records[verse['id']]['footnotes'])
            book, chapter, number = verse['source'].split('.')
            self.assertEqual([n['ko'] for n in verse['footnotes']], library[book][chapter][number]['footnotes']['ko'])
        for d in decisions.values():
            for note in d.get('footnotes', []):
                self.assertTrue(all(note[k].strip() for k in ('ko', 'en', 'es')))

    def test_standing_rule_is_written_where_the_automation_reads_it(self):
        agents = (R / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('Owner rule (2026-11-27)', agents)
        self.assertIn('verse footnote', agents)
        self.assertIn('no defensible base text', agents)
        for name in ('RESET-SCHEDULING.ko.md', 'automation/LEFTOVER-BATCH-PROMPT.md'):
            self.assertIn('각주', (R / name).read_text(encoding='utf-8'))

    def test_a_hold_must_say_why_no_defensible_base_text_exists(self):
        for entry in read('automation/held-verses.json')['verses']:
            if entry.get('status', 'held') == 'held':
                self.assertTrue(entry.get('no_defensible_base_ko'), entry['id'])


if __name__ == '__main__':
    unittest.main()
