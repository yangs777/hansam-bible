"""Build useful Torah draft jobs from pinned WLC; unsupported variant markup is deferred."""
import argparse,hashlib,json,pathlib,urllib.request,xml.etree.ElementTree as ET
R=pathlib.Path(__file__).resolve().parents[1]
BOOKS=['Gen','Exod','Lev','Num','Deut','Josh','Judg','Ruth','1Sam','2Sam','1Kgs','2Kgs','1Chr','2Chr','Ezra','Neh','Esth','Job','Ps','Prov','Eccl','Song','Isa','Jer','Lam','Ezek','Dan','Hos','Joel','Amos','Obad','Jonah','Mic','Nah','Hab','Zeph','Hag','Zech','Mal']
def build(books):
    commit=json.loads((R/'config.json').read_text(encoding='utf-8'))['source_commit']
    cache=R/'private/upstream_cache';cache.mkdir(parents=True,exist_ok=True)
    jobs=[];deferred=[];counts={}
    published={v['source'] for p in json.loads((R/'data/editorial.json').read_text(encoding='utf-8'))['passages'] for v in p['verses']}
    for book in books:
        url=f'https://raw.githubusercontent.com/openscriptures/morphhb/{commit}/wlc/{book}.xml'
        f=cache/(commit+'-'+book+'.xml')
        if not f.exists():f.write_bytes(urllib.request.urlopen(url,timeout=45).read())
        raw=f.read_bytes();root=ET.fromstring(raw);groups={};counts[book]=0
        for verse in root.findall('.//{http://www.bibletechnologies.net/2003/OSIS/namespace}verse'):
            ref=verse.get('osisID');parts=[];tokens=[];unsupported=False
            if ref in published:continue
            for el in verse:
                tag=el.tag.rsplit('}',1)[-1]
                if tag=='w' and not list(el):
                    text=''.join(el.itertext()).replace('/','');parts.append(text)
                    tokens.append({'hebrew':text,'lemma':el.get('lemma'),'morph':el.get('morph')})
                elif tag=='seg':
                    if el.get('type') not in ('x-pe','x-samekh','x-reversednun'):parts.append(''.join(el.itertext()))
                elif tag=='note' and not list(el) and el.get('n') in ('c','p'):pass
                else:unsupported=True
            if unsupported or not tokens:deferred.append(ref);continue
            text=' '.join(parts).replace(' ־ ','־').replace(' ׃','׃')
            groups.setdefault('.'.join(ref.split('.')[:2]),[]).append({'id':ref,'hebrew':text,'tokens':tokens})
            counts[book]+=1
        for chapter,verses in groups.items():
            for start in range(0,len(verses),5):
                batch=verses[start:start+5]
                jobs.append({'id':chapter+'.batch'+str(start//5+1),'basis':'MT-WLC display; uncollated draft source','source_url':url,'source_file_sha256':hashlib.sha256(raw).hexdigest(),'source_commit':commit,'rights':{'text':'WLC public domain','morphology':'Open Scriptures Hebrew Bible CC BY 4.0','credit':'https://github.com/openscriptures/morphhb'},'verses':batch})
    dest=R/'automation';dest.mkdir(exist_ok=True)
    (dest/'cloud-queue.json').write_text(json.dumps(jobs,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    report={'eligible_verses':counts,'jobs':len(jobs),'deferred_unsupported_readings':deferred,'policy':'Deferred verses require explicit Qere/Ketiv/markup review before translation. No silent joining. No automatic final publication.'}
    (dest/'source-queue-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'eligible_verses':sum(counts.values()),'jobs':len(jobs),'deferred':len(deferred)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--books',nargs='+',choices=BOOKS,default=BOOKS[:5]);args=p.parse_args();build(args.books)
