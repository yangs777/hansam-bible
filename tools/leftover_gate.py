"""Model-free gate: reserve one daily Bible batch using reset_planner.

Rule (owner, 2026-11-07):
- Divide discretionary weekly quota over remaining days, minimum 15-point reserve.
- Retain the 5-hour reserve and fixed safety margins, including for small batches.
- Skip if the owner is actively using Codex (non-Bible weekly rise in the last hour).
- Shared daily ledger and OS lock prevent duplicate spending by timer entry points.

Usage source: `codex app-server` RPC `account/rateLimits/read` (no model call),
falling back to the newest `rate_limits` event in ~/.codex/sessions rollouts.

  python tools/leftover_gate.py            # decide; on GO run one batch via codex exec
  python tools/leftover_gate.py --dry-run  # decide only
  python tools/leftover_gate.py --dry-run --simulate weekly_used=60,weekly_reset_hours=3
"""
import argparse
import contextlib
import ctypes
import datetime as dt
import glob
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
from reset_planner import plan, DAILY_LEDGER, reserve_daily_budget

R = pathlib.Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
CODEX_HOME = pathlib.Path(os.environ.get('CODEX_HOME', pathlib.Path.home() / '.codex'))
STATE = R / 'private/leftover-gate-state.json'
LOG = R / 'private/leftover-gate.log'
BATCH_DIR = R / 'private/leftover-batches'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def codex_exe():
    found = sorted(glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe')), key=os.path.getmtime)
    if found:
        return found[-1]
    return 'codex'


def live_rate_limits(timeout=45):
    """Read account rate limits through the local app-server. No model turn is created."""
    proc = subprocess.Popen([codex_exe(), 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding='utf-8', creationflags=NO_WINDOW)
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(x) for x in proc.stdout], daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + '\n'); proc.stdin.flush()

    def wait(ident):
        deadline = dt.datetime.now() + dt.timedelta(seconds=timeout)
        while dt.datetime.now() < deadline:
            try:
                msg = json.loads(lines.get(timeout=max(0.1, (deadline - dt.datetime.now()).total_seconds())))
            except (queue.Empty, ValueError):
                continue
            if msg.get('id') == ident:
                if 'error' in msg:
                    raise RuntimeError('app-server error: ' + json.dumps(msg['error'])[:300])
                return msg['result']
        raise TimeoutError('app-server did not answer')
    try:
        send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'bible-leftover-gate', 'version': '1'}}})
        wait(1)
        send({'jsonrpc': '2.0', 'method': 'initialized'})
        send({'jsonrpc': '2.0', 'id': 2, 'method': 'account/rateLimits/read'})
        raw = wait(2)
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        proc.terminate()
    bucket = (raw.get('rateLimitsByLimitId') or {}).get('codex') or raw.get('rateLimits') or {}
    return normalize(bucket.get('primary'), bucket.get('secondary'), dt.datetime.now(UTC), 'app-server account/rateLimits/read',
                     allowed=raw.get('ordinaryUsageAllowed') is True and not bucket.get('spendControlReached') and not bucket.get('rateLimitReachedType'))


def normalize(primary, secondary, observed_at, source, allowed=True):
    def window(w, mins, key_used, key_mins, key_reset):
        if not w or w.get(key_mins) != mins:
            raise ValueError('unexpected window shape for %s-minute window' % mins)
        used = w.get(key_used)
        if not isinstance(used, (int, float)) or isinstance(used, bool) or not 0 <= used <= 100:
            raise ValueError('missing used percent')
        return {'used': float(used), 'resets_at': dt.datetime.fromtimestamp(w[key_reset], UTC)}
    camel = primary and 'usedPercent' in primary
    keys = ('usedPercent', 'windowDurationMins', 'resetsAt') if camel else ('used_percent', 'window_minutes', 'resets_at')
    return {'observed_at': observed_at, 'source': source, 'allowed': allowed,
            'primary': window(primary, 300, *keys), 'weekly': window(secondary, 10080, *keys)}


def _tail_lines(path, max_bytes):
    size = path.stat().st_size
    with open(path, 'rb') as fh:
        fh.seek(max(0, size - max_bytes))
        data = fh.read()
    lines = data.split(b'\n')
    if size > max_bytes:
        lines = lines[1:]
    return lines


def _session_cwd(path):
    try:
        with open(path, 'rb') as fh:
            first = json.loads(fh.readline())
        return (first.get('payload') or {}).get('cwd') or ''
    except (OSError, ValueError):
        return ''


def rollout_events(now, lookback_minutes, sessions=None, max_bytes=8_000_000):
    """(time, thread_id, cwd, primary, secondary) for recent rate_limits events across rollouts."""
    sessions = pathlib.Path(sessions or CODEX_HOME / 'sessions')
    cutoff = now - dt.timedelta(minutes=lookback_minutes)
    events = []
    for path in sessions.rglob('rollout-*.jsonl'):
        try:
            if dt.datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff:
                continue
        except OSError:
            continue
        thread = path.stem[-36:]
        cwd = _session_cwd(path)
        for line in _tail_lines(path, max_bytes):
            if b'"rate_limits"' not in line:
                continue
            try:
                obj = json.loads(line)
                ts = dt.datetime.fromisoformat(obj['timestamp'].replace('Z', '+00:00'))
                rl = obj['payload']['rate_limits']
            except (ValueError, KeyError, TypeError):
                continue
            if ts < cutoff or not rl or rl.get('limit_id') not in (None, 'codex'):
                continue
            events.append({'time': ts, 'thread': thread, 'cwd': cwd, 'primary': rl.get('primary'), 'secondary': rl.get('secondary')})
    events.sort(key=lambda e: e['time'])
    return events


def is_bible(event, cfg):
    return event['thread'] in cfg['bible_thread_ids'] or cfg['bible_cwd_marker'].lower() in (event['cwd'] or '').lower()


def owner_activity(events, weekly_reset, now, cfg):
    """Weekly points first reported by non-Bible threads in the lookback window (approximate attribution)."""
    window_start = now - dt.timedelta(minutes=cfg['owner_activity_lookback_minutes'])
    peak, other, bible = None, 0.0, 0.0
    for e in events:
        s = e['secondary'] or {}
        if s.get('window_minutes') != 10080 or abs(s.get('resets_at', 0) - weekly_reset.timestamp()) > 120:
            continue
        used = float(s.get('used_percent', 0))
        if peak is not None and used > peak and e['time'] >= window_start:
            if is_bible(e, cfg):
                bible += used - peak
            else:
                other += used - peak
        peak = used if peak is None else max(peak, used)
    return {'non_bible_weekly_points': round(other, 1), 'bible_weekly_points': round(bible, 1)}


def rollout_snapshot(events, now, cfg):
    for e in reversed(events):
        if (now - e['time']).total_seconds() <= cfg['rollout_snapshot_max_age_minutes'] * 60:
            return normalize(e['primary'], e['secondary'], e['time'], 'rollout rate_limits (%s)' % e['thread'])
    raise RuntimeError('no rollout rate_limits within %s minutes' % cfg['rollout_snapshot_max_age_minutes'])


def pid_alive(pid):
    if not pid:
        return False
    if os.name == 'nt':
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def decide(snap, activity, state, cfg, now, ledger=None, policy=None):
    """Pure decision. Returns dict with go (bool), reasons and the numbers used."""
    wk, pr = snap['weekly'], snap['primary']
    weekly_hours = (wk['resets_at'] - now).total_seconds() / 3600
    primary_used = pr['used']
    weekly_remaining = 100 - wk['used']
    leftover = weekly_remaining - cfg['weekly_owner_reserve_points']
    numbers = {
        'snapshot_source': snap['source'],
        'snapshot_age_min': round((now - snap['observed_at']).total_seconds() / 60, 1),
        'weekly_used': wk['used'], 'weekly_remaining': weekly_remaining,
        'weekly_resets_at_kst': wk['resets_at'].astimezone(dt.timezone(dt.timedelta(hours=9))).strftime('%m-%d %H:%M'),
        'hours_to_weekly_reset': round(weekly_hours, 2),
        'owner_reserve': cfg['weekly_owner_reserve_points'],
        'spendable_leftover': leftover, 'weekly_batch_cost': cfg['weekly_batch_cost_points'],
        'primary_used': primary_used, 'primary_remaining': 100 - primary_used,
        'primary_batch_cost': cfg['primary_batch_cost_points'],
        'hours_to_primary_reset': round(max(0.0, (pr['resets_at'] - now).total_seconds() / 3600), 2),
        'non_bible_weekly_points_last_hour': activity['non_bible_weekly_points'],
    }
    policy = policy or json.loads((R/'automation/local-policy.json').read_text(encoding='utf-8'))
    # Both entry points use exactly the same allocation and reserve rules.
    current = {'checked_at': snap['observed_at'].isoformat(), 'account_key': 'local-profile',
               'pool': 'codex', 'ordinary_usage_allowed': snap['allowed'], 'banked': []}
    for name in ('primary', 'weekly'):
        current[name] = {'used_percent': snap[name]['used'], 'remaining_percent': 100-snap[name]['used'],
                         'resets_at': snap[name]['resets_at'].isoformat()}
    decision = plan(current, None, policy, [], now, ledger)
    numbers.update(daily_budget=decision.get('daily_budget'), batch_verses=decision['batch_verses'],
                   estimated_usage_points=decision.get('estimated_usage_points'))
    numbers['owner_reserve'] = (decision.get('daily_budget') or {}).get('reserve_points', max(15, policy['weekly_reserve_percent']))
    numbers['spendable_leftover'] = weekly_remaining-numbers['owner_reserve']
    reasons = [] if decision['start_batch'] else list(decision['reasons'])
    if not cfg.get('enabled'):
        reasons.append('gate disabled in automation/leftover-gate.json')
    if not snap['allowed']:
        reasons.append('ordinary usage not allowed / limit reached')
    if activity['non_bible_weekly_points'] > cfg['owner_activity_max_weekly_points']:
        reasons.append('owner active: non-Bible weekly +%.1f in last %s min' % (activity['non_bible_weekly_points'], cfg['owner_activity_lookback_minutes']))
    last = state.get('last_launch') or {}
    if last.get('pid') and pid_alive(last['pid']):
        reasons.append('previous batch still running (pid %s)' % last['pid'])
    if last.get('started_at'):
        since = (now - dt.datetime.fromisoformat(last['started_at'])).total_seconds() / 60
        if since < cfg['min_minutes_between_batches']:
            reasons.append('last batch started %.0f min ago (< %s)' % (since, cfg['min_minutes_between_batches']))
    return {'checked_at': now.isoformat(), 'go': not reasons, 'reasons': reasons or decision['reasons'], 'numbers': numbers}


def apply_simulation(snap, activity, spec, now):
    snap = json.loads(json.dumps(snap, default=str))
    snap['observed_at'] = now
    snap['weekly']['resets_at'] = dt.datetime.fromisoformat(snap['weekly']['resets_at'])
    snap['primary']['resets_at'] = dt.datetime.fromisoformat(snap['primary']['resets_at'])
    snap['source'] += ' + SIMULATED'
    activity = dict(activity)
    for item in filter(None, spec.split(',')):
        key, value = item.split('=')
        value = float(value)
        if key == 'weekly_used': snap['weekly']['used'] = value
        elif key == 'weekly_reset_hours': snap['weekly']['resets_at'] = now + dt.timedelta(hours=value)
        elif key == 'primary_used': snap['primary']['used'] = value
        elif key == 'primary_reset_hours': snap['primary']['resets_at'] = now + dt.timedelta(hours=value)
        elif key == 'owner_points': activity['non_bible_weekly_points'] = value
        else: raise SystemExit('unknown simulate key: ' + key)
    return snap, activity


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def launch(decision, cfg, state, now):
    """Run one batch in a fresh small `codex exec` thread and wait for it (bounded)."""
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    prompt = (R / cfg['launch']['prompt_file']).read_text(encoding='utf-8').replace(
        '{DECISION}', json.dumps(decision['numbers'], ensure_ascii=False))
    cmd = [codex_exe(), 'exec', '-C', str(R), '-m', cfg['launch']['model'],
           '-c', 'model_reasoning_effort="%s"' % cfg['launch']['reasoning_effort'],
           '--json', '-o', str(BATCH_DIR / (stamp + '.last.txt')), '-']
    with open(BATCH_DIR / (stamp + '.events.jsonl'), 'w', encoding='utf-8') as out:
        proc = subprocess.Popen(cmd, cwd=str(R), stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', creationflags=NO_WINDOW)
        state['last_launch'] = {'started_at': now.isoformat(), 'pid': proc.pid, 'stamp': stamp, 'decision': decision['numbers']}
        save_json(STATE, state)
        proc.stdin.write(prompt); proc.stdin.close()
        try:
            code = proc.wait(timeout=cfg['max_batch_runtime_minutes'] * 60)
        except subprocess.TimeoutExpired:
            proc.kill(); code = 'killed_after_timeout'
    state['last_launch'].update(pid=None, finished_at=dt.datetime.now(UTC).isoformat(), exit=code)
    save_json(STATE, state)
    return code


def run():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true', help='decide only; never start a batch')
    ap.add_argument('--simulate', default='', help='override numbers, e.g. weekly_used=60,weekly_reset_hours=3,primary_used=95,owner_points=5 (implies --dry-run)')
    ap.add_argument('--no-live', action='store_true', help='skip app-server read; use rollout snapshot only')
    ap.add_argument('--reserve-only', action='store_true', help='reserve the one allowed batch for work in the current session; never launch another agent')
    args = ap.parse_args()
    cfg = load_json(R / 'automation/leftover-gate.json', None)
    if cfg is None:
        raise SystemExit('missing automation/leftover-gate.json')
    now = dt.datetime.now(UTC)
    state = load_json(STATE, {})
    # A damaged ledger must stop work, never silently replenish an allowance.
    ledger = json.loads(DAILY_LEDGER.read_text(encoding='utf-8')) if DAILY_LEDGER.exists() else {}
    events = rollout_events(now, cfg['owner_activity_lookback_minutes'] + 60)
    snap, err = None, None
    if not args.no_live:
        try:
            snap = live_rate_limits()
        except Exception as exc:  # fall back to rollouts
            err = '%s: %s' % (type(exc).__name__, exc)
    # The live read stamps its response on completion. Compare against a later
    # clock reading, including when a slow failed read falls back to rollouts.
    now = dt.datetime.now(UTC)
    if snap is None:
        try:
            snap = rollout_snapshot(events, now, cfg)
        except RuntimeError as exc:
            decision = {'checked_at': now.isoformat(), 'go': False, 'reasons': ['no fresh usage data: %s; live read: %s' % (exc, err)], 'numbers': {}}
            print(json.dumps(decision, ensure_ascii=False, indent=2)); _log(decision, args); return
    activity = owner_activity(events, snap['weekly']['resets_at'], now, cfg)
    if args.simulate:
        snap, activity = apply_simulation(snap, activity, args.simulate, now)
        args.dry_run = True
    decision = decide(snap, activity, state, cfg, now, ledger)
    decision['dry_run'] = args.dry_run
    if err:
        decision['live_read_error'] = err
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    _log(decision, args)
    if decision['go'] and not args.dry_run:
        budget = decision['numbers']['daily_budget']
        charge = decision['numbers']['estimated_usage_points']['weekly']
        save_json(DAILY_LEDGER, reserve_daily_budget(ledger, budget, charge))
        if args.reserve_only:
            state['last_launch'] = {'started_at': now.isoformat(), 'pid': None,
                                    'mode': 'current_session', 'decision': decision['numbers']}
            save_json(STATE, state)
        else:
            code = launch(decision, cfg, state, now)
            _log({'checked_at': dt.datetime.now(UTC).isoformat(), 'batch_exit': code}, args)


@contextlib.contextmanager
def gate_lock():
    """OS lock shared by hourly and legacy timer entry points; crash releases it."""
    path = R/'private/daily-translation-gate.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+b') as fh:
        if fh.tell() == 0:
            fh.write(b'0'); fh.flush()
        fh.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fh.seek(0)
            if os.name == 'nt':
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def main():
    try:
        with gate_lock():
            run()
    except (OSError, ValueError) as exc:
        print(json.dumps({'go': False, 'reasons': ['Gate lock/state unavailable: '+str(exc)]}))
        raise SystemExit(1)


def _log(entry, args):
    if args.simulate:
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
