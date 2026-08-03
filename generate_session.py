"""Run ONCE locally to produce a Telethon StringSession.

    pip install telethon
    python generate_session.py

Enter your api_id / api_hash (from https://my.telegram.org -> API development
tools), then the phone number and the login code Telegram sends you (and your
2FA password if enabled). It prints a session string — store it as the
TG_SESSION secret. Treat it like a password: it grants access to that account.

Tip: use a DEDICATED Telegram account (not your personal number) for scraping.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("api_id: ").strip())
api_hash = input("api_hash: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== TG_SESSION (store this as a secret) ===")
    print(client.session.save())
    print("===========================================")
