"""Verify photograph scope and provenance boundaries for the published corpus."""
import hashlib
import json
import unittest
from pathlib import Path
import chapter_sources

R = Path(__file__).resolve().parents[1]


class ChapterSourceTests(unittest.TestCase):
    def test_every_published_verse_has_an_indexed_photo_without_claiming_future_verses(self):
        data = chapter_sources.load()
        expected = {v['source'] for p in json.loads((R/'data/editorial.json').read_text(encoding='utf-8'))['passages'] for v in p['verses']}
        actual = set()
        for c in data['chapters']:
            indexed = {n for p in c['photos'] for n in p['covered_verses']}
            self.assertEqual(indexed, set(c['published_verses']))
            actual.update(f'{c["key"]}.{n}' for n in indexed)
        self.assertEqual(actual, expected)
        index = chapter_sources.reader_index()
        self.assertNotIn('Gen.6', index)
        self.assertEqual(index['Gen.5']['published_verses'][-1], 25)
        first = next(c for c in data['chapters'] if c['key']=='Gen.1')
        self.assertEqual([p['folio'] for p in first['photos']], ['001b','002a'])
        self.assertIn(26, first['photos'][0]['covered_verses'])
        self.assertIn(26, first['photos'][1]['covered_verses'])

    def test_photographs_have_original_links_rights_and_matching_local_bytes(self):
        for c in chapter_sources.load()['chapters']:
            for p in c['photos']:
                self.assertTrue(p['original_url'].startswith('https://manuscripts.sefaria.org/'))
                self.assertTrue(p['commons_page'].startswith('https://commons.wikimedia.org/wiki/File:'))
                self.assertTrue(p['mapping_source'].startswith('https://www.sefaria.org/api/manuscripts/'))
                self.assertIn('Public Domain', p['rights'])
                self.assertEqual(hashlib.sha256((R/p['preview'].lstrip('/')).read_bytes()).hexdigest(),p['preview_sha256'])
        self.assertEqual(chapter_sources.verse_ranges([1,2,3,5,7,8]),'1–3, 5, 7–8')

    def test_deuteronomy_trace_never_passes_mt_off_as_the_selected_variant(self):
        page = (R/'dist/sources/deut-32/index.html').read_text(encoding='utf-8')
        self.assertIn('채택 번역의 하나님의 아들들 어구는 이 MT 대조문에 없으며', page)
        self.assertIn('직접 판독 미완료', page)
        self.assertIn('4Q37-1', page)
        for c in chapter_sources.load()['chapters']:
            page=(R/'dist'/chapter_sources.chapter_url(c).strip('/')/'index.html').read_text(encoding='utf-8')
            self.assertIn('id="basis"',page)
            self.assertIn('id="photos"',page)
            self.assertIn('id="history"',page)
            self.assertNotIn('<img ',page)
            self.assertIn(chapter_sources.photos_url(c),page)
            gallery=(R/'dist'/chapter_sources.photos_url(c).strip('/')/'index.html').read_text(encoding='utf-8')
            self.assertIn('<img ',gallery)
            self.assertIn('최초 번역 당시의 사진 직접 판독으로 소급하지 않습니다',gallery)
            self.assertNotIn('__VERSION__',page)
            self.assertNotIn('__VERSES__',page)

    def test_source_links_reject_executable_and_protocol_relative_urls(self):
        for bad in ('javascript:alert(1)','data:text/html,test','//attacker.example','file:///private'):
            with self.assertRaises(ValueError):chapter_sources.href(bad)


if __name__=='__main__':unittest.main()
