"""Parser for LaxmiTeluguTech channel SSD/DD token-status messages.

Handles the formats seen in the channel, e.g.:
    SSD & DD Tokens Issue Started @ 10.30Am
    SSD Tokens - Current Status:
    • Available Tokens: 9689
    Srivari Mettu Divya Darshan Tokens:
    • Available Tokens: 1949
and the "Quota Completed" variants. These posts are typed by a person, not a
bot, so wording drifts: "Issued Started", "Tokens Started @", "Started
Issuing at", "Sold Out", "No Tokens Available", "Tokens Over" have all been
seen for what is really the same two events (open / completed). The regexes
below match on the KEY WORDS (start/issue, complete/sold-out/over/exhausted)
rather than one fixed phrase, so small typos and reorderings still parse —
while still requiring the words be adjacent, so prose that merely mentions
"completed" or "started" in passing (e.g. "Issue NOT Started yet", "...till
completed") is not mistaken for a real status line.
"""
import re

# "Issue Started @ 7pm" / "Issued Start@7.00Pm" / "Tokens Started @ 7 PM" /
# "Token Issue Started @ 7pm" / "Started Issuing at 7pm" / "Distribution
# Started @ 7am". Each alternative requires the key words to sit right next
# to each other (only whitespace between), so a negation wedged between them
# — "Issue NOT Started yet" — breaks the match instead of accidentally
# satisfying it.
ISSUE_RE = re.compile(
    r"(?:"
    r"Iss\w*\s+Start\w*"                    # Issue(d) Start(ed)
    r"|Start\w*\s+Iss\w*"                   # Start(ed) Issu(ing)
    r"|Token\w*\s+(?:Iss\w*\s+)?Start\w*"   # Token(s) Start(ed) / Token(s) Issue Started
    r"|Distribut\w*\s+Start\w*"             # Distribution Started
    r")\s*(?:@|at)?\s*(\d{1,2}[.:]?\d{0,2}\s*[APap]\.?\s?[Mm]\.?)",
    re.I,
)

# "Quota Completed" / "Tokens Completed" / "Sold Out" / "No Tokens
# Available" / "Tokens Over" / "Exhausted" / "Fully Booked". Requiring
# "Quota"/"Token(s)"/"SSD" immediately before "Compl…"/"Over" keeps this from
# firing on prose that just happens to contain the word "completed" or
# "over" elsewhere in a sentence.
COMPLETED_RE = re.compile(
    r"(?:Quota|Tokens?)\s*Compl\w*"
    r"|Sold\s*Out"
    r"|No\s*Tokens?(?:\s*Available)?"
    r"|(?:Tokens?|Quota|SSD)\s*Over\b"
    r"|Exhaust\w*"
    r"|Fully\s*Booked",
    re.I,
)

STATUS_HINT_RE = re.compile(
    r"Current\s*Status|Available\s*Tokens?|" + COMPLETED_RE.pattern, re.I,
)


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
    if COMPLETED_RE.search(seg):
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
    im = ISSUE_RE.search(t)
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
    # "…Issue NOT Started yet") that merely mention these words. A bare
    # "Issue Started @ …" with no counts yet is still accepted — it's a
    # real signal (the open time), just an early one.
    if not (STATUS_HINT_RE.search(t) or im):
        return None
    return {
        "issue_started_time": issue,
        "ssd_available": ssd_av,
        "ssd_completed": ssd_done,
        "mettu_available": mettu_av,
        "mettu_completed": mettu_done,
    }
