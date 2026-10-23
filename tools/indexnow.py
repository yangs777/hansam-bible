"""Submit canonical project URLs only after public key verification; receipt is not indexing."""
import argparse,hashlib,json,pathlib,urllib.parse,urllib.request,xml.etree.ElementTree as ET
R=pathlib.Path(__file__).resolve().parents[1]
def submit(execute=False):
    c=json.loads((R/'config.json').read_text(encoding='utf-8'));origin=c['origin'];key=json.loads((R/'automation/indexnow.json').read_text())['key']
    urls=[x.text for x in ET.parse(R/'dist/sitemap.xml').getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    if any(not u.startswith(origin+'/') for u in urls):raise ValueError('URL outside project origin')
    key_url=origin+'/'+key+'.txt';payload={'host':urllib.parse.urlparse(origin).hostname,'key':key,'keyLocation':key_url,'urlList':urls}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();record=R/'private/indexnow-receipt.json'
    if not execute:return {'status':'dry_run','url_count':len(urls),'keyLocation':key_url}
    if record.exists() and json.loads(record.read_text())['payload_sha256']==digest:return {'status':'unchanged_not_resubmitted','url_count':len(urls)}
    with urllib.request.urlopen(key_url,timeout=30) as response:
        if response.read().decode().strip()!=key:raise ValueError('Public key file mismatch')
    request=urllib.request.Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json; charset=utf-8'})
    with urllib.request.urlopen(request,timeout=45) as response:status=response.status
    result={'http_status':status,'url_count':len(urls),'payload_sha256':digest,'meaning':'Submission received or pending key verification; no indexing/ranking guarantee'}
    record.parent.mkdir(exist_ok=True);record.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');a=p.parse_args();print(json.dumps(submit(a.submit)))
