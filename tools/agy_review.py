"""Call Gemini through the official Antigravity CLI (`agy --print`) with bounded retries.

2026-11-26: the backend intermittently answered
"failed to start conversation: backend returned an empty conversation id" (status ERROR,
no response, ~0 s). The same prompt succeeded an hour later, so one attempt per run lost
whole batches. This wrapper retries such transient start failures with backoff, then tries
the listed fallback models, and records every attempt. Authentication, quota, rate-limit,
CAPTCHA or security-verification errors stop immediately (policy stop_on); never retried.

The successful attempt's model is the requested model identity to record; the serving
snapshot is still not exposed by the CLI.

  python tools/agy_review.py --prompt-file private/X-gemini-initial-prompt.txt \
      --out private/X-gemini-initial [--model gemini-3.8-flash-medium] \
      [--fallback-model gemini-4-hydrogen-high] [--retries 2]

Writes <out>-result.json (raw CLI JSON of the final attempt), <out>-result.json.stderr.txt
and <out>-call.json (all attempts). Exit 0 on success, 3 on transient failure after all
attempts, 4 on a stop condition, 1 on other errors.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import time

UTC = dt.timezone.utc
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
DEFAULT_MODEL = 'gemini-3.8-flash-medium'
DEFAULT_FALLBACKS = ['gemini-4-hydrogen-high']
BACKOFF_SECONDS = [20, 60, 120]
# Windows CreateProcess limit is 32767 UTF-16 units for the whole command line.
MAX_PROMPT_CHARS = 30000

STOP = re.compile(r'(?i)(unauthori[sz]ed|unauthenticated|not logged in|log ?in required|sign ?in|re-?authenticate|'
                  r'credential|quota|rate.?limit|resource.?exhausted|\b429\b|usage limit|captcha|'
                  r'security verification|verify (?:that )?you|permission denied|forbidden|\b403\b|billing|upgrade)')
TRANSIENT = re.compile(r'(?i)(empty conversation id|failed to start conversation|\b5\d\d\b|unavailable|'
                       r'internal error|deadline|timed? ?out|timeout|try again|temporar|connection|reset by peer|eof|'
                       r'backend)')
MODEL_MISSING = re.compile(r'(?i)(unknown model|model .*not (?:found|available|supported)|invalid model)')


def agy_exe():
    found = shutil.which('agy')
    if found:
        return found
    return str(pathlib.Path(os.environ.get('LOCALAPPDATA', '')) / 'agy' / 'bin' / 'agy.exe')


def parse_output(stdout):
    """Last JSON object printed by `--output-format json`; None if there is none."""
    for line in reversed((stdout or '').strip().splitlines()):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except ValueError:
                continue
    try:
        return json.loads(stdout)
    except (ValueError, TypeError):
        return None


def classify(exit_code, out, stderr, local_error=None):
    """'success' | 'stop' | 'model_missing' | 'transient' | 'error'."""
    response = (out or {}).get('response') or ''
    if exit_code == 0 and out and out.get('status') == 'SUCCESS' and response.strip() and (out.get('conversation_id') or '').strip():
        return 'success'
    text = ' '.join(str(x) for x in ((out or {}).get('error'), (out or {}).get('status'), stderr, local_error) if x)
    if STOP.search(text):
        return 'stop'
    if MODEL_MISSING.search(text):
        return 'model_missing'
    if local_error or TRANSIENT.search(text) or (out and not (out.get('conversation_id') or '').strip()):
        return 'transient'
    return 'error'


def run_agy(prompt, model, mode, timeout_seconds):
    cmd = [agy_exe(), '--print', prompt, '--model', model, '--mode', mode,
           '--output-format', 'json', '--print-timeout', '%ds' % timeout_seconds]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=timeout_seconds + 30, creationflags=NO_WINDOW)
        return p.returncode, p.stdout, p.stderr, None
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or '', exc.stderr or '', 'local timeout after %ss' % (timeout_seconds + 30)


def call(prompt, model=DEFAULT_MODEL, fallbacks=None, retries=2, mode='plan', timeout_seconds=110,
         runner=run_agy, sleep=time.sleep, now=lambda: dt.datetime.now(UTC)):
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError('Prompt has %d chars (> %d, Windows command-line limit); have the model read_file a '
                         'prompt file instead' % (len(prompt), MAX_PROMPT_CHARS))
    models = [model] + [m for m in (DEFAULT_FALLBACKS if fallbacks is None else fallbacks) if m != model]
    attempts, last = [], None
    for index, current in enumerate(models):
        for attempt in range(retries + 1):
            started = now()
            code, stdout, stderr, local_error = runner(prompt, current, mode, timeout_seconds)
            out = parse_output(stdout)
            kind = classify(code, out, stderr, local_error)
            attempts.append({'model': current, 'fallback': index > 0, 'started_at': started.isoformat(),
                             'finished_at': now().isoformat(), 'exit_code': code, 'outcome': kind,
                             'status': (out or {}).get('status'), 'conversation_id': (out or {}).get('conversation_id'),
                             'error': ((out or {}).get('error') or local_error or (stderr or '').strip()[-500:] or None)})
            last = {'stdout': stdout, 'stderr': stderr, 'out': out}
            if kind in ('success', 'stop'):
                return finish(kind, current, attempts, last, mode)
            if kind in ('model_missing', 'error'):
                break  # do not hammer the same model on a non-transient error; try the next model
            if attempt < retries:
                sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
    return finish('transient_exhausted' if attempts and attempts[-1]['outcome'] == 'transient' else 'failed',
                  None, attempts, last, mode)


def finish(state, model, attempts, last, mode):
    record = {'state': state, 'requested_model': model, 'first_requested_model': attempts[0]['model'],
              'fallback_used': bool(model and model != attempts[0]['model']), 'mode': mode,
              'attempts': len(attempts), 'retry_count': max(0, len(attempts) - 1), 'attempt_log': attempts,
              'provider': 'Antigravity official agy CLI',
              'identity_basis': 'CLI model selector of the successful attempt; the serving snapshot is not exposed.'}
    if state == 'stop':
        record['stop_reason'] = 'Authentication, quota, rate-limit or verification message; stop and report (not retried).'
    return record, last


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--prompt-file', type=pathlib.Path, required=True)
    ap.add_argument('--out', required=True, help='output prefix, e.g. private/batch-X-gemini-initial')
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--fallback-model', action='append', default=None,
                    help='repeatable; default %s; pass "none" for no fallback' % DEFAULT_FALLBACKS)
    ap.add_argument('--retries', type=int, default=2, help='extra attempts per model for transient failures')
    ap.add_argument('--mode', default='plan', choices=['plan', 'accept-edits'])
    ap.add_argument('--timeout', type=int, default=110, help='seconds per attempt')
    args = ap.parse_args()
    fallbacks = None if args.fallback_model is None else [m for m in args.fallback_model if m.lower() != 'none']
    prompt = args.prompt_file.read_text(encoding='utf-8')
    record, last = call(prompt, args.model, fallbacks, max(0, args.retries), args.mode, args.timeout)
    record['prompt_file'] = str(args.prompt_file)
    prefix = pathlib.Path(args.out)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(str(prefix) + '-result.json').write_text((last or {}).get('stdout') or '', encoding='utf-8')
    pathlib.Path(str(prefix) + '-result.json.stderr.txt').write_text((last or {}).get('stderr') or '', encoding='utf-8')
    pathlib.Path(str(prefix) + '-call.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('state', 'requested_model', 'fallback_used', 'attempts')}, ensure_ascii=False))
    raise SystemExit({'success': 0, 'transient_exhausted': 3, 'stop': 4}.get(record['state'], 1))


if __name__ == '__main__':
    main()
