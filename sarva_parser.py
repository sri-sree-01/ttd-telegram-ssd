"""Parser for the "Tirumala Live Status" Telegram bot (@TirumalaLiveBot).

The bot pushes one long status post every couple of hours. We only want the
SARVA DARSHAN (free, general queue) part of it:

    🕐 Updated: 28th September 2026 11:30 AM IST
    📊 Crowd: Very High
    📈 Trend: increasing
    ⏰ Best time: Late Morning 8-11 AM
    📍 Reporting Location: Krishnateja Circle
    👥 Pilgrims Waiting in Compartments: 11,798
    ✅ Darshan Completed: 15,750
    📊 Balance Capacity for the day: 7,452      (or "Pilgrims Sent beyond capacity
                                                 for the day: 2,196")
    🚪 Active Compartments: 30/31
    ⏱ Free Darshanam Estimated Timing: 17-24 hrs

Everything else in the post (SSD/DD token timing, ₹300 timing, accommodation,
Srivani quota, links) is ignored ON PURPOSE — the app's Sarva Darshan screen
shows only the free queue.

These are the bot's exact figures. They are stored in the admin-only table
public.sarva_darshan_raw; the app never reads them directly. The database
rounds them to thousands and nudges them (see sarva_darshan_publish()) before
anything is shown to users.
"""
import re
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}

# A label may be preceded by an emoji / bullet and may be bold in Telegram
# (entities are separate from the text, so no markdown noise here).
_NUM = r"([\d][\d,]*)"


def _int(s):
    if s is None:
        return None
    try:
        return int(s.replace(",", "").strip())
    except ValueError:
        return None


def _clean(s):
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip(" .:-*_")
    return s or None


def _line_value(text, label_regex):
    """Value after `<label>:` up to the end of that line."""
    m = re.search(r"(?im)^[^\w\n]*" + label_regex + r"\s*[:：]\s*(.+?)\s*$", text)
    return _clean(m.group(1)) if m else None


def _parse_updated(text):
    """'Updated: 28th September 2026 11:30 AM IST' -> aware UTC datetime."""
    m = re.search(
        r"Updated\s*[:：]?\s*(\d{1,2})(?:st|nd|rd|th)?[\s\-/]+([A-Za-z]{3,9})\.?,?[\s\-/]+(\d{4}),?\s+"
        r"(?:at\s+)?(\d{1,2})[:.](\d{2})\s*([AaPp])\.?\s?[Mm]\.?",
        text,
    )
    if not m:
        return None
    day, mon_name, year, hh, mm, ap = m.groups()
    mon = _MONTHS.get(mon_name.lower())
    if not mon:
        return None
    h = int(hh) % 12 + (12 if ap.upper() == "P" else 0)
    try:
        local = datetime(int(year), mon, int(day), h, int(mm), tzinfo=IST)
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


def _parse_free_wait(text):
    """'Free Darshanam Estimated Timing: 17-24 hrs' -> (17.0, 24.0)."""
    t = text.replace("–", "-").replace("—", "-")
    head = r"Free\s+Darshan\w*\s*(?:Estimated\s+)?(?:Waiting\s+)?(?:Timing|Time)s?\s*[:：]\s*"
    m = re.search(
        head + r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:hrs?|hours?)\b",
        t,
        re.I,
    )
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi
    m = re.search(head + r"(\d+(?:\.\d+)?)\s*\+?\s*(?:hrs?|hours?)\b", t, re.I)
    if m:
        v = float(m.group(1))
        return v, v
    return None, None


def parse_sarva_message(text):
    """Return the Sarva Darshan fields of a status post, or None if this post
    isn't a live-status post (announcements, welcome text, etc.)."""
    if not text or len(text) < 40:
        return None

    waiting = _int(
        (re.search(r"Waiting\s+in\s+(?:the\s+)?Compartments?\s*[:：]\s*" + _NUM, text, re.I) or [None, None])[1]
    )
    completed = _int(
        (re.search(r"Darshan\s+Completed(?:\s*\(\s*Today\s*\))?\s*[:：]\s*" + _NUM, text, re.I) or [None, None])[1]
    )
    balance = _int(
        (re.search(r"Balance\s+Capacity(?:\s+for\s+the\s+day)?\s*[:：]\s*" + _NUM, text, re.I) or [None, None])[1]
    )
    beyond = _int(
        (re.search(r"beyond\s+(?:the\s+)?capacity(?:\s+for\s+the\s+day)?\s*[:：]\s*" + _NUM, text, re.I) or [None, None])[1]
    )

    comp_active = comp_total = None
    cm = re.search(r"Active\s+Compartments?\s*[:：]\s*(\d+)\s*(?:/|of)\s*(\d+)", text, re.I)
    if cm:
        comp_active, comp_total = int(cm.group(1)), int(cm.group(2))
    else:
        cm = re.search(r"Active\s+Compartments?\s*[:：]\s*(\d+)\b", text, re.I)
        if cm:
            comp_active = int(cm.group(1))

    wait_lo, wait_hi = _parse_free_wait(text)

    location = _line_value(text, r"Reporting\s+(?:Location|Point)")
    crowd = _line_value(text, r"Crowd(?:\s+Level)?")  # "Crowd: X" — NOT "Crowd is X"
    trend = _line_value(text, r"Trend")
    best = _line_value(text, r"Best\s+Time(?:\s+for\s+Darshan)?")

    core = [waiting, completed, wait_lo, location, comp_active]
    if sum(v is not None for v in core) < 2:
        return None  # not a live-status post

    # Sanity bounds — a parsing slip must never publish nonsense.
    def within(v, lo, hi):
        return v if (v is not None and lo <= v <= hi) else None

    waiting = within(waiting, 0, 300000)
    completed = within(completed, 0, 300000)
    balance = within(balance, 0, 300000)
    beyond = within(beyond, 0, 300000)
    if comp_total is not None and not (1 <= comp_total <= 200):
        comp_active = comp_total = None
    if comp_active is not None and comp_total is not None and comp_active > comp_total:
        comp_active = comp_total
    if wait_hi is not None and not (0 <= wait_hi <= 96):
        wait_lo = wait_hi = None

    updated = _parse_updated(text)
    return {
        "source_updated_at": updated.isoformat() if updated else None,
        "crowd_text": crowd[:60] if crowd else None,
        "trend_text": trend[:60] if trend else None,
        "best_time_text": best[:80] if best else None,
        "reporting_location": location[:120] if location else None,
        "waiting": waiting,
        "completed": completed,
        "balance_capacity": balance,
        "beyond_capacity": beyond,
        "compartments_active": comp_active,
        "compartments_total": comp_total,
        "free_wait_min_hrs": wait_lo,
        "free_wait_max_hrs": wait_hi,
    }
