"""Parser for LaxmiTeluguTech channel SSD/DD token-status messages.

Handles the formats seen in the channel, e.g.:
    SSD & DD Tokens Issue Started @ 10.30Am
    SSD Tokens - Current Status:
    • Available Tokens: 9689
    Srivari Mettu Divya Darshan Tokens:
    • Available Tokens: 1949
and the "Quota Completed" variants. Robust to minor wording/spacing changes.
"""
import re


def normalize_time(raw):
    """'10.30Am' / '1:16 PM' / '10 AM' -> 'HH:MM AM/PM'."""
    if not raw:
        return None
    m = re.search(r"(\d{1,2})[.:](\d{2})\s*([APap])\.?\s?[Mm]\.?", raw)
    if m:
        h, mm, ap = int(m.group(1)), m.group(2), m.group(3).upper()
    else:
        m2 = re.search(r"(\d{1,2})\s*([APap])\.?\s?[Mm]\.?", raw)  # "10 AM"
        if not m2:
            return None
        h, mm, ap = int(m2.group(1)), "00", m2.group(2).upper()
    if h < 1 or h > 12:
        return None
    return f"{h:02d}:{mm} {ap}M"


def _section_status(seg):
    """Return (available:int|None, completed:bool|None) for one section."""
    if re.search(r"Quota\s*Completed|Sold\s*Out|No\s*Tokens", seg, re.I):
        return None, True
    m = re.search(r"Available\s*Tokens?\s*[:\-]?\s*([\d,]+)", seg, re.I)
    if m:
        return int(m.group(1).replace(",", "")), False
    return None, None


def parse_message(text):
    """Return a dict of token status, or None if this isn't a token-status post."""
    if not text:
        return None
    t = text.replace("–", "-").replace("—", "-")  # normalise en/em dashes

    issue = None
    im = re.search(
        r"Issue\s*Started\s*@?\s*([0-9]{1,2}[.:][0-9]{2}\s*[APap]\.?\s?[Mm]\.?)", t, re.I
    )
    if im:
        issue = normalize_time(im.group(1))

    # Split SSD vs Mettu/DD on the Mettu anchor.
    ma = re.search(r"(?:Srivari|Sreevari)\s+Mettu|Mettu\s+Divya|\bMettu\b", t, re.I)
    if ma:
        ssd_seg, mettu_seg = t[: ma.start()], t[ma.start():]
    else:
        ssd_seg, mettu_seg = t, ""

    ssd_av, ssd_done = _section_status(ssd_seg)
    mettu_av, mettu_done = _section_status(mettu_seg) if mettu_seg else (None, None)

    # Only accept posts that carry a real status marker; ignore prose
    # announcements (e.g. "…issued continuously till completed",
    # "…Issue NOT Started yet") that merely mention these words.
    if not re.search(r"Current\s*Status|Available\s*Tokens?|Quota\s*Completed", t, re.I):
        return None
    return {
        "issue_started_time": issue,
        "ssd_available": ssd_av,
        "ssd_completed": ssd_done,
        "mettu_available": mettu_av,
        "mettu_completed": mettu_done,
    }
