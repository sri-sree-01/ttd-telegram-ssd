"""Offline tests for sarva_parser.py — run: python test_sarva_parser.py

Samples are transcribed from real "Tirumala Live Status" bot posts
(screenshots, 28 Sep 2026), plus the "beyond capacity" variant.
"""
from sarva_parser import parse_sarva_message

SAMPLE_BALANCE = """🕉 Tirumala Live Status
━━━━━━━━━━━━━━━━
🕐 Updated: 28th September 2026 11:30 AM IST

📊 Crowd: Very High
📈 Trend: increasing
⏰ Best time: Late Morning 8-11 AM

📍 Reporting Location: Krishnateja Circle
👥 Pilgrims Waiting in Compartments: 11,798
✅ Darshan Completed: 15,750
📊 Balance Capacity for the day: 7,452
🚪 Active Compartments: 30/31
━━━━━━━━━━━━━━━━
🔴 Crowd is Very High
⏱ Free Darshanam Estimated Timing: 17-24 hrs
🎟 SSD / DD Token Darshanam Timing: 3-6 hrs
💰 300₹ Darshanam Timing: 2-5 hrs
━━━━━━━━━━━━━━━━
🎟 SSD / DD TOKENS
🕐 Released yesterday at 06:30 PM
🛑 Completed yesterday · SSD 07:40 PM · DD 07:40 PM
⏰ Expected SSD release today: after 06:30 PM (based on yesterday)
━━━━━━━━━━━━━━━━
🏨 ACCOMMODATION
📋 Quota: 1,600
✅ Registered: 1,542
🛏 Awaiting to receive keys for allotted room: 827
━━━━━━━━━━━━━━━━
🪷 Srivani Tickets · Airport Quota
🟤 Sold out
📋 Quota: 200
🔗 Full details on website
🌐 www.TirumalaInfo.com
"""

SAMPLE_BEYOND = """🕉 Tirumala Live Status
━━━━━━━━━━━━━━━━
🕐 Updated: 24th Sep 2026 09:30 PM IST

📊 Crowd: High
📉 Trend: decreasing
⏰ Best time: Early Morning 3–5 AM

📍 Reporting Location: Krishnateja Circle
👥 Pilgrims Waiting in Compartments: 11,496
✅ Darshan Completed: 20,700
⚠️ Pilgrims Sent beyond capacity for the day: 2,196
🚪 Active Compartments: 29/31
━━━━━━━━━━━━━━━━
🟠 Crowd is High
⏱ Free Darshanam Estimated Timing: 7 – 16 hrs
🎟 SSD / DD Token Darshanam Timing: 2-4 hrs
💰 300₹ Darshanam Timing: 2-3 hrs
"""

WELCOME = """Welcome to Tirumala Live Status bot! 🙏
Use the menu to get darshan queue status, tokens and rooms."""

SSD_ONLY = """🎟 SSD / DD TOKENS
🕐 Released today at 06:30 PM
Free Darshanam timings will be updated soon."""

SINGLE_WAIT = """Tirumala Live Status
Updated: 1st Oct 2026, 6:05 am IST
Crowd: Low
Reporting Location: VQC-2 Compartments
Pilgrims Waiting in Compartments: 850
Active Compartments: 4 / 31
Free Darshanam Estimated Timing: 6 hrs
"""


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_balance():
    p = parse_sarva_message(SAMPLE_BALANCE)
    check(p is not None, "balance sample should parse")
    check(p["source_updated_at"] == "2026-09-28T06:00:00+00:00", p["source_updated_at"])
    check(p["crowd_text"] == "Very High", p["crowd_text"])
    check(p["trend_text"] == "increasing", p["trend_text"])
    check(p["best_time_text"] == "Late Morning 8-11 AM", p["best_time_text"])
    check(p["reporting_location"] == "Krishnateja Circle", p["reporting_location"])
    check(p["waiting"] == 11798, p["waiting"])
    check(p["completed"] == 15750, p["completed"])
    check(p["balance_capacity"] == 7452, p["balance_capacity"])
    check(p["beyond_capacity"] is None, p["beyond_capacity"])
    check((p["compartments_active"], p["compartments_total"]) == (30, 31), p)
    # Must be the FREE darshan timing, never SSD (3-6) or ₹300 (2-5).
    check((p["free_wait_min_hrs"], p["free_wait_max_hrs"]) == (17.0, 24.0), p)


def test_beyond():
    p = parse_sarva_message(SAMPLE_BEYOND)
    check(p is not None, "beyond sample should parse")
    check(p["source_updated_at"] == "2026-09-24T16:00:00+00:00", p["source_updated_at"])
    check(p["crowd_text"] == "High", p["crowd_text"])
    check(p["trend_text"] == "decreasing", p["trend_text"])
    check(p["best_time_text"] == "Early Morning 3–5 AM", p["best_time_text"])
    check(p["waiting"] == 11496 and p["completed"] == 20700, p)
    check(p["balance_capacity"] is None and p["beyond_capacity"] == 2196, p)
    check((p["compartments_active"], p["compartments_total"]) == (29, 31), p)
    check((p["free_wait_min_hrs"], p["free_wait_max_hrs"]) == (7.0, 16.0), p)


def test_single_wait_and_variants():
    p = parse_sarva_message(SINGLE_WAIT)
    check(p is not None, "single-wait sample should parse")
    check(p["source_updated_at"] == "2026-10-01T00:35:00+00:00", p["source_updated_at"])
    check((p["free_wait_min_hrs"], p["free_wait_max_hrs"]) == (6.0, 6.0), p)
    check((p["compartments_active"], p["compartments_total"]) == (4, 31), p)
    check(p["reporting_location"] == "VQC-2 Compartments", p)
    check(p["waiting"] == 850, p)


def test_ignores_non_status_posts():
    check(parse_sarva_message(WELCOME) is None, "welcome text must be ignored")
    check(parse_sarva_message(SSD_ONLY) is None, "SSD-only text must be ignored")
    check(parse_sarva_message("") is None, "empty")
    check(parse_sarva_message(None) is None, "None")


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  ", t.__name__)
    print(f"all {len(tests)} sarva parser tests passed")
