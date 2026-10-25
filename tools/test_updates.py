"""Update history survives publication and distinguishes recorded from deployed state."""
import copy,json,pathlib,subprocess,tempfile,unittest,xml.etree.ElementTree as ET
from unittest.mock import patch
import update_log,updates

ROOT=pathlib.Path(__file__).resolve().parents[1]
class UpdateTests(unittest.TestCase):
    def entry(self):return {'id':'edition-1.0.0','kind':'edition','version':'1.0.0','recorded_at':'2026-10-25T20:00:00Z','time_basis':'edition_adopted_at','title_ko':'새 판본','summary_ko':['검토된 본문 추가'],'links':[]}
    def test_append_is_idempotent_but_corrections_need_new_ids(self):
        with tempfile.TemporaryDirectory() as t:
            e=self.entry();self.assertTrue(update_log.append_entry(t,e));self.assertFalse(update_log.append_entry(t,e))
            before=(pathlib.Path(t)/'data/updates.json').read_bytes();e['summary_ko']=['changed']
            with self.assertRaisesRegex(ValueError,'immutable'):update_log.append_entry(t,e)
            self.assertEqual(before,(pathlib.Path(t)/'data/updates.json').read_bytes())
    def test_timezone_required(self):
        with tempfile.TemporaryDirectory() as t:
            e=self.entry();e['recorded_at']='2026-10-25T12:00:00'
            with self.assertRaisesRegex(ValueError,'timezone'):update_log.append_entry(t,e)
    def test_html_rss_json_share_history_and_korean_time(self):
        with tempfile.TemporaryDirectory() as t:
            root=pathlib.Path(t);update_log.append_entry(root,self.entry());(root/'tools').mkdir();(root/'tools/updates.js').write_text('',encoding='utf-8');pages=[];files={}
            with patch.object(updates,'R',root):updates.build(lambda *a,**k:pages.append((a,k)),lambda p,s:files.__setitem__(p,s),{'version':'1.0.0','repository':'https://github.com/yangs777/hansam-bible','origin':'https://yangs777.github.io/hansam-bible'},[{'verses':[{}]}])
            self.assertIn('2026.10.26 05:00 KST',pages[0][0][2]);self.assertIn('판본 채택',pages[0][0][2])
            self.assertEqual(json.loads(files['updates/feed.json'])['entries'][0],self.entry())
            self.assertIn('edition-1.0.0',files['updates/feed.xml'])
            self.assertEqual(ET.fromstring(files['updates/feed.xml'].encode('utf-8')).findtext('channel/item/title'),'새 판본')
    def test_unlogged_edition_cannot_be_built(self):
        with tempfile.TemporaryDirectory() as t,patch.object(updates,'R',pathlib.Path(t)):
            with self.assertRaisesRegex(ValueError,'needs an update record'):updates.build(None,None,{'version':'1.0.0'},[])
    def test_public_status_success_failure_pending_and_network_fallback(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[2],'utf8');
async function run(run,error=false){
 const status={textContent:''},link={href:'original'};
 const context={document:{getElementById:id=>id==='deployment-status'?status:link},fetch:async()=>{if(error)throw Error();return {ok:true,json:async()=>({workflow_runs:[run]})}},AbortSignal,Intl,Date};
 await vm.runInNewContext(source,context);return {status:status.textContent,link:link.href};
}
(async()=>{
 const base={updated_at:'2026-10-25T20:00:00Z',html_url:'https://github.com/yangs777/hansam-bible/actions/runs/123'};
 let x=await run({...base,status:'completed',conclusion:'success'});assert(x.status.includes('성공'));assert(x.status.includes('26'));assert(x.link.endsWith('/123'));
 x=await run({...base,status:'completed',conclusion:'failure',html_url:'https://example.com/'});assert(x.status.includes('실패'));assert.equal(x.link,'original');
 x=await run({...base,status:'queued'});assert(x.status.includes('대기'));assert(!x.status.includes('성공'));
 x=await run(null,true);assert(x.status.includes('불러오지 못했습니다'));
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t)/'test.cjs';p.write_text(script,encoding='utf-8');subprocess.run(['node',str(p),str(ROOT/'tools/updates.js')],check=True,timeout=20)

if __name__=='__main__':unittest.main()
