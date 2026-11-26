import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import agy_review

EMPTY = json.dumps({'conversation_id': '', 'status': 'ERROR', 'response': '',
                    'error': 'failed to start conversation: backend returned an empty conversation id'})
OK = json.dumps({'conversation_id': 'abc-123', 'status': 'SUCCESS', 'response': 'proposal'})


def runner(script):
    calls = []

    def run(prompt, model, mode, timeout):
        calls.append(model)
        return script.pop(0)
    return run, calls


class AgyReviewTests(unittest.TestCase):
    def test_empty_conversation_id_is_retried_then_succeeds(self):
        run, calls = runner([(1, EMPTY, 'error: failed to start conversation', None), (0, OK, '', None)])
        sleeps = []
        record, last = agy_review.call('p', 'gemini-3.8-flash-medium', [], 2, runner=run, sleep=sleeps.append)
        self.assertEqual(record['state'], 'success')
        self.assertEqual(record['requested_model'], 'gemini-3.8-flash-medium')
        self.assertEqual(record['attempts'], 2)
        self.assertEqual(record['attempt_log'][0]['outcome'], 'transient')
        self.assertEqual(len(sleeps), 1)
        self.assertEqual(last['out']['response'], 'proposal')

    def test_falls_back_to_next_model_after_retries(self):
        run, calls = runner([(1, EMPTY, '', None)] * 3 + [(0, OK, '', None)])
        record, _ = agy_review.call('p', 'gemini-3.8-flash-medium', ['gemini-4-hydrogen-high'], 2,
                                    runner=run, sleep=lambda s: None)
        self.assertEqual(calls, ['gemini-3.8-flash-medium'] * 3 + ['gemini-4-hydrogen-high'])
        self.assertEqual(record['state'], 'success')
        self.assertTrue(record['fallback_used'])
        self.assertEqual(record['requested_model'], 'gemini-4-hydrogen-high')

    def test_exhausted_transient_failures_are_reported(self):
        run, calls = runner([(1, EMPTY, '', None)] * 2)
        record, _ = agy_review.call('p', 'm1', [], 1, runner=run, sleep=lambda s: None)
        self.assertEqual(record['state'], 'transient_exhausted')
        self.assertIsNone(record['requested_model'])
        self.assertEqual(len(calls), 2)

    def test_quota_or_auth_errors_stop_without_retry(self):
        for error in ('RESOURCE_EXHAUSTED: quota exceeded', 'not logged in; sign in again', 'HTTP 429 rate limit'):
            out = json.dumps({'conversation_id': '', 'status': 'ERROR', 'response': '', 'error': error})
            run, calls = runner([(1, out, '', None), (0, OK, '', None)])
            record, _ = agy_review.call('p', 'm1', ['m2'], 2, runner=run, sleep=lambda s: None)
            self.assertEqual(record['state'], 'stop', error)
            self.assertEqual(calls, ['m1'])

    def test_success_needs_response_and_conversation_id(self):
        self.assertEqual(agy_review.classify(0, json.loads(OK), ''), 'success')
        self.assertEqual(agy_review.classify(0, {'status': 'SUCCESS', 'response': '', 'conversation_id': 'x'}, ''), 'error')
        self.assertEqual(agy_review.classify(None, None, '', 'local timeout after 140s'), 'transient')

    def test_overlong_prompt_is_refused(self):
        with self.assertRaises(ValueError):
            agy_review.call('x' * (agy_review.MAX_PROMPT_CHARS + 1), runner=lambda *a: None)


if __name__ == '__main__':
    unittest.main()
