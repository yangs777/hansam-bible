"""Freeze separately licensed reading editions; never import into editorial decisions."""
import hashlib,json,pathlib,urllib.request
R=pathlib.Path(__file__).resolve().parents[1]
COMMIT='59b18c5af5845728c275d5b7178ad0d024172b1f'
CODES='Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'.split()
# Canonical book order, not a textual harmonization of verse boundaries.
KO='창세기 출애굽기 레위기 민수기 신명기 여호수아 사사기 룻기 사무엘상 사무엘하 열왕기상 열왕기하 역대상 역대하 에스라 느헤미야 에스더 욥기 시편 잠언 전도서 아가 이사야 예레미야 예레미야애가 에스겔 다니엘 호세아 요엘 아모스 오바댜 요나 미가 나훔 하박국 스바냐 학개 스가랴 말라기 마태복음 마가복음 누가복음 요한복음 사도행전 로마서 고린도전서 고린도후서 갈라디아서 에베소서 빌립보서 골로새서 데살로니가전서 데살로니가후서 디모데전서 디모데후서 디도서 빌레몬서 히브리서 야고보서 베드로전서 베드로후서 요한일서 요한이서 요한삼서 유다서 요한계시록'.split()
ABBR='창 출 레 민 신 수 삿 룻 삼상 삼하 왕상 왕하 대상 대하 스 느 에 욥 시 잠 전 아 사 렘 애 겔 단 호 욜 암 옵 욘 미 나 합 습 학 슥 말 마 막 눅 요 행 롬 고전 고후 갈 엡 빌 골 살전 살후 딤전 딤후 딛 몬 히 약 벧전 벧후 요일 요이 요삼 유 계'.split()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
def main():
    assert len(CODES)==len(KO)==len(ABBR)==66
    books=[];versions=[]
    for key,ident,label,lang in [('KorRV','krv','개역한글 · 공개 배포본','ko'),('ASV','asv','ASV 1901 · English','en'),('SpaRV','rv1909','Reina-Valera 1909 · Español','es')]:
        url=f'https://raw.githubusercontent.com/scrollmapper/bible_databases/{COMMIT}/formats/json/{key}.json'
        cache=R/'private/reader-sources'/f'{key}.json'
        raw=cache.read_bytes() if cache.exists() else urllib.request.urlopen(url,timeout=60).read()
        data=json.loads(raw);assert len(data['books'])==66
        count=0
        for i,b in enumerate(data['books']):
            chapters={}
            for c in b['chapters']:
                rows={str(v['verse']):v['text'] for v in c['verses']}
                assert len(rows)==len(c['verses'])
                assert all('<' not in t and '>' not in t for t in rows.values()),'Unexpected markup: require explicit handling'
                chapters[str(c['chapter'])]=rows;count+=len(rows)
            save(R/'library'/ident/f'{CODES[i]}.json',{'book':CODES[i],'chapters':chapters})
            if ident=='krv':books.append({'id':CODES[i],'name':KO[i],'english':b['name'],'abbr':ABBR[i],'testament':'OT' if i<39 else 'NT','chapters':{k:max(map(int,v)) for k,v in chapters.items()}})
        for i in range(66):
            for c in data['books'][i]['chapters']:
                number=str(c['chapter']);books[i]['chapters'][number]=max(books[i]['chapters'].get(number,0),max(v['verse'] for v in c['verses']))
        versions.append({'id':ident,'label':label,'lang':lang,'type':'library','upstream_title':data['translation'],'source_url':url,'source_commit':COMMIT,'source_sha256':hashlib.sha256(raw).hexdigest(),'rights':'Public Domain (as declared by this edition’s source)','rights_url':f'https://github.com/scrollmapper/bible_databases/blob/{COMMIT}/sources/{"ko" if lang=="ko" else "en" if lang=="en" else "es"}/{key}/README.md','verse_count':count,'empty_verses':[f'{CODES[i]}.{c["chapter"]}.{v["verse"]}' for i,b in enumerate(data['books']) for c in b['chapters'] for v in c['verses'] if not v['text'].strip()],'scope':'66-book Protestant canon; source verse numbers retained; no textual modernization or manuscript verification'})
    save(R/'library/catalog.json',{'books':books,'versions':versions,'alignment':'Chapter and verse numbers only; numbering and textual bases can differ across editions.','korean_edition_note':'Upstream labels this KorRV: 개역성경. This digital distribution was not collated against a printed 1961 edition.','korean_rights_reference':'https://www.biblekorea.kr/bbs/content.php?co_id=subpage2_3_4_1'})
    print(json.dumps({v['id']:v['verse_count'] for v in versions}))
if __name__=='__main__':main()
