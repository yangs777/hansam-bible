"""Fail-closed budget checks and conservative reservation; no live API requests."""
import copy,datetime as dt,json,pathlib,tempfile,unittest
from unittest.mock import patch
from cloud_worker import guard,reserve_cost,run,UTC
class CreditTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((pathlib.Path(__file__).resolve().parents[1]/'automation/credit-policy.json').read_text())
        self.now=dt.datetime(2026,10,23,tzinfo=UTC)
    def ready(self):
        p=copy.deepcopy(self.p);p.update(enabled=True,balance_verified_at=self.now.isoformat(),credit_expires_at=(self.now+dt.timedelta(days=7)).isoformat(),verified_remaining_usd=150,project_cap_usd=140,credit_isolated_from_paid_balance=True);return p
    def test_unverified_default_never_calls(self):self.assertIsNotNone(guard(self.p,self.now,True))
    def test_secret_is_required(self):self.assertIsNotNone(guard(self.ready(),self.now,False))
    def test_verified_policy_ready(self):self.assertIsNone(guard(self.ready(),self.now,True))
    def test_expired_stale_and_paid_balance_stop(self):
        for update in [{'credit_expires_at':self.now.isoformat()},{'balance_verified_at':(self.now-dt.timedelta(days=2)).isoformat()},{'credit_isolated_from_paid_balance':False},{'project_cap_usd':151}]:
            p=self.ready();p.update(update);self.assertIsNotNone(guard(p,self.now,True))
    def test_reservation_bounds_maximum_output(self):
        p=self.ready();self.assertGreater(reserve_cost('אבג'*200,p),p['max_output_tokens']*15/1000000)
    def test_ledger_push_failure_prevents_api_request(self):
        p=self.ready();now=dt.datetime.now(UTC);p['balance_verified_at']=now.isoformat();p['credit_expires_at']=(now+dt.timedelta(days=7)).isoformat()
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{'ANTHROPIC_API_KEY':'test-only'}),patch('cloud_worker.persist',side_effect=RuntimeError('push failed')),patch('cloud_worker.urllib.request.urlopen') as request:
            with self.assertRaisesRegex(RuntimeError,'push failed'):run(p,pathlib.Path(folder),True,True)
            request.assert_not_called()
if __name__=='__main__':unittest.main()
