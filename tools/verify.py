"""Publication checks for provenance survival, Hebrew integrity and usable static routes."""
import hashlib, json, pathlib, re, urllib.parse, xml.etree.ElementTree as ET
from html.parser import HTMLParser
R=pathlib.Path(__file__).resolve().parents[1]; D=R/'dist'
C=json.loads((R/'config.json').read_text(encoding='utf-8'))
H=json.loads((R/'data/hebrew.json').read_text(encoding='utf-8'))
E=json.loads((R/'data/editorial.json').read_text(encoding='utf-8'))['passages']
records=[json.loads(s) for s in (D/'data/hansam-bible.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(records)==10 and len({r['id'] for r in records})==10
assert json.loads((D/'data/hansam-bible.json').read_text(encoding='utf-8'))['records']==records
for r in records:
    assert r['project_author']=='Hansam Yang' and r['translation_status']=='draft'
    assert r['human_specialist_review']=='pending'
    assert r['hebrew_layer']==H[r['reference']]
    assert r['rights']['hebrew_text']['status']=='public-domain'
    assert r['rights']['morphology']['credit']=='Open Scriptures Hebrew Bible'
    assert 'CC BY 4.0' in r['hebrew_layer']['rights']['lemma_and_morphology']
    assert r['hebrew_layer']['source_attribution'].startswith('Original work of the Open Scriptures')
    trace=r['decision_trace']; selection=trace['selection']
    assert r['selection_status']==selection['selection_status']=='current_best_provisional'
    assert selection['translations']==r['translations'] and selection['version']==C['version']
    assert r['title']=='원문성경 · Original Bible'
    assert {p['model'] for p in trace['model_proposals']} >= {'gpt-6.1-sol','gemini-3.8-flash-medium'}
    assert set(trace['model_final_opinions']) >= {'gpt-6.1-sol','gemini-3.8-flash-medium'}
    assert r['model_provenance']['gemini-3.8-flash-medium']['requested_model_id']=='gemini-3.8-flash-medium'
    assert trace['previous_editions'][0]['version']=='0.1.0'
    for lang in ('ko','en','es'):
        assert r['translations'][lang] and 'Hansam Yang' in r['citations'][lang]
        assert r['version'] in r['citations'][lang] and r['canonical_urls'][lang].startswith(C['origin'])
for p in E:
    for v in p['verses']: assert v['review_status']=='human_specialist_pending'
archived=json.loads((R/'data/releases/v0.1.0.json').read_text(encoding='utf-8'))
assert (D/'data/releases/v0.1.0.json').read_bytes()==(R/'data/releases/v0.1.0.json').read_bytes()
assert len(archived['records'])==10 and all(v['version']=='0.1.0' for v in archived['records'])
assert 'sons of Israel' in archived['records'][-1]['translations']['en']
assert 'sons of God' in records[-1]['translations']['en']
assert 'editorial reconstruction' in records[-1]['basis'].lower()
assert 'sons of Israel' in records[-1]['decision_trace']['selection']['mt_display_translation']['en']
assert json.loads((D/f'data/releases/v{C["version"]}.json').read_text(encoding='utf-8'))['records']==records
assert E[2]['variant']['not_a_complete_verse'] is True
assert E[2]['variant']['en']=='sons of God' and len(E[2]['readings'])==3
# Compare imported tokens to pinned XML when the local preparation cache is available.
checked_tokens=0
for f in (R/'private/upstream_cache').glob('*.xml'):
    raw=f.read_bytes(); root=ET.fromstring(raw)
    for v in root.findall('.//{http://www.bibletechnologies.net/2003/OSIS/namespace}verse'):
        ref=v.get('osisID')
        if ref not in H:continue
        assert hashlib.sha256(raw).hexdigest()==H[ref]['source_file_sha256']
        words=[w for w in v if w.tag.endswith('}w')]
        assert len(words)==len(H[ref]['tokens'])
        for original,saved in zip(words,H[ref]['tokens']):
            assert ''.join(original.itertext()).replace('/','')==saved['hebrew']
            assert original.get('morph')==saved['morph']
            checked_tokens+=1
class Parse(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.canon=[];self.ids=set();self.jsons=[];self.injson=False;self.js='';self.lang=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html':self.lang=a.get('lang')
        if a.get('id'):assert a['id'] not in self.ids;self.ids.add(a['id'])
        if tag in ('a','link') and a.get('href'):self.links.append(a['href'])
        if tag=='script' and a.get('src'):self.links.append(a['src'])
        if tag=='link' and a.get('rel')=='canonical':self.canon.append(a['href'])
        if tag=='script' and a.get('type')=='application/ld+json':self.injson=True;self.js=''
    def handle_data(self,data):
        if self.injson:self.js+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.injson:self.jsons.append(json.loads(self.js));self.injson=False
pages={}
for file in D.rglob('*.html'):
    parser=Parse();text=file.read_text(encoding='utf-8');parser.feed(text);pages[file.resolve()]=parser
    assert len(parser.canon)==1 and parser.canon[0].startswith(C['origin'])
    assert parser.lang in ('ko','en','es') and parser.jsons
    assert 'Hansam Yang' in text and any(s in text for s in ('draft','연구 초안','borrador')),str(file)
for file,p in pages.items():
    for link in p.links:
        u=urllib.parse.urlparse(link)
        if u.scheme or u.netloc:continue
        if not u.path:target=file
        else:target=(D/u.path.lstrip('/')).resolve() if u.path.startswith('/') else (file.parent/u.path).resolve()
        if target.is_dir():target=target/'index.html'
        assert target.exists(),f'Broken local URL: {file.name}: {link}'
        if u.fragment and target in pages:assert u.fragment in pages[target].ids,f'Missing anchor {link}'
for line in (D/'data/checksums.sha256').read_text().splitlines():
    digest,name=line.split('  ',1); assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
for lang in ('ko','en','es'):
    for p in E:
        f=D/lang/p['slug']/'index.html';assert f.resolve() in pages
        s=f.read_text(encoding='utf-8');assert s.count('class="verse"')==len(p['verses'])
        assert s.count('class="model-review"')==len(p['verses'])
        assert 'ORIGINAL BIBLE' in s and 'gemini-3.8-flash-medium' in s and 'gpt-6.1-sol' in s
        assert any(x in s for x in ('review pending','검수 전','pendiente de revisión'))
        for k in ('ko','en','es'):assert f'hreflang="{k}"' in s
assert len(pages)==17
ET.parse(D/'sitemap.xml')
print(json.dumps({'result':'PASS','html_pages':len(pages),'localized_passage_pages':9,'verse_records':10,'draft_translations':30,'upstream_tokens_compared':checked_tokens,'checks':['per-record provenance and rights','draft and review states','shared-data export equality','source Hebrew codepoint preservation when cache exists','local links and anchors','JSON-LD parsing','canonical/hreflang','SHA-256 manifest','XML sitemap']},ensure_ascii=False,indent=2))
