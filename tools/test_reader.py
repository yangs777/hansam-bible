"""Library preservation and copy/paste edge cases, without a browser dependency."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

R = pathlib.Path(__file__).resolve().parents[1]


class ReaderTests(unittest.TestCase):
    def test_complete_library_and_source_identity(self):
        catalog = json.loads((R / 'library/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog['books']), 66)
        self.assertEqual(len({b['id'] for b in catalog['books']}), 66)
        for version in catalog['versions']:
            count = 0
            empty = []
            for book in catalog['books']:
                document = json.loads((R / 'library' / version['id'] / (book['id'] + '.json')).read_text(encoding='utf-8'))
                self.assertEqual(document['book'], book['id'])
                for chapter, verses in document['chapters'].items():
                    count += len(verses)
                    self.assertLessEqual(max(map(int, verses)), book['chapters'][chapter])
                    empty.extend(f'{book["id"]}.{chapter}.{n}' for n, text in verses.items() if not text.strip())
            self.assertEqual(count, version['verse_count'])
            self.assertEqual(empty, version['empty_verses'])
            self.assertIn(version['source_commit'], version['source_url'])

    def test_published_original_matches_editorial_data(self):
        own = json.loads((R / 'dist/library/original.json').read_text(encoding='utf-8'))
        editorial = json.loads((R / 'data/editorial.json').read_text(encoding='utf-8'))
        hebrew = json.loads((R / 'data/hebrew.json').read_text(encoding='utf-8'))
        count = 0
        for p in editorial['passages']:
            for v in p['verses']:
                book, chapter, number = v['source'].split('.')
                row = own['records'][book][chapter][number]
                for lang in ('ko', 'en', 'es'):
                    self.assertEqual(row[lang], v[lang])
                self.assertEqual(row['he'], hebrew[v['source']]['hebrew'])
                count += 1
        self.assertEqual(sum(len(v) for b in own['records'].values() for v in b.values()), count)

    def test_published_library_checksums(self):
        for line in (R / 'dist/library/checksums.sha256').read_text().splitlines():
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256((R / 'dist' / name).read_bytes()).hexdigest(), digest)
        self.assertFalse((R / 'dist/data/krv').exists())

    def test_no_transformation_of_downloaded_source_when_cached(self):
        catalog = json.loads((R / 'library/catalog.json').read_text(encoding='utf-8'))
        for v, key in zip(catalog['versions'], ('KorRV', 'ASV', 'SpaRV')):
            cached = R / 'private/reader-sources' / (key + '.json')
            if not cached.exists():
                continue
            raw = cached.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), v['source_sha256'])
            for book, src in zip(catalog['books'], json.loads(raw)['books']):
                actual = json.loads((R / 'library' / v['id'] / (book['id'] + '.json')).read_text(encoding='utf-8'))
                self.assertEqual(actual['chapters'], {str(c['chapter']): {str(x['verse']): x['text'] for x in c['verses']} for c in src['chapters']})

    @unittest.skipUnless(shutil.which('node'), 'Node.js not installed')
    def test_copy_formats_and_paste_validation(self):
        script = '''import {parsePasted,formatRows,safeHTTP} from './reader.mjs';
import assert from 'node:assert/strict';
assert.deepEqual(parsePasted('1 First\\ncontinued\\n[3] Third',1,31),{'1':'First continued','3':'Third'});
assert.deepEqual(parsePasted('First\\nSecond',5,31),{'5':'First','6':'Second'});
assert.deepEqual(parsePasted('3)Third\\n[4]Fourth\\n5. Fifth',1,31),{'3':'Third','4':'Fourth','5':'Fifth'});
assert.equal(safeHTTP('ko/genesis-1/',new URL('https://example.org/hansam-bible/')).href,'https://example.org/hansam-bible/ko/genesis-1/');
for(const href of ['javascript:alert(1)','data:text/html,test','file:///private'])assert.throws(()=>safeHTTP(href));
for(const s of ['1 A\\n1 B','32 Outside','1 A\\n0 Wrong','Before\\n1 A',''])assert.throws(()=>parsePasted(s,1,31));
assert.throws(()=>parsePasted('A\\nB',31,31));
const cols=[{label:'Original'},{label:'Comparison'}];
const rows=[{number:1,cols,values:['Alpha','Beta']},{number:2,cols,values:[undefined,'']},{number:3,cols,values:['Gamma','Tab\\tline\\nbreak']}];
assert.equal(formatRows(rows,[0],'plain'),'Alpha\\nGamma');
assert.equal(formatRows(rows,[0],'numbered'),'1 Alpha\\n3 Gamma');
const tsv=formatRows(rows,[0,1],'tsv');
assert.equal(tsv.split('\\n').length,4);
assert.ok(tsv.includes('[미공개 / 미입력]\\t[배포본에 별도 본문 없음]'));
assert.ok(tsv.endsWith('Tab line break'));
assert.equal(formatRows([], [0], 'plain'),'');
console.log('copy/paste edge cases PASS');'''
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp)
            (folder / 'reader.mjs').write_bytes((R / 'tools/reader.js').read_bytes())
            (folder / 'test.mjs').write_text(script, encoding='utf-8')
            subprocess.run(['node', str(folder / 'test.mjs')], check=True, timeout=20)


if __name__ == '__main__':
    unittest.main()
