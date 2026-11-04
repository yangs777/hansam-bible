"""Leftover gate: spend only weekly quota that expires unused; 5h window is a rate limiter."""
import datetime as dt
import json
import pathlib
import unittest
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

    def test_start_of_week_is_idle_even_with_lots_left(self):
        self.assertFalse(self.go(self.snap(5, 166)))

    def test_expiring_leftover_near_reset_runs_without_35_percent_floor(self):
        self.assertTrue(self.go(self.snap(60, 3)))   # 40 left, 30 spendable
        self.assertTrue(self.go(self.snap(85, 3)))   # 15 left, 5 spendable

    def test_owner_reserve_and_batch_cost(self):
        self.assertFalse(self.go(self.snap(86, 3)))

    def test_primary_window_only_rate_limits(self):
        self.assertFalse(self.go(self.snap(60, 3, primary_used=95)))
        self.assertTrue(self.go(self.snap(60, 3, primary_used=95, primary_hours=-0.1)))  # already reset

    def test_owner_activity_and_cooldown(self):
        self.assertFalse(self.go(self.snap(60, 3), owner=5))
        recent = {'last_launch': {'started_at': (self.now-dt.timedelta(minutes=20)).isoformat(), 'pid': None}}
        self.assertFalse(self.go(self.snap(60, 3), state=recent))

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
