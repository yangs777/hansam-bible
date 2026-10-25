"""Read-only notice monitor and conservative, account-aware Bible work scheduler.

No redemption, account settings, paid calls, or translation execution lives here.
Unreviewed web text is evidence to inspect, never an executable instruction.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import statistics
import urllib.parse
import urllib.request
from html.parser import HTMLParser

R = pathlib.Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
OFFICIAL = {'help.openai.com', 'developers.openai.com', 'openai.com'}


def timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return dt.datetime.fromtimestamp(value, UTC)
    if not isinstance(value, str):
        raise TypeError('Missing timestamp')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('An exact timestamp must include a time zone')
    return parsed.astimezone(UTC)


def official(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.scheme == 'https' and parsed.hostname in OFFICIAL and not parsed.username and not parsed.password and parsed.port in (None, 443)
    except (ValueError, TypeError, AttributeError):
        return False


def unwrap(raw):
    if raw.get('isError'):
        raise ValueError('Usage tool reported an error')
    if 'content' in raw:
        raw = json.loads(next(x['text'] for x in raw['content'] if x.get('type') == 'text'))
    return raw


def snapshot(raw, checked_at):
    raw = unwrap(raw)
    bucket = raw.get('rateLimitsByLimitId', {}).get('codex') or raw.get('rateLimits')
    if not bucket or bucket.get('limitId') != 'codex':
        raise ValueError('Codex quota bucket is unavailable')
    result = {'checked_at': checked_at.isoformat(), 'account_key': hashlib.sha256(raw['accountId'].encode()).hexdigest(), 'pool': 'codex'}
    for source, target in [('primary', 'primary'), ('secondary', 'weekly')]:
        window = bucket.get(source)
        if not window:
            raise ValueError('Quota window is unavailable: ' + source)
        # get_usage_limits schema: primary=5h, secondary=7d on this Plus plan.
        # Stop rather than silently treating a different plan's window as weekly.
        if window.get('windowDurationMins') != (300 if source == 'primary' else 10080):
            raise ValueError('Unsupported quota window duration: ' + source)
        used = window.get('usedPercent')
        reset = window.get('resetsAt')
        if not isinstance(used, (int, float)) or isinstance(used, bool) or not math.isfinite(used) or not 0 <= used <= 100 or not isinstance(reset, (int, float)) or isinstance(reset, bool) or not math.isfinite(reset):
            raise ValueError('Missing or invalid live usage; never interpret null as zero')
        result[target] = {'used_percent': used, 'remaining_percent': 100-used, 'resets_at': timestamp(reset).isoformat()}
    result['ordinary_usage_allowed'] = raw.get('ordinaryUsageAllowed') is True and not bucket.get('spendControlReached') and not bucket.get('rateLimitReachedType')
    credits = raw.get('rateLimitResetCredits') or {}
    result['banked'] = []
    for credit in credits.get('credits') or []:
        if credit.get('status') != 'available' or not credit.get('id'):
            continue
        try:
            expiry = timestamp(credit['expiresAt']).isoformat()
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
        result['banked'].append({'id': credit['id'], 'type': credit.get('resetType'), 'expires_at': expiry})
    return result


def observed_changes(previous, current):
    if not previous or previous.get('account_key') != current['account_key'] or previous.get('pool') != current['pool']:
        return []
    changes = []
    for name in ('primary', 'weekly'):
        before, after = previous[name], current[name]
        moved = before['resets_at'] != after['resets_at']
        dropped = after['used_percent'] < before['used_percent']
        if moved or dropped:
            changes.append({'window': name, 'reset_time_changed': moved, 'usage_decreased': dropped,
                            'previous_reset': before['resets_at'], 'current_reset': after['resets_at'],
                            'attribution': 'Observed schedule/usage change only; does not establish a global reset or redemption.'})
    return changes


def cadence(events, now, minimum=6):
    """Separate grant types; tentative date forecasts may ONLY change monitoring."""
    reports = {}
    for kind in ('automatic_reset', 'banked_grant'):
        dated = set()
        for event in events:
            if event.get('verified') is not True or event.get('kind') != kind or not official(event.get('source_url', '')):
                continue
            try:
                date = dt.date.fromisoformat(event['event_date'])
                if date <= now.date(): dated.add(date)
            except (KeyError, ValueError, TypeError):
                continue
        dates = sorted(dated)
        intervals = [(b-a).days for a, b in zip(dates, dates[1:])]
        report = {'sample_count': len(dates), 'interval_days': intervals, 'reliable_prediction': False, 'next_date_advisory': None, 'assessment': 'insufficient_samples', 'date_precision': 'Source calendar day, possibly unknown timezone; no exact UTC effective time inferred.'}
        if len(dates) >= minimum:
            median = statistics.median(intervals)
            variation = statistics.pstdev(intervals) / statistics.mean(intervals)
            same_weekday = max(sum(d.weekday() == day for d in dates) for day in range(7)) / len(dates)
            report.update(median_interval_days=median, coefficient_of_variation=round(variation, 3), dominant_weekday_fraction=round(same_weekday, 3))
            report['assessment'] = 'irregular_intervals'
            if median >= 1 and variation <= .2:
                # A missed forecast is not rolled forward into invented future grants.
                candidate = dates[-1] + dt.timedelta(days=round(median))
                if candidate >= now.date():
                    report['next_date_advisory'] = candidate.isoformat()
                    report['assessment'] = 'Tentative regularity in a small observed sample; monitoring only, never a guaranteed grant.'
                else:
                    report['assessment'] = 'forecast_elapsed_without_confirmed_new_event'
        reports[kind] = report
    return reports


def plan(current, previous, policy, events, now):
    changes = observed_changes(previous, current)
    result = {'checked_at': now.isoformat(), 'start_batch': False, 'batch_verses': policy['batch_verses'],
              'max_batches': 1, 'redeem_reset': False, 'spend_cash': False, 'reasons': [], 'observed_changes': changes,
              'notice_candidates_cannot_authorize_work': True, 'banked_attention': [], 'cadence': cadence(events, now)}
    age = (now-timestamp(current['checked_at'])).total_seconds()
    if not 0 <= age <= 900:
        result['reasons'].append('Usage snapshot is stale or from the future; recheck live usage')
        return result
    for credit in current['banked']:
        hours = (timestamp(credit['expires_at'])-now).total_seconds()/3600
        if credit['type'] == 'codexRateLimits' and 0 < hours <= policy['reset_planner']['banked_expiry_attention_hours']:
            result['banked_attention'].append({'id': credit['id'], 'expires_at': credit['expires_at'],
                'action': 'Review free banked reset before expiry through official controls; do not redeem automatically or lower protected reserves.'})
    if not policy.get('enabled') or not policy['reset_planner'].get('enabled') or not current['ordinary_usage_allowed']:
        result['reasons'].append('Policy disabled or ordinary included usage unavailable')
        return result
    minutes = {}
    for window, reserve in [('primary', policy['primary_reserve_percent']), ('weekly', policy['weekly_reserve_percent'])]:
        minutes[window] = (timestamp(current[window]['resets_at'])-now).total_seconds()/60
        if minutes[window] <= 0:
            result['reasons'].append('Displayed reset passed; obtain a fresh live snapshot')
            return result
        # 20 primary / 5 weekly points based on prior pilot display deltas,
        # plus a 3/2 point margin. Shared-account deltas are not a guarantee.
        estimate = policy['reset_planner']['estimated_batch_usage_points'][window]
        margin = policy['reset_planner']['usage_safety_margin_points'][window]
        # All these quantities are percentage points of this quota window,
        # not tokens, dollars, or an independently convertible credit balance.
        if policy['reset_planner'].get('usage_unit') != 'percentage_points_of_window' or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or not 0 <= x <= 100 for x in (reserve, estimate, margin)):
            result['reasons'].append('Invalid reserve/estimate units or bounds')
            return result
        if current[window]['remaining_percent']-estimate-margin < reserve:
            result['reasons'].append(window + ' reserve cannot cover the estimated batch and safety margin')
            return result
    if minutes['primary'] <= policy['start_within_minutes_of_primary_reset'] or minutes['weekly'] <= policy['start_within_minutes_of_weekly_reset']:
        result['reasons'].append('Regular reset window')
    for event in events:
        # Human/agent review must establish exact time, window scope and this
        # account's eligibility. A publication date or a plan name is insufficient.
        if event.get('verified') is not True or event.get('applies_to_account') is not True or event.get('kind') != 'automatic_reset' or not official(event.get('source_url', '')) or event.get('pool') != 'codex':
            continue
        if not set(event.get('covers', [])) & {'primary', 'weekly'}:
            continue
        try:
            minutes_until = (timestamp(event['effective_at'])-now).total_seconds()/60
        except (KeyError, ValueError, TypeError):
            continue
        if 0 < minutes_until <= policy['reset_planner']['automatic_reset_lead_minutes']:
            result['reasons'].append('Verified upcoming automatic reset: '+event['id'])
    for credit in current['banked']:
        if credit['type'] != 'codexRateLimits':
            continue
        hours = (timestamp(credit['expires_at'])-now).total_seconds()/3600
        if 0 < hours <= policy['reset_planner']['banked_expiry_work_hours']:
            result['reasons'].append('Live banked-reset expiry window; included quota only: '+credit['id'])
    result['start_batch'] = bool(result['reasons'])
    if not result['reasons']:
        result['reasons'].append('No confirmed reset/expiry work window')
    result['minutes_until_live_resets'] = {k: round(v, 1) for k, v in minutes.items()}
    result['after_batch'] = 'Recheck actual shared usage; stop if a protected reserve is approached. Estimates are not hard provider-side caps.'
    return result


class NoticeText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.ignored += 1
        if tag in ('h1', 'h2', 'h3', 'p', 'li', 'time', 'br'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.ignored = max(0, self.ignored-1)
        if tag in ('h1', 'h2', 'h3', 'p', 'li', 'time'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def extract_candidates(document, url):
    if not official(url):
        raise ValueError('Only configured official HTTPS sources are allowed')
    parser = NoticeText(); parser.feed(document)
    text = ''.join(parser.parts)
    lines = [re.sub(r'^#{1,6}\s+', '', re.sub(r'\s+', ' ', s).strip()) for s in text.splitlines() if s.strip()]
    current_date = None; candidates = []
    for i, line in enumerate(lines):
        # Only explicit standalone publication-date headings. No relative dates,
        # time-zone guesses or effective-time inference from prose.
        for fmt in ('%B %d, %Y', '%Y-%m-%d'):
            try:
                current_date = dt.datetime.strptime(line, fmt).date().isoformat()
                break
            except ValueError:
                pass
        if not re.search(r'(?i)(?:\breset(?:s|ting)?\b|리셋|한도.{0,12}초기화)', line):
            continue
        excerpt = ' '.join(lines[max(0, i-1):i+2])[:650]
        identity = hashlib.sha256((url+'\n'+str(current_date)+'\n'+line).encode()).hexdigest()[:24]
        candidates.append({'id': identity, 'source_url': url, 'publication_date': current_date,
                           'date_basis': 'nearest_explicit_heading_unverified; not a confirmed publication or effective time',
                           'excerpt': excerpt, 'verified': False, 'effective_at': None,
                           'requires_review': 'Classify paid vs free, grant vs automatic, affected product, account eligibility and exact effective time separately.'})
    return candidates[:80]


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official(newurl):
            raise ValueError('Redirect left the configured official HTTPS hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

    # Python 3.10 otherwise rejects ordinary permanent HTTP 308 redirects.
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_302(req, fp, 302, msg, headers)


def scan_notices(state, urls, now, interval_hours=6, fetch=None):
    state = json.loads(json.dumps(state))
    state.setdefault('documents', {}); state.setdefault('candidates', {})
    if state.get('last_attempt_at') and (now-timestamp(state['last_attempt_at'])).total_seconds() < interval_hours*3600:
        return state, []
    state['last_attempt_at'] = now.isoformat(); new = []
    for url in urls:
        if not official(url):
            raise ValueError('Unofficial notice source')
        entry = state['documents'].setdefault(url, {})
        try:
            if fetch:
                body = fetch(url)
            else:
                opener = urllib.request.build_opener(OfficialRedirect())
                with opener.open(url, timeout=20) as response:
                    if not official(response.geturl()):
                        raise ValueError('Unofficial response URL')
                    raw = response.read(6_000_001)
                    if len(raw) > 6_000_000:
                        raise ValueError('Notice exceeds bounded fetch size; use official web page reader')
                    body = raw.decode('utf-8')
            digest = hashlib.sha256(body.encode()).hexdigest()
            if digest != entry.get('sha256'):
                for candidate in extract_candidates(body, url):
                    if candidate['id'] not in state['candidates']:
                        candidate['first_seen_at'] = now.isoformat()
                        state['candidates'][candidate['id']] = candidate; new.append(candidate['id'])
            entry.update(sha256=digest, last_success_at=now.isoformat(), consecutive_failures=0)
            entry.pop('error', None)
        except Exception as exc:
            entry.update(last_failure_at=now.isoformat(), consecutive_failures=entry.get('consecutive_failures', 0)+1, error=type(exc).__name__+': '+str(exc))
    return state, new


def ingest_web_notices(state, documents, allowed, now):
    """Public official-page text already retrieved through the web tool.

    This is an ordinary alternate public reading channel, never a CAPTCHA,
    login, paywall, or security-interstitial workaround. Candidates stay unverified.
    """
    state = json.loads(json.dumps(state))
    state.setdefault('documents', {}); state.setdefault('candidates', {})
    new = []
    for document in documents:
        url = document['source_url']
        if not official(url) or url not in allowed or document.get('method') != 'official_web_tool':
            raise ValueError('Unapproved notice evidence')
        observed = timestamp(document['fetched_at'])
        if not 0 <= (now-observed).total_seconds() <= 900:
            raise ValueError('Official web evidence is stale or future-dated')
        body = document['text']
        if not isinstance(body, str) or not body.strip() or len(body) > 500000:
            raise ValueError('Missing or excessive official web evidence')
        for candidate in extract_candidates(body, url):
            if candidate['id'] not in state['candidates']:
                candidate['first_seen_at'] = observed.isoformat()
                state['candidates'][candidate['id']] = candidate; new.append(candidate['id'])
        entry = state['documents'].setdefault(url, {})
        if entry.get('error'): entry['last_direct_fetch_error'] = entry.pop('error')
        entry.update(sha256=hashlib.sha256(body.encode()).hexdigest(), last_success_at=observed.isoformat(), source_method='official_web_tool', consecutive_failures=0)
    return state, new


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usage', type=pathlib.Path, required=True, help='Fresh get_usage_limits JSON (raw payload or tool result)')
    parser.add_argument('--state', type=pathlib.Path, default=R/'private/reset-planner-state.json')
    parser.add_argument('--scan-notices', action='store_true')
    parser.add_argument('--web-notices', type=pathlib.Path, help='Fresh public-page evidence returned by official web reading tools; no security bypass')
    parser.add_argument('--mark-notified', action='append', default=[], help='Record an ID only when preparing a real user notification; local deduplication only')
    args = parser.parse_args()
    now = dt.datetime.now(UTC)
    policy = json.loads((R/'automation/local-policy.json').read_text(encoding='utf-8'))
    catalog = json.loads((R/'automation/reset-announcements.json').read_text(encoding='utf-8'))
    state = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else {}
    receipt = json.loads(args.usage.read_text(encoding='utf-8'))
    # Timestamp must travel with the live receipt; reading an old saved payload
    # cannot make it fresh merely by invoking this CLI again.
    current = snapshot(receipt.get('usage', receipt), timestamp(receipt['checked_at']))
    previous = state.get('snapshot')
    if previous and previous['account_key'] == current['account_key'] and timestamp(current['checked_at']) < timestamp(previous['checked_at']):
        raise ValueError('Out-of-order usage receipt; obtain fresh live usage instead of rewinding account state')
    decision = plan(current, state.get('snapshot'), policy, catalog['events'], now)
    if args.scan_notices:
        interval = policy['reset_planner']['notice_check_hours']
        if any(report['next_date_advisory'] and dt.date.fromisoformat(report['next_date_advisory']) <= now.date()+dt.timedelta(days=2) for report in decision['cadence'].values()):
            interval = 1
        for event in catalog['events']:
            try:
                if event.get('verified') is True and event.get('kind') == 'automatic_reset' and official(event.get('source_url', '')) and 0 < (timestamp(event['effective_at'])-now).total_seconds() <= 86400:
                    interval = 1
            except (KeyError, ValueError, TypeError):
                pass
            try:
                if event.get('verified') is True and event.get('kind') == 'automatic_reset' and official(event.get('source_url', '')) and now.date() <= dt.date.fromisoformat(event['event_date']) <= now.date()+dt.timedelta(days=2):
                    interval = 1  # Date-only notices increase observation, never authorize work.
            except (KeyError, ValueError, TypeError):
                pass
        old_monitor = state.get('notice_monitor', {})
        monitor, new = scan_notices(old_monitor, policy['reset_planner']['official_notice_sources'], now, interval)
        state['notice_monitor'] = monitor; decision['new_notice_candidate_ids'] = new
        decision['notice_checked_this_run'] = old_monitor.get('last_attempt_at') != monitor.get('last_attempt_at')
        decision['notice_baseline_created'] = not old_monitor.get('last_attempt_at')
        decision['notice_check_interval_hours'] = interval
        decision['notice_failures'] = {url: e['error'] for url, e in monitor['documents'].items() if e.get('error')}
    if args.web_notices:
        previous_monitor = state.get('notice_monitor', {})
        first_success = not any(d.get('last_success_at') for d in previous_monitor.get('documents', {}).values())
        monitor, new = ingest_web_notices(previous_monitor, json.loads(args.web_notices.read_text(encoding='utf-8')), policy['reset_planner']['official_notice_sources'], now)
        state['notice_monitor'] = monitor
        decision['new_notice_candidate_ids'] = list(dict.fromkeys(decision.get('new_notice_candidate_ids', [])+new))
        decision['notice_checked_this_run'] = True
        decision['notice_baseline_created'] = decision.get('notice_baseline_created', False) or first_success
        decision['notice_failures'] = {url: e['error'] for url, e in monitor['documents'].items() if e.get('error')}
    notified = state.setdefault('notified_ids_by_account', {}).setdefault(current['account_key'], [])
    decision['banked_attention'] = [item for item in decision['banked_attention'] if item['id'] not in notified]
    decision['previously_notified_ids'] = list(notified)
    for identity in args.mark_notified:
        if identity not in notified: notified.append(identity)
    state['notified_ids_by_account'][current['account_key']] = notified[-500:]
    state['snapshot'] = current; state['last_decision'] = decision
    state.setdefault('observations', []).extend(dict(observed_at=now.isoformat(), **c) for c in decision['observed_changes'])
    state['observations'] = state['observations'][-200:]
    save(args.state, state)
    print(json.dumps(decision, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
