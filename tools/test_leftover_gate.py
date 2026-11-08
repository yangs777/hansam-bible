"""Leftover gate: spend only weekly quota that expires unused; 5h window is a rate limiter."""
import datetime as dt
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from leftover_gate import UTC, decide, owner_activity

R = pathlib.Path(__file__).resolve().parents[1]


class LeftoverGateTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 11, 11, 20, tzinfo=UTC)
        self.cfg = json.loads((R/'automation/leftover-gate.json').read_text(encoding='utf-8'))
        self.cfg['enabled'] = True

    def snap(self, weekly_used, weekly_hours, primary_used=20, primary_hours=2):
        return {'observed_at': self.now, 'source': 'test', 'allowed': True,
                'weekly': {'used': weekly_used, 'resets_at': self.now+dt.timedelta(hours=weekly_hours)},
                'primary': {'used': primary_used, 'resets_at': self.now+dt.timedelta(hours=primary_hours)}}

    def go(self, snap, owner=0.0, state=None):
        return decide(snap, {'non_bible_weekly_points': owner}, state or {}, self.cfg, self.now)['go']

    def test_start_of_week_has_daily_budget(self):
        self.assertTrue(self.go(self.snap(5, 166)))

    def test_expiring_leftover_near_reset_runs_without_35_percent_floor(self):
        self.assertTrue(self.go(self.snap(60, 3)))   # 40 left, 30 spendable
        self.assertTrue(self.go(self.snap(82, 3)))   # 15 left, 5 spendable

    def test_owner_reserve_and_batch_cost(self):
        self.assertFalse(self.go(self.snap(86, 3)))

    def test_primary_window_only_rate_limits(self):
        self.assertFalse(self.go(self.snap(60, 3, primary_used=95)))
        self.assertFalse(self.go(self.snap(60, 3, primary_used=95, primary_hours=-0.1)))  # must re-read, never assume zero

    def test_owner_activity_and_cooldown(self):
        self.assertFalse(self.go(self.snap(60, 3), owner=5))
        recent = {'last_launch': {'started_at': (self.now-dt.timedelta(minutes=20)).isoformat(), 'pid': None}}
        self.assertFalse(self.go(self.snap(60, 3), state=recent))

    def test_stale_future_and_passed_week_never_run(self):
        for hours in (-1, 0):
            self.assertFalse(self.go(self.snap(60, hours)))
        snap = self.snap(60, 100)
        snap['observed_at'] -= dt.timedelta(minutes=16)
        self.assertFalse(self.go(snap))
        snap['observed_at'] = self.now+dt.timedelta(minutes=1)
        self.assertFalse(self.go(snap))

    def test_run_checks_time_after_live_response(self):
        import leftover_gate as gate
        snap = self.snap(60, 100)
        snap['observed_at'] = self.now+dt.timedelta(milliseconds=250)
        finished = self.now+dt.timedelta(milliseconds=251)
        with mock.patch.object(gate.dt, 'datetime', wraps=dt.datetime) as clock, \
             mock.patch.object(gate, 'load_json', side_effect=[self.cfg, {}]), \
             mock.patch.object(gate, 'DAILY_LEDGER') as ledger, \
             mock.patch.object(gate, 'rollout_events', return_value=[]), \
             mock.patch.object(gate, 'live_rate_limits', return_value=snap), \
             mock.patch.object(gate, '_log') as log, \
             mock.patch('sys.argv', ['leftover_gate.py', '--dry-run']), \
             mock.patch('builtins.print'):
            ledger.exists.return_value = False
            clock.now.side_effect = [self.now, finished]
            gate.run()
        decision = log.call_args.args[0]
        self.assertTrue(decision['go'], decision['reasons'])
        self.assertEqual(decision['checked_at'], finished.isoformat())
        self.assertEqual(decision['numbers']['snapshot_age_min'], 0.0)

    def test_slow_live_failure_does_not_rejuvenate_rollout(self):
        import leftover_gate as gate
        snap = self.snap(60, 100)
        with mock.patch.object(gate.dt, 'datetime', wraps=dt.datetime) as clock, \
             mock.patch.object(gate, 'load_json', side_effect=[self.cfg, {}]), \
             mock.patch.object(gate, 'DAILY_LEDGER') as ledger, \
             mock.patch.object(gate, 'rollout_events', return_value=[]), \
             mock.patch.object(gate, 'live_rate_limits', side_effect=TimeoutError), \
             mock.patch.object(gate, 'rollout_snapshot', return_value=snap), \
             mock.patch.object(gate, '_log') as log, \
             mock.patch('sys.argv', ['leftover_gate.py', '--dry-run']), \
             mock.patch('builtins.print'):
            ledger.exists.return_value = False
            clock.now.side_effect = [self.now, self.now+dt.timedelta(minutes=16)]
            gate.run()
        decision = log.call_args.args[0]
        self.assertFalse(decision['go'])
        self.assertIn('stale or from the future', ' '.join(decision['reasons']))

    def test_shared_ledger_stops_second_entry_point(self):
        from reset_planner import reserve_daily_budget
        snap = self.snap(70, 101)
        first = decide(snap, {'non_bible_weekly_points': 0}, {}, self.cfg, self.now)
        self.assertTrue(first['go'])
        self.assertEqual(first['numbers']['batch_verses'], 1)
        ledger = reserve_daily_budget({}, first['numbers']['daily_budget'], 3)
        second = decide(snap, {'non_bible_weekly_points': 0}, {}, self.cfg, self.now, ledger)
        self.assertFalse(second['go'])

    def test_process_lock_blocks_competing_timer_and_releases(self):
        import leftover_gate as gate
        original = gate.R
        with tempfile.TemporaryDirectory() as folder:
            gate.R = pathlib.Path(folder)
            command = [sys.executable, '-c',
                       "import sys,pathlib; sys.path.insert(0,sys.argv[1]); "
                       "import leftover_gate as g; g.R=pathlib.Path(sys.argv[2]); "
                       "\nwith g.gate_lock(): print('locked')", str(R/'tools'), folder]
            try:
                with gate.gate_lock():
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            finally:
                gate.R = original

    def test_owner_activity_attribution(self):
        reset = self.now+dt.timedelta(hours=3)
        def ev(minutes_ago, used, thread, cwd=''):
            return {'time': self.now-dt.timedelta(minutes=minutes_ago), 'thread': thread, 'cwd': cwd,
                    'secondary': {'window_minutes': 10080, 'used_percent': used, 'resets_at': reset.timestamp()}}
        events = [ev(90, 50, 'other'), ev(50, 52, 'other'), ev(30, 53, self.cfg['bible_thread_ids'][0]),
                  ev(10, 56, 'x', r'C:\Users\Com\Documents\ChatGPT\hansam-bible-pilot')]
        got = owner_activity(events, reset, self.now, self.cfg)
        self.assertEqual(got, {'non_bible_weekly_points': 2.0, 'bible_weekly_points': 4.0})


if __name__ == '__main__':
    unittest.main()
