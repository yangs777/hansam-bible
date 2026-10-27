"""Locale-specific, optional support pages; payment details stay out of other locales."""
import hashlib
import html
import json
import pathlib
import shutil
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

R = pathlib.Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def load():
    config = json.loads((R / 'support.json').read_text(encoding='utf-8'))
    wallet = config['usdt']
    # Validate the receiving address, independently of the QR image.
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    number = 0
    for char in wallet['address']:
        number = number * 58 + alphabet.index(char)
    raw = number.to_bytes((number.bit_length() + 7) // 8, 'big')
    if len(raw) != 25 or raw[0] != 0x41 or hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4] != raw[-4:]:
        raise ValueError('Invalid TRON receiving address')
    if wallet['network'] != 'TRON (TRC20)' or wallet['symbol'] != 'USDT':
        raise ValueError('Support QR is specifically for USDT on TRON (TRC20)')
    date.fromisoformat(wallet['verified_date'])
    if not Decimal(wallet['minimum_deposit_exclusive']).is_finite() or Decimal(wallet['minimum_deposit_exclusive']) < 0:
        raise ValueError('Minimum deposit must be a non-negative finite amount')
    proof = json.loads((R / 'assets/support/qr-manifest.json').read_text(encoding='utf-8'))
    if proof['payload'] != wallet['address']:
        raise ValueError('Receiving address and verified QR payload differ')
    for name, digest in proof['sha256'].items():
        if name not in ('usdt-trc20.svg', 'usdt-trc20.png') or hashlib.sha256((R / 'assets/support' / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Verified QR asset changed; decode it again before publication')
    product_url = config['product']['url']
    if product_url:
        parsed = urlsplit(product_url)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or not (host == 'coupang.com' or host.endswith('.coupang.com')) or parsed.username or parsed.password:
            raise ValueError('Use the creator-provided HTTPS Coupang product URL')
    return config


def footer(lang):
    line, label = {
        'ko': ('광고 없이, 독자의 자발적인 후원으로 이어갑니다.', '프로젝트 후원'),
        'en': ('Ad-free, with voluntary reader support.', 'Support the project'),
        'es': ('Sin publicidad, con el apoyo voluntario de sus lectores.', 'Apoyar el proyecto'),
    }[lang]
    return f'<div class="support-footer"><p>{line}</p><a href="/{lang}/support/">{label} <span aria-hidden="true">↗</span></a></div>'


def copy_field(identifier, value, label, copied):
    return f'''<div class="support-copy"><code id="{identifier}" dir="ltr">{esc(value)}</code><button class="button" type="button" data-copy="{identifier}" data-done="{copied}">{label}</button><p class="copy-status" role="status" aria-live="polite"></p></div>'''


def body(lang, config):
    if lang == 'ko':
        bank, product = config['bank'], config['product']
        product_link = (f'<a class="button" href="{esc(product["url"])}" target="_blank" rel="noopener sponsored">쿠팡에서 메주자 살펴보기 <span aria-hidden="true">↗</span></a><p class="fine">쿠팡 상품 페이지가 새 창으로 열립니다. 가격·배송·반품 조건은 상품 페이지에서 확인해 주세요.</p>'
                        if product['url'] else '<p class="fine support-pending">메주자 상품 링크 확인 중입니다.</p>')
        return f'''<section class="document support-page"><p class="eyebrow">ORIGINAL BIBLE / READER SUPPORT</p><h1>광고 없이,<br>함께 이어가는 원문성경.</h1><p class="lead">원문성경은 제작자의 작업과 독자의 자발적인 후원으로 이어가는 공개 프로젝트입니다.</p><p>후원은 선택입니다. 본문 읽기·복사·대조와 공개 데이터는 누구에게나 열려 있습니다. 보내주시는 마음은 원문 자료 정리, 번역 비교와 검토, 사이트 유지에 보탬이 됩니다.</p><div class="support-grid"><section class="support-card" aria-labelledby="bank-heading"><p class="eyebrow">01 / 마음을 보태기</p><h2 id="bank-heading">계좌로 후원하기</h2><p>{esc(bank['name'])} · 예금주 {esc(bank['holder'])}</p>{copy_field('support-bank-account', bank['account'], '계좌번호 복사', '계좌번호를 복사했습니다.')}<p class="fine">입금 전 은행과 예금주를 확인해 주세요.</p></section><section class="support-card" aria-labelledby="product-heading"><p class="eyebrow">02 / 제작자의 물건</p><h2 id="product-heading">직접 만든 메주자</h2><p>제작자 양한샘이 직접 만들어 쿠팡에서 판매하는 메주자입니다. 마음에 드는 물건을 구매해 주시는 것도 제작 활동과 원문성경을 이어가는 데 큰 힘이 됩니다.</p><p class="fine">제작자가 직접 판매하는 상품의 구매 안내입니다.</p>{product_link}</section></div><p class="support-thanks">읽어 주시는 것만으로도 감사합니다.</p><a class="text-link" href="/read/">본문으로 돌아가기 →</a></section>'''
    wallet = config['usdt']
    text = {
        'en': dict(title='Ad-free.<br>Supported by readers.', lead='Original Bible is an open project sustained by its creator’s work and voluntary reader support.', intro='Support is optional. Reading, copying, comparison and the open data remain available to everyone. Your support helps with source preparation, translation comparison and review, and site upkeep.', heading='Support with USDT', account='Binance receiving address', copy='Copy address', copied='Address copied.', network='Send only USDT on TRON (TRC20). Match this network in your sending wallet before transferring.', minimum=f'Binance minimum deposit: more than {esc(wallet["minimum_deposit_exclusive"])} USDT.', checked=f'Receiving details checked on {esc(wallet["verified_date"])}. Provider limits may change. Your sending wallet may charge fees.', qr='QR containing the receiving address only; use USDT on TRON (TRC20).', download='Download address QR (PNG)', thanks='Thank you for reading, whether or not you choose to support.', back='Return to the text'),
        'es': dict(title='Sin publicidad.<br>Con el apoyo de sus lectores.', lead='Original Bible es un proyecto abierto que se sostiene con el trabajo de su creador y el apoyo voluntario de sus lectores.', intro='Apoyar es opcional. La lectura, la copia, la comparación y los datos abiertos siguen disponibles para todos. Su apoyo contribuye a preparar las fuentes, comparar y revisar las traducciones y mantener el sitio.', heading='Apoyar con USDT', account='Dirección de depósito en Binance', copy='Copiar dirección', copied='Dirección copiada.', network='Envíe únicamente USDT por la red TRON (TRC20). Seleccione esta misma red en su billetera antes de transferir.', minimum=f'Depósito mínimo en Binance: más de {esc(wallet["minimum_deposit_exclusive"].replace(".", ","))} USDT.', checked=f'Datos de depósito comprobados el {esc(wallet["verified_date"])}. Los límites del proveedor pueden cambiar. Su billetera de origen puede cobrar comisiones.', qr='QR que contiene solo la dirección de depósito; utilice USDT en TRON (TRC20).', download='Descargar QR de la dirección (PNG)', thanks='Gracias por leer, decida o no apoyar el proyecto.', back='Volver al texto'),
    }[lang]
    return f'''<section class="document support-page"><p class="eyebrow">ORIGINAL BIBLE / READER SUPPORT</p><h1>{text['title']}</h1><p class="lead">{text['lead']}</p><p>{text['intro']}</p><section class="support-card support-wallet" aria-labelledby="wallet-heading"><div><p class="eyebrow">USDT · TRON (TRC20)</p><h2 id="wallet-heading">{text['heading']}</h2><p>{text['account']}</p>{copy_field('support-usdt-address', wallet['address'], text['copy'], text['copied'])}<p class="support-network">{text['network']}</p><p class="fine">{text['minimum']} {text['checked']}</p></div><figure class="support-qr"><img src="{esc(wallet['qr'])}" width="240" height="240" alt="{text['qr']}"><figcaption>USDT · TRON (TRC20)</figcaption><a href="/assets/support/usdt-trc20.png" download="original-bible-usdt-trc20.png">{text['download']}</a></figure></section><p class="support-thanks">{text['thanks']}</p><a class="text-link" href="/{lang}/">{text['back']} →</a></section>'''


def build(page):
    config = load()
    shutil.copytree(R / 'assets/support', R / 'dist/assets/support', dirs_exist_ok=True)
    titles = {'ko': '프로젝트 후원 — 광고 없이 함께 이어가는 원문성경', 'en': 'Support Original Bible — ad-free and open', 'es': 'Apoyar Original Bible — abierto y sin publicidad'}
    for lang, title in titles.items():
        page(f'/{lang}/support/', title, body(lang, config), lang, {key: f'/{key}/support/' for key in titles}, description=title)
