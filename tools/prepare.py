"""Freeze selected WLC verses and OSHB analyses from a specific upstream commit."""
import hashlib, json, pathlib, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'private/upstream_cache'; CACHE.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
COMMIT=CFG['source_commit']
NS={'o':'http://www.bibletechnologies.net/2003/OSIS/namespace'}
SELECT={'Gen':{'Gen.1.'+str(i) for i in range(1,32)},'Ps':{'Ps.1.'+str(i) for i in range(1,7)},'Num':{'Num.6.'+str(i) for i in range(24,27)},'Deut':{'Deut.32.8'}}
previous=json.loads((ROOT/'data/hebrew.json').read_text(encoding='utf-8')) if (ROOT/'data/hebrew.json').exists() else {}
out={}
for book,ids in SELECT.items():
    url=f'https://raw.githubusercontent.com/openscriptures/morphhb/{COMMIT}/wlc/{book}.xml'
    cached=CACHE/(COMMIT+'-'+book+'.xml')
    if cached.exists(): raw=cached.read_bytes()
    else:
        try: raw=urllib.request.urlopen(url,timeout=40).read()
        except Exception as exc: raise RuntimeError(f'Could not retrieve pinned source {book}; existing data was not overwritten') from exc
        cached.write_bytes(raw)
    expected={v['source_file_sha256'] for v in previous.values() if v.get('source_url')==url}
    if expected and hashlib.sha256(raw).hexdigest() not in expected:
        raise ValueError(f'{book}: cached/downloaded XML hash differs from recorded pinned source')
    root=ET.fromstring(raw)
    for verse in root.findall('.//o:verse',NS):
        vid=verse.get('osisID')
        if vid not in ids: continue
        words=[]; pieces=[]; notes=[]
        for el in verse:
            tag=el.tag.rsplit('}',1)[-1]
            if tag=='w':
                if list(el): raise ValueError(f'{vid}: nested word markup needs explicit editorial handling; refusing to join readings')
                text=''.join(el.itertext()).replace('/','')
                words.append({'hebrew':text,'lemma':el.get('lemma'),'morph':el.get('morph'),'upstream_id':el.get('id')})
                pieces.append(text)
            elif tag=='seg' and el.get('type') not in ('x-pe','x-samekh','x-reversednun'):
                pieces.append(''.join(el.itertext()))
            elif tag=='note' and not list(el) and el.get('n') in ('c','p'):
                notes.append({'type':{'c':'upstream_accent_comparison','p':'upstream_punctuation_comparison'}[el.get('n')],'text':el.text or ''})
            elif tag!='seg':
                raise ValueError(f'{vid}: unsupported {tag} markup; review Qere/Ketiv and notes before extending the pilot')
        text=' '.join(pieces).replace(' ־ ','־').replace(' ׃','׃')
        out[vid]={'hebrew':text,'tokens':words,'source_notes':notes,'source_url':url,'source_file_sha256':hashlib.sha256(raw).hexdigest(),'source_commit':COMMIT,'source_reference':vid,'source_attribution':'Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb','rights':{'text':'Westminster Leningrad Codex — public domain','lemma_and_morphology':'Open Scriptures Hebrew Bible — CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/'},'display_transformation':'Removed OSHB morpheme separators; joined words and punctuation; kept vowel and accent codepoints. Plain upstream accent/punctuation comparison notes are preserved separately. Not a manuscript diplomatic transcription. Unsupported nested or variant markup causes a stop, not silent flattening.'}
(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data'/'hebrew.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v['hebrew'] for k,v in out.items()},ensure_ascii=False,indent=2))
