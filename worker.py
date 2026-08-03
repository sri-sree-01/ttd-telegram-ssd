"""Telegram -> Supabase worker for the LaxmiTeluguTech SSD/DD token channel.

Reads the latest posts from a PUBLIC Telegram channel via MTProto (Telethon,
logged in as a user account), parses the token status, and upserts rows into
public.ssd_telegram_status (dedup/upsert on message_id, so edited posts update
in place).

Why not a Supabase edge function? MTProto needs a stateful connection, so this
runs as a standalone job (GitHub Actions cron / VPS / Raspberry Pi).

Env vars:
  TG_API_ID, TG_API_HASH        - from my.telegram.org
  TG_SESSION                    - StringSession from generate_session.py
  TG_CHANNEL                    - channel username (default LaxmiTeluguTechChannel)
  TG_LIMIT                      - how many recent messages to scan (default 20)
  SUPABASE_URL                  - https://<ref>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY     - service role key (server-side only)
"""
import os

import requests
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from parser import parse_message

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]
CHANNEL = os.environ.get("TG_CHANNEL", "LaxmiTeluguTechChannel")
LIMIT = int(os.environ.get("TG_LIMIT", "20"))
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def upsert(rows):
    if not rows:
        return
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/ssd_telegram_status?on_conflict=message_id",
        headers={
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        json=rows,
        timeout=30,
    )
    r.raise_for_status()


def main():
    rows = []
    with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        for msg in client.iter_messages(CHANNEL, limit=LIMIT):
            text = msg.message or ""
            parsed = parse_message(text)
            if not parsed:
                continue
            when = msg.edit_date or msg.date  # UTC datetime
            rows.append({
                "message_id": msg.id,
                "message_at": when.isoformat() if when else None,
                "issue_started_time": parsed["issue_started_time"],
                "ssd_available": parsed["ssd_available"],
                "ssd_completed": parsed["ssd_completed"],
                "mettu_available": parsed["mettu_available"],
                "mettu_completed": parsed["mettu_completed"],
                "raw_text": text[:2000],
            })

    upsert(rows)
    print(f"[telegram-ssd] parsed & upserted {len(rows)} status message(s)")
    for row in rows[:5]:
        print(
            f"  msg {row['message_id']} @ {row['message_at']} | "
            f"start={row['issue_started_time']} "
            f"SSD={'DONE' if row['ssd_completed'] else row['ssd_available']} "
            f"Mettu={'DONE' if row['mettu_completed'] else row['mettu_available']}"
        )


if __name__ == "__main__":
    main()
