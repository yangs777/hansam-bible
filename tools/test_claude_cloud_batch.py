"""Native-cloud deadline and source exclusion checks; no paid model calls."""
import datetime as dt,json,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch
import claude_cloud_batch as batch
class NativeCloudTests(unittest.TestCase):
    def test_deadline_and_cash_guard(self):
        p={'enabled':True,'new_cash_budget_usd':0,'stop_new_translation_at':'2026-11-05T16:00:00+09:00'}
        self.assertTrue(batch.guard(p,dt.datetime.fromisoformat('2026-11-05T15:59:59+09:00')))
        self.assertFalse(batch.guard(p,dt.datetime.fromisoformat('2026-11-05T16:00:00+09:00')))
        p['new_cash_budget_usd']=1;self.assertFalse(batch.guard(p,dt.datetime.fromisoformat('2026-10-24T00:00:00+09:00')))
    def test_preparation_skips_adopted_and_claimed(self):
        with tempfile.TemporaryDirectory() as d:
            r=pathlib.Path(d);subprocess.run(['git','init','-q',str(r)],check=True)
            fixtures={'automation/claude-cloud-policy.json':{'enabled':True,'new_cash_budget_usd':0,'stop_new_translation_at':'2099-01-01T00:00:00+00:00','initial_verse_limit_per_run':100},'data/editorial.json':{'passages':[{'verses':[{'source':'Gen.2.1'}]}]},'automation/cloud-runs/old.json':{'verse_ids':['Gen.2.2']},'automation/cloud-queue.json':[{'source_url':'https://example.test/pinned','source_file_sha256':'test-hash','source_commit':'pinned','rights':{},'verses':[{'id':'Gen.2.'+str(n),'hebrew':'test'} for n in (1,2,3)]}]}
            for name,item in fixtures.items():
                p=r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(item),encoding='utf-8')
            with patch.object(batch,'R',r):result=batch.prepare(5)
            self.assertEqual(result['verse_count'],1);self.assertEqual(result['first_id'],'Gen.2.3')
            self.assertEqual(result['paid_api_calls'],0)
if __name__=='__main__':unittest.main()
