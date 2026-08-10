"""One-time BACKFILL of historical SSD token-status posts from the channel.

Pages backwards through the channel's history and upserts every parseable
status post into `ssd_telegram_status` (dedup on message_id, so re-running is
safe). The `ssd_release_daily` view then derives a per-day open/close for each
historical day, giving the predictor years of data instead of days.

Run locally (or via the backfill GitHub Action). Needs the same env as worker.py:
    pip install telethon requests
    BACKFILL_DAYS=730 python backfill_history.py

Env:
    TG_API_ID, TG_API_HASH, TG_SESSION, TG_CHANNEL
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    BACKFILL_DAYS   how far back to go (default 730 = ~2 years)
"""
import datetime as dt
import os

import requests
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from parser import parse_message

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]
CHANNEL = os.environ.get("TG_CHANNEL", "LaxmiTeluguTechChannel")
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
DAYS = int(os.environ.get("BACKFILL_DAYS", "730"))
BATCH = 200

CUTOFF = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)


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
        timeout=60,
    )
    r.raise_for_status()


def main():
    scanned = 0
    upserted = 0
    oldest = None
    newest = None
    unparsed = []
    buf = []

    with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        # iter_messages defaults to newest -> oldest.
        for msg in client.iter_messages(CHANNEL):
            if msg.date < CUTOFF:
                break
            scanned += 1
            oldest = msg.date
            if newest is None:
                newest = msg.date

            text = msg.message or ""
            parsed = parse_message(text)
            if not parsed:
                # Collect a few token-related posts we DIDN'T parse, so we can
                # tell whether an older message format needs new regexes.
                low = text.lower()
                if ("token" in low or "ssd" in low or "mettu" in low) \
                        and len(unparsed) < 20:
                    unparsed.append(text.replace("\n", " ")[:180])
                continue

            when = msg.edit_date or msg.date
            buf.append({
                "message_id": msg.id,
                "message_at": when.isoformat() if when else None,
                "issue_started_time": parsed["issue_started_time"],
                "ssd_available": parsed["ssd_available"],
                "ssd_completed": parsed["ssd_completed"],
                "mettu_available": parsed["mettu_available"],
                "mettu_completed": parsed["mettu_completed"],
                "raw_text": text[:2000],
            })
            upserted += 1
            if len(buf) >= BATCH:
                upsert(buf)
                buf = []
                print(f"  … {upserted} upserted (at {msg.date.date()})", flush=True)

        upsert(buf)

    print(f"\n[backfill] scanned {scanned} messages, upserted {upserted} status posts")
    print(f"[backfill] range: {oldest.date() if oldest else '-'} … {newest.date() if newest else '-'}")
    if scanned and oldest and oldest > CUTOFF + dt.timedelta(days=1):
        print("[backfill] NOTE: reached the channel's earliest post before the "
              "cutoff — it doesn't have the full requested history.")
    if unparsed:
        print("\n[backfill] Token-related posts NOT parsed (check for an older "
              "wording that needs a parser tweak):")
        for u in unparsed:
            print("   -", u)


if __name__ == "__main__":
    main()
