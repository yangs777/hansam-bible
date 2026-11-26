"""Regression checks for the reading layers and the Korean divine-name edition."""
import json
import pathlib
import unittest
from html.parser import HTMLParser

import editorial_text
import review_layers

R = pathlib.Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((R / name).read_text(encoding='utf-8'))


class ReadingPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.closed = 0
        self.summary = 0
        self.main = False
        self.visible = []
        self.catalog = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main':
            self.main = True
        if tag == 'details' and 'open' not in attrs:
            self.closed += 1
        if tag == 'summary':
            self.summary += 1
        if tag == 'a' and attrs.get('class') == 'passage-row':
            self.catalog.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'main':
            self.main = False
        if tag == 'details':
            self.closed -= 1
        if tag == 'summary':
            self.summary -= 1

    def handle_data(self, text):
        if self.main and (not self.closed or self.summary):
            self.visible.append(text)


class ReadingUITests(unittest.TestCase):
    def test_spacing_repairs_generated_prose_and_preserves_witness_ids(self):
        self.assertEqual(editorial_text.spaced('창세기5장1–25절'), '창세기 5장 1–25절')
        self.assertEqual(editorial_text.spaced('창세기5장 첫25절'), '창세기 5장 첫 25절')
        self.assertEqual(editorial_text.spaced('독립 제안,공식 검토.26절 계보,라멕의'), '독립 제안, 공식 검토. 26절 계보, 라멕의')
        self.assertEqual(editorial_text.spaced('Genesis5:1–25 / Génesis5:1–25'), 'Genesis 5:1–25 / Génesis 5:1–25')
        original = '4Q37 · Swete1901 · v0.4.19 · 1,000 · יהוה · CC BY 4.0'
        self.assertEqual(editorial_text.spaced(original), original)

    def test_home_catalog_uses_biblical_order_in_all_languages(self):
        expected = ['genesis-1', 'genesis-2', 'genesis-3', 'genesis-4', 'genesis-5', 'genesis-6', 'genesis-7', 'genesis-8', 'numbers-6-24-26', 'deuteronomy-32-8', 'psalm-1']
        for lang in ('ko', 'en', 'es'):
            parser = ReadingPage()
            parser.feed((R / 'dist' / lang / 'index.html').read_text(encoding='utf-8'))
            self.assertEqual(parser.catalog, [f'/{lang}/{slug}/' for slug in expected])

    def test_reading_surface_has_localized_status_and_folded_evidence(self):
        passages = read('data/editorial.json')['passages']
        for lang, label in [('ko', '현재 최선의 채택 번역'), ('en', 'Current best selected translation'), ('es', 'Mejor traducción actual seleccionada')]:
            for passage in passages:
                html = (R / 'dist' / lang / passage['slug'] / 'index.html').read_text(encoding='utf-8')
                parser = ReadingPage()
                parser.feed(html)
                visible = '\n'.join(parser.visible)
                self.assertEqual(visible.count(label), 1)
                for internal in ('agy', 'Claude Code', 'Swete1901', 'WLC 잠정 저본', 'Current best selected —'):
                    self.assertNotIn(internal, visible)
                self.assertEqual(html.count('class="model-review"'), len(passage['verses']))
                self.assertNotIn('<details open', html)
                if lang == 'ko':
                    for verse in passage['verses']:
                        self.assertIn(verse['ko'], visible)

    def test_korean_name_changes_exactly_33_verses_and_keeps_other_languages(self):
        old = {r['id']: r for r in read('data/releases/v0.4.19.json')['records']}
        current = read('dist/data/releases/v0.4.20.json')['records']
        changed = []
        for record in current:
            previous = old[record['id']]['translations']
            self.assertEqual(record['translations']['en'], previous['en'])
            self.assertEqual(record['translations']['es'], previous['es'])
            self.assertEqual(record['hebrew_layer'], old[record['id']]['hebrew_layer'])
            expected = previous['ko'].replace('YHWH', '여호와').replace('야훼', '여호와').replace('야웨', '여호와')
            self.assertEqual(record['translations']['ko'], expected)
            if expected != previous['ko']:
                changed.append(record['id'])
        self.assertEqual(len(changed), 33)

    def test_previous_model_proposals_and_final_opinions_are_preserved(self):
        old = {r['id']: r for r in read('data/releases/v0.4.19.json')['records']}
        for record in read('dist/data/releases/v0.4.20.json')['records']:
            for field in ('model_proposals', 'model_final_opinions', 'model_opinion_history'):
                self.assertEqual(record['decision_trace'][field], old[record['id']]['decision_trace'][field])

    def test_only_different_selection_version_gets_per_verse_label(self):
        version = read('config.json')['version']
        trace = next(iter(review_layers.load(version)['records'].values()))
        self.assertNotIn('class="selection-label"', review_layers.render(trace, 'ko', version))
        self.assertIn('class="selection-label"', review_layers.render(trace, 'ko', '0.0.0'))


if __name__ == '__main__':
    unittest.main()
