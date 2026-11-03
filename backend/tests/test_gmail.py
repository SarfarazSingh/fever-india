import asyncio
import base64
import hashlib
import json
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import utcnow
from app.v1.integrations import decode_message, sync_mailbox
from app.v1.mail import READ_SCOPE, SEND_SCOPE, send_delivery
from app.v1.models import Account, EmailDelivery, MailConnection
from app.v1.security import decrypt, encrypt


@pytest.fixture
def gmail(client, monkeypatch):
    c = TestClient(app)
    result = c.post('/api/v1/auth/demo').json()
    c.headers['x-csrf-token'] = result['csrf_token']
    c.account_id = result['account']['id']
    c.account_email = 'gmail-' + c.account_id + '@example.com'
    for key, value in {'allowed_emails': c.account_email, 'google_client_id': 'private-client',
        'google_client_secret': 'private-secret', 'gmail_send_enabled': True,
        'gmail_redirect_uri': 'http://testserver/api/v1/connections/gmail/callback',
        'token_encryption_key': Fernet.generate_key().decode()}.items():
        monkeypatch.setattr(get_settings(), key, value)
    async def setup():
        async with SessionLocal() as db:
            account = await db.get(Account, c.account_id)
            account.email, account.is_demo = c.account_email, False
            await db.commit()
    asyncio.run(setup())
    return c


def response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request('POST', 'https://gmail.googleapis.com/test'))


def provider(monkeypatch, mode='success'):
    mock = AsyncMock()
    def post(url, **kwargs):
        if 'oauth2.googleapis.com' in url:
            return response({'access_token': 'private-access', 'refresh_token': 'private-refresh', 'scope': READ_SCOPE + ' ' + SEND_SCOPE})
        if mode == 'timeout': raise httpx.ReadTimeout('ambiguous response')
        if mode == 'declined': return response({'error': 'denied'}, 403)
        return response({'id': 'provider-message-id'})
    mock.post.side_effect = post
    def get(url, **kwargs):
        if url.endswith('/profile'): return response({'emailAddress': 'sender@example.com'})
        return response({'messages': [{'id': 'provider-message-id'}]} if mode == 'reconciled' else {'messages': []})
    mock.get.side_effect = get
    manager = AsyncMock()
    manager.__aenter__.return_value = mock
    monkeypatch.setattr('app.v1.mail.httpx.AsyncClient', lambda **kwargs: manager)
    return mock


def connect(c, send=False):
    r = c.post('/api/v1/connections/gmail/connect', json={'send_reminders': send})
    assert r.status_code == 200, r.text
    return parse_qs(urlsplit(r.json()['url']).query)


def test_gmail_permissions_are_separate_and_pkce_stays_server_side(gmail):
    assert connect(gmail)['scope'] == [READ_SCOPE]
    q = connect(gmail, True)
    assert q['scope'] == [READ_SCOPE + ' ' + SEND_SCOPE]
    assert q['code_challenge_method'] == ['S256']
    async def read():
        async with SessionLocal() as db:
            return await db.get(MailConnection, gmail.account_id)
    row = asyncio.run(read())
    verifier = json.loads(decrypt(row.verifier_ciphertext))['verifier']
    assert verifier not in row.verifier_ciphertext
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    assert q['code_challenge'] == [challenge]
    assert 'private-secret' not in str(q)


def test_callback_encrypts_credentials_and_rejects_replay(gmail, monkeypatch):
    mock = provider(monkeypatch)
    q = connect(gmail, True)
    path = '/api/v1/connections/gmail/callback?state=' + q['state'][0] + '&code=one-use'
    r = gmail.get(path, follow_redirects=False)
    assert r.status_code == 303 and 'access' not in r.headers['location']
    assert gmail.get('/api/v1/connections').json()['gmail']['can_send'] is True
    assert gmail.get(path, follow_redirects=False).status_code == 400
    async def read():
        async with SessionLocal() as db:
            return await db.get(MailConnection, gmail.account_id)
    row = asyncio.run(read())
    assert 'private-refresh' not in row.token_ciphertext
    assert 'access_token' not in decrypt(row.token_ciphertext)
    assert mock.post.call_count == 1


def test_gmail_cancel_and_expired_attempts_fail_closed(gmail):
    q = connect(gmail)
    path = '/api/v1/connections/gmail/callback'
    r = gmail.get(path, params={'state': q['state'][0], 'error': 'access_denied'}, follow_redirects=False)
    assert r.status_code == 303 and 'cancelled' in r.headers['location']
    assert gmail.get(path, params={'state': q['state'][0], 'code': 'replay'}).status_code == 400
    q = connect(gmail)
    async def expire():
        async with SessionLocal() as db:
            row = await db.get(MailConnection, gmail.account_id)
            row.state_expires_at = utcnow() - timedelta(seconds=1)
            await db.commit()
    asyncio.run(expire())
    assert gmail.get(path, params={'state': q['state'][0], 'code': 'expired'}).status_code == 400


def saved_connection(c):
    return MailConnection(account_id=c.account_id, status='connected', forwarding_token=secrets.token_hex(24),
        token_ciphertext=encrypt(json.dumps({'refresh_token': 'private-refresh', 'scope': READ_SCOPE + ' ' + SEND_SCOPE, 'mailbox_email': 'sender@example.com'})))


def add_delivery(c):
    key = secrets.token_hex(32)
    async def setup():
        async with SessionLocal() as db:
            db.add(saved_connection(c))
            db.add(EmailDelivery(id=key, account_id=c.account_id, kind='test'))
            await db.commit()
    asyncio.run(setup())
    return key


def state(key):
    async def read():
        async with SessionLocal() as db:
            return (await db.get(EmailDelivery, key)).state
    return asyncio.run(read())


def test_gmail_timeout_reconciles_without_resubmitting(gmail, monkeypatch):
    key = add_delivery(gmail)
    mock = provider(monkeypatch, 'timeout')
    asyncio.run(send_delivery(key))
    assert state(key) == 'confirming'
    asyncio.run(send_delivery(key))
    assert state(key) == 'confirming'
    assert len([c for c in mock.post.call_args_list if c.args[0].endswith('/send')]) == 1
    provider(monkeypatch, 'reconciled')
    asyncio.run(send_delivery(key))
    assert state(key) == 'sent'


def test_gmail_decline_is_terminal_and_delivery_is_private(gmail, monkeypatch):
    key = add_delivery(gmail)
    mock = provider(monkeypatch, 'declined')
    asyncio.run(send_delivery(key))
    asyncio.run(send_delivery(key))
    assert state(key) == 'failed'
    assert len([c for c in mock.post.call_args_list if c.args[0].endswith('/send')]) == 1
    other = TestClient(app)
    other.post('/api/v1/auth/demo')
    assert other.get('/api/v1/notifications/' + key).status_code == 404
    assert gmail.get('/api/v1/notifications/' + key).json()['state'] == 'failed'


def test_verified_gmail_send_targets_owner_and_does_not_duplicate(gmail, monkeypatch):
    key = add_delivery(gmail)
    mock = provider(monkeypatch)
    asyncio.run(send_delivery(key))
    assert state(key) == 'sent'
    sent = next(c for c in mock.post.call_args_list if c.args[0].endswith('/send'))
    mime = base64.urlsafe_b64decode(sent.kwargs['json']['raw'] + '===').decode()
    assert 'To: ' + gmail.account_email in mime
    assert 'From: sender@example.com' in mime and 'No flight was booked' in mime
    asyncio.run(send_delivery(key))
    assert len([c for c in mock.post.call_args_list if c.args[0].endswith('/send')]) == 1


def test_gmail_pagination_resumes_past_first_page(gmail, monkeypatch):
    mock = provider(monkeypatch)
    pages = iter([response({'messages': [], 'nextPageToken': 'next-page'}), response({'messages': []})])
    mock.get.side_effect = lambda *args, **kwargs: next(pages)
    async def sync():
        async with SessionLocal() as db:
            row = saved_connection(gmail)
            db.add(row)
            await db.commit()
            await sync_mailbox(db, row)
            assert row.last_synced_at is None and row.sync_state['page_token'] == 'next-page'
            await sync_mailbox(db, row)
            assert row.last_synced_at is not None and not row.sync_state
    asyncio.run(sync())
    assert mock.get.call_args_list[1].kwargs['params']['pageToken'] == 'next-page'


def test_multipart_confirmations_are_not_duplicated():
    def part(mime, text):
        return {'mimeType': mime, 'body': {'data': base64.urlsafe_b64encode(text.encode()).decode()}}
    message = {'mimeType': 'multipart/alternative', 'parts': [part('text/plain', 'Flight BA178'), part('text/html', '<p>Flight BA178</p>')]}
    assert decode_message(message) == ['Flight BA178']
    message['parts'][1] = part('text/html', '<script type="application/ld+json">{"@type":"FlightReservation"}</script>')
    assert len(decode_message(message)) == 1 and 'FlightReservation' in decode_message(message)[0]
