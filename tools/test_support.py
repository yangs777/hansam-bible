"""Prevent cross-locale payment disclosures and mismatched receiving QR assets."""
import json
import unittest
from unittest.mock import patch

import support


class SupportTests(unittest.TestCase):
    def test_korean_has_two_routes_and_no_wallet(self):
        config = support.load()
        config['product']['url'] = 'https://www.coupang.com/vp/products/123'
        output = support.body('ko', config)
        for value in (config['bank']['account'], config['bank']['holder'], config['product']['url']):
            self.assertIn(value, output)
        for value in (config['usdt']['address'], 'USDT', 'TRC20', 'support-qr'):
            self.assertNotIn(value, output)
        self.assertEqual(output.count('class="support-card"'), 2)
        self.assertIn('id="support-bank-account" dir="ltr">' + config['bank']['account'] + '</code>', output)

    def test_foreign_pages_show_only_verified_wallet(self):
        config = support.load()
        config['product']['url'] = 'https://www.coupang.com/vp/products/123'
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                output = support.body(lang, config)
                self.assertIn(config['usdt']['address'], output)
                self.assertIn('USDT', output)
                self.assertIn('TRON (TRC20)', output)
                self.assertIn(config['usdt']['qr'], output)
                self.assertIn('data-copy="support-usdt-address"', output)
                self.assertIn('role="status"', output)
                for value in (*config['bank'].values(), config['product']['url'], 'coupang', '쿠팡', '메주자'):
                    self.assertNotIn(value, output)

    def test_stale_or_modified_qr_is_rejected(self):
        original = json.loads
        def wrong_payload(raw):
            value = original(raw)
            if 'payload' in value:
                value['payload'] = 'another-wallet'
            return value
        with patch.object(support.json, 'loads', side_effect=wrong_payload):
            with self.assertRaisesRegex(ValueError, 'payload differ'):
                support.load()
        def wrong_hash(raw):
            value = original(raw)
            if 'sha256' in value:
                value['sha256']['usdt-trc20.svg'] = '0' * 64
            return value
        with patch.object(support.json, 'loads', side_effect=wrong_hash):
            with self.assertRaisesRegex(ValueError, 'QR asset changed'):
                support.load()

    def test_footer_is_findable_and_locale_specific_without_payment_details(self):
        config = support.load()
        for lang in ('ko', 'en', 'es'):
            output = support.footer(lang)
            self.assertIn(f'href="/{lang}/support/"', output)
            self.assertNotIn(config['bank']['account'], output)
            self.assertNotIn(config['usdt']['address'], output)


if __name__ == '__main__':
    unittest.main()
