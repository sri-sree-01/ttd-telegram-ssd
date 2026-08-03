from parser import parse_message, normalize_time
fails = 0
def eq(label, got, exp):
    global fails
    ok = got == exp
    if not ok: fails += 1; print("FAIL", label, "got", got, "exp", exp)
    else: print("ok  ", label, got)

# From the screenshots:
m1 = "SSD & DD Tokens Issue Started @ 10.30Am\nSSD Tokens - Current Status:\n• Available Tokens: 9689\nSrivari Mettu Divya Darshan Tokens:\n• Available Tokens: 1949"
r = parse_message(m1)
eq("m1 issue", r['issue_started_time'], "10:30 AM")
eq("m1 ssd", r['ssd_available'], 9689); eq("m1 ssd_done", r['ssd_completed'], False)
eq("m1 mettu", r['mettu_available'], 1949)

m2 = "SSD Tokens - Current Status:\n• Available Tokens: 7712\nSrivari Mettu Divya Darshan Tokens:\n• Available Tokens: 1636"
r = parse_message(m2)
eq("m2 ssd", r['ssd_available'], 7712); eq("m2 mettu", r['mettu_available'], 1636); eq("m2 issue", r['issue_started_time'], None)

m3 = "SSD Tokens - Current Status:\n• Available Tokens: 160\nSrivari Mettu Divya Darshan Tokens:\n• Available Tokens: 717"
r = parse_message(m3); eq("m3 ssd", r['ssd_available'], 160); eq("m3 mettu", r['mettu_available'], 717)

m4 = "SSD Tokens - Current Status:\n• Quota Completed\nSrivari Mettu Divya Darshan Tokens:\n• Available Tokens: 616"
r = parse_message(m4)
eq("m4 ssd_done", r['ssd_completed'], True); eq("m4 ssd_av", r['ssd_available'], None); eq("m4 mettu", r['mettu_available'], 616)

m5 = "SSD Tokens - Current Status:\n• Quota Completed\nSrivari Mettu Divya Darshan Tokens:\n• Quota Completed"
r = parse_message(m5); eq("m5 ssd_done", r['ssd_completed'], True); eq("m5 mettu_done", r['mettu_completed'], True)

# Non-status message (Telugu announcement) -> None
eq("m6 non-status", parse_message("టీటీడీ ముఖ్య ప్రజాసంబంధాల అధికారిచే విడుదల చేయబడినది"), None)

# Prose announcement that mentions "completed" / "Mettu" but is NOT a status post -> None
m7 = "10K SSD & 2K Srivari Mettu tokens for 2nd August Issue NOT Started yet.\n\nGuys pls wait patiently at SSD counters until they receive orders they won't issue but once started all tokens issued continuously till completed"
eq("m7 prose-not-status", parse_message(m7), None)

# time normaliser variants
eq("t1", normalize_time("10.30Am"), "10:30 AM")
eq("t2", normalize_time("1:16 PM"), "01:16 PM")
eq("t3", normalize_time("10.32 am"), "10:32 AM")

print("\nRESULT:", "PASS ✅" if fails == 0 else f"FAIL ❌ ({fails})")
