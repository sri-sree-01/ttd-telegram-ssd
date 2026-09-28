"""Telegram -> Supabase worker for the Sarva Darshan (free queue) screen.

Reads the latest "Tirumala Live Status" posts that the bot @TirumalaLiveBot
pushes to our dedicated Telegram account, keeps ONLY the Sarva Darshan part
(see sarva_parser.py) and upserts it into public.sarva_darshan_raw.

That table is admin-only. The app never sees these exact figures: a database
trigger (sarva_darshan_publish) turns every new row into a rounded, nudged
public snapshot (public.sarva_darshan_status), which is what the app reads.

Runs as an extra step of the existing telegram-ssd GitHub workflow, with the
same Telegram session as worker.py. That workflow is dispatched every 2-15
minutes, but the bot only posts every ~2 hours, so this script skips itself
when it already ran in the last SARVA_MIN_INTERVAL_MIN minutes (no Telegram
connection at all on those runs).

First run: a bot can't message a user who never started it, so if our chat
with the bot is empty we send /start once. After that we only LISTEN to the
bot's regular pushes — nothing is sent, unless you set SARVA_REFRESH_CMD.

Env vars:
  TG_API_ID, TG_API_HASH, TG_SESSION   - same as worker.py
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  SARVA_BOT                 - bot username (default TirumalaLiveBot)
  SARVA_LIMIT               - recent messages to scan (default 12)
  SARVA_MIN_INTERVAL_MIN    - skip if the last run was newer than this (default 10)
  SARVA_REFRESH_CMD         - OPTIONAL command to ask the bot for a fresh status
                              when the newest post is older than SARVA_STALE_MIN
                              (e.g. "/status" — check the bot's Menu). Off when empty.
  SARVA_STALE_MIN           - default 150
"""
import os
import sys
import time
from datetime import datetime, timezone

import requests

from sarva_parser import parse_sarva_message

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BOT = os.environ.get("SARVA_BOT", "TirumalaLiveBot").lstrip("@")
LIMIT = int(os.environ.get("SARVA_LIMIT", "12"))
MIN_INTERVAL_MIN = float(os.environ.get("SARVA_MIN_INTERVAL_MIN", "10"))
REFRESH_CMD = os.environ.get("SARVA_REFRESH_CMD", "").strip()
STALE_MIN = float(os.environ.get("SARVA_STALE_MIN", "150"))

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}


def now_utc():
    return datetime.now(timezone.utc)


def _parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_state():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/sarva_darshan_worker_state?id=eq.1&select=*",
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0] if rows else {}


def put_state(**fields):
    fields["id"] = 1
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/sarva_darshan_worker_state?on_conflict=id",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=fields,
        timeout=20,
    )
    r.raise_for_status()


def upsert_raw(rows):
    if not rows:
        return
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/sarva_darshan_raw?on_conflict=message_id",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=rows,
        timeout=30,
    )
    r.raise_for_status()


def read_posts(client, bot):
    """Newest-first list of (message, parsed) for the bot's status posts."""
    out = []
    for msg in client.get_messages(bot, limit=LIMIT):
        if msg.out:  # our own /start etc.
            continue
        parsed = parse_sarva_message(msg.message or "")
        if parsed:
            out.append((msg, parsed))
    return out


def data_time(msg, parsed):
    return _parse_ts(parsed.get("source_updated_at")) or msg.edit_date or msg.date


def main():
    state = {}
    try:
        state = get_state()
    except Exception as e:  # table missing / network — still try to run
        print(f"[sarva] could not read worker state: {e}")

    last_run = _parse_ts(state.get("last_run_at"))
    if last_run and (now_utc() - last_run).total_seconds() < MIN_INTERVAL_MIN * 60:
        print(f"[sarva] ran {int((now_utc() - last_run).total_seconds() // 60)} min ago — skipping")
        return

    # Imported here so the skip path above needs no Telegram libs/connection.
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession

    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    session = os.environ["TG_SESSION"]

    run_at = now_utc()
    sent = None
    commands = None
    with TelegramClient(StringSession(session), api_id, api_hash) as client:
        bot = client.get_entity(BOT)

        history = client.get_messages(bot, limit=1)
        if not history:
            # Never talked to this bot: subscribe once so it starts pushing.
            client.send_message(bot, "/start")
            sent = "/start"
            time.sleep(8)

        posts = read_posts(client, bot)
        newest_at = data_time(*posts[0]) if posts else None
        last_refresh = _parse_ts(state.get("last_refresh_at"))
        stale = newest_at is None or (run_at - newest_at).total_seconds() > STALE_MIN * 60
        refresh_due = last_refresh is None or (run_at - last_refresh).total_seconds() > STALE_MIN * 60
        if REFRESH_CMD and sent is None and stale and refresh_due:
            client.send_message(bot, REFRESH_CMD)
            sent = REFRESH_CMD
            time.sleep(8)
            posts = read_posts(client, bot)

        # Record the bot's command menu once, so SARVA_REFRESH_CMD can be
        # chosen from the admin panel's worker section if ever needed.
        if not state.get("bot_commands"):
            try:
                from telethon.tl.functions.users import GetFullUserRequest

                full = client(GetFullUserRequest(bot))
                info = getattr(full.full_user, "bot_info", None)
                cmds = getattr(info, "commands", None) or []
                commands = [{"command": c.command, "description": c.description} for c in cmds]
            except Exception as e:
                print(f"[sarva] could not read bot commands: {e}")

    rows = []
    for msg, parsed in posts[:6]:  # newest few are plenty; older ones are already stored
        when = msg.edit_date or msg.date
        rows.append({
            "message_id": msg.id,
            "message_at": when.isoformat() if when else None,
            **parsed,
            "raw_text": (msg.message or "")[:4000],
        })
    upsert_raw(rows)

    newest = max((data_time(m, p) for m, p in posts), default=None)
    st = {
        "last_run_at": run_at.isoformat(),
        "last_ok_at": now_utc().isoformat(),
        "last_error": None,
        "last_rows": len(rows),
    }
    if newest:
        st["last_post_at"] = newest.isoformat()
    if sent:
        st["last_refresh_at"] = run_at.isoformat()
        st["last_sent"] = sent
    if commands is not None:
        st["bot_commands"] = commands
    put_state(**st)

    print(f"[sarva] parsed & upserted {len(rows)} status post(s) from @{BOT}")
    for r in rows[:3]:
        print(
            f"  msg {r['message_id']} data@{r['source_updated_at']} | loc={r['reporting_location']} "
            f"wait={r['free_wait_min_hrs']}-{r['free_wait_max_hrs']}h waiting={r['waiting']}"
        )
    if not rows:
        print("[sarva] no status posts yet — the bot pushes every ~2h after /start")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[sarva] FAILED: {e}", file=sys.stderr)
        try:
            put_state(last_run_at=now_utc().isoformat(), last_error=str(e)[:500])
        except Exception:
            pass
        sys.exit(1)
